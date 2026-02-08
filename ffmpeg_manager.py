import os
import signal
from datetime import datetime, timedelta
import subprocess
from led_ws281x_new import blink_n_times, cleanup, start_blinking
import time
from database import get_db, Video, VideoStatus
import json
import threading

device_name="rpi4bmobile"

class FFMpegManager:
    def __init__(self, buffer_dir_video0, buffer_dir_video2, final_dir, stream_dir):
        self.buffer_dir_video0 = '/home/pi/app/recordings/buffers/video0'
        self.buffer_dir_video2 = '/home/pi/app/recordings/buffers/video2'
        self.final_dir = final_dir
        self.stream_dir = stream_dir
        self.ffmpeg_process_0 = None
        self.ffmpeg_process_1 = None

        # Diretório para armazenar os arquivos de timestamp
        self.timestamp_dir = os.path.join(stream_dir, "timestamps")
        os.makedirs(self.timestamp_dir, exist_ok=True)

    def start_ffmpeg_processes(self, device_number=0, input_source="usb", stream=""):
        if device_number == 0:
            DEVICE= "/dev/video0" if input_source == "usb" else stream
            PREFIX="video0"
            BUFFER_DIR = f"{self.buffer_dir_video0}"
            DISK_DIR = "/media/pi/usb64gb/bts/stream1"
        else:
            DEVICE="/dev/video2" if input_source == "usb" else stream
            PREFIX="video2"
            BUFFER_DIR = f"{self.buffer_dir_video2}"
            DISK_DIR = "/media/pi/usb64gb/bts/stream2"
            
        STREAM_NAME = DISK_DIR.split('/')[-1]
        print(f"stream name: {STREAM_NAME}")

        cmd_usb = [
            "ffmpeg", "-rtbufsize","256M",
	    "-hide_banner","-loglevel","error",
        # "-report","-benchmark_all","-stats_period","5",
	    "-fflags", "+genpts",
            "-f", "v4l2", "-input_format", "h264", "-video_size", "1280x720", "-r", "25", 
            "-i", f"{DEVICE}",
            "-use_wallclock_as_timestamps", "1", "-fps_mode", "vfr",
            "-force_key_frames", "expr:gte(t,n_forced*2)",  # Força keyframes a cada 2s
            "-map", "0:v",
            "-c:v", "copy",          # usa aceleração de hardware
            #  "-c:v", "h264_v4l2m2m","-pix_fmt", "yuv420p", "-b:v", "2M","-maxrate", "2.5M","-bufsize", "4M",
	    #"-preset", "ultrafast", "-crf", "23",  # Re-encode para keyframes regulares
            # "-g", "50", "-keyint_min", "50",  # Keyframe a cada 2s (50 frames @ 25fps)
            "-ignore_io_errors", "1",
            "-f", "tee",
            (
                f"[f=flv:onfail=ignore]"
                f"rtmp://localhost/live/{STREAM_NAME}|"
                # f"[f=segment:segment_time=300:reset_timestamps=1:avoid_negative_ts=make_zero:segment_format=mp4:segment_wrap=50]{BUFFER_DIR}/buffer_{PREFIX}_%03d.mp4"

                f"[f=segment:segment_time=300:reset_timestamps=1:avoid_negative_ts=make_zero:segment_format=mp4:strftime=1:segment_wrap=60]{DISK_DIR}/{PREFIX}_%Y%m%d_%H%M%S.mp4"
                #f"[f=segment:segment_time=5:reset_timestamps=1:avoid_negative_ts=make_zero:segment_format=mp4:strftime=1:segment_wrap=691200]{DISK_DIR}/{PREFIX}_%Y%m%d_%H%M%S_%03d.mp4"
            )
            
            
        ]
        cmd_rtsp = [
            "ffmpeg", "-rtbufsize","256M",
	    "-hide_banner","-loglevel","error","-report","-benchmark_all","-stats_period","5",
	    "-fflags", "+genpts",
            "-i", f"{DEVICE}",
            "-use_wallclock_as_timestamps", "1", "-fps_mode", "vfr",
            "-force_key_frames", "expr:gte(t,n_forced*2)",  # Força keyframes a cada 2s
            "-map", "0:v",
            "-c:v", "copy",          # usa aceleração de hardware
            "-ignore_io_errors", "1",
            "-f", "tee",
            (
                # f"[f=segment:segment_time=2:reset_timestamps=1:avoid_negative_ts=make_zero:segment_format=mp4:segment_wrap=100]{BUFFER_DIR}/buffer_{PREFIX}_%03d.mp4|"
                f"[f=segment:segment_time=300:reset_timestamps=1:avoid_negative_ts=make_zero:segment_format=mp4:strftime=1:segment_wrap=60]{DISK_DIR}/{PREFIX}_%Y%m%d_%H%M%S.mp4"
            )
            
            
        ]

        """Inicia os processos ffmpeg com buffer circular."""
        if device_number == 0:
            print("Iniciando ffmpeg para /dev/video0...")
            with open("/media/pi/usb64gb/bts/ffmpeg_device0.log", "a") as logfile:
                cmd = cmd_usb if input_source == "usb" else cmd_rtsp
                self.ffmpeg_process_0 = subprocess.Popen(cmd, preexec_fn=os.setsid, stdout=logfile, stderr=logfile)
        else:
            print("Iniciando ffmpeg para /dev/video2...")
            with open("/media/pi/usb64gb/bts/ffmpeg_device2.log", "a") as logfile:
                cmd = cmd_usb if input_source == "usb" else cmd_rtsp
                self.ffmpeg_process_1 = subprocess.Popen(cmd, preexec_fn=os.setsid, stdout=logfile, stderr=logfile)


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
        """
        Registra apenas o timestamp do evento em um arquivo.
        Esta função é rápida e não bloqueia.
        """
        try:
            current_time = datetime.now()
            date_str = current_time.strftime("%Y%m%d")
            timestamp_file = os.path.join(self.timestamp_dir, f"{date_str}.txt")
            
            
            # Formato: timestamp_epoch|timestamp_iso|cam_id|status
            event_data = {
                "timestamp_epoch": int(current_time.timestamp()),
                "timestamp_iso": current_time.isoformat(),
                "cam_id": cam_id,
                "status": "pending"
            }
            
            # Append ao arquivo do dia
            with open(timestamp_file, "a") as f:
                f.write(json.dumps(event_data) + "\n")
            
            print(f"Evento registrado: cam_id={cam_id}, timestamp={current_time.isoformat()}")
            
            # Feedback visual rápido
            if cam_id == 0:
                threading.Thread(target=lambda: [
                    blink_n_times(color=(255, 0, 0), n=2, interval=0.1, direction="left"),
                    cleanup()
                ], daemon=True).start()
            else:
                threading.Thread(target=lambda: [
                    blink_n_times(color=(0, 0, 255), n=2, interval=0.1, direction="right"),
                    cleanup()
                ], daemon=True).start()
            
            return True
            
        except Exception as e:
            print(f"Erro ao registrar timestamp: {e}")
            return False

    def _update_event_status(self, timestamp_file, event, new_status):
        """Atualiza o status de um evento no arquivo."""
        try:
            # Lê todas as linhas
            with open(timestamp_file, "r") as f:
                lines = f.readlines()
            
            # Atualiza a linha correspondente
            updated_lines = []
            for line in lines:
                try:
                    current_event = json.loads(line.strip())
                    if (current_event["timestamp_epoch"] == event["timestamp_epoch"] and 
                        current_event["cam_id"] == event["cam_id"]):
                        current_event["status"] = new_status
                        current_event["processed_at"] = datetime.now().isoformat()
                        updated_lines.append(json.dumps(current_event) + "\n")
                    else:
                        updated_lines.append(line)
                except json.JSONDecodeError:
                    updated_lines.append(line)
            
            # Reescreve o arquivo
            with open(timestamp_file, "w") as f:
                f.writelines(updated_lines)
                
        except Exception as e:
            print(f"Erro ao atualizar status do evento: {e}")

    def _extract_video_from_timestamp(self, timestamp_epoch, cam_id):
        """
        Extrai um vídeo de 10 segundos baseado no timestamp fornecido.
        Busca nos arquivos de segmento de 5 minutos.
        """
        try:
            # Define o diretório baseado na câmera
            if cam_id == 0:
                DISK_DIR = "/media/pi/usb64gb/bts/stream1"
                PREFIX = "video0"
            else:
                DISK_DIR = "/media/pi/usb64gb/bts/stream2"
                PREFIX = "video2"
            
            # Converte timestamp para datetime
            event_time = datetime.fromtimestamp(timestamp_epoch)
            
            # Busca o arquivo de segmento que contém o timestamp
            # Como cada segmento tem 5 minutos, procura 6 horas antes e depois
            search_start = event_time - timedelta(hours=6)
            search_end = event_time + timedelta(minutes=5)
            
            # Lista todos os arquivos de segmento do disco
            segment_files = []
            if os.path.exists(DISK_DIR):
                for filename in os.listdir(DISK_DIR):
                    if filename.startswith(PREFIX) and filename.endswith(".mp4"):
                        try:
                            # Parse do timestamp do nome do arquivo: video0_20260208_131022.mp4
                            # Formato: PREFIX_YYYYMMDD_HHMMSS.mp4
                            timestamp_part = filename.replace(f"{PREFIX}_", "").replace(".mp4", "")
                            file_time = datetime.strptime(timestamp_part, "%Y%m%d_%H%M%S")
                            
                            filepath = os.path.join(DISK_DIR, filename)
                            
                            # Verifica se o arquivo está no range de busca
                            if search_start <= file_time <= search_end:
                                segment_files.append((filepath, file_time))
                        except (ValueError, IndexError) as e:
                            # Se não conseguir parsear o nome, usa mtime como fallback
                            print(f"Aviso: não foi possível parsear timestamp do arquivo {filename}: {e}")
                            file_mtime = os.path.getmtime(os.path.join(DISK_DIR, filename))
                            file_time = datetime.fromtimestamp(file_mtime)
                            if search_start <= file_time <= search_end:
                                segment_files.append((filepath, file_time))
            
            if not segment_files:
                print(f"Nenhum arquivo de segmento encontrado para o timestamp {event_time}")
                return False
            
            # Ordena por tempo
            segment_files.sort(key=lambda x: x[1])
            
            print(f"DEBUG: Encontrados {len(segment_files)} arquivos de segmento para evento em {event_time}")
            
            # Encontra o arquivo que contém o timestamp do evento
            target_file = None
            file_start_time = None
            for filepath, file_time in segment_files:
                # Cada arquivo tem 5 minutos (300 segundos)
                file_end_time = file_time + timedelta(minutes=5)
                print(f"DEBUG: Verificando arquivo {os.path.basename(filepath)}: {file_time} até {file_end_time}")
                if file_time <= event_time <= file_end_time:
                    target_file = filepath
                    file_start_time = file_time
                    print(f"DEBUG: Arquivo encontrado! {os.path.basename(filepath)}")
                    break
            
            if not target_file:
                # Se não encontrar exato, pega o mais próximo
                print(f"DEBUG: Nenhum arquivo exato, pegando o mais próximo")
                closest = min(segment_files, key=lambda x: abs((x[1] - event_time).total_seconds()))
                target_file = closest[0]
                file_start_time = closest[1]
                print(f"DEBUG: Arquivo mais próximo: {os.path.basename(target_file)}")
            
            # Verifica se o arquivo está completo (não está sendo escrito)
            file_size = os.path.getsize(target_file)
            file_age = time.time() - os.path.getmtime(target_file)
            
            if file_size < 100000:  # Menos de 100KB, provavelmente ainda sendo escrito
                print(f"AVISO: Arquivo {os.path.basename(target_file)} muito pequeno ({file_size} bytes), pode estar incompleto")
                return False
            
            # Aguarda pelo menos 10 segundos após a última modificação para garantir que foi finalizado
            if file_age < 10:
                print(f"AVISO: Arquivo {os.path.basename(target_file)} muito recente ({file_age:.1f}s), ainda pode estar sendo escrito")
                return False
            
            # Calcula o offset dentro do arquivo
            # IMPORTANTE: Com reset_timestamps=1 no FFmpeg, cada arquivo inicia em 0
            # Então o offset é: (event_time - file_start_time)
            # E queremos 5 segundos ANTES do evento até 5 segundos DEPOIS
            offset_in_file = (event_time - file_start_time).total_seconds()
            offset_seconds = max(0, offset_in_file - 5)  # 5 segundos antes do evento
            
            # Verifica se o evento está realmente dentro do arquivo (com margem de 10s para o clipe)
            if offset_seconds > 290:  # 300s - 10s de margem
                print(f"ERRO: Offset {offset_seconds:.2f}s muito grande para arquivo de 5 minutos")
                return False
            
            print(f"DEBUG: Offset calculado: {offset_seconds:.2f}s no arquivo {os.path.basename(target_file)}")
            
            # Cria o diretório de saída
            date_folder = event_time.strftime("%Y%m%d")
            date_folder_path = os.path.join(self.stream_dir, date_folder)
            os.makedirs(date_folder_path, exist_ok=True)
            os.chown(date_folder_path, 1000, 1000)
            
            # Nome do arquivo de saída
            timestamp_str = event_time.strftime("%Y%m%d_%H%M%S")
            stream_name = "stream1" if cam_id == 0 else "stream2"
            output_file = os.path.join(date_folder_path, f"{device_name}_{stream_name}_{timestamp_str}.mp4")
            
            # Extrai 10 segundos do vídeo usando ffmpeg
            # Abordagem simples: -ss antes de -i (rápido) com -c:v copy
            extract_cmd = [
                "ffmpeg", "-y",
                "-ss", str(offset_seconds),
                "-i", target_file,
                "-t", "10",  # 10 segundos
                "-c:v", "copy",
                "-movflags", "+faststart",
                output_file
            ]
            
            print(f"Extraindo vídeo: arquivo={os.path.basename(target_file)}, offset={offset_seconds:.2f}s -> {os.path.basename(output_file)}")
            result = subprocess.run(extract_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"ERRO FFmpeg: {result.stderr}")
            
            if result.returncode == 0 and os.path.exists(output_file) and os.path.getsize(output_file) > 10000:
                # Gera thumbnail
                generateThumb(output_file)
                
                # Salva no banco de dados
                self._save_video_to_db(output_file)
                
                print(f"Vídeo extraído com sucesso: {output_file}")
                return True
            else:
                print(f"Erro ao extrair vídeo: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"Erro ao extrair vídeo do timestamp: {e}")
            return False

    def manual_process_timestamps(self, date_str=None, days_back=3):
        """
        Processa manualmente os timestamps de um dia específico ou dos últimos N dias.
        Se date_str for None, processa os últimos 'days_back' dias.
        """
        total_processed = 0
        total_failed = 0
        dates_processed = []
        
        if date_str:
            # Processa apenas o dia específico
            dates_to_process = [date_str]
        else:
            # Processa os últimos N dias
            dates_to_process = []
            for days_ago in range(days_back):
                target_date = datetime.now() - timedelta(days=days_ago)
                dates_to_process.append(target_date.strftime("%Y%m%d"))
        
        for current_date in dates_to_process:
            timestamp_file = os.path.join(self.timestamp_dir, f"{current_date}.txt")
            
            if not os.path.exists(timestamp_file):
                continue
            
            print(f"Processando timestamps de {current_date}...")
            processed = 0
            failed = 0
            
            # Lê todos os eventos do arquivo
            with open(timestamp_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            event = json.loads(line)
                            if event.get("status") == "pending":
                                success = self._extract_video_from_timestamp(
                                    timestamp_epoch=event["timestamp_epoch"],
                                    cam_id=event["cam_id"]
                                )
                                
                                if success:
                                    self._update_event_status(timestamp_file, event, "processed")
                                    processed += 1
                                else:
                                    self._update_event_status(timestamp_file, event, "failed")
                                    failed += 1
                        except Exception as e:
                            print(f"Erro ao processar linha: {e}")
                            failed += 1
            
            if processed > 0 or failed > 0:
                dates_processed.append(current_date)
                total_processed += processed
                total_failed += failed
                print(f"Data {current_date}: {processed} processados, {failed} falharam")
        
        if not dates_processed:
            return {
                "status": "error",
                "message": "Nenhum timestamp pendente encontrado",
                "processed": 0,
                "failed": 0
            }
        
        return {
            "status": "success",
            "processed": total_processed,
            "failed": total_failed,
            "dates": dates_processed
        }
        
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
