import cv2
import threading
import datetime
from collections import deque

class VideoCaptureThread(threading.Thread):
    def __init__(self, source=0):
        super(VideoCaptureThread, self).__init__()
        self.source = source
        self.stopped = False
        self.frame = None
        self.start_buffer = False
        self.register_buffer = False

    def run(self):
        # Open the video capture
        cap = cv2.VideoCapture(self.source)
        # Get the frame width and height from the capture
        frame_width= int(cap.get(3))
        frame_height= int(cap.get(4))
        frame_buffer = deque(maxlen=240)

        size = (frame_width, frame_height)
        
        # Create the video writer
        
        # Check if the capture is open
        if not cap.isOpened():
            print(f"Error: Could not open video source {self.source}")
            return
        
        while not self.stopped:
            # Capture frame-by-frame
            ret, frame = cap.read()
            if not ret:
                print("Error: Failed to capture frame")
                break
            
            if self.start_buffer:
                # Check if the frame buffer is full
                if len(frame_buffer) == 240:
                    frame_buffer.popleft()

                # Append the frame to the frame buffer
                frame_buffer.append(frame)
            
            if self.register_buffer:
                current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                filename = f"output_{current_time}.mp4"
                highlight_writer = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*'mp4v'), 24, size)
                for fps in frame_buffer:
                    highlight_writer.write(fps)
                highlight_writer.release()
                self.register_buffer = False
            # Store the frame
            self.frame = frame
        
        # Release the capture when the thread is stopped
        cap.release()

    def stop(self):
        self.stopped = True

    def get_frame(self):
        return self.frame
    
    def get_start_buffer(self):
        self.start_buffer = True

    def get_registerbuffer(self):
        self.register_buffer = True