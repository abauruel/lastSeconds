# Video Uploader Service

A systemd service that automatically uploads recorded videos to a remote server. The service monitors a local database for videos with "pending" status and uploads them along with their thumbnails.

## Features

- Automated video uploading every 15 minutes
- Internet connectivity check before upload attempts
- Thumbnail support
- Duplicate file detection
- Pre-signed URL generation for secure uploads
- Automatic retry on failure
- Database status tracking (pending, sent, deleted)
- Systemd service integration
- Tagged logging for easy filtering ([video_upload])

## Requirements

- Python 3.x
- Required Python packages (install via pip):
  ```bash
  pip install -r requirements_uploader.txt
  ```
- systemd (for service management)
- Network connectivity
- Write access to the video directory

## Configuration

### Environment Variables

- `API_BASE_URL`: The base URL for the upload API (default: "http://registroesportivo.com.br/api")
- `API_TOKEN`: Authentication token for the API

### Service Configuration

The service is configured to:
- Run as the 'pi' user
- Auto-restart on failure (10-second delay)
- Start after network is available
- Work from `/home/pi/app` directory

## Installation

1. Ensure Python dependencies are installed:
   ```bash
   pip install -r requirements_uploader.txt
   ```

2. Copy the service file to systemd:
   ```bash
   sudo cp video_uploader.service /etc/systemd/system/
   ```

3. Reload systemd daemon:
   ```bash
   sudo systemctl daemon-reload
   ```

4. Enable and start the service:
   ```bash
   sudo systemctl enable video_uploader
   sudo systemctl start video_uploader
   ```

## Service Management

### Start the service
```bash
sudo systemctl start video_uploader
```

### Stop the service
```bash
sudo systemctl stop video_uploader
```

### Check service status
```bash
sudo systemctl status video_uploader
```

### View logs

View all logs:
```bash
sudo journalctl -u video_uploader -f
```

Filter logs for video upload operations:
```bash
sudo journalctl -u video_uploader -f | grep "\[video_upload\]"
```

## Video Processing Flow

1. **Internet Check**: Verifies internet connectivity before starting operations
2. **Scan**: Every 15 minutes, scans database for videos with "pending" status
3. **Check**: Verifies if video file exists locally
4. **Duplicate Check**: Checks if video already exists on remote server
4. **Upload Process**:
   - Generate pre-signed URL for upload
   - Upload video file
   - If exists, upload thumbnail
   - Register video with remote server
   - Update database status to "sent"

## Error Handling

- Internet connection: Checks connection before attempting uploads
- Network failures: Service will retry on next scheduled run
- Missing files: Logs error and continues with next file
- API errors: Full error logging with HTTP status codes
- Database errors: Transaction rollback on failure

All errors are logged with the [video_upload] tag for easy filtering and debugging.

## API Endpoints Used

### Generate Upload URL
- **Endpoint**: `/generate_upload_url`
- **Method**: POST
- **Headers**: 
  - x-api-token
  - Content-Type: application/json
- **Body**: `{"filename": "video_name.mp4"}`

### Check File Exists
- **Endpoint**: `/media_events`
- **Method**: GET
- **Query Params**: `filename`

### Register Video
- **Endpoint**: `/media_events`
- **Method**: POST
- **Body**: 
  ```json
  {
    "filename": "video_name.mp4",
    "thumbnail_url": "video_name.mp4.jpeg" // Optional
  }
  ```

## File Structure
```
/recordings/streams/
├── [date_folders]/
    └── video_files.mp4
    └── video_files.mp4.jpeg
```

## Database Schema

Videos are tracked in the database with the following status values:
- `PENDING`: Ready for upload
- `SENT`: Successfully uploaded
- `DELETED`: Marked for deletion

## Troubleshooting

1. **Service won't start**:
   - Check logs: `sudo journalctl -u video_uploader -n 50`
   - Verify Python dependencies
   - Check file permissions

2. **Videos not uploading**:
   - Verify network connectivity
   - Check API token validity
   - Ensure video files exist in correct location
   - Verify database connection

3. **High CPU/Memory Usage**:
   - Check size of pending videos queue
   - Verify disk space availability
   - Monitor network bandwidth

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License.