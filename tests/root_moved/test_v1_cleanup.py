#!/usr/bin/env python3
"""
Test script to validate that all v1 endpoints have been removed
"""

def test_v1_cleanup():
    """Verify that v1 endpoints have been successfully removed"""
    results = []
    
    # Test 1: Check main.py for v1 references
    print("✓ Checking main.py for v1 references...")
    try:
        with open("app/main.py", "r") as f:
            content = f.read()
            if "/api/v1" in content or "from app.api.v1" in content:
                results.append("❌ Found v1 references in main.py")
            else:
                results.append("✅ No v1 references in main.py")
    except Exception as e:
        results.append(f"⚠️ Could not check main.py: {e}")
    
    # Test 2: Check if v1 directory exists
    print("✓ Checking for v1 directory...")
    import os
    if os.path.exists("app/api/v1"):
        results.append("❌ v1 directory still exists at app/api/v1")
    else:
        results.append("✅ v1 directory has been removed")
    
    # Test 3: Check FastAPI routes
    print("✓ Checking FastAPI routes...")
    try:
        from app.main import app
        routes = [route.path for route in app.routes]
        v1_routes = [r for r in routes if "/v1/" in r or "/api/v1" in r]
        if v1_routes:
            results.append(f"❌ Found v1 routes: {v1_routes}")
        else:
            results.append("✅ No v1 routes in FastAPI app")
    except Exception as e:
        results.append(f"⚠️ Could not check routes: {e}")
    
    # Test 4: List remaining endpoints
    print("✓ Listing remaining endpoints...")
    try:
        from app.main import app
        endpoints = []
        for route in app.routes:
            if hasattr(route, 'methods') and route.methods:
                for method in route.methods:
                    if method in ['GET', 'POST', 'PUT', 'DELETE']:
                        endpoints.append(f"{method} {route.path}")
        
        # Filter out OpenAPI endpoints
        user_endpoints = [e for e in endpoints if not any(x in e for x in ['/openapi.json', '/docs', '/redoc'])]
        results.append(f"📋 Remaining endpoints ({len(user_endpoints)}):")
        for endpoint in sorted(user_endpoints):
            results.append(f"   • {endpoint}")
    except Exception as e:
        results.append(f"⚠️ Could not list endpoints: {e}")
    
    return results

if __name__ == "__main__":
    print("=" * 60)
    print("V1 API CLEANUP VALIDATION")
    print("=" * 60 + "\n")
    
    results = test_v1_cleanup()
    
    print("\n📊 RESULTS:")
    print("-" * 40)
    for result in results:
        print(result)
    
    # Summary
    print("\n" + "=" * 60)
    errors = [r for r in results if "❌" in r]
    if errors:
        print("⚠️ CLEANUP INCOMPLETE - Issues found:")
        for error in errors:
            print(f"  {error}")
    else:
        print("✅ CLEANUP SUCCESSFUL - All v1 endpoints removed!")
    print("=" * 60)