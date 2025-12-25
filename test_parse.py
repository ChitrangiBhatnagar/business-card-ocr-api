"""Test JSON parsing"""
import json
from src.vlm_ocr import GeminiOCR

# Test the parse method directly
ocr = GeminiOCR()

test_response = '''{
    "name": "SYED RIZVI",
    "title": "President",
    "company": "INTERNATIONAL Real Estate Management Corporation",
    "email": "remco@aol.com",
    "phone": ["630.528.9915", "630.582.9916"],
    "website": null,
    "address": "2005 Bloomingdale Road",
    "linkedin": null,
    "raw_text": "Test"
}'''

print("=== TEST 1: Direct parse ===")
result = ocr._parse_response(test_response)
print('Parse result:', result)
print('Type:', type(result))
print('Empty?', not result)

print("\n=== TEST 2: Parse with extra spaces ===")
test_with_spaces = """
{
    "name": "SYED RIZVI",
    "title": "President"
}
"""
result2 = ocr._parse_response(test_with_spaces)
print('Parse result:', result2)

print("\n=== TEST 3: Parse actual Gemini response ===")
# Simulate what Gemini returns
actual = '{\n    "name": "SYED RIZVI",\n    "title": "President",\n    "company": "INTERNATIONAL Real Estate Management Corporation",\n    "email": "remco@aol.com",\n    "phone": ["630.528.9915", "630.582.9916", "630.546.5419"],\n    "website": null,\n    "address": "2005 Bloomingdale Road, Suite A Glendale Heights, IL 60139",\n    "linkedin": null,\n    "raw_text": "SYED RIZVI\\nPresident"\n}'
result3 = ocr._parse_response(actual)
print('Parse result:', result3)
print('Name:', result3.get('name') if result3 else 'FAILED')
