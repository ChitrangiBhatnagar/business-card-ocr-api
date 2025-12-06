"""
Business Card Processing API - Flask Application Entry Point.

A production-ready API for extracting and enriching contact data
from business card images using OCR.
"""

import logging
import os

from flask import Flask, jsonify, render_template
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
    
    # Root endpoint - Serve the UI
    @app.route("/")
    def index():
        """Serve the main UI page."""
        return render_template("index.html")
    
    # API info endpoint
    @app.route("/api/info")
    def api_info():
        """API information endpoint."""
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
            "documentation": "https://github.com/ChitrangiBhatnagar/business-card-ocr-api"
        })
    
    # Favicon handler (prevents 404 errors from browsers)
    @app.route("/favicon.ico")
    def favicon():
        """Return empty response for favicon requests."""
        return "", 204
    
    # Global error handlers
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        return jsonify({
            "success": False,
            "error": "Not found"
        }), 404
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        """Handle file too large errors."""
        return jsonify({
            "success": False,
            "error": f"File too large. Maximum size: {Config.MAX_CONTENT_LENGTH // (1024*1024)}MB"
        }), 413
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        logger.error(f"Internal error: {str(error)}")
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle uncaught exceptions."""
        # Don't log 404 errors as they're handled above
        if hasattr(error, 'code') and error.code == 404:
            return not_found(error)
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
