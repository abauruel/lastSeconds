import os
import signal
from datetime import datetime
import subprocess
from led_ws281x_new import blink_n_times, cleanup, start_blinking
import time
from database import get_db, Video, VideoStatus

device_name="rpi4bmobile"

class FFMpegManager:
    def __init__(self, buffer_dir_video0, buffer_dir_video2, final_dir, stream_dir):
        self.buffer_dir_video0 = '/tmp/buffers/video0'
        self.buffer_dir_video2 = '/tmp/buffers/video2'
        self.final_dir = final_dir
        self.stream_dir = stream_dir
        self.ffmpeg_process_0 = None
        self.ffmpeg_process_1 = None

    def start_ffmpeg_processes(self):
        
 
        """Inicia os processos ffmpeg com buffer circular."""
        self.ffmpeg_process_0 = subprocess.Popen([
            "ffmpeg", "-loglevel", "info", "-fflags", "+genpts", "-f", "v4l2", "-input_format", "h264", "-video_size", "1280x720", "-r", "25", "-i", "/dev/video0",

            "-use_wallclock_as_timestamps", "1", "-fps_mode", "vfr",
            "-c:v", "copy", "-crf","18","-f", "segment", "-segment_time", "5", "-segment_format", "mp4",
            "-reset_timestamps", "1",
            "-segment_wrap", "100",
            f"{self.buffer_dir_video0}/buffer_video0_%03d.mp4",

            "-c:v", "copy", "-preset", "ultrafast", "-tune", "zerolatency", 
            # "-b:v", "4M", "-maxrate", "4M", "-bufsize", "4M", "-an", 
            "-f", "flv", "rtmp://localhost/live/stream1",

           "-c:v", "copy", "-crf", "23", "-f", "segment", "-segment_time","5","-segment_format","mp4", 
            "-reset_timestamps", "1", "-strftime", "1", "-ignore_io_errors", "1", "-segment_wrap","51840",
            "/media/pi/EC-N-64GB/bts/stream1/video0_%Y%m%d_%H%M%S_%03d.mp4",
            
            
        ], preexec_fn=os.setsid)

        self.ffmpeg_process_1 = subprocess.Popen([
            "ffmpeg",  "-loglevel", "info", "-fflags", "+genpts", "-f", "v4l2", "-input_format", "h264", "-video_size", "1280x720", "-r", "25", "-i", "/dev/video2",
            "-use_wallclock_as_timestamps", "1", "-fps_mode", "vfr",
            "-c:v", "copy", "-preset", "ultrafast", "-tune", "zerolatency", 
            # "-b:v", "4M", "-maxrate", "4M", "-bufsize", "4M", "-an", 
            "-f", "flv", "rtmp://localhost/live/stream2",
            "-c:v", "copy",  "-crf", "18","-f", "segment", "-segment_time", "1", "-segment_format", "mp4",
            "-reset_timestamps", "1", 
            "-segment_wrap", "100",
            f"{self.buffer_dir_video2}/buffer_video2_%03d.mp4",

            "-c:v", "copy", "-crf", "23", "-f", "segment", "-segment_time","5","-segment_format","mp4", 
            "-reset_timestamps", "1", "-strftime", "1", "-ignore_io_errors", "1", "-segment_wrap","51840",
            "/media/pi/EC-N-64GB/bts/stream2/video2_%Y%m%d_%H%M%S_%03d.mp4",
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

    def record_last_10_seconds(self, cam_id=0):
        """Copia os últimos 10 segundos de stream para um novo arquivo."""
        print("Gravando os últimos 10 segundos de stream...")
        if cam_id == 0:
            blink_n_times(color=(255, 0, 0), n=5, interval=0.2, direction="left")
            cleanup()
        if cam_id == 1:
            blink_n_times(color=(0, 0, 255), n=5, interval=0.2, direction="right")
            cleanup()
        current_date = datetime.now()
        date_folder = current_date.strftime("%Y%m%d")
        date_folder_path = os.path.join(self.stream_dir, date_folder)
        
        # Create date folder if it doesn't exist
        os.makedirs(date_folder_path, exist_ok=True)
        
        timestamp = current_date.strftime("%Y%m%d_%H%M%S")
        output_file_0 = os.path.join(date_folder_path, f"{device_name}_stream1_{timestamp}.mp4")
        output_file_1 = os.path.join(date_folder_path, f"{device_name}_stream2_{timestamp}.mp4")

        buffer_files_0 = sorted([os.path.join(self.buffer_dir_video0, f) for f in os.listdir(self.buffer_dir_video0) if f.startswith("buffer_video0_")],
                                 key=os.path.getmtime)[-6:]
        
        buffer_files_1 = sorted([os.path.join(self.buffer_dir_video2, f) for f in os.listdir(self.buffer_dir_video2) if f.startswith("buffer_video2_")],
                                key=os.path.getmtime)[-6:]

        if cam_id == 0 and buffer_files_0:
            self._combine_segments(buffer_files_0, output_file_0)
            generateThumb(output_file_0)
            print(f"Gravação concluída: {output_file_0}")
        else:
            print("Erro: Nenhum arquivo encontrado no buffer para /dev/video0.")

        if cam_id == 1 and buffer_files_1:
            self._combine_segments(buffer_files_1, output_file_1)
            generateThumb(output_file_1)
            print(f"Gravação concluída: {output_file_1}")
        else:
            print("Erro: Nenhum arquivo encontrado no buffer para /dev/video2.")

        
        
     
        
    def _save_video_to_db(self, video_path):
        """Salva informações do vídeo no banco de dados."""
        try:
            db = next(get_db())
            video_name = os.path.basename(video_path)
            relative_path = os.path.relpath(video_path, start=self.stream_dir)
            
            video = Video(
                name=video_name,
                path=relative_path,  # Salva o caminho relativo do arquivo
                date=datetime.now(),
                status=VideoStatus.PENDING
            )
            db.add(video)
            db.commit()
            print(f"Informações do vídeo {video_name} salvas no banco de dados. Path: {relative_path}")
        except Exception as e:
            print(f"Erro ao salvar informações do vídeo no banco de dados: {e}")
            if 'db' in locals():
                db.rollback()

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
        
        # Salva informações do vídeo no banco de dados com o caminho completo
        self._save_video_to_db(output_file)
    
    
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
