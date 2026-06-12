from functools import wraps
from flask import request, jsonify, g

def token_required(f):
    """Middleware para validar el JWT de Supabase."""
    @wraps(f)
    def decorated(*args, **kwargs):
        from .app import SB 
        
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(" ")[1]

        if not token:
            return jsonify({'error': 'Token de acceso faltante'}), 401

        try:
            # Valido el token directamente con Supabase
            res = SB.auth.get_user(token)
            if not res or not res.user:
                return jsonify({'error': 'Token inválido o expirado'}), 401
            
            # Guardo el ID del usuario autenticado en el contexto global de Flask (g)
            g.user_id = res.user.id
        except Exception as e:
            return jsonify({'error': 'Error de autenticación', 'details': str(e)}), 401

        return f(*args, **kwargs)
    return decorated