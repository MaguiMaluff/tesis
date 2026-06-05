from __future__ import annotations

from supabase import Client


def get_ig_account_for_conversation(sb: Client, conversation_id: str) -> dict:
    """
    Returns the ig_accounts row (joined manually) for a given conversation.
    Expects conversations.ig_account_id.
    """
    conv_res = (
        sb.table("conversations")
        .select("id,ig_account_id,peer_id,conversation_ext_id,pending_count,pending_since,last_preprocessed_at")
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
        .select("*")
        .eq("id", ig_account_id)
        .limit(1)
        .execute()
    )
    acc_rows = acc_res.data or []
    if not acc_rows:
        raise RuntimeError(f"ig_account not found: {ig_account_id}")

    acc = acc_rows[0]
    return {"conversation": conv, "ig_account": acc}