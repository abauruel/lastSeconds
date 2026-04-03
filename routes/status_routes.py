from flask import Blueprint, jsonify, request
import os
import time
import subprocess
from datetime import datetime

# Cria um blueprint para as rotas de status
status_bp = Blueprint('status', __name__)

def init_status_routes(ffmpeg_manager=None):
    """Inicializa as rotas relacionadas ao status."""

    @status_bp.route('/status', methods=['GET'])
    def status():
        return jsonify({"status": "running"}), 200
    
    @status_bp.route('/health', methods=['GET'])
    def health():
        """
        Endpoint de health check que retorna informações detalhadas sobre
        o status dos processos FFmpeg, arquivos recentes, câmeras, etc.
        """
        health_data = {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "issues": [],
            "ffmpeg_processes": {},
            "streams": {},
            "cameras": {},
            "disk": {},
            "system": {}
        }
        
        try:
            # 1. Verifica processos FFmpeg
            try:
                result = subprocess.run(
                    ["ps", "aux"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                ffmpeg_lines = [line for line in result.stdout.split('\n') 
                               if 'ffmpeg' in line and ('video0' in line or 'video2' in line) 
                               and 'grep' not in line]
                
                health_data["ffmpeg_processes"]["count"] = len(ffmpeg_lines)
                health_data["ffmpeg_processes"]["expected"] = 2
                health_data["ffmpeg_processes"]["running"] = len(ffmpeg_lines) == 2
                
                if len(ffmpeg_lines) != 2:
                    health_data["issues"].append(f"Expected 2 FFmpeg processes, found {len(ffmpeg_lines)}")
                    health_data["status"] = "degraded"
            except Exception as e:
                health_data["issues"].append(f"Failed to check FFmpeg processes: {str(e)}")
                health_data["status"] = "unhealthy"
            
            # 2. Verifica processos zumbis
            try:
                result = subprocess.run(
                    ["ps", "aux"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                zombie_count = len([line for line in result.stdout.split('\n') 
                                  if 'defunct' in line and 'grep' not in line])
                
                health_data["ffmpeg_processes"]["zombies"] = zombie_count
                
                if zombie_count > 0:
                    health_data["issues"].append(f"{zombie_count} zombie processes detected")
            except Exception as e:
                health_data["issues"].append(f"Failed to check zombie processes: {str(e)}")
            
            # 3. Verifica Stream1 (RAM disk primeiro, depois pendrive)
            stream1_ram = "/dev/shm/bts/stream1"
            stream1_usb = "/media/pi/usb64gb/bts/stream1"
            try:
                # Tenta primeiro no RAM disk (onde FFmpeg está gravando)
                check_dirs = [(stream1_ram, "RAM"), (stream1_usb, "USB")]
                latest_file = None
                latest_source = None
                
                for check_dir, source in check_dirs:
                    if os.path.exists(check_dir):
                        files = [f for f in os.listdir(check_dir) 
                                if f.startswith("video0") and f.endswith(".ts")]
                        if files:
                            candidate = max([os.path.join(check_dir, f) for f in files], 
                                          key=os.path.getmtime)
                            if latest_file is None or os.path.getmtime(candidate) > os.path.getmtime(latest_file):
                                latest_file = candidate
                                latest_source = source
                
                if latest_file:
                    file_age = time.time() - os.path.getmtime(latest_file)
                    file_size = os.path.getsize(latest_file)
                    
                    health_data["streams"]["stream1"] = {
                        "latest_file": os.path.basename(latest_file),
                        "file_age_seconds": int(file_age),
                        "file_size_bytes": file_size,
                        "recording": file_age < 120,
                        "source": latest_source
                    }
                    
                    if file_age > 300:
                        health_data["issues"].append(f"Stream1 last file is {int(file_age)}s old (>5min)")
                        health_data["status"] = "unhealthy"
                else:
                    health_data["streams"]["stream1"] = {"error": "No files found"}
                    health_data["issues"].append("Stream1 has no video files")
                    health_data["status"] = "unhealthy"
            except Exception as e:
                health_data["streams"]["stream1"] = {"error": str(e)}
                health_data["issues"].append(f"Failed to check Stream1: {str(e)}")
            
            # 4. Verifica Stream2 (RAM disk primeiro, depois pendrive)
            stream2_ram = "/dev/shm/bts/stream2"
            stream2_usb = "/media/pi/usb64gb/bts/stream2"
            try:
                # Tenta primeiro no RAM disk (onde FFmpeg está gravando)
                check_dirs = [(stream2_ram, "RAM"), (stream2_usb, "USB")]
                latest_file = None
                latest_source = None
                
                for check_dir, source in check_dirs:
                    if os.path.exists(check_dir):
                        files = [f for f in os.listdir(check_dir) 
                                if f.startswith("video2") and f.endswith(".ts")]
                        if files:
                            candidate = max([os.path.join(check_dir, f) for f in files], 
                                          key=os.path.getmtime)
                            if latest_file is None or os.path.getmtime(candidate) > os.path.getmtime(latest_file):
                                latest_file = candidate
                                latest_source = source
                
                if latest_file:
                    file_age = time.time() - os.path.getmtime(latest_file)
                    file_size = os.path.getsize(latest_file)
                    
                    health_data["streams"]["stream2"] = {
                        "latest_file": os.path.basename(latest_file),
                        "file_age_seconds": int(file_age),
                        "file_size_bytes": file_size,
                        "recording": file_age < 120,
                        "source": latest_source
                    }
                    
                    if file_age > 300:
                        health_data["issues"].append(f"Stream2 last file is {int(file_age)}s old (>5min)")
                        health_data["status"] = "unhealthy"
                else:
                    health_data["streams"]["stream2"] = {"error": "No files found"}
                    health_data["issues"].append("Stream2 has no video files")
                    health_data["status"] = "unhealthy"
            except Exception as e:
                health_data["streams"]["stream2"] = {"error": str(e)}
                health_data["issues"].append(f"Failed to check Stream2: {str(e)}")
            
            # 5. Verifica câmeras (USB ou RTSP)
            # Detecta se está usando RTSP via variáveis de ambiente
            use_rtsp = bool(os.environ.get('CAMERA_0_RTSP_URL', '').startswith('rtsp://') or 
                           os.environ.get('CAMERA_1_RTSP_URL', '').startswith('rtsp://'))
            
            # Função auxiliar para testar conectividade RTSP
            def test_rtsp_connectivity(rtsp_url, timeout=3):
                """Testa se uma URL RTSP está acessível"""
                try:
                    import socket
                    import re
                    # Extrai host e porta da URL RTSP
                    match = re.search(r'rtsp://(?:[^@]+@)?([^:/]+)(?::(\d+))?', rtsp_url)
                    if not match:
                        return False
                    host = match.group(1)
                    port = int(match.group(2)) if match.group(2) else 554
                    
                    # Testa conexão TCP na porta RTSP
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(timeout)
                    result = sock.connect_ex((host, port))
                    sock.close()
                    return result == 0
                except Exception:
                    return False
            
            try:
                if use_rtsp:
                    # Modo RTSP - verifica URLs configuradas e testa conectividade
                    camera_0_url = os.environ.get('CAMERA_0_RTSP_URL', '')
                    camera_1_url = os.environ.get('CAMERA_1_RTSP_URL', '')
                    
                    rtsp_cameras = []
                    camera_status = {}
                    
                    if camera_0_url.startswith('rtsp://'):
                        is_reachable = test_rtsp_connectivity(camera_0_url)
                        rtsp_cameras.append("Camera 0: " + camera_0_url)
                        camera_status["camera_0"] = {
                            "url": camera_0_url,
                            "reachable": is_reachable
                        }
                        if not is_reachable:
                            health_data["issues"].append("Camera 0 RTSP not reachable")
                    
                    if camera_1_url.startswith('rtsp://'):
                        is_reachable = test_rtsp_connectivity(camera_1_url)
                        rtsp_cameras.append("Camera 1: " + camera_1_url)
                        camera_status["camera_1"] = {
                            "url": camera_1_url,
                            "reachable": is_reachable
                        }
                        if not is_reachable:
                            health_data["issues"].append("Camera 1 RTSP not reachable")
                    
                    health_data["cameras"]["mode"] = "RTSP"
                    health_data["cameras"]["detected"] = rtsp_cameras
                    health_data["cameras"]["status"] = camera_status
                    health_data["cameras"]["count"] = len(rtsp_cameras)
                    health_data["cameras"]["details"] = {
                        "camera_0": camera_0_url if camera_0_url else "NOT CONFIGURED",
                        "camera_1": camera_1_url if camera_1_url else "NOT CONFIGURED"
                    }
                    
                    # Em modo RTSP, não é erro não ter câmeras USB
                    if len(rtsp_cameras) < 2:
                        health_data["issues"].append(
                            f"Only {len(rtsp_cameras)} RTSP camera(s) configured, expected 2"
                        )
                else:
                    # Modo USB - detecção original
                    result = subprocess.run(
                        ["v4l2-ctl", "--list-devices"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    
                    # Processa output para identificar apenas câmeras USB
                    lines = result.stdout.split('\n')
                    usb_cameras = []
                    current_device_type = None
                    
                    for line in lines:
                        line_stripped = line.strip()
                        
                        # Identifica linhas que contêm "usb" (câmeras USB)
                        if 'usb' in line.lower() and ':' in line:
                            current_device_type = 'usb'
                        
                        # Se estamos em um bloco USB e encontramos /dev/video
                        if current_device_type == 'usb' and line_stripped.startswith('/dev/video'):
                            device_path = line_stripped
                            if os.path.exists(device_path):
                                try:
                                    video_num = int(device_path.split('video')[1])
                                    # Adiciona apenas números pares (câmeras principais, não background)
                                    if video_num % 2 == 0:
                                        usb_cameras.append(device_path)
                                except (ValueError, IndexError):
                                    pass
                        
                        # Reset quando sai de um bloco USB
                        if current_device_type == 'usb' and line_stripped == '':
                            current_device_type = None
                    
                    # Ordena para manter consistência
                    usb_cameras = sorted(usb_cameras)
                    
                    health_data["cameras"]["mode"] = "USB"
                    health_data["cameras"]["detected"] = usb_cameras
                    health_data["cameras"]["count"] = len(usb_cameras)
                    
                    # Informações detalhadas sobre cada câmera
                    health_data["cameras"]["details"] = {
                        "camera_0": usb_cameras[0] if len(usb_cameras) > 0 else "NOT FOUND",
                        "camera_1": usb_cameras[1] if len(usb_cameras) > 1 else "NOT FOUND"
                    }
                    
                    # Verifica se tem as 2 câmeras esperadas
                    if len(usb_cameras) < 2:
                        health_data["issues"].append(
                            f"Only {len(usb_cameras)} USB camera(s) detected, expected 2. "
                            f"Found: {usb_cameras}"
                        )
                        health_data["status"] = "unhealthy"
                    
            except Exception as e:
                health_data["cameras"]["error"] = str(e)
                health_data["issues"].append(f"Failed to check cameras: {str(e)}")
            
            # 6. Verifica espaço em disco
            try:
                result = subprocess.run(
                    ["df", "/media/pi/usb64gb"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    parts = lines[1].split()
                    if len(parts) >= 5:
                        total = int(parts[1]) * 1024  # KB to bytes
                        used = int(parts[2]) * 1024
                        available = int(parts[3]) * 1024
                        usage_percent = int(parts[4].replace('%', ''))
                        
                        health_data["disk"] = {
                            "total_bytes": total,
                            "used_bytes": used,
                            "available_bytes": available,
                            "usage_percent": usage_percent
                        }
                        
                        if usage_percent > 90:
                            health_data["issues"].append(f"Disk usage critical: {usage_percent}%")
                            health_data["status"] = "unhealthy"
                        elif usage_percent > 80:
                            health_data["issues"].append(f"Disk usage high: {usage_percent}%")
                            if health_data["status"] == "healthy":
                                health_data["status"] = "degraded"
            except Exception as e:
                health_data["disk"]["error"] = str(e)
                health_data["issues"].append(f"Failed to check disk: {str(e)}")
            
            # 7. Temperatura do sistema
            try:
                if os.path.exists('/sys/class/thermal/thermal_zone0/temp'):
                    with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                        temp = int(f.read().strip()) / 1000
                        health_data["system"]["cpu_temperature_celsius"] = temp
                        
                        if temp > 70:
                            health_data["issues"].append(f"CPU temperature critical: {temp}°C")
                            if health_data["status"] != "unhealthy":
                                health_data["status"] = "degraded"
                        elif temp > 60:
                            health_data["issues"].append(f"CPU temperature high: {temp}°C")
            except Exception as e:
                health_data["system"]["temperature_error"] = str(e)
            
        except Exception as e:
            health_data["status"] = "error"
            health_data["issues"].append(f"Health check error: {str(e)}")
        
        # Define código HTTP baseado no status
        status_code = 200
        if health_data["status"] == "degraded":
            status_code = 200  # Still OK but with warnings
        elif health_data["status"] == "unhealthy":
            status_code = 503  # Service Unavailable
        elif health_data["status"] == "error":
            status_code = 500  # Internal Server Error
        
        return jsonify(health_data), status_code

    @status_bp.route('/update_time', methods=['POST'])
    def update_time():
        """
        Endpoint para atualizar a hora do sistema.
        
        Recebe um JSON com:
        - datetime: string no formato ISO 8601 (ex: "2026-03-28T14:30:00")
          ou formato "YYYY-MM-DD HH:MM:SS"
        
        Exemplo de requisição:
        POST /update_time
        {
            "datetime": "2026-03-28 14:30:00"
        }
        
        Returns:
            JSON com o status da operação e a nova hora do sistema
        """
        try:
            data = request.get_json()
            
            if not data or 'datetime' not in data:
                return jsonify({
                    "status": "error",
                    "message": "Campo 'datetime' é obrigatório"
                }), 400
            
            datetime_str = data['datetime']
            
            # Tenta parsear a data para validar o formato
            try:
                # Aceita formato ISO 8601
                if 'T' in datetime_str:
                    dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                    # Converte para o formato esperado pelo comando date
                    date_format = dt.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    # Valida formato YYYY-MM-DD HH:MM:SS
                    dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
                    date_format = datetime_str
            except ValueError as e:
                return jsonify({
                    "status": "error",
                    "message": f"Formato de data inválido. Use 'YYYY-MM-DD HH:MM:SS' ou ISO 8601. Erro: {str(e)}"
                }), 400
            
            # Atualiza a hora do sistema usando o comando date
            # Formato: date -s "YYYY-MM-DD HH:MM:SS"
            try:
                result = subprocess.run(
                    ["sudo", "date", "-s", date_format],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    # Sincroniza o hardware clock com o system clock
                    subprocess.run(
                        ["sudo", "hwclock", "-w"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    
                    return jsonify({
                        "status": "success",
                        "message": "Hora do sistema atualizada com sucesso",
                        "previous_datetime": datetime_str,
                        "current_datetime": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "timestamp": datetime.now().isoformat()
                    }), 200
                else:
                    return jsonify({
                        "status": "error",
                        "message": f"Falha ao atualizar hora do sistema: {result.stderr}",
                        "returncode": result.returncode
                    }), 500
                    
            except subprocess.TimeoutExpired:
                return jsonify({
                    "status": "error",
                    "message": "Timeout ao executar comando de atualização da hora"
                }), 500
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": f"Erro ao executar comando: {str(e)}"
                }), 500
                
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Erro ao processar requisição: {str(e)}"
            }), 500

    @status_bp.route('/shutdown', methods=['POST'])
    def shutdown():
        """
        Endpoint para desligar o Raspberry Pi com segurança.
        
        Realiza:
        1. Para os processos FFmpeg gracefully
        2. Sincroniza dados do disco
        3. Executa shutdown do sistema
        
        Retorna confirmação antes do shutdown ser executado.
        """
        try:
            data = request.get_json() or {}
            delay_seconds = data.get('delay', 10)  # Delay padrão de 10 segundos
            
            # Valida delay
            if not isinstance(delay_seconds, int) or delay_seconds < 0 or delay_seconds > 300:
                return jsonify({
                    "status": "error",
                    "message": "delay deve ser um inteiro entre 0 e 300 segundos"
                }), 400
            
            print("🔴 SHUTDOWN SOLICITADO via API")
            print(f"   Delay: {delay_seconds} segundos")
            
            response_data = {
                "status": "success",
                "message": "Shutdown iniciado com sucesso",
                "timestamp": datetime.now().isoformat(),
                "delay_seconds": delay_seconds,
                "steps": []
            }
            
            # Passo 1: Para os processos FFmpeg
            if ffmpeg_manager:
                try:
                    print("   Passo 1/3: Parando processos FFmpeg...")
                    ffmpeg_manager.stop_ffmpeg_processes()
                    response_data["steps"].append("FFmpeg processes stopped")
                    print("   ✓ Processos FFmpeg parados")
                except Exception as e:
                    error_msg = f"Erro ao parar FFmpeg: {str(e)}"
                    print(f"   ✗ {error_msg}")
                    response_data["steps"].append(error_msg)
            else:
                response_data["steps"].append("FFmpeg manager not available (skipped)")
            
            # Passo 2: Sincroniza dados do disco
            try:
                print("   Passo 2/3: Sincronizando dados do disco...")
                subprocess.run(["sync"], check=True, timeout=10)
                response_data["steps"].append("Disk data synchronized")
                print("   ✓ Dados sincronizados")
            except Exception as e:
                error_msg = f"Erro ao sincronizar disco: {str(e)}"
                print(f"   ✗ {error_msg}")
                response_data["steps"].append(error_msg)
            
            # Passo 3: Agenda o shutdown
            try:
                print(f"   Passo 3/3: Agendando shutdown em {delay_seconds}s...")
                
                # Usa 'sudo shutdown' com delay
                subprocess.Popen(
                    ["sudo", "shutdown", "-h", f"+{int(delay_seconds/60) if delay_seconds >= 60 else 0}"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                
                response_data["steps"].append(f"System shutdown scheduled in {delay_seconds}s")
                print(f"   ✓ Shutdown agendado")
                print("🔴 Sistema será desligado em {delay_seconds}s")
                
            except Exception as e:
                error_msg = f"Erro ao executar shutdown: {str(e)}"
                print(f"   ✗ {error_msg}")
                response_data["status"] = "error"
                response_data["steps"].append(error_msg)
                return jsonify(response_data), 500
            
            return jsonify(response_data), 200
            
        except Exception as e:
            print(f"✗ Erro no shutdown: {str(e)}")
            return jsonify({
                "status": "error",
                "message": f"Erro ao processar shutdown: {str(e)}"
            }), 500

    @status_bp.route('/reboot', methods=['POST'])
    def reboot():
        """
        Endpoint para reiniciar o Raspberry Pi com segurança.
        
        Realiza:
        1. Para os processos FFmpeg gracefully
        2. Sincroniza dados do disco
        3. Executa reboot do sistema
        
        Retorna confirmação antes do reboot ser executado.
        """
        try:
            data = request.get_json() or {}
            delay_seconds = data.get('delay', 10)  # Delay padrão de 10 segundos
            
            # Valida delay
            if not isinstance(delay_seconds, int) or delay_seconds < 0 or delay_seconds > 300:
                return jsonify({
                    "status": "error",
                    "message": "delay deve ser um inteiro entre 0 e 300 segundos"
                }), 400
            
            print("🔄 REBOOT SOLICITADO via API")
            print(f"   Delay: {delay_seconds} segundos")
            
            response_data = {
                "status": "success",
                "message": "Reboot iniciado com sucesso",
                "timestamp": datetime.now().isoformat(),
                "delay_seconds": delay_seconds,
                "steps": []
            }
            
            # Passo 1: Para os processos FFmpeg
            if ffmpeg_manager:
                try:
                    print("   Passo 1/3: Parando processos FFmpeg...")
                    ffmpeg_manager.stop_ffmpeg_processes()
                    response_data["steps"].append("FFmpeg processes stopped")
                    print("   ✓ Processos FFmpeg parados")
                except Exception as e:
                    error_msg = f"Erro ao parar FFmpeg: {str(e)}"
                    print(f"   ✗ {error_msg}")
                    response_data["steps"].append(error_msg)
            else:
                response_data["steps"].append("FFmpeg manager not available (skipped)")
            
            # Passo 2: Sincroniza dados do disco
            try:
                print("   Passo 2/3: Sincronizando dados do disco...")
                subprocess.run(["sync"], check=True, timeout=10)
                response_data["steps"].append("Disk data synchronized")
                print("   ✓ Dados sincronizados")
            except Exception as e:
                error_msg = f"Erro ao sincronizar disco: {str(e)}"
                print(f"   ✗ {error_msg}")
                response_data["steps"].append(error_msg)
            
            # Passo 3: Agenda o reboot
            try:
                print(f"   Passo 3/3: Agendando reboot em {delay_seconds}s...")
                
                # Usa 'sudo reboot' com delay via shutdown -r
                subprocess.Popen(
                    ["sudo", "shutdown", "-r", f"+{int(delay_seconds/60) if delay_seconds >= 60 else 0}"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                
                response_data["steps"].append(f"System reboot scheduled in {delay_seconds}s")
                print(f"   ✓ Reboot agendado")
                print(f"🔄 Sistema será reiniciado em {delay_seconds}s")
                
            except Exception as e:
                error_msg = f"Erro ao executar reboot: {str(e)}"
                print(f"   ✗ {error_msg}")
                response_data["status"] = "error"
                response_data["steps"].append(error_msg)
                return jsonify(response_data), 500
            
            return jsonify(response_data), 200
            
        except Exception as e:
            print(f"✗ Erro no reboot: {str(e)}")
            return jsonify({
                "status": "error",
                "message": f"Erro ao processar reboot: {str(e)}"
            }), 500

    return status_bp