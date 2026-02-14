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
        
        # Mapeia device_number para o device path usado
        self.device_paths = {}  # {0: '/dev/video0', 1: '/dev/video2'}
        
        # Lock para operações no arquivo de timestamps
        self.timestamp_lock = threading.Lock()

        # Diretório para armazenar os arquivos de timestamp
        self.timestamp_dir = os.path.join(stream_dir, "timestamps")
        os.makedirs(self.timestamp_dir, exist_ok=True)
        
        # Flag para indicar se há processamento em andamento
        self.is_processing = False
        self.processing_lock = threading.Lock()
        
        # Watchdog thread para monitorar saúde dos processos
        self.watchdog_running = False
        self.watchdog_thread = None
    
    def detect_usb_cameras(self):
        """
        Retorna os dispositivos fixos de câmera USB.
        Sempre usa /dev/video0 e /dev/video2 como dispositivos primários.
        """
        cameras = {}
        
        # Configuração fixa dos dispositivos de vídeo
        fixed_devices = {
            0: '/dev/video0',  # stream1
            1: '/dev/video2'   # stream2
        }
        
        # Verifica se os dispositivos existem
        for idx, device_path in fixed_devices.items():
            if os.path.exists(device_path):
                cameras[idx] = device_path
                print(f"Câmera {idx}: {device_path}")
            else:
                print(f"AVISO: Dispositivo {device_path} não encontrado!")
        
        if not cameras:
            print("ERRO: Nenhum dispositivo de vídeo encontrado!")
        
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
            self.device_paths[device_number] = DEVICE  # Armazena o device path
            print(f"Usando câmera {device_number}: {DEVICE}")
        else:
            # Para RTSP, usa o stream fornecido
            DEVICE = stream
            self.device_paths[device_number] = DEVICE  # Armazena o stream path
        
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
            "-c:v", "copy",
            "-ignore_io_errors", "1",
            "-f", "tee",
            (
                f"[f=flv:onfail=ignore]"
                f"rtmp://localhost/live/{STREAM_NAME}|"
                f"[f=segment:segment_time=60:segment_atclocktime=1:segment_clocktime_offset=0:reset_timestamps=1:avoid_negative_ts=make_zero:segment_format=mpegts:strftime=1:segment_wrap=18000]"
                f"{DISK_DIR}/{PREFIX}_%Y%m%d_%H%M%S.ts"
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
            "-c:v", "copy",
            "-ignore_io_errors", "1",
            "-f", "tee",
            (
                f"[f=flv:onfail=ignore]"
                f"rtmp://localhost/live/{STREAM_NAME}|"
                f"[f=segment:segment_time=60:segment_atclocktime=1:segment_clocktime_offset=0:reset_timestamps=1:avoid_negative_ts=make_zero:segment_format=mp4:strftime=1:segment_wrap=18000]"
                f"{DISK_DIR}/{PREFIX}_%Y%m%d_%H%M%S.mp4"
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
        
        # Inicia watchdog se ainda não estiver rodando
        if not self.watchdog_running:
            self.start_watchdog()

    def stop_ffmpeg_processes(self):
        """Finaliza os processos ffmpeg e limpa processos zumbis de forma robusta."""
        try:
            print("🛑 Iniciando finalização de processos FFmpeg...")
            
            # Para o watchdog primeiro
            self.watchdog_running = False
            if self.watchdog_thread:
                self.watchdog_thread.join(timeout=2)
            
            # Lista para armazenar PIDs que precisamos garantir que morreram
            pids_to_kill = []
            
            # Finaliza processo 0
            if self.ffmpeg_process_0:
                try:
                    pid = self.ffmpeg_process_0.pid
                    pgid = os.getpgid(pid)
                    pids_to_kill.append((pid, pgid))
                    
                    print(f"  → Finalizando processo 0 (PID {pid}, PGID {pgid})...")
                    os.killpg(pgid, signal.SIGTERM)
                    
                    # Aguarda até 3 segundos por finalização graceful
                    try:
                        self.ffmpeg_process_0.wait(timeout=3)
                        print(f"  ✓ Processo 0 finalizado gracefully")
                    except subprocess.TimeoutExpired:
                        print(f"  ⚠ Processo 0 não finalizou, forçando SIGKILL...")
                        os.killpg(pgid, signal.SIGKILL)
                        self.ffmpeg_process_0.wait(timeout=2)
                        print(f"  ✓ Processo 0 finalizado forçadamente")
                        
                except ProcessLookupError:
                    print(f"  ℹ Processo 0 já estava morto")
                except Exception as e:
                    print(f"  ✗ Erro ao finalizar processo 0: {e}")
                        
            # Finaliza processo 1
            if self.ffmpeg_process_1:
                try:
                    pid = self.ffmpeg_process_1.pid
                    pgid = os.getpgid(pid)
                    pids_to_kill.append((pid, pgid))
                    
                    print(f"  → Finalizando processo 1 (PID {pid}, PGID {pgid})...")
                    os.killpg(pgid, signal.SIGTERM)
                    
                    # Aguarda até 3 segundos por finalização graceful
                    try:
                        self.ffmpeg_process_1.wait(timeout=3)
                        print(f"  ✓ Processo 1 finalizado gracefully")
                    except subprocess.TimeoutExpired:
                        print(f"  ⚠ Processo 1 não finalizou, forçando SIGKILL...")
                        os.killpg(pgid, signal.SIGKILL)
                        self.ffmpeg_process_1.wait(timeout=2)
                        print(f"  ✓ Processo 1 finalizado forçadamente")
                        
                except ProcessLookupError:
                    print(f"  ℹ Processo 1 já estava morto")
                except Exception as e:
                    print(f"  ✗ Erro ao finalizar processo 1: {e}")
            
            # Garante que todos os processos FFmpeg relacionados foram mortos
            print("  → Limpando processos FFmpeg órfãos...")
            try:
                # Busca por processos ffmpeg que estejam usando os dispositivos de vídeo
                result = subprocess.run(
                    ["pgrep", "-f", "ffmpeg.*video"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                
                if result.stdout.strip():
                    orphan_pids = result.stdout.strip().split('\n')
                    print(f"  ⚠ Encontrados {len(orphan_pids)} processos FFmpeg órfãos: {orphan_pids}")
                    
                    # Tenta SIGTERM primeiro
                    subprocess.run(["pkill", "-15", "-f", "ffmpeg.*video"], timeout=2)
                    time.sleep(1)
                    
                    # Verifica se ainda existem
                    result = subprocess.run(
                        ["pgrep", "-f", "ffmpeg.*video"],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    
                    if result.stdout.strip():
                        print(f"  ⚠ Processos órfãos resistentes, usando SIGKILL...")
                        subprocess.run(["pkill", "-9", "-f", "ffmpeg.*video"], timeout=2)
                        time.sleep(0.5)
                else:
                    print(f"  ✓ Nenhum processo FFmpeg órfão encontrado")
                    
            except Exception as e:
                print(f"  ⚠ Erro ao limpar órfãos: {e}")
            
            # Limpa processos zumbis
            self._cleanup_zombie_processes()
            
            # Aguarda um pouco para garantir que dispositivos foram liberados
            time.sleep(1)
            
            print("✅ Finalização de processos FFmpeg concluída")
            
        except Exception as e:
            print(f"❌ Erro ao finalizar os processos do ffmpeg: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.ffmpeg_process_0 = None
            self.ffmpeg_process_1 = None

    def _cleanup_zombie_processes(self):
        """Limpa processos zumbis (defunct) reapando os filhos mortos."""
        try:
            import signal
            # Reapar todos os processos filhos mortos sem bloquear
            while True:
                try:
                    pid, status = os.waitpid(-1, os.WNOHANG)
                    if pid == 0:
                        break  # Não há mais processos para reapar
                    print(f"Processo zumbi {pid} limpo (exit status: {status})")
                except ChildProcessError:
                    break  # Não há mais filhos
        except Exception as e:
            print(f"Erro ao limpar processos zumbis: {e}")
    
    def check_process_health(self, device_number):
        """Verifica se o processo FFmpeg está rodando e saudável.
        
        Returns:
            bool: True se o processo está saudável, False caso contrário
        """
        process = self.ffmpeg_process_0 if device_number == 0 else self.ffmpeg_process_1
        
        if process is None:
            return False
        
        # Verifica se o processo ainda está vivo
        poll_result = process.poll()
        if poll_result is not None:
            print(f"⚠️ ALERTA: Processo FFmpeg device{device_number} morreu com código {poll_result}")
            return False
        
        # Verifica se está gerando arquivos recentemente (últimos 5 minutos)
        if device_number == 0:
            disk_dir = "/media/pi/usb64gb/bts/stream1"
            prefix = "video0"
        else:
            disk_dir = "/media/pi/usb64gb/bts/stream2"
            prefix = "video2"
        
        try:
            # Lista arquivos recentes (suporta .mp4 e .ts)
            files = [f for f in os.listdir(disk_dir) if f.startswith(prefix) and (f.endswith(".mp4") or f.endswith(".ts"))]
            if files:
                # Pega o arquivo mais recente
                latest_file = max([os.path.join(disk_dir, f) for f in files], key=os.path.getmtime)
                file_age = time.time() - os.path.getmtime(latest_file)
                file_size = os.path.getsize(latest_file)
                
                # Se o arquivo mais recente tem mais de 5 minutos, algo está errado
                if file_age > 300:  # 5 minutos
                    print(f"⚠️ ALERTA: Último arquivo de device{device_number} tem {file_age:.0f}s (>5min)")
                    return False
                
                # Se o arquivo mais recente tem 0 bytes e mais de 10 segundos, algo está errado
                if file_size == 0 and file_age > 10:
                    print(f"⚠️ ALERTA: Arquivo mais recente está vazio há {file_age:.0f}s")
                    return False
            else:
                print(f"⚠️ ALERTA: Nenhum arquivo encontrado para device{device_number}")
                return False
                
        except Exception as e:
            print(f"Erro ao verificar saúde de device{device_number}: {e}")
            return False
        
        return True
    
    def restart_dead_process(self, device_number):
        """Reinicia um processo FFmpeg morto de forma robusta.
        
        Args:
            device_number: 0 ou 1
        """
        print(f"🔄 Reiniciando processo FFmpeg para device{device_number}...")
        
        # Log de restart
        try:
            timestamp = datetime.now().isoformat()
            log_file = "/media/pi/usb64gb/bts/ffmpeg_restart_log.txt"
            with open(log_file, "a") as f:
                f.write(f"{timestamp} - Restarting device {device_number}\n")
        except Exception as e:
            print(f"Aviso: Não foi possível logar restart: {e}")
        
        try:
            # Limpa processos zumbis primeiro
            self._cleanup_zombie_processes()
            
            # Finaliza o processo antigo de forma robusta
            process = self.ffmpeg_process_0 if device_number == 0 else self.ffmpeg_process_1
            if process:
                try:
                    pid = process.pid
                    pgid = os.getpgid(pid)
                    print(f"  → Finalizando processo antigo (PID {pid}, PGID {pgid})...")
                    
                    # Tenta SIGTERM primeiro
                    os.killpg(pgid, signal.SIGTERM)
                    try:
                        process.wait(timeout=2)
                        print(f"  ✓ Processo antigo finalizado gracefully")
                    except subprocess.TimeoutExpired:
                        print(f"  ⚠ Forçando SIGKILL...")
                        os.killpg(pgid, signal.SIGKILL)
                        process.wait(timeout=1)
                        
                except ProcessLookupError:
                    print(f"  ℹ Processo antigo já estava morto")
                except Exception as e:
                    print(f"  ⚠ Erro ao finalizar processo antigo: {e}")
            
            # Reseta o processo
            if device_number == 0:
                self.ffmpeg_process_0 = None
            else:
                self.ffmpeg_process_1 = None
            
            # Verifica se o dispositivo está sendo usado por algum processo órfão
            device_path = self.device_paths.get(device_number)
            if device_path and device_path.startswith("/dev/"):
                print(f"  → Verificando se {device_path} está livre...")
                
                # Busca processos usando este dispositivo específico
                try:
                    result = subprocess.run(
                        ["fuser", device_path],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    
                    if result.returncode == 0 and result.stdout.strip():
                        orphan_pids = result.stdout.strip().split()
                        print(f"  ⚠ Dispositivo em uso por PIDs: {orphan_pids}")
                        print(f"  → Finalizando processos órfãos...")
                        
                        for pid in orphan_pids:
                            try:
                                subprocess.run(["kill", "-9", pid], timeout=1)
                            except:
                                pass
                        
                        time.sleep(0.5)
                        print(f"  ✓ Processos órfãos finalizados")
                    else:
                        print(f"  ✓ Dispositivo livre")
                        
                except Exception as e:
                    print(f"  ⚠ Erro ao verificar dispositivo: {e}")
                
                # Verifica se o dispositivo existe
                if not os.path.exists(device_path):
                    print(f"❌ ERRO: Dispositivo {device_path} não existe! Câmera desconectada?")
                    # Tenta re-detectar as câmeras
                    print("🔍 Tentando re-detectar câmeras...")
                    self.detected_cameras = self.detect_usb_cameras()
                    if device_number not in self.detected_cameras:
                        print(f"❌ Câmera {device_number} não foi detectada após re-scan")
                        return False
                    # Atualiza o device_path com o novo detectado
                    device_path = self.detected_cameras[device_number]
                    self.device_paths[device_number] = device_path
                    print(f"✓ Câmera re-detectada: {device_path}")
            
            # Aguarda um pouco para garantir que o dispositivo está disponível
            time.sleep(1)
            
            # Reinicia o processo
            input_source = "rtsp" if device_path and device_path.startswith("rtsp") else "usb"
            self.start_ffmpeg_processes(device_number=device_number, input_source=input_source, stream=device_path or "")
            
            print(f"✅ Processo FFmpeg device{device_number} reiniciado com sucesso")
            return True
            
        except Exception as e:
            print(f"❌ ERRO ao reiniciar processo device{device_number}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def start_watchdog(self):
        """Inicia thread de monitoramento dos processos FFmpeg."""
        if self.watchdog_running:
            return
        
        self.watchdog_running = True
        self.watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self.watchdog_thread.start()
        print("🐕 Watchdog de processos FFmpeg iniciado")
    
    def _watchdog_loop(self):
        """Loop principal do watchdog que monitora os processos."""
        check_interval = 60  # Verifica a cada 60 segundos
        
        while self.watchdog_running:
            try:
                # Verifica device 0
                if self.ffmpeg_process_0 is not None:
                    if not self.check_process_health(0):
                        print("🚨 Device 0 não está saudável, tentando restart...")
                        self.restart_dead_process(0)
                
                # Verifica device 1
                if self.ffmpeg_process_1 is not None:
                    if not self.check_process_health(1):
                        print("🚨 Device 1 não está saudável, tentando restart...")
                        self.restart_dead_process(1)
                
                # Limpa zumbis periodicamente
                self._cleanup_zombie_processes()
                
                # Limpa arquivos 0-byte periodicamente
                self._cleanup_empty_segments()
                
            except Exception as e:
                print(f"Erro no watchdog: {e}")
                import traceback
                traceback.print_exc()
            
            # Aguarda antes da próxima verificação
            for _ in range(check_interval):
                if not self.watchdog_running:
                    break
                time.sleep(1)
        
        print("🐕 Watchdog de processos FFmpeg finalizado")
    
    def _cleanup_empty_segments(self):
        """Remove arquivos .ts e .mp4 com 0 bytes que indicam segmentos corrompidos."""
        try:
            cleaned_count = 0
            for disk_dir in ["/media/pi/usb64gb/bts/stream1", "/media/pi/usb64gb/bts/stream2"]:
                if not os.path.exists(disk_dir):
                    continue
                    
                for filename in os.listdir(disk_dir):
                    if filename.endswith('.ts') or filename.endswith('.mp4'):
                        filepath = os.path.join(disk_dir, filename)
                        try:
                            # Remove se o arquivo tem 0 bytes e tem mais de 60 segundos
                            file_size = os.path.getsize(filepath)
                            file_age = time.time() - os.path.getmtime(filepath)
                            
                            if file_size == 0 and file_age > 60:
                                print(f"🧹 Removendo arquivo vazio: {filename}")
                                os.remove(filepath)
                                cleaned_count += 1
                        except Exception as e:
                            print(f"Erro ao limpar {filename}: {e}")
            
            if cleaned_count > 0:
                print(f"🧹 Limpeza concluída: {cleaned_count} arquivo(s) vazio(s) removido(s)")
                
        except Exception as e:
            print(f"Erro na limpeza de arquivos vazios: {e}")

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
                                # Compara timestamp_epoch, cam_id, duration e timestamp_iso para garantir unicidade
                                if (current_event["timestamp_epoch"] == event["timestamp_epoch"] and 
                                    current_event["cam_id"] == event["cam_id"] and
                                    current_event.get("duration", 10) == event.get("duration", 10) and
                                    current_event["timestamp_iso"] == event["timestamp_iso"]):
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
        Busca nos arquivos de segmento de 1 minuto.
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
            
            # Lista todos os arquivos de segmento do disco (suporta .mp4 e .ts)
            segment_files = []
            if os.path.exists(DISK_DIR):
                for filename in os.listdir(DISK_DIR):
                    if filename.startswith(PREFIX) and (filename.endswith(".mp4") or filename.endswith(".ts")):
                        try:
                            # Parse do timestamp do nome do arquivo: video0_20260208_131022.mp4 ou .ts
                            # Formato: PREFIX_YYYYMMDD_HHMMSS.mp4 ou .ts
                            timestamp_part = filename.replace(f"{PREFIX}_", "").replace(".mp4", "").replace(".ts", "")
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
            
            # Valida integridade do arquivo verificando se pode ser lido
            try:
                probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", target_file]
                probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=15)
                if probe_result.returncode != 0 or not probe_result.stdout.strip():
                    print(f"ERRO: Arquivo {os.path.basename(target_file)} corrompido ou ilegível (ffprobe falhou)")
                    return False
                file_duration = float(probe_result.stdout.strip())
                if file_duration < 10:  # Arquivo de 60s deveria ter pelo menos 10s de conteúdo válido
                    print(f"AVISO: Arquivo {os.path.basename(target_file)} tem duração muito curta ({file_duration:.1f}s), pode estar corrompido")
                    return False
            except (subprocess.TimeoutExpired, ValueError, Exception) as e:
                print(f"ERRO: Falha ao validar arquivo {os.path.basename(target_file)}: {e}")
                return False
            
            # Calcula o offset dentro do arquivo
            # IMPORTANTE: Com reset_timestamps=1 no FFmpeg, cada arquivo inicia em 0
            # Então o offset é: (event_time - file_start_time)
            # Queremos recuperar TODA a duração ANTES do evento (ex: últimos 10s ou 15s)
            offset_in_file = (event_time - file_start_time).total_seconds()
            seconds_before = duration  # Toda a duração antes do evento
            
            # EDGE CASE: Evento ocorre muito cedo no arquivo (menos de 'duration' segundos do início)
            # Precisamos buscar conteúdo do arquivo ANTERIOR para completar a duração
            previous_file = None
            needs_previous_file = offset_in_file < duration
            
            if needs_previous_file:
                missing_seconds = duration - offset_in_file
                print(f"INFO: Evento ocorre em {offset_in_file:.1f}s do início do arquivo.")
                print(f"      Faltam {missing_seconds:.1f}s para completar {duration}s. Buscando arquivo anterior...")
                
                # Busca o arquivo anterior (1 minuto antes)
                previous_file_start = file_start_time - timedelta(seconds=SEGMENT_DURATION_SECONDS)
                previous_file_path = None
                
                # Tenta encontrar o arquivo anterior (mp4 ou ts)
                for ext in [".mp4", ".ts"]:
                    prev_filename = previous_file_start.strftime(f"{PREFIX}_%Y%m%d_%H%M%S{ext}")
                    candidate_path = os.path.join(DISK_DIR, prev_filename)
                    if os.path.exists(candidate_path):
                        previous_file_path = candidate_path
                        break
                
                if previous_file_path and os.path.exists(previous_file_path):
                    # Verifica se o arquivo anterior está completo
                    prev_age = time.time() - os.path.getmtime(previous_file_path)
                    prev_size = os.path.getsize(previous_file_path)
                    
                    if prev_age < 15:
                        print(f"ERRO: Arquivo anterior muito recente ({prev_age:.1f}s), aguardar mais tempo")
                        return False
                    
                    if prev_size < 100000:
                        print(f"ERRO: Arquivo anterior muito pequeno ({prev_size} bytes), pode estar corrompido")
                        return False
                    
                    # Valida continuidade temporal: arquivo anterior deve estar no máximo 90s antes
                    # (normal seria 60s, mas dá margem para pequenos atrasos na gravação)
                    time_gap = (file_start_time - previous_file_start).total_seconds()
                    if time_gap > 90:  # Mais de 90 segundos indica gap na gravação
                        print(f"AVISO: Gap detectado entre arquivos ({time_gap:.0f}s > 90s).")
                        print(f"       Arquivo anterior muito distante. Usando apenas conteúdo disponível desde início.")
                        print(f"       Vídeo terá {offset_in_file:.1f}s ao invés de {duration}s")
                        # Não usa o arquivo anterior, apenas o conteúdo atual
                    else:
                        previous_file = previous_file_path
                        print(f"      Arquivo anterior encontrado: {os.path.basename(previous_file)}")
                        print(f"      Continuidade temporal validada: {time_gap:.0f}s entre arquivos")
                else:
                    print(f"AVISO: Arquivo anterior não encontrado. Usando conteúdo disponível desde início.")
                    print(f"       Vídeo terá {offset_in_file:.1f}s ao invés de {duration}s")
                    # Continua mesmo sem arquivo anterior, recuperando o máximo possível
            
            # Calcula offset para extração
            if needs_previous_file and previous_file:
                # Vai extrair do arquivo anterior + arquivo atual
                offset_seconds = 0  # Do arquivo atual, pega desde o início até o evento
            else:
                # Extração normal: subtrai a duração do offset
                offset_seconds = max(0, offset_in_file - seconds_before)
            
            # Se não há arquivo anterior mas precisa, ajusta a duração efetiva
            effective_duration = duration
            if needs_previous_file and not previous_file:
                # Só há conteúdo desde o início do arquivo até o evento
                effective_duration = offset_in_file
                print(f"      Ajustando duração para {effective_duration:.1f}s (conteúdo disponível desde início do arquivo)")
            
            # Verifica se há conteúdo suficiente no arquivo (para eventos no FINAL)
            available_content = SEGMENT_DURATION_SECONDS - offset_seconds
            needs_concatenation = available_content < effective_duration
            next_file = None
            
            if needs_concatenation:
                print(f"INFO: Evento próximo ao final. Disponível: {available_content:.1f}s, necessário: {effective_duration}s")
                print(f"      Buscando próximo segmento para concatenação...")
                
                # Busca o próximo arquivo de segmento (tenta .mp4 e .ts)
                next_file_start = file_start_time + timedelta(seconds=SEGMENT_DURATION_SECONDS)
                next_file_path = None
                # Tenta encontrar o próximo arquivo (mp4 ou ts)
                for ext in [".mp4", ".ts"]:
                    next_filename = next_file_start.strftime(f"{PREFIX}_%Y%m%d_%H%M%S{ext}")
                    candidate_path = os.path.join(DISK_DIR, next_filename)
                    if os.path.exists(candidate_path):
                        next_file_path = candidate_path
                        break
                
                if next_file_path and os.path.exists(next_file_path):
                    # Verifica se o próximo arquivo não é o segmento atual
                    next_age = time.time() - os.path.getmtime(next_file_path)
                    if next_age < 15:
                        print(f"ERRO: Próximo arquivo muito recente ({next_age:.1f}s), aguardar mais tempo")
                        return False
                    next_file = next_file_path
                    print(f"      Próximo segmento encontrado: {os.path.basename(next_file)}")
                else:
                    print(f"ERRO: Próximo segmento não encontrado (tentou .mp4 e .ts)")
                    return False
            
            # Verifica se o evento está realmente dentro do arquivo (com margem para o clipe)
            if not needs_concatenation and not needs_previous_file and offset_seconds > (SEGMENT_DURATION_SECONDS - effective_duration):
                print(f"ERRO: Offset {offset_seconds:.2f}s muito grande para arquivo de {SEGMENT_DURATION_SECONDS}s (duração: {effective_duration}s)")
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
            
            # Extração com diferentes cenários
            if needs_previous_file and previous_file:
                # CENÁRIO 1: Evento muito cedo - precisa arquivo ANTERIOR + arquivo atual
                missing_seconds = duration - offset_in_file
                print(f"Extraindo vídeo COM ARQUIVO ANTERIOR: {os.path.basename(previous_file)} + {os.path.basename(target_file)}")
                print(f"      Extraindo últimos {missing_seconds:.1f}s do anterior + primeiros {offset_in_file:.1f}s do atual")
                
                temp_prev = os.path.join("/tmp", f"prev_{timestamp_str}.mp4")
                temp_curr = os.path.join("/tmp", f"curr_{timestamp_str}.mp4")
                concat_list = os.path.join("/tmp", f"concat_{timestamp_str}.txt")
                
                try:
                    # Parte 1: Últimos N segundos do arquivo anterior
                    # Arquivo anterior tem 60s, queremos os últimos 'missing_seconds' segundos
                    prev_start_offset = SEGMENT_DURATION_SECONDS - missing_seconds
                    cmd_prev = ["ffmpeg", "-y", "-i", previous_file, "-ss", str(prev_start_offset), "-t", str(missing_seconds), "-c:v", "copy", temp_prev]
                    result_prev = subprocess.run(cmd_prev, capture_output=True, text=True, timeout=30)
                    if result_prev.returncode != 0:
                        print(f"ERRO ao extrair do arquivo anterior: {result_prev.stderr}")
                        return False
                    
                    # Parte 2: Do início do arquivo atual até o evento
                    cmd_curr = ["ffmpeg", "-y", "-i", target_file, "-t", str(offset_in_file), "-c:v", "copy", temp_curr]
                    result_curr = subprocess.run(cmd_curr, capture_output=True, text=True, timeout=30)
                    if result_curr.returncode != 0:
                        print(f"ERRO ao extrair do arquivo atual: {result_curr.stderr}")
                        return False
                    
                    # Cria lista para concatenação
                    with open(concat_list, "w") as f:
                        f.write(f"file '{temp_prev}'\n")
                        f.write(f"file '{temp_curr}'\n")
                    
                    # Concatena as partes
                    extract_cmd = [
                        "ffmpeg", "-y",
                        "-f", "concat",
                        "-safe", "0",
                        "-i", concat_list,
                        "-c", "copy",
                        "-avoid_negative_ts", "make_zero",
                        "-movflags", "+faststart",
                        output_file
                    ]
                    
                    result = subprocess.run(extract_cmd, capture_output=True, text=True, timeout=30)
                    
                finally:
                    # Remove arquivos temporários
                    for temp_file in [temp_prev, temp_curr, concat_list]:
                        try:
                            if os.path.exists(temp_file):
                                os.remove(temp_file)
                        except:
                            pass
                    
            elif needs_concatenation and next_file:
                # CENÁRIO 2: Evento muito tarde - precisa arquivo atual + arquivo SEGUINTE
                print(f"Extraindo vídeo COM CONCATENAÇÃO: {os.path.basename(target_file)} + {os.path.basename(next_file)}")
                
                # Extrai de cada arquivo separadamente
                temp_part1 = os.path.join("/tmp", f"part1_{timestamp_str}.mp4")
                temp_part2 = os.path.join("/tmp", f"part2_{timestamp_str}.mp4")
                concat_list = os.path.join("/tmp", f"concat_{timestamp_str}.txt")
                
                try:
                    # Parte 1: do offset até o final do primeiro arquivo
                    cmd_part1 = ["ffmpeg", "-y", "-i", target_file, "-ss", str(offset_seconds), "-c:v", "copy", temp_part1]
                    result1 = subprocess.run(cmd_part1, capture_output=True, text=True, timeout=30)
                    if result1.returncode != 0:
                        print(f"ERRO ao extrair parte 1: {result1.stderr}")
                        return False
                    
                    # Parte 2: do início do próximo arquivo até completar a duração
                    remaining_duration = effective_duration - available_content
                    cmd_part2 = ["ffmpeg", "-y", "-i", next_file, "-t", str(remaining_duration), "-c:v", "copy", temp_part2]
                    result2 = subprocess.run(cmd_part2, capture_output=True, text=True, timeout=30)
                    if result2.returncode != 0:
                        print(f"ERRO ao extrair parte 2: {result2.stderr}")
                        return False
                    
                    # Cria lista para concatenação
                    with open(concat_list, "w") as f:
                        f.write(f"file '{temp_part1}'\n")
                        f.write(f"file '{temp_part2}'\n")
                    
                    # Concatena as partes
                    extract_cmd = [
                        "ffmpeg", "-y",
                        "-f", "concat",
                        "-safe", "0",
                        "-i", concat_list,
                        "-c", "copy",
                        "-avoid_negative_ts", "make_zero",
                        "-movflags", "+faststart",
                        output_file
                    ]
                    
                    result = subprocess.run(extract_cmd, capture_output=True, text=True, timeout=30)
                    
                finally:
                    # Remove arquivos temporários
                    for temp_file in [temp_part1, temp_part2, concat_list]:
                        try:
                            if os.path.exists(temp_file):
                                os.remove(temp_file)
                        except:
                            pass
                    
            else:
                # CENÁRIO 3: Evento normal no meio do arquivo - extração simples
                extract_cmd = [
                    "ffmpeg", "-y",
                    "-i", target_file,
                    "-ss", str(offset_seconds),
                    "-t", str(effective_duration),
                    "-c:v", "copy",
                    "-avoid_negative_ts", "make_zero",
                    "-movflags", "+faststart",
                    output_file
                ]
                print(f"Extraindo vídeo: arquivo={os.path.basename(target_file)}, offset={offset_seconds:.2f}s, duração={effective_duration}s")
                print(f"      Recuperando {effective_duration}s ANTES do evento (de {offset_seconds:.2f}s até {offset_seconds + effective_duration:.2f}s)")
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

    def manual_process_timestamps(self, date_str=None, days_back=3, max_events=None):
        """
        Inicia o processamento de timestamps em background.
        Retorna imediatamente sem bloquear a requisição HTTP.
        Processa TODOS os eventos pending até o fim.
        """
        with self.processing_lock:
            if self.is_processing:
                return {
                    "status": "already_processing",
                    "message": "Já existe um processamento em andamento"
                }
            self.is_processing = True
        
        # Inicia thread em background
        thread = threading.Thread(
            target=self._process_all_pending_background,
            args=(date_str, days_back),
            daemon=False  # Não é daemon para garantir que termine
        )
        thread.start()
        
        return {
            "status": "started",
            "message": "Processamento iniciado em background. Todos os pending serão processados."
        }
    
    def _process_all_pending_background(self, date_str=None, days_back=3):
        """
        Método executado em background para processar TODOS os timestamps pending.
        Processa um evento por vez até finalizar todos.
        """
        try:
            print("[Background] Iniciando processamento de timestamps...")
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
                
                print(f"[Background] Processando timestamps de {current_date}...")
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
                
                # Processa TODOS os eventos pending (sem limite)
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
                                    
                                # Log de progresso
                                if (processed + failed) % 10 == 0:
                                    print(f"[Background] Progresso: {processed} processados, {failed} falharam")
                                    
                        except json.JSONDecodeError as e:
                            print(f"[Background] Erro ao processar linha (JSON inválido): {line[:50]}... - {e}")
                            failed += 1
                        except KeyError as e:
                            print(f"[Background] Erro ao processar linha (campo faltando): {line[:50]}... - {e}")
                            failed += 1
                        except Exception as e:
                            print(f"[Background] Erro ao processar linha: {e}")
                            failed += 1
                
                if processed > 0 or failed > 0:
                    dates_processed.append(current_date)
                    total_processed += processed
                    total_failed += failed
                    print(f"[Background] Data {current_date}: {processed} processados, {failed} falharam")
            
            print(f"[Background] Processamento concluído. Total: {total_processed} processados, {total_failed} falharam")
            
        except Exception as e:
            print(f"[Background] Erro durante processamento: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Marca como não processando
            with self.processing_lock:
                self.is_processing = False
            print("[Background] Flag de processamento liberada")
        
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
