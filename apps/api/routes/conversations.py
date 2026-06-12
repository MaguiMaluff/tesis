from flask import Blueprint, jsonify, g
from ..app import SB
from ..auth_middleware import token_required

conv_bp = Blueprint('conversations', __name__)

@conv_bp.get('/<account_id>/conversations')
@token_required
def list_conversations(account_id):
    """Lista chats de una cuenta de IG, ordenados por actividad reciente."""
    # Verificación de seguridad: ¿Esta cuenta pertenece a un hijo de este padre?
    check = SB.table('ig_accounts') \
        .select('id, children(parent_id)') \
        .eq('id', account_id) \
        .single().execute()
    
    if not check.data or check.data['children']['parent_id'] != g.user_id:
        return jsonify({"error": "No autorizado"}), 403

    res = SB.table('conversations') \
        .select('*') \
        .eq('ig_account_id', account_id) \
        .order('last_message_at', desc=True) \
        .execute()
    return jsonify(res.data)

@conv_bp.get('/conversations/<conv_id>/events')
@token_required
def get_chat_events(conv_id):
    """
    Retorna la línea de tiempo de mensajes de un chat.
    Solo metadatos (sent_at, direction, features).
    """
    # Cambiamos el endpoint dinámicamente si es necesario o usamos rutas absolutas
    res = SB.table('message_events') \
        .select('id, sent_at, direction, features') \
        .eq('conversation_id', conv_id) \
        .order('sent_at', desc=False) \
        .execute()
    return jsonify(res.data)