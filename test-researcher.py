"""
Test script for enhanced OCR pipeline
Run this to verify improvements
"""

from src.pipeline import CardResearchPipeline
from pathlib import Path
import sys

def test_card(image_path: str):
    """Test processing a single card."""
    
    print("="*60)
    print("TESTING ENHANCED OCR PIPELINE")
    print("="*60)
    
    # Initialize pipeline
    print("\n[1/4] Initializing pipeline...")
    pipeline = CardResearchPipeline(
        output_folder="./outputs",
        ocr_languages=['en'],
        ocr_gpu=False  # Set to True if you have CUDA GPU
    )
    print("✓ Pipeline initialized")
    
    # Check if file exists
    image_file = Path(image_path)
    if not image_file.exists():
        print(f"\n✗ Error: Image not found: {image_path}")
        return
    
    # Process image
    print(f"\n[2/4] Processing image: {image_file.name}")
    result = pipeline.process_image(image_file, enrich=False)
    
    # Display results
    print(f"\n[3/4] Processing complete!")
    print("-"*60)
    
    if result['success']:
        print(f"✓ SUCCESS")
        print(f"\nOCR Method: {result.get('ocr_method')}")
        print(f"OCR Confidence: {result.get('ocr_confidence', 0):.1%}")
        
        print(f"\n--- RAW OCR TEXT ---")
        print(result.get('raw_text', 'No text extracted'))
        
        print(f"\n--- PARSED CONTACT DATA ---")
        contact = result.get('contact_data', {})
        
        print(f"Name:            {contact.get('name', '-')}")
        print(f"First Name:      {contact.get('first_name', '-')}")
        print(f"Last Name:       {contact.get('last_name', '-')}")
        print(f"Title:           {contact.get('title', '-')}")
        print(f"Company:         {contact.get('company', '-')}")
        print(f"Email:           {contact.get('email', '-')}")
        print(f"Phone:           {', '.join(contact.get('phone', [])) or '-'}")
        print(f"Website:         {contact.get('website', '-')}")
        print(f"LinkedIn:        {contact.get('linkedin', '-')}")
        print(f"Twitter:         {contact.get('twitter', '-')}")
        print(f"Address:         {contact.get('address', '-')}")
        print(f"\nOverall Confidence: {contact.get('confidence_score', 0):.1%}")
        
        print("\n[4/4] Evaluation:")
        conf = contact.get('confidence_score', 0)
        if conf >= 0.85:
            print("✓ EXCELLENT - Data extraction is highly accurate!")
        elif conf >= 0.70:
            print("✓ GOOD - Data extraction is acceptable")
        elif conf >= 0.50:
            print("⚠ FAIR - Some fields may need manual review")
        else:
            print("✗ POOR - Multiple fields missing or incorrect")
        
    else:
        print(f"✗ FAILED")
        print(f"Error: {result.get('error')}")
        if result.get('raw_text'):
            print(f"\nPartial OCR text:\n{result['raw_text']}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_enhanced.py <path_to_business_card_image>")
        print("\nExample:")
        print("  python test_enhanced.py syed_business_card.jpeg")
        print("  python test_enhanced.py 2ndcard.jpg")
        sys.exit(1)
    
    image_path = sys.argv[1]
    test_card(image_path)