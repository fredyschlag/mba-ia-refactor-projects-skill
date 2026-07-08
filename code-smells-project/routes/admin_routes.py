from flask import Blueprint

from controllers import admin_controller
from middlewares.auth import admin_required

admin_bp = Blueprint("admin", __name__)

admin_bp.add_url_rule(
    "/admin/reset-db", "reset_database", admin_required(admin_controller.reset_database), methods=["POST"]
)
