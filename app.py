"""
Flask API for Video Effects Generation
Simple API that generates videos with various effects
"""
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import time
import uuid
import logging
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from supabase import create_client


# Import our video effects engine
from effects_engine import EFFECT_REGISTRY, process_video_effect

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "videos")
supabase_client = (
    create_client(SUPABASE_URL, SUPABASE_KEY)
    if SUPABASE_URL and SUPABASE_KEY
    else None
)

# Create directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Allowed image extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Video Effects API',
        'version': '1.0.0',
        'available_effects': list(EFFECT_REGISTRY.keys())
    })

@app.route('/api/effects', methods=['GET'])
def list_effects():
    """List all available effects with their parameters"""
    effects_info = {
        'rotation_3d': {
            'name': '3D Rotation',
            'description': 'Creates a 3D rotation animation effect',
            'parameters': {
                'axis': {'type': 'string', 'choices': ['x', 'y', 'z'], 'default': 'y'},
                'rotation_angle': {'type': 'number', 'min': -360, 'max': 360, 'default': 45},
                'duration': {'type': 'number', 'min': 1, 'max': 30, 'default': 5},
                'fps': {'type': 'number', 'min': 15, 'max': 60, 'default': 30}
            }
        },
        'ripple_zoom': {
            'name': 'Ripple Zoom',
            'description': 'Creates a ripple zoom out effect',
            'parameters': {
                'zoom_factor': {'type': 'number', 'min': 1.1, 'max': 5.0, 'default': 2.0},
                'ripple_strength': {'type': 'number', 'min': 0.1, 'max': 2.0, 'default': 0.5},
                'duration': {'type': 'number', 'min': 1, 'max': 30, 'default': 4},
                'fps': {'type': 'number', 'min': 15, 'max': 60, 'default': 30}
            }
        },
        'zoom_highlight': {
            'name': 'Zoom Highlight',
            'description': 'Zoom effect with progressive highlighting',
            'parameters': {
                'zoom_factor': {'type': 'number', 'min': 1.1, 'max': 3.0, 'default': 1.8},
                'highlight_color': {'type': 'string', 'default': 'yellow'},
                'duration': {'type': 'number', 'min': 1, 'max': 30, 'default': 4},
                'fps': {'type': 'number', 'min': 15, 'max': 60, 'default': 30}
            }
        },
        'wikipedia_text': {
            'name': 'Wikipedia Text Generator',
            'description': 'Generates Wikipedia-style text video',
            'parameters': {
                'text_content': {'type': 'string', 'default': 'Wikipedia is a free online encyclopedia.'},
                'aspect_ratio': {'type': 'string', 'choices': ['9:16', '16:9'], 'default': '9:16'},
                'duration': {'type': 'number', 'min': 1, 'max': 30, 'default': 5},
                'fps': {'type': 'number', 'min': 15, 'max': 60, 'default': 30}
            }
        },
        'font_video': {
            'name': 'Font Video Generator',
            'description': 'Creates dynamic font animation video',
            'parameters': {
                'text_content': {'type': 'string', 'default': 'Sample Text'},
                'font_changes': {'type': 'boolean', 'default': True},
                'zoom_effect': {'type': 'boolean', 'default': True},
                'duration': {'type': 'number', 'min': 1, 'max': 30, 'default': 6},
                'fps': {'type': 'number', 'min': 15, 'max': 60, 'default': 30}
            }
        },
        'perspective_transform': {
            'name': 'Perspective Transform',
            'description': 'Creates perspective transformation animation',
            'parameters': {
                'perspective_strength': {'type': 'number', 'min': 0.1, 'max': 1.0, 'default': 0.5},
                'zoom_factor': {'type': 'number', 'min': 1.0, 'max': 3.0, 'default': 1.5},
                'duration': {'type': 'number', 'min': 1, 'max': 30, 'default': 5},
                'fps': {'type': 'number', 'min': 15, 'max': 60, 'default': 30}
            }
        },
        'perspective_with_highlight': {
            'name': 'Perspective with Highlight',
            'description': 'Perspective transform with progressive highlighting',
            'parameters': {
                'perspective_strength': {'type': 'number', 'min': 0.1, 'max': 1.0, 'default': 0.5},
                'zoom_factor': {'type': 'number', 'min': 1.0, 'max': 3.0, 'default': 1.5},
                'highlight_area': {'type': 'array', 'default': None},
                'duration': {'type': 'number', 'min': 1, 'max': 30, 'default': 5},
                'fps': {'type': 'number', 'min': 15, 'max': 60, 'default': 30}
            }
        },
        'ripple_zoom_with_highlight': {
            'name': 'Ripple Zoom with Highlight',
            'description': 'Ripple zoom effect with progressive highlighting',
            'parameters': {
                'zoom_factor': {'type': 'number', 'min': 1.1, 'max': 5.0, 'default': 2.0},
                'ripple_strength': {'type': 'number', 'min': 0.1, 'max': 2.0, 'default': 0.5},
                'highlight_start': {'type': 'number', 'min': 0.0, 'max': 1.0, 'default': 0.7},
                'duration': {'type': 'number', 'min': 1, 'max': 30, 'default': 4},
                'fps': {'type': 'number', 'min': 15, 'max': 60, 'default': 30}
            }
        }
    }
    
    return jsonify({
        'success': True,
        'effects': effects_info
    })

