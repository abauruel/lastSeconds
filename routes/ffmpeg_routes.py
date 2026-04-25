from flask import Blueprint, jsonify, request, send_file
from database.models import Video, VideoStatus
from database.db_config import SessionLocal
import os
import glob
from datetime import datetime
from audio_player import play_event_sound

# Cria um blueprint para as rotas do ffmpeg
ffmpeg_bp = Blueprint('ffmpeg', __name__)

def init_ffmpeg_routes(ffmpeg_manager):
    """Inicializa as rotas relacionadas ao ffmpeg."""

    @ffmpeg_bp.route('/start', methods=['POST'])
    def handle_start():
        """Inicia as gravações das câmeras via API."""
        # Obtém as URLs RTSP das variáveis de ambiente
        camera_0_rtsp = os.environ.get('CAMERA_0_RTSP_URL', 'rtsp://')
        camera_1_rtsp = os.environ.get('CAMERA_1_RTSP_URL', 'rtsp://')
        
        # Parâmetros opcionais via body da requisição
        data = request.get_json(silent=True, force=True) or {}
        input_source = data.get('input_source', 'rtsp')  # padrão: rtsp
        
        # Permite override das URLs via requisição (opcional)
        camera_0_url = data.get('camera_0_url', camera_0_rtsp)
        camera_1_url = data.get('camera_1_url', camera_1_rtsp)
        
        # Limpa os buffers antes de iniciar
        ffmpeg_manager.clear_buffers()
        
        # Inicia ambas as câmeras
        ffmpeg_manager.start_ffmpeg_processes(device_number=0, input_source=input_source, stream=camera_0_url)
        ffmpeg_manager.start_ffmpeg_processes(device_number=1, input_source=input_source, stream=camera_1_url)
        
        return jsonify({
            "status": "success", 
            "message": "Processos do ffmpeg iniciados para ambas as câmeras.",
            "camera_0": camera_0_url,
            "camera_1": camera_1_url,
            "input_source": input_source
        }), 200

    @ffmpeg_bp.route('/record', methods=['POST'])
    def handle_record():
        """Registra apenas o timestamp do evento para ambas as câmeras"""
        data = request.get_json(silent=True, force=True) or {}
        duration = data.get('duration', 12)  # Padrão 12 segundos
        
        # Toca áudio de evento (não-bloqueante)
        play_event_sound(blocking=False)
        
        # Registra evento para ambas as câmeras
        success_cam1 = ffmpeg_manager.record_last_10_seconds(cam_id=0, duration=duration)
        success_cam2 = ffmpeg_manager.record_last_10_seconds(cam_id=1, duration=duration)
        
        if success_cam1 and success_cam2:
            return jsonify({"status": "success", "message": f"Evento registrado para ambas as câmeras (duração: {duration}s)"}), 200
        elif success_cam1 or success_cam2:
            cameras = "cam1" if success_cam1 else "cam2"
            return jsonify({"status": "partial", "message": f"Evento registrado apenas para {cameras} (duração: {duration}s)"}), 200
        return jsonify({"status": "error", "message": "Erro ao registrar evento em ambas as câmeras"}), 500
    
    @ffmpeg_bp.route('/record/cam1', methods=['POST'])
    def handle_record_cam1():
        """Registra apenas o timestamp do evento da câmera 1"""
        data = request.get_json(silent=True, force=True) or {}
        duration = data.get('duration', 12)  # Padrão 12 segundos
        
        # Toca áudio de evento (não-bloqueante)
        play_event_sound(blocking=False)
        
        success = ffmpeg_manager.record_last_10_seconds(cam_id=0, duration=duration)
        if success:
            
            return jsonify({"status": "success", "message": f"Evento cam1 registrado (duração: {duration}s)"}), 200
        return jsonify({"status": "error", "message": "Erro ao registrar evento"}), 500
    
    @ffmpeg_bp.route('/record/cam2', methods=['POST'])
    def handle_record_cam2():
        """Registra apenas o timestamp do evento da câmera 2"""
        data = request.get_json(silent=True, force=True) or {}
        duration = data.get('duration', 12)  # Padrão 12 segundos
        
        # Toca áudio de evento (não-bloqueante)
        play_event_sound(blocking=False)
        
        success = ffmpeg_manager.record_last_10_seconds(cam_id=1, duration=duration)
        if success:
            
            return jsonify({"status": "success", "message": f"Evento cam2 registrado (duração: {duration}s)"}), 200
        return jsonify({"status": "error", "message": "Erro ao registrar evento"}), 500

    @ffmpeg_bp.route('/process_timestamps', methods=['POST'])
    def handle_process_timestamps():
        """Inicia processamento de timestamps em background (não bloqueia)"""
        try:
            data = request.get_json() or {}
            date_str = data.get('date')  # Formato: YYYYMMDD (opcional)
            days_back = data.get('days_back', 3)  # Quantos dias processar (padrão: 3)
            
            result = ffmpeg_manager.manual_process_timestamps(date_str, days_back)
            return jsonify(result), 200
        except Exception as e:
            print(f"Erro ao processar timestamps: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "status": "error",
                "message": f"Erro interno ao processar timestamps: {str(e)}"
            }), 500
    
    @ffmpeg_bp.route('/process_timestamps/status', methods=['GET'])
    def handle_process_status():
        """Verifica se há processamento em andamento"""
        try:
            with ffmpeg_manager.processing_lock:
                is_processing = ffmpeg_manager.is_processing
            
            return jsonify({
                "status": "success",
                "is_processing": is_processing,
                "message": "Processamento em andamento" if is_processing else "Nenhum processamento em andamento"
            }), 200
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Erro ao verificar status: {str(e)}"
            }), 500
    
    @ffmpeg_bp.route('/stop', methods=['POST'])
    def handle_stop():
        ffmpeg_manager.stop_ffmpeg_processes()
        return jsonify({"status": "success", "message": "Processos do ffmpeg finalizados."}), 200


    @ffmpeg_bp.route('/clear_buffers', methods=['POST'])
    def handle_clear_buffers():
        ffmpeg_manager.clear_buffers()
        return jsonify({"status": "success", "message": "Buffers limpos com sucesso."}), 200
    
    @ffmpeg_bp.route('/update_status', methods=['PUT'])
    def update_video_status():
        data = request.get_json()
        name = data.get('name')
        status = data.get('status')
        
        if not name:
            return jsonify({"status": "error", "message": "Nome do vídeo é obrigatório"}), 400
            
        if not status:
            return jsonify({"status": "error", "message": "Status é obrigatório"}), 400
            
        # Validate if the status is valid
        try:
            new_status = VideoStatus[status.upper()]
        except KeyError:
            return jsonify({
                "status": "error", 
                "message": f"Status inválido. Use: {', '.join([s.name.lower() for s in VideoStatus])}"
            }), 400
        
        try:
            db = SessionLocal()
            video = db.query(Video).filter(Video.name == name).first()
            
            if not video:
                return jsonify({"status": "error", "message": "Vídeo não encontrado"}), 404
            
            video.status = new_status
            db.commit()
            
            return jsonify({
                "status": "success", 
                "message": f"Status do vídeo {name} atualizado para {status.lower()}"
            }), 200
            
        except Exception as e:
            db.rollback()
            return jsonify({"status": "error", "message": str(e)}), 500
            
        finally:
            db.close()
    

    @ffmpeg_bp.route('/restart_service', methods=['POST'])
    def restart_service():
        service_name = "better_seconds_record.service"
        try:
            os.system(f"sudo systemctl restart {service_name}")
            return jsonify({"status": "success", "message": f"Serviço {service_name} reiniciado."}), 200
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    
    @ffmpeg_bp.route('/videos', methods=['GET'])
    def list_video_dates():
        """Lista todas as datas com vídeos processados disponíveis"""
        try:
            base_path = "/home/pi/recordings/streams"
            
            if not os.path.exists(base_path):
                return jsonify({
                    "status": "error",
                    "message": "Diretório de vídeos não encontrado"
                }), 404
            
            # Lista todos os diretórios em formato YYYYMMDD
            dates = []
            for item in os.listdir(base_path):
                item_path = os.path.join(base_path, item)
                # Verifica se é um diretório e tem formato YYYYMMDD (8 dígitos)
                if os.path.isdir(item_path) and item.isdigit() and len(item) == 8:
                    try:
                        # Valida se é uma data válida
                        date_obj = datetime.strptime(item, '%Y%m%d')
                        
                        # Conta quantos vídeos tem nessa data
                        video_files = [f for f in os.listdir(item_path) 
                                     if f.endswith('.mp4')]
                        
                        dates.append({
                            "date": item,
                            "date_formatted": date_obj.strftime('%d/%m/%Y'),
                            "video_count": len(video_files),
                            "path": f"/videos/{item}"
                        })
                    except ValueError:
                        # Ignora diretórios que não são datas válidas
                        pass
            
            # Ordena por data (mais recente primeiro)
            dates.sort(key=lambda x: x['date'], reverse=True)
            
            return jsonify({
                "status": "success",
                "total_dates": len(dates),
                "dates": dates
            }), 200
            
        except Exception as e:
            print(f"Erro ao listar datas de vídeos: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "status": "error",
                "message": f"Erro ao listar datas: {str(e)}"
            }), 500
    
    @ffmpeg_bp.route('/videos/<date>', methods=['GET'])
    def list_videos_by_date(date):
        """Lista todos os vídeos de uma data específica (formato YYYYMMDD)"""
        try:
            # Valida formato da data
            if not date.isdigit() or len(date) != 8:
                return jsonify({
                    "status": "error",
                    "message": "Formato de data inválido. Use YYYYMMDD (ex: 20260403)"
                }), 400
            
            try:
                date_obj = datetime.strptime(date, '%Y%m%d')
            except ValueError:
                return jsonify({
                    "status": "error",
                    "message": "Data inválida"
                }), 400
            
            date_path = f"/home/pi/recordings/streams/{date}"
            
            if not os.path.exists(date_path):
                return jsonify({
                    "status": "error",
                    "message": f"Nenhum vídeo encontrado para a data {date}"
                }), 404
            
            # Lista todos os arquivos MP4
            videos = []
            for filename in os.listdir(date_path):
                if filename.endswith('.mp4'):
                    file_path = os.path.join(date_path, filename)
                    file_stat = os.stat(file_path)
                    
                    videos.append({
                        "filename": filename,
                        "size_bytes": file_stat.st_size,
                        "size_mb": round(file_stat.st_size / (1024 * 1024), 2),
                        "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                        "download_url": f"/videos/{date}/{filename}"
                    })
            
            # Ordena por nome (mais recente primeiro)
            videos.sort(key=lambda x: x['filename'], reverse=True)
            
            return jsonify({
                "status": "success",
                "date": date,
                "date_formatted": date_obj.strftime('%d/%m/%Y'),
                "total_videos": len(videos),
                "videos": videos
            }), 200
            
        except Exception as e:
            print(f"Erro ao listar vídeos da data {date}: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "status": "error",
                "message": f"Erro ao listar vídeos: {str(e)}"
            }), 500
    
    @ffmpeg_bp.route('/videos/<date>/<filename>', methods=['GET'])
    def download_video(date, filename):
        """Faz download de um vídeo específico"""
        try:
            # Valida formato da data
            if not date.isdigit() or len(date) != 8:
                return jsonify({
                    "status": "error",
                    "message": "Formato de data inválido"
                }), 400
            
            # Valida extensão do arquivo
            if not filename.endswith('.mp4'):
                return jsonify({
                    "status": "error",
                    "message": "Apenas arquivos .mp4 são permitidos"
                }), 400
            
            # Previne path traversal
            if '..' in filename or '/' in filename:
                return jsonify({
                    "status": "error",
                    "message": "Nome de arquivo inválido"
                }), 400
            
            file_path = f"/home/pi/recordings/streams/{date}/{filename}"
            
            if not os.path.exists(file_path):
                return jsonify({
                    "status": "error",
                    "message": "Vídeo não encontrado"
                }), 404
            
            # Envia o arquivo para download
            return send_file(
                file_path,
                mimetype='video/mp4',
                as_attachment=True,
                download_name=filename
            )
            
        except Exception as e:
            print(f"Erro ao fazer download do vídeo {date}/{filename}: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "status": "error",
                "message": f"Erro ao fazer download: {str(e)}"
            }), 500
        
    return ffmpeg_bp