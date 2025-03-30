import os
import signal
import subprocess
from flask import Flask, jsonify
from datetime import datetime


# Configurações
BASE_DIR = "./recordings"
BUFFER_DIR = os.path.join(BASE_DIR, "buffers")
FINAL_DIR = os.path.join(BASE_DIR, "recordings")
STREAM_DIR = os.path.join(BASE_DIR, "streams")

# Cria os diretórios, se não existirem
os.makedirs(BUFFER_DIR, exist_ok=True)
os.makedirs(FINAL_DIR, exist_ok=True)
os.makedirs(STREAM_DIR, exist_ok=True)

# Subdiretórios para buffers de cada câmera
BUFFER_DIR_VIDEO0 = os.path.join(BUFFER_DIR, "video0")
BUFFER_DIR_VIDEO2 = os.path.join(BUFFER_DIR, "video2")
os.makedirs(BUFFER_DIR_VIDEO0, exist_ok=True)
os.makedirs(BUFFER_DIR_VIDEO2, exist_ok=True)


# Configurações
# OUTPUT_DIR = "./recordings"
# os.makedirs(OUTPUT_DIR, exist_ok=True)

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
        "-reset_timestamps", "1", f"{BUFFER_DIR_VIDEO0}/buffer_video0_%03d.mp4"
    ], preexec_fn=os.setsid)  # Inicia o processo em um novo grupo de processos

    # Buffer circular para /dev/video2
    ffmpeg_process_1 = subprocess.Popen([
        "ffmpeg", "-f", "v4l2", "-input_format", "h264", "-video_size", "1280x720", "-r", "25", "-i", "/dev/video2",
        "-use_wallclock_as_timestamps", "1", 
        "-c:v", "copy", "-preset", "ultrafast", "-tune", "zerolatency",  "-b:v", "800k", "-maxrate","1M", "-bufsize", "800k", "-an", "-f", "flv", "rtmp://localhost/live/stream2",
        "-c:v", "copy", "-f", "segment", "-segment_time", "1", "-segment_format", "mp4",
        "-reset_timestamps", "1", f"{BUFFER_DIR_VIDEO2}/buffer_video2_%03d.mp4"
    ], preexec_fn=os.setsid)

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
    output_file_0 = os.path.join(STREAM_DIR, f"stream1_{timestamp}.mp4")
    output_file_1 = os.path.join(STREAM_DIR, f"stream2_{timestamp}.mp4")

    # Arquivos temporários para listas de segmentos
    temp_file_0 = os.path.join(BUFFER_DIR_VIDEO0, "file_list_video0.txt")
    temp_file_1 = os.path.join(BUFFER_DIR_VIDEO2, "file_list_video2.txt")

    # Identifica os últimos 10 arquivos no buffer circular
    buffer_files_0 = sorted([os.path.join(BUFFER_DIR_VIDEO0, f) for f in os.listdir(BUFFER_DIR_VIDEO0) if f.startswith("buffer_video0_")])[-5:]
    buffer_files_1 = sorted([os.path.join(BUFFER_DIR_VIDEO2, f) for f in os.listdir(BUFFER_DIR_VIDEO2) if f.startswith("buffer_video2_")])[-5:]

    if buffer_files_0:
        combine_segments(buffer_files_0, output_file_0, temp_file_0)
        generateThumb(output_file_0)
        print(f"Gravação concluída: {output_file_0}")
    else:
        print("Erro: Nenhum arquivo encontrado no buffer para /dev/video0.")

    if buffer_files_1:
        combine_segments(buffer_files_1, output_file_1, temp_file_1)
        generateThumb(output_file_1)
        print(f"Gravação concluída: {output_file_1}")
    else:
        print("Erro: Nenhum arquivo encontrado no buffer para /dev/video2.")

def generateThumb(file):
    print(f'Generating thumb for {file}')
    command = f'ffmpeg -loglevel error -y -i ./{file} -ss 00:00:03.000 -vframes 1 {file}.jpeg '
    proc = os.popen(command)
    proc.close()

@app.route('/start', methods=['POST'])
def handle_start():
    """Rota para iniciar os processos do ffmpeg."""
    print("Iniciando os processos do ffmpeg...")
    start_ffmpeg_processes()  # Inicia os processos do ffmpeg
    return jsonify({"status": "success", "message": "Processos do ffmpeg iniciados."}), 200

@app.route('/record', methods=['POST'])
def handle_record():
    """Rota para iniciar a gravação dos últimos 10 segundos."""
    record_last_10_seconds()
    return jsonify({"status": "success", "message": "Gravação iniciada"}), 200


@app.route('/status', methods=['GET'])
def status():
    """Rota para verificar o status do servidor."""
    return jsonify({"status": "running"}), 200

