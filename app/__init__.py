from flask import Flask

def create_app():
    app = Flask(__name__)
    
    # Register API routes
    from . import api
    print(__name__)
    app.register_blueprint(api.bp)

    return app
