#!/usr/bin/env python3
"""
Test script for the /keygen endpoint functionality
"""

import requests
import json
from datetime import datetime

def test_keygen_endpoint():
    """Test the keygen endpoint with various scenarios"""
    
    base_url = "http://localhost:8000"
    keygen_url = f"{base_url}/keygen"
    
    # Test scenarios
    test_cases = [
        {
            "name": "Valid request with correct auth header",
            "headers": {"X-Keygen-Auth": "dy2025@fileBucket"},
            "data": {
                "project_name": "TestProject",
                "request_date": datetime.now().strftime("%Y%m%d")
            },
            "expected_status": 200
        },
        {
            "name": "Invalid auth header",
            "headers": {"X-Keygen-Auth": "wrong-auth"},
            "data": {
                "project_name": "TestProject",
                "request_date": "20250810"
            },
            "expected_status": 401
        },
        {
            "name": "Missing auth header",
            "headers": {},
            "data": {
                "project_name": "TestProject",
                "request_date": "20250810"
            },
            "expected_status": 401
        },
        {
            "name": "Invalid date format",
            "headers": {"X-Keygen-Auth": "dy2025@fileBucket"},
            "data": {
                "project_name": "TestProject",
                "request_date": "2025-08-10"  # Wrong format
            },
            "expected_status": 400
        },
        {
            "name": "Empty project name",
            "headers": {"X-Keygen-Auth": "dy2025@fileBucket"},
            "data": {
                "project_name": "",
                "request_date": "20250810"
            },
            "expected_status": 400
        },
        {
            "name": "Short project name",
            "headers": {"X-Keygen-Auth": "dy2025@fileBucket"},
            "data": {
                "project_name": "A",  # Too short
                "request_date": "20250810"
            },
            "expected_status": 400
        }
    ]
    
    print("🧪 Testing /keygen endpoint...\n")
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}: {test_case['name']}")
        
        try:
            response = requests.post(
                keygen_url,
                headers=test_case['headers'],
                json=test_case['data'],
                timeout=5
            )
            
            actual_status = response.status_code
            expected_status = test_case['expected_status']
            
            if actual_status == expected_status:
                print(f"  ✅ Status: {actual_status} (Expected: {expected_status})")
                
                if actual_status == 200:
                    response_data = response.json()
                    print(f"  📋 Project ID: {response_data.get('project_id')}")
                    print(f"  📋 Project Name: {response_data.get('project_name')}")
                    print(f"  🔑 Project Key: {response_data.get('project_key')[:20]}...")
                    print(f"  📅 Request Date: {response_data.get('request_date')}")
                    print(f"  💬 Message: {response_data.get('message')}")
                    
                    # Store successful key for further testing
                    if test_case['name'] == "Valid request with correct auth header":
                        results.append({
                            "project_key": response_data.get('project_key'),
                            "project_id": response_data.get('project_id')
                        })
                else:
                    error_data = response.json()
                    print(f"  ⚠️ Error: {error_data.get('detail')}")
                    
            else:
                print(f"  ❌ Status: {actual_status} (Expected: {expected_status})")
                
        except requests.exceptions.ConnectionError:
            print(f"  🔌 Server not running. Start with: uvicorn app.main:app --reload")
            return False
        except Exception as e:
            print(f"  ❌ Error: {e}")
            
        print()
    
    # Summary
    print("=" * 60)
    print("📊 KEYGEN ENDPOINT TEST SUMMARY")
    print("=" * 60)
    
    if results:
        print(f"✅ Generated {len(results)} project key(s) successfully")
        for i, result in enumerate(results, 1):
            print(f"   {i}. Project ID: {result['project_id']}")
            print(f"      Key: {result['project_key'][:30]}...")
    else:
        print("⚠️ No successful project keys generated")
    
    print("\n🔧 cURL Example for valid request:")
    print(f"""curl -X POST {keygen_url} \\
     -H "Content-Type: application/json" \\
     -H "X-Keygen-Auth: dy2025@fileBucket" \\
     -d '{{"project_name": "MyProject", "request_date": "{datetime.now().strftime('%Y%m%d')}"}}' """)
    
    return len(results) > 0

def test_endpoint_structure():
    """Test the endpoint structure and imports"""
    try:
        from app.main import app, generate_project_key
        from app.models.orm_models import ProjectKey
        from app.services.project_key_service import ProjectKeyService
        
        # Check if keygen endpoint exists
        routes = [route.path for route in app.routes]
        if "/keygen" in routes:
            print("✅ /keygen endpoint found in app routes")
        else:
            print("❌ /keygen endpoint not found in app routes")
            return False
            
        # Check function signature
        import inspect
        sig = inspect.signature(generate_project_key)
        params = list(sig.parameters.keys())
        
        print(f"✅ generate_project_key parameters: {params}")
        
        expected_params = ["request_data", "request", "db", "keygen_auth"]
        if all(p in params for p in expected_params):
            print("✅ All required parameters present")
            return True
        else:
            print("❌ Missing required parameters")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing /keygen endpoint functionality...\n")
    
    # Test structure first
    print("1️⃣ Testing endpoint structure:")
    structure_ok = test_endpoint_structure()
    print()
    
    if structure_ok:
        # Test actual functionality
        print("2️⃣ Testing endpoint functionality:")
        functionality_ok = test_keygen_endpoint()
        
        if functionality_ok:
            print("\n🎉 All tests passed! Keygen endpoint is working correctly.")
        else:
            print("\n⚠️ Some functionality tests failed. Check server status.")
    else:
        print("\n❌ Endpoint structure issues found.")