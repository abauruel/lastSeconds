import threading
from datetime import datetime
from collections import deque
# from .save_file import SaveFile


from linuxpy.video.device import Device, BufferType, Memory, VideoCapture, VideoOutput
import time

def saveFile(source, buffer):
        now = datetime.now()
        output_file = f'output/cam_{source}_{now.strftime("%Y%m%d_%H%M%S")}'
        with open(output_file, 'wb') as video_file:
            for frame in buffer:
                video_file.write(frame.data)
            


class VideoCaptureThread(threading.Thread):
    def __init__(self, source=0, buffer_size=168, devices_running=[]):
        super(VideoCaptureThread, self).__init__()
        self.source = source
        self._stop_event = threading.Event()
        self.fps = 25
        self.register_buffer = False
        
        
      

    
            
    def run(self):
        # Open the video capture
        duration = 7
        total_frame = self.fps*(duration+2)
        frame_count = 0
        frame_buffer = deque(maxlen=total_frame)
       
        with Device.from_id(self.source) as device:
            device.set_format(BufferType.VIDEO_CAPTURE, 1280, 720, "H264")
            device.set_fps( BufferType.VIDEO_CAPTURE, self.fps)
            start_time = time.time()
            print(frame_buffer)
        
            
            # try:
            while not self._stop_event.is_set():
                # Capture frame-by-frame
                for frame in device:
                    frame_count += 1
                    if self._stop_event.is_set():
                        return
                    # Calcular o tempo decorrido
                    elapsed_time = time.time() - start_time

                    # Calcular FPS
                    fps = frame_count / elapsed_time
                    # print(f"cam {self.source} fps: {fps :.2f}")
                    # Calcular o tempo decorrido
                    # print(f"fps => {fps}")
                    elapsed_time = time.time() - start_time
                    if len(frame_buffer) == total_frame:
                        frame_buffer.popleft()
                    # Append the frame to the frame buffer
                    frame_buffer.append(frame)
                    
                    # yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame_coverted + b"\r\n"

                    
                    if self.register_buffer:
                        saveFile(self.source, frame_buffer)
                        self.register_buffer = False
            print(f"Encerrando gravação para a câmera {self.source}")
                    
                    
    def stop(self):
        self._stop_event.set()
        

    def set_register_buffer(self):
        self.register_buffer = True

