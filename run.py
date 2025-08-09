#!/usr/bin/env python3
"""
Entry point for running the Flask Video Effects API
"""
import os
from app import app
from config import config_by_name

def create_app(config_name=None):
    """Create and configure the Flask application"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    config_class = config_by_name.get(config_name, config_by_name['default'])
    
    # Apply configuration
    app.config.from_object(config_class)
    
    # Create directories if they don't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
    
    return app

if __name__ == '__main__':
    # Get configuration from environment
    config_name = os.environ.get('FLASK_ENV', 'development')
    flask_app = create_app(config_name)
    
    # Run the application
    flask_app.run(
        host=flask_app.config['HOST'],
        port=flask_app.config['PORT'],
        debug=flask_app.config.get('DEBUG', False)
    )
