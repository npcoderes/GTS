"""
Standardized error response utility for consistent API error handling
"""
from rest_framework.response import Response
from rest_framework import status


def error_response(message, status_code=status.HTTP_400_BAD_REQUEST, extra_data=None):
    """
    Create a standardized error response with message field.
    
    Args:
        message (str): Error message to display to user
        status_code (int): HTTP status code (default: 400)
        extra_data (dict): Additional data to include in response
    
    Returns:
        Response: DRF Response object with standardized error format
    """
    response_data = {'message': message}
    
    if extra_data:
        response_data.update(extra_data)
    
    return Response(response_data, status=status_code)


def validation_error_response(message, errors=None):
    """
    Create a validation error response (400 Bad Request).
    
    Args:
        message (str): Main error message
        errors (dict): Field-specific validation errors
    
    Returns:
        Response: DRF Response object with validation error format
    """
    response_data = {'message': message}
    
    if errors:
        response_data['errors'] = errors
    
    return Response(response_data, status=status.HTTP_400_BAD_REQUEST)


def not_found_response(message="Resource not found"):
    """
    Create a not found error response (404 Not Found).
    
    Args:
        message (str): Error message
    
    Returns:
        Response: DRF Response object with 404 error
    """
    return Response({'message': message}, status=status.HTTP_404_NOT_FOUND)


def unauthorized_response(message="Authentication required"):
    """
    Create an unauthorized error response (401 Unauthorized).
    
    Args:
        message (str): Error message
    
    Returns:
        Response: DRF Response object with 401 error
    """
    return Response({'message': message}, status=status.HTTP_401_UNAUTHORIZED)


def forbidden_response(message="Permission denied"):
    """
    Create a forbidden error response (403 Forbidden).
    
    Args:
        message (str): Error message
    
    Returns:
        Response: DRF Response object with 403 error
    """
    return Response({'message': message}, status=status.HTTP_403_FORBIDDEN)


def server_error_response(message="Internal server error"):
    """
    Create a server error response (500 Internal Server Error).
    
    Args:
        message (str): Error message
    
    Returns:
        Response: DRF Response object with 500 error
    """
    return Response({'message': message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)