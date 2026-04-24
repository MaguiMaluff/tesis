from __future__ import annotations
from datetime import datetime, timezone

def _iso(s: str | None):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None

def resolve_conversation_ext_id(graph, ig_user_id: str, peer_id: str, search_limit_conversations=50, probe_messages=5):
    """
    Try to map peer_id -> conversation_ext_id.
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
                    return c.get("id")

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
                return cid

    return None