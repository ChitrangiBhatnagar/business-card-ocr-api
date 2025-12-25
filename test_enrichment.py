"""
Test script for enhanced OCR pipeline with Company Enrichment and Field Confidence
"""

from dotenv import load_dotenv
load_dotenv()

from src.pipeline import CardResearchPipeline
from pathlib import Path
import sys
import json

def test_card(image_path: str):
    """Test processing a single card with all enhancements."""
    
    print("="*60)
    print("TESTING ENHANCED OCR PIPELINE")
    print("With Company Enrichment & Field Confidence")
    print("="*60)
    
    # Initialize pipeline
    print("\n[1/5] Initializing pipeline...")
    pipeline = CardResearchPipeline(
        output_folder="./outputs",
        ocr_languages=['en'],
        ocr_gpu=False
    )
    print("✓ Pipeline initialized")
    print(f"  Gemini Fallback: {pipeline.gemini_ocr is not None}")
    
    # Check if file exists
    image_file = Path(image_path)
    if not image_file.exists():
        print(f"\n✗ Error: Image not found: {image_path}")
        return
    
    # Process image
    print(f"\n[2/5] Processing image: {image_file.name}")
    result = pipeline.process_image(image_file, enrich=True, force_gemini=False)
    
    # Display results
    print(f"\n[3/5] Processing complete!")
    print("-"*60)
    
    if result['success']:
        print(f"✓ SUCCESS")
        print(f"\nOCR Method: {result.get('ocr_method')}")
        print(f"OCR Confidence: {result.get('ocr_confidence', 0):.1%}")
        
        print(f"\n--- CONTACT DATA ---")
        contact = result.get('contact_data', {})
        
        print(f"  Name:       {contact.get('name', '-')}")
        print(f"  Title:      {contact.get('title', '-')}")
        print(f"  Company:    {contact.get('company', '-')}")
        print(f"  Email:      {contact.get('email', '-')}")
        print(f"  Phone:      {', '.join(contact.get('phone', [])) or '-'}")
        print(f"  Website:    {contact.get('website', '-')}")
        print(f"  LinkedIn:   {contact.get('linkedin', '-')}")
        print(f"  Address:    {contact.get('address', '-')}")
        
        # NEW: Show enriched data
        if contact.get('industry'):
            print(f"  Industry:   {contact.get('industry')}")
        if contact.get('company_logo'):
            print(f"  Logo:       {contact.get('company_logo')}")
        
        # NEW: Field Confidence
        print(f"\n[4/5] --- FIELD CONFIDENCE ---")
        fc = result.get('field_confidence', {})
        if fc:
            print(f"  Name:       {fc.get('name', 0)*100:.0f}%")
            print(f"  Email:      {fc.get('email', 0)*100:.0f}%")
            print(f"  Phone:      {fc.get('phone', 0)*100:.0f}%")
            print(f"  Company:    {fc.get('company', 0)*100:.0f}%")
            print(f"  Title:      {fc.get('title', 0)*100:.0f}%")
            print(f"  Website:    {fc.get('website', 0)*100:.0f}%")
            print(f"  Overall:    {fc.get('overall', 0)*100:.0f}%")
            
            quality = fc.get('quality', {})
            if quality:
                print(f"\n  Quality Indicators:")
                print(f"    Name:   {quality.get('name', 'unknown')}")
                print(f"    Email:  {quality.get('email', 'unknown')}")
                print(f"    Phone:  {quality.get('phone', 'unknown')}")
        
        # NEW: Company Enrichment
        print(f"\n[5/5] --- COMPANY ENRICHMENT ---")
        ce = result.get('company_enrichment', {})
        if ce:
            print(f"  Domain:     {ce.get('domain') or 'Not detected'}")
            print(f"  Logo URL:   {ce.get('logo_url') or 'Not found'}")
            print(f"  Industry:   {ce.get('industry') or 'Not detected'}")
            print(f"  LinkedIn:   {ce.get('linkedin_url') or 'Not available'}")
            print(f"  Sources:    {', '.join(ce.get('enrichment_sources', [])) or 'None'}")
        
        print("\n" + "-"*60)
        overall = fc.get('overall', 0) if fc else contact.get('confidence_score', 0)
        if overall >= 0.85:
            print("✓ EXCELLENT - High confidence extraction!")
        elif overall >= 0.70:
            print("✓ GOOD - Reliable data extraction")
        elif overall >= 0.50:
            print("⚠ FAIR - Some fields may need review")
        else:
            print("✗ POOR - Manual review recommended")
        
    else:
        print(f"✗ FAILED")
        print(f"Error: {result.get('error')}")
    
    print("\n" + "="*60)
    
    # Optional: Print full JSON
    if "--json" in sys.argv:
        print("\nFull JSON Response:")
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_enrichment.py <path_to_business_card_image> [--json]")
        print("\nExample:")
        print("  python test_enrichment.py syed_business_card.jpeg")
        print("  python test_enrichment.py 2ndcard.jpg --json")
        sys.exit(1)
    
    image_path = sys.argv[1]
    test_card(image_path)
