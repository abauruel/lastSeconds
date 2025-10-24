import os
from flask import Flask, jsonify
from gpio_config import setup_gpio, cleanup_gpio
from ffmpeg_manager import FFMpegManager
from gpio_button import register_button_callback
from routes import create_app
from temperature_monitor import start_temperature_monitoring, stop_temperature_monitoring
# from led_ws281x_new import blink_n_times, cleanup, start_blinking

import led_ws281x_new

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

led_ws281x_new.cleanup()




start_temperature_monitoring(BASE_DIR)

# Inicializa o Flask
app = create_app(ffmpeg_manager)

# Função principal
def main():
    # Iniciar o monitoramento de temperatura
    
    
    try:
        print("Servidor Flask rodando...")
        app.run(host="0.0.0.0", port=5000)
    except KeyboardInterrupt:
        print("Encerrando aplicação...")
        stop_temperature_monitoring()  # Parar o monitoramento de temperatura
        ffmpeg_manager.stop_ffmpeg_processes()
        cleanup_gpio()

if __name__ == "__main__":
    main()