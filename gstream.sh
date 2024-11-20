#!/bin/bash

# Define the output files and the duration of the recording (in seconds)
OUTPUT_FILE1="output_video1.mp4"
OUTPUT_FILE2="output_video2.mp4"
DURATION=10

# Command to capture video from the first webcam and save it to a file
timeout $DURATION gst-launch-1.0 -e \
  v4l2src device=/dev/video0 ! videoconvert ! videoscale ! videorate ! video/x-raw,width=1280,height=720,framerate=30/1 ! x264enc bitrate=2048 ! mp4mux ! filesink location=$OUTPUT_FILE1 -e \
