# Flask Video Effects API - Setup Guide

## 🚀 Quick Start

### 1. Navigate to Flask Backend Directory
```bash
cd "/Users/adityavyas/Desktop/Video Editing Tools/flask_backend"
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Start the Server
```bash
python app.py
```

Or use the startup script:
```bash
./start_server.sh
```

### 4. Test the API
```bash
python test_api.py
```

## 📁 Project Structure

```
flask_backend/
├── app.py                  # Main Flask application
├── effects_engine.py       # Video effects processing engine
├── config.py              # Configuration settings
├── run.py                 # Alternative entry point
├── requirements.txt       # Python dependencies
├── README.md             # Detailed documentation
├── SETUP_GUIDE.md        # This file
├── test_api.py           # API test script
├── start_server.sh       # Startup script
├── .gitignore           # Git ignore rules
├── assets/              # Static assets
│   └── Wikipedia_logo.svg.png
├── uploads/             # Temporary upload directory
└── outputs/             # Generated video output directory
```

## 🎬 Available Effects

The API provides 8 different video effects:

1. **rotation_3d** - 3D rotation animation
2. **ripple_zoom** - Ripple zoom out effect  
3. **zoom_highlight** - Zoom with progressive highlighting
4. **wikipedia_text** - Wikipedia-style text video
5. **font_video** - Dynamic font animation
6. **perspective_transform** - Perspective transformation
7. **perspective_with_highlight** - Perspective with highlighting
8. **ripple_zoom_with_highlight** - Ripple zoom with highlighting

## 🔗 API Endpoints

- **GET** `/` - Health check
- **GET** `/api/effects` - List all effects and parameters
- **POST** `/api/generate/<effect_type>` - Generate video
- **GET** `/api/download/<filename>` - Download video
- **POST** `/api/cleanup` - Clean up old files

## 📝 Usage Example

### Generate a 3D Rotation Video

```bash
curl -X POST \
  -F "image=@your_image.jpg" \
  -F "axis=y" \
  -F "rotation_angle=45" \
  -F "duration=5" \
  -F "fps=30" \
  http://localhost:5000/api/generate/rotation_3d
```

### Response
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

## 🛠️ Configuration

Environment variables (optional):
- `FLASK_ENV`: development/production/testing
- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 5000)
- `MAX_CONTENT_LENGTH`: Max upload size (default: 16MB)

## 🧪 Testing

Run the test suite:
```bash
python test_api.py
```

This will test:
- Health check endpoint
- Effects listing
- Video generation and download

## 🚀 Production Deployment

For production:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 📋 Requirements

- Python 3.7+
- OpenCV 4.9.0.80
- MoviePy 1.0.3
- Flask 3.0.0
- NumPy 1.26.3
- Pillow 10.2.0

## 🔧 Troubleshooting

### Common Issues

1. **Import errors**: Make sure all dependencies are installed
2. **File upload fails**: Check file size (max 16MB) and format
3. **Video generation fails**: Check logs for specific error details
4. **Port already in use**: Change port in config or kill existing process

### Logs

Check the console output for detailed error messages and processing information.

## 🆘 Support

- Check the main README.md for detailed API documentation
- Run `python test_api.py` to verify setup
- Ensure all dependencies are properly installed
- Check file permissions for upload/output directories

## 🎯 Next Steps

1. **Frontend Integration**: Connect with React/Vue.js frontend
2. **Authentication**: Add API key authentication for production
3. **Rate Limiting**: Implement request rate limiting
4. **Monitoring**: Add logging and monitoring for production use
5. **Scaling**: Use Redis/Celery for background processing

---

**Status**: ✅ Ready for use
**Last Updated**: January 2025
