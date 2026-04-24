from __future__ import annotations

from datetime import datetime, timezone, timedelta
from .resolve_conversation import resolve_conversation_ext_id


# ----------------------------
# Time helpers
# ----------------------------
def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


# ----------------------------
# Best-effort conversation lock
# ----------------------------
def claim_conversation_lock(
    sb,
    conversation_id: str,
    lock_by: str,
    ttl_seconds: int = 120,
) -> bool:
    """
    Best-effort lock to prevent hourly + threshold from processing the same conversation
    at the same time (and creating multiple preprocess_runs).

    This is not perfectly atomic across multiple workers, but it's good enough for 1 worker instance.
    If you plan to scale workers horizontally, we should replace this with a single SQL RPC function.
    """
    until_iso = (utc_now() + timedelta(seconds=ttl_seconds)).isoformat()

    current = (
        sb.table("conversations")
        .select("processing_lock_until")
        .eq("id", conversation_id)
        .limit(1)
        .execute()
    )
    rows = current.data or []
    if not rows:
        return False

    lock_until = rows[0].get("processing_lock_until")
    lock_dt = _parse_iso(lock_until)

    # If lock exists and hasn't expired, do not claim.
    if lock_dt and lock_dt > utc_now():
        return False

    # Claim lock (best-effort)
    sb.table("conversations").update(
        {
            "processing_lock_until": until_iso,
            "processing_lock_by": lock_by,
        }
    ).eq("id", conversation_id).execute()

    return True


def release_conversation_lock(sb, conversation_id: str, lock_by: str):
    # Release only if we own it (best-effort)
    (
        sb.table("conversations")
        .update({"processing_lock_until": None, "processing_lock_by": None})
        .eq("id", conversation_id)
        .eq("processing_lock_by", lock_by)
        .execute()
    )


# ----------------------------
# Preprocess job
# ----------------------------
def preprocess_conversation(sb, graph, conv_row: dict, trigger: str):
    """
    Create preprocess_run with a fetch_plan; reset pending_count.
    No IA, no transcript stored.
    """
    conv_id = conv_row["id"]
    pending_count = int(conv_row.get("pending_count") or 0)

    # Nothing to do
    if pending_count <= 0:
        return

    # Acquire lock to avoid duplicates across threshold/hourly loops
    lock_by = f"worker:{trigger}"
    if not claim_conversation_lock(sb, conv_id, lock_by=lock_by, ttl_seconds=120):
        return

    try:
        window_start = (
            conv_row.get("pending_since")
            or conv_row.get("last_preprocessed_at")
            or utc_now_iso()
        )
        window_end = utc_now_iso()

        # Resolve conversation_ext_id if missing
        conversation_ext_id = conv_row.get("conversation_ext_id")
        if not conversation_ext_id:
            resolved = resolve_conversation_ext_id(
                graph,
                conv_row["ig_user_id"],
                conv_row["peer_id"],
            )
            if resolved:
                conversation_ext_id = resolved
                (
                    sb.table("conversations")
                    .update({"conversation_ext_id": conversation_ext_id})
                    .eq("id", conv_id)
                    .execute()
                )

        # If we couldn't resolve it, don't create a "ready_for_ai" run.
        # (Without conversation_ext_id we can't fetch /{conversation_id}/messages.)
        if not conversation_ext_id:
            sb.table("preprocess_runs").insert(
                {
                    "conversation_id": conv_id,
                    "window_start": window_start,
                    "window_end": window_end,
                    "trigger": trigger,
                    "status": "skipped",
                    "message_count": pending_count,
                    "fetch_plan": {
                        "source": "instagram",
                        "api_host": "graph.instagram.com",
                        "api_version": "env:API_VERSION",
                        "ig_user_id": conv_row.get("ig_user_id"),
                        "conversation_ext_id": None,
                        "window_start": window_start,
                        "window_end": window_end,
                        "strategy": "fetch_by_conversation_then_filter_by_time",
                        "fields": "id,from,to,message,created_time",
                        "notes": "Skipped because conversation_ext_id could not be resolved yet.",
                    },
                    "error": "conversation_ext_id is null; cannot fetch messages",
                }
            ).execute()
            return

        fetch_plan = {
            "source": "instagram",
            "api_host": "graph.instagram.com",
            "api_version": "env:API_VERSION",
            "ig_user_id": conv_row.get("ig_user_id"),
            "conversation_ext_id": conversation_ext_id,
            "window_start": window_start,
            "window_end": window_end,
            "strategy": "fetch_by_conversation_then_filter_by_time",
            "fields": "id,from,to,message,created_time",
            "notes": "Transcript will be reconstructed at AI-send time. No message text stored in DB.",
        }

        # Create preprocess run
        sb.table("preprocess_runs").insert(
            {
                "conversation_id": conv_id,
                "window_start": window_start,
                "window_end": window_end,
                "trigger": trigger,
                "status": "ready_for_ai",
                "message_count": pending_count,
                "fetch_plan": fetch_plan,
            }
        ).execute()

        # Reset pending
        sb.table("conversations").update(
            {
                "pending_count": 0,
                "pending_since": None,
                "last_preprocessed_at": window_end,
            }
        ).eq("id", conv_id).execute()

    finally:
        release_conversation_lock(sb, conv_id, lock_by=lock_by)


# ----------------------------
# Query helpers
# ----------------------------
def fetch_pending_conversations(sb, min_pending: int):
    res = (
        sb.table("conversations")
        .select("*")
        .gte("pending_count", min_pending)
        .eq("status", "active")
        .execute()
    )
    return res.data or []


def fetch_any_pending_conversations(sb):
    res = (
        sb.table("conversations")
        .select("*")
        .gt("pending_count", 0)
        .eq("status", "active")
        .execute()
    )
    return res.data or []