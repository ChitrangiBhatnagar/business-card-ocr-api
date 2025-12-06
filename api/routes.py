"""
API routes for Business Card Processing API.

Flask REST API endpoints for processing business cards.
"""

import logging
import os
from typing import Optional
from pathlib import Path

from flask import Blueprint, request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename

from src.pipeline import CardResearchPipeline
from config import Config

logger = logging.getLogger(__name__)

# Create Blueprint
api_bp = Blueprint("api", __name__, url_prefix="/api")

# Pipeline instance (lazy initialization)
_pipeline: Optional[CardResearchPipeline] = None


def get_pipeline() -> CardResearchPipeline:
    """Get or create pipeline instance.
    
    Returns:
        CardResearchPipeline instance
    """
    global _pipeline
    
    if _pipeline is None:
        _pipeline = CardResearchPipeline(
            output_folder=Config.OUTPUT_FOLDER,
            ocr_languages=Config.OCR_LANGUAGES,
            ocr_gpu=Config.OCR_GPU,
            hunter_api_key=Config.HUNTER_API_KEY,
            abstract_api_key=Config.ABSTRACT_API_KEY,
            github_token=Config.GITHUB_TOKEN
        )
        logger.info("Pipeline initialized")
    
    return _pipeline


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed.
    
    Args:
        filename: Name of the file
        
    Returns:
        True if allowed, False otherwise
    """
    return Config.is_allowed_file(filename)


@api_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint.
    
    Returns:
        JSON with health status
    """
    return jsonify({
        "success": True,
        "status": "healthy",
        "message": "Business Card Processing API is running",
        "version": "1.0.0"
    }), 200


