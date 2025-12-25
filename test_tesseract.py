"""
Test if Tesseract works from Python (no PATH needed)
"""

print("Testing Tesseract from Python...\n")

# Step 1: Import pytesseract
print("[1/4] Importing pytesseract...")
try:
    import pytesseract
    print("✓ pytesseract imported successfully")
except ImportError:
    print("✗ pytesseract not found")
    print("   Fix: pip install pytesseract")
    exit(1)

# Step 2: Set Tesseract path explicitly
print("\n[2/4] Setting Tesseract path...")
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
print(f"✓ Path set to: {pytesseract.pytesseract.tesseract_cmd}")

# Step 3: Check if file exists
print("\n[3/4] Checking if Tesseract executable exists...")
import os
if os.path.exists(pytesseract.pytesseract.tesseract_cmd):
    print("✓ Tesseract.exe found!")
else:
    print("✗ Tesseract.exe NOT found at this path")
    print("\n   Checking alternative locations...")
    
    # Check common alternative paths
    alternative_paths = [
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        r'C:\Users\moham\AppData\Local\Programs\Tesseract-OCR\tesseract.exe',
        r'C:\Tesseract-OCR\tesseract.exe'
    ]
    
    for path in alternative_paths:
        if os.path.exists(path):
            print(f"   ✓ Found at: {path}")
            pytesseract.pytesseract.tesseract_cmd = path
            break
    else:
        print("   ✗ Could not find Tesseract in common locations")
        print("\n   Please find tesseract.exe location:")
        print("   1. Open File Explorer")
        print("   2. Search for 'tesseract.exe'")
        print("   3. Copy the full path")
        exit(1)

# Step 4: Test Tesseract
print("\n[4/4] Testing Tesseract...")
try:
    version = pytesseract.get_tesseract_version()
    print(f"✓ SUCCESS! Tesseract version: {version}")
    print("\n" + "="*60)
    print("🎉 Tesseract is working perfectly in Python!")
    print("="*60)
    print("\nYou can now run: python test_enhanced.py your_card.jpeg")
except Exception as e:
    print(f"✗ ERROR: {e}")
    print("\nTroubleshooting:")
    print("1. Make sure Tesseract is installed")
    print("2. Check the path is correct")