@app.route('/api/generate/<effect_type>', methods=['POST'])
def generate_video(effect_type):
    """Generate video with specified effect"""
    start_time = time.time()
    
    try:
        # Check if effect type is valid
        if effect_type not in EFFECT_REGISTRY:
            return jsonify({
                'success': False,
                'error': f'Unknown effect type: {effect_type}',
                'available_effects': list(EFFECT_REGISTRY.keys())
            }), 400

        # User email
        email = request.form.get('email') or (request.json.get('email') if request.is_json else None)
        if not email:
            return jsonify({'success': False, 'error': 'Email is required'}), 400

        # Handle file upload
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No image file provided'
            }), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400

        # Save uploaded file
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(input_path)

        # Upload original file to Supabase
        input_public_url = None
        storage_folder = email.replace('@', '_')
        if supabase_client:
            try:
                with open(input_path, 'rb') as f:
                    supabase_client.storage.from_(SUPABASE_BUCKET).upload(
                        f"{storage_folder}/input/{unique_filename}", f, {"upsert": "true"}
                    )
                input_public_url = supabase_client.storage.from_(SUPABASE_BUCKET).get_public_url(
                    f"{storage_folder}/input/{unique_filename}"
                )
            except Exception as e:
                logger.warning(f"Failed to upload original file to Supabase: {e}")

        # Get parameters from form data
        parameters = {}
        for key, value in request.form.items():
            if key not in ['image', 'email']:
                if value.lower() in ['true', 'false']:
                    parameters[key] = value.lower() == 'true'
                elif value.replace('.', '', 1).replace('-', '', 1).isdigit():
                    parameters[key] = float(value) if '.' in value else int(value)
                else:
                    parameters[key] = value

        # Generate output filename
        output_filename = f"{uuid.uuid4().hex}_{effect_type}.mp4"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        
        # Process video
        logger.info(f"Processing {effect_type} with parameters: {parameters}")
        success = process_video_effect(effect_type, input_path, output_path, parameters)

        # Clean up input file
        try:
            os.remove(input_path)
        except Exception:
            pass

        if not success:
            return jsonify({
                'success': False,
                'error': 'Video processing failed'
            }), 500

        # Upload processed video to Supabase
        output_public_url = None
        if supabase_client:
            try:
                with open(output_path, 'rb') as f:
                    supabase_client.storage.from_(SUPABASE_BUCKET).upload(
                        f"{storage_folder}/output/{output_filename}", f, {"upsert": "true"}
                    )
                output_public_url = supabase_client.storage.from_(SUPABASE_BUCKET).get_public_url(
                    f"{storage_folder}/output/{output_filename}"
                )
            except Exception as e:
                logger.warning(f"Failed to upload processed file to Supabase: {e}")

        processing_time = time.time() - start_time

        return jsonify({
            'success': True,
            'message': 'Video generated successfully',
            'video_id': output_filename.replace('.mp4', ''),
            'download_url': f'/api/download/{output_filename}',
            'original_url': input_public_url,
            'public_url': output_public_url,
            'processing_time': round(processing_time, 2),
            'effect_type': effect_type,
            'parameters': parameters
        })
        
    except Exception as e:
        logger.error(f"Error processing video: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@app.route('/api/download/<filename>', methods=['GET'])
def download_video(filename):
    """Download generated video file"""
    try:
        file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='video/mp4'
        )
        
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Download failed'
        }), 500

@app.route('/api/cleanup', methods=['POST'])
def cleanup_files():
    """Clean up old files (optional maintenance endpoint)"""
    try:
        deleted_count = 0
        
        # Clean up files older than 1 hour
        current_time = time.time()
        for folder in [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER']]:
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getctime(file_path)
                    if file_age > 3600:  # 1 hour
                        os.remove(file_path)
                        deleted_count += 1
        
        return jsonify({
            'success': True,
            'message': f'Cleaned up {deleted_count} old files'
        })
        
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Cleanup failed'
        }), 500

@app.errorhandler(413)
def too_large(e):
    """Handle file too large error"""
    return jsonify({
        'success': False,
        'error': 'File too large. Maximum size is 16MB.'
    }), 413

@app.errorhandler(400)
def bad_request(e):
    """Handle bad request errors"""
    return jsonify({
        'success': False,
        'error': 'Bad request'
    }), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)
