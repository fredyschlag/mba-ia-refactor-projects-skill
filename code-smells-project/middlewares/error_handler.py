from flask import jsonify


def register(app):
    @app.errorhandler(ValueError)
    def handle_value_error(e):
        return jsonify({"erro": str(e), "sucesso": False}), 400

    @app.errorhandler(404)
    def handle_not_found(e):
        return jsonify({"erro": "Recurso não encontrado", "sucesso": False}), 404

    @app.errorhandler(Exception)
    def handle_unexpected_error(e):
        app.logger.exception("Erro não tratado")
        return jsonify({"erro": "Erro interno", "sucesso": False}), 500
