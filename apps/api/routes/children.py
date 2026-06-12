from flask import Blueprint, jsonify, request, g
from ..app import SB
from ..auth_middleware import token_required

children_bp = Blueprint('children', __name__)

@children_bp.get('/')
@token_required
def list_children():
    """Lista todos los hijos del tutor actual."""
    res = SB.table('children').select('*, ig_accounts(id, ig_username, status)').eq('parent_id', g.user_id).execute()
    return jsonify(res.data)

@children_bp.post('/')
@token_required
def add_child():
    """Crea un nuevo perfil de hijo."""
    data = request.json
    if not data or 'display_name' not in data:
        return jsonify({"error": "Missing fields"}), 400
        
    res = SB.table('children').insert({
        "display_name": data['display_name'],
        "parent_id": g.user_id  # Forzamos el ID del usuario autenticado
    }).execute()
    return jsonify(res.data), 201

@children_bp.get('/<child_id>/accounts')
@token_required
def get_child_accounts(child_id):
    """Lista las cuentas de IG de un hijo específico."""
    # Verificamos que el hijo sea del padre
    child = SB.table('children').select('parent_id').eq('id', child_id).single().execute()
    if not child.data or child.data['parent_id'] != g.user_id:
        return jsonify({"error": "No autorizado"}), 403

    res = SB.table('ig_accounts').select('*').eq('child_id', child_id).execute()
    return jsonify(res.data)