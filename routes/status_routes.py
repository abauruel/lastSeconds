from flask import Blueprint, jsonify

# Cria um blueprint para as rotas de status
status_bp = Blueprint('status', __name__)

def init_status_routes():
    """Inicializa as rotas relacionadas ao status."""

    @status_bp.route('/status', methods=['GET'])
    def status():
        return jsonify({"status": "running"}), 200

    return status_bp