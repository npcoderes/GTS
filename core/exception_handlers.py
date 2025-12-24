from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed


def custom_exception_handler(exc, context):
    """
    Custom exception handler to format token expiration errors.
    """
    response = exception_handler(exc, context)
    
    if response is not None:
        # Check if it's a token expiration error
        if isinstance(exc, AuthenticationFailed):
            error_detail = str(exc.detail) if hasattr(exc, 'detail') else str(exc)
            
            # Check for token expiration messages
            if 'expired' in error_detail.lower() or 'invalid token' in error_detail.lower():
                response.data = {
                    'detail': {
                        'code': 'TOKEN_EXPIRED',
                        'message': 'Token has expired.'
                    }
                }
                response.status_code = status.HTTP_401_UNAUTHORIZED
    
    return response
