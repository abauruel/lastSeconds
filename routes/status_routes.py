from flask import Blueprint, jsonify
import os
import time
import subprocess
from datetime import datetime

# Cria um blueprint para as rotas de status
status_bp = Blueprint('status', __name__)

def init_status_routes():
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
            
            # 3. Verifica Stream1
            stream1_dir = "/media/pi/usb64gb/bts/stream1"
            try:
                if os.path.exists(stream1_dir):
                    files = [f for f in os.listdir(stream1_dir) 
                            if f.startswith("video0") and f.endswith(".ts")]
                    
                    if files:
                        latest_file = max([os.path.join(stream1_dir, f) for f in files], 
                                        key=os.path.getmtime)
                        file_age = time.time() - os.path.getmtime(latest_file)
                        file_size = os.path.getsize(latest_file)
                        
                        health_data["streams"]["stream1"] = {
                            "latest_file": os.path.basename(latest_file),
                            "file_age_seconds": int(file_age),
                            "file_size_bytes": file_size,
                            "recording": file_age < 120
                        }
                        
                        if file_age > 300:
                            health_data["issues"].append(f"Stream1 last file is {int(file_age)}s old (>5min)")
                            health_data["status"] = "unhealthy"
                    else:
                        health_data["streams"]["stream1"] = {"error": "No files found"}
                        health_data["issues"].append("Stream1 has no video files")
                        health_data["status"] = "unhealthy"
                else:
                    health_data["streams"]["stream1"] = {"error": "Directory not found"}
                    health_data["issues"].append("Stream1 directory does not exist")
                    health_data["status"] = "unhealthy"
            except Exception as e:
                health_data["streams"]["stream1"] = {"error": str(e)}
                health_data["issues"].append(f"Failed to check Stream1: {str(e)}")
            
            # 4. Verifica Stream2
            stream2_dir = "/media/pi/usb64gb/bts/stream2"
            try:
                if os.path.exists(stream2_dir):
                    files = [f for f in os.listdir(stream2_dir) 
                            if f.startswith("video2") and f.endswith(".ts")]
                    
                    if files:
                        latest_file = max([os.path.join(stream2_dir, f) for f in files], 
                                        key=os.path.getmtime)
                        file_age = time.time() - os.path.getmtime(latest_file)
                        file_size = os.path.getsize(latest_file)
                        
                        health_data["streams"]["stream2"] = {
                            "latest_file": os.path.basename(latest_file),
                            "file_age_seconds": int(file_age),
                            "file_size_bytes": file_size,
                            "recording": file_age < 120
                        }
                        
                        if file_age > 300:
                            health_data["issues"].append(f"Stream2 last file is {int(file_age)}s old (>5min)")
                            health_data["status"] = "unhealthy"
                    else:
                        health_data["streams"]["stream2"] = {"error": "No files found"}
                        health_data["issues"].append("Stream2 has no video files")
                        health_data["status"] = "unhealthy"
                else:
                    health_data["streams"]["stream2"] = {"error": "Directory not found"}
                    health_data["issues"].append("Stream2 directory does not exist")
                    health_data["status"] = "unhealthy"
            except Exception as e:
                health_data["streams"]["stream2"] = {"error": str(e)}
                health_data["issues"].append(f"Failed to check Stream2: {str(e)}")
            
            # 5. Verifica câmeras (USB ou RTSP)
            # Detecta se está usando RTSP via variáveis de ambiente
            use_rtsp = bool(os.environ.get('CAMERA_0_RTSP_URL', '').startswith('rtsp://') or 
                           os.environ.get('CAMERA_1_RTSP_URL', '').startswith('rtsp://'))
            
            try:
                if use_rtsp:
                    # Modo RTSP - verifica URLs configuradas
                    camera_0_url = os.environ.get('CAMERA_0_RTSP_URL', '')
                    camera_1_url = os.environ.get('CAMERA_1_RTSP_URL', '')
                    
                    rtsp_cameras = []
                    if camera_0_url.startswith('rtsp://'):
                        rtsp_cameras.append("Camera 0: " + camera_0_url)
                    if camera_1_url.startswith('rtsp://'):
                        rtsp_cameras.append("Camera 1: " + camera_1_url)
                    
                    health_data["cameras"]["mode"] = "RTSP"
                    health_data["cameras"]["detected"] = rtsp_cameras
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

    return status_bp