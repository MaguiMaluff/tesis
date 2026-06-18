from flask import Blueprint, jsonify, g

from ..auth_middleware import token_required
from ..service_modules.dashboard_service import get_general_stats_for_user

stats_bp = Blueprint('stats', __name__)


@stats_bp.get('/')
@token_required
def get_general_stats():
    return jsonify(get_general_stats_for_user(g.user_id))
