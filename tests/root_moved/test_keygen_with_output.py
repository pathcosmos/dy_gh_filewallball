#!/usr/bin/env python3
"""
Test script for /keygen endpoint that displays actual returned values
"""

import requests
import json
from datetime import datetime
import time

def print_separator():
    print("=" * 80)

def test_keygen_with_output():
    """Test keygen endpoint and display actual returned values"""
    
    base_url = "http://localhost:8000"
    keygen_url = f"{base_url}/keygen"
    
    print_separator()
    print("🔬 KEYGEN ENDPOINT TEST WITH ACTUAL OUTPUT VALUES")
    print_separator()
    print()
    
    # Test 1: Valid request with correct auth header
    print("📍 TEST 1: Valid Request with Correct Authentication")
    print("-" * 60)
    
    request_data = {
        "project_name": "TestProject_Demo",
        "request_date": datetime.now().strftime("%Y%m%d")
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-Keygen-Auth": "dy2025@fileBucket"
    }
    
    print("📤 Request Details:")
    print(f"   URL: POST {keygen_url}")
    print(f"   Headers: {json.dumps(headers, indent=12)}")
    print(f"   Body: {json.dumps(request_data, indent=12)}")
    print()
    
    try:
        response = requests.post(keygen_url, headers=headers, json=request_data)
        
        print("📥 Response Details:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Status: {'✅ SUCCESS' if response.status_code == 200 else '❌ FAILED'}")
        print()
        
        if response.status_code == 200:
            response_data = response.json()
            print("📊 Actual Returned Values:")
            print(f"   project_id: {response_data.get('project_id')}")
            print(f"   project_name: {response_data.get('project_name')}")
            print(f"   project_key: {response_data.get('project_key')}")
            print(f"   request_date: {response_data.get('request_date')}")
            print(f"   message: {response_data.get('message')}")
            print()
            print("🔐 Full Project Key (Base64):")
            print(f"   {response_data.get('project_key')}")
            print()
            print("📋 Complete JSON Response:")
            print(json.dumps(response_data, indent=4))
            
            # Store the key for later reference
            valid_key = response_data.get('project_key')
            valid_project_id = response_data.get('project_id')
        else:
            print("❌ Error Response:")
            print(json.dumps(response.json(), indent=4))
    
    except requests.exceptions.ConnectionError:
        print("🔌 ERROR: Server not running!")
        print("   Please start the server with:")
        print("   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        return
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return
    
    print()
    print_separator()
    
    # Test 2: Different project names to show unique key generation
    print("📍 TEST 2: Multiple Projects - Unique Key Generation")
    print("-" * 60)
    
    test_projects = [
        {"name": "MyApp_Production", "date": "20250810"},
        {"name": "TestEnvironment", "date": "20250809"},
        {"name": "DevProject_2025", "date": "20250808"},
        {"name": "한글프로젝트", "date": "20250810"},  # Korean characters
        {"name": "Project-with-dashes", "date": "20250810"}
    ]
    
    generated_keys = []
    
    for i, project in enumerate(test_projects, 1):
        print(f"\n🔹 Project {i}: {project['name']}")
        
        request_data = {
            "project_name": project["name"],
            "request_date": project["date"]
        }
        
        try:
            response = requests.post(keygen_url, headers=headers, json=request_data)
            
            if response.status_code == 200:
                response_data = response.json()
                generated_keys.append({
                    "project_name": response_data.get('project_name'),
                    "project_id": response_data.get('project_id'),
                    "project_key": response_data.get('project_key'),
                    "request_date": response_data.get('request_date')
                })
                
                print(f"   ✅ Success!")
                print(f"   Project ID: {response_data.get('project_id')}")
                print(f"   Project Key: {response_data.get('project_key')}")
                print(f"   Key Length: {len(response_data.get('project_key', ''))} characters")
            else:
                print(f"   ❌ Failed: {response.json().get('detail')}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Small delay between requests
        time.sleep(0.1)
    
    print()
    print_separator()
    
    # Test 3: Invalid authentication to show error response
    print("📍 TEST 3: Invalid Authentication - Error Response")
    print("-" * 60)
    
    invalid_headers = {
        "Content-Type": "application/json",
        "X-Keygen-Auth": "wrong-auth-value"
    }
    
    request_data = {
        "project_name": "UnauthorizedProject",
        "request_date": datetime.now().strftime("%Y%m%d")
    }
    
    print("📤 Request with Invalid Auth:")
    print(f"   Headers: {json.dumps(invalid_headers, indent=12)}")
    print()
    
    try:
        response = requests.post(keygen_url, headers=invalid_headers, json=request_data)
        
        print("📥 Error Response:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Status: {'✅' if response.status_code == 401 else '❌'} Expected 401")
        print()
        print("📋 Error Details:")
        error_data = response.json()
        print(json.dumps(error_data, indent=4))
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print()
    print_separator()
    
    # Summary of all generated keys
    if generated_keys:
        print("📊 SUMMARY: All Generated Project Keys")
        print("-" * 60)
        print()
        
        for i, key_info in enumerate(generated_keys, 1):
            print(f"Project {i}:")
            print(f"  Name: {key_info['project_name']}")
            print(f"  ID: {key_info['project_id']}")
            print(f"  Date: {key_info['request_date']}")
            print(f"  Key: {key_info['project_key']}")
            print()
        
        print(f"Total Projects Created: {len(generated_keys)}")
        print(f"All Keys Unique: {len(set(k['project_key'] for k in generated_keys)) == len(generated_keys)}")
    
    print()
    print_separator()
    print("✅ Test completed successfully!")
    print_separator()

def test_curl_equivalent():
    """Show equivalent cURL commands"""
    print()
    print("🔧 EQUIVALENT CURL COMMANDS")
    print("=" * 80)
    print()
    
    today = datetime.now().strftime("%Y%m%d")
    
    print("1️⃣ Valid Request:")
    print('curl -X POST http://localhost:8000/keygen \\')
    print('     -H "Content-Type: application/json" \\')
    print('     -H "X-Keygen-Auth: dy2025@fileBucket" \\')
    print(f'     -d \'{{"project_name": "TestProject", "request_date": "{today}"}}\'')
    print()
    
    print("2️⃣ Invalid Auth (Expected 401):")
    print('curl -X POST http://localhost:8000/keygen \\')
    print('     -H "Content-Type: application/json" \\')
    print('     -H "X-Keygen-Auth: wrong-auth" \\')
    print(f'     -d \'{{"project_name": "TestProject", "request_date": "{today}"}}\'')
    print()
    
    print("3️⃣ Pretty Print JSON Response:")
    print('curl -X POST http://localhost:8000/keygen \\')
    print('     -H "Content-Type: application/json" \\')
    print('     -H "X-Keygen-Auth: dy2025@fileBucket" \\')
    print(f'     -d \'{{"project_name": "TestProject", "request_date": "{today}"}}\' | python -m json.tool')
    print()

if __name__ == "__main__":
    print("🚀 Starting /keygen Endpoint Test with Actual Output Values")
    print()
    
    # Check if server is running
    try:
        health_check = requests.get("http://localhost:8000/health", timeout=2)
        if health_check.status_code == 200:
            print("✅ Server is running")
            print()
        else:
            print("⚠️ Server responded but may have issues")
            print()
    except:
        print("❌ Server is not running!")
        print("Please start it with:")
        print("uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        print()
        exit(1)
    
    # Run main test
    test_keygen_with_output()
    
    # Show cURL examples
    test_curl_equivalent()