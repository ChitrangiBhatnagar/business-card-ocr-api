"""
OCR module for Business Card Processing API.

Handles image-to-text extraction using EasyOCR.
"""

import logging
from typing import List, Optional, Tuple, Union
from pathlib import Path

import easyocr
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)


class CardOCR:
    """Handles OCR extraction from business card images using EasyOCR.
    
    This class provides methods to extract text from business card images
    with confidence scoring and preprocessing capabilities.
    
    Attributes:
        reader: EasyOCR Reader instance
        languages: List of language codes for OCR
        gpu: Whether to use GPU acceleration
    """
    
    def __init__(
        self, 
        languages: Optional[List[str]] = None, 
        gpu: bool = False
    ) -> None:
        """Initialize the CardOCR with EasyOCR reader.
        
        Args:
            languages: List of language codes (default: ["en"])
            gpu: Whether to use GPU for OCR processing
        """
        self.languages = languages or ["en"]
        self.gpu = gpu
        self._reader: Optional[easyocr.Reader] = None
        
        logger.info(
            f"CardOCR initialized with languages={self.languages}, gpu={self.gpu}"
        )
    
    @property
    def reader(self) -> easyocr.Reader:
        """Lazy initialization of EasyOCR reader.
        
        Returns:
            Initialized EasyOCR Reader instance
        """
        if self._reader is None:
            logger.info("Initializing EasyOCR reader (this may take a moment)...")
            self._reader = easyocr.Reader(
                self.languages, 
                gpu=self.gpu,
                verbose=False
            )
            logger.info("EasyOCR reader initialized successfully")
        return self._reader
    
    def extract_text(
        self, 
        image_path: Union[str, Path],
        detail: int = 1,
        paragraph: bool = False
    ) -> List[Tuple[str, float]]:
        """Extract text from a business card image.
        
        Args:
            image_path: Path to the image file
            detail: Level of detail (0 for text only, 1 for full details)
            paragraph: Whether to merge text into paragraphs
            
        Returns:
            List of tuples containing (text, confidence_score)
            
        Raises:
            FileNotFoundError: If image file doesn't exist
            ValueError: If image cannot be processed
        """
        image_path = Path(image_path)
        
        if not image_path.exists():
            logger.error(f"Image file not found: {image_path}")
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        try:
            logger.debug(f"Processing image: {image_path}")
            
            # Read and preprocess image
            image = self._preprocess_image(image_path)
            
            # Perform OCR
            results = self.reader.readtext(
                image,
                detail=detail,
                paragraph=paragraph
            )
            
            # Parse results based on detail level
            if detail == 0:
                # Simple text list
                extracted = [(text, 1.0) for text in results]
            else:
                # Full details: [(bbox, text, confidence), ...]
                extracted = [(item[1], item[2]) for item in results]
            
            logger.info(
                f"Extracted {len(extracted)} text segments from {image_path.name}"
            )
            
            return extracted
            
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {str(e)}")
            raise ValueError(f"Failed to process image: {str(e)}")
    
    def extract_text_simple(
        self, 
        image_path: Union[str, Path]
    ) -> str:
        """Extract text from image as a single string.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Concatenated text from the image
        """
        results = self.extract_text(image_path, detail=1, paragraph=False)
        
        # Sort by confidence and join
        text_lines = [text for text, _ in results]
        return "\n".join(text_lines)
    
    def extract_with_positions(
        self, 
        image_path: Union[str, Path]
    ) -> List[dict]:
        """Extract text with bounding box positions.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            List of dictionaries with text, confidence, and bounding box
        """
        image_path = Path(image_path)
        
        try:
            image = self._preprocess_image(image_path)
            results = self.reader.readtext(image, detail=1)
            
            extracted = []
            for bbox, text, confidence in results:
                extracted.append({
                    "text": text,
                    "confidence": round(confidence, 4),
                    "bounding_box": bbox,
                    "top_left": bbox[0],
                    "bottom_right": bbox[2]
                })
            
            return extracted
            
        except Exception as e:
            logger.error(f"Error extracting with positions: {str(e)}")
            raise
    
    def _preprocess_image(
        self, 
        image_path: Union[str, Path]
    ) -> np.ndarray:
        """Preprocess image for better OCR results.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Preprocessed image as numpy array
        """
        try:
            # Open image with PIL
            image = Image.open(image_path)
            
            # Convert to RGB if necessary
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            # Resize if too small (EasyOCR works better with larger images)
            min_dimension = 800
            width, height = image.size
            
            if width < min_dimension or height < min_dimension:
                scale = max(min_dimension / width, min_dimension / height)
                new_size = (int(width * scale), int(height * scale))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
                logger.debug(f"Resized image from {width}x{height} to {new_size}")
            
            # Convert to numpy array
            return np.array(image)
            
        except Exception as e:
            logger.error(f"Image preprocessing failed: {str(e)}")
            raise ValueError(f"Failed to preprocess image: {str(e)}")
    
    def get_confidence_stats(
        self, 
        results: List[Tuple[str, float]]
    ) -> dict:
        """Calculate confidence statistics for OCR results.
        
        Args:
            results: List of (text, confidence) tuples
            
        Returns:
            Dictionary with min, max, mean, and count statistics
        """
        if not results:
            return {
                "count": 0,
                "min_confidence": 0.0,
                "max_confidence": 0.0,
                "mean_confidence": 0.0
            }
        
        confidences = [conf for _, conf in results]
        
        return {
            "count": len(results),
            "min_confidence": round(min(confidences), 4),
            "max_confidence": round(max(confidences), 4),
            "mean_confidence": round(sum(confidences) / len(confidences), 4)
        }
    
    def is_valid_card(
        self, 
        results: List[Tuple[str, float]], 
        min_segments: int = 3,
        min_avg_confidence: float = 0.5
    ) -> bool:
        """Check if OCR results indicate a valid business card.
        
        Args:
            results: List of (text, confidence) tuples
            min_segments: Minimum number of text segments required
            min_avg_confidence: Minimum average confidence required
            
        Returns:
            True if results appear to be from a valid business card
        """
        if len(results) < min_segments:
            logger.debug(f"Too few segments: {len(results)} < {min_segments}")
            return False
        
        stats = self.get_confidence_stats(results)
        
        if stats["mean_confidence"] < min_avg_confidence:
            logger.debug(
                f"Low confidence: {stats['mean_confidence']} < {min_avg_confidence}"
            )
            return False
        
        return True
