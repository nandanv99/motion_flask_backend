"""
Configuration settings for Flask Video Effects API
"""
import os
from decouple import config

class Config:
    """Base configuration"""
    # Flask settings
    SECRET_KEY = config('SECRET_KEY', default='dev-secret-key-change-in-production')
    
    # File upload settings
    MAX_CONTENT_LENGTH = config('MAX_CONTENT_LENGTH', default=16 * 1024 * 1024, cast=int)  # 16MB
    UPLOAD_FOLDER = config('UPLOAD_FOLDER', default='uploads')
    OUTPUT_FOLDER = config('OUTPUT_FOLDER', default='outputs')
    
    # Server settings
    HOST = config('HOST', default='0.0.0.0')
    PORT = config('PORT', default=3000, cast=int)
    
    # Logging
    LOG_LEVEL = config('LOG_LEVEL', default='INFO')
    
    # File cleanup
    FILE_CLEANUP_AGE = config('FILE_CLEANUP_AGE', default=3600, cast=int)  # 1 hour
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    
class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    
class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True

# Configuration mapping
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
