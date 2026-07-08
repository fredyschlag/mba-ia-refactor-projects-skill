from flask import g, jsonify, request

from middlewares.auth import gerar_token
from models import usuario as usuario_model


def listar_usuarios():
    usuarios = usuario_model.listar_todos()
    return jsonify({"dados": usuarios, "sucesso": True}), 200


def buscar_usuario(id):
    if g.usuario_tipo != "admin" and g.usuario_id != id:
        return jsonify({"erro": "Acesso negado", "sucesso": False}), 403

    encontrado = usuario_model.buscar_por_id(id)
    if not encontrado:
        return jsonify({"erro": "Usuário não encontrado"}), 404
    return jsonify({"dados": encontrado, "sucesso": True}), 200


def criar_usuario():
    dados = request.get_json()
    id = usuario_model.criar(dados)
    return jsonify({"dados": {"id": id}, "sucesso": True}), 201


def login():
    dados = request.get_json() or {}
    email = dados.get("email", "")
    senha = dados.get("senha", "")

    usuario_autenticado = usuario_model.autenticar(email, senha)
    if usuario_autenticado:
        token = gerar_token(usuario_autenticado)
        return jsonify({
            "dados": {**usuario_autenticado, "token": token},
            "sucesso": True,
            "mensagem": "Login OK",
        }), 200

    return jsonify({"erro": "Email ou senha inválidos", "sucesso": False}), 401
