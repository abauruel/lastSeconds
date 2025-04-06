import os
import signal
import subprocess
from datetime import datetime

class FFMpegManager:
    def __init__(self, buffer_dir_video0, buffer_dir_video2, final_dir, stream_dir):
        self.buffer_dir_video0 = buffer_dir_video0
        self.buffer_dir_video2 = buffer_dir_video2
        self.final_dir = final_dir
        self.stream_dir = stream_dir
        self.ffmpeg_process_0 = None
        self.ffmpeg_process_1 = None

    def start_ffmpeg_processes(self):
        
        """Inicia os processos ffmpeg com buffer circular."""
        self.ffmpeg_process_0 = subprocess.Popen([
            "ffmpeg", "-fflags", "+genpts", "-f", "v4l2", "-input_format", "h264", "-video_size", "1280x720", "-r", "30", "-i", "/dev/video0",

            "-use_wallclock_as_timestamps", "1", "-fps_mode", "vfr",
            "-c:v", "copy", "-crf","18","-f", "segment", "-segment_time", "1", "-segment_format", "mp4",
            "-reset_timestamps", "1", f"{self.buffer_dir_video0}/buffer_video0_%03d.mp4",
            "-c:v", "copy", "-preset", "ultrafast", "-tune", "zerolatency", "-b:v", "6M", "-maxrate", "6M", "-bufsize", "12M", "-an", "-f", "flv", "rtmp://localhost/live/stream1"
        ], preexec_fn=os.setsid)

        self.ffmpeg_process_1 = subprocess.Popen([
            "ffmpeg", "-fflags", "+genpts", "-f", "v4l2", "-input_format", "h264", "-video_size", "1280x720", "-r", "30", "-i", "/dev/video2",
            "-use_wallclock_as_timestamps", "1", "-fps_mode", "vfr",
            "-c:v", "copy", "-preset", "ultrafast", "-tune", "zerolatency", "-b:v", "6M", "-maxrate", "6M", "-bufsize", "12M", "-an", "-f", "flv", "rtmp://localhost/live/stream2",
            "-c:v", "copy",  "-crf", "18","-f", "segment", "-segment_time", "1", "-segment_format", "mp4",
            "-reset_timestamps", "1", f"{self.buffer_dir_video2}/buffer_video2_%03d.mp4"
        ], preexec_fn=os.setsid)

        print("Processos ffmpeg iniciados com buffer circular.")

    def stop_ffmpeg_processes(self):
        """Finaliza os processos ffmpeg."""
        try:
            if self.ffmpeg_process_0:
                os.killpg(os.getpgid(self.ffmpeg_process_0.pid), signal.SIGTERM)
                print("Processo ffmpeg_process_0 finalizado com sucesso.")
            if self.ffmpeg_process_1:
                os.killpg(os.getpgid(self.ffmpeg_process_1.pid), signal.SIGTERM)
                print("Processo ffmpeg_process_1 finalizado com sucesso.")
        except Exception as e:
            print(f"Erro ao finalizar os processos do ffmpeg: {e}")
        finally:
            self.ffmpeg_process_0 = None
            self.ffmpeg_process_1 = None

    def record_last_10_seconds(self):
        """Copia os últimos 10 segundos de stream para um novo arquivo."""
        print("Gravando os últimos 10 segundos de stream...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file_0 = os.path.join(self.stream_dir, f"stream1_{timestamp}.mp4")
        output_file_1 = os.path.join(self.stream_dir, f"stream2_{timestamp}.mp4")

        buffer_files_0 = sorted([os.path.join(self.buffer_dir_video0, f) for f in os.listdir(self.buffer_dir_video0) if f.startswith("buffer_video0_")])[-5:]
        buffer_files_1 = sorted([os.path.join(self.buffer_dir_video2, f) for f in os.listdir(self.buffer_dir_video2) if f.startswith("buffer_video2_")])[-5:]

        if buffer_files_0:
            self._combine_segments(buffer_files_0, output_file_0)
            generateThumb(output_file_0)
            print(f"Gravação concluída: {output_file_0}")
        else:
            print("Erro: Nenhum arquivo encontrado no buffer para /dev/video0.")

        if buffer_files_1:
            self._combine_segments(buffer_files_1, output_file_1)
            generateThumb(output_file_1)
            print(f"Gravação concluída: {output_file_1}")
        else:
            print("Erro: Nenhum arquivo encontrado no buffer para /dev/video2.")

    def _combine_segments(self, segment_files, output_file):
        """Combina múltiplos arquivos de segmento em um único arquivo."""
        temp_file = f"{output_file}_list.txt"
        with open(temp_file, "w") as file_list:
            for segment in segment_files:
                file_list.write(f"file '{os.path.abspath(segment)}'\n")

        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", temp_file, "-c:v", "copy", "-movflags", "+faststart", output_file
        ])
        os.remove(temp_file)
    
    
    def clear_buffers(self):
        """Rota para limpar os arquivos das pastas buffers/video0 e buffers/video2."""
        try:
            # Remove os arquivos da pasta buffers/video0
            for buffer_file in os.listdir(self.buffer_dir_video0):
                file_path = os.path.join(self.buffer_dir_video0, buffer_file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            print("Arquivos da pasta buffers/video0 removidos.")

            # Remove os arquivos da pasta buffers/video2
            for buffer_file in os.listdir(self.buffer_dir_video2):
                file_path = os.path.join(self.buffer_dir_video2, buffer_file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            print("Arquivos da pasta buffers/video2 removidos.")

            # return jsonify({"status": "success", "message": "Buffers limpos com sucesso."}), 200
        except Exception as e:
            print(f"Erro ao limpar os buffers: {e}")
            # return jsonify({"status": "error", "message": "Erro ao limpar os buffers."}), 500

def generateThumb(file):
    print(f'Generating thumb for {file}')
    command = f'ffmpeg -loglevel error -y -i ./{file} -ss 00:00:01.000 -vframes 1 {file}.jpeg '
    proc = os.popen(command)
    proc.close()