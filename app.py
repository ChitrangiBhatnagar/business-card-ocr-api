"""
Business Card Processing API - Flask Application Entry Point.

A production-ready API for extracting and enriching contact data
from business card images using OCR.
"""

import logging
import os

from flask import Flask, jsonify
from flask_cors import CORS

from config import Config, get_config
from api.routes import api_bp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_app(config_name: str = None) -> Flask:
    """Application factory for creating Flask app.
    
    Args:
        config_name: Configuration name (development, production, testing)
        
    Returns:
        Configured Flask application
    """
    app = Flask(__name__)
    
    # Load configuration
    config_class = get_config(config_name)
    config_class.init_app(app)
    
    # Enable CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Register blueprints
    app.register_blueprint(api_bp)
    
    # Root endpoint
    @app.route("/")
    def index():
        """Root endpoint with API information."""
        return jsonify({
            "name": "Business Card Processing API",
            "version": "1.0.0",
            "description": "Extract and enrich contact data from business card images",
            "endpoints": {
                "health": "/api/health",
                "status": "/api/status",
                "process_single": "POST /api/process",
                "process_batch": "POST /api/batch",
                "parse_text": "POST /api/parse-text",
                "enrich": "POST /api/enrich",
                "download": "GET /api/download/<filename>",
                "list_files": "GET /api/files"
            },
            "documentation": "https://github.com/your-repo/business-card-api"
        })
    
    # Global error handlers
    @app.errorhandler(413)
    def request_entity_too_large(error):
        """Handle file too large errors."""
        return jsonify({
            "success": False,
            "error": f"File too large. Maximum size: {Config.MAX_CONTENT_LENGTH // (1024*1024)}MB"
        }), 413
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle uncaught exceptions."""
        logger.error(f"Uncaught exception: {str(error)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred"
        }), 500
    
    logger.info(f"Application created with config: {config_class.__name__}")
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    # Get port from environment or default to 5000
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("CARD_API_DEBUG", "True").lower() == "true"
    
    logger.info(f"Starting server on port {port}, debug={debug}")
    
    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug
    )
