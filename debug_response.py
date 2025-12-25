#!/usr/bin/env python3
"""Debug script to check API response structure"""

import json
from pathlib import Path
from src.pipeline import CardResearchPipeline

# Create pipeline
pipeline = CardResearchPipeline(output_folder="./outputs")

# Process image
image_path = Path("uploads/businesscard.jpg")
if image_path.exists():
    result = pipeline.process_image(image_path, enrich=False)
    
    print("=" * 60)
    print("PIPELINE RESPONSE STRUCTURE")
    print("=" * 60)
    print(json.dumps(result, indent=2, default=str))
    print("\n" + "=" * 60)
    print("CHECKING RESPONSE FOR API")
    print("=" * 60)
    
    # Simulate what the API returns
    api_response = {
        "success": True,
        "data": result
    }
    
    print(json.dumps(api_response, indent=2, default=str))
    
    # Check if contact_data exists
    if "contact_data" in result:
        print("\n[OK] contact_data found in result")
        print(f"  Keys: {list(result['contact_data'].keys())}")
    else:
        print("\n[ERROR] contact_data NOT found in result!")
        print(f"  Available keys: {list(result.keys())}")
else:
    print(f"[ERROR] Image not found: {image_path}")
