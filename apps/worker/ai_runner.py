from __future__ import annotations

import os
import time
from typing import Any

from dotenv import load_dotenv

from apps.api.app import app as api_app
from apps.api.database import db
from apps.api.models import CaseSnapshot, Conversation, IgAccount, PreprocessRun, RiskCase
from apps.api.service_modules.utils import parse_dt, to_iso, utcnow

from .ai_client import chat_completions, extract_json_content, load_ai_config_from_env
from .ai_prompt import SYSTEM_PROMPT, build_user_prompt
from apps.api.service_modules.privacy import sanitize_ai_output
from .build_transcript import parse_ig_created_time, parse_iso_utc
from .config import load_worker_config
from .ig_api import InstagramGraph
from .resolve_conversation import resolve_conversation_identity


def fetch_one_ready_run() -> dict | None:
    run = (
        PreprocessRun.query.filter_by(status="ready_for_ai")
        .order_by(PreprocessRun.created_at.asc())
        .first()
    )
    if not run:
        return None
    return {
        "id": run.id,
        "conversation_id": run.conversation_id,
        "window_start": to_iso(run.window_start),
        "window_end": to_iso(run.window_end),
        "fetch_plan": run.fetch_plan or {},
    }


def mark_run_status(run_id: str, status: str, error: str | None = None) -> None:
    run = db.session.get(PreprocessRun, run_id)
    if not run:
        raise RuntimeError(f"Preprocess run not found: {run_id}")
    run.status = status
    run.error = (error or "")[:1000] if error else None
    run.updated_at = utcnow()
    db.session.commit()


def get_conversation(conversation_id: str) -> dict:
    conversation = db.session.get(Conversation, conversation_id)
    if not conversation:
        raise RuntimeError(f"Conversation not found: {conversation_id}")
    return {
        "id": conversation.id,
        "rolling_summary": conversation.rolling_summary,
        "ig_user_id": conversation.ig_account.ig_user_id if conversation.ig_account else None,
        "peer_id": conversation.peer_id,
    }


def get_graph_for_conversation(conversation_id: str, api_version: str) -> tuple[InstagramGraph, str]:
    conversation = db.session.get(Conversation, conversation_id)
    if not conversation or not conversation.ig_account_id:
        raise RuntimeError(f"Conversation not found or missing ig_account: {conversation_id}")

    ig_account = db.session.get(IgAccount, conversation.ig_account_id)
    if not ig_account:
        raise RuntimeError(f"ig_account not found: {conversation.ig_account_id}")

    if not ig_account.access_token:
        raise RuntimeError(f"ig_account {ig_account.id} has no access_token")

    return InstagramGraph(api_version, ig_account.access_token), ig_account.ig_user_id


def build_window_messages(graph: InstagramGraph, fetch_plan: dict) -> list[dict]:
    ig_user_id = fetch_plan["ig_user_id"]
    conversation_ext_id = fetch_plan["conversation_ext_id"]
    ws = parse_iso_utc(fetch_plan["window_start"])
    we = parse_iso_utc(fetch_plan["window_end"])

    msgs = graph.list_messages(conversation_ext_id, limit=80, max_pages=20)

    picked: list[tuple[Any, dict]] = []
    for m in msgs:
        ct = parse_ig_created_time(m.get("created_time"))
        if not ct:
            continue
        if ws <= ct <= we:
            picked.append((ct, m))

    picked.sort(key=lambda t: t[0])

    window_messages: list[dict] = []
    for ct, m in picked:
        window_messages.append(
            {
                "ts": ct.isoformat().replace("+00:00", "Z"),
                "direction": (
                    "outbound"
                    if str((m.get("from") or {}).get("id")) == str(ig_user_id)
                    else "inbound"
                ),
                "text": (m.get("message") or "").strip(),
                "ig_id": m.get("id"),
                "context": False,
            }
        )
    return window_messages


def persist_fetch_plan(run_id: str, fetch_plan: dict[str, Any]) -> None:
    run = db.session.get(PreprocessRun, run_id)
    if not run:
        raise RuntimeError(f"Preprocess run not found: {run_id}")
    run.fetch_plan = fetch_plan
    run.updated_at = utcnow()
    db.session.commit()


def update_rolling_summary(conversation_id: str, ai_json: dict[str, Any]) -> None:
    rolling = ai_json.get("rolling_summary")
    if not isinstance(rolling, dict):
        return
    conversation = db.session.get(Conversation, conversation_id)
    if not conversation:
        raise RuntimeError(f"Conversation not found: {conversation_id}")
    previous = conversation.rolling_summary if isinstance(conversation.rolling_summary, dict) else {}
    if previous.get("peer_username") and not rolling.get("peer_username"):
        rolling["peer_username"] = previous["peer_username"]
    conversation.rolling_summary = rolling
    db.session.commit()


def upsert_risk_case_and_snapshot(
    conversation_id: str,
    window_start: str,
    window_end: str,
    ai_json: dict[str, Any],
) -> None:
    assessment = (ai_json or {}).get("assessment") or {}
    stage = int(assessment.get("risk_stage") or 0)
    confidence = assessment.get("confidence")
    reason_safe = ((ai_json.get("explanation") or {}).get("short_reason_safe") or "")[:500]

    if stage <= 1:
        return

    existing = (
        RiskCase.query.filter_by(conversation_id=conversation_id, status="open")
        .order_by(RiskCase.opened_at.desc())
        .first()
    )
    if existing:
        risk_case = existing
        risk_case.stage = stage
        risk_case.confidence = confidence
        risk_case.reason_safe = reason_safe
        risk_case.evidence_window_start = parse_dt(window_start)
        risk_case.evidence_window_end = parse_dt(window_end)
    else:
        risk_case = RiskCase(
            conversation_id=conversation_id,
            status="open",
            stage=stage,
            confidence=confidence,
            reason_safe=reason_safe,
            evidence_window_start=parse_dt(window_start),
            evidence_window_end=parse_dt(window_end),
        )
        db.session.add(risk_case)
        db.session.flush()

    db.session.add(
        CaseSnapshot(
            risk_case_id=risk_case.id,
            snapshot_json=ai_json,
            encrypted=False,
        )
    )
    db.session.commit()


