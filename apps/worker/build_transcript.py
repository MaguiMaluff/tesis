from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

from .config import load_worker_config
from .ig_api import InstagramGraph


def parse_ig_created_time(s: str | None) -> datetime | None:
    if not s:
        return None

    s = s.strip()

    # +0000 -> +00:00
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
    """
    Determine message direction relative to the monitored IG account.
    We avoid "user/assistant" here and keep explicit inbound/outbound,
    which is clearer for later risk analysis.
    """
    frm = (msg.get("from") or {}).get("id")
    if str(frm) == str(ig_user_id):
        return "outbound"
    return "inbound"


def extract_text(msg: dict) -> str:
    """
    IG API may use 'message' field for text. Keep best-effort fallback.
    """
    return (msg.get("message") or msg.get("text") or "").strip()


def main() -> None:
    """
    Fetches the latest preprocess_run (ready_for_ai), pulls IG messages for its window,
    and writes a JSON transcript file under ./transcripts.

    Enhancements vs previous version:
    - outputs direction=inbound/outbound (instead of role=user/assistant)
    - includes rolling_summary_prev from conversations (if present)
    - supports optional context messages before the window (for extra continuity)
    - keeps message objects compact for prompt usage
    """
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

    sb = create_client(cfg.supabase_url, cfg.supabase_service_role_key)
    graph = InstagramGraph(cfg.api_version, cfg.access_token)

    # 1) get preprocess_run
    q = sb.table("preprocess_runs").select("*").eq("status", "ready_for_ai").order("created_at", desc=True).limit(1)
    if args.run_id:
        q = sb.table("preprocess_runs").select("*").eq("id", args.run_id).limit(1)

    res = q.execute()
    rows = res.data or []
    if not rows:
        raise SystemExit("No preprocess_runs found for the given query.")

    run = rows[0]
    run_id = run["id"]
    fetch_plan = run.get("fetch_plan") or {}

    ig_user_id = fetch_plan.get("ig_user_id")
    conversation_ext_id = fetch_plan.get("conversation_ext_id")
    window_start = fetch_plan.get("window_start")
    window_end = fetch_plan.get("window_end")

    if not (ig_user_id and conversation_ext_id and window_start and window_end):
        raise SystemExit(f"Run {run_id} fetch_plan missing required fields.")

    ws = parse_iso_utc(window_start)
    we = parse_iso_utc(window_end)

    # 2) fetch conversation (for rolling_summary_prev)
    conv_res = (
        sb.table("conversations")
        .select("id,rolling_summary,ig_user_id,peer_id")
        .eq("id", run["conversation_id"])
        .limit(1)
        .execute()
    )
    conv_rows = conv_res.data or []
    rolling_summary_prev = None
    if conv_rows:
        rolling_summary_prev = conv_rows[0].get("rolling_summary")

    # 3) fetch messages from conversation (latest-first from API)
    msgs = graph.list_messages(conversation_ext_id, limit=args.limit, max_pages=args.max_pages)

    # 4) normalize + filter by time window
    normalized = []
    for m in msgs:
        ct = parse_ig_created_time(m.get("created_time"))
        if not ct:
            continue
        normalized.append((ct, m))

    # sort ascending by created_time
    normalized.sort(key=lambda t: t[0])

    # pick those inside the window
    window_msgs = []
    for ct, m in normalized:
        if ws <= ct <= we:
            window_msgs.append((ct, m))

    # context messages immediately before window_start
    context_msgs = []
    if args.context_before > 0:
        before = [(ct, m) for ct, m in normalized if ct < ws]
        context_msgs = before[-args.context_before :]

    # 5) build compact message list
    def to_item(ct: datetime, m: dict, context: bool) -> dict:
        return {
            "ts": ct.isoformat().replace("+00:00", "Z"),
            "direction": infer_direction(ig_user_id, m),
            "text": extract_text(m),
            "ig_id": m.get("id"),
            "context": context,
        }

    out_messages = [to_item(ct, m, True) for ct, m in context_msgs] + [
        to_item(ct, m, False) for ct, m in window_msgs
    ]

    out = {
        "run_id": run_id,
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
        "window_messages": out_messages,  # this is what will be paste into the LLM prompt
    }

    Path("transcripts").mkdir(parents=True, exist_ok=True)
    path = Path("transcripts") / f"{run_id}.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    print("Saved:", str(path))
    print("Window messages:", len(window_msgs), "| Context before:", len(context_msgs))


if __name__ == "__main__":
    main()