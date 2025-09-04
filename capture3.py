import os
import threading
from flask import Flask, jsonify
from gpio_config import setup_gpio, cleanup_gpio
from ffmpeg_manager import FFMpegManager
from gpio_button import register_button_callback
from routes import create_app
from send_pending_files import scheduler_send, init_db

# Configurações
BASE_DIR = "./recordings"
BUFFER_DIR = os.path.join(BASE_DIR, "buffers")
FINAL_DIR = os.path.join(BASE_DIR, "recordings")
STREAM_DIR = os.path.join(BASE_DIR, "streams")
BUFFER_DIR_VIDEO0 = os.path.join(BUFFER_DIR, "video0")
BUFFER_DIR_VIDEO2 = os.path.join(BUFFER_DIR, "video2")

# Cria os diretórios, se não existirem
os.makedirs(BUFFER_DIR_VIDEO0, exist_ok=True)
os.makedirs(BUFFER_DIR_VIDEO2, exist_ok=True)
os.makedirs(FINAL_DIR, exist_ok=True)
os.makedirs(STREAM_DIR, exist_ok=True)

# Inicializa o Flask e o GPIO
GPIO = setup_gpio()


# Inicializa o gerenciador de ffmpeg
ffmpeg_manager = FFMpegManager(BUFFER_DIR_VIDEO0, BUFFER_DIR_VIDEO2, FINAL_DIR, STREAM_DIR)
ffmpeg_manager.start_ffmpeg_processes()
# Inicializa o Flask
app = create_app(ffmpeg_manager)

# Função principal
def main():
    # Inicializa banco e tabela se não existirem
    init_db()
    # Inicia o agendador de envio em thread separada
    threading.Thread(target=scheduler_send, daemon=True).start()
    try:
        print("Servidor Flask rodando...")
        app.run(host="0.0.0.0", port=5000)
    except KeyboardInterrupt:
        ffmpeg_manager.stop_ffmpeg_processes()
        cleanup_gpio()

if __name__ == "__main__":
    main()