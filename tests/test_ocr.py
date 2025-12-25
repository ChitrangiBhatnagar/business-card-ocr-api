# test_ocr_fix.py
import sys
import os
from pathlib import Path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ocr import OCRExtractor

ocr = OCRExtractor(gpu=False)  # Set gpu=True if you have GPU

# Test with your problematic image
image_path = Path("2ndcard.jpg")
if image_path.exists():
    result = ocr.extract_text(image_path)
    
    print("=== OCR EXTRACTION RESULT ===")
    print(f"Success: {result['success']}")
    print(f"Method: {result['method']}")
    print(f"Confidence: {result['confidence']:.2%}")
    print("\nExtracted Text:")
    print("-" * 50)
    print(result['raw_text'])
    print("-" * 50)
else:
    print(f"Image not found: {image_path}")