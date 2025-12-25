"""
Enhanced OCR Extractor using your accurate EasyOCR configuration.
"""
import logging
from pathlib import Path
from typing import Dict, List, Tuple
import cv2
import numpy as np
import easyocr
import uuid
import os
import re

logger = logging.getLogger(__name__)

class OCRExtractor:
    """OCR extractor using your accurate EasyOCR setup."""
    
    def __init__(
        self,
        languages: List[str] = None,
        gpu: bool = False,
        model_dir: str = "./models"
    ):
        """
        Initialize OCR extractor.
        
        Args:
            languages: List of languages for OCR
            gpu: Use GPU for OCR
            model_dir: Directory for model storage
        """
        self.languages = languages or ['en']
        self.gpu = gpu
        
        # Create models directory
        os.makedirs(model_dir, exist_ok=True)
        
        # Initialize EasyOCR with YOUR configuration
        logger.info(f"Initializing EasyOCR with languages: {self.languages}")
        try:
            self.reader = easyocr.Reader(
                lang_list=self.languages,
                gpu=self.gpu,
                model_storage_directory=model_dir,
                download_enabled=True,
                recog_network='english_g2',  # Better English model
                verbose=False
            )
            logger.info("EasyOCR initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")
            raise
        
        # Temporary directory for processed images
        self.temp_dir = Path("./temp_ocr")
        self.temp_dir.mkdir(exist_ok=True)
        
        # Word-level corrections (applied to whole words/common patterns)
        # These are specific known OCR mistakes
        self.word_corrections = {
            # Common name mistakes (1 should be l or i)
            "Wi11iam": "William",
            "Wil1iam": "William", 
            "W1lliam": "William",
            "Mo11y": "Molly",
            "Mol1y": "Molly",
            "Mi11er": "Miller",
            "Mil1er": "Miller",
            "A1ex": "Alex",
            "A1ice": "Alice",
            "Phi1ip": "Philip",
            "Phi11ip": "Phillip",
            "Bi11": "Bill",
            "Wi1son": "Wilson",
            "W1lson": "Wilson",
            "Michae1": "Michael",
            "Danie1": "Daniel",
            "Samue1": "Samuel",
            "Pau1": "Paul",
            "Char1es": "Charles",
            "Char1ie": "Charlie",
            "Ol1via": "Olivia",
            "O1ivia": "Olivia",
            "0livia": "Olivia",
            "El1a": "Ella",
            "E1la": "Ella",
            "Mi1es": "Miles",
            "Ga1e": "Gale",
            "Ke11y": "Kelly",
            "Kel1y": "Kelly",
            "Sa11y": "Sally",
            "Sal1y": "Sally",
            "Ho11y": "Holly",
            "Hol1y": "Holly",
            "Li1y": "Lily",
            "L1ly": "Lily",
            "Li11ian": "Lillian",
            "Lil1ian": "Lillian",
            "Ha11": "Hall",
            "Hal1": "Hall",
            
            # Common title mistakes
            "Rea1": "Real",
            "rea1": "real",
            "Rea1 Estate": "Real Estate",
            "Sa1es": "Sales",
            "sa1es": "sales",
            "Genera1": "General",
            
            # Company word mistakes
            "So1utions": "Solutions",
            "so1utions": "solutions",
            "Techno1ogy": "Technology",
            "techno1ogy": "technology",
            "Techno1ogies": "Technologies",
            "G1oba1": "Global",
            "g1oba1": "global",
            "Financia1": "Financial",
            "Digita1": "Digital",
            "Professiona1": "Professional",
            "Internationa1": "International",
            "Industria1": "Industrial",
            "Capita1": "Capital",
            "Lega1": "Legal",
            "Socia1": "Social",
            "Virtua1": "Virtual",
            "Centra1": "Central",
            "Roya1": "Royal",
            "Imperia1": "Imperial",
            "Universa1": "Universal",
            "Coasta1": "Coastal",
            "Regiona1": "Regional",
            "Nationa1": "National",
            "Federa1": "Federal",
            "Commercia1": "Commercial",
            "Residentia1": "Residential",
            "Municipa1": "Municipal",
            "Cora1": "Coral",
            "Crysta1": "Crystal",
            "Meta1": "Metal",
            "Tota1": "Total",
            "Fisca1": "Fiscal",
            "Corpora1": "Corporal",
            
            # Other common words
            "1ive": "live",
            "1ife": "life",
            "on1ine": "online",
            "On1ine": "Online",
            "mobi1e": "mobile",
            "Mobi1e": "Mobile",
            "emai1": "email",
            "Emai1": "Email",
            "1obster": "lobster",
            "Lobster": "Lobster",
            "1ishing": "fishing", 
            "fishing": "fishing",
            "B1ue": "Blue",
            "b1ue": "blue",
            "Purp1e": "Purple",
            "Yel1ow": "Yellow",
            "Go1d": "Gold",
            "Si1ver": "Silver",
            "P1atinum": "Platinum",
            
            # Domain fixes
            "c0m": "com",
            ".c0m": ".com",
            "cQm": "com",
            ".cQm": ".com",
            "ccm": "com",
            ".ccm": ".com",
            
            # Common company suffixes
            "1nc": "Inc",
            "1NC": "INC",
            "L1C": "LLC",
            "11C": "LLC",
            "1LC": "LLC",
            "Corp0ration": "Corporation",
            "Corporat1on": "Corporation",
            
            # State abbreviations 
            "F1orida": "Florida",
            "Ca1ifornia": "California",
            "I11inois": "Illinois",
            "Pennsy1vania": "Pennsylvania",
            "Caro1ina": "Carolina",
            
            # Misc
            "Manag3r": "Manager",
            "D1rector": "Director",
            "Eng1neer": "Engineer",
            "Deve1oper": "Developer",
            "Consu1tant": "Consultant",
            "Spec1alist": "Specialist",
            "Ana1yst": "Analyst",
            "Adm1n": "Admin",
        }
        
        logger.info("OCR extractor initialized with word corrections")
    
    def _preprocess_image(self, image_path: Path) -> str:
        """
        Preprocess image using YOUR accurate preprocessing.
        
        Args:
            image_path: Path to image
            
        Returns:
            Path to preprocessed temporary image
        """
        try:
            # Read image
            img = cv2.imread(str(image_path))
            if img is None:
                raise ValueError(f"Cannot read image: {image_path}")
            
            # Step 1: Enhanced resizing with aspect ratio preservation
            h, w = img.shape[:2]
            
            # Target optimal dimensions for EasyOCR
            target_width = 1600  # Sweet spot for EasyOCR
            if w < target_width:
                scale = target_width / w
                new_w = target_width
                new_h = int(h * scale)
                img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
            elif w > 2400:  # Too large, scale down
                scale = 2400 / w
                new_w = int(w * scale)
                new_h = int(h * scale)
                img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            
            logger.debug(f"Resized from {w}x{h} to {img.shape[1]}x{img.shape[0]}")
            
            # Step 2: Convert to grayscale with optimal method
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Step 3: Advanced denoising
            gray = cv2.fastNlMeansDenoising(gray, None, h=8, templateWindowSize=7, searchWindowSize=21)
            
            # Step 4: Adaptive contrast enhancement
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(12, 12))
            gray = clahe.apply(gray)
            
            # Step 5: Enhanced sharpening with edge preservation
            # Gaussian blur to find edges
            blurred = cv2.GaussianBlur(gray, (0, 0), 1.0)
            # Unsharp mask
            gray = cv2.addWeighted(gray, 1.5, blurred, -0.5, 0)
            
            # Step 6: Morphological operations to clean up text
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            gray = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
            
            # Step 7: Final contrast adjustment
            gray = cv2.convertScaleAbs(gray, alpha=1.1, beta=10)
            
            # Save to temp file
            temp_path = self.temp_dir / f"{uuid.uuid4()}.png"
            cv2.imwrite(str(temp_path), gray)
            
            logger.debug(f"Preprocessed image saved to: {temp_path}")
            return str(temp_path)
            
        except Exception as e:
            logger.error(f"Image preprocessing error: {e}")
            # Return original path if preprocessing fails
            return str(image_path)
    
    def _correct_ocr_text(self, text: str) -> str:
        """
        Apply smart word-level corrections to OCR text.
        
        The key insight: EasyOCR often mistakes 'l' (lowercase L) for '1' (one).
        We fix this by correcting known word patterns.
        
        Args:
            text: Raw OCR text
            
        Returns:
            Corrected text
        """
        # Apply word-level corrections (specific known patterns)
        for wrong, correct in self.word_corrections.items():
            # Case-insensitive replacement but preserve case when possible
            text = re.sub(re.escape(wrong), correct, text, flags=re.IGNORECASE)
        
        # Smart context-aware 1 → l conversion
        # In words that have letters around the 1, it's probably an 'l'
        # Pattern: letter + 1 + letter (like "b1ue" → "blue")
        text = re.sub(r'([a-zA-Z])1([a-zA-Z])', r'\1l\2', text)
        
        # Pattern: start of word + 1 + letters (like "1ive" → "live", but not "1234")
        text = re.sub(r'\b1([a-zA-Z]{2,})', r'l\1', text)
        
        # Pattern: letters + 1 at end of word (like "emai1" → "email")
        text = re.sub(r'([a-zA-Z]{2,})1\b', r'\1l', text)
        
        # Fix double 1s that should be ll (like "wa11" → "wall")
        text = re.sub(r'([a-zA-Z])11([a-zA-Z])', r'\1ll\2', text)
        text = re.sub(r'([a-zA-Z])11\b', r'\1ll', text)
        
        # Fix 0 → o in words (like "s0lutions" → "solutions")
        text = re.sub(r'([a-zA-Z])0([a-zA-Z])', r'\1o\2', text)
        
        # Fix email domains
        text = re.sub(r'@(\w+)\s*\.\s*com\b', r'@\1.com', text, flags=re.IGNORECASE)
        text = re.sub(r'@(\w+)\s+com\b', r'@\1.com', text, flags=re.IGNORECASE)
        text = re.sub(r'(\w+)@(\w+)\.c[o0]m\b', r'\1@\2.com', text, flags=re.IGNORECASE)
        
        # Fix website URLs
        text = re.sub(r'www\s*\.\s*', 'www.', text, flags=re.IGNORECASE)
        text = re.sub(r'\.c[o0]m\b', '.com', text, flags=re.IGNORECASE)
        
        # Remove extra spaces
        text = ' '.join(text.split())
        
        return text
    
    def _postprocess_text(self, lines: List[str]) -> List[str]:
        """
        Postprocess OCR text lines.
        
        Args:
            lines: Raw OCR lines
            
        Returns:
            Cleaned text lines
        """
        cleaned_lines = []
        
        for line in lines:
            # Apply text correction
            line = self._correct_ocr_text(line)
            
            # Filter out lines that are too short or garbage
            if len(line.strip()) > 1:  # At least 2 characters
                # Remove lines that are mostly special characters
                char_count = len([c for c in line if c.isalnum()])
                if char_count / len(line) > 0.5:  # At least 50% alphanumeric
                    cleaned_lines.append(line.strip())
        
        return cleaned_lines
    
    def extract_text(self, image_path: Path) -> Dict:
        """
        Extract text from image using YOUR accurate OCR.
        
        Args:
            image_path: Path to image
            
        Returns:
            Dictionary with extraction results
        """
        try:
            logger.info(f"Extracting text from {image_path}")
            
            # Step 1: Preprocess image for optimal EasyOCR performance
            processed_path = self._preprocess_image(image_path)
            
            # Step 2: Run OCR with safe settings to avoid numpy/scipy shape errors
            # Read image properly first
            img = cv2.imread(str(processed_path))
            if img is None:
                raise ValueError(f"Could not load image: {processed_path}")
                
            # Ensure image is in correct format (BGR, uint8)
            if len(img.shape) == 3 and img.shape[2] > 3:
                # Handle RGBA or other multi-channel formats
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            elif len(img.shape) == 2:
                # Convert grayscale to BGR
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                
            # Ensure proper dtype
            if img.dtype != np.uint8:
                img = img.astype(np.uint8)
            
            results = self.reader.readtext(
                img,
                detail=1,  # Get bounding boxes and confidence scores
                paragraph=False,  # Get individual text regions
                rotation_info=None  # Disable rotation to avoid shape errors
            )
            
            # Step 3: Enhanced result processing
            lines = []
            confidences = []
            
            # Sort results by Y coordinate (top to bottom) for better line ordering
            results.sort(key=lambda x: x[0][0][1])  # Sort by top-left Y coordinate
            
            for bbox, text, confidence in results:
                text = text.strip()
                # Only include text with decent confidence and reasonable length
                if confidence >= 0.15 and len(text) >= 2:
                    lines.append(text)
                    confidences.append(confidence)
            
            # Step 4: Advanced text post-processing
            cleaned_lines = self._postprocess_text(lines)
            
            # Step 5: Calculate weighted average confidence (higher weights for longer text)
            if confidences:
                weights = [len(line) for line in lines]
                weighted_conf = sum(c * w for c, w in zip(confidences, weights))
                total_weight = sum(weights)
                avg_confidence = weighted_conf / total_weight if total_weight > 0 else sum(confidences) / len(confidences)
            else:
                avg_confidence = 0.0
            
            # Step 6: Clean up temp file if we created one
            if processed_path != str(image_path):
                try:
                    os.remove(processed_path)
                except:
                    pass
            
            logger.info(f"Extracted {len(cleaned_lines)} lines with {avg_confidence:.2%} confidence")
            
            if not cleaned_lines:
                return {
                    "success": False,
                    "error": "No text extracted from image",
                    "raw_text": "",
                    "confidence": 0.0,
                    "method": "easyocr_enhanced"
                }
            
            return {
                "success": True,
                "raw_text": "\n".join(cleaned_lines),
                "confidence": avg_confidence,
                "method": "easyocr_enhanced"
            }
            
        except Exception as e:
            logger.error(f"OCR extraction error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "raw_text": "",
                "confidence": 0.0,
                "method": "easyocr"
            }