# Flask Video Effects API

A standalone Flask backend for generating videos with various visual effects from static images.

## Features

- **8 Different Video Effects**: 3D rotation, ripple zoom, zoom highlight, Wikipedia text, font video, perspective transform, and more
- **RESTful API**: Simple HTTP endpoints for effect generation
- **File Upload Support**: Supports PNG, JPG, JPEG, GIF, BMP, and WebP formats
- **Configurable Parameters**: Customize duration, FPS, zoom factors, colors, and more
- **Automatic Cleanup**: Removes old files to prevent disk space issues
- **CORS Enabled**: Ready for frontend integration

## Quick Start

### 1. Install Dependencies

```bash
cd flask_backend
pip install -r requirements.txt
```

### 2. Run the Server

```bash
python app.py
```

Or using the run script:

```bash
python run.py
```

The API will be available at `http://localhost:5000`

### 3. Test the API

Check if the server is running:

```bash
curl http://localhost:5000/
```

List available effects:

```bash
curl http://localhost:5000/api/effects
```

## API Endpoints

### Health Check
- **GET** `/` - Returns server status and available effects

### Effects Management
- **GET** `/api/effects` - List all available effects with parameters
- **POST** `/api/generate/<effect_type>` - Generate video with specified effect
- **GET** `/api/download/<filename>` - Download generated video file
- **POST** `/api/cleanup` - Clean up old files (maintenance)

## Available Effects

1. **rotation_3d** - 3D rotation animation
2. **ripple_zoom** - Ripple zoom out effect
3. **zoom_highlight** - Zoom with progressive highlighting
4. **wikipedia_text** - Wikipedia-style text video
5. **font_video** - Dynamic font animation
6. **perspective_transform** - Perspective transformation
7. **perspective_with_highlight** - Perspective with highlighting
8. **ripple_zoom_with_highlight** - Ripple zoom with highlighting

## Usage Example

### Generate a 3D Rotation Effect

```bash
curl -X POST \
  -F "image=@your_image.jpg" \
  -F "axis=y" \
  -F "rotation_angle=45" \
  -F "duration=5" \
  -F "fps=30" \
  http://localhost:5000/api/generate/rotation_3d
```

Response:
```json
{
  "success": true,
  "message": "Video generated successfully",
  "video_id": "abc123def456",
  "download_url": "/api/download/abc123def456_rotation_3d.mp4",
  "processing_time": 12.34,
  "effect_type": "rotation_3d",
  "parameters": {
    "axis": "y",
    "rotation_angle": 45,
    "duration": 5,
    "fps": 30
  }
}
```

### Download the Generated Video

```bash
curl -O http://localhost:5000/api/download/abc123def456_rotation_3d.mp4
```

## Configuration

The application can be configured through environment variables or by modifying `config.py`:

- `FLASK_ENV`: Environment (development/production/testing)
- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 5000)
- `MAX_CONTENT_LENGTH`: Maximum file upload size (default: 16MB)
- `UPLOAD_FOLDER`: Directory for uploaded files (default: uploads)
- `OUTPUT_FOLDER`: Directory for generated videos (default: outputs)

## Effect Parameters

Each effect supports different parameters. Use the `/api/effects` endpoint to see all available parameters for each effect.

### Common Parameters
- `duration`: Video duration in seconds (1-30)
- `fps`: Frames per second (15-60)

### Effect-Specific Parameters
- **rotation_3d**: `axis`, `rotation_angle`
- **ripple_zoom**: `zoom_factor`, `ripple_strength`
- **zoom_highlight**: `zoom_factor`, `highlight_color`
- **wikipedia_text**: `text_content`, `aspect_ratio`
- **font_video**: `text_content`, `font_changes`, `zoom_effect`
- **perspective_transform**: `perspective_strength`, `zoom_factor`

## File Management

- Uploaded files are automatically cleaned up after processing
- Generated videos are kept for 1 hour by default
- Use the `/api/cleanup` endpoint to manually trigger cleanup
- Maximum file size: 16MB

## Production Deployment

For production deployment:

1. Set `FLASK_ENV=production`
2. Use a production WSGI server like Gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

3. Configure reverse proxy (nginx) for better performance
4. Set up proper logging and monitoring

## Error Handling

The API returns appropriate HTTP status codes:
- `200`: Success
- `400`: Bad request (invalid parameters, missing file)
- `404`: File not found
- `413`: File too large
- `500`: Internal server error

All error responses include a JSON object with `success: false` and an `error` message.

## Dependencies

- Flask 3.0.0 - Web framework
- OpenCV 4.9.0.80 - Image processing
- MoviePy 1.0.3 - Video generation
- NumPy 1.26.3 - Numerical operations
- Pillow 10.2.0 - Image handling
- Flask-CORS 4.0.0 - Cross-origin requests

## License

This project is part of the Video Editing Tools suite.
