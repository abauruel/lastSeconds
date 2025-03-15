### Capture a raw video stream from video device:
```v4l2-ctl --device /dev/video0 --set-fmt-video=width=1280,height=720,pixelformat=format --stream-mmap --stream-to=path/to/output --stream-count=number_of_frames_to_capture
```

### Capture a JPEG photo with a specific resolution from video device:
```v4l2-ctl --device /dev/video0 --set-fmt-video=width=1280,height=720,pixelformat=MJPG --stream-mmap --stream-to=output/output.jpg --stream-count=1
```

https://www.mankier.com/1/v4l2-ctl

### List all video devices:
v4l2-ctl --list-devices

### Capture a raw video stream from video device:
v4l2-ctl --device /dev/video2 --set-fmt-video=width=1280,height=720,pixelformat=H264 --stream-mmap --stream-to=output/video_cam2_hevc.raw --stream-count=125

h265 = HEVC

## Convert video raw from 
ffmpeg -i output/video_cam0.raw -c:v copy output/video_cam0.mp4

v4l2-ctl --device /dev/video2 --set-fmt-video=width=1280,height=720,pixelformat=H264 --stream-mmap --stream-to=- | ffmpeg -f rawvideo -pix_fmt yuv420p -s 1280x720 -i - \
  -vcodec libx264 -preset ultrafast -tune zerolatency -r 24 \
  -f flv rtmp://localhost/hls