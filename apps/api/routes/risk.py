from flask import Blueprint, jsonify, request, g
from ..app import SB
from ..auth_middleware import token_required

risk_bp = Blueprint('risk', __name__)

@risk_bp.get('/')
@token_required
def list_alerts():
    """Lista todos los casos de riesgo detectados."""
    # Filtramos por parent_id a través de la cadena de relaciones
    res = SB.table('risk_cases') \
        .select('*, conversations(peer_id, ig_accounts(children(display_name)))') \
        .eq('conversations.ig_accounts.children.parent_id', g.user_id) \
        .order('opened_at', desc=True) \
        .execute()
    return jsonify(res.data)

@risk_bp.get('/<case_id>')
def get_case_detail(case_id):
    """Obtiene el detalle de un caso y sus snapshots de análisis IA."""
    case = SB.table('risk_cases').select('*').eq('id', case_id).single().execute()
    snapshots = SB.table('case_snapshots') \
        .select('*') \
        .eq('risk_case_id', case_id) \
        .order('created_at', desc=True) \
        .execute()
        
    return jsonify({
        "case": case.data,
        "history": snapshots.data
    })

@risk_bp.patch('/<case_id>/close')
def close_case(case_id):
    """Cierra un caso de riesgo (marcado como revisado)."""
    res = SB.table('risk_cases') \
        .update({"status": "closed"}) \
        .eq('id', case_id) \
        .execute()
    return jsonify(res.data)