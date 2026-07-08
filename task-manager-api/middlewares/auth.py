import time
from functools import wraps

import jwt
from flask import current_app, jsonify, request

ALGORITHM = 'HS256'
TOKEN_TTL_SECONDS = 24 * 60 * 60


def generate_token(user):
    payload = {
        'user_id': user.id,
        'role': user.role,
        'exp': int(time.time()) + TOKEN_TTL_SECONDS,
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm=ALGORITHM)


def _extract_token():
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[len('Bearer '):]
    return auth_header or None


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = _extract_token()
        if not token:
            return jsonify({'error': 'Não autenticado'}), 401
        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=[ALGORITHM])
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token inválido ou expirado'}), 401
        request.current_user_id = payload['user_id']
        request.current_user_role = payload['role']
        return func(*args, **kwargs)
    return wrapper


def admin_required(func):
    @login_required
    @wraps(func)
    def wrapper(*args, **kwargs):
        if request.current_user_role != 'admin':
            return jsonify({'error': 'Acesso negado'}), 403
        return func(*args, **kwargs)
    return wrapper
