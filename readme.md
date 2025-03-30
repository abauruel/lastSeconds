# **Video Recording and Streaming Application**

This application is a Python-based video recording and streaming server built using Flask and FFmpeg. It provides APIs for managing video streams, recording segments, generating thumbnails, and cleaning up buffers.

---

## **Features**
- **Video Streaming**:
  - Streams video from two cameras (video0 and video2) using FFmpeg.
  - Supports real-time streaming via RTMP.

- **Buffer Management**:
  - Stores video segments in circular buffers for each camera.
  - Buffers are saved in the buffers directory.

- **Recording**:
  - Combines the last 10 seconds of video segments into a single file.
  - Saves recordings in the streams directory.

- **Thumbnail Generation**:
  - Generates a thumbnail for each recorded video.

- **API Endpoints**:
  - Start/stop video streaming.
  - Record the last 10 seconds of video.
  - Clear video buffers.

---

## **Directory Structure**
```
recordings/
├── buffers/
│   ├── video0/  # Buffer for /dev/video0
│   └── video2/  # Buffer for /dev/video2
├── streams/     # Final recorded videos
└── recordings/  # Processed recordings
```

---

## **Setup Instructions**

### **Prerequisites**
1. Python 3.8 or higher.
2. FFmpeg installed on the system.
3. Flask and required Python dependencies.

### **Installation**
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Ensure FFmpeg is installed:
   ```bash
   sudo apt install ffmpeg
   ```

4. Run the application:
   ```bash
   python capture3.py
   ```

---

## **API Endpoints**

### **1. Start Streaming**
- **Endpoint**: `/start`
- **Method**: `POST`
- **Description**: Starts the FFmpeg processes for video streaming.
- **Response**:
  ```json
  {
    "status": "success",
    "message": "FFmpeg processes started."
  }
  ```

---

### **2. Record Last 10 Seconds**
- **Endpoint**: `/record`
- **Method**: `POST`
- **Description**: Combines the last 10 seconds of video segments into a single file.
- **Response**:
  ```json
  {
    "status": "success",
    "message": "Recording started."
  }
  ```

---

### **3. Stop Streaming**
- **Endpoint**: `/stop`
- **Method**: `POST`
- **Description**: Stops the FFmpeg processes and combines all buffer segments into a final video file.
- **Response**:
  ```json
  {
    "status": "success",
    "message": "Processes stopped and buffers combined."
  }
  ```

---

### **4. Clear Buffers**
- **Endpoint**: `/clear_buffers`
- **Method**: `POST`
- **Description**: Deletes all files in the `buffers/video0` and `buffers/video2` directories.
- **Response**:
  ```json
  {
    "status": "success",
    "message": "Buffers cleared successfully."
  }
  ```

---

### **5. Server Status**
- **Endpoint**: `/status`
- **Method**: `GET`
- **Description**: Checks if the server is running.
- **Response**:
  ```json
  {
    "status": "running"
  }
  ```

---

## **Functions**

### **1. `start_ffmpeg_processes()`**
- Starts FFmpeg processes for video0 and video2.
- Saves video segments in circular buffers.

### **2. `combine_segments(segment_files, output_file, temp_file)`**
- Combines multiple video segments into a single file using FFmpeg.

### **3. `record_last_10_seconds()`**
- Combines the last 10 seconds of video segments into a single file.
- Saves the output in the streams directory.

### **4. `generateThumb(file)`**
- Generates a thumbnail for a given video file using FFmpeg.

### **5. `clear_buffers()`**
- Deletes all files in the `buffers/video0` and `buffers/video2` directories.

### **6. `cleanup()`**
- Terminates all FFmpeg processes gracefully.

---

## **Error Handling**
- If any error occurs during file operations or FFmpeg execution, appropriate error messages are logged, and a `500` status code is returned.

---

## **Example Usage**

### **Start Streaming**
```bash
curl -X POST http://localhost:5000/start
```

### **Record Last 10 Seconds**
```bash
curl -X POST http://localhost:5000/record
```

### **Stop Streaming**
```bash
curl -X POST http://localhost:5000/stop
```

### **Clear Buffers**
```bash
curl -X POST http://localhost:5000/clear_buffers
```

### **Check Server Status**
```bash
curl -X GET http://localhost:5000/status
```

---

## **Dependencies**
- **Python Libraries**:
  - Flask
  - subprocess (built-in)
  - os (built-in)
  - datetime (built-in)

- **External Tools**:
  - FFmpeg

---

## **Known Issues**
1. **Buffer Overwrite**:
   - If the buffer size exceeds the limit, older segments are overwritten.

2. **Thumbnail Generation**:
   - If FFmpeg fails to generate a thumbnail, the process continues without it.

---

## **Future Improvements**
1. Add authentication for API endpoints.
2. Implement a web-based dashboard for managing recordings.
3. Add support for more video formats and resolutions.
4. Optimize FFmpeg commands for better performance.

---

## **License**
This project is licensed under the MIT License.

--- 
