from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

from .config import load_worker_config
from .ig_api import InstagramGraph


def parse_ig_created_time(s: str | None) -> datetime | None:
    """
    IG often returns created_time like:
      - '2026-04-23T22:14:01+0000'
      - '2026-04-23T22:14:01+00:00'
      - sometimes ISO with Z
    We'll normalize a bit.
    """
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
    # Our DB timestamps are ISO with timezone
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def pick_role(ig_user_id: str, msg: dict) -> str:
    frm = (msg.get("from") or {}).get("id")
    if str(frm) == str(ig_user_id):
        return "assistant"  # your account
    return "user"         # the peer


def main():
    load_dotenv()
    cfg = load_worker_config()

    sb = create_client(cfg.supabase_url, cfg.supabase_service_role_key)
    graph = InstagramGraph(cfg.api_version, cfg.access_token)

    # 1) get latest ready_for_ai preprocess_run
    res = (
        sb.table("preprocess_runs")
        .select("*")
        .eq("status", "ready_for_ai")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    if not rows:
        raise SystemExit("No preprocess_runs with status=ready_for_ai found.")

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

    # 2) fetch messages from conversation
    msgs = graph.list_messages(conversation_ext_id, limit=50, max_pages=20)

    # 3) filter by time window
    picked = []
    for m in msgs:
        ct = parse_ig_created_time(m.get("created_time"))
        if not ct:
            continue
        if ws <= ct <= we:
            picked.append(m)

    # sort ascending by created_time
    picked.sort(key=lambda m: parse_ig_created_time(m.get("created_time")) or datetime(1970, 1, 1, tzinfo=timezone.utc))

    # 4) build transcript (no DB writes)
    transcript = []
    for m in picked:
        role = pick_role(ig_user_id, m)
        text = m.get("message") or ""
        transcript.append({
            "role": role,
            "created_time": m.get("created_time"),
            "text": text,
            "id": m.get("id"),
        })

    out = {
        "run_id": run_id,
        "conversation_id": run["conversation_id"],
        "window_start": window_start,
        "window_end": window_end,
        "conversation_ext_id": conversation_ext_id,
        "message_count_filtered": len(transcript),
        "transcript": transcript,
    }

    Path("transcripts").mkdir(parents=True, exist_ok=True)
    path = Path("transcripts") / f"{run_id}.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    print("Saved:", str(path))
    print("Filtered messages:", len(transcript))


if __name__ == "__main__":
    main()