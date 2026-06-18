from flask import Blueprint, jsonify, g

from ..auth_middleware import token_required
from ..service_modules.dashboard_service import dashboard_summary_for_user


dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.get('/dashboard/summary')
@token_required
def dashboard_summary():
    return jsonify(dashboard_summary_for_user(g.user_id))
