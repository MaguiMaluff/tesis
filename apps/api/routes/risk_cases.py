from flask import Blueprint, jsonify, g

from ..auth_middleware import token_required
from ..database import db
from ..models import RiskCase
from ..services import load_user_bundle, serialize_risk_case, serialize_risk_case_detail

risk_bp = Blueprint('risk', __name__)


@risk_bp.get('/risk-cases')
@token_required
def list_alerts():
    bundle = load_user_bundle(g.user_id)
    payload = [serialize_risk_case(case, bundle) for case in bundle['risk_cases']]
    payload.sort(key=lambda item: item.get('opened_at') or '', reverse=True)
    return jsonify(payload)


@risk_bp.get('/risk-cases/<case_id>')
@token_required
def get_case_detail(case_id):
    bundle = load_user_bundle(g.user_id)
    risk_case = None
    for item in bundle['risk_cases']:
        if item.id == case_id:
            risk_case = item
            break

    if not risk_case:
        return jsonify({'error': 'Risk case not found'}), 404

    return jsonify(serialize_risk_case_detail(risk_case, bundle))


@risk_bp.patch('/risk-cases/<case_id>/close')
@token_required
def close_case(case_id):
    risk_case = db.session.get(RiskCase, case_id)
    if not risk_case:
        return jsonify({'error': 'Risk case not found'}), 404
    risk_case.status = 'closed'
    db.session.commit()
    return jsonify({'id': risk_case.id, 'status': risk_case.status})