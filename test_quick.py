#!/usr/bin/env python3
"""
Quick test - Create a dummy uploaded file and process it
"""
from pathlib import Path
import json
from src.pipeline import CardResearchPipeline

# Make sure uploads folder exists
uploads_folder = Path("uploads")
uploads_folder.mkdir(exist_ok=True)

# Try to process the most recent image in outputs if it exists
test_images = list(Path(".").glob("**/*.jpg")) + list(Path(".").glob("**/*.png"))
test_images = [f for f in test_images if "uploads" not in str(f)]  # Exclude uploads folder

if test_images:
    test_image = test_images[0]
    print(f"Processing: {test_image}")
    
    pipeline = CardResearchPipeline(output_folder="./outputs")
    result = pipeline.process_image(Path(test_image), enrich=False)
    
    print("\nRESULT KEYS:", list(result.keys()))
    if "contact_data" in result:
        print("Contact Data Keys:", list(result["contact_data"].keys()))
        print("\nContact Data:")
        print(json.dumps(result["contact_data"], indent=2))
    else:
        print("WARNING: contact_data not in result!")
        print("Full result:")
        print(json.dumps(result, indent=2, default=str))
else:
    print("No test images found!")
