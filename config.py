"""
Configuration file for Flask NDVI Calculator
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Base configuration"""

    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'

    # Sentinel API credentials
    SENTINEL_USER = os.environ.get('SENTINEL_USER', '')
    SENTINEL_PASSWORD = os.environ.get('SENTINEL_PASSWORD', '')
    SENTINEL_API_URL = os.environ.get('SENTINEL_API_URL', 'https://scihub.copernicus.eu/dhus')

    # File upload settings
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'downloads')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB

    # NDVI processing settings
    MAX_CLOUD_COVER = int(os.environ.get('MAX_CLOUD_COVER', 30))  # Percentage
    DEFAULT_DATE_RANGE_DAYS = int(os.environ.get('DEFAULT_DATE_RANGE_DAYS', 30))

    # Image processing
    NDVI_COLORMAP = os.environ.get('NDVI_COLORMAP', 'RdYlGn')
    OUTPUT_DPI = int(os.environ.get('OUTPUT_DPI', 150))

    @staticmethod
    def validate():
        """Validate configuration"""
        errors = []

        if not Config.SENTINEL_USER:
            errors.append("SENTINEL_USER not set")

        if not Config.SENTINEL_PASSWORD:
            errors.append("SENTINEL_PASSWORD not set")

        if errors:
            return False, errors

        return True, []


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config(config_name='default'):
    """Get configuration by name"""
    return config.get(config_name, DevelopmentConfig)
