from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from apps.api.app import app as api_app
from apps.api.database import db
from apps.api.models import Conversation, IgAccount, PreprocessRun

from .config import load_worker_config
from .ig_api import InstagramGraph
from .resolve_conversation import resolve_conversation_ext_id


def parse_ig_created_time(s: str | None) -> datetime | None:
    if not s:
        return None

    s = s.strip()

    if len(s) >= 5 and (s.endswith("+0000") or s.endswith("-0000")):
        s = s[:-5] + s[-5:-2] + ":" + s[-2:]

    if s.endswith("Z"):
        s = s[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def parse_iso_utc(s: str) -> datetime:
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def infer_direction(ig_user_id: str, msg: dict) -> str:
    frm = (msg.get("from") or {}).get("id")
    if str(frm) == str(ig_user_id):
        return "outbound"
    return "inbound"


def extract_text(msg: dict) -> str:
    return (msg.get("message") or msg.get("text") or "").strip()


def _fetch_run(run_id: str | None) -> dict:
    with api_app.app_context():
        query = PreprocessRun.query.filter_by(status="ready_for_ai").order_by(PreprocessRun.created_at.desc())
        if run_id:
            query = PreprocessRun.query.filter_by(id=run_id)

        run = query.first()
        if not run:
            raise SystemExit("No preprocess_runs found for the given query.")

        return {
            "id": run.id,
            "conversation_id": run.conversation_id,
            "window_start": run.window_start.isoformat().replace("+00:00", "Z"),
            "window_end": run.window_end.isoformat().replace("+00:00", "Z"),
            "fetch_plan": run.fetch_plan or {},
        }


def _load_conversation(conversation_id: str) -> dict:
    with api_app.app_context():
        conversation = db.session.get(Conversation, conversation_id)
        if not conversation:
            raise SystemExit(f"Conversation not found: {conversation_id}")
        ig_account = db.session.get(IgAccount, conversation.ig_account_id) if conversation.ig_account_id else None
        if not ig_account:
            raise SystemExit(f"ig_account not found for conversation: {conversation_id}")
        if not ig_account.access_token:
            raise SystemExit(f"ig_account {ig_account.id} has no access_token")
        if not conversation.conversation_ext_id:
            graph = InstagramGraph(load_worker_config().api_version, ig_account.access_token)
            resolved = resolve_conversation_ext_id(graph, ig_account.ig_user_id, conversation.peer_id)
            if not resolved:
                raise SystemExit(
                    f"Conversation {conversation_id} is missing conversation_ext_id; rerun preprocessing first"
                )
            conversation.conversation_ext_id = resolved
            db.session.commit()
        return {
            "id": conversation.id,
            "rolling_summary": conversation.rolling_summary,
            "ig_user_id": ig_account.ig_user_id,
            "access_token": ig_account.access_token,
            "peer_id": conversation.peer_id,
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=80, help="messages per page (IG API limit)")
    parser.add_argument("--max-pages", type=int, default=20, help="max pages to fetch from IG API")
    parser.add_argument(
        "--context-before",
        type=int,
        default=0,
        help="how many messages immediately before window_start to include as context (flagged context=true)",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default="",
        help="optional specific preprocess_run id to build transcript for (otherwise picks latest ready_for_ai)",
    )
    args = parser.parse_args()

    load_dotenv()
    cfg = load_worker_config()

    run = _fetch_run(args.run_id or None)
    fetch_plan = run.get("fetch_plan") or {}

    ig_user_id = fetch_plan.get("ig_user_id")
    conversation_ext_id = fetch_plan.get("conversation_ext_id")
    window_start = fetch_plan.get("window_start")
    window_end = fetch_plan.get("window_end")

    if not (ig_user_id and conversation_ext_id and window_start and window_end):
        raise SystemExit(f"Run {run['id']} fetch_plan missing required fields.")

    ws = parse_iso_utc(window_start)
    we = parse_iso_utc(window_end)

    conv = _load_conversation(run["conversation_id"])
    rolling_summary_prev = conv.get("rolling_summary")

    graph = InstagramGraph(cfg.api_version, conv["access_token"])
    msgs = graph.list_messages(conversation_ext_id, limit=args.limit, max_pages=args.max_pages)

    normalized = []
    for m in msgs:
        ct = parse_ig_created_time(m.get("created_time"))
        if not ct:
            continue
        normalized.append((ct, m))

    normalized.sort(key=lambda t: t[0])

    window_msgs = []
    for ct, m in normalized:
        if ws <= ct <= we:
            window_msgs.append((ct, m))

    context_msgs = []
    if args.context_before > 0:
        before = [(ct, m) for ct, m in normalized if ct < ws]
        context_msgs = before[-args.context_before:]

    def to_item(ct: datetime, m: dict, context: bool) -> dict:
        return {
            "ts": ct.isoformat().replace("+00:00", "Z"),
            "direction": infer_direction(ig_user_id, m),
            "text": extract_text(m),
            "ig_id": m.get("id"),
            "context": context,
        }

    out_messages = [to_item(ct, m, True) for ct, m in context_msgs] + [to_item(ct, m, False) for ct, m in window_msgs]

    out = {
        "run_id": run["id"],
        "conversation_id": run["conversation_id"],
        "window_start": window_start,
        "window_end": window_end,
        "conversation_ext_id": conversation_ext_id,
        "counts": {
            "context_before": len(context_msgs),
            "window": len(window_msgs),
            "total_sent": len(out_messages),
        },
        "rolling_summary_prev": rolling_summary_prev,
        "window_messages": out_messages,
    }

    Path("transcripts").mkdir(parents=True, exist_ok=True)
    path = Path("transcripts") / f"{run['id']}.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    print("Saved:", str(path))
    print("Window messages:", len(window_msgs), "| Context before:", len(context_msgs))


if __name__ == "__main__":
    main()