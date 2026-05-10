import os
import signal
from datetime import datetime, timedelta
import subprocess
# from led_ws281x_new import blink_n_times, cleanup, start_blinking  # LED removido do projeto
import time
from database import get_db, Video, VideoStatus
import json
import threading
import re
import fcntl

device_name="rpi4bmobile"

class FFMpegManager:
    def __init__(self, buffer_dir_video0, buffer_dir_video2, final_dir, stream_dir):
        self.buffer_dir_video0 = buffer_dir_video0
        self.buffer_dir_video2 = buffer_dir_video2
        self.final_dir = final_dir
        self.stream_dir = stream_dir
        self.ffmpeg_process_0 = None
        self.ffmpeg_process_1 = None
        
        # Cache dos dispositivos detectados
        self.detected_cameras = {}
        
        # Mapeia device_number para o device path usado
        self.device_paths = {}  # {0: '/dev/video0', 1: '/dev/video2'}
        
        # Mapeia device_number para o tipo de input source ('usb' ou 'rtsp')
        self.input_sources = {}  # {0: 'rtsp', 1: 'rtsp'}
        
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
        # Controle de tentativas de restart/re-detecção
        self.last_restart_attempt = {0: 0, 1: 0}
        self.restart_cooldown_seconds = 10
    
    def _rotate_logs(self, log_dir, device_prefix, max_size_mb=5, max_files=3):
        """Rotaciona logs para evitar uso excessivo de espaço no USB.
        
        Args:
            log_dir: Diretório onde os logs estão armazenados
            device_prefix: Prefixo do arquivo (ex: 'device0', 'device2')
            max_size_mb: Tamanho máximo em MB antes de rotacionar
            max_files: Número máximo de arquivos antigos a manter
        """
        try:
            # Lista todos os logs deste dispositivo
            pattern = f"{device_prefix}_*.log"
            log_files = sorted(
                [f for f in os.listdir(log_dir) if f.startswith(device_prefix) and f.endswith('.log')],
                key=lambda x: os.path.getmtime(os.path.join(log_dir, x)),
                reverse=True  # Mais recente primeiro
            )
            
            # Remove logs além do limite de arquivos
            if len(log_files) > max_files:
                for old_log in log_files[max_files:]:
                    old_log_path = os.path.join(log_dir, old_log)
                    try:
                        os.remove(old_log_path)
                        print(f"  🗑️  Log antigo removido: {old_log}")
                    except Exception as e:
                        print(f"  ⚠️  Erro ao remover log {old_log}: {e}")
            
            # Verifica tamanho dos logs existentes
            for log_file in log_files[:max_files]:
                log_path = os.path.join(log_dir, log_file)
                try:
                    size_mb = os.path.getsize(log_path) / (1024 * 1024)
                    if size_mb > max_size_mb:
                        print(f"  ⚠️  Log {log_file} excede {max_size_mb}MB ({size_mb:.1f}MB)")
                except Exception:
                    pass
                    
        except Exception as e:
            print(f"Erro ao rotacionar logs: {e}")
    
    def detect_usb_cameras(self):
        """
        Detecta dinamicamente os dispositivos de câmera USB.
        NÃO assume números fixos (/dev/video0, /dev/video2, etc).
        
        Estratégia:
        1. Executa v4l2-ctl --list-devices
        2. Identifica blocos de câmeras USB (procura por "usb" no nome)
        3. Para cada bloco, pega apenas o primeiro /dev/videoX (câmera principal)
        4. Mapeia para índices 0 e 1
        
        Fallback: Se detectar < 2 câmeras, tenta dispositivos conhecidos (0,2) ou (0,3)
        """
        cameras = {}
        
        try:
            # Tenta detecção dinâmica com v4l2-ctl
            result = subprocess.run(
                ["v4l2-ctl", "--list-devices"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Processa output linha por linha
            lines = result.stdout.split('\n')
            usb_camera_devices = []
            current_device_type = None
            
            for line in lines:
                line_stripped = line.strip()
                
                # Identifica linhas que contêm "usb" (câmeras USB)
                if 'usb' in line.lower() and ':' in line:
                    # Nova câmera USB encontrada
                    current_device_type = 'usb'
                
                # Se estamos em um bloco USB e encontramos /dev/video
                if current_device_type == 'usb' and line_stripped.startswith('/dev/video'):
                    device_path = line_stripped
                    
                    # Verifica se é um número válido e se o dispositivo existe
                    try:
                        video_num = int(device_path.split('video')[1])
                        # Adiciona apenas o primeiro dispositivo de cada câmera USB
                        # (ignora o background que vem depois, ex: video0, video1 -> pega apenas video0)
                        if os.path.exists(device_path):
                            usb_camera_devices.append(device_path)
                            # Para esta câmera USB, vamos ignorar os próximos /dev/video da mesma câmera
                            # (identificamos isso pelo padrão sequencial video0/1, video2/3, etc)
                    except (ValueError, IndexError):
                        pass
                
                # Reset quando sai de uma câmera USB
                if current_device_type == 'usb' and line_stripped == '':
                    current_device_type = None
            
            # Pega apenas as câmeras principais (primeira de cada par)
            # Se temos video0/1 e video2/3, pega video0 e video2
            main_cameras = []
            seen_pairs = set()
            
            for device in usb_camera_devices:
                try:
                    video_num = int(device.split('video')[1])
                    # Cada par (video0/1, video2/3, etc) tem uma câmera principal
                    # Se é um número par, é câmera principal
                    # Se é ímpar, é background (pula)
                    if video_num % 2 == 0 and os.path.exists(device):
                        main_cameras.append(device)
                except (ValueError, IndexError):
                    pass
            
            # Mapeia para índices 0 e 1
            for idx, device_path in enumerate(main_cameras[:2]):  # Max 2 câmeras
                cameras[idx] = device_path
                print(f"Câmera {idx}: {device_path} (detectada dinamicamente via USB)")
            
            # Se encontrou as 2 câmeras esperadas, retorna
            if len(cameras) >= 2:
                return cameras
            
            # Se não encontrou 2 câmeras, tenta fallback
            if len(cameras) < 2:
                print(f"⚠️  Encontradas apenas {len(cameras)} câmera(s), tentando fallback...")
                raise Exception(f"Expected 2 cameras, found {len(cameras)}")
                
        except Exception as e:
            print(f"Detecção USB falhou: {e}")
            print("Tentando configuração de fallback com dispositivos fixos...")
            
            # Fallback 1: Tenta /dev/video0 e /dev/video2
            fixed_devices = {
                0: '/dev/video0',  # Primeira câmera
                1: '/dev/video2'   # Segunda câmera
            }
            
            for idx, device_path in fixed_devices.items():
                if os.path.exists(device_path):
                    cameras[idx] = device_path
                    print(f"Câmera {idx}: {device_path} (fallback 1: fixo)")
            
            # Fallback 2: Se video2 não existe, procura video3 em diante
            if 1 not in cameras:
                print("⚠️  /dev/video2 não encontrado, procurando alternativas...")
                for alt_video_num in range(3, 10):
                    alt_device = f'/dev/video{alt_video_num}'
                    if os.path.exists(alt_device):
                        # Testa se é realmente uma câmera
                        try:
                            test = subprocess.run(
                                ["v4l2-ctl", "-d", alt_device, "--list-formats"],
                                capture_output=True,
                                text=True,
                                timeout=2
                            )
                            if test.returncode == 0 and "PixelFormat" in test.stdout:
                                cameras[1] = alt_device
                                print(f"Câmera 1: {alt_device} (fallback 2: alternativa)")
                                break
                        except Exception:
                            pass
        
        if not cameras:
            print("❌ ERRO: Nenhum dispositivo de vídeo encontrado!")
        
        return cameras

    def start_ffmpeg_processes(self, device_number=0, input_source="usb", stream=""):
        # Armazena o tipo de input source para esta câmera
        self.input_sources[device_number] = input_source
        
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
        # Suporte para gravação em RAM via variáveis de ambiente
        if device_number == 0:
            PREFIX="video0"
            BUFFER_DIR = f"{self.buffer_dir_video0}"
            DISK_DIR = os.environ.get("BTS_STREAM1_DIR", "/home/pi/recordings/stream1")
        else:
            PREFIX="video2"
            BUFFER_DIR = f"{self.buffer_dir_video2}"
            DISK_DIR = os.environ.get("BTS_STREAM2_DIR", "/home/pi/recordings/stream2")
        
        # Cria diretório se não existir (importante para RAM)
        os.makedirs(DISK_DIR, exist_ok=True)
        
        # Indica se está usando RAM
        if DISK_DIR.startswith("/dev/shm"):
            print(f"⚡ MODO RAM: Gravando em {DISK_DIR} (alta performance)")
        else:
            print(f"💾 MODO DISCO: Gravando em {DISK_DIR}")
            
        STREAM_NAME = DISK_DIR.split('/')[-1]
        print(f"stream name: {STREAM_NAME}")
        print(f"Iniciando FFmpeg: device={DEVICE}, prefix={PREFIX}, dir={DISK_DIR}")

        cmd_usb = [
            "ffmpeg", "-rtbufsize","128M",  # 16s @ 8MB/s - otimizado para o bitrate
	    "-hide_banner","-loglevel","warning","-stats","-stats_period","30",
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
                f"[f=segment:segment_time=180:segment_atclocktime=1:segment_clocktime_offset=0:reset_timestamps=1:avoid_negative_ts=make_zero:segment_format=mpegts:strftime=1:segment_wrap=100]"
                f"{DISK_DIR}/{PREFIX}_%Y%m%d_%H%M%S.ts"
            )
        ]
        cmd_rtsp = [
            "ffmpeg",
            # Timeout e protocolo RTSP otimizado
            "-timeout", "10000000",  # 10s timeout para operações de rede (microsegundos)
            "-rtsp_transport", "tcp",  # TCP é mais confiável que UDP
            "-rtbufsize", "128M",  # 16s @ 8MB/s - otimizado para bitrate 6-8MB/s @ 25fps
            "-max_delay", "2000000",  # 2s de delay máximo (mais tolerante)
            "-hide_banner", "-loglevel", "warning", "-stats", "-stats_period", "30",
            # Flags de entrada com tratamento de erros
            "-fflags", "+genpts+discardcorrupt+igndts",
            "-err_detect", "ignore_err",  # Continua mesmo com erros menores
            "-analyzeduration", "5000000",  # 5s para analisar stream
            "-probesize", "10000000",  # 10MB para detectar propriedades
            "-i", f"{DEVICE}",
            # Timestamps e modo de frame
            "-use_wallclock_as_timestamps", "1",
            "-fps_mode", "passthrough",  # Mantém FPS original do stream
            # Mapeamento e codec (copy preserva qualidade original)
            "-map", "0:v",
            "-c:v", "copy",
            # Segmentos para gravação
            "-f", "segment",
            "-segment_time", "180",
            "-segment_atclocktime", "1",
            "-segment_clocktime_offset", "0",
            "-reset_timestamps", "1",
            "-avoid_negative_ts", "make_zero",
            "-segment_format", "mpegts",
            "-strftime", "1",
            "-segment_wrap", "1400",
            f"{DISK_DIR}/{PREFIX}_%Y%m%d_%H%M%S.ts"
        ]

        """Inicia os processos ffmpeg com buffer circular."""
        # Configura logs no USB com rotação automática
        log_base_dir = "/media/pi/usb64gb/bts/logs/ffmpeg"
        os.makedirs(log_base_dir, exist_ok=True)
        
        if device_number == 0:
            print(f"Iniciando ffmpeg para device0 ({DEVICE})...")
            log_file = os.path.join(log_base_dir, f"device0_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
            self._rotate_logs(log_base_dir, "device0", max_size_mb=5, max_files=3)
            
            with open(log_file, "a") as logfile:
                cmd = cmd_usb if input_source == "usb" else cmd_rtsp
                self.ffmpeg_process_0 = subprocess.Popen(cmd, preexec_fn=os.setsid, stdout=logfile, stderr=logfile)
        else:
            print(f"Iniciando ffmpeg para device1 ({DEVICE})...")
            log_file = os.path.join(log_base_dir, f"device2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
            self._rotate_logs(log_base_dir, "device2", max_size_mb=5, max_files=3)
            
            with open(log_file, "a") as logfile:
                cmd = cmd_usb if input_source == "usb" else cmd_rtsp
                self.ffmpeg_process_1 = subprocess.Popen(cmd, preexec_fn=os.setsid, stdout=logfile, stderr=logfile)


        print("Processos ffmpeg iniciados com buffer circular.")
        
        # Inicia watchdog automaticamente para monitorar saúde dos processos
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
            disk_dir = os.environ.get("BTS_STREAM1_DIR", "/home/pi/recordings/stream1")
            prefix = "video0"
        else:
            disk_dir = os.environ.get("BTS_STREAM2_DIR", "/home/pi/recordings/stream2")
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
        
        # Log de restart com mais detalhes
        try:
            timestamp = datetime.now().isoformat()
            log_file = "/home/pi/recordings/ffmpeg_restart_log.txt"
            input_source = self.input_sources.get(device_number, "unknown")
            device_path = self.device_paths.get(device_number, "unknown")
            
            with open(log_file, "a") as f:
                f.write(f"{timestamp} - Restarting device {device_number} | Source: {input_source} | Path: {device_path}\n")
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
                
                # Verifica se o dispositivo existe (apenas para USB)
                input_source = self.input_sources.get(device_number, "usb")
                if input_source == "usb" and not os.path.exists(device_path):
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

    def _ensure_device_running(self, device_number):
        """Garante que o device esteja rodando quando disponível.

        Se a câmera não estiver presente, aguarda e tenta novamente.
        Usa cooldown para evitar loop agressivo.
        """
        now = time.time()
        if now - self.last_restart_attempt.get(device_number, 0) < self.restart_cooldown_seconds:
            return

        self.last_restart_attempt[device_number] = now

        # Verifica qual é o input_source desta câmera
        input_source = self.input_sources.get(device_number, "usb")
        
        # Se for USB, tenta re-detectar câmeras
        if input_source == "usb":
            # Re-detecta câmeras
            self.detected_cameras = self.detect_usb_cameras()
            if device_number not in self.detected_cameras:
                print(f"⚠️ Watchdog: Câmera {device_number} ausente. Aguardando reconexão...")
                return

            device_path = self.detected_cameras[device_number]
            self.device_paths[device_number] = device_path

            # Inicia o processo se não estiver rodando
            print(f"🔄 Watchdog: Iniciando device{device_number} ({device_path})...")
            self.start_ffmpeg_processes(device_number=device_number, input_source="usb", stream=device_path)
        else:
            # Para RTSP, usa o device_path já armazenado
            device_path = self.device_paths.get(device_number)
            if device_path:
                print(f"🔄 Watchdog: Iniciando device{device_number} (RTSP: {device_path})...")
                self.start_ffmpeg_processes(device_number=device_number, input_source="rtsp", stream=device_path)
            else:
                print(f"⚠️ Watchdog: Câmera {device_number} RTSP não tem device_path configurado")
    
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
        check_interval = 30  # Verifica a cada 30 segundos (evita falsos positivos)
        
        while self.watchdog_running:
            try:
                # Verifica device 0
                if self.ffmpeg_process_0 is not None:
                    if not self.check_process_health(0):
                        print("🚨 Device 0 não está saudável, tentando restart...")
                        self.restart_dead_process(0)
                else:
                    self._ensure_device_running(0)
                
                # Verifica device 1
                if self.ffmpeg_process_1 is not None:
                    if not self.check_process_health(1):
                        print("🚨 Device 1 não está saudável, tentando restart...")
                        self.restart_dead_process(1)
                else:
                    self._ensure_device_running(1)
                
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
            stream1_dir = os.environ.get("BTS_STREAM1_DIR", "/home/pi/recordings/stream1")
            stream2_dir = os.environ.get("BTS_STREAM2_DIR", "/home/pi/recordings/stream2")
            for disk_dir in [stream1_dir, stream2_dir]:
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
            
            # Adiciona 2 segundos ao timestamp para compensar delay de processamento
            event_time = current_time + timedelta(seconds=2)
            
            # Formato: timestamp_epoch|timestamp_iso|cam_id|duration|status
            event_data = {
                "timestamp_epoch": int(event_time.timestamp()),
                "timestamp_iso": event_time.isoformat(),
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
            
            print(f"Evento registrado: cam_id={cam_id}, timestamp={event_time.isoformat()} (+2s compensação)")
            
            # Feedback visual rápido - LED removido
            # if cam_id == 0:
            #     threading.Thread(target=lambda: [
            #         blink_n_times(color=(255, 0, 0), n=2, interval=0.1, direction="left"),
            #         cleanup()
            #     ], daemon=True).start()
            # else:
            #     threading.Thread(target=lambda: [
            #         blink_n_times(color=(0, 0, 255), n=2, interval=0.1, direction="right"),
            #         cleanup()
            #     ], daemon=True).start()
            
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
            print(f"\n{'='*60}")
            print(f"DEBUG: Iniciando _extract_video_from_timestamp")
            print(f"  timestamp_epoch: {timestamp_epoch}")
            print(f"  cam_id: {cam_id}")
            print(f"  duration: {duration}s")
            print(f"{'='*60}")
            
            # Define o diretório baseado na câmera
            if cam_id == 0:
                DISK_DIR = os.environ.get("BTS_STREAM1_DIR", "/home/pi/recordings/stream1")
                PREFIX = "video0"
            else:
                DISK_DIR = os.environ.get("BTS_STREAM2_DIR", "/home/pi/recordings/stream2")
                PREFIX = "video2"
            
            print(f"DEBUG: DISK_DIR={DISK_DIR}, PREFIX={PREFIX}")
            
            # Converte timestamp para datetime
            event_time = datetime.fromtimestamp(timestamp_epoch)
            print(f"DEBUG: event_time={event_time}")
            
            # Busca o arquivo de segmento que contém o timestamp
            # Segmentos de 1 minuto, busca 6 horas antes e 5 minutos depois
            # (5 min depois para capturar arquivos alternativos em caso de arquivo corrompido)
            search_start = event_time - timedelta(hours=6)
            search_end = event_time + timedelta(minutes=5)  # Expandido de 1min para 5min
            
            # Lista todos os arquivos de segmento do disco (suporta .mp4 e .ts)
            segment_files = []
            if os.path.exists(DISK_DIR):
                for filename in os.listdir(DISK_DIR):
                    # Permite arquivos com PREFIX ou arquivos consolidados sem PREFIX
                    is_valid_file = (filename.startswith(PREFIX) or re.match(r'^\d{14}-\d{14}\.mp4$', filename))
                    if is_valid_file and (filename.endswith(".mp4") or filename.endswith(".ts")):
                        filepath = os.path.join(DISK_DIR, filename)
                        file_time = None
                        
                        try:
                            # Tenta 3 formatos diferentes:
                            # 1. Arquivo consolidado com intervalo: YYYYMMDDHHMMSS-YYYYMMDDHHMMSS.mp4
                            if re.match(r'^\d{14}-\d{14}\.mp4$', filename):
                                start_part = filename.split('-')[0]
                                file_time = datetime.strptime(start_part, "%Y%m%d%H%M%S")
                                print(f"DEBUG: Arquivo consolidado detectado: {filename}, início: {file_time}")
                            
                            # 2. Arquivo consolidado .ts: PREFIX_YYYYMMDD_HHMMSS-HHMMSS_consolidated.ts
                            elif '_consolidated.ts' in filename:
                                # Formato: video2_20260404_071000-083500_consolidated.ts
                                base = filename.replace(f"{PREFIX}_", "").replace("_consolidated.ts", "")
                                # base agora é: 20260404_071000-083500
                                date_time_part = base.split('-')[0]  # 20260404_071000
                                file_time = datetime.strptime(date_time_part, "%Y%m%d_%H%M%S")
                                print(f"DEBUG: Arquivo consolidado .ts detectado: {filename}, início: {file_time}")
                            
                            # 3. Formato padrão: PREFIX_YYYYMMDD_HHMMSS.mp4 ou .ts
                            else:
                                timestamp_part = filename.replace(f"{PREFIX}_", "").replace(".mp4", "").replace(".ts", "")
                                file_time = datetime.strptime(timestamp_part, "%Y%m%d_%H%M%S")
                            
                            # Verifica se o arquivo está no range de busca
                            if file_time and search_start <= file_time <= search_end:
                                segment_files.append((filepath, file_time))
                                
                        except (ValueError, IndexError) as e:
                            # Se não conseguir parsear o nome, usa mtime como fallback
                            print(f"Aviso: não foi possível parsear timestamp do arquivo {filename}: {e}")
                            file_mtime = os.path.getmtime(filepath)
                            file_time = datetime.fromtimestamp(file_mtime)
                            if search_start <= file_time <= search_end:
                                segment_files.append((filepath, file_time))
            
            # Para camera 0 (stream1), busca também no diretório de referência se configurado
            # (adiciona aos arquivos já encontrados no diretório padrão)
            # Variável de ambiente: REFERENCE_VIDEO_DIR_PATTERN (opcional)
            # Exemplo: REFERENCE_VIDEO_DIR_PATTERN="/media/pi/usb64gb/nfs_repository/EF000000060B2747/schedule/{date}"
            # O placeholder {date} será substituído pelo formato YYYYMMDD
            if cam_id == 0:
                ref_dir_pattern = os.environ.get("REFERENCE_VIDEO_DIR_PATTERN", "")
                
                if ref_dir_pattern:
                    # Formata a data no formato YYYYMMDD
                    event_date = event_time.strftime("%Y%m%d")
                    ref_dir = ref_dir_pattern.replace("{date}", event_date)
                    
                    if os.path.exists(ref_dir):
                        print(f"DEBUG: Buscando também no diretório de referência: {ref_dir}")
                        ref_files_count = 0
                        
                        for filename in os.listdir(ref_dir):
                            # Formato: HHMMSS-vv-1.mp4 (ex: 071225-vv-1.mp4)
                            if filename.endswith('.mp4') and '-vv-' in filename:
                                filepath = os.path.join(ref_dir, filename)
                                
                                try:
                                    # Extrai o timestamp do nome do arquivo (HHMMSS)
                                    time_part = filename.split('-')[0]  # 071225
                                    
                                    if len(time_part) == 6 and time_part.isdigit():
                                        # Constrói datetime com a data do evento + hora do arquivo
                                        hour = int(time_part[0:2])
                                        minute = int(time_part[2:4])
                                        second = int(time_part[4:6])
                                        
                                        file_time = event_time.replace(hour=hour, minute=minute, second=second, microsecond=0)
                                        
                                        # Verifica se o arquivo está no range de busca
                                        if search_start <= file_time <= search_end:
                                            segment_files.append((filepath, file_time))
                                            ref_files_count += 1
                                            print(f"DEBUG: Arquivo de referência adicionado: {filename} -> {file_time}")
                                            
                                except (ValueError, IndexError) as e:
                                    print(f"DEBUG: Não foi possível parsear {filename}: {e}")
                                    continue
                        
                        if ref_files_count > 0:
                            print(f"DEBUG: Adicionados {ref_files_count} arquivo(s) do diretório de referência")
                    else:
                        print(f"DEBUG: Diretório de referência não existe: {ref_dir}")
                else:
                    print(f"DEBUG: REFERENCE_VIDEO_DIR_PATTERN não configurado, usando apenas diretório padrão")
            
            if not segment_files:
                print(f"Nenhum arquivo de segmento encontrado para o timestamp {event_time}")
                return False
            
            # Ordena por tempo
            segment_files.sort(key=lambda x: x[1])
            
            print(f"DEBUG: Encontrados {len(segment_files)} arquivos de segmento para evento em {event_time}")
            
            # Encontra o arquivo que contém o timestamp do evento
            target_file = None
            file_start_time = None
            file_duration = None
            SEGMENT_DURATION_SECONDS = 60  # FFmpeg configurado com segment_time=60 (1 minuto)
            
            # Lista de candidatos que contém o timestamp pelo nome, mas precisamos validar duração
            candidates = []
            for filepath, file_time in segment_files:
                filename = os.path.basename(filepath)
                
                # Determina o tempo de fim baseado no tipo de arquivo
                # 1. Arquivo consolidado com intervalo: YYYYMMDDHHMMSS-YYYYMMDDHHMMSS.mp4
                if re.match(r'^\d{14}-\d{14}\.mp4$', filename):
                    end_part = filename.split('-')[1].replace('.mp4', '')
                    file_end_time = datetime.strptime(end_part, "%Y%m%d%H%M%S")
                    print(f"DEBUG: Arquivo consolidado MP4: {filename}, fim: {file_end_time.strftime('%H:%M:%S')}")
                
                # 2. Arquivo consolidado .ts: PREFIX_YYYYMMDD_HHMMSS-HHMMSS_consolidated.ts
                elif '_consolidated.ts' in filename:
                    # Formato: video2_20260404_071000-083500_consolidated.ts
                    base = filename.replace(f"video2_", "").replace(f"video0_", "").replace("_consolidated.ts", "")
                    # base agora é: 20260404_071000-083500
                    end_time_part = base.split('-')[1]  # 083500
                    date_part = base.split('_')[0]  # 20260404
                    file_end_time = datetime.strptime(f"{date_part}_{end_time_part}", "%Y%m%d_%H%M%S")
                    print(f"DEBUG: Arquivo consolidado TS: {filename}, fim: {file_end_time.strftime('%H:%M:%S')}")
                
                # 3. Arquivo de referência: HHMMSS-vv-1.mp4
                elif re.match(r'^\d{6}-vv-\d+\.mp4$', filename):
                    # Para arquivos de referência, precisa usar ffprobe para obter duração
                    try:
                        probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
                                   "-of", "default=noprint_wrappers=1:nokey=1", filepath]
                        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=30)
                        
                        if probe_result.returncode == 0 and probe_result.stdout.strip():
                            ref_duration = float(probe_result.stdout.strip())
                            file_end_time = file_time + timedelta(seconds=ref_duration)
                            print(f"DEBUG: Arquivo de referência: {filename}, duração: {ref_duration:.1f}s, fim: {file_end_time.strftime('%H:%M:%S')}")
                        else:
                            # Se ffprobe falhar, assume duração de 3 minutos (típico dos arquivos de referência)
                            file_end_time = file_time + timedelta(minutes=3)
                            print(f"DEBUG: Arquivo de referência (duração assumida): {filename}, fim: {file_end_time.strftime('%H:%M:%S')}")
                    except Exception as e:
                        print(f"DEBUG: Erro ao obter duração de {filename}: {e}, assumindo 3 minutos")
                        file_end_time = file_time + timedelta(minutes=3)
                
                # 4. Arquivo padrão de 60s
                else:
                    file_end_time = file_time + timedelta(seconds=SEGMENT_DURATION_SECONDS)
                
                if file_time <= event_time <= file_end_time:
                    candidates.append((filepath, file_time))
            
            print(f"DEBUG: Encontrados {len(candidates)} candidatos que contêm o timestamp")
            
            # Ordena candidatos por prioridade:
            # 1. Arquivos consolidados MP4 (maiores, mais confiáveis)
            # 2. Arquivos maiores em geral
            # Isso evita validar centenas de arquivos .ts pequenos/corrompidos antes dos consolidados
            candidates_with_size = []
            for filepath, file_time in candidates:
                try:
                    file_size = os.path.getsize(filepath)
                    is_consolidated_mp4 = filepath.endswith('.mp4') and re.match(r'^\d{14}-\d{14}\.mp4$', os.path.basename(filepath))
                    # Prioridade: consolidados primeiro, depois por tamanho
                    priority = (1 if is_consolidated_mp4 else 0, file_size)
                    candidates_with_size.append((filepath, file_time, priority))
                except:
                    candidates_with_size.append((filepath, file_time, (0, 0)))
            
            # Ordena por prioridade (consolidados e maiores primeiro)
            candidates_with_size.sort(key=lambda x: x[2], reverse=True)
            
            # Valida candidatos na ordem de prioridade e escolhe o primeiro válido
            for filepath, file_time, priority in candidates_with_size:
                # Valida duração real do arquivo
                try:
                    probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", filepath]
                    probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=30)
                    
                    if probe_result.returncode == 0 and probe_result.stdout.strip():
                        candidate_duration = float(probe_result.stdout.strip())
                        offset_in_candidate = (event_time - file_time).total_seconds()
                        
                        # Verifica se o evento realmente está dentro do arquivo (com sua duração real)
                        if offset_in_candidate <= candidate_duration:
                            # Candidato válido!
                            # Preferência: arquivos consolidados (maiores) ou completos (próximos de 60s)
                            # sobre arquivos pequenos/corrompidos
                            if candidate_duration >= 30 or (candidate_duration >= 10 and offset_in_candidate + duration <= candidate_duration):
                                target_file = filepath
                                file_start_time = file_time
                                file_duration = candidate_duration
                                print(f"DEBUG: Arquivo validado! {os.path.basename(filepath)} (duração: {candidate_duration:.1f}s)")
                                break
                            else:
                                print(f"DEBUG: Candidato {os.path.basename(filepath)} muito curto ({candidate_duration:.1f}s), buscando melhor alternativa...")
                        else:
                            print(f"DEBUG: Evento em {offset_in_candidate:.1f}s excede duração de {os.path.basename(filepath)} ({candidate_duration:.1f}s)")
                except Exception as e:
                    print(f"DEBUG: Erro ao validar {os.path.basename(filepath)}: {e}")
                    continue
            
            if target_file:
                print(f"DEBUG: Arquivo selecionado após validação: {os.path.basename(target_file)}")
            else:
                print(f"DEBUG: Nenhum candidato válido encontrado pelo nome, buscando alternativa...")
            
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
            # Se já temos file_duration da validação anterior, use-a; caso contrário, valide agora
            if file_duration is None:
                try:
                    print(f"DEBUG: Validando arquivo com ffprobe (timeout: 90s)...")
                    probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", target_file]
                    probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=90)
                    print(f"DEBUG: ffprobe returncode: {probe_result.returncode}")
                    
                    if probe_result.returncode != 0 or not probe_result.stdout.strip():
                        print(f"ERRO: Arquivo {os.path.basename(target_file)} corrompido ou ilegível (ffprobe falhou)")
                        print(f"  stderr: {probe_result.stderr[:200]}")
                        return False
                        
                    file_duration = float(probe_result.stdout.strip())
                    print(f"DEBUG: Duração do arquivo: {file_duration:.2f}s")
                except subprocess.TimeoutExpired as e:
                    print(f"ERRO: Timeout ao validar arquivo {os.path.basename(target_file)} após 90s")
                    print(f"  Possível problema de I/O no disco ou arquivo corrompido")
                    return False
                except (ValueError, Exception) as e:
                    print(f"ERRO: Falha ao validar arquivo {os.path.basename(target_file)}: {e}")
                    return False
            else:
                print(f"DEBUG: Duração já validada anteriormente: {file_duration:.2f}s")
            
            if file_duration < 3:  # Menor que 3s é provavelmente inútil
                print(f"AVISO: Arquivo {os.path.basename(target_file)} tem duração muito curta ({file_duration:.1f}s), pode estar corrompido")
                print(f"       Tentando buscar arquivo alternativo...")
                # Não retorna False imediatamente, deixa a lógica abaixo buscar alternativa
            elif file_duration < 10:
                print(f"AVISO: Arquivo {os.path.basename(target_file)} tem duração curta ({file_duration:.1f}s)")
            
            # Calcula o offset dentro do arquivo
            # IMPORTANTE: Com reset_timestamps=1 no FFmpeg, cada arquivo inicia em 0
            # Então o offset é: (event_time - file_start_time)
            # Queremos recuperar TODA a duração ANTES do evento (ex: últimos 10s ou 15s)
            offset_in_file = (event_time - file_start_time).total_seconds()
            seconds_before = duration  # Toda a duração antes do evento
            
            # CRITICAL: Valida se o evento está dentro dos limites do arquivo
            # (arquivos corrompidos/pequenos podem ter duração menor que esperado)
            # OU se o arquivo é muito curto para ser útil (< 10s)
            if offset_in_file > file_duration or file_duration < 10:
                if offset_in_file > file_duration:
                    print(f"ERRO: Evento em {offset_in_file:.1f}s está além do fim do arquivo ({file_duration:.1f}s)")
                else:
                    print(f"AVISO: Arquivo muito curto ({file_duration:.1f}s) pode não conter conteúdo suficiente")
                print(f"      Buscando arquivo alternativo...")
                
                found_alternative = False
                # Busca de forma mais flexível: qualquer arquivo que possa conter o evento
                for filepath, file_time in segment_files:
                    # Calcula offset neste arquivo candidato
                    candidate_offset = (event_time - file_time).total_seconds()
                    
                    # Valida se é um candidato plausível (offset positivo e razoável)
                    if 0 <= candidate_offset <= SEGMENT_DURATION_SECONDS * 1.5:  # Margem de 50%
                        # Revalida duração deste arquivo candidato
                        try:
                            probe_result = subprocess.run(
                                ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
                                 "-of", "default=noprint_wrappers=1:nokey=1", filepath],
                                capture_output=True, text=True, timeout=90
                            )
                            if probe_result.returncode == 0 and probe_result.stdout.strip():
                                candidate_duration = float(probe_result.stdout.strip())
                                
                                # Verifica se o evento cabe dentro deste arquivo
                                if candidate_offset <= candidate_duration:
                                    target_file = filepath
                                    file_start_time = file_time
                                    offset_in_file = candidate_offset
                                    file_duration = candidate_duration
                                    print(f"      ✓ Arquivo alternativo encontrado: {os.path.basename(target_file)}")
                                    print(f"        Offset: {offset_in_file:.1f}s, Duração: {file_duration:.1f}s")
                                    found_alternative = True
                                    break
                        except Exception as e:
                            print(f"      Erro ao validar {os.path.basename(filepath)}: {e}")
                            continue
                
                if not found_alternative:
                    print(f"ERRO: Não foi possível encontrar nenhum arquivo válido com o evento")
                    return False
                    
            # EDGE CASE: Evento ocorre muito cedo no arquivo (menos de 'duration' segundos do início)
            # Precisamos buscar conteúdo do arquivo ANTERIOR para completar a duração
            previous_file = None
            needs_previous_file = offset_in_file < duration
            
            if needs_previous_file:
                missing_seconds = duration - offset_in_file
                print(f"INFO: Evento ocorre em {offset_in_file:.1f}s do início do arquivo.")
                print(f"      Faltam {missing_seconds:.1f}s para completar {duration}s. Buscando arquivo anterior...")
                
                # Busca o arquivo imediatamente anterior na lista ordenada de segmentos
                # (em vez de calcular nome exato, pois os timestamps não são perfeitamente alinhados)
                previous_file_path = None
                target_index = None
                
                # Encontra o índice do arquivo atual na lista
                for i, (filepath, file_time) in enumerate(segment_files):
                    if filepath == target_file:
                        target_index = i
                        break
                
                # Pega o arquivo anterior da lista (índice - 1)
                if target_index is not None and target_index > 0:
                    previous_file_path, previous_file_start = segment_files[target_index - 1]
                    print(f"DEBUG: Arquivo anterior encontrado na lista: {os.path.basename(previous_file_path)}")
                
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
                effective_duration = min(offset_in_file, file_duration)
                print(f"      Ajustando duração para {effective_duration:.1f}s (conteúdo disponível desde início do arquivo)")
            
            # Verifica se há conteúdo suficiente no arquivo (para eventos no FINAL)
            # CRITICAL: Usa file_duration real, não SEGMENT_DURATION_SECONDS teórico
            available_content = file_duration - offset_seconds
            needs_concatenation = available_content < effective_duration
            next_file = None
            
            # AJUSTE: Se o arquivo é muito pequeno e não tem conteúdo suficiente, 
            # reduz a duração efetiva ao invés de falhar
            if needs_concatenation and available_content > 0:
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
                        print(f"AVISO: Próximo arquivo muito recente ({next_age:.1f}s), usando apenas conteúdo disponível")
                        effective_duration = available_content
                        needs_concatenation = False
                    else:
                        next_file = next_file_path
                        print(f"      Próximo segmento encontrado: {os.path.basename(next_file)}")
                else:
                    print(f"AVISO: Próximo segmento não encontrado, usando conteúdo disponível ({available_content:.1f}s)")
                    effective_duration = available_content
                    needs_concatenation = False
            elif available_content <= 0:
                print(f"ERRO: Offset {offset_seconds:.2f}s está além ou no fim do arquivo (duração: {file_duration:.2f}s)")
                return False
            
            # DEBUG: Validações já feitas acima com file_duration real
            print(f"DEBUG: Offset calculado: {offset_seconds:.2f}s no arquivo {os.path.basename(target_file)}")
            print(f"DEBUG: Duração efetiva a extrair: {effective_duration:.2f}s")
            print(f"DEBUG: Conteúdo disponível: {available_content:.2f}s")
            
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
                    
                    # Adiciona flags para lidar com arquivos corrompidos
                    cmd_prev = [
                        "ffmpeg", "-y",
                        "-err_detect", "ignore_err",  # Ignora erros de decodificação
                        "-i", previous_file,
                        "-ss", str(prev_start_offset),
                        "-t", str(missing_seconds),
                        "-c:v", "copy",
                        "-avoid_negative_ts", "make_zero",  # Corrige timestamps negativos
                        temp_prev
                    ]
                    
                    print(f"DEBUG: Executando extração do arquivo anterior")
                    print(f"  Comando: {' '.join(cmd_prev)}")
                    print(f"  prev_start_offset: {prev_start_offset}s")
                    print(f"  missing_seconds: {missing_seconds}s")
                    
                    result_prev = subprocess.run(cmd_prev, capture_output=True, text=True, timeout=90)
                    print(f"DEBUG: Resultado extração anterior - returncode: {result_prev.returncode}")
                    
                    if result_prev.returncode != 0:
                        print(f"ERRO ao extrair do arquivo anterior: {result_prev.stderr}")
                        return False
                    
                    print(f"DEBUG: Arquivo anterior extraído com sucesso: {temp_prev}")
                    if os.path.exists(temp_prev):
                        print(f"  Tamanho: {os.path.getsize(temp_prev)} bytes")
                    
                    # Parte 2: Do início do arquivo atual até o evento
                    # EDGE CASE: Se offset_in_file < 0.5s, pular extração do arquivo atual
                    # (FFmpeg falha ao extrair ~0 segundos)
                    print(f"\nDEBUG: Verificando se precisa extrair do arquivo atual")
                    print(f"  offset_in_file: {offset_in_file:.3f}s")
                    
                    if offset_in_file >= 0.5:
                        cmd_curr = ["ffmpeg", "-y", "-i", target_file, "-t", str(offset_in_file), "-c:v", "copy", temp_curr]
                        print(f"DEBUG: Executando extração do arquivo atual")
                        print(f"  Comando: {' '.join(cmd_curr)}")
                        
                        result_curr = subprocess.run(cmd_curr, capture_output=True, text=True, timeout=90)
                        print(f"DEBUG: Resultado extração atual - returncode: {result_curr.returncode}")
                        
                        if result_curr.returncode != 0:
                            print(f"ERRO ao extrair do arquivo atual: {result_curr.stderr}")
                            return False
                        
                        print(f"DEBUG: Arquivo atual extraído com sucesso: {temp_curr}")
                        if os.path.exists(temp_curr):
                            print(f"  Tamanho: {os.path.getsize(temp_curr)} bytes")
                    else:
                        print(f"INFO: Offset muito pequeno ({offset_in_file:.3f}s), usando apenas arquivo anterior")
                        temp_curr = None  # Não usar arquivo atual
                    
                    # Cria lista para concatenação
                    print(f"\nDEBUG: Criando lista de concatenação: {concat_list}")
                    with open(concat_list, "w") as f:
                        f.write(f"file '{temp_prev}'\n")
                        print(f"  Arquivo 1: {temp_prev}")
                        if temp_curr and os.path.exists(temp_curr):
                            f.write(f"file '{temp_curr}'\n")
                            print(f"  Arquivo 2: {temp_curr}")
                        else:
                            print(f"  Arquivo 2: (nenhum - usando apenas anterior)")
                    
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
                    
                    print(f"\nDEBUG: Executando concatenação final")
                    print(f"  Comando: {' '.join(extract_cmd)}")
                    print(f"  Output: {output_file}")
                    
                    result = subprocess.run(extract_cmd, capture_output=True, text=True, timeout=90)
                    print(f"DEBUG: Resultado concatenação - returncode: {result.returncode}")
                    
                finally:
                    # Remove arquivos temporários
                    print(f"\nDEBUG: Limpando arquivos temporários")
                    for temp_file in [temp_prev, temp_curr, concat_list]:
                        try:
                            if os.path.exists(temp_file):
                                print(f"  Removendo: {temp_file}")
                                os.remove(temp_file)
                        except Exception as e:
                            print(f"  Erro ao remover {temp_file}: {e}")
                    
            elif needs_concatenation and next_file:
                # CENÁRIO 2: Evento muito tarde - precisa arquivo atual + arquivo SEGUINTE
                print(f"Extraindo vídeo COM CONCATENAÇÃO: {os.path.basename(target_file)} + {os.path.basename(next_file)}")
                
                # Extrai de cada arquivo separadamente
                temp_part1 = os.path.join("/tmp", f"part1_{timestamp_str}.mp4")
                temp_part2 = os.path.join("/tmp", f"part2_{timestamp_str}.mp4")
                concat_list = os.path.join("/tmp", f"concat_{timestamp_str}.txt")
                
                try:
                    # Parte 1: do offset até o final do primeiro arquivo
                    cmd_part1 = ["ffmpeg", "-y", "-err_detect", "ignore_err", "-i", target_file, "-ss", str(offset_seconds), "-c:v", "copy", temp_part1]
                    result1 = subprocess.run(cmd_part1, capture_output=True, text=True, timeout=90)
                    if result1.returncode != 0:
                        print(f"ERRO ao extrair parte 1: {result1.stderr[:300]}")
                        return False
                    
                    # Parte 2: do início do próximo arquivo até completar a duração
                    remaining_duration = effective_duration - available_content
                    cmd_part2 = ["ffmpeg", "-y", "-err_detect", "ignore_err", "-i", next_file, "-t", str(remaining_duration), "-c:v", "copy", temp_part2]
                    result2 = subprocess.run(cmd_part2, capture_output=True, text=True, timeout=90)
                    if result2.returncode != 0:
                        print(f"ERRO ao extrair parte 2: {result2.stderr[:300]}")
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
                    
                    result = subprocess.run(extract_cmd, capture_output=True, text=True, timeout=90)
                    
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
                
                # Detecta se é arquivo de referência (HEVC) que precisa de re-encoding
                is_reference_file = re.match(r'^\d{6}-vv-\d+\.mp4$', os.path.basename(target_file))
                needs_reencode = False
                
                if is_reference_file:
                    print(f"DEBUG: Arquivo de referência detectado, verificando codec...")
                    # Verifica se é HEVC e se tem pixel format válido
                    probe_cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", 
                                "-show_entries", "stream=codec_name,pix_fmt", 
                                "-of", "default=noprint_wrappers=1", target_file]
                    try:
                        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
                        codec_info = probe_result.stdout
                        
                        if "hevc" in codec_info.lower():
                            print(f"DEBUG: Codec HEVC detectado")
                        
                        # Verifica se tem pixel format válido
                        if "pix_fmt=unknown" in codec_info or "pix_fmt=none" in codec_info or "pix_fmt=" not in codec_info:
                            print(f"ERRO: Arquivo HEVC com pixel format inválido/desconhecido")
                            print(f"      Buscando arquivo alternativo...")
                            
                            original_target = target_file
                            found_alternative = False
                            
                            # Busca alternativa entre outros arquivos de referência
                            print(f"      Buscando alternativa entre {len(segment_files)} arquivos...")
                            
                            # Cria lista de candidatos com prioridade
                            candidates_with_priority = []
                            for alt_filepath, alt_file_time in segment_files:
                                if alt_filepath == original_target:
                                    continue  # Pula o arquivo corrompido
                                
                                alt_filename = os.path.basename(alt_filepath)
                                if not re.match(r'^\d{6}-vv-\d+\.mp4$', alt_filename):
                                    continue  # Só considera arquivos de referência
                                
                                # Calcula offset temporal
                                alt_offset = (event_time - alt_file_time).total_seconds()
                                time_distance = abs(alt_offset)
                                
                                # Considera arquivos em um range mais amplo: -300s a +300s (5min)
                                # Offset positivo: evento está DEPOIS do início do arquivo
                                # Offset negativo: evento está ANTES do início do arquivo (pode estar no arquivo anterior)
                                if -300 <= alt_offset <= 300:
                                    candidates_with_priority.append((alt_filepath, alt_file_time, alt_offset, time_distance))
                            
                            # Ordena por distância temporal (mais próximo primeiro)
                            candidates_with_priority.sort(key=lambda x: x[3])
                            
                            print(f"      Encontrados {len(candidates_with_priority)} candidatos no range de ±5min")
                            
                            # Testa candidatos na ordem de proximidade
                            for alt_filepath, alt_file_time, alt_offset, time_distance in candidates_with_priority:
                                alt_filename = os.path.basename(alt_filepath)
                                print(f"      Testando: {alt_filename} (offset: {alt_offset:.1f}s)")
                                
                                # Valida pixel format e duração
                                try:
                                    alt_probe = subprocess.run(
                                        ["ffprobe", "-v", "error", "-select_streams", "v:0",
                                         "-show_entries", "stream=pix_fmt,duration",
                                         "-of", "default=noprint_wrappers=1", alt_filepath],
                                        capture_output=True, text=True, timeout=10
                                    )
                                    
                                    if alt_probe.returncode != 0:
                                        print(f"        ✗ Erro ao validar arquivo")
                                        continue
                                    
                                    # Verifica pixel format
                                    if "pix_fmt=unknown" in alt_probe.stdout or "pix_fmt=none" in alt_probe.stdout:
                                        print(f"        ✗ Pixel format inválido")
                                        continue
                                    
                                    if "pix_fmt=yuv420p" not in alt_probe.stdout:
                                        print(f"        ⚠ Pixel format diferente de yuv420p")
                                        # Continua mesmo assim, pode funcionar
                                    
                                    # Extrai duração
                                    alt_duration = None
                                    for line in alt_probe.stdout.split('\n'):
                                        if line.startswith('duration='):
                                            try:
                                                alt_duration = float(line.split('=')[1])
                                                break
                                            except:
                                                pass
                                    
                                    if alt_duration is None or alt_duration < 10:
                                        print(f"        ✗ Duração inválida ou muito curta")
                                        continue
                                    
                                    # Verifica se o evento cabe dentro deste arquivo
                                    if alt_offset >= 0:
                                        # Evento está DEPOIS do início do arquivo
                                        if alt_offset <= alt_duration:
                                            target_file = alt_filepath
                                            file_start_time = alt_file_time
                                            offset_in_file = alt_offset
                                            file_duration = alt_duration
                                            print(f"        ✓ Arquivo alternativo válido!")
                                            print(f"          Offset: {alt_offset:.1f}s, Duração: {alt_duration:.1f}s")
                                            is_reference_file = True
                                            needs_reencode = True
                                            found_alternative = True
                                            break
                                        else:
                                            print(f"        ✗ Evento além da duração do arquivo ({alt_offset:.1f}s > {alt_duration:.1f}s)")
                                    else:
                                        # Offset negativo: evento está ANTES do início deste arquivo
                                        # Pode usar o evento como próximo ao início (primeiros segundos)
                                        # Útil quando o arquivo original corrompido está antes deste
                                        if abs(alt_offset) <= 60:  # Permite usar arquivo que começa até 60s depois do evento
                                            # Usa do início do arquivo (offset=0)
                                            target_file = alt_filepath
                                            file_start_time = alt_file_time
                                            offset_in_file = 0  # Começa do início
                                            file_duration = alt_duration
                                            print(f"        ✓ Arquivo alternativo válido (usando início do arquivo)!")
                                            print(f"          Evento {abs(alt_offset):.1f}s antes do início, usando primeiros {duration}s")
                                            print(f"          NOTA: Vídeo será dos primeiros {duration}s após o arquivo começar")
                                            print(f"          Duração do arquivo: {alt_duration:.1f}s")
                                            is_reference_file = True
                                            needs_reencode = True
                                            found_alternative = True
                                            # NOTA: O vídeo não será exatamente do momento do evento,
                                            # mas os primeiros segundos depois (melhor que nada)
                                            break
                                        else:
                                            print(f"        ✗ Evento muito antes do início ({abs(alt_offset):.1f}s > 60s)")
                                    
                                except Exception as e:
                                    print(f"        ✗ Erro ao validar: {e}")
                                    continue
                            
                            if not found_alternative:
                                print(f"      ERRO: Nenhum arquivo alternativo válido encontrado entre {len(candidates_with_priority)} candidatos")
                                return False
                        else:
                            needs_reencode = True
                            print(f"DEBUG: Pixel format válido, usando re-encoding para HEVC")
                            
                    except Exception as e:
                        print(f"DEBUG: Erro ao verificar codec: {e}, assumindo necessidade de re-encoding")
                        needs_reencode = True
                
                # Monta o comando ffmpeg baseado na necessidade de re-encoding
                if needs_reencode:
                    extract_cmd = [
                        "ffmpeg", "-y",
                        "-err_detect", "ignore_err",
                        "-analyzeduration", "10M",  # Aumenta análise para HEVC
                        "-probesize", "10M",
                        "-i", target_file,
                        "-ss", str(offset_seconds),
                        "-t", str(effective_duration),
                        "-c:v", "libx264",  # Re-encode para H.264
                        "-preset", "fast",
                        "-crf", "23",
                        "-avoid_negative_ts", "make_zero",
                        "-movflags", "+faststart",
                        output_file
                    ]
                    print(f"Extraindo vídeo com RE-ENCODING: arquivo={os.path.basename(target_file)}, offset={offset_seconds:.2f}s, duração={effective_duration}s")
                else:
                    extract_cmd = [
                        "ffmpeg", "-y",
                        "-err_detect", "ignore_err",  # Ignora erros de decodificação/pacotes corrompidos
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
                result = subprocess.run(extract_cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                print(f"ERRO FFmpeg: {result.stderr[:500]}")
            
            # Aceita arquivo se for gerado com tamanho razoável, mesmo com warnings
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
                
                # Processa TODOS os eventos pending e failed (sem limite)
                for line in lines:
                    line = line.strip()
                    if line:
                        try:
                            event = json.loads(line)
                            # Processa pending e failed (reprocessa as falhas)
                            if event.get("status") in ["pending", "failed"]:
                                duration = event.get("duration", 10)  # Padrão 10s se não especificado
                                print(f"\n[Background] Processando evento: {event['timestamp_iso']}, cam_id={event['cam_id']}, status={event.get('status')}")
                                
                                success = self._extract_video_from_timestamp(
                                    timestamp_epoch=event["timestamp_epoch"],
                                    cam_id=event["cam_id"],
                                    duration=duration
                                )
                                
                                if success:
                                    self._update_event_status(timestamp_file, event, "processed")
                                    processed += 1
                                    print(f"[Background] ✓ Sucesso!")
                                else:
                                    self._update_event_status(timestamp_file, event, "failed")
                                    failed += 1
                                    print(f"[Background] ✗ Falhou!")
                                    
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
