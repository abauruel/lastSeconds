from flask import Blueprint, jsonify, request
from database.models import Video, VideoStatus
from database.db_config import SessionLocal
import os
import glob
# Cria um blueprint para as rotas do ffmpeg
ffmpeg_bp = Blueprint('ffmpeg', __name__)

def init_ffmpeg_routes(ffmpeg_manager):
    """Inicializa as rotas relacionadas ao ffmpeg."""

    @ffmpeg_bp.route('/start', methods=['POST'])
    def handle_start():
        ffmpeg_manager.clear_buffers()
        ffmpeg_manager.start_ffmpeg_processes()
        return jsonify({"status": "success", "message": "Processos do ffmpeg iniciados."}), 200

    @ffmpeg_bp.route('/record', methods=['POST'])
    def handle_record():
        ffmpeg_manager.record_last_10_seconds()
        return jsonify({"status": "success", "message": "Gravação iniciada"}), 200
    
    @ffmpeg_bp.route('/record/cam1', methods=['POST'])
    def handle_record_cam1():
        ffmpeg_manager.record_last_10_seconds(cam_id=0)
        return jsonify({"status": "success", "message": "Gravação iniciada"}), 200
    
    @ffmpeg_bp.route('/record/cam2', methods=['POST'])
    def handle_record_cam2():
        ffmpeg_manager.record_last_10_seconds(cam_id=1)
        return jsonify({"status": "success", "message": "Gravação iniciada"}), 200

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
    
    return ffmpeg_bp