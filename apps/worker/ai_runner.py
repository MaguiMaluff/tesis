from __future__ import annotations

import os
import time
from typing import Any

from dotenv import load_dotenv
from supabase import create_client

from .ai_client import chat_completions, extract_json_content, load_ai_config_from_env
from .ai_prompt import SYSTEM_PROMPT, build_user_prompt
from .build_transcript import parse_ig_created_time, parse_iso_utc
from .config import load_worker_config
from .ig_api import InstagramGraph


def fetch_one_ready_run(sb) -> dict | None:
    res = (
        sb.table("preprocess_runs")
        .select("*")
        .eq("status", "ready_for_ai")
        .order("created_at", desc=False)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def mark_run_status(sb, run_id: str, status: str, error: str | None = None) -> None:
    upd: dict[str, Any] = {"status": status}
    if error:
        upd["error"] = error[:1000]
    sb.table("preprocess_runs").update(upd).eq("id", run_id).execute()


def get_conversation(sb, conversation_id: str) -> dict:
    res = (
        sb.table("conversations")
        .select("*")
        .eq("id", conversation_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    if not rows:
        raise RuntimeError(f"Conversation not found: {conversation_id}")
    return rows[0]


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
                "direction": ("outbound" if str((m.get("from") or {}).get("id")) == str(ig_user_id) else "inbound"),
                "text": (m.get("message") or "").strip(),
                "ig_id": m.get("id"),
                "context": False,
            }
        )
    return window_messages


def update_rolling_summary(sb, conversation_id: str, ai_json: dict[str, Any]) -> None:
    rolling = ai_json.get("rolling_summary")
    if not isinstance(rolling, dict):
        return
    sb.table("conversations").update({"rolling_summary": rolling}).eq("id", conversation_id).execute()


def upsert_risk_case_and_snapshot(
    sb,
    conversation_id: str,
    window_start: str,
    window_end: str,
    ai_json: dict[str, Any],
) -> None:
    assessment = (ai_json or {}).get("assessment") or {}
    stage = int(assessment.get("risk_stage") or 0)
    confidence = assessment.get("confidence")
    reason_safe = ((ai_json.get("explanation") or {}).get("short_reason_safe") or "")[:500]

    # Only create/update risk_cases for meaningful risk
    if stage <= 1:
        return

    existing = (
        sb.table("risk_cases")
        .select("*")
        .eq("conversation_id", conversation_id)
        .eq("status", "open")
        .order("opened_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = existing.data or []
    if rows:
        risk_case_id = rows[0]["id"]
        sb.table("risk_cases").update(
            {
                "stage": stage,
                "confidence": confidence,
                "reason_safe": reason_safe,
                "evidence_window_start": window_start,
                "evidence_window_end": window_end,
            }
        ).eq("id", risk_case_id).execute()
    else:
        ins = (
            sb.table("risk_cases")
            .insert(
                {
                    "conversation_id": conversation_id,
                    "status": "open",
                    "stage": stage,
                    "confidence": confidence,
                    "reason_safe": reason_safe,
                    "evidence_window_start": window_start,
                    "evidence_window_end": window_end,
                }
            )
            .execute()
        )
        risk_case_id = ins.data[0]["id"]

    sb.table("case_snapshots").insert(
        {
            "risk_case_id": risk_case_id,
            "snapshot_json": ai_json,
            "encrypted": False,
        }
    ).execute()


def _finish_reason(resp: dict[str, Any]) -> str:
    try:
        return ((resp.get("choices") or [{}])[0]).get("finish_reason") or ""
    except Exception:
        return ""


def run_once() -> None:
    load_dotenv()
    cfg = load_worker_config()
    ai_cfg = load_ai_config_from_env()

    sb = create_client(cfg.supabase_url, cfg.supabase_service_role_key)
    graph = InstagramGraph(cfg.api_version, cfg.access_token)

    run = fetch_one_ready_run(sb)
    if not run:
        print("[ai] no ready_for_ai runs")
        return

    run_id = run["id"]
    conv_id = run["conversation_id"]
    fetch_plan = run.get("fetch_plan") or {}

    try:
        mark_run_status(sb, run_id, "processing")

        conv = get_conversation(sb, conv_id)
        rolling_prev = conv.get("rolling_summary")

        window_messages = build_window_messages(graph, fetch_plan)
        print(f"[ai] run_id={run_id} conv_id={conv_id} window_msgs={len(window_messages)}")

        user_prompt = build_user_prompt(
            rolling_summary_prev=rolling_prev,
            window_messages=window_messages,
            window_start=fetch_plan.get("window_start") or str(run.get("window_start")),
            window_end=fetch_plan.get("window_end") or str(run.get("window_end")),
        )

        # Try once, and retry once if JSON parse fails (common when response truncates)
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
                # If truncated, retry with a slightly smaller prompt next attempt (drop rolling_summary_prev)
                user_prompt = build_user_prompt(
                    rolling_summary_prev=None,
                    window_messages=window_messages,
                    window_start=fetch_plan.get("window_start") or str(run.get("window_start")),
                    window_end=fetch_plan.get("window_end") or str(run.get("window_end")),
                )
        else:
            raise last_err or RuntimeError("AI parse failed")

        update_rolling_summary(sb, conv_id, ai_json)
        upsert_risk_case_and_snapshot(
            sb,
            conversation_id=conv_id,
            window_start=str(run["window_start"]),
            window_end=str(run["window_end"]),
            ai_json=ai_json,
        )

        mark_run_status(sb, run_id, "ai_done")
        print(f"[ai] done run_id={run_id} messages={len(window_messages)}")

    except Exception as e:
        mark_run_status(sb, run_id, "error", error=str(e))
        print(f"[ai] error run_id={run_id}: {e}")


def main() -> None:
    poll = int(os.getenv("AI_POLL_SECONDS", "10"))
    print(f"[ai] runner started poll={poll}s")
    while True:
        run_once()
        time.sleep(poll)


if __name__ == "__main__":
    main()