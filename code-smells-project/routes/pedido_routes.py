from flask import Blueprint

from controllers import pedido_controller
from middlewares.auth import admin_required, login_required

pedido_bp = Blueprint("pedidos", __name__)

pedido_bp.add_url_rule(
    "/pedidos", "criar_pedido", login_required(pedido_controller.criar_pedido), methods=["POST"]
)
pedido_bp.add_url_rule(
    "/pedidos", "listar_todos_pedidos", admin_required(pedido_controller.listar_todos_pedidos), methods=["GET"]
)
pedido_bp.add_url_rule(
    "/pedidos/usuario/<int:usuario_id>",
    "listar_pedidos_usuario",
    login_required(pedido_controller.listar_pedidos_usuario),
    methods=["GET"],
)
pedido_bp.add_url_rule(
    "/pedidos/<int:pedido_id>/status",
    "atualizar_status_pedido",
    admin_required(pedido_controller.atualizar_status_pedido),
    methods=["PUT"],
)
pedido_bp.add_url_rule(
    "/relatorios/vendas", "relatorio_vendas", admin_required(pedido_controller.relatorio_vendas), methods=["GET"]
)
