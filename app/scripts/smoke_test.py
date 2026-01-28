#!/usr/bin/env python3
"""
Smoke test script for deployment validation
"""

import requests
import argparse
import sys
from typing import Dict, List

def test_endpoint(url: str, endpoint: str, expected_status: int = 200) -> bool:
    """Test a single endpoint"""
    full_url = f"{url.rstrip('/')}/{endpoint.lstrip('/')}"
    try:
        response = requests.get(full_url, timeout=10)
        if response.status_code == expected_status:
            print(f"✓ {endpoint}: {response.status_code}")
            return True
        else:
            print(f"✗ {endpoint}: Expected {expected_status}, got {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ {endpoint}: Error - {str(e)}")
        return False

def test_api_endpoint(url: str, endpoint: str, method: str = "GET", 
                     data: Dict = None, expected_status: int = 200) -> bool:
    """Test API endpoint"""
    full_url = f"{url.rstrip('/')}/{endpoint.lstrip('/')}"
    try:
        if method == "GET":
            response = requests.get(full_url, timeout=10)
        elif method == "POST":
            response = requests.post(full_url, json=data, timeout=10)
        else:
            print(f"✗ {endpoint}: Unsupported method {method}")
            return False
        
        if response.status_code == expected_status:
            print(f"✓ {endpoint} [{method}]: {response.status_code}")
            return True
        else:
            print(f"✗ {endpoint} [{method}]: Expected {expected_status}, got {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"✗ {endpoint} [{method}]: Error - {str(e)}")
        return False

def run_smoke_tests(base_url: str) -> bool:
    """Run comprehensive smoke tests"""
    print(f"Running smoke tests for: {base_url}")
    print("=" * 60)
    
    tests = [
        # Basic connectivity
        ("/health", "GET", None, 200),
        ("/", "GET", None, 200),
        ("/docs", "GET", None, 200),
        
        # API endpoints
        ("/api/v1/students", "GET", None, 200),
        ("/api/v1/universities", "GET", None, 200),
        
        # Email endpoints (should work but may require auth)
        ("/api/v1/email/templates", "GET", None, 200),
        ("/api/v1/email/statistics", "GET", None, 200),
    ]
    
    passed = 0
    failed = 0
    
    for endpoint, method, data, expected_status in tests:
        success = test_api_endpoint(base_url, endpoint, method, data, expected_status)
        if success:
            passed += 1
        else:
            failed += 1
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    
    return failed == 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run smoke tests for deployment validation")
    parser.add_argument("--url", required=True, help="Base URL to test")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds")
    
    args = parser.parse_args()
    
    success = run_smoke_tests(args.url)
    
    if success:
        print("✅ All smoke tests passed!")
        sys.exit(0)
    else:
        print("❌ Smoke tests failed!")
        sys.exit(1)