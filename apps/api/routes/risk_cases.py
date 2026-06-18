from flask import Blueprint, jsonify, g, request

from ..auth_middleware import token_required
from ..database import db
from ..service_modules.bundles import load_user_bundle
from ..service_modules.serializers import serialize_risk_case, serialize_risk_case_detail

risk_bp = Blueprint('risk', __name__)


def _filter_risk_cases(payload):
    query = request.args.get('search', '').strip().lower()
    stage = request.args.get('stage')
    severity = request.args.get('severity')
    status = request.args.get('status')

    if stage not in (None, '', 'all'):
        payload = [item for item in payload if str(item.get('stage')) == str(stage)]
    if severity not in (None, '', 'all'):
        payload = [item for item in payload if item.get('risk_level') == severity]
    if status not in (None, '', 'all'):
        payload = [item for item in payload if item.get('status') == status]
    if query:
        payload = [
            item for item in payload
            if any(
                query in str(value).lower()
                for value in (
                    item.get('reason_safe'),
                    item.get('stage_label'),
                    item.get('peer_username'),
                    item.get('peer_id'),
                    item.get('account_username'),
                    item.get('status'),
                )
                if value is not None
            )
        ]

    reverse = request.args.get('order', 'recent') != 'oldest'
    payload.sort(key=lambda item: item.get('opened_at') or '', reverse=reverse)
    return payload


@risk_bp.get('/risk-cases')
@token_required
def list_alerts():
    bundle = load_user_bundle(g.user_id)
    payload = [serialize_risk_case(case, bundle) for case in bundle['risk_cases']]
    return jsonify(_filter_risk_cases(payload))


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
    bundle = load_user_bundle(g.user_id)
    risk_case = None
    for item in bundle['risk_cases']:
        if item.id == case_id:
            risk_case = item
            break

    if not risk_case:
        return jsonify({'error': 'Risk case not found'}), 404

    risk_case.status = 'closed'
    db.session.commit()
    return jsonify({'id': risk_case.id, 'status': risk_case.status})
