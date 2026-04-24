from __future__ import annotations

from supabase import create_client, Client


def make_supabase(url: str, key: str) -> Client:
    """
    Create a Supabase client.

    IMPORTANT (security):
    - This uses the Service Role key in this project.
    - Must be used only server-side (API/worker), never in frontend code.
    """
    return create_client(url, key)


def upsert_conversation(
    sb: Client,
    ig_user_id: str,
    peer_id: str,
    last_message_at_iso: str,
) -> dict:
    """
    Upsert a conversation row using the unique constraint (ig_user_id, peer_id).

    This function also maintains the "pending window" state:
      - pending_count: how many new messages arrived since the last preprocess.
      - pending_since: timestamp of the first pending message (window start).

    Behavior:
      - If conversation does not exist:
          create it with pending_count=1 and pending_since=last_message_at_iso.
      - If it exists:
          increment pending_count and keep pending_since unchanged if already set.
          (pending_since only gets set if it was NULL).
    """

    # 1) Look up existing conversation by unique key (ig_user_id, peer_id)
    existing = (
        sb.table("conversations")
        .select("*")
        .eq("ig_user_id", ig_user_id)
        .eq("peer_id", peer_id)
        .limit(1)
        .execute()
    )

    rows = existing.data or []

    # 2) Insert if missing
    if not rows:
        ins = (
            sb.table("conversations")
            .insert(
                {
                    "ig_user_id": ig_user_id,
                    "peer_id": peer_id,
                    "last_message_at": last_message_at_iso,
                    # First message in a new pending window
                    "pending_count": 1,
                    "pending_since": last_message_at_iso,
                    "status": "active",
                }
            )
            .execute()
        )
        return ins.data[0]

    # 3) Update if exists
    conv = rows[0]

    # Increment pending_count
    pending_count = int(conv.get("pending_count") or 0) + 1

    # Keep the original pending_since if it already exists.
    # If it's NULL, we set it to this message timestamp (start of new window).
    pending_since = conv.get("pending_since") or last_message_at_iso

    upd = (
        sb.table("conversations")
        .update(
            {
                "last_message_at": last_message_at_iso,
                "pending_count": pending_count,
                "pending_since": pending_since,
            }
        )
        .eq("id", conv["id"])
        .execute()
    )

    return upd.data[0]


def insert_message_event(
    sb: Client,
    conversation_id: str,
    mid: str,
    sent_at_iso: str,
    direction: str,
    text_hash: str | None,
    features: dict,
) -> bool:
    """
    Insert a message event row.

    Returns:
      True  -> inserted successfully
      False -> failed (most commonly because mid already exists due to retries/duplicates)

    Why we need this:
      - keep a minimal audit trail per message (without message text)
      - dedupe webhook retries via unique(mid)
    """
    try:
        sb.table("message_events").insert(
            {
                "conversation_id": conversation_id,
                "mid": mid,
                "sent_at": sent_at_iso,
                "direction": direction,
                "text_hash": text_hash,
                "features": features,
            }
        ).execute()
        return True
    except Exception:
        
        return False