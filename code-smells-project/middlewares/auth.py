from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import g, jsonify, request

from config.settings import JWT_EXPIRATION_HOURS, SECRET_KEY


def gerar_token(usuario):
    payload = {
        "usuario_id": usuario["id"],
        "tipo": usuario["tipo"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def _extrair_payload():
    cabecalho = request.headers.get("Authorization", "")
    if not cabecalho.startswith("Bearer "):
        return None
    token = cabecalho.removeprefix("Bearer ")
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return None


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        payload = _extrair_payload()
        if payload is None:
            return jsonify({"erro": "Não autenticado", "sucesso": False}), 401
        g.usuario_id = payload["usuario_id"]
        g.usuario_tipo = payload["tipo"]
        return func(*args, **kwargs)

    return wrapper


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        payload = _extrair_payload()
        if payload is None:
            return jsonify({"erro": "Não autenticado", "sucesso": False}), 401
        if payload["tipo"] != "admin":
            return jsonify({"erro": "Acesso restrito a administradores", "sucesso": False}), 403
        g.usuario_id = payload["usuario_id"]
        g.usuario_tipo = payload["tipo"]
        return func(*args, **kwargs)

    return wrapper
