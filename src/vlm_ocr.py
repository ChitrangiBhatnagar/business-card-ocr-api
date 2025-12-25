"""
Vision Language Model OCR using Gemini (cost-effective fallback).
Only used when EasyOCR confidence is low or fields are missing.

Gemini Flash is nearly free: ~$0.0001 per business card
Free tier: 1500 requests/day
"""

import os
import base64
import json
import logging
import re
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Try to import google genai (new package)
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    # Fallback to old package
    try:
        import google.generativeai as genai
        types = None
        GEMINI_AVAILABLE = True
        logger.warning("Using deprecated google-generativeai package. Consider upgrading to google-genai")
    except ImportError:
        GEMINI_AVAILABLE = False
        genai = None
        types = None
        logger.warning("google-genai not installed. Run: pip install google-genai")


@dataclass
class VLMResult:
    """Result from VLM OCR extraction."""
    success: bool
    name: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[List[str]] = None
    website: Optional[str] = None
    address: Optional[str] = None
    linkedin: Optional[str] = None
    raw_text: Optional[str] = None
    confidence: float = 0.0
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "name": self.name,
            "title": self.title,
            "company": self.company,
            "email": self.email,
            "phone": self.phone or [],
            "website": self.website,
            "address": self.address,
            "linkedin": self.linkedin,
            "raw_text": self.raw_text,
            "confidence_score": self.confidence,
            "error": self.error
        }


