from __future__ import annotations

from datetime import timedelta

import jwt
from flask import current_app

from ..models import User
from .utils import utcnow


def issue_token(user: User) -> str:
    payload = {
        'sub': user.id,
        'email': user.email,
        'full_name': user.full_name,
        'iat': utcnow(),
        'exp': utcnow() + timedelta(hours=current_app.config['JWT_EXPIRATION_HOURS']),
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
