"""Debug Gemini extraction"""
from dotenv import load_dotenv
load_dotenv()

from pathlib import Path
from src.vlm_ocr import GeminiOCR

# Initialize with API key loaded
ocr = GeminiOCR()
print(f'Gemini available: {ocr.is_available()}')
print(f'Has client: {hasattr(ocr, "client") and ocr.client is not None}')
print(f'Uses new API: {getattr(ocr, "use_new_api", False)}')

print("\n=== Extracting from image ===")
result = ocr.extract(Path('syed_business_card.jpeg'))

print(f'Success: {result.success}')
print(f'Error: {result.error}')
print(f'Name: {result.name}')
print(f'Company: {result.company}')
print(f'Email: {result.email}')
print(f'Phone: {result.phone}')
print(f'Raw Text: {result.raw_text[:200] if result.raw_text else "None"}...')
