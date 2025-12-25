"""
Business Card Processing Pipeline
Complete pipeline for OCR, parsing, post-processing, and enrichment

HYBRID APPROACH:
1. First try EasyOCR (FREE)
2. If confidence < threshold OR missing key fields → Fallback to Gemini (nearly free)
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from .ocr import OCRExtractor
from .parser import ContactParser
from .researcher import ContactResearcher
from .vlm_ocr import GeminiOCR, is_gemini_configured
from .enrichment import CompanyEnricher, FieldConfidenceScorer
from src.postprocessing import postprocess_contact

logger = logging.getLogger(__name__)

# Confidence threshold for Gemini fallback
GEMINI_FALLBACK_THRESHOLD = 0.70  # Use Gemini if EasyOCR confidence < 70%
MIN_REQUIRED_FIELDS = 3  # Minimum fields required (name, email, phone, company, title)


class CardResearchPipeline:
    """Complete pipeline for processing business cards.
    
    Supports hybrid OCR:
    - EasyOCR: Fast, free, good for clear cards
    - Gemini: Accurate, nearly free ($0.0001/card), fallback for difficult cards
    """

    def __init__(
        self,
        output_folder: str = "./outputs",
        ocr_languages: List[str] = None,
        ocr_gpu: bool = False,
        hunter_api_key: Optional[str] = None,
        abstract_api_key: Optional[str] = None,
        github_token: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        use_gemini_fallback: bool = True,
        gemini_model: str = "gemini-2.5-flash"
    ):
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(parents=True, exist_ok=True)

        # Primary OCR: EasyOCR (FREE)
        self.ocr = OCRExtractor(
            languages=ocr_languages or ["en"],
            gpu=ocr_gpu
        )

        self.parser = ContactParser()

        self.researcher = ContactResearcher(
            hunter_api_key=hunter_api_key,
            abstract_api_key=abstract_api_key,
            github_token=github_token
        )
        
        # Company enricher (cached - initialized once)
        self.company_enricher = CompanyEnricher()
        
        # Field confidence scorer base (reused)
        self.confidence_scorer_class = FieldConfidenceScorer

        # Fallback OCR: Gemini (nearly free, high accuracy)
        self.use_gemini_fallback = use_gemini_fallback
        self.gemini_ocr = None
        
        if use_gemini_fallback:
            api_key = gemini_api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key:
                try:
                    self.gemini_ocr = GeminiOCR(api_key=api_key, model=gemini_model)
                    if self.gemini_ocr.is_available():
                        logger.info(f"Gemini fallback enabled with model: {gemini_model}")
                    else:
                        self.gemini_ocr = None
                        logger.warning("Gemini fallback not available")
                except Exception as e:
                    logger.warning(f"Failed to initialize Gemini: {e}")
            else:
                logger.info("Gemini API key not configured. Using EasyOCR only.")

        logger.info("CardResearchPipeline initialized")

    # ======================================================
    # SINGLE IMAGE
    # ======================================================

    def _has_ocr_errors(self, contact_dict: Dict) -> bool:
        """Check if extracted data has obvious OCR errors (numbers in names, etc.)."""
        # Check if name contains numbers (like "Wi11iam" that wasn't corrected)
        name = contact_dict.get("name", "") or ""
        if name and any(c.isdigit() for c in name):
            logger.info(f"Name contains numbers: {name} - likely OCR error")
            return True
        
        # Check if company contains numbers (excluding valid ones like "3M")
        company = contact_dict.get("company", "") or ""
        if company:
            # Count digits in company name
            digit_count = sum(1 for c in company if c.isdigit())
            if digit_count > 2 and digit_count / len(company) > 0.1:
                logger.info(f"Company has too many numbers: {company} - likely OCR error")
                return True
        
        # Check if email has obvious errors
        email = contact_dict.get("email", "") or ""
        if email and ("1" in email.split("@")[0] or "0" in email.split("@")[0]):
            # Suspicious numbers in email username
            logger.info(f"Email may have OCR errors: {email}")
            return True
        
        return False

    def _should_use_gemini_fallback(self, ocr_confidence: float, contact_dict: Dict) -> bool:
        """Determine if we should fallback to Gemini for better accuracy."""
        if not self.gemini_ocr or not self.gemini_ocr.is_available():
            return False
        
        # Check confidence threshold
        if ocr_confidence < GEMINI_FALLBACK_THRESHOLD:
            logger.info(f"Low confidence ({ocr_confidence:.2%}) - using Gemini fallback")
            return True
        
        # Check if key fields are missing
        key_fields = ["name", "email", "phone", "company"]
        found_fields = sum(1 for f in key_fields if contact_dict.get(f))
        
        if found_fields < MIN_REQUIRED_FIELDS:
            logger.info(f"Missing key fields ({found_fields}/{MIN_REQUIRED_FIELDS}) - using Gemini fallback")
            return True
        
        # Check for obvious OCR errors in the extracted data
        if self._has_ocr_errors(contact_dict):
            logger.info("OCR errors detected in extracted data - using Gemini fallback")
            return True
        
        return False

    def _process_with_gemini(self, image_path: Path) -> Optional[Dict]:
        """Process image using Gemini VLM."""
        if not self.gemini_ocr:
            return None
        
        try:
            result = self.gemini_ocr.extract(image_path)
            
            if result.success:
                return {
                    "name": result.name,
                    "first_name": result.name.split()[0] if result.name else None,
                    "last_name": " ".join(result.name.split()[1:]) if result.name and len(result.name.split()) > 1 else None,
                    "title": result.title,
                    "company": result.company,
                    "email": result.email,
                    "phone": result.phone or [],
                    "website": result.website,
                    "address": result.address,
                    "linkedin": result.linkedin,
                    "confidence_score": result.confidence,
                    "raw_text": result.raw_text,
                    "ocr_method": "gemini"
                }
        except Exception as e:
            logger.error(f"Gemini processing failed: {e}")
        
        return None

    def process_image(self, image_path: Path, enrich: bool = True, force_gemini: bool = False) -> Dict:
        """
        Process a business card image.
        
        Args:
            image_path: Path to the image
            enrich: Whether to enrich with external APIs
            force_gemini: Force using Gemini (skip EasyOCR)
        """
        import time
        start_time = time.time()
        
        try:
            logger.info(f"Processing image: {image_path}")
            
            ocr_method = "easyocr"
            final_contact = None

            # Option 1: Force Gemini (for premium/batch processing)
            if force_gemini and self.gemini_ocr:
                logger.info("Using Gemini (forced)")
                final_contact = self._process_with_gemini(image_path)
                if final_contact:
                    ocr_method = "gemini"

            # Option 2: Standard flow - EasyOCR first, Gemini fallback
            if not final_contact:
                # 1️⃣ PRIMARY OCR: EasyOCR (FREE)
                ocr_start = time.time()
                ocr_result = self.ocr.extract_text(image_path)
                raw_text = ocr_result.get("raw_text", "")
                ocr_confidence = ocr_result.get("confidence", 0.0)
                logger.debug(f"⏱️ EasyOCR: {time.time() - ocr_start:.2f}s")

                # 2️⃣ PARSE
                parse_start = time.time()
                parsed_contacts = []
                if ocr_result.get("success") and raw_text:
                    parsed_contacts = self.parser.parse_from_image_text(raw_text)
                logger.debug(f"⏱️ Parse: {time.time() - parse_start:.2f}s")

                # 3️⃣ POST-PROCESS
                cleaned_contact = {}
                if parsed_contacts:
                    raw_contact_dict = parsed_contacts[0].to_dict()
                    cleaned_contact = postprocess_contact(raw_contact_dict)

                # 4️⃣ CHECK IF GEMINI FALLBACK NEEDED
                if self._should_use_gemini_fallback(ocr_confidence, cleaned_contact):
                    gemini_start = time.time()
                    gemini_result = self._process_with_gemini(image_path)
                    logger.debug(f"⏱️ Gemini fallback: {time.time() - gemini_start:.2f}s")
                    if gemini_result:
                        final_contact = gemini_result
                        ocr_method = "gemini_fallback"
                        ocr_confidence = gemini_result.get("confidence_score", 0.9)
                        raw_text = gemini_result.get("raw_text", raw_text)

                # 5️⃣ USE EASYOCR RESULT IF NO GEMINI
                if not final_contact:
                    if not parsed_contacts:
                        return {
                            "success": False,
                            "error": "No contact extracted",
                            "raw_text": raw_text,
                            "ocr_confidence": ocr_confidence,
                            "image": str(image_path)
                        }

                    final_contact = {
                        "name": cleaned_contact.get("name"),
                        "first_name": cleaned_contact.get("name").split()[0] if cleaned_contact.get("name") else None,
                        "last_name": " ".join(cleaned_contact.get("name").split()[1:]) if cleaned_contact.get("name") and len(cleaned_contact.get("name").split()) > 1 else None,
                        "title": cleaned_contact.get("title"),
                        "company": cleaned_contact.get("company"),
                        "email": cleaned_contact.get("email"),
                        "phone": cleaned_contact.get("phone") or [],
                        "website": cleaned_contact.get("website"),
                        "address": cleaned_contact.get("address"),
                        "confidence_score": cleaned_contact.get("confidence_score", ocr_confidence)
                    }

            # 6️⃣ ENRICH (optional)
            company_enrichment = {}
            field_confidence = {}
            
            if enrich and final_contact and (final_contact.get("email") or final_contact.get("name")):
                try:
                    from .parser import ContactData
                    contact_obj = ContactData(
                        name=final_contact.get("name"),
                        email=final_contact.get("email"),
                        company=final_contact.get("company")
                    )
                    enriched = self.researcher.enrich(contact_obj)
                    enriched_dict = enriched.to_dict()

                    # Merge enrichment safely
                    for key, value in enriched_dict.items():
                        if value and not final_contact.get(key):
                            final_contact[key] = value
                except Exception as e:
                    logger.warning(f"Enrichment failed: {e}")
            
            # 7️⃣ COMPANY ENRICHMENT (FREE APIs only - no Gemini, uses cached enricher)
            if final_contact:
                try:
                    company_data = self.company_enricher.enrich(
                        company_name=final_contact.get("company"),
                        email=final_contact.get("email"),
                        website=final_contact.get("website")
                    )
                    company_enrichment = company_data.to_dict()
                    
                    # Add logo URL to contact if found
                    if company_data.logo_url:
                        final_contact["company_logo"] = company_data.logo_url
                    if company_data.industry:
                        final_contact["industry"] = company_data.industry
                except Exception as e:
                    logger.warning(f"Company enrichment failed: {e}")
            
            # 8️⃣ FIELD CONFIDENCE SCORING (lightweight, no API calls)
            if final_contact:
                try:
                    scorer = self.confidence_scorer_class(base_ocr_confidence=ocr_confidence)
                    confidence_scores = scorer.score_all_fields(final_contact)
                    field_confidence = confidence_scores.to_dict()
                    
                    # Update overall confidence with detailed score
                    final_contact["confidence_score"] = confidence_scores.overall
                except Exception as e:
                    logger.warning(f"Confidence scoring failed: {e}")

            total_time = time.time() - start_time
            logger.info(f"⏱️ Total processing time: {total_time:.2f}s ({ocr_method})")
            
            return {
                "success": True,
                "contact_data": final_contact,
                "all_contacts": [final_contact],
                "contacts_count": 1,
                "raw_text": final_contact.get("raw_text", ""),
                "ocr_confidence": final_contact.get("confidence_score", 0.0),
                "ocr_method": ocr_method,
                "processing_time_ms": int(total_time * 1000),
                "field_confidence": field_confidence,
                "company_enrichment": company_enrichment,
                "image": str(image_path),
                "processed_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.exception("Pipeline error")
            return {
                "success": False,
                "error": str(e),
                "image": str(image_path)
            }

    # ======================================================
    # BATCH
    # ======================================================

    def process_batch(self, image_paths: List[Path], enrich: bool = True, force_gemini: bool = False) -> Dict:
        """Process multiple business card images.
        
        Args:
            image_paths: List of image paths
            enrich: Whether to enrich with external APIs
            force_gemini: Force using Gemini for all images
        """
        results = []
        success_count = 0

        for path in image_paths:
            result = self.process_image(path, enrich=enrich, force_gemini=force_gemini)
            results.append(result)

            if result.get("success"):
                success_count += 1

        return {
            "success": True,
            "total": len(image_paths),
            "successful": success_count,
            "failed": len(image_paths) - success_count,
            "results": results
        }

    # ======================================================
    # STATUS
    # ======================================================

    def get_status(self) -> Dict:
        """Get pipeline status information."""
        return {
            "ocr_engine": "easyocr",
            "gemini_fallback_enabled": self.gemini_ocr is not None and self.gemini_ocr.is_available(),
            "gemini_model": self.gemini_ocr.model_name if self.gemini_ocr else None,
            "ocr_languages": self.ocr.languages,
            "output_folder": str(self.output_folder)
        }
