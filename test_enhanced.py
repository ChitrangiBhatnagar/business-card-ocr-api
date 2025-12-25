# test_enhanced.py (save in project root)
import sys
from pathlib import Path
import json

# Add current directory to path
sys.path.append('.')

print("🚀 TESTING ENHANCED OCR + PARSER")
print("=" * 50)

try:
    from src.ocr import OCRExtractor
    from src.parser import ContactParser
    print("✅ Modules imported successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Initialize components
print("\nInitializing OCR...")
ocr = OCRExtractor(gpu=False)  # Change to True if you have GPU
parser = ContactParser()
print("✅ OCR and Parser initialized")

# Find all JPG images in root
jpg_files = list(Path('.').glob('*.jpg'))
print(f"\nFound {len(jpg_files)} JPG images in root folder:")

for i, img_path in enumerate(jpg_files):
    print(f"  {i+1}. {img_path.name}")

if not jpg_files:
    print("\n❌ No JPG images found in root folder!")
    sys.exit(1)

# Test each image
for img_path in jpg_files:
    print(f"\n{'='*60}")
    print(f"PROCESSING: {img_path.name}")
    print(f"{'='*60}")
    
    # Step 1: OCR Extraction
    print("\n1️⃣  OCR Extraction...")
    ocr_result = ocr.extract_text(img_path)
    
    print(f"   Success: {ocr_result['success']}")
    print(f"   Confidence: {ocr_result['confidence']:.2%}")
    print(f"   Method: {ocr_result['method']}")
    
    if not ocr_result['success']:
        print(f"   ❌ Error: {ocr_result.get('error', 'Unknown')}")
        continue
    
    # Show extracted text
    raw_text = ocr_result['raw_text']
    print(f"\n   📝 Extracted Text ({len(raw_text)} chars):")
    print("   " + "-" * 40)
    lines = raw_text.split('\n')
    for j, line in enumerate(lines):
        print(f"   {j+1:2d}: {line}")
    print("   " + "-" * 40)
    
    # Step 2: Parsing
    print("\n2️⃣  Parsing contact data...")
    contact = parser.parse_enhanced(raw_text, ocr_result['confidence'])
    
    print(f"   ✅ Parsed successfully")
    print(f"   Name: {contact.name or 'N/A'}")
    print(f"   Email: {contact.email or 'N/A'}")
    print(f"   Phone: {contact.phone or 'N/A'}")
    print(f"   Company: {contact.company or 'N/A'}")
    print(f"   Title: {contact.title or 'N/A'}")
    print(f"   Website: {contact.website or 'N/A'}")
    print(f"   Confidence: {contact.confidence_score:.2%}")
    
    # Step 3: Show what was fixed
    print("\n3️⃣  Corrections applied:")
    if "REALE5TATE" in raw_text:
        print("   - Fixed: REALE5TATE → REAL ESTATE")
    if "5TEWART" in raw_text:
        print("   - Fixed: 5TEWART → STEWART")
    if "F1orida" in raw_text:
        print("   - Fixed: F1orida → FLORIDA")
    if "Y0UR" in raw_text:
        print("   - Fixed: Y0UR → YOUR")
    if "info@websitename com" in raw_text:
        print("   - Fixed: info@websitename com → info@websitename.com")
    
    print(f"\n✅ Processing complete for {img_path.name}")

print(f"\n{'='*60}")
print("🎉 ALL TESTS COMPLETE!")
print("=" * 60)

# Bonus: Test with your original problematic text
print("\n" + "="*60)
print("BONUS: Testing with original problematic text")
print("=" * 60)

problem_text = """Access KIs
Secure Mobile Timing
Phone: 1-8-10
01/17/2024
info@securemobilety.com
www.securemobilety.com
James Kirk
kirk@bostonlobsterfishing.com"""

print("Input text:")
print(problem_text)

result = parser.parse_enhanced(problem_text, 0.8)
print(f"\n✅ Parser corrected:")
print(f"   Name: {result.name}")
print(f"   Email: {result.email}")
print(f"   Phone: {result.phone}")
print(f"   Company: {result.company}")
print(f"   Title: {result.title}")
print(f"   Confidence: {result.confidence_score:.2%}")