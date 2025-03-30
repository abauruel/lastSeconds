import os
import subprocess
from flask import Flask, jsonify
from datetime import datetime

# Configurações
OUTPUT_DIR = "./recordings"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Inicializa o Flask
app = Flask(__name__)

# Processos do ffmpeg
ffmpeg_process_0 = None
ffmpeg_process_1 = None


def start_ffmpeg_processes():
    """Inicia os processos ffmpeg com buffer circular."""
    global ffmpeg_process_0, ffmpeg_process_1

    # Buffer circular para /dev/video0
    ffmpeg_process_0 = subprocess.Popen([
        "ffmpeg", "-f", "v4l2", "-input_format", "h264", "-video_size", "1280x720", "-r", "25", "-i", "/dev/video0",
        "-use_wallclock_as_timestamps", "1", 
        "-c:v", "copy", "-preset", "ultrafast", "-tune", "zerolatency",  "-b:v", "800k", "-maxrate","1M", "-bufsize", "800k", "-an", "-f", "flv", "rtmp://localhost/live/stream1",
        "-c:v", "copy", "-f", "segment", "-segment_time", "1", "-segment_format", "mp4",
        "-reset_timestamps", "1", f"{OUTPUT_DIR}/buffer_video0_%03d.mp4"
    ])

    # Buffer circular para /dev/video2
    ffmpeg_process_1 = subprocess.Popen([
        "ffmpeg", "-f", "v4l2", "-input_format", "h264", "-video_size", "1280x720", "-r", "25", "-i", "/dev/video2",
        "-use_wallclock_as_timestamps", "1", 
        "-c:v", "copy", "-preset", "ultrafast", "-tune", "zerolatency",  "-b:v", "800k", "-maxrate","1M", "-bufsize", "800k", "-an", "-f", "flv", "rtmp://localhost/live/stream2",
        "-c:v", "copy", "-f", "segment", "-segment_time", "1", "-segment_format", "mp4",
        "-reset_timestamps", "1", f"{OUTPUT_DIR}/buffer_video2_%03d.mp4"
    ])

    print("Processos ffmpeg iniciados com buffer circular.")

def combine_segments(segment_files, output_file, temp_file):
    """Combina múltiplos arquivos de segmento em um único arquivo."""
    with open(temp_file, "w") as file_list:
        for segment in segment_files:
            # Adiciona o caminho absoluto para cada segmento
            file_list.write(f"file '{os.path.abspath(segment)}'\n")

    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", temp_file, "-c:v", "copy", "-movflags", "+faststart", output_file
    ])

    os.remove(temp_file)


def record_last_10_seconds():
    """Copia os últimos 10 segundos de stream para um novo arquivo."""
    print("Gravando os últimos 10 segundos de stream...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file_0 = os.path.join(OUTPUT_DIR, f"stream1_{timestamp}.mp4")
    output_file_1 = os.path.join(OUTPUT_DIR, f"stream2_{timestamp}.mp4")

    # Arquivos temporários para listas de segmentos
    temp_file_0 = os.path.join(OUTPUT_DIR, "file_list_video0.txt")
    temp_file_1 = os.path.join(OUTPUT_DIR, "file_list_video2.txt")

    # Identifica os últimos 10 arquivos no buffer circular
    buffer_files_0 = sorted([os.path.join(OUTPUT_DIR, f) for f in os.listdir(OUTPUT_DIR) if f.startswith("buffer_video0_")])[-5:]
    buffer_files_1 = sorted([os.path.join(OUTPUT_DIR, f) for f in os.listdir(OUTPUT_DIR) if f.startswith("buffer_video2_")])[-5:]

    if buffer_files_0:
        combine_segments(buffer_files_0, output_file_0, temp_file_0)
        print(f"Gravação concluída: {output_file_0}")
    else:
        print("Erro: Nenhum arquivo encontrado no buffer para /dev/video0.")

    if buffer_files_1:
        combine_segments(buffer_files_1, output_file_1, temp_file_1)
        print(f"Gravação concluída: {output_file_1}")
    else:
        print("Erro: Nenhum arquivo encontrado no buffer para /dev/video2.")


@app.route('/record', methods=['POST'])
def handle_record():
    """Rota para iniciar a gravação dos últimos 10 segundos."""
    record_last_10_seconds()
    return jsonify({"status": "success", "message": "Gravação iniciada"}), 200


@app.route('/status', methods=['GET'])
def status():
    """Rota para verificar o status do servidor."""
    return jsonify({"status": "running"}), 200


def cleanup():
    """Finaliza os processos do ffmpeg corretamente."""
    print("Finalizando os processos do ffmpeg...")
    global ffmpeg_process_0, ffmpeg_process_1

    if ffmpeg_process_0 and ffmpeg_process_0.poll() is None:
        ffmpeg_process_0.terminate()
        ffmpeg_process_0.wait()

    if ffmpeg_process_1 and ffmpeg_process_1.poll() is None:
        ffmpeg_process_1.terminate()
        ffmpeg_process_1.wait()

    print("Todos os processos do ffmpeg foram finalizados.")


def main():
    try:
        # Inicia os processos ffmpeg
        start_ffmpeg_processes()

        # Inicia o servidor Flask
        print("Servidor Flask rodando...")
        app.run(host="0.0.0.0", port=5000)
    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()