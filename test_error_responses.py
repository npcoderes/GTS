#!/usr/bin/env python
"""
Test script to verify all API error responses include 'message' field
Run this from the Django project root: python test_error_responses.py
"""

import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from core.models import Role, UserRole, Station
from logistics.models import Driver
import json

User = get_user_model()

def test_api_error_responses():
    """Test that all API endpoints return proper error messages"""
    client = Client()
    
    print("Testing API Error Response Standardization...")
    print("=" * 50)
    
    # Test cases for various error scenarios
    test_cases = [
        {
            'name': 'Login with invalid credentials',
            'method': 'POST',
            'url': '/api/auth/login/',
            'data': {'username': 'invalid@test.com', 'password': 'wrongpass'},
            'expected_status': 401,
            'should_have_message': True
        },
        {
            'name': 'Login without required fields',
            'method': 'POST', 
            'url': '/api/auth/login/',
            'data': {},
            'expected_status': 400,
            'should_have_message': True
        },
        {
            'name': 'Set MPIN without authentication',
            'method': 'POST',
            'url': '/api/auth/set-mpin/',
            'data': {'password': 'test', 'mpin': '1234'},
            'expected_status': 401,
            'should_have_message': True
        },
        {
            'name': 'Password reset with invalid user',
            'method': 'POST',
            'url': '/api/auth/request-password-reset/',
            'data': {'username': 'nonexistent@test.com'},
            'expected_status': 404,
            'should_have_message': True
        },
        {
            'name': 'Choose role with invalid role',
            'method': 'POST',
            'url': '/api/auth/choose-role/',
            'data': {'role': 'INVALID_ROLE'},
            'expected_status': 404,
            'should_have_message': True
        },
        {
            'name': 'Driver trips without authentication',
            'method': 'GET',
            'url': '/api/driver-trips/pending-offers/',
            'data': {},
            'expected_status': 401,
            'should_have_message': True
        },
        {
            'name': 'Accept trip without required data',
            'method': 'POST',
            'url': '/api/driver-trips/accept/',
            'data': {},
            'expected_status': 401,  # Will fail auth first
            'should_have_message': True
        },
        {
            'name': 'MS dashboard without station assignment',
            'method': 'GET',
            'url': '/api/ms/dashboard/',
            'data': {},
            'expected_status': 401,  # Will fail auth first
            'should_have_message': True
        }
    ]
    
    passed = 0
    failed = 0
    
    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        print(f"URL: {test_case['method']} {test_case['url']}")
        
        try:
            if test_case['method'] == 'GET':
                response = client.get(test_case['url'], test_case['data'])
            elif test_case['method'] == 'POST':
                response = client.post(
                    test_case['url'], 
                    test_case['data'], 
                    content_type='application/json'
                )
            
            # Check status code
            if response.status_code != test_case['expected_status']:
                print(f"❌ Status code mismatch: expected {test_case['expected_status']}, got {response.status_code}")
                failed += 1
                continue
            
            # Parse response
            try:
                response_data = json.loads(response.content.decode())
            except json.JSONDecodeError:
                print(f"❌ Invalid JSON response")
                failed += 1
                continue
            
            # Check for message field
            if test_case['should_have_message']:
                if 'message' in response_data:
                    print(f"✅ Response contains 'message' field: '{response_data['message']}'")
                    passed += 1
                else:
                    print(f"❌ Response missing 'message' field")
                    print(f"   Response: {response_data}")
                    failed += 1
            else:
                print(f"✅ Test passed (no message field required)")
                passed += 1
                
        except Exception as e:
            print(f"❌ Test failed with exception: {str(e)}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All API error responses now include proper 'message' fields!")
    else:
        print("⚠️  Some APIs still need message field standardization")
    
    return failed == 0

if __name__ == '__main__':
    success = test_api_error_responses()
    sys.exit(0 if success else 1)