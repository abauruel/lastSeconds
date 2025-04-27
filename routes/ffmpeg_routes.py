from flask import Blueprint, jsonify

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

    @ffmpeg_bp.route('/stop', methods=['POST'])
    def handle_stop():
        ffmpeg_manager.stop_ffmpeg_processes()
        return jsonify({"status": "success", "message": "Processos do ffmpeg finalizados."}), 200


    @ffmpeg_bp.route('/clear_buffers', methods=['POST'])
    def handle_clear_buffers():
        ffmpeg_manager.clear_buffers()
        return jsonify({"status": "success", "message": "Buffers limpos com sucesso."}), 200
    
    return ffmpeg_bp