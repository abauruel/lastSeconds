from flask import Blueprint, jsonify, Response, stream_with_context
from .video_thread import VideoCaptureThread
from .show_camera_thread import thread_gen_frames, gen_frames
import threading

bp = Blueprint('api', __name__)

# uri = 'rtsp://admin:L20AB9FE@192.168.1.174:554/cam/realmonitor?channel=1&subtype=0&unicast=true&proto=Onvif'
# uri = 'rtmp://127.0.0.1:1935/live'
# Global video thread instance
video_thread = None

video_thread_1 = None
video_thread_2 = None
isConfiguring = False

@bp.route('/configure', methods=['POST'])
def show_camera_live():
   global isConfiguring
   isConfiguring = not isConfiguring
   print(isConfiguring)
   return jsonify({'message': 'Configuration is enableD.'}), 200
    
@bp.route("/stream/<int:id>")
def stream(id):
    global isConfiguring
    if isConfiguring :
        thread = threading.Thread(target=thread_gen_frames, args=(id,))
        thread.start()
        return Response(
            gen_frames(id), mimetype='multipart/x-mixed-replace; boundary=frame')
    else :
       return jsonify({'message': 'Configuration is not enabled.'}), 428
    

@bp.route('/start_capture', methods=['POST'])
def start_capture():
    global video_thread_1, video_thread_2, isConfiguring
    if isConfiguring is False :
        if (video_thread_1 is None or not video_thread_1.is_alive()) and (video_thread_2 is None or not video_thread_2.is_alive()):
            video_thread_1 = VideoCaptureThread(source=0)  # Camera 1
            video_thread_2 = VideoCaptureThread(source=2)  # Camera 2
            video_thread_1.start()
            video_thread_2.start()
            return jsonify({'message': 'Video capture started.'}), 200
        else:
            return jsonify({'message': 'Video capture is already running.'}), 400
    else :
       return jsonify({'message': 'Configuration is enabled.'}), 428

     
@bp.route('/source/0')
def show_source():
    global video_thread_1
    # if (video_thread_1 is None and video_thread_1.is_alive()):
        # video_thread_1 = VideoCaptureThread(source=0)  # Camera 1
    video_thread_1.get_device_info(0)
    # print(generate_frames(video_thread_1.frames_buffer))
    return Response(stream_with_context(video_thread_1.get_device_info(0)),  mimetype='multipart/x-mixed-replace; boundary=frame' )
    return jsonify({'message': 'Video capture started.'}), 200
    # else:
        # return jsonify({'message': 'Video capture is already running.'}), 400

   
  
@bp.route('/register_buffer', methods=['POST'])
def registerbuffer():
  global video_thread_1, video_thread_2, isConfiguring
  if isConfiguring is False :
    if (video_thread_1 is not None and video_thread_1.is_alive()) and (video_thread_2 is not None and video_thread_2.is_alive()):
        video_thread_1.set_register_buffer()
        video_thread_2.set_register_buffer()
        return jsonify({'message': 'Video buffer registered.'}), 200
    else:
        return jsonify({'message': 'Video buffer is not running.'}), 400
  else :
       return jsonify({'message': 'Configuration is enabled.'}), 428