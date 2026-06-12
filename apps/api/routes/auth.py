from flask import Blueprint, jsonify, request, g
from ..app import SB
from ..auth_middleware import token_required

auth_bp = Blueprint('auth', __name__)

@auth_bp.post('/login')
def login():
    """Inicia sesión y retorna el JWT para el frontend."""
    data = request.json
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({"error": "Email y password requeridos"}), 400
    
    try:
        res = SB.auth.sign_in_with_password({
            "email": data['email'], 
            "password": data['password']
        })
        
        return jsonify({
            "access_token": res.session.access_token,
            "refresh_token": res.session.refresh_token,
            "user": {
                "id": res.user.id,
                "email": res.user.email
            }
        })
    except Exception as e:
        return jsonify({"error": "Credenciales inválidas"}), 401

@auth_bp.post('/signup')
def signup():
    """Registra un nuevo tutor y lo sincroniza con la tabla app_users."""
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    try:
        # 1. Registro en Supabase Auth
        res = SB.auth.sign_up({"email": email, "password": password})
        
        # 2. Sincronización con tabla pública app_users (usando service role)
        if res.user:
            SB.table('app_users').upsert({
                "id": res.user.id,
                "email": email,
                "full_name": data.get('full_name', '')
            }).execute()

        return jsonify({"message": "Usuario creado", "user_id": res.user.id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@auth_bp.get('/me')
@token_required
def get_profile():
    """Retorna el perfil del usuario autenticado."""
    res = SB.table('app_users').select('*').eq('id', g.user_id).single().execute()
    return jsonify(res.data)