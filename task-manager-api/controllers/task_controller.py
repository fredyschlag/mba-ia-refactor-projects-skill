from flask import current_app, jsonify, request
from sqlalchemy.orm import joinedload

from database import db
from models.category import Category
from models.task import Task
from models.user import User
from utils.helpers import calculate_percentage, parse_date


def list_tasks():
    tasks = Task.query.options(joinedload(Task.user), joinedload(Task.category)).all()
    return jsonify([t.to_dict(include_relations=True) for t in tasks]), 200


def get_task(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({'error': 'Task não encontrada'}), 404
    return jsonify(task.to_dict()), 200


def create_task():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Dados inválidos'}), 400

    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({'error': 'Título é obrigatório'}), 400
    if not Task.validate_title(title):
        return jsonify({
            'error': f'Título deve ter entre {Task.MIN_TITLE_LENGTH} e {Task.MAX_TITLE_LENGTH} caracteres'
        }), 400

    status = data.get('status', 'pending')
    if not Task.validate_status(status):
        return jsonify({'error': 'Status inválido'}), 400

    try:
        priority = int(data.get('priority', Task.DEFAULT_PRIORITY))
    except (TypeError, ValueError):
        return jsonify({'error': 'Prioridade inválida'}), 400
    if not Task.validate_priority(priority):
        return jsonify({
            'error': f'Prioridade deve ser entre {Task.MIN_PRIORITY} e {Task.MAX_PRIORITY}'
        }), 400

    user_id = data.get('user_id')
    if user_id and not db.session.get(User, user_id):
        return jsonify({'error': 'Usuário não encontrado'}), 404

    category_id = data.get('category_id')
    if category_id and not db.session.get(Category, category_id):
        return jsonify({'error': 'Categoria não encontrada'}), 404

    task = Task()
    task.title = title
    task.description = data.get('description', '')
    task.status = status
    task.priority = priority
    task.user_id = user_id
    task.category_id = category_id

    due_date = data.get('due_date')
    if due_date:
        parsed = parse_date(due_date)
        if not parsed:
            return jsonify({'error': 'Formato de data inválido. Use YYYY-MM-DD'}), 400
        task.due_date = parsed

    tags = data.get('tags')
    if tags:
        task.tags = ','.join(tags) if isinstance(tags, list) else tags

    db.session.add(task)
    db.session.commit()
    current_app.logger.info('Task criada: %s - %s', task.id, task.title)
    return jsonify(task.to_dict()), 201


def update_task(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({'error': 'Task não encontrada'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Dados inválidos'}), 400

    if 'title' in data:
        title = (data['title'] or '').strip()
        if not Task.validate_title(title):
            return jsonify({
                'error': f'Título deve ter entre {Task.MIN_TITLE_LENGTH} e {Task.MAX_TITLE_LENGTH} caracteres'
            }), 400
        task.title = title

    if 'description' in data:
        task.description = data['description']

    if 'status' in data:
        if not Task.validate_status(data['status']):
            return jsonify({'error': 'Status inválido'}), 400
        task.status = data['status']

    if 'priority' in data:
        try:
            priority = int(data['priority'])
        except (TypeError, ValueError):
            return jsonify({'error': 'Prioridade inválida'}), 400
        if not Task.validate_priority(priority):
            return jsonify({
                'error': f'Prioridade deve ser entre {Task.MIN_PRIORITY} e {Task.MAX_PRIORITY}'
            }), 400
        task.priority = priority

    if 'user_id' in data:
        if data['user_id'] and not db.session.get(User, data['user_id']):
            return jsonify({'error': 'Usuário não encontrado'}), 404
        task.user_id = data['user_id']

    if 'category_id' in data:
        if data['category_id'] and not db.session.get(Category, data['category_id']):
            return jsonify({'error': 'Categoria não encontrada'}), 404
        task.category_id = data['category_id']

    if 'due_date' in data:
        if data['due_date']:
            parsed = parse_date(data['due_date'])
            if not parsed:
                return jsonify({'error': 'Formato de data inválido'}), 400
            task.due_date = parsed
        else:
            task.due_date = None

    if 'tags' in data:
        tags = data['tags']
        task.tags = ','.join(tags) if isinstance(tags, list) else tags

    db.session.commit()
    current_app.logger.info('Task atualizada: %s', task.id)
    return jsonify(task.to_dict()), 200


def delete_task(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({'error': 'Task não encontrada'}), 404

    db.session.delete(task)
    db.session.commit()
    current_app.logger.info('Task deletada: %s', task_id)
    return jsonify({'message': 'Task deletada com sucesso'}), 200


def search_tasks():
    query = request.args.get('q', '')
    status = request.args.get('status', '')
    priority = request.args.get('priority', '')
    user_id = request.args.get('user_id', '')

    tasks = Task.query

    if query:
        tasks = tasks.filter(
            db.or_(Task.title.like(f'%{query}%'), Task.description.like(f'%{query}%'))
        )
    if status:
        tasks = tasks.filter(Task.status == status)
    if priority:
        tasks = tasks.filter(Task.priority == int(priority))
    if user_id:
        tasks = tasks.filter(Task.user_id == int(user_id))

    return jsonify([t.to_dict() for t in tasks.all()]), 200


def task_stats():
    total = Task.query.count()
    pending = Task.query.filter_by(status='pending').count()
    in_progress = Task.query.filter_by(status='in_progress').count()
    done = Task.query.filter_by(status='done').count()
    cancelled = Task.query.filter_by(status='cancelled').count()
    overdue_count = sum(1 for t in Task.query.all() if t.is_overdue())

    return jsonify({
        'total': total,
        'pending': pending,
        'in_progress': in_progress,
        'done': done,
        'cancelled': cancelled,
        'overdue': overdue_count,
        'completion_rate': calculate_percentage(done, total),
    }), 200
