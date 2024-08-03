### stream video and set to rmtp server
ffmpeg -loglevel verbose -re -i SS5-Grupo2-Cloud.mp4  -vcodec libx264 \
-vprofile baseline  \
-f flv rtmp://localhost:1935/live

## strem video(set looping infinity) and send to rmtp server 
ffmpeg -stream_loop -1 -loglevel verbose -re -i SS5-Grupo2-Cloud.mp4  -vcodec libx264 \
-vprofile baseline  \
-f flv rtmp://127.0.0.1:1935/live

##
ffmpeg -f v4l2  -video_size 1280x720 -thread_queue_size 512 -framerate 25 -i /dev/video0 -vf fps=24 -c:v libx264 -r 24 camera0_output.mp4

ffmpeg -f v4l2  -video_size 1280x720 -framerate 25 -i /dev/video2  -vf fps=24 -c:v libx264 -r 24 camera2_output.mp4

ffmpeg -f v4l2 -framerate 24 -video_size 1280x720 -thread_queue_size 512 -i /dev/video0 -r 24 output.mp4
ffmpeg -f v4l2 -framerate 24 -thread_queue_size 1024 -i /dev/video2 -r 24 output2.mp4


ffmpeg -f v4l2 -video_size 1280x720 -i /dev/video0 -c:v h264_v4l2m2m -vf fps=24 -r 24  output.mp4
ffmpeg -f v4l2 -video_size 1280x720 -i /dev/video2 -c:v h264 -vf fps=24 -r 24 -max_muxing_queue_size 9999 output2.mp4

ffmpeg -f v4l2 -video_size 1280x720 -i /dev/video2 -c:v h264_v4l2m2m -vf fps=24 -r 24 -max_muxing_queue_size 9999 output2.mp4

v4l2-ctl --list-formats-ext -d /dev/video0

ffmpeg -f v4l2 -framerate 25 -video_size 1280x720 -i /dev/video0 -c:v h264_omx -b:v 2M -r 25 output.mp4

ffmpeg -f v4l2 -input_format h264 -framerate 25 -video_size 2560x1440 -i /dev/video0 -c:v copy output.mp4
