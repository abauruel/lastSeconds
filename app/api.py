from flask import Blueprint, jsonify
from .video_thread import VideoCaptureThread

bp = Blueprint('api', __name__)

# Global video thread instance
video_thread = None


@bp.route('/start_buffer', methods=['POST'])
def start_buffer():
  global video_thread

  if video_thread is not None and video_thread.is_alive():
    video_thread.get_start_buffer()

    return jsonify({'message': 'Video buffer started.'}), 200
  else:
    return jsonify({'message': 'Video buffer is already running.'}), 400

@bp.route('/register_buffer', methods=['POST'])
def registerbuffer():
  global video_thread

  if video_thread is not None and video_thread.is_alive():
    video_thread.get_registerbuffer()
    return jsonify({'message': 'Video buffer registered.'}), 200
  else:
    return jsonify({'message': 'Video buffer is not running.'}), 400
  
@bp.route('/start_capture', methods=['POST'])
def start_capture():
    global video_thread

    if video_thread is None or not video_thread.is_alive():
        video_thread = VideoCaptureThread()
        video_thread.start()
        return jsonify({'message': 'Video capture started.'}), 200
    else:
        return jsonify({'message': 'Video capture is already running.'}), 400

@bp.route('/stop_capture', methods=['POST'])
def stop_capture():
    global video_thread

    if video_thread is not None and video_thread.is_alive():
        video_thread.stop()
        video_thread.join()
        return jsonify({'message': 'Video capture stopped.'}), 200
    else:
        return jsonify({'message': 'Video capture is not running.'}), 400
