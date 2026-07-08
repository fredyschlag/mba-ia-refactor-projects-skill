from flask import jsonify
from werkzeug.exceptions import HTTPException

from database import db


def register_error_handlers(app):
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        db.session.rollback()
        return jsonify({'error': error.description or error.name}), error.code

    @app.errorhandler(Exception)
    def handle_exception(error):
        app.logger.exception('Erro não tratado')
        db.session.rollback()
        return jsonify({'error': 'Erro interno'}), 500
