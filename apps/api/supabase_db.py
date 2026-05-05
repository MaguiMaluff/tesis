from __future__ import annotations
from supabase import create_client, Client

def make_supabase(url: str, key: str) -> Client:
    return create_client(url, key)

def get_or_create_conversation(sb: Client, ig_user_id: str, peer_id: str, last_message_at_iso: str) -> dict:
    """
    Ensure a conversation exists for (ig_user_id, peer_id) WITHOUT incrementing pending_count.
    We still update last_message_at for observability.
    """
    existing = (
        sb.table("conversations")
          .select("*")
          .eq("ig_user_id", ig_user_id)
          .eq("peer_id", peer_id)
          .limit(1)
          .execute()
    )
    rows = existing.data or []
    if not rows:
        ins = (
            sb.table("conversations")
              .insert({
                  "ig_user_id": ig_user_id,
                  "peer_id": peer_id,
                  "last_message_at": last_message_at_iso,
                  "pending_count": 0,
                  "pending_since": None,
                  "status": "active",
              })
              .execute()
        )
        return ins.data[0]

    conv = rows[0]
    upd = (
        sb.table("conversations")
          .update({"last_message_at": last_message_at_iso})
          .eq("id", conv["id"])
          .execute()
    )
    return upd.data[0]


def mark_conversation_pending(sb: Client, conversation_id: str, sent_at_iso: str) -> dict:
    """
    Increment pending_count and set pending_since if currently NULL.
    Call this ONLY after message_events insert succeeds (non-duplicate).
    """
    current = (
        sb.table("conversations")
          .select("id,pending_count,pending_since")
          .eq("id", conversation_id)
          .limit(1)
          .execute()
    )
    rows = current.data or []
    if not rows:
        raise RuntimeError(f"Conversation not found: {conversation_id}")

    conv = rows[0]
    pending_count = int(conv.get("pending_count") or 0) + 1
    pending_since = conv.get("pending_since") or sent_at_iso

    upd = (
        sb.table("conversations")
          .update({
              "pending_count": pending_count,
              "pending_since": pending_since,
          })
          .eq("id", conversation_id)
          .execute()
    )
    return upd.data[0]

def insert_message_event(sb: Client, conversation_id: str, mid: str, sent_at_iso: str,
                         direction: str, text_hash: str | None, features: dict) -> bool:

    try:
        sb.table("message_events").insert({
            "conversation_id": conversation_id,
            "mid": mid,
            "sent_at": sent_at_iso,
            "direction": direction,
            "text_hash": text_hash,
            "features": features,
        }).execute()
        return True
    except Exception:
        return False