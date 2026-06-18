from flask import Blueprint, jsonify, g, request

from ..auth_middleware import token_required
from ..database import db
from ..models import IgAccount
from ..service_modules.bundles import load_user_bundle
from ..service_modules.serializers import (
    serialize_conversation,
    serialize_conversation_detail,
    serialize_message_event,
)


conversations_bp = Blueprint('conversations', __name__)


def _filter_conversations(payload):
    query = request.args.get('search', '').strip().lower()
    if query:
        payload = [
            item for item in payload
            if any(
                query in str(value).lower()
                for value in (
                    item.get('peer_id'),
                    item.get('child_name'),
                    item.get('account_username'),
                    item.get('status'),
                    item.get('max_stage_label'),
                )
                if value is not None
            )
        ]

    reverse = request.args.get('order', 'recent') != 'oldest'
    payload.sort(key=lambda item: item.get('last_message_at') or item.get('created_at') or '', reverse=reverse)
    return payload


@conversations_bp.get('/conversations')
@token_required
def list_conversations():
    bundle = load_user_bundle(g.user_id)
    payload = [serialize_conversation(conversation, bundle) for conversation in bundle['conversations']]
    return jsonify(_filter_conversations(payload))


@conversations_bp.get('/conversations/<conversation_id>')
@token_required
def get_conversation(conversation_id):
    bundle = load_user_bundle(g.user_id)
    conversation = bundle['conversation_by_id'].get(conversation_id)
    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404
    return jsonify(serialize_conversation_detail(conversation, bundle))


@conversations_bp.get('/conversations/<conversation_id>/events')
@token_required
def get_conversation_events(conversation_id):
    bundle = load_user_bundle(g.user_id)
    conversation = bundle['conversation_by_id'].get(conversation_id)
    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404
    events = bundle['events_by_conversation'].get(conversation_id, [])
    return jsonify([serialize_message_event(event) for event in events])


@conversations_bp.get('/conversations/<account_id>/conversations')
@token_required
def list_account_conversations(account_id):
    account = db.session.get(IgAccount, account_id)
    if not account:
        return jsonify({'error': 'Account not found'}), 404
    child = account.child
    if not child or child.parent_id != g.user_id:
        return jsonify({'error': 'No autorizado'}), 403
    bundle = load_user_bundle(g.user_id)
    payload = [
        serialize_conversation(conversation, bundle)
        for conversation in bundle['conversations_by_account'].get(account_id, [])
    ]
    return jsonify(_filter_conversations(payload))
