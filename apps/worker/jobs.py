from __future__ import annotations

from contextlib import contextmanager
from datetime import timedelta

from apps.api.app import app as api_app
from apps.api.database import db
from apps.api.models import Conversation, IgAccount, PreprocessRun
from apps.api.services import parse_dt, to_iso, utcnow

from .ig_api import InstagramGraph
from .resolve_conversation import resolve_conversation_ext_id


@contextmanager
def app_context():
    with api_app.app_context():
        yield


def _conversation_payload(conversation: Conversation) -> dict:
    return {
        "id": conversation.id,
        "ig_account_id": conversation.ig_account_id,
        "peer_id": conversation.peer_id,
        "conversation_ext_id": conversation.conversation_ext_id,
        "pending_count": conversation.pending_count,
        "pending_since": to_iso(conversation.pending_since),
        "last_preprocessed_at": to_iso(conversation.last_preprocessed_at),
        "processing_lock_until": to_iso(conversation.processing_lock_until),
        "processing_lock_by": conversation.processing_lock_by,
        "status": conversation.status,
    }


def claim_conversation_lock(conversation_id: str, lock_by: str, ttl_seconds: int = 120) -> bool:
    with app_context():
        conversation = db.session.get(Conversation, conversation_id)
        if not conversation:
            return False

        now = utcnow()
        if conversation.processing_lock_until and conversation.processing_lock_until > now:
            return False

        conversation.processing_lock_until = now + timedelta(seconds=ttl_seconds)
        conversation.processing_lock_by = lock_by
        db.session.commit()
        return True


def release_conversation_lock(conversation_id: str, lock_by: str):
    with app_context():
        conversation = db.session.get(Conversation, conversation_id)
        if not conversation:
            return
        if conversation.processing_lock_by and conversation.processing_lock_by != lock_by:
            return

        conversation.processing_lock_until = None
        conversation.processing_lock_by = None
        db.session.commit()


def get_ig_account_for_conversation(conversation_id: str) -> dict:
    with app_context():
        conversation = db.session.get(Conversation, conversation_id)
        if not conversation:
            raise RuntimeError(f"Conversation not found: {conversation_id}")

        if not conversation.ig_account_id:
            raise RuntimeError(f"Conversation {conversation_id} has null ig_account_id")

        ig_account = db.session.get(IgAccount, conversation.ig_account_id)
        if not ig_account:
            raise RuntimeError(f"ig_account not found: {conversation.ig_account_id}")

        return {
            "conversation": _conversation_payload(conversation),
            "ig_account": {
                "id": ig_account.id,
                "ig_user_id": ig_account.ig_user_id,
                "access_token": ig_account.access_token,
                "status": ig_account.status,
                "webhook_enabled": ig_account.webhook_enabled,
            },
        }


def build_graph_for_conversation(conversation_id: str, api_version: str) -> tuple[InstagramGraph, str]:
    credentials = get_ig_account_for_conversation(conversation_id)
    ig_account = credentials["ig_account"]

    access_token = ig_account.get("access_token")
    if not access_token:
        raise RuntimeError(f"ig_account {ig_account['id']} has no access_token")

    graph = InstagramGraph(api_version, access_token)
    return graph, str(ig_account.get("ig_user_id") or "")


def is_synthetic_conversation_ext_id(conversation_ext_id: str | None, conversation_id: str | None = None) -> bool:
    if not conversation_ext_id:
        return False
    if conversation_id and conversation_ext_id.startswith(f"{conversation_id}:"):
        return True
    if ":" in conversation_ext_id:
        left, right = conversation_ext_id.split(":", 1)
        if len(left) == 36 and len(right) > 0:
            return True
    return False


def _build_fetch_plan(conv_row: dict, ig_user_id_ext: str | None, conversation_ext_id: str | None, window_start, window_end):
    return {
        "source": "instagram",
        "api_host": "graph.instagram.com",
        "api_version": "env:API_VERSION",
        "ig_account_id": conv_row.get("ig_account_id"),
        "ig_user_id": ig_user_id_ext,
        "conversation_ext_id": conversation_ext_id,
        "window_start": to_iso(window_start),
        "window_end": to_iso(window_end),
        "strategy": "fetch_by_conversation_then_filter_by_time",
        "fields": "id,from,to,message,created_time",
    }


