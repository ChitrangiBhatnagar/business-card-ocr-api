#!/usr/bin/env python3
"""
Simple API Test Script - Enhanced OCR System
"""

import requests
import json
import os
from pathlib import Path

def test_api():
    print("🧪 Testing Enhanced Business Card OCR API")
    print("=" * 50)
    
    # Test status endpoint first
    try:
        print("📊 Testing Status Endpoint...")
        response = requests.get("http://127.0.0.1:5000/api/status")
        if response.status_code == 200:
            status_data = response.json()
            print(f"✅ Server Status: {status_data.get('status', 'Unknown')}")
            print(f"🧠 OCR Method: {status_data.get('ocr_method', 'Unknown')}")
            print(f"🔗 Gemini Available: {status_data.get('gemini_available', False)}")
        else:
            print(f"❌ Status check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Server not responding: {e}")
        return False
    
    print("\n" + "=" * 50)
    
    # Look for test images in common locations
    test_locations = [
        "test_images",
        "sample_images", 
        "images",
        "samples",
        "../test_images",
        "../samples"
    ]
    
    test_files = []
    
    for location in test_locations:
        if os.path.exists(location):
            for ext in ['*.jpg', '*.jpeg', '*.png']:
                test_files.extend(Path(location).glob(ext))
    
    if not test_files:
        print("⚠️ No test images found. Please add business card images to a 'test_images' folder.")
        print("Expected formats: .jpg, .jpeg, .png")
        return False
    
    print(f"🖼️ Found {len(test_files)} test images")
    
    # Test single card processing
    for i, test_file in enumerate(test_files[:3]):  # Test first 3 images
        print(f"\n📋 Testing Card {i+1}: {test_file.name}")
        print("-" * 30)
        
        try:
            with open(test_file, 'rb') as f:
                files = {'file': (test_file.name, f, 'image/jpeg')}
                response = requests.post(
                    "http://127.0.0.1:5000/api/process",
                    files=files,
                    params={'enrich': 'true'}
                )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    contact_data = result.get('data', {}).get('contact_data', {})
                    
                    print("✅ Processing successful!")
                    print(f"📝 Name: {contact_data.get('name', 'Not found')}")
                    print(f"🏢 Company: {contact_data.get('company', 'Not found')}")
                    print(f"📧 Email: {contact_data.get('email', 'Not found')}")
                    print(f"📞 Phone: {contact_data.get('phone', 'Not found')}")
                    print(f"🎯 Confidence: {contact_data.get('confidence_score', 0):.1%}")
                    
                    # Show OCR method used
                    ocr_method = result.get('data', {}).get('ocr_method', 'Unknown')
                    print(f"🤖 OCR Method: {ocr_method}")
                    
                else:
                    print(f"❌ Processing failed: {result.get('error', 'Unknown error')}")
                    
            else:
                print(f"❌ API call failed: {response.status_code}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Error processing {test_file.name}: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Test completed!")
    return True

if __name__ == "__main__":
    test_api()