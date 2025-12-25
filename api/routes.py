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
from src.batch_processor import batch_processor
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
            github_token=Config.GITHUB_TOKEN,
            gemini_api_key=Config.GOOGLE_API_KEY,
            use_gemini_fallback=Config.USE_GEMINI_FALLBACK,
            gemini_model=Config.GEMINI_MODEL
        )
        logger.info("Pipeline initialized with Gemini fallback: " + str(Config.USE_GEMINI_FALLBACK and Config.GOOGLE_API_KEY is not None))
    
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
        - Optional query param: force_gemini=true/false (default: false) - Use Gemini directly for best accuracy
        - Optional query param: ocr_method=auto/easyocr/gemini (default: auto)
    
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
    
    # Get options
    enrich = request.args.get("enrich", "true").lower() == "true"
    force_gemini = request.args.get("force_gemini", "false").lower() == "true"
    ocr_method = request.args.get("ocr_method", "auto").lower()
    
    # ocr_method=gemini is equivalent to force_gemini=true
    if ocr_method == "gemini":
        force_gemini = True
    
    try:
        # Save uploaded file
        filename = secure_filename(file.filename)
        upload_path = Path(Config.UPLOAD_FOLDER) / filename
        file.save(str(upload_path))
        
        logger.info(f"Processing uploaded file: {filename} (force_gemini={force_gemini})")
        
        # Process image
        pipeline = get_pipeline()
        result = pipeline.process_image(upload_path, enrich=enrich, force_gemini=force_gemini)
        
        # Clean up uploaded file
        try:
            os.remove(upload_path)
        except Exception as e:
            logger.warning(f"Failed to clean up file: {str(e)}")
        
        return jsonify(result), 200 if result.get("success") else 500

            
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_bp.route("/batch", methods=["POST"])
def process_batch():
    """Enhanced progressive batch processing.
    
    Processes files in chunks and returns results progressively.
    For large batches (>10 files), automatically uses progressive processing.
    """
    if "files" not in request.files:
        return jsonify({
            "success": False,
            "error": "No files provided"
        }), 400

    files = request.files.getlist("files")
    enrich = request.args.get("enrich", "false").lower() == "true"  # Default to false for speed
    force_gemini = request.args.get("force_gemini", "false").lower() == "true"

    try:
        saved_paths = []

        for file in files:
            if file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                path = Path(Config.UPLOAD_FOLDER) / filename
                file.save(str(path))
                saved_paths.append(path)

        if not saved_paths:
            return jsonify({
                "success": False,
                "error": "No valid files to process"
            }), 400

        pipeline = get_pipeline()
        
        # For small batches, process normally
        if len(saved_paths) <= 10:
            results = []
            for i, image_path in enumerate(saved_paths):
                try:
                    result = pipeline.process_image(image_path, enrich=enrich, force_gemini=force_gemini)
                    results.append(result)
                    logger.info(f"Processed {i+1}/{len(saved_paths)}: {image_path.name}")
                except Exception as e:
                    logger.error(f"Error processing {image_path}: {e}")
                    results.append({
                        "success": False,
                        "error": str(e),
                        "image": str(image_path)
                    })
            
            # Clean up files
            for p in saved_paths:
                try:
                    os.remove(p)
                except Exception:
                    pass
            
            successful = sum(1 for r in results if r.get("success"))
            
            return jsonify({
                "success": True,
                "results": results,
                "total": len(results),
                "successful": successful,
                "failed": len(results) - successful
            }), 200
        
        # For large batches, use progressive processing automatically
        else:
            # Start progressive job
            job_id = batch_processor.start_batch_job(saved_paths)
            all_results = []
            
            # Process all batches immediately but with progress tracking
            while True:
                batch_result = batch_processor.process_next_batch(job_id, pipeline)
                if batch_result is None:
                    break
                    
                # Add batch results to total
                for item in batch_result['batch_results']:
                    all_results.append(item['result'])
                
                logger.info(f"Completed batch {batch_result['batch_number']}/{batch_result['total_batches']} "
                           f"({batch_result['progress']:.1f}% complete)")
            
            # Clean up files and job
            for p in saved_paths:
                try:
                    os.remove(p)
                except Exception:
                    pass
            
            batch_processor.cleanup_job(job_id)
            
            successful = sum(1 for r in all_results if r.get("success"))
            
            return jsonify({
                "success": True,
                "results": all_results,
                "total": len(all_results),
                "successful": successful,
                "failed": len(all_results) - successful,
                "processing_method": "progressive_batch"
            }), 200

    except Exception as e:
        logger.exception("Unhandled error in /batch")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_bp.route("/batch-progressive/start", methods=["POST"])
def start_progressive_batch():
    """Start a progressive batch processing job.
    
    Expects:
        - multipart/form-data with 'files' field (multiple files)
        - Optional query param: batch_size=20 (default: 20)
    
    Returns:
        JSON with job_id for tracking progress
    """
    if "files" not in request.files:
        return jsonify({
            "success": False,
            "error": "No files provided"
        }), 400

    files = request.files.getlist("files")
    batch_size = int(request.args.get("batch_size", "20"))

    try:
        saved_paths = []

        for file in files:
            if file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                path = Path(Config.UPLOAD_FOLDER) / filename
                file.save(str(path))
                saved_paths.append(path)

        if not saved_paths:
            return jsonify({
                "success": False,
                "error": "No valid files to process"
            }), 400

        # Start batch job
        batch_processor.batch_size = batch_size
        job_id = batch_processor.start_batch_job(saved_paths)
        
        return jsonify({
            "success": True,
            "job_id": job_id,
            "total_files": len(saved_paths),
            "batch_size": batch_size,
            "estimated_batches": len(saved_paths) // batch_size + (1 if len(saved_paths) % batch_size else 0)
        }), 200

    except Exception as e:
        logger.error(f"Error starting batch job: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_bp.route("/batch-progressive/<job_id>/next", methods=["POST"])
def process_next_batch(job_id: str):
    """Process the next batch for a job.
    
    Args:
        job_id: Job ID from start_progressive_batch
    
    Returns:
        JSON with batch results and progress
    """
    try:
        pipeline = get_pipeline()
        result = batch_processor.process_next_batch(job_id, pipeline)
        
        if result is None:
            # Job not found or already complete
            job_status = batch_processor.get_job_status(job_id)
            if job_status is None:
                return jsonify({
                    "success": False,
                    "error": "Job not found"
                }), 404
            else:
                return jsonify({
                    "success": True,
                    "job_id": job_id,
                    "status": "completed",
                    "is_complete": True,
                    "final_results": job_status.get('results', [])
                }), 200
        
        return jsonify({
            "success": True,
            **result
        }), 200

    except Exception as e:
        logger.error(f"Error processing batch {job_id}: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_bp.route("/batch-progressive/<job_id>/status", methods=["GET"])
def get_batch_status(job_id: str):
    """Get status of a batch processing job.
    
    Args:
        job_id: Job ID
    
    Returns:
        JSON with current job status
    """
    try:
        job_status = batch_processor.get_job_status(job_id)
        
        if job_status is None:
            return jsonify({
                "success": False,
                "error": "Job not found"
            }), 404
        
        return jsonify({
            "success": True,
            "job_id": job_id,
            "status": job_status['status'],
            "progress": (job_status['processed'] / job_status['total_images']) * 100,
            "processed": job_status['processed'],
            "successful": job_status['successful'],
            "failed": job_status['failed'],
            "total": job_status['total_images'],
            "current_batch": job_status['current_batch'],
            "total_batches": job_status['total_batches'],
            "is_complete": job_status['current_batch'] >= job_status['total_batches']
        }), 200

    except Exception as e:
        logger.error(f"Error getting batch status {job_id}: {str(e)}")
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
