"""
Temporary testing middleware to force API errors for frontend testing.
This will make all APIs (except login) return standardized error responses.
"""
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status


class ForceAPIErrorsMiddleware:
    """
    Temporary middleware to force all APIs to return errors for testing.
    Excludes login API so users can still authenticate.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Only activate in DEBUG mode for safety
        if not getattr(settings, 'DEBUG', False):
            return self.get_response(request)
            
        # Skip if not an API request
        if not request.path.startswith('/api/'):
            return self.get_response(request)
            
        # Allow login endpoints to work normally
        login_paths = [
            '/api/auth/login/',
            '/api/auth/request-password-reset/',
            '/api/auth/verify-reset-otp/',
            '/api/auth/confirm-password-reset/',
            '/api/auth/choose-role/',
            '/api/notifications/register-token'
        ]
        
        if any(request.path.startswith(path) for path in login_paths):
            return self.get_response(request)
            
        # Force error response for all other APIs
        error_responses = {
            'GET': {
                'message': 'Test error: GET request failed for testing error handling',
                'error_type': 'VALIDATION_ERROR',
                'endpoint': request.path
            },
            'POST': {
                'message': 'Test error: POST request failed for testing error handling', 
                'error_type': 'BUSINESS_LOGIC_ERROR',
                'endpoint': request.path
            },
            'PUT': {
                'message': 'Test error: PUT request failed for testing error handling',
                'error_type': 'PERMISSION_ERROR', 
                'endpoint': request.path
            },
            'DELETE': {
                'message': 'Test error: DELETE request failed for testing error handling',
                'error_type': 'NOT_FOUND_ERROR',
                'endpoint': request.path
            }
        }
        
        method = request.method
        error_data = error_responses.get(method, {
            'message': f'Test error: {method} request failed for testing error handling',
            'error_type': 'GENERIC_ERROR',
            'endpoint': request.path
        })
        
        # Return different status codes based on method for variety
        status_codes = {
            'GET': status.HTTP_404_NOT_FOUND,
            'POST': status.HTTP_400_BAD_REQUEST,
            'PUT': status.HTTP_403_FORBIDDEN,
            'DELETE': status.HTTP_404_NOT_FOUND
        }
        
        status_code = status_codes.get(method, status.HTTP_400_BAD_REQUEST)
        
        return Response(error_data, status=status_code)