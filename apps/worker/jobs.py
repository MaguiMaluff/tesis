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

    NOTE: Requires conversations.processing_lock_until / processing_lock_by columns.
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

    if lock_dt and lock_dt > utc_now():
        return False

    sb.table("conversations").update(
        {
            "processing_lock_until": until_iso,
            "processing_lock_by": lock_by,
        }
    ).eq("id", conversation_id).execute()

    return True


def release_conversation_lock(sb, conversation_id: str, lock_by: str):
    (
        sb.table("conversations")
        .update({"processing_lock_until": None, "processing_lock_by": None})
        .eq("id", conversation_id)
        .eq("processing_lock_by", lock_by)
        .execute()
    )


# ----------------------------
# IG account lookup helper
# ----------------------------
def get_ig_account_for_conversation(sb, conversation_id: str) -> dict:
    """
    Fetch conversation + its ig_account row.

    Expects:
      - conversations.ig_account_id exists (uuid)
      - ig_accounts.id exists
    """
    conv_res = (
        sb.table("conversations")
        .select(
            "id,ig_account_id,peer_id,conversation_ext_id,pending_count,pending_since,last_preprocessed_at"
        )
        .eq("id", conversation_id)
        .limit(1)
        .execute()
    )
    conv_rows = conv_res.data or []
    if not conv_rows:
        raise RuntimeError(f"Conversation not found: {conversation_id}")
    conv = conv_rows[0]

    ig_account_id = conv.get("ig_account_id")
    if not ig_account_id:
        raise RuntimeError(f"Conversation {conversation_id} has null ig_account_id")

    acc_res = (
        sb.table("ig_accounts")
        .select("id,ig_user_id,status,webhook_enabled")
        .eq("id", ig_account_id)
        .limit(1)
        .execute()
    )
    acc_rows = acc_res.data or []
    if not acc_rows:
        raise RuntimeError(f"ig_account not found: {ig_account_id}")

    acc = acc_rows[0]
    return {"conversation": conv, "ig_account": acc}


# ----------------------------
# Preprocess job
# ----------------------------
def preprocess_conversation(sb, graph, conv_row: dict, trigger: str):
    """
    Create preprocess_run with a fetch_plan; reset pending_count.
    No IA, no transcript stored.

    IMPORTANT:
      - graph is created outside (worker.py) using a token (MVP: one global token).
      - We resolve ig_user_id (external) via ig_accounts using conversations.ig_account_id.
    """
    conv_id = conv_row["id"]
    pending_count = int(conv_row.get("pending_count") or 0)

    if pending_count <= 0:
        return

    lock_by = f"worker:{trigger}"
    if not claim_conversation_lock(sb, conv_id, lock_by=lock_by, ttl_seconds=120):
        return

    try:
        # Re-fetch conversation + ig_account to ensure we have ig_account_id and external ig_user_id
        lookup = get_ig_account_for_conversation(sb, conv_id)
        conv_row = lookup["conversation"]
        ig_account = lookup["ig_account"]

        ig_user_id_ext = ig_account.get("ig_user_id")
        if not ig_user_id_ext:
            # Without external ig_user_id we can't resolve conversations via Graph API
            sb.table("preprocess_runs").insert(
                {
                    "conversation_id": conv_id,
                    "window_start": conv_row.get("pending_since") or conv_row.get("last_preprocessed_at") or utc_now_iso(),
                    "window_end": utc_now_iso(),
                    "trigger": trigger,
                    "status": "skipped",
                    "message_count": pending_count,
                    "fetch_plan": {
                        "source": "instagram",
                        "api_host": "graph.instagram.com",
                        "api_version": "env:API_VERSION",
                        "ig_account_id": conv_row.get("ig_account_id"),
                        "ig_user_id": None,
                        "conversation_ext_id": None,
                        "window_start": conv_row.get("pending_since") or conv_row.get("last_preprocessed_at") or utc_now_iso(),
                        "window_end": utc_now_iso(),
                        "strategy": "fetch_by_conversation_then_filter_by_time",
                        "fields": "id,from,to,message,created_time",
                        "notes": "Skipped because ig_user_id (external) is missing for ig_account.",
                    },
                    "error": "ig_user_id is null on ig_accounts; cannot resolve conversation_ext_id",
                }
            ).execute()
            return

        window_start = (
            conv_row.get("pending_since")
            or conv_row.get("last_preprocessed_at")
            or utc_now_iso()
        )
        window_end = utc_now_iso()

        conversation_ext_id = conv_row.get("conversation_ext_id")

        # Resolve conversation_ext_id if missing
        if not conversation_ext_id:
            resolved = resolve_conversation_ext_id(graph, ig_user_id_ext, conv_row["peer_id"])
            if resolved:
                conversation_ext_id = resolved
                (
                    sb.table("conversations")
                    .update({"conversation_ext_id": conversation_ext_id})
                    .eq("id", conv_id)
                    .execute()
                )

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
                        "ig_account_id": conv_row.get("ig_account_id"),
                        "ig_user_id": ig_user_id_ext,
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
            "ig_account_id": conv_row.get("ig_account_id"),
            "ig_user_id": ig_user_id_ext,
            "conversation_ext_id": conversation_ext_id,
            "window_start": window_start,
            "window_end": window_end,
            "strategy": "fetch_by_conversation_then_filter_by_time",
            "fields": "id,from,to,message,created_time",
            "notes": "Transcript will be reconstructed at AI-send time. No message text stored in DB.",
        }

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