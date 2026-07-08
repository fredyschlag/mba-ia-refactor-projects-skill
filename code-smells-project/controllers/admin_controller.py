from flask import jsonify

from models import pedido as pedido_model
from models import produto as produto_model
from models import usuario as usuario_model


def reset_database():
    pedido_model.deletar_todos()
    produto_model.deletar_todos()
    usuario_model.deletar_todos()
    return jsonify({"mensagem": "Banco de dados resetado", "sucesso": True}), 200
