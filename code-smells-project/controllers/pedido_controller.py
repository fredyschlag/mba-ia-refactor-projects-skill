from flask import current_app, g, jsonify, request

from models import pedido as pedido_model


def criar_pedido():
    dados = request.get_json() or {}
    usuario_id = dados.get("usuario_id")
    itens = dados.get("itens", [])

    if not usuario_id:
        return jsonify({"erro": "Usuario ID é obrigatório"}), 400
    if g.usuario_tipo != "admin" and g.usuario_id != usuario_id:
        return jsonify({"erro": "Não é possível criar pedido para outro usuário", "sucesso": False}), 403

    resultado = pedido_model.criar(usuario_id, itens)

    current_app.logger.info(
        "Notificações disparadas para pedido %s (usuario %s): email, sms, push",
        resultado["pedido_id"], usuario_id,
    )

    return jsonify({
        "dados": resultado,
        "sucesso": True,
        "mensagem": "Pedido criado com sucesso",
    }), 201


def listar_pedidos_usuario(usuario_id):
    if g.usuario_tipo != "admin" and g.usuario_id != usuario_id:
        return jsonify({"erro": "Acesso negado", "sucesso": False}), 403

    pedidos = pedido_model.listar_por_usuario(usuario_id)
    return jsonify({"dados": pedidos, "sucesso": True}), 200


def listar_todos_pedidos():
    pedidos = pedido_model.listar_todos()
    return jsonify({"dados": pedidos, "sucesso": True}), 200


def atualizar_status_pedido(pedido_id):
    dados = request.get_json() or {}
    novo_status = dados.get("status", "")

    pedido_model.atualizar_status(pedido_id, novo_status)

    current_app.logger.info("Notificação: pedido %s mudou para status '%s'", pedido_id, novo_status)

    return jsonify({"sucesso": True, "mensagem": "Status atualizado"}), 200


def relatorio_vendas():
    relatorio = pedido_model.relatorio_vendas()
    return jsonify({"dados": relatorio, "sucesso": True}), 200
