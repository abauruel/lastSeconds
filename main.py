
import cv2
import numpy as np
from collections import deque
import datetime

uri = ''
cap = cv2.VideoCapture(uri)


if not cap.isOpened():
    print("Error: Couldn;t open the video stream.")
    exit()

frame_width= int(cap.get(3))
frame_height= int(cap.get(4))

size = (frame_width, frame_height)

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
frame_buffer = deque(maxlen=240)

recording = False

while (cap.isOpened()):
    ret, frame = cap.read()
    if ret:
        cv2.imshow("frame", frame)
        
        
        if(len(frame_buffer)==240):
            frame_buffer.popleft()

        frame_buffer.append(frame)
        # out.write(frame)


        
        # Press 'r' to start recording last 10 seconds
        key = cv2.waitKey(1) & 0xFF
        # if key == ord('r'):
        #     recording = True
        #     frame_buffer.clear() # clear the buffer
        #     print('Recording started...')
        
        # Press 's' to save the last 10 seconds to a file
        if key == ord('s'):
            # recording = False
            # print('Recording stopped and saving last 10 seconds...')

            # Generate a unique filename based on current date and time
           
            current_time2 = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename2 = f"output_{current_time2}.mp4"
            out3 = cv2.VideoWriter(filename2, fourcc, 24,size)
            for fps in frame_buffer:
                out3.write(fps)
            out3.release()
            print('last 10 seconds saved successfully.')
            # recording= True

            #teste
        # out.write(frame)
            # Press 'q' to exit
        if key == ord('q'):
            break
    else:
        break

   
cap.release()
# out.release()
cv2.destroyAllWindows()

def currentFileName():
    return  datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")