from flask import Flask
from routes.ffmpeg_routes import init_ffmpeg_routes
from routes.status_routes import init_status_routes
from database import Base, engine


# import led_ws281x_new  # LED removido do projeto

def init_db():
    """Initialize the database by creating all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)

def create_app(ffmpeg_manager):
    """Cria e configura o aplicativo Flask."""
    app = Flask(__name__)
    
    # Initialize the database
    init_db()

    # Inicializa e registra os blueprints
    app.register_blueprint(init_ffmpeg_routes(ffmpeg_manager))
    app.register_blueprint(init_status_routes())
    
    # TODO: LED manager será inicializado apenas no worker principal
    # Comentado temporariamente para evitar conflitos entre workers


    return app