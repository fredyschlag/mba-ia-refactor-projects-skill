from flask import Blueprint

from controllers import user_controller
from middlewares.auth import admin_required, login_required

user_bp = Blueprint('users', __name__)

user_bp.add_url_rule('/users', view_func=login_required(user_controller.list_users), methods=['GET'])
user_bp.add_url_rule('/users/<int:user_id>', view_func=login_required(user_controller.get_user), methods=['GET'])
user_bp.add_url_rule('/users', view_func=user_controller.create_user, methods=['POST'])
user_bp.add_url_rule('/users/<int:user_id>', view_func=admin_required(user_controller.update_user), methods=['PUT'])
user_bp.add_url_rule('/users/<int:user_id>', view_func=admin_required(user_controller.delete_user), methods=['DELETE'])
user_bp.add_url_rule(
    '/users/<int:user_id>/tasks', view_func=login_required(user_controller.get_user_tasks), methods=['GET']
)
user_bp.add_url_rule('/login', view_func=user_controller.login, methods=['POST'])
