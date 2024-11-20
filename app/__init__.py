from flask import Flask

from gpio_test import button_pressed_callback

def create_app():
    app = Flask(__name__)
    with app.app_context():
        button_pressed_callback(8)
    # Register API routes
    from . import api
    print(__name__)
    app.register_blueprint(api.bp)

    return app
