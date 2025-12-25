"""Quick test for Gemini response"""
from dotenv import load_dotenv
load_dotenv()

import os
from pathlib import Path
from google import genai
from google.genai import types

# Initialize client
client = genai.Client(api_key=os.getenv('GOOGLE_API_KEY'))

# Load image
with open('syed_business_card.jpeg', 'rb') as f:
    image_bytes = f.read()

# Call Gemini
prompt = """Analyze this business card image and extract ALL contact information.

Return a JSON object with these exact fields (use null if not found):
{
    "name": "Full name of the person",
    "title": "Job title/position",
    "company": "Company/organization name",
    "email": "Email address",
    "phone": ["Array of phone numbers"],
    "website": "Website URL",
    "address": "Full address",
    "linkedin": "LinkedIn URL or handle",
    "raw_text": "All visible text on the card"
}

Rules:
- Extract EXACTLY what you see
- Return ONLY valid JSON, no markdown"""

response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=[
        types.Content(
            parts=[
                types.Part.from_text(text=prompt),
                types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg')
            ]
        )
    ]
)

print('=== RAW RESPONSE ===')
print(response.text)
print()
print('=== RESPONSE TYPE ===')
print(type(response.text))
