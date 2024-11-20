import threading
from datetime import datetime
from collections import deque
# from .save_file import SaveFile


from linuxpy.video.device import Device, BufferType, Memory, VideoCapture, VideoOutput
import time


def gen_frames(source):
    # Variáveis para calcular o FPS
    frame_count = 0
    start_time = time.time()
    with Device.from_id(int(source)) as cam:
     

        cam.set_format(BufferType.VIDEO_CAPTURE,620, 480, "MJPG")
        cam.set_fps( BufferType.VIDEO_CAPTURE, 15)
        print(cam.get_format(BufferType.VIDEO_CAPTURE))
        print(cam.get_fps(BufferType.VIDEO_CAPTURE)) 
      
        with cam:
            for frame in cam:
                # Contar o número de frames
                frame_count += 1
                
                # Calcular o tempo decorrido
                elapsed_time = time.time() - start_time

                # Calcular FPS
                fps = frame_count / elapsed_time
                print(f"cam {source} fps: {fps :.2f}")

                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame.data + b"\r\n"

def thread_gen_frames(source):
    return gen_frames(source)
                    
    

    

