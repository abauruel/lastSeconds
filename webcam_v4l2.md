## compile 
g++ webcam_v4l2.cpp -o webcam_v4l2 `pkg-config --cflags --libs libv4l2` -lSDL2
