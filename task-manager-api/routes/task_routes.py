from flask import Blueprint

from controllers import task_controller
from middlewares.auth import admin_required, login_required

task_bp = Blueprint('tasks', __name__)

task_bp.add_url_rule('/tasks', view_func=login_required(task_controller.list_tasks), methods=['GET'])
task_bp.add_url_rule('/tasks/search', view_func=login_required(task_controller.search_tasks), methods=['GET'])
task_bp.add_url_rule('/tasks/stats', view_func=login_required(task_controller.task_stats), methods=['GET'])
task_bp.add_url_rule('/tasks/<int:task_id>', view_func=login_required(task_controller.get_task), methods=['GET'])
task_bp.add_url_rule('/tasks', view_func=login_required(task_controller.create_task), methods=['POST'])
task_bp.add_url_rule('/tasks/<int:task_id>', view_func=login_required(task_controller.update_task), methods=['PUT'])
task_bp.add_url_rule('/tasks/<int:task_id>', view_func=admin_required(task_controller.delete_task), methods=['DELETE'])
