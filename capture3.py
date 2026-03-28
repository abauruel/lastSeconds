import os
from flask import Flask, jsonify
from gpio_config import setup_gpio, cleanup_gpio
from ffmpeg_manager import FFMpegManager
from gpio_button import register_button_callback
from routes import create_app
# from temperature_monitor import start_temperature_monitoring, stop_temperature_monitoring  # Desativado
# from led_ws281x_new import blink_n_times, cleanup, start_blinking

from dotenv import load_dotenv
load_dotenv()

# Configurações
BASE_DIR = "/media/pi/usb64gb/bts"
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


os.makedirs("/tmp/buffers/video0", exist_ok=True)
os.makedirs("/tmp/buffers/video2", exist_ok=True)

# Inicializa o Flask e o GPIO
GPIO = setup_gpio()

# Inicializa o gerenciador de ffmpeg
ffmpeg_manager = FFMpegManager(BUFFER_DIR_VIDEO0, BUFFER_DIR_VIDEO2, FINAL_DIR, STREAM_DIR)

# Inicializa o Flask ANTES de iniciar FFmpeg
app = create_app(ffmpeg_manager)

# IMPORTANTE: Só inicia FFmpeg e watchdog quando usado com gunicorn preload
# ou quando rodado diretamente (não em múltiplos workers)

# Configuração das URLs RTSP das câmeras via variáveis de ambiente
CAMERA_0_RTSP_URL = os.environ.get('CAMERA_0_RTSP_URL', 'rtsp://')
CAMERA_1_RTSP_URL = os.environ.get('CAMERA_1_RTSP_URL', 'rtsp://')

if os.environ.get('SERVER_SOFTWARE', '').startswith('gunicorn'):
    # Rodando em gunicorn - só inicia no master process com preload
    import sys
    if '--preload' in sys.argv or 'gunicorn_config.py' in ' '.join(sys.argv):
        print("🎥 Inicializando FFmpeg no master process...")
        ffmpeg_manager.start_ffmpeg_processes(0, "rtsp", CAMERA_0_RTSP_URL) 
        ffmpeg_manager.start_ffmpeg_processes(1, "rtsp", CAMERA_1_RTSP_URL)
        # ffmpeg_manager.start_ffmpeg_processes(0,"rtsp", "rtsp://admin:123456@192.168.1.188/stream0")
        # ffmpeg_manager.start_ffmpeg_processes(1,"rtsp", "rtsp://admin:123456@192.168.1.188/stream1")
        # start_temperature_monitoring(BASE_DIR)  # Desativado
else:
    # Rodando diretamente (python capture3.py)
    print("🎥 Inicializando FFmpeg em modo standalone...")
    ffmpeg_manager.start_ffmpeg_processes(0, "rtsp", CAMERA_0_RTSP_URL)
    ffmpeg_manager.start_ffmpeg_processes(1, "rtsp", CAMERA_1_RTSP_URL)
    # start_temperature_monitoring(BASE_DIR)  # Desativado

# Função principal
def main():
    # Iniciar o monitoramento de temperatura
    
    
    try:
        print("Servidor Flask rodando...")
        app.run(host="0.0.0.0", port=5000)
    except KeyboardInterrupt:
        print("Encerrando aplicação...")
        # stop_temperature_monitoring()  # Parar o monitoramento de temperatura - Desativado
        ffmpeg_manager.stop_ffmpeg_processes()
        cleanup_gpio()

if __name__ == "__main__":
    main()