@api_bp.route("/status", methods=["GET"])
def get_status():
    """Get API and pipeline status.
    
    Returns:
        JSON with status information
    """
    try:
        pipeline = get_pipeline()
        status = pipeline.get_status()
        
        return jsonify({
            "success": True,
            "data": {
                "api_status": "running",
                "pipeline_status": status,
                "api_keys_configured": Config.get_api_status()
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_bp.route("/process", methods=["POST"])
def process_single():
    """Process a single business card image.
    
    Expects:
        - multipart/form-data with 'file' field
        - Optional query param: enrich=true/false (default: true)
    
    Returns:
        JSON with extracted contact data
    """
    # Check if file is present
    if "file" not in request.files:
        return jsonify({
            "success": False,
            "error": "No file provided. Use 'file' field in form-data."
        }), 400
    
    file = request.files["file"]
    
    if file.filename == "":
        return jsonify({
            "success": False,
            "error": "No file selected"
        }), 400
    
    if not allowed_file(file.filename):
        return jsonify({
            "success": False,
            "error": f"File type not allowed. Allowed: {', '.join(Config.ALLOWED_EXTENSIONS)}"
        }), 400
    
    # Get enrichment option
    enrich = request.args.get("enrich", "true").lower() == "true"
    
    try:
        # Save uploaded file
        filename = secure_filename(file.filename)
        upload_path = Path(Config.UPLOAD_FOLDER) / filename
        file.save(str(upload_path))
        
        logger.info(f"Processing uploaded file: {filename}")
        
        # Process image
        pipeline = get_pipeline()
        result = pipeline.process_image(upload_path, enrich=enrich)
        
        # Clean up uploaded file
        try:
            os.remove(upload_path)
        except Exception as e:
            logger.warning(f"Failed to clean up file: {str(e)}")
        
        if result["success"]:
            return jsonify({
                "success": True,
                "data": result
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": result["error"]
            }), 500
            
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_bp.route("/batch", methods=["POST"])
def process_batch():
    """Process multiple business card images.
    
    Expects:
        - multipart/form-data with multiple 'files' fields
        - Optional query params:
            - enrich=true/false (default: true)
            - generate_csv=true/false (default: true)
    
    Returns:
        JSON with batch processing results
    """
    if "files" not in request.files:
        return jsonify({
            "success": False,
            "error": "No files provided. Use 'files' field in form-data."
        }), 400
    
    files = request.files.getlist("files")
    
    if not files or all(f.filename == "" for f in files):
        return jsonify({
            "success": False,
            "error": "No files selected"
        }), 400
    
    # Get options
    enrich = request.args.get("enrich", "true").lower() == "true"
    generate_csv = request.args.get("generate_csv", "true").lower() == "true"
    
    try:
        # Save all uploaded files
        saved_paths = []
        for file in files:
            if file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                upload_path = Path(Config.UPLOAD_FOLDER) / filename
                file.save(str(upload_path))
                saved_paths.append(upload_path)
        
        if not saved_paths:
            return jsonify({
                "success": False,
                "error": "No valid files to process"
            }), 400
        
        logger.info(f"Processing batch of {len(saved_paths)} files")
        
        # Process batch
        pipeline = get_pipeline()
        result = pipeline.process_batch(
            saved_paths,
            enrich=enrich,
            generate_csv=generate_csv
        )
        
        # Clean up uploaded files
        for path in saved_paths:
            try:
                os.remove(path)
            except Exception as e:
                logger.warning(f"Failed to clean up file: {str(e)}")
        
        return jsonify({
            "success": result["success"],
            "data": result
        }), 200 if result["success"] else 500
        
    except Exception as e:
        logger.error(f"Error processing batch: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_bp.route("/parse-text", methods=["POST"])
def parse_text():
    """Parse raw text (skip OCR).
    
    Expects:
        - JSON body with 'text' field
        - Optional query param: enrich=true/false (default: true)
    
    Returns:
        JSON with parsed contact data
    """
    data = request.get_json()
    
    if not data or "text" not in data:
        return jsonify({
            "success": False,
            "error": "No text provided. Send JSON with 'text' field."
        }), 400
    
    text = data["text"]
    enrich = request.args.get("enrich", "true").lower() == "true"
    
    try:
        pipeline = get_pipeline()
        result = pipeline.process_text(text, enrich=enrich)
        
        return jsonify({
            "success": result["success"],
            "data": result
        }), 200 if result["success"] else 500
        
    except Exception as e:
        logger.error(f"Error parsing text: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_bp.route("/download/<filename>", methods=["GET"])
def download_csv(filename: str):
    """Download a generated CSV file.
    
    Args:
        filename: Name of the CSV file
        
    Returns:
        CSV file download
    """
    # Security: ensure filename is safe
    filename = secure_filename(filename)
    
    # Ensure it's a CSV file
    if not filename.endswith(".csv"):
        return jsonify({
            "success": False,
            "error": "Only CSV files can be downloaded"
        }), 400
    
    file_path = Path(Config.OUTPUT_FOLDER) / filename
    
    if not file_path.exists():
        return jsonify({
            "success": False,
            "error": f"File not found: {filename}"
        }), 404
    
    try:
        return send_file(
            file_path,
            mimetype="text/csv",
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_bp.route("/files", methods=["GET"])
def list_output_files():
    """List available CSV files for download.
    
    Returns:
        JSON with list of available files
    """
    try:
        output_path = Path(Config.OUTPUT_FOLDER)
        
        if not output_path.exists():
            return jsonify({
                "success": True,
                "data": {"files": []}
            }), 200
        
        files = []
        for file_path in output_path.glob("*.csv"):
            stat = file_path.stat()
            files.append({
                "filename": file_path.name,
                "size_bytes": stat.st_size,
                "created_at": stat.st_ctime,
                "download_url": f"/api/download/{file_path.name}"
            })
        
        # Sort by creation time (newest first)
        files.sort(key=lambda x: x["created_at"], reverse=True)
        
        return jsonify({
            "success": True,
            "data": {"files": files}
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_bp.route("/enrich", methods=["POST"])
def enrich_contact():
    """Enrich contact data with external APIs.
    
    Expects:
        - JSON body with contact fields (email, name, company, etc.)
    
    Returns:
        JSON with enriched data
    """
    data = request.get_json()
    
    if not data:
        return jsonify({
            "success": False,
            "error": "No data provided. Send JSON with contact fields."
        }), 400
    
    # Need at least email or name
    if not data.get("email") and not data.get("name"):
        return jsonify({
            "success": False,
            "error": "Provide at least 'email' or 'name' for enrichment"
        }), 400
    
    try:
        from src.parser import ContactData
        
        # Create ContactData from input
        contact = ContactData(
            name=data.get("name"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            email=data.get("email"),
            phone=data.get("phone", []),
            company=data.get("company"),
            title=data.get("title")
        )
        
        # Enrich
        pipeline = get_pipeline()
        enriched = pipeline.researcher.enrich(contact)
        
        return jsonify({
            "success": True,
            "data": {
                "original": contact.to_dict(),
                "enriched": enriched.to_dict()
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error enriching contact: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# Error handlers
@api_bp.errorhandler(400)
def bad_request(error):
    """Handle 400 errors."""
    return jsonify({
        "success": False,
        "error": "Bad request"
    }), 400


@api_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        "success": False,
        "error": "Resource not found"
    }), 404


@api_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({
        "success": False,
        "error": "Internal server error"
    }), 500
