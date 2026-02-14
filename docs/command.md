```shell
```shell
# Capture video from a 3MP webcam with increased bitrate and quality
ffmpeg -loglevel info -fflags +genpts -f v4l2 -input_format h264 -video_size 2048x1536 -r 30 -i /dev/video0 \
-use_wallclock_as_timestamps 1 -fps_mode vfr \
-c:v copy -crf 18 -f segment -segment_time 1 -segment_format mp4 \
-reset_timestamps 1 -segment_wrap 100 \
"/path/to/buffer_dir_video0/buffer_video0_%03d.mp4" \
-c:v copy -preset ultrafast -tune zerolatency -b:v 8M -maxrate 8M -bufsize 8M -an -f flv rtmp://localhost/live/stream1

# Alternative: Save to MP4 with hardware encoding, 3MP resolution, and higher bitrate
ffmpeg -f v4l2 -video_size 2048x1536 -i /dev/video0 -c:v h264_v4l2m2m -vf fps=24 -r 24 -b:v 8M -maxrate 8M -bufsize 8M output.mp4
```
HEV
2560x1440 30FPS

MJPEG
2560X1440 30FPS

v4l2-ctl -d /dev/video0 --set-fmt-video=width=2560,height=1440,pixelformat=MJPG
v4l2-ctl -d /dev/video2 --set-fmt-video=width=2560,height=1440,pixelformat=H264

ffmpeg -f v4l2 -framerate 30 -input_format h264 -video_size 1920x1080 -i /dev/video2 \
-vf "format=yuv420p,eq=contrast=1.05:saturation=1.1" \
-c:v h264_v4l2m2m -b:v 7M -maxrate 8M -bufsize 16M -r 30 output.mp4
