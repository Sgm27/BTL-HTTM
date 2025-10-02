#!/usr/bin/env python3
"""
Test script for the Audio Dataset Management API
Demonstrates the audio-transcript pair functionality
"""

import requests
import json
from pathlib import Path

# API base URL
BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test the health check endpoint"""
    print("=== Testing Health Check ===")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_create_pair():
    """Test creating an audio-transcript pair"""
    print("=== Testing Pair Creation ===")
    
    # Prepare test data
    data = {
        "key_name": "test_001",
        "language": "vi",
        "text": "Đây là một đoạn ghi âm thử nghiệm.",
        "audio_variant": "original",
        "sample_rate": 22050,
        "channels": 1,
        "duration_seconds": 3.5
    }
    
    # You would need to provide an actual audio file for this to work
    # files = {"audio_file": ("test_audio.wav", open("test_audio.wav", "rb"), "audio/wav")}
    
    print(f"Would create pair with data: {json.dumps(data, indent=2)}")
    print("Note: Actual file upload requires a real audio file")
    print()

def test_get_pair():
    """Test getting an audio-transcript pair"""
    print("=== Testing Get Pair ===")
    
    key_name = "test_001"
    url = f"{BASE_URL}/pairs/{key_name}?variant=original&model_name="
    
    try:
        response = requests.get(url)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Pair data: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"Response: {response.text}")
    except requests.exceptions.ConnectionError:
        print("Connection failed - make sure the server is running")
    print()

def test_list_pairs():
    """Test listing audio-transcript pairs"""
    print("=== Testing List Pairs ===")
    
    url = f"{BASE_URL}/pairs/?limit=5&offset=0"
    
    try:
        response = requests.get(url)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            pairs = response.json()
            print(f"Number of pairs: {len(pairs)}")
            for pair in pairs:
                print(f"- {pair['key_name']} ({pair['variant']})")
        else:
            print(f"Response: {response.text}")
    except requests.exceptions.ConnectionError:
        print("Connection failed - make sure the server is running")
    print()

def test_generate_audio():
    """Test model audio generation"""
    print("=== Testing Model Audio Generation ===")
    
    data = {
        "transcript_key": "test_001",
        "model_name": "vietnamese_tts_v1",
        "target_sample_rate": 22050,
        "target_channels": 1
    }
    
    try:
        response = requests.post(f"{BASE_URL}/generate-audio/", 
                               json=data,
                               headers={"Content-Type": "application/json"})
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except requests.exceptions.ConnectionError:
        print("Connection failed - make sure the server is running")
    print()

def test_statistics():
    """Test getting database statistics"""
    print("=== Testing Statistics ===")
    
    try:
        response = requests.get(f"{BASE_URL}/stats/")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            stats = response.json()
            print(f"Statistics: {json.dumps(stats, indent=2)}")
        else:
            print(f"Response: {response.text}")
    except requests.exceptions.ConnectionError:
        print("Connection failed - make sure the server is running")
    print()

def main():
    """Run all tests"""
    print("Audio Dataset Management API Test Script")
    print("=" * 50)
    
    test_health_check()
    test_get_pair()
    test_list_pairs()
    test_generate_audio()
    test_statistics()
    
    print("=" * 50)
    print("Test script completed!")
    print()
    print("To test pair creation with actual file upload, you need to:")
    print("1. Have an audio file (e.g., test_audio.wav)")
    print("2. Modify the test_create_pair() function to include the file")
    print("3. Uncomment the file upload lines")

if __name__ == "__main__":
    main()