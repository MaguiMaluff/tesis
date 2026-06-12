from flask import Blueprint, jsonify, g
from ..app import SB  # Importamos el cliente Supabase de app.py
from ..auth_middleware import token_required

stats_bp = Blueprint('stats', __name__)

@stats_bp.get('/')
@token_required
def get_general_stats():
    """Resumen de métricas para el dashboard."""
    # Primero obtenemos los IDs de los hijos de este tutor
    children = SB.table('children').select('id').eq('parent_id', g.user_id).execute()
    child_ids = [c['id'] for c in children.data]

    # Conteo de cuentas de IG monitoreadas del tutor
    accounts = SB.table('ig_accounts').select('id', count='exact').in_('child_id', child_ids).execute()
    
    # Conteo de casos abiertos (relacionados a sus hijos)
    cases = SB.table('risk_cases').select('id', count='exact').eq('status', 'open').execute() 
    
    return jsonify({
        "active_monitored_accounts": accounts.count or 0,
        "open_risk_cases": cases.count or 0,
        "system_health": "ok"
    })