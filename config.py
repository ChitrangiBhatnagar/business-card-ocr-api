"""
Configuration management for Business Card Processing API.

Handles environment variables, API keys, and application settings.
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    """Application configuration class.
    
    Attributes:
        DEBUG: Enable debug mode
        TESTING: Enable testing mode
        SECRET_KEY: Flask secret key
        MAX_CONTENT_LENGTH: Maximum upload file size (16MB default)
        UPLOAD_FOLDER: Directory for uploaded files
        OUTPUT_FOLDER: Directory for generated CSV files
        ALLOWED_EXTENSIONS: Allowed image file extensions
    """
    
    # Flask Settings
    DEBUG: bool = os.getenv("CARD_API_DEBUG", "False").lower() == "true"
    TESTING: bool = os.getenv("CARD_API_TESTING", "False").lower() == "true"
    SECRET_KEY: str = os.getenv("CARD_API_SECRET_KEY", "dev-secret-key-change-in-production")
    
    # File Upload Settings
    MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER: str = os.getenv("CARD_API_UPLOAD_FOLDER", "uploads")
    OUTPUT_FOLDER: str = os.getenv("CARD_API_OUTPUT_FOLDER", "outputs")
    ALLOWED_EXTENSIONS: set = {"png", "jpg", "jpeg", "gif", "bmp", "webp"}
    
    # OCR Settings
    OCR_LANGUAGES: list = ["en"]  # EasyOCR language codes
    OCR_GPU: bool = os.getenv("CARD_API_OCR_GPU", "False").lower() == "true"
    # Performance and tuning
    OCR_MAX_DIMENSION: int = int(os.getenv("CARD_API_OCR_MAX_DIMENSION", "1600"))
    OCR_ENHANCE_IMAGES: bool = os.getenv("CARD_API_OCR_ENHANCE_IMAGES", "False").lower() == "true"
    OCR_CANVAS_SIZE: int = int(os.getenv("CARD_API_OCR_CANVAS_SIZE", "1280"))
    OCR_MAG_RATIO: float = float(os.getenv("CARD_API_OCR_MAG_RATIO", "1.0"))
    OCR_MIN_SIZE: int = int(os.getenv("CARD_API_OCR_MIN_SIZE", "10"))
    # Batch processing
    PARALLEL_PROCESSING: bool = os.getenv("CARD_API_PARALLEL_PROCESSING", "False").lower() == "true"
    PARALLEL_WORKERS: int = int(os.getenv("CARD_API_PARALLEL_WORKERS", "2"))
    
    # Free API Keys (Optional - for enrichment)
    HUNTER_API_KEY: Optional[str] = os.getenv("HUNTER_API_KEY")
    ABSTRACT_API_KEY: Optional[str] = os.getenv("ABSTRACT_API_KEY")
    GITHUB_TOKEN: Optional[str] = os.getenv("GITHUB_TOKEN")
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("CARD_API_RATE_LIMIT", "60"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("CARD_API_LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @classmethod
    def init_app(cls, app) -> None:
        """Initialize Flask app with configuration.
        
        Args:
            app: Flask application instance
        """
        app.config.from_object(cls)
        
        # Create required directories
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(cls.OUTPUT_FOLDER, exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=getattr(logging, cls.LOG_LEVEL.upper()),
            format=cls.LOG_FORMAT
        )
        
        logger.info("Configuration initialized successfully")
    
    @classmethod
    def is_allowed_file(cls, filename: str) -> bool:
        """Check if file extension is allowed.
        
        Args:
            filename: Name of the file to check
            
        Returns:
            True if file extension is allowed, False otherwise
        """
        return "." in filename and \
            filename.rsplit(".", 1)[1].lower() in cls.ALLOWED_EXTENSIONS
    
    @classmethod
    def get_api_status(cls) -> dict:
        """Get status of configured API keys.
        
        Returns:
            Dictionary with API availability status
        """
        return {
            "hunter_api": cls.HUNTER_API_KEY is not None,
            "abstract_api": cls.ABSTRACT_API_KEY is not None,
            "github_api": cls.GITHUB_TOKEN is not None
        }


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    LOG_LEVEL = "DEBUG"


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    LOG_LEVEL = "INFO"


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    LOG_LEVEL = "DEBUG"


# Configuration mapping
config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig
}


def get_config(config_name: Optional[str] = None) -> Config:
    """Get configuration class by name.
    
    Args:
        config_name: Configuration name (development, production, testing)
        
    Returns:
        Configuration class
    """
    if config_name is None:
        config_name = os.getenv("CARD_API_ENV", "development")
    return config_by_name.get(config_name, DevelopmentConfig)