@app.route('/stop', methods=['POST'])
def handle_stop():
    """Rota para parar os processos do ffmpeg e juntar todos os buffers em um único arquivo."""
    print("Parando os processos do ffmpeg e juntando os buffers...")
    cleanup()  # Finaliza os processos do ffmpeg

    # Junta todos os buffers de cada câmera
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file_0 = os.path.join(FINAL_DIR, f"final_stream1_{timestamp}.mp4")
    output_file_1 = os.path.join(FINAL_DIR, f"final_stream2_{timestamp}.mp4")

    # Identifica todos os arquivos no buffer circular
    buffer_files_0 = sorted([os.path.join(BUFFER_DIR_VIDEO0, f) for f in os.listdir(BUFFER_DIR_VIDEO0) if f.startswith("buffer_video0_")])
    buffer_files_1 = sorted([os.path.join(BUFFER_DIR_VIDEO2, f) for f in os.listdir(BUFFER_DIR_VIDEO2) if f.startswith("buffer_video2_")])

    if buffer_files_0:
        temp_file_0 = os.path.join(BUFFER_DIR_VIDEO0, "file_list_video0.txt")
        with open(temp_file_0, "w") as file_list:
            for segment in buffer_files_0:
                file_list.write(f"file '{os.path.abspath(segment)}'\n")

        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", temp_file_0, "-c:v", "copy", "-movflags", "+faststart", output_file_0
        ])
        os.remove(temp_file_0)
        print(f"Arquivo final criado para /dev/video0: {output_file_0}")
        generateThumb(output_file_0)

        # Remove os buffers de /dev/video0
        # for buffer_file in buffer_files_0:
        #     os.remove(buffer_file)
        # print("Buffers de /dev/video0 removidos.")

    else:
        print("Erro: Nenhum arquivo encontrado no buffer para /dev/video0.")

    if buffer_files_1:
        temp_file_1 = os.path.join(BUFFER_DIR_VIDEO2, "file_list_video2.txt")
        with open(temp_file_1, "w") as file_list:
            for segment in buffer_files_1:
                file_list.write(f"file '{os.path.abspath(segment)}'\n")

        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", temp_file_1, "-c:v", "copy", "-movflags", "+faststart", output_file_1
        ])
        os.remove(temp_file_1)
        print(f"Arquivo final criado para /dev/video2: {output_file_1}")
        generateThumb(output_file_1)

        # Remove os buffers de /dev/video0
        # for buffer_file in buffer_files_1:
        #     os.remove(buffer_file)
        # print("Buffers de /dev/video2 removidos.")
    else:
        print("Erro: Nenhum arquivo encontrado no buffer para /dev/video2.")

    return jsonify({"status": "success", "message": "Processos parados e buffers combinados."}), 200

@app.route('/clear_buffers', methods=['POST'])
def clear_buffers():
    """Rota para limpar os arquivos das pastas buffers/video0 e buffers/video2."""
    try:
        # Remove os arquivos da pasta buffers/video0
        for buffer_file in os.listdir(BUFFER_DIR_VIDEO0):
            file_path = os.path.join(BUFFER_DIR_VIDEO0, buffer_file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        print("Arquivos da pasta buffers/video0 removidos.")

        # Remove os arquivos da pasta buffers/video2
        for buffer_file in os.listdir(BUFFER_DIR_VIDEO2):
            file_path = os.path.join(BUFFER_DIR_VIDEO2, buffer_file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        print("Arquivos da pasta buffers/video2 removidos.")

        return jsonify({"status": "success", "message": "Buffers limpos com sucesso."}), 200
    except Exception as e:
        print(f"Erro ao limpar os buffers: {e}")
        return jsonify({"status": "error", "message": "Erro ao limpar os buffers."}), 500

def cleanup():
    """Finaliza os processos do ffmpeg corretamente."""
    print("Finalizando os processos do ffmpeg...")
    global ffmpeg_process_0, ffmpeg_process_1

    try:
        if ffmpeg_process_0:
            os.killpg(os.getpgid(ffmpeg_process_0.pid), signal.SIGTERM)
            print("Processo ffmpeg_process_0 finalizado com sucesso.")
        else:
            print("ffmpeg_process_0 não foi inicializado.")

        if ffmpeg_process_1:
            os.killpg(os.getpgid(ffmpeg_process_1.pid), signal.SIGTERM)
            print("Processo ffmpeg_process_1 finalizado com sucesso.")
        else:
            print("ffmpeg_process_1 não foi inicializado.")
    except Exception as e:
        print(f"Erro ao finalizar os processos do ffmpeg: {e}")
    finally:
        ffmpeg_process_0 = None
        ffmpeg_process_1 = None
        print("Cleanup concluído.")

def check_ffmpeg_processes():
    """Verifica o status dos processos ffmpeg."""
    global ffmpeg_process_0, ffmpeg_process_1

    if ffmpeg_process_0 and ffmpeg_process_0.poll() is None:
        print("ffmpeg_process_0 ainda está rodando.")
    else:
        print("ffmpeg_process_0 não está rodando.")

    if ffmpeg_process_1 and ffmpeg_process_1.poll() is None:
        print("ffmpeg_process_1 ainda está rodando.")
    else:
        print("ffmpeg_process_1 não está rodando.")

def main():
    try:
        # Inicia os processos ffmpeg
        # start_ffmpeg_processes()

        # Inicia o servidor Flask
        print("Servidor Flask rodando...")
        app.run(host="0.0.0.0", port=5000)
    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()