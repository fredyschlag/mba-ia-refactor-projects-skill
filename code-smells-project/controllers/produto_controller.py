from flask import jsonify, request

from models import produto as produto_model


def listar_produtos():
    produtos = produto_model.listar_todos()
    return jsonify({"dados": produtos, "sucesso": True}), 200


def buscar_produto(id):
    encontrado = produto_model.buscar_por_id(id)
    if not encontrado:
        return jsonify({"erro": "Produto não encontrado", "sucesso": False}), 404
    return jsonify({"dados": encontrado, "sucesso": True}), 200


def buscar_produtos():
    termo = request.args.get("q", "")
    categoria = request.args.get("categoria", None)
    preco_min = request.args.get("preco_min", None)
    preco_max = request.args.get("preco_max", None)

    if preco_min:
        preco_min = float(preco_min)
    if preco_max:
        preco_max = float(preco_max)

    resultados = produto_model.buscar(termo, categoria, preco_min, preco_max)
    return jsonify({"dados": resultados, "total": len(resultados), "sucesso": True}), 200


def criar_produto():
    dados = request.get_json()
    id = produto_model.criar(dados)
    return jsonify({"dados": {"id": id}, "sucesso": True, "mensagem": "Produto criado"}), 201


def atualizar_produto(id):
    if not produto_model.buscar_por_id(id):
        return jsonify({"erro": "Produto não encontrado"}), 404
    dados = request.get_json()
    produto_model.atualizar(id, dados)
    return jsonify({"sucesso": True, "mensagem": "Produto atualizado"}), 200


def deletar_produto(id):
    if not produto_model.buscar_por_id(id):
        return jsonify({"erro": "Produto não encontrado"}), 404
    produto_model.deletar(id)
    return jsonify({"sucesso": True, "mensagem": "Produto deletado"}), 200
