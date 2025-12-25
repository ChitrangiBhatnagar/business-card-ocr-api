"""
Image Preprocessing Module for Business Card OCR
Enhances image quality for optimal text extraction
"""

import cv2
import numpy as np
from PIL import Image
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """Preprocesses business card images for optimal OCR results."""
    
    @staticmethod
    def preprocess_for_ocr(image_path: Path, output_path: Path = None) -> np.ndarray:
        """
        Apply comprehensive preprocessing to improve OCR accuracy.
        
        Args:
            image_path: Path to input image
            output_path: Optional path to save preprocessed image
            
        Returns:
            Preprocessed image as numpy array
        """
        try:
            # Read image
            img = cv2.imread(str(image_path))
            
            if img is None:
                raise ValueError(f"Could not read image: {image_path}")
            
            logger.debug(f"Original image shape: {img.shape}")
            
            # 1. Resize if too small (min 1500px width for better OCR)
            height, width = img.shape[:2]
            if width < 1500:
                scale = 1500 / width
                new_width = int(width * scale)
                new_height = int(height * scale)
                img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
                logger.debug(f"Resized to: {new_width}x{new_height}")
            
            # 2. Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # 3. Deskew if card is rotated
            deskewed = ImagePreprocessor.deskew_image(gray)
            
            # 4. Denoise
            denoised = cv2.fastNlMeansDenoising(deskewed, None, h=10, templateWindowSize=7, searchWindowSize=21)
            
            # 5. Increase contrast using CLAHE (handles shadows & lighting variations)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(10, 10))
            enhanced = clahe.apply(denoised)
            
            # 5. Sharpen image
            kernel_sharpening = np.array([
                [-1, -1, -1],
                [-1,  9, -1],
                [-1, -1, -1]
            ])
            sharpened = cv2.filter2D(enhanced, -1, kernel_sharpening)
            
            # 6. Apply adaptive thresholding
            binary1 = cv2.adaptiveThreshold(
                sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            binary2 = cv2.threshold(
                sharpened, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )[1]
            
            # Use the one with better characteristics
            if np.sum(binary1 == 255) > np.sum(binary2 == 255):
                binary = binary1
            else:
                binary = binary2
            
            # 7. Morphological operations to clean up
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            
            # 8. Remove border noise
            cleaned = ImagePreprocessor._remove_borders(cleaned)
            
            # Save if output path provided
            if output_path:
                cv2.imwrite(str(output_path), cleaned)
                logger.debug(f"Saved preprocessed image to: {output_path}")
            
            return cleaned
            
        except Exception as e:
            logger.error(f"Preprocessing failed: {e}")
            raise
    
    @staticmethod
    def _remove_borders(img: np.ndarray, border_size: int = 5) -> np.ndarray:
        """Remove border noise from image."""
        h, w = img.shape[:2]
        img_copy = img.copy()
        
        # Set borders to white
        img_copy[0:border_size, :] = 255
        img_copy[h-border_size:h, :] = 255
        img_copy[:, 0:border_size] = 255
        img_copy[:, w-border_size:w] = 255
        
        return img_copy
    
    @staticmethod
    def deskew_image(image: np.ndarray) -> np.ndarray:
        """Deskew image if it's rotated (crooked card photo)."""
        # Use edge detection for better angle estimation
        edges = cv2.Canny(image, 50, 150)
        
        # Find contours and calculate rotation angle
        contours = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = contours[0] if len(contours) == 2 else contours[1]
        
        if len(contours) == 0:
            return image
        
        # Get the largest contour (should be the card)
        c = max(contours, key=cv2.contourArea)
        rect = cv2.minAreaRect(c)
        angle = rect[-1]
        
        # Normalize angle to [-90, 0)
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        
        # Only deskew if angle is significant (>1 degree)
        if abs(angle) > 1.0:
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(
                image, M, (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE
            )
            logger.debug(f"Deskewed image by {angle:.1f} degrees")
            return rotated
        
        return image