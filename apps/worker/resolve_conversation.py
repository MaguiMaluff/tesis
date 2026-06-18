from __future__ import annotations
from datetime import datetime, timezone

def _iso(s: str | None):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _participant_username(participant: dict) -> str | None:
    for key in ("username", "name"):
        value = str(participant.get(key) or "").strip().lstrip("@")
        if value:
            return value
    return None


def resolve_conversation_identity(graph, ig_user_id: str, peer_id: str, search_limit_conversations=50, probe_messages=5):
    """
    Try to map peer_id -> conversation_ext_id and readable peer username.
    Strategy:
      1) If conversations list includes participants, match peer_id.
      2) Else: probe a few messages from recent conversations and match peer_id in from/to.
    """
    convs = graph.list_conversations(ig_user_id, limit=search_limit_conversations, max_pages=2)

    # 1) Try participants
    for c in convs:
        parts = c.get("participants")
        if isinstance(parts, dict):
            data = parts.get("data") or []
            for p in data:
                pid = str(p.get("id", ""))
                if pid and pid == str(peer_id):
                    return {
                        "conversation_ext_id": c.get("id"),
                        "peer_username": _participant_username(p),
                    }

    # 2) Fallback: probe messages
    # sort by updated_time desc if present
    convs_sorted = sorted(
        convs,
        key=lambda x: _iso(x.get("updated_time")) or datetime(1970,1,1,tzinfo=timezone.utc),
        reverse=True
    )

    for c in convs_sorted[:25]:
        cid = c.get("id")
        if not cid:
            continue

        try:
            msgs = graph.list_messages(cid, limit=probe_messages, max_pages=1)
        except Exception:
            continue

        for m in msgs:
            frm = (m.get("from") or {}).get("id")
            to = (m.get("to") or {}).get("id")
            if str(frm) == str(peer_id) or str(to) == str(peer_id):
                peer = m.get("from") if str(frm) == str(peer_id) else m.get("to")
                return {
                    "conversation_ext_id": cid,
                    "peer_username": _participant_username(peer or {}),
                }

    return None


def resolve_conversation_ext_id(graph, ig_user_id: str, peer_id: str, search_limit_conversations=50, probe_messages=5):
    resolved = resolve_conversation_identity(
        graph,
        ig_user_id,
        peer_id,
        search_limit_conversations=search_limit_conversations,
        probe_messages=probe_messages,
    )
    return resolved.get("conversation_ext_id") if resolved else None