class GeminiOCR:
    """
    Gemini-based OCR for business cards.
    Uses Gemini 1.5/2.0 Flash for cost-effective, high-accuracy extraction.
    """
    
    # Extraction prompt - optimized for business cards
    EXTRACTION_PROMPT = """Analyze this business card image and extract ALL contact information.

Return a JSON object with these exact fields (use null if not found):
{
    "name": "Full name of the person",
    "title": "Job title/position",
    "company": "Company/organization name",
    "email": "Email address",
    "phone": ["Array of phone numbers"],
    "website": "Website URL",
    "address": "Full address",
    "linkedin": "LinkedIn URL or handle",
    "raw_text": "All visible text on the card"
}

Rules:
- Extract EXACTLY what you see, don't invent information
- For phone, include all numbers found (mobile, office, fax)
- Clean up any OCR-like errors in text
- If a field is not visible, use null
- Return ONLY valid JSON, no markdown or explanation"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash"):
        """
        Initialize Gemini OCR.
        
        Args:
            api_key: Google API key (or set GOOGLE_API_KEY env var)
            model: Model to use (gemini-2.5-flash, gemini-2.0-flash-exp, gemini-1.5-flash, gemini-1.5-pro)
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.model_name = model
        self.model = None
        
        if not GEMINI_AVAILABLE:
            logger.error("google-generativeai package not installed")
            return
            
        if not self.api_key:
            logger.warning("No Gemini API key provided. Set GOOGLE_API_KEY or GEMINI_API_KEY env var")
            return
        
        try:
            # New google-genai package
            if types is not None:
                self.client = genai.Client(api_key=self.api_key)
                self.use_new_api = True
            else:
                # Old google-generativeai package
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(self.model_name)
                self.use_new_api = False
            logger.info(f"Gemini OCR initialized with model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
    
    def is_available(self) -> bool:
        """Check if Gemini is available and configured."""
        if hasattr(self, 'use_new_api') and self.use_new_api:
            return hasattr(self, 'client') and self.client is not None
        return self.model is not None
    
    def _load_image(self, image_path: Path) -> Optional[Dict]:
        """Load image and prepare for Gemini API."""
        try:
            with open(image_path, "rb") as f:
                image_data = f.read()
            
            # Determine mime type
            suffix = image_path.suffix.lower()
            mime_types = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".webp": "image/webp",
                ".bmp": "image/bmp"
            }
            mime_type = mime_types.get(suffix, "image/jpeg")
            
            return {
                "mime_type": mime_type,
                "data": base64.b64encode(image_data).decode("utf-8")
            }
        except Exception as e:
            logger.error(f"Failed to load image: {e}")
            return None
    
    def _parse_response(self, response_text: str) -> Dict:
        """Parse JSON from Gemini response."""
        try:
            # Try direct JSON parse
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code block
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # Try to find JSON object in text
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass
        
        return {}
    
    def extract(self, image_path: Path) -> VLMResult:
        """
        Extract contact information from business card image.
        
        Args:
            image_path: Path to business card image
            
        Returns:
            VLMResult with extracted data
        """
        if not self.is_available():
            return VLMResult(
                success=False,
                error="Gemini not configured. Set GOOGLE_API_KEY environment variable."
            )
        
        try:
            # Load image
            image_data = self._load_image(Path(image_path))
            if not image_data:
                return VLMResult(success=False, error="Failed to load image")
            
            # Call Gemini API
            logger.info(f"Calling Gemini API for: {image_path}")
            
            if hasattr(self, 'use_new_api') and self.use_new_api:
                # New google-genai API
                with open(image_path, "rb") as f:
                    image_bytes = f.read()
                
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[
                        types.Content(
                            parts=[
                                types.Part.from_text(text=self.EXTRACTION_PROMPT),
                                types.Part.from_bytes(data=image_bytes, mime_type=image_data["mime_type"])
                            ]
                        )
                    ],
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        max_output_tokens=1024
                    )
                )
                response_text = response.text
            else:
                # Old google-generativeai API - fallback for compatibility
                image_part = {
                    "inline_data": image_data
                }
                
                # Import the old package if needed
                try:
                    import google.generativeai as old_genai
                    if not hasattr(self, 'old_model'):
                        old_genai.configure(api_key=self.api_key)
                        self.old_model = old_genai.GenerativeModel(self.model_name)
                    
                    response = self.old_model.generate_content(
                        [self.EXTRACTION_PROMPT, image_part],
                        generation_config={
                            "temperature": 0.1,
                            "max_output_tokens": 1024
                        }
                    )
                    response_text = response.text
                except ImportError:
                    return VLMResult(
                        success=False,
                        error="Neither google-genai nor google-generativeai package available"
                    )
            
            logger.debug(f"Gemini response: {response_text[:500]}")
            
            data = self._parse_response(response_text)
            
            if not data:
                return VLMResult(
                    success=False,
                    error="Failed to parse Gemini response",
                    raw_text=response_text
                )
            
            # Calculate confidence based on extracted fields
            fields = [data.get("name"), data.get("email"), data.get("phone"), 
                     data.get("company"), data.get("title")]
            valid_fields = sum(1 for f in fields if f)
            confidence = min(valid_fields / 5, 1.0) * 0.95  # Max 95% for VLM
            
            # Handle phone as list
            phone = data.get("phone")
            if isinstance(phone, str):
                phone = [phone] if phone else []
            elif not isinstance(phone, list):
                phone = []
            
            return VLMResult(
                success=True,
                name=data.get("name"),
                title=data.get("title"),
                company=data.get("company"),
                email=data.get("email"),
                phone=phone,
                website=data.get("website"),
                address=data.get("address"),
                linkedin=data.get("linkedin"),
                raw_text=data.get("raw_text", response_text),
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Gemini extraction failed: {e}", exc_info=True)
            return VLMResult(success=False, error=str(e))
    
    def extract_batch(self, image_paths: List[Path]) -> List[VLMResult]:
        """
        Extract from multiple images.
        Note: Processes sequentially to respect rate limits.
        
        Args:
            image_paths: List of image paths
            
        Returns:
            List of VLMResult objects
        """
        results = []
        for path in image_paths:
            result = self.extract(path)
            results.append(result)
        return results


# Convenience function
def extract_with_gemini(image_path: Path, api_key: Optional[str] = None) -> VLMResult:
    """
    Convenience function to extract business card data using Gemini.
    
    Args:
        image_path: Path to business card image
        api_key: Optional API key (defaults to GOOGLE_API_KEY env var)
        
    Returns:
        VLMResult with extracted data
    """
    ocr = GeminiOCR(api_key=api_key)
    return ocr.extract(image_path)


# Check if Gemini is configured
def is_gemini_configured() -> bool:
    """Check if Gemini API is configured."""
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    return bool(api_key) and GEMINI_AVAILABLE