def _finish_reason(resp: dict[str, Any]) -> str:
    try:
        return ((resp.get("choices") or [{}])[0]).get("finish_reason") or ""
    except Exception:
        return ""


def run_once() -> None:
    load_dotenv()
    cfg = load_worker_config()
    ai_cfg = load_ai_config_from_env()

    with api_app.app_context():
        run = fetch_one_ready_run()
        if not run:
            print("[ai] no ready_for_ai runs")
            return

        run_id = run["id"]
        conv_id = run["conversation_id"]
        fetch_plan = run.get("fetch_plan") or {}

        try:
            mark_run_status(run_id, "processing")

            conv = get_conversation(conv_id)
            rolling_prev = conv.get("rolling_summary")

            graph, account_ig_user_id = get_graph_for_conversation(conv_id, cfg.api_version)
            if account_ig_user_id and conv.get("ig_user_id") and str(account_ig_user_id) != str(conv.get("ig_user_id")):
                print(f"[ai] warning ig_user_id mismatch conv={conv.get('ig_user_id')} account={account_ig_user_id}")

            conversation = db.session.get(Conversation, conv_id)
            if not conversation:
                raise RuntimeError(f"Conversation not found: {conv_id}")

            if account_ig_user_id and not fetch_plan.get("ig_user_id"):
                fetch_plan["ig_user_id"] = account_ig_user_id

            if run.get("window_start") and not fetch_plan.get("window_start"):
                fetch_plan["window_start"] = run["window_start"]

            if run.get("window_end") and not fetch_plan.get("window_end"):
                fetch_plan["window_end"] = run["window_end"]

            if conversation.conversation_ext_id and not fetch_plan.get("conversation_ext_id"):
                fetch_plan["conversation_ext_id"] = conversation.conversation_ext_id

            if not fetch_plan.get("conversation_ext_id"):
                resolved = resolve_conversation_identity(graph, account_ig_user_id, conversation.peer_id)
                if not resolved:
                    mark_run_status(run_id, "skipped", error="conversation_ext_id missing")
                    print(f"[ai] skipped run_id={run_id} missing conversation_ext_id")
                    return
                conversation.conversation_ext_id = resolved.get("conversation_ext_id")
                fetch_plan["conversation_ext_id"] = conversation.conversation_ext_id
                peer_username = resolved.get("peer_username")
                if peer_username:
                    rolling = conversation.rolling_summary if isinstance(conversation.rolling_summary, dict) else {}
                    conversation.rolling_summary = {**rolling, "peer_username": peer_username}
                db.session.commit()

            missing_fetch_plan = [
                key for key in ("ig_user_id", "conversation_ext_id", "window_start", "window_end")
                if not fetch_plan.get(key)
            ]
            if missing_fetch_plan:
                error = f"fetch_plan missing required fields: {', '.join(missing_fetch_plan)}"
                mark_run_status(run_id, "skipped", error=error)
                print(f"[ai] skipped run_id={run_id} {error}")
                return

            persist_fetch_plan(run_id, fetch_plan)
            window_messages = build_window_messages(graph, fetch_plan)
            print(f"[ai] run_id={run_id} conv_id={conv_id} window_msgs={len(window_messages)}")

            user_prompt = build_user_prompt(
                rolling_summary_prev=rolling_prev,
                window_messages=window_messages,
                window_start=fetch_plan.get("window_start") or str(run.get("window_start")),
                window_end=fetch_plan.get("window_end") or str(run.get("window_end")),
            )

            last_err: Exception | None = None
            for attempt in (1, 2):
                resp = chat_completions(
                    ai_cfg,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                fr = _finish_reason(resp)
                try:
                    ai_json = extract_json_content(resp)
                    break
                except Exception as e:
                    last_err = e
                    print(f"[ai] parse_failed attempt={attempt} finish_reason={fr!r} err={e}")
                    if attempt == 2:
                        raise
                    user_prompt = build_user_prompt(
                        rolling_summary_prev=None,
                        window_messages=window_messages,
                        window_start=fetch_plan.get("window_start") or str(run.get("window_start")),
                        window_end=fetch_plan.get("window_end") or str(run.get("window_end")),
                    )
            else:
                raise last_err or RuntimeError("AI parse failed")

            ai_json = sanitize_ai_output(ai_json)
            update_rolling_summary(conv_id, ai_json)
            upsert_risk_case_and_snapshot(
                conversation_id=conv_id,
                window_start=str(run["window_start"]),
                window_end=str(run["window_end"]),
                ai_json=ai_json,
            )

            mark_run_status(run_id, "ai_done")
            print(f"[ai] done run_id={run_id} messages={len(window_messages)}")

        except Exception as e:
            mark_run_status(run_id, "error", error=str(e))
            print(f"[ai] error run_id={run_id}: {e}")


def main() -> None:
    poll = int(os.getenv("AI_POLL_SECONDS", "10"))
    print(f"[ai] runner started poll={poll}s")
    while True:
        run_once()
        time.sleep(poll)


if __name__ == "__main__":
    main()
