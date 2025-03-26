#include <iostream>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <linux/videodev2.h>
#include <sys/mman.h>
#include <cstring>
#include <cstdio>
#include <thread>

void capture_and_transmit(const char* device, const char* rtmp_url) {
    int fd = open(device, O_RDWR);
    if (fd == -1) {
        std::cerr << "Erro ao abrir o dispositivo " << device << std::endl;
        return;
    }

    v4l2_capability cap;
    if (ioctl(fd, VIDIOC_QUERYCAP, &cap) == -1) {
        std::cerr << "Erro ao consultar capacidades do dispositivo " << device << std::endl;
        close(fd);
        return;
    }

    v4l2_format fmt;
    fmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    fmt.fmt.pix.width = 640;
    fmt.fmt.pix.height = 480;
    fmt.fmt.pix.pixelformat = V4L2_PIX_FMT_MJPEG; // ou outro formato suportado pela sua webcam
    if (ioctl(fd, VIDIOC_S_FMT, &fmt) == -1) {
        std::cerr << "Erro ao configurar o formato do vídeo " << device << std::endl;
        close(fd);
        return;
    }

    v4l2_requestbuffers req;
    req.count = 4;
    req.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    req.memory = V4L2_MEMORY_MMAP;
    if (ioctl(fd, VIDIOC_REQBUFS, &req) == -1) {
        std::cerr << "Erro ao solicitar buffers " << device << std::endl;
        close(fd);
        return;
    }

    v4l2_buffer buf;
    buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    buf.memory = V4L2_MEMORY_MMAP;
    buf.index = 0;
    if (ioctl(fd, VIDIOC_QUERYBUF, &buf) == -1) {
        std::cerr << "Erro ao consultar buffer " << device << std::endl;
        close(fd);
        return;
    }

    void* buffer = mmap(NULL, buf.length, PROT_READ | PROT_WRITE, MAP_SHARED, fd, buf.m.offset);
    if (buffer == MAP_FAILED) {
        std::cerr << "Erro ao mapear buffer " << device << std::endl;
        close(fd);
        return;
    }

    v4l2_buffer queue_buf;
    queue_buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    queue_buf.memory = V4L2_MEMORY_MMAP;
    queue_buf.index = 0;
    if (ioctl(fd, VIDIOC_QBUF, &queue_buf) == -1) {
        std::cerr << "Erro ao enfileirar buffer " << device << std::endl;
        munmap(buffer, buf.length);
        close(fd);
        return;
    }

    v4l2_buf_type type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    if (ioctl(fd, VIDIOC_STREAMON, &type) == -1) {
        std::cerr << "Erro ao iniciar streaming " << device << std::endl;
        munmap(buffer, buf.length);
        close(fd);
        return;
    }

    char ffmpeg_command[2048];
    snprintf(ffmpeg_command, sizeof(ffmpeg_command),
            // "ffmpeg -i pipe:0  -vcodec libx264  -f flv %s",
            //  "ffmpeg -f mjpeg -framerate 30 -i pipe:0 -c:v libx264 -preset ultrafast -crf 23 -tune zerolatency -f flv %s",
             "ffmpeg -i pipe:0 -s 1280x720 -r 25 -c:v libx264  -preset ultrafast -tune zerolatency -b:v 2M -f flv %s",

             rtmp_url);

    FILE* ffmpeg_pipe = popen(ffmpeg_command, "w");
    if (!ffmpeg_pipe) {
        std::cerr << "Erro ao abrir pipe do FFmpeg " << device << std::endl;
        ioctl(fd, VIDIOC_STREAMOFF, &type);
        munmap(buffer, buf.length);
        close(fd);
        return;
    }

    while (true) {
        v4l2_buffer dequeue_buf;
        dequeue_buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
        dequeue_buf.memory = V4L2_MEMORY_MMAP;
        if (ioctl(fd, VIDIOC_DQBUF, &dequeue_buf) == -1) {
            std::cerr << "Erro ao desenfileirar buffer " << device << std::endl;
            break;
        }

        fwrite(buffer, buf.length, 1, ffmpeg_pipe);

        if (ioctl(fd, VIDIOC_QBUF, &dequeue_buf) == -1) {
            std::cerr << "Erro ao enfileirar buffer " << device << std::endl;
            break;
        }
    }

    ioctl(fd, VIDIOC_STREAMOFF, &type);
    munmap(buffer, buf.length);
    close(fd);
    pclose(ffmpeg_pipe);
}

int main() {
    const char* rtmp_url1 = "rtmp://localhost/live/stream1";
    const char* rtmp_url2 = "rtmp://localhost/live/stream2";

    std::thread thread1(capture_and_transmit, "/dev/video0", rtmp_url1);
    std::thread thread2(capture_and_transmit, "/dev/video2", rtmp_url2);

    thread1.join();
    thread2.join();

    return 0;
}