def _insert_preprocess_run(conv_id: str, window_start, window_end, trigger: str, status: str, message_count: int, fetch_plan: dict, error: str | None = None):
    run = PreprocessRun(
        conversation_id=conv_id,
        window_start=window_start,
        window_end=window_end,
        trigger=trigger,
        status=status,
        message_count=message_count,
        fetch_plan=fetch_plan,
        error=error,
    )
    db.session.add(run)
    db.session.commit()
    return run


def preprocess_conversation(api_version: str, conv_row: dict, trigger: str):
    conv_id = conv_row["id"]
    pending_count = int(conv_row.get("pending_count") or 0)

    if pending_count <= 0:
        return

    lock_by = f"worker:{trigger}"
    if not claim_conversation_lock(conv_id, lock_by=lock_by, ttl_seconds=120):
        return

    try:
        with app_context():
            conversation = db.session.get(Conversation, conv_id)
            if not conversation:
                return

            pending_count = int(conversation.pending_count or 0)
            if pending_count <= 0:
                return

            ig_account = db.session.get(IgAccount, conversation.ig_account_id)
            if not ig_account:
                raise RuntimeError(f"ig_account not found: {conversation.ig_account_id}")

            ig_user_id_ext = ig_account.ig_user_id
            access_token = ig_account.access_token
            if not access_token:
                raise RuntimeError(f"ig_account {ig_account.id} has no access_token")

            graph = InstagramGraph(api_version, access_token)
            window_start = parse_dt(conversation.pending_since) or parse_dt(conversation.last_preprocessed_at) or utcnow()
            window_end = utcnow()

            if not ig_user_id_ext:
                fetch_plan = _build_fetch_plan(_conversation_payload(conversation), None, None, window_start, window_end)
                fetch_plan["notes"] = "Skipped because ig_user_id (external) is missing for ig_account."
                _insert_preprocess_run(
                    conv_id,
                    window_start,
                    window_end,
                    trigger,
                    status="skipped",
                    message_count=pending_count,
                    fetch_plan=fetch_plan,
                    error="ig_user_id is null on ig_accounts; cannot resolve conversation_ext_id",
                )
                return

            conversation_ext_id = conversation.conversation_ext_id
            if is_synthetic_conversation_ext_id(conversation_ext_id, conversation.ig_account_id):
                conversation_ext_id = None
            if not conversation_ext_id:
                resolved = resolve_conversation_ext_id(graph, conversation.ig_account_id.ig_user_id, conversation.peer_id)
                if resolved:
                    conversation.conversation_ext_id = resolved
                    conversation_ext_id = resolved
                    db.session.commit()

            if not conversation_ext_id:
                fetch_plan = _build_fetch_plan(_conversation_payload(conversation), ig_user_id_ext, None, window_start, window_end)
                fetch_plan["notes"] = "Skipped because conversation_ext_id could not be resolved yet."
                _insert_preprocess_run(
                    conv_id,
                    window_start,
                    window_end,
                    trigger,
                    status="skipped",
                    message_count=pending_count,
                    fetch_plan=fetch_plan,
                    error="conversation_ext_id is null; cannot fetch messages",
                )
                return

            fetch_plan = _build_fetch_plan(_conversation_payload(conversation), ig_user_id_ext, conversation_ext_id, window_start, window_end)
            fetch_plan["notes"] = "Transcript will be reconstructed at AI-send time. No message text stored in DB."

            _insert_preprocess_run(
                conv_id,
                window_start,
                window_end,
                trigger,
                status="ready_for_ai",
                message_count=pending_count,
                fetch_plan=fetch_plan,
            )

            conversation.pending_count = 0
            conversation.pending_since = None
            conversation.last_preprocessed_at = window_end
            db.session.commit()

    finally:
        release_conversation_lock(conv_id, lock_by=lock_by)


def fetch_pending_conversations(min_pending: int):
    with app_context():
        rows = (
            Conversation.query.filter(Conversation.pending_count >= min_pending)
            .filter(Conversation.status == "active")
            .order_by(Conversation.pending_since.asc(), Conversation.last_message_at.asc())
            .all()
        )
        return [_conversation_payload(row) for row in rows]


def fetch_any_pending_conversations():
    with app_context():
        rows = (
            Conversation.query.filter(Conversation.pending_count > 0)
            .filter(Conversation.status == "active")
            .order_by(Conversation.pending_since.asc(), Conversation.last_message_at.asc())
            .all()
        )
        return [_conversation_payload(row) for row in rows]