from flask import Flask
from routes.ffmpeg_routes import init_ffmpeg_routes
from routes.status_routes import init_status_routes

def create_app(ffmpeg_manager):
    """Cria e configura o aplicativo Flask."""
    app = Flask(__name__)

    # Inicializa e registra os blueprints
    app.register_blueprint(init_ffmpeg_routes(ffmpeg_manager))
    app.register_blueprint(init_status_routes())

    return app