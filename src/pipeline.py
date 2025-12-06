"""
Pipeline module for Business Card Processing API.

Orchestrates the full processing flow: OCR -> Parse -> Enrich -> CSV.
"""

import logging
import os
from typing import Dict, List, Optional, Union
from pathlib import Path
from datetime import datetime
import uuid

import pandas as pd

from .ocr import CardOCR
from config import Config
from .parser import CardDataParser, ContactData
from .researcher import FreeLeadResearcher, EnrichedData

logger = logging.getLogger(__name__)


class CardResearchPipeline:
    """Orchestrates the full business card processing pipeline.
    
    Pipeline stages:
    1. OCR: Extract text from images
    2. Parse: Extract structured data from text
    3. Enrich: Add data from free APIs
    4. Export: Generate CSV output
    
    Attributes:
        ocr: CardOCR instance
        parser: CardDataParser instance
        researcher: FreeLeadResearcher instance
        output_folder: Directory for CSV output
    """
    
    def __init__(
        self,
        ocr: Optional[CardOCR] = None,
        parser: Optional[CardDataParser] = None,
        researcher: Optional[FreeLeadResearcher] = None,
        output_folder: str = "outputs",
        ocr_languages: Optional[List[str]] = None,
        ocr_gpu: bool = False,
        hunter_api_key: Optional[str] = None,
        abstract_api_key: Optional[str] = None,
        github_token: Optional[str] = None
    ) -> None:
        """Initialize the CardResearchPipeline.
        
        Args:
            ocr: Optional CardOCR instance (creates new if not provided)
            parser: Optional CardDataParser instance (creates new if not provided)
            researcher: Optional FreeLeadResearcher instance (creates new if not provided)
            output_folder: Directory for output files
            ocr_languages: Languages for OCR (default: ["en"])
            ocr_gpu: Whether to use GPU for OCR
            hunter_api_key: Hunter.io API key
            abstract_api_key: Abstract API key
            github_token: GitHub token
        """
        # Initialize components
        # Read performance settings from Config when not provided
        max_dim = Config.OCR_MAX_DIMENSION
        enhance = Config.OCR_ENHANCE_IMAGES
        canvas = Config.OCR_CANVAS_SIZE
        mag_ratio = Config.OCR_MAG_RATIO
        min_size = Config.OCR_MIN_SIZE

        self.ocr = ocr or CardOCR(
            languages=ocr_languages,
            gpu=ocr_gpu,
            max_dimension=max_dim,
            enhance_images=enhance,
            canvas_size=canvas,
            mag_ratio=mag_ratio,
            min_size=min_size
        )
        self.parser = parser or CardDataParser()
        self.researcher = researcher or FreeLeadResearcher(
            hunter_api_key=hunter_api_key,
            abstract_api_key=abstract_api_key,
            github_token=github_token
        )
        
        # Set up output folder
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            f"CardResearchPipeline initialized. Output folder: {self.output_folder}"
        )
    
    def process_image(
        self,
        image_path: Union[str, Path],
        enrich: bool = True
    ) -> Dict:
        """Process a single business card image.
        
        Args:
            image_path: Path to the image file
            enrich: Whether to enrich with external APIs
            
        Returns:
            Dictionary with processed results
        """
        image_path = Path(image_path)
        logger.info(f"Processing image: {image_path}")
        
        result = {
            "success": True,
            "image_path": str(image_path),
            "ocr_text": None,
            "contact_data": None,
            "enriched_data": None,
            "ocr_confidence": None,
            "processing_time": None,
            "error": None
        }
        
        start_time = datetime.now()
        
        try:
            # Stage 1: OCR
            logger.debug("Stage 1: OCR extraction")
            ocr_results = self.ocr.extract_text(image_path)
            result["ocr_text"] = "\n".join([text for text, _ in ocr_results])
            result["ocr_confidence"] = self.ocr.get_confidence_stats(ocr_results)
            
            # Stage 2: Parse
            logger.debug("Stage 2: Data parsing")
            contact = self.parser.parse(result["ocr_text"], ocr_results)
            result["contact_data"] = contact.to_dict()
            
            # Stage 3: Enrich (optional)
            if enrich:
                logger.debug("Stage 3: Data enrichment")
                enriched = self.researcher.enrich(contact)
                result["enriched_data"] = enriched.to_dict()
            
            # Calculate processing time
            end_time = datetime.now()
            result["processing_time"] = (end_time - start_time).total_seconds()
            
            logger.info(
                f"Successfully processed {image_path.name} "
                f"in {result['processing_time']:.2f}s"
            )
            
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {str(e)}")
            result["success"] = False
            result["error"] = str(e)
        
        return result
    
    def process_batch(
        self,
        image_paths: List[Union[str, Path]],
        enrich: bool = True,
        generate_csv: bool = True
    ) -> Dict:
        """Process multiple business card images.
        
        Args:
            image_paths: List of image file paths
            enrich: Whether to enrich with external APIs
            generate_csv: Whether to generate CSV output
            
        Returns:
            Dictionary with batch processing results
        """
        logger.info(f"Processing batch of {len(image_paths)} images")
        
        batch_result = {
            "success": True,
            "total_images": len(image_paths),
            "processed": 0,
            "failed": 0,
            "results": [],
            "csv_path": None,
            "total_processing_time": None,
            "errors": []
        }
        
        start_time = datetime.now()
        
        # Optionally process in parallel for speed. Uses ThreadPoolExecutor which
        # shares the same EasyOCR reader instance and avoids reloading the model
        # per worker. This is a good trade-off between memory usage and speed.
        if Config.PARALLEL_PROCESSING:
            import concurrent.futures
            max_workers = max(1, Config.PARALLEL_WORKERS)
            logger.info(f"Processing batch in parallel with {max_workers} workers")
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(self.process_image, p, enrich) for p in image_paths]
                for i, future in enumerate(concurrent.futures.as_completed(futures)):
                    try:
                        result = future.result()
                    except Exception as e:
                        logger.error(f"Image {i+1} processing failed: {e}")
                        result = {
                            "success": False,
                            "image_path": str(image_paths[i]),
                            "error": str(e)
                        }
                    batch_result["results"].append(result)
        else:
            for i, image_path in enumerate(image_paths):
                logger.info(f"Processing image {i + 1}/{len(image_paths)}")
                result = self.process_image(image_path, enrich=enrich)
                batch_result["results"].append(result)
            
            if result["success"]:
                batch_result["processed"] += 1
            else:
                batch_result["failed"] += 1
                batch_result["errors"].append({
                    "image": str(image_path),
                    "error": result["error"]
                })
        
        # Generate CSV if requested
        if generate_csv and batch_result["processed"] > 0:
            try:
                csv_path = self.generate_csv(batch_result["results"])
                batch_result["csv_path"] = str(csv_path)
            except Exception as e:
                logger.error(f"Error generating CSV: {str(e)}")
                batch_result["errors"].append({
                    "stage": "csv_generation",
                    "error": str(e)
                })
        
        # Calculate total time
        end_time = datetime.now()
        batch_result["total_processing_time"] = (end_time - start_time).total_seconds()
        
        # Set overall success based on results
        batch_result["success"] = batch_result["failed"] < batch_result["total_images"]
        
        logger.info(
            f"Batch processing complete: {batch_result['processed']} successful, "
            f"{batch_result['failed']} failed, "
            f"total time: {batch_result['total_processing_time']:.2f}s"
        )
        
        return batch_result
    
    def generate_csv(
        self,
        results: List[Dict],
        filename: Optional[str] = None
    ) -> Path:
        """Generate CSV file from processing results.
        
        Args:
            results: List of processing result dictionaries
            filename: Optional custom filename
            
        Returns:
            Path to generated CSV file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"leads_{timestamp}_{unique_id}.csv"
        
        csv_path = self.output_folder / filename
        
        # Flatten results into rows
        rows = []
        for result in results:
            if not result.get("success"):
                continue
            
            contact = result.get("contact_data", {})
            enriched = result.get("enriched_data", {}) or {}
            
            row = {
                # Basic contact info
                "name": contact.get("name"),
                "first_name": contact.get("first_name"),
                "last_name": contact.get("last_name"),
                "email": contact.get("email"),
                "phone": ", ".join(contact.get("phone", [])) if contact.get("phone") else None,
                "company": contact.get("company"),
                "title": contact.get("title"),
                "website": contact.get("website"),
                "address": contact.get("address"),
                "linkedin": contact.get("linkedin"),
                "twitter": contact.get("twitter"),
                
                # Enriched data
                "email_verified": enriched.get("email_verified"),
                "email_deliverable": enriched.get("email_deliverable"),
                "email_score": enriched.get("email_score"),
                
                # Company info from enrichment
                "company_domain": enriched.get("company_info", {}).get("domain"),
                "company_industry": enriched.get("company_info", {}).get("industry"),
                "company_country": enriched.get("company_info", {}).get("country"),
                
                # GitHub info
                "github_url": enriched.get("github_profile", {}).get("html_url"),
                "github_bio": enriched.get("github_profile", {}).get("bio"),
                "github_followers": enriched.get("github_profile", {}).get("followers"),
                
                # Metadata
                "source_image": result.get("image_path"),
                "confidence_score": contact.get("confidence_score"),
                "enrichment_sources": ", ".join(enriched.get("enrichment_sources", [])),
                "processed_at": datetime.now().isoformat()
            }
            
            rows.append(row)
        
        # Create DataFrame and save
        df = pd.DataFrame(rows)
        df.to_csv(csv_path, index=False)
        
        logger.info(f"Generated CSV with {len(rows)} rows: {csv_path}")
        
        return csv_path
    
    def process_folder(
        self,
        folder_path: Union[str, Path],
        extensions: Optional[List[str]] = None,
        enrich: bool = True,
        generate_csv: bool = True
    ) -> Dict:
        """Process all images in a folder.
        
        Args:
            folder_path: Path to folder containing images
            extensions: List of file extensions to process
            enrich: Whether to enrich with external APIs
            generate_csv: Whether to generate CSV output
            
        Returns:
            Dictionary with batch processing results
        """
        folder_path = Path(folder_path)
        extensions = extensions or [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"]
        
        if not folder_path.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        
        # Collect all image files
        image_paths = []
        for ext in extensions:
            image_paths.extend(folder_path.glob(f"*{ext}"))
            image_paths.extend(folder_path.glob(f"*{ext.upper()}"))
        
        if not image_paths:
            logger.warning(f"No images found in {folder_path}")
            return {
                "success": False,
                "error": "No images found in folder",
                "total_images": 0
            }
        
        logger.info(f"Found {len(image_paths)} images in {folder_path}")
        
        return self.process_batch(
            image_paths,
            enrich=enrich,
            generate_csv=generate_csv
        )
    
    def get_status(self) -> Dict:
        """Get pipeline status and configuration.
        
        Returns:
            Dictionary with pipeline status
        """
        return {
            "ocr": {
                "languages": self.ocr.languages,
                "gpu": self.ocr.gpu,
                "reader_initialized": self.ocr._reader is not None
            },
            "researcher": {
                "api_usage": self.researcher.get_api_usage(),
                "apis_configured": {
                    "hunter": self.researcher.hunter_api_key is not None,
                    "abstract": self.researcher.abstract_api_key is not None,
                    "github": self.researcher.github_token is not None
                }
            },
            "output_folder": str(self.output_folder),
            "output_folder_exists": self.output_folder.exists()
        }
    
    def process_text(
        self,
        text: str,
        enrich: bool = True
    ) -> Dict:
        """Process raw text (skip OCR stage).
        
        Args:
            text: Raw text to parse
            enrich: Whether to enrich with external APIs
            
        Returns:
            Dictionary with processed results
        """
        logger.info("Processing raw text (skipping OCR)")
        
        result = {
            "success": True,
            "ocr_text": text,
            "contact_data": None,
            "enriched_data": None,
            "error": None
        }
        
        try:
            # Parse
            contact = self.parser.parse(text)
            result["contact_data"] = contact.to_dict()
            
            # Enrich
            if enrich:
                enriched = self.researcher.enrich(contact)
                result["enriched_data"] = enriched.to_dict()
            
        except Exception as e:
            logger.error(f"Error processing text: {str(e)}")
            result["success"] = False
            result["error"] = str(e)
        
        return result
