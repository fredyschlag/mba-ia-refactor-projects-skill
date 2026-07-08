from flask import Blueprint

from controllers import main_controller

main_bp = Blueprint("main", __name__)

main_bp.add_url_rule("/", "index", main_controller.index, methods=["GET"])
main_bp.add_url_rule("/health", "health_check", main_controller.health_check, methods=["GET"])
