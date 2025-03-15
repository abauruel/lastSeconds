from flask import Blueprint, jsonify, Response, stream_with_context, request

from .audio_player import play_song
from .video_thread import VideoCaptureThread
from .show_camera_thread import thread_gen_frames, gen_frames
from convert_videos import listar_arquivos_sem_extensao
import threading
import os


bp = Blueprint('api', __name__)

# uri = 'rtsp://admin:L20AB9FE@192.168.1.174:554/cam/realmonitor?channel=1&subtype=0&unicast=true&proto=Onvif'
# uri = 'rtmp://127.0.0.1:1935/live'
# Global video thread instance
video_stream_1 = None
video_stream_2 = None

video_thread_1 = None
video_thread_2 = None
isConfiguring = False




@bp.route('/configure', methods=['POST'])
def show_camera_live():
   global isConfiguring, video_stream_1, video_stream_2
   configuring = request.get_json()
   isConfiguring = configuring.get('configure')
   if isConfiguring == False :
        if video_stream_1 is not None :
            print("Stopping video stream 1...")
            video_stream_1.join()
            video_stream_1 = None
            
        if video_stream_2 is not None:
            print("Stopping video stream 2...")
            video_stream_2.join()
            video_stream_2 = None
        
        return jsonify({'message': 'Configuration is disabled.'}), 200
   else:
    return jsonify({'message': 'Configuration is enableD.'}), 200

    
@bp.route("/stream/<int:id>")
def stream(id):
    global isConfiguring, video_stream_1, video_stream_2
    if isConfiguring :
        if (video_stream_1 is None or not video_stream_1.is_alive()) and (video_stream_2 is None or not video_stream_2.is_alive()):
            if int(id) == 0 :
                video_stream_1 = threading.Thread(target=thread_gen_frames, args=(id,))
                video_stream_1.start()
                return Response(
                    gen_frames(id), mimetype='multipart/x-mixed-replace; boundary=frame')

            if int(id) == 2 :
                video_stream_2 = threading.Thread(target=thread_gen_frames, args=(id,))
                video_stream_2.start()
                return Response(
                    gen_frames(id), mimetype='multipart/x-mixed-replace; boundary=frame')
    else :
       
       return jsonify({'message': 'Configuration is not enabled.'}), 428
    

@bp.route('/start_capture', methods=['POST'])
def start_capture():
    global video_thread_1, video_thread_2, isConfiguring
    print(isConfiguring)
    if isConfiguring is False :
        if (video_thread_1 is None or not video_thread_1.is_alive()) and (video_thread_2 is None or not video_thread_2.is_alive()):
            video_thread_1 = VideoCaptureThread(source=0)  # Camera 1
            video_thread_2 = VideoCaptureThread(source=2)  # Camera 2
            video_thread_1.start()
            video_thread_2.start()
            play_song(1)
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
def register_buffer():
  global video_thread_1, video_thread_2, isConfiguring
  if isConfiguring is False :
    if (video_thread_1 is not None and video_thread_1.is_alive()) and (video_thread_2 is not None and video_thread_2.is_alive()):
        video_thread_1.set_register_buffer()
        video_thread_2.set_register_buffer()
        play_song(0)
        return jsonify({'message': 'Video buffer registered.'}), 200
    else:
        return jsonify({'message': 'Video buffer is not running.'}), 400
  else :
       return jsonify({'message': 'Configuration is enabled.'}), 428




@bp.route('/stop_capture', methods=['POST'])
def stop_capture():
    global video_thread_1, video_thread_2, isConfiguring
    if isConfiguring is False :
        if (video_thread_1.is_alive()) or (video_thread_2.is_alive()):
            video_thread_1.stop()
            video_thread_2.stop()
            print("convert videos")
            listar_arquivos_sem_extensao('output')

            return jsonify({'message': 'Video capture is stopped.'}), 200
        else:
            return jsonify({'message': 'Video capture is not running.'}), 400
    else :
       return jsonify({'message': 'Configuration is enabled.'}), 428
    
@bp.route('/convert_files', methods=['POST'])
def convert_files():
    global video_thread_1, video_thread_2, isConfiguring
    if isConfiguring is False :
        if (video_thread_1 is None or not video_thread_1.is_alive()) and (video_thread_2 is None or not video_thread_2.is_alive()):
            listar_arquivos_sem_extensao('output')
            return jsonify({'message': 'Video converted.'}), 200
        else:
            return jsonify({'message': 'Cannot convert videos'}), 400
    else :
       return jsonify({'message': 'Configuration is enabled.'}), 428
    


