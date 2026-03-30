from flask import Blueprint, jsonify, request
from database.models import Video, VideoStatus
from database.db_config import SessionLocal
import os
import glob
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
        """Registra apenas o timestamp do evento (resposta rápida)"""
        handle_record_cam1()  # Registra evento para câmera 1
        handle_record_cam2()  # Registra evento para câmera 2
        if success:
            return jsonify({"status": "success", "message": f"Evento registrado para processamento (duração: {duration}s)"}), 200
        return jsonify({"status": "error", "message": "Erro ao registrar evento"}), 500
    
    @ffmpeg_bp.route('/record/cam1', methods=['POST'])
    def handle_record_cam1():
        """Registra apenas o timestamp do evento da câmera 1"""
        data = request.get_json(silent=True, force=True) or {}
        duration = data.get('duration', 10)  # Padrão 10 segundos
        
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
        duration = data.get('duration', 10)  # Padrão 10 segundos
        
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
        
    return ffmpeg_bp