import os
import signal
from datetime import datetime, timedelta
import subprocess
from led_ws281x_new import blink_n_times, cleanup, start_blinking
import time
from database import get_db, Video, VideoStatus
import json
import threading
import re
import fcntl

device_name="rpi4bmobile"

class FFMpegManager:
    def __init__(self, buffer_dir_video0, buffer_dir_video2, final_dir, stream_dir):
        self.buffer_dir_video0 = '/home/pi/app/recordings/buffers/video0'
        self.buffer_dir_video2 = '/home/pi/app/recordings/buffers/video2'
        self.final_dir = final_dir
        self.stream_dir = stream_dir
        self.ffmpeg_process_0 = None
        self.ffmpeg_process_1 = None
        
        # Cache dos dispositivos detectados
        self.detected_cameras = {}
        
        # Lock para operações no arquivo de timestamps
        self.timestamp_lock = threading.Lock()

        # Diretório para armazenar os arquivos de timestamp
        self.timestamp_dir = os.path.join(stream_dir, "timestamps")
        os.makedirs(self.timestamp_dir, exist_ok=True)
    
    def detect_usb_cameras(self):
        """
        Detecta automaticamente as câmeras USB disponíveis.
        Retorna um dicionário com índice da câmera e path do dispositivo.
        Filtra para pegar apenas um dispositivo por câmera física (por bus).
        """
        cameras = {}
        
        try:
            # Lista todos os dispositivos de vídeo
            video_devices = []
            for i in range(32):
                device_path = f"/dev/video{i}"
                if os.path.exists(device_path):
                    video_devices.append(device_path)
            
            if not video_devices:
                print("ERRO: Nenhum dispositivo de vídeo encontrado!")
                return cameras
            
            # Para cada dispositivo, verifica se é uma câmera USB principal
            usb_cameras = []
            seen_buses = set()
            
            for device_path in video_devices:
                try:
                    # Executa v4l2-ctl para obter informações do dispositivo
                    result = subprocess.run(
                        ['v4l2-ctl', '--device', device_path, '--all'],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    
                    output = result.stdout
                    
                    # Verifica se é uvcvideo (câmera USB)
                    if 'uvcvideo' not in output:
                        continue
                    
                    # Extrai informações
                    bus_info = ""
                    device_caps = []
                    in_device_caps_section = False
                    
                    for line in output.split('\n'):
                        if 'Bus info' in line:
                            bus_info = line.split(':', 1)[1].strip()
                        
                        # Detecta início da seção Device Caps
                        if 'Device Caps' in line:
                            in_device_caps_section = True
                            # Pega capabilities da mesma linha se houver
                            if ':' in line:
                                caps_part = line.split(':', 1)[1].strip()
                                if caps_part and not caps_part.startswith('0x'):
                                    device_caps.append(caps_part)
                        # Linhas seguintes após Device Caps (indentadas)
                        elif in_device_caps_section and line.startswith((' ', '\t')):
                            device_caps.append(line.strip())
                        # Fim da seção Device Caps
                        elif in_device_caps_section and not line.startswith((' ', '\t', '')):
                            in_device_caps_section = False
                    
                    device_caps_str = ' '.join(device_caps)
                    
                    # Só adiciona se tiver "Video Capture" nas Device Caps (não Metadata Capture)
                    # Deve ter "Video Capture" mas não deve ser APENAS "Metadata Capture"
                    has_video_capture = 'Video Capture' in device_caps_str
                    is_metadata_only = 'Metadata Capture' in device_caps_str and device_caps_str.count('Capture') == 1
                    
                    if has_video_capture and not is_metadata_only:
                        # Evita duplicatas: pega apenas o primeiro dispositivo de cada bus
                        if bus_info not in seen_buses:
                            seen_buses.add(bus_info)
                            usb_cameras.append({
                                'device': device_path,
                                'bus_info': bus_info,
                                'capabilities': device_caps_str
                            })
                            print(f"Câmera USB detectada: {device_path} (Bus: {bus_info})")
                
                except (subprocess.TimeoutExpired, subprocess.CalledProcessError, Exception) as e:
                    # Ignora dispositivos que não respondem
                    continue
            
            # Ordena por bus_info para manter ordem consistente
            usb_cameras.sort(key=lambda x: x['bus_info'])
            
            # Atribui índices às câmeras
            for idx, cam_info in enumerate(usb_cameras):
                cameras[idx] = cam_info['device']
                print(f"Câmera {idx}: {cam_info['device']} (Bus: {cam_info['bus_info']})")
            
            if not cameras:
                print("AVISO: Nenhuma câmera USB válida encontrada!")
            
        except Exception as e:
            print(f"ERRO ao detectar câmeras: {e}")
        
        return cameras

    def start_ffmpeg_processes(self, device_number=0, input_source="usb", stream=""):
        # Se for USB, detecta as câmeras automaticamente
        if input_source == "usb":
            # Detecta câmeras apenas se ainda não foram detectadas ou se o cache está vazio
            if not self.detected_cameras:
                print(f"\nDetectando câmeras USB disponíveis...")
                self.detected_cameras = self.detect_usb_cameras()
            
            # Verifica se a câmera solicitada foi detectada
            if device_number not in self.detected_cameras:
                print(f"ERRO: Câmera {device_number} não encontrada!")
                print(f"Câmeras disponíveis: {list(self.detected_cameras.keys())}")
                return
            
            DEVICE = self.detected_cameras[device_number]
            print(f"Usando câmera {device_number}: {DEVICE}")
        else:
            # Para RTSP, usa o stream fornecido
            DEVICE = stream
        
        # Configuração baseada no device_number
        if device_number == 0:
            PREFIX="video0"
            BUFFER_DIR = f"{self.buffer_dir_video0}"
            DISK_DIR = "/media/pi/usb64gb/bts/stream1"
        else:
            PREFIX="video2"
            BUFFER_DIR = f"{self.buffer_dir_video2}"
            DISK_DIR = "/media/pi/usb64gb/bts/stream2"
            
        STREAM_NAME = DISK_DIR.split('/')[-1]
        print(f"stream name: {STREAM_NAME}")
        print(f"Iniciando FFmpeg: device={DEVICE}, prefix={PREFIX}, dir={DISK_DIR}")

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
                # Segmentos de 1 minuto para testes rápidos
                f"[f=segment:segment_time=60:reset_timestamps=1:avoid_negative_ts=make_zero:segment_format=mp4:strftime=1:segment_wrap=18000]{DISK_DIR}/{PREFIX}_%Y%m%d_%H%M%S.mp4"
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
                f"[f=segment:segment_time=60:reset_timestamps=1:avoid_negative_ts=make_zero:segment_format=mp4:strftime=1:segment_wrap=18000]{DISK_DIR}/{PREFIX}_%Y%m%d_%H%M%S.mp4"
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

    def record_last_10_seconds(self, cam_id=0, duration=10):
        """
        Registra apenas o timestamp do evento em um arquivo.
        Esta função é rápida e não bloqueia.
        
        Args:
            cam_id: ID da câmera (0 ou 1)
            duration: Duração do vídeo em segundos (padrão: 10)
        """
        try:
            current_time = datetime.now()
            date_str = current_time.strftime("%Y%m%d")
            timestamp_file = os.path.join(self.timestamp_dir, f"{date_str}.txt")
            
            
            # Formato: timestamp_epoch|timestamp_iso|cam_id|duration|status
            event_data = {
                "timestamp_epoch": int(current_time.timestamp()),
                "timestamp_iso": current_time.isoformat(),
                "cam_id": cam_id,
                "duration": duration,
                "status": "pending"
            }
            
            # Append ao arquivo do dia com file locking
            with self.timestamp_lock:
                with open(timestamp_file, "a") as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    try:
                        f.write(json.dumps(event_data) + "\n")
                        f.flush()
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
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
            with self.timestamp_lock:
                # Lê todas as linhas com file lock
                with open(timestamp_file, "r+") as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    try:
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
                            except (json.JSONDecodeError, KeyError):
                                # Mantém linha inválida como está
                                updated_lines.append(line)
                        
                        # Reescreve o arquivo
                        f.seek(0)
                        f.truncate()
                        f.writelines(updated_lines)
                        f.flush()
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    
        except Exception as e:
            print(f"Erro ao atualizar status do evento: {e}")

    def _extract_video_from_timestamp(self, timestamp_epoch, cam_id, duration=10):
        """Extrai vídeo com duração especificada baseado no timestamp.
        
        Args:
            timestamp_epoch: Timestamp Unix do evento
            cam_id: ID da câmera (0 ou 1)
            duration: Duração do vídeo em segundos (padrão: 10)
            
        Returns:
            str: Caminho do arquivo de vídeo extraído, ou None se falhar
        """
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
            # Segmentos de 1 minuto, busca 6 horas antes e 1 minuto depois
            search_start = event_time - timedelta(hours=6)
            search_end = event_time + timedelta(minutes=1)
            
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
            SEGMENT_DURATION_SECONDS = 60  # FFmpeg configurado com segment_time=60 (1 minuto)
            
            for filepath, file_time in segment_files:
                # Cada arquivo tem 60 segundos (1 minuto)
                file_end_time = file_time + timedelta(seconds=SEGMENT_DURATION_SECONDS)
                # print(f"DEBUG: Verificando arquivo {os.path.basename(filepath)}: {file_time} até {file_end_time}")
                if file_time <= event_time <= file_end_time:
                    target_file = filepath
                    file_start_time = file_time
                    print(f"DEBUG: Arquivo encontrado! {os.path.basename(filepath)}")
                    break
            
            if not target_file:
                # Se não encontrar exato, pega o mais próximo que seja ANTERIOR ao evento
                # (não podemos usar arquivo que ainda não existe)
                valid_files = [(fp, ft) for fp, ft in segment_files if ft <= event_time]
                if not valid_files:
                    print(f"ERRO: Nenhum arquivo anterior ao evento {event_time} encontrado")
                    return False
                
                print(f"DEBUG: Nenhum arquivo exato, pegando o mais próximo anterior")
                closest = min(valid_files, key=lambda x: abs((x[1] - event_time).total_seconds()))
                target_file = closest[0]
                file_start_time = closest[1]
                print(f"DEBUG: Arquivo mais próximo: {os.path.basename(target_file)}, início: {file_start_time}")
                
                # Verifica se o evento está muito longe do arquivo
                time_diff = (event_time - file_start_time).total_seconds()
                if time_diff > 600:  # Mais de 10 minutos de diferença
                    print(f"ERRO: Evento muito distante do arquivo mais próximo ({time_diff:.0f}s)")
                    return False
            
            # Verifica se o arquivo está completo (não está sendo escrito)
            file_size = os.path.getsize(target_file)
            file_age = time.time() - os.path.getmtime(target_file)
            
            print(f"INFO: Arquivo selecionado: {os.path.basename(target_file)}")
            print(f"      Tamanho: {file_size} bytes, idade mtime: {file_age:.1f}s")
            print(f"      Início do segmento: {file_start_time}")
            print(f"      Idade desde início: {(time.time() - file_start_time.timestamp()):.0f}s")
            
            # Verifica se é o arquivo mais recente (provavelmente ainda sendo escrito)
            # Com segment_time=60, aguarda pelo menos 65s após início do segmento
            is_current_segment = (time.time() - file_start_time.timestamp()) < (SEGMENT_DURATION_SECONDS + 5)
            
            if is_current_segment:
                print(f"AVISO: Arquivo {os.path.basename(target_file)} é o segmento atual (ainda sendo escrito pelo FFmpeg)")
                print(f"       Idade do segmento: {(time.time() - file_start_time.timestamp()):.0f}s / {SEGMENT_DURATION_SECONDS}s")
                print(f"       Aguarde até que o segmento seja finalizado (próximos {SEGMENT_DURATION_SECONDS - (time.time() - file_start_time.timestamp()):.0f}s)")
                return False
            
            if file_size < 100000:  # Menos de 100KB, provavelmente corrompido
                print(f"AVISO: Arquivo {os.path.basename(target_file)} muito pequeno ({file_size} bytes), pode estar incompleto")
                return False
            
            # Aguarda pelo menos 15 segundos após a última modificação para garantir que foi finalizado
            if file_age < 15:
                print(f"AVISO: Arquivo {os.path.basename(target_file)} muito recente ({file_age:.1f}s), aguardar mais tempo antes de processar")
                return False
            
            # Calcula o offset dentro do arquivo
            # IMPORTANTE: Com reset_timestamps=1 no FFmpeg, cada arquivo inicia em 0
            # Então o offset é: (event_time - file_start_time)
            # E queremos metade da duração ANTES do evento até metade DEPOIS
            offset_in_file = (event_time - file_start_time).total_seconds()
            seconds_before = duration / 2  # Metade antes do evento
            offset_seconds = max(0, offset_in_file - seconds_before)
            
            # Verifica se o evento está realmente dentro do arquivo (com margem para o clipe)
            if offset_seconds > (SEGMENT_DURATION_SECONDS - duration):  # Deixa margem da duração
                print(f"ERRO: Offset {offset_seconds:.2f}s muito grande para arquivo de {SEGMENT_DURATION_SECONDS}s (duração: {duration}s)")
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
            
            # Extrai vídeo com duração especificada usando ffmpeg
            # -ss APÓS -i para seeking preciso (evita duração 0)
            extract_cmd = [
                "ffmpeg", "-y",
                "-i", target_file,
                "-ss", str(offset_seconds),
                "-t", str(duration),  # Duração dinâmica
                "-c:v", "copy",
                "-avoid_negative_ts", "make_zero",
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
            
            # Lê todos os eventos do arquivo com file locking
            with self.timestamp_lock:
                with open(timestamp_file, "r") as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # Shared lock para leitura
                    try:
                        lines = f.readlines()
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            # Processa os eventos fora do lock para não bloquear outras operações
            for line in lines:
                line = line.strip()
                if line:
                    try:
                        event = json.loads(line)
                        if event.get("status") == "pending":
                            duration = event.get("duration", 10)  # Padrão 10s se não especificado
                            success = self._extract_video_from_timestamp(
                                timestamp_epoch=event["timestamp_epoch"],
                                cam_id=event["cam_id"],
                                duration=duration
                            )
                            
                            if success:
                                self._update_event_status(timestamp_file, event, "processed")
                                processed += 1
                            else:
                                self._update_event_status(timestamp_file, event, "failed")
                                failed += 1
                    except json.JSONDecodeError as e:
                        print(f"Erro ao processar linha (JSON inválido): {line[:50]}... - {e}")
                        failed += 1
                    except KeyError as e:
                        print(f"Erro ao processar linha (campo faltando): {line[:50]}... - {e}")
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
