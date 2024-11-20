from app import create_app
import threading
def start_flask():
    app = create_app()
    app.run(debug=True)

if __name__ == '__main__':
    # flask_thread = threading.Thread(target=start_flask)
    # flask_thread.start()
    app = create_app()
    app.run(debug=True)
    # import button_control