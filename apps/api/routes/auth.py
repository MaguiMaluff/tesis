from flask import Blueprint, jsonify, request, g
from werkzeug.security import check_password_hash, generate_password_hash

from ..auth_middleware import create_access_token, token_required
from ..database import db
from ..models import User
from ..service_modules.serializers import serialize_user
from ..service_modules.utils import utcnow

auth_bp = Blueprint('auth', __name__)


@auth_bp.post('/login')
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get('email', '')).strip().lower()
    password = str(data.get('password', ''))

    if not email or not password:
        return jsonify({'error': 'Email y password requeridos'}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Credenciales inválidas'}), 401

    token = create_access_token(user)
    return jsonify({'access_token': token, 'refresh_token': token, 'user': serialize_user(user)})
    


@auth_bp.post('/signup')
def signup():
    
    data = request.get_json(silent=True) or {}
    email = str(data.get('email', '')).strip().lower()
    password = str(data.get('password', ''))
    full_name = str(data.get('full_name', '')).strip()

    if not email or not password or not full_name:
        return jsonify({'error': 'Email, password y full_name son requeridos'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'El email ya está registrado'}), 409

    user = User(email=email, full_name=full_name, created_at=utcnow())
    user.password_hash = generate_password_hash(password)
    db.session.add(user)
    db.session.commit()

    token = create_access_token(user)
    return jsonify({'message': 'Usuario creado', 'access_token': token, 'refresh_token': token, 'user': serialize_user(user)}), 201


@auth_bp.post('/logout')
def logout():
    return jsonify({'message': 'Sesión cerrada'})


@auth_bp.get('/me')
@token_required
def get_profile():
    user = getattr(g, 'current_user', None)
    if not user:
        return jsonify({'error': 'No autenticado'}), 401
    return jsonify(serialize_user(user))
