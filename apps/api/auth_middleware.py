from functools import wraps
from datetime import timedelta

import jwt
from flask import current_app, g, jsonify, request

from .database import db
from .models import User
from .service_modules.utils import utcnow


def create_access_token(user: User) -> str:
    payload = {
        "sub": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "iat": utcnow(),
        "exp": utcnow().replace(microsecond=0) + timedelta(hours=int(current_app.config["JWT_EXPIRATION_HOURS"])),
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def token_required(view):
    @wraps(view)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.split(" ", 1)[1] if auth_header.startswith("Bearer ") else None

        if not token:
            return jsonify({"error": "Token de acceso faltante"}), 401

        try:
            decoded = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
            user_id = decoded.get("sub")
            if not user_id:
                return jsonify({"error": "Token inválido o expirado"}), 401

            user = db.session.get(User, user_id)
            if not user:
                return jsonify({"error": "Token inválido o expirado"}), 401

            g.user_id = user.id
            g.current_user = user
        except Exception:
            return jsonify({"error": "Token inválido o expirado"}), 401

        return view(*args, **kwargs)

    return decorated
