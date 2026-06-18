from flask import Blueprint, jsonify, request, g

from ..auth_middleware import token_required
from ..database import db
from ..models import Child, IgAccount
from ..service_modules.bundles import load_user_bundle
from ..service_modules.serializers import serialize_account, serialize_child_card, serialize_child_detail

children_bp = Blueprint('children', __name__)


@children_bp.get('/children')
@token_required
def list_children():
    bundle = load_user_bundle(g.user_id)
    return jsonify([serialize_child_card(child, bundle) for child in bundle['children']])


@children_bp.get('/children/<child_id>')
@token_required
def get_child(child_id):
    bundle = load_user_bundle(g.user_id)
    child = bundle['child_by_id'].get(child_id)
    if not child or child.parent_id != g.user_id:
        return jsonify({'error': 'Child not found'}), 404
    return jsonify(serialize_child_detail(child, bundle))


@children_bp.post('/children')
@token_required
def add_child():
    data = request.get_json(silent=True) or {}
    display_name = str(data.get('display_name', '')).strip()
    ig_user_id = str(data.get('ig_user_id', '')).strip()
    ig_username = str(data.get('ig_username', '')).strip().lstrip('@')
    access_token = str(data.get('access_token', '')).strip()

    if not display_name or not ig_user_id or not ig_username or not access_token:
        return jsonify({'error': 'Missing fields'}), 400

    child = Child(display_name=display_name, parent_id=g.user_id)
    db.session.add(child)
    db.session.flush()

    account = IgAccount(
        child_id=child.id,
        ig_user_id=ig_user_id,
        ig_username=ig_username,
        access_token=access_token,
        webhook_enabled=True,
        status='active',
    )
    db.session.add(account)
    db.session.commit()
    bundle = load_user_bundle(g.user_id)
    return jsonify(serialize_child_detail(child, bundle)), 201


@children_bp.get('/children/<child_id>/accounts')
@token_required
def get_child_accounts(child_id):
    child = db.session.get(Child, child_id)
    if not child or child.parent_id != g.user_id:
        return jsonify({'error': 'No autorizado'}), 403

    accounts = [serialize_account(account) for account in child.ig_accounts]
    return jsonify(accounts)
