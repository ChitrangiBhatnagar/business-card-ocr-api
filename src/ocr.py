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
        gpu: bool = False,
        max_dimension: int = 1600,
        enhance_images: bool = False,
        canvas_size: int = 1280,
        mag_ratio: float = 1.0,
        min_size: int = 10
    ) -> None:
        """Initialize the CardOCR with EasyOCR reader.
        
        Args:
            languages: List of language codes (default: ["en"])
            gpu: Whether to use GPU for OCR processing
        """
        self.languages = languages or ["en"]
        self.gpu = gpu
        self._reader: Optional[easyocr.Reader] = None
        # Performance/tuning parameters
        self.max_dimension = max_dimension
        self.enhance_images = enhance_images
        self.canvas_size = canvas_size
        self.mag_ratio = mag_ratio
        self.min_size = min_size
        
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
            
            # Perform OCR with optimized parameters for business cards
            results = self.reader.readtext(
                image,
                detail=detail,
                paragraph=paragraph,
                min_size=self.min_size,           # Minimum text size
                text_threshold=0.6,    # Lower threshold for text detection
                low_text=0.3,          # Lower bound for text detection
                link_threshold=0.3,    # Link adjacent text
                canvas_size=self.canvas_size,      # Canvas for detection
                mag_ratio=self.mag_ratio,         # Magnification ratio
                slope_ths=0.2,         # Slope threshold for text lines
                ycenter_ths=0.5,       # Y-center threshold
                height_ths=0.5,        # Height threshold
                width_ths=0.5,         # Width threshold
                add_margin=0.1,        # Add margin around detected text
                contrast_ths=0.1,      # Contrast threshold
                adjust_contrast=0.5    # Contrast adjustment
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
        """Advanced preprocessing for better OCR accuracy: auto-rotation, shadow removal, background cropping, enhancement."""
        try:
            # Open image with PIL
            image = Image.open(image_path)
            # Convert to RGB if necessary
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Auto-rotate using EXIF
            try:
                exif = image._getexif()
                if exif is not None:
                    orientation = exif.get(274)
                    if orientation == 3:
                        image = image.rotate(180, expand=True)
                    elif orientation == 6:
                        image = image.rotate(270, expand=True)
                    elif orientation == 8:
                        image = image.rotate(90, expand=True)
            except Exception:
                pass

            # Downscale large images to a maximum dimension
            width, height = image.size
            if self.max_dimension and (width > self.max_dimension or height > self.max_dimension):
                scale = min(self.max_dimension / width, self.max_dimension / height)
                new_size = (int(width * scale), int(height * scale))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
                logger.debug(f"Downscaled image from {width}x{height} to {new_size}")

            # Convert to numpy array
            img_array = np.array(image)

            # Advanced preprocessing with OpenCV
            try:
                if not self.enhance_images:
                    raise ImportError("Image enhancement disabled")
                import cv2

                # Convert to grayscale
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

                # Shadow removal (morphological closing)
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
                bg = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
                diff = 255 - cv2.absdiff(gray, bg)
                norm = cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX)

                # Adaptive thresholding for binarization
                bin_img = cv2.adaptiveThreshold(norm, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                                cv2.THRESH_BINARY, 35, 11)

                # Find contours and crop to largest contour (assume card is largest object)
                contours, _ = cv2.findContours(bin_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    largest = max(contours, key=cv2.contourArea)
                    x, y, w, h = cv2.boundingRect(largest)
                    crop_img = img_array[y:y+h, x:x+w]
                    img_array = crop_img
                    logger.debug(f"Cropped to largest contour: {x},{y},{w},{h}")

                # Denoising
                denoised = cv2.fastNlMeansDenoising(cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY), None, 10, 7, 21)

                # Contrast enhancement
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                enhanced = clahe.apply(denoised)

                # Sharpening
                kernel = np.array([[-1, -1, -1],
                                   [-1,  9, -1],
                                   [-1, -1, -1]])
                sharpened = cv2.filter2D(enhanced, -1, kernel)

                # Convert back to RGB for EasyOCR
                img_array = cv2.cvtColor(sharpened, cv2.COLOR_GRAY2RGB)
                logger.debug("Applied advanced image enhancement with OpenCV")

            except ImportError:
                logger.debug("OpenCV not available, using raw image")
            except Exception as e:
                logger.debug(f"Advanced image enhancement failed, using raw image: {e}")

            return img_array

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
