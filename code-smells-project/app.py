from flask import Flask
from flask_cors import CORS

import database
from config.settings import DEBUG, SECRET_KEY
from middlewares import error_handler
from routes.admin_routes import admin_bp
from routes.main_routes import main_bp
from routes.pedido_routes import pedido_bp
from routes.produto_routes import produto_bp
from routes.usuario_routes import usuario_bp


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["DEBUG"] = DEBUG
    CORS(app)

    database.init_app(app)
    error_handler.register(app)

    app.register_blueprint(main_bp)
    app.register_blueprint(produto_bp)
    app.register_blueprint(usuario_bp)
    app.register_blueprint(pedido_bp)
    app.register_blueprint(admin_bp)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=DEBUG)
