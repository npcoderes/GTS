"""
Standardized error response utility for consistent API error handling.

All API errors should use these utility functions to ensure:
1. Consistent 'message' field for frontend display
2. Optional 'code' field for programmatic error handling
3. Optional additional data for context

Error Response Format:
{
    "message": "Human-readable error message",
    "code": "ERROR_CODE",  // Optional - for programmatic handling
    ...additional_data
}
"""
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


# Error codes for programmatic error handling
class ErrorCodes:
    """Standard error codes for API responses"""
    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    MISSING_FIELD = "MISSING_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"
    INVALID_VALUE = "INVALID_VALUE"
    
    # Authentication/Authorization
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    
    # Resource errors
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    CONFLICT = "CONFLICT"
    
    # Business logic errors
    INVALID_STATUS = "INVALID_STATUS"
    OPERATION_NOT_ALLOWED = "OPERATION_NOT_ALLOWED"
    EXPIRED = "EXPIRED"
    
    # Server errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


def error_response(message, status_code=status.HTTP_400_BAD_REQUEST, code=None, extra_data=None):
    """
    Create a standardized error response with message field.
    
    Args:
        message (str): Error message to display to user
        status_code (int): HTTP status code (default: 400)
        code (str): Optional error code for programmatic handling
        extra_data (dict): Additional data to include in response
    
    Returns:
        Response: DRF Response object with standardized error format
    """
    response_data = {'message': message}
    
    if code:
        response_data['code'] = code
    
    if extra_data:
        response_data.update(extra_data)
    
    return Response(response_data, status=status_code)


def validation_error_response(message, errors=None, code=ErrorCodes.VALIDATION_ERROR):
    """
    Create a validation error response (400 Bad Request).
    
    Args:
        message (str): Main error message
        errors (dict): Field-specific validation errors
        code (str): Error code (default: VALIDATION_ERROR)
    
    Returns:
        Response: DRF Response object with validation error format
    """
    response_data = {'message': message, 'code': code}
    
    if errors:
        response_data['errors'] = errors
    
    return Response(response_data, status=status.HTTP_400_BAD_REQUEST)


def not_found_response(message="Resource not found", code=ErrorCodes.NOT_FOUND):
    """
    Create a not found error response (404 Not Found).
    
    Args:
        message (str): Error message
        code (str): Error code (default: NOT_FOUND)
    
    Returns:
        Response: DRF Response object with 404 error
    """
    return Response({'message': message, 'code': code}, status=status.HTTP_404_NOT_FOUND)


def unauthorized_response(message="Authentication required", code=ErrorCodes.UNAUTHORIZED):
    """
    Create an unauthorized error response (401 Unauthorized).
    
    Args:
        message (str): Error message
        code (str): Error code (default: UNAUTHORIZED)
    
    Returns:
        Response: DRF Response object with 401 error
    """
    return Response({'message': message, 'code': code}, status=status.HTTP_401_UNAUTHORIZED)


def forbidden_response(message="Permission denied", code=ErrorCodes.FORBIDDEN):
    """
    Create a forbidden error response (403 Forbidden).
    
    Args:
        message (str): Error message
        code (str): Error code (default: FORBIDDEN)
    
    Returns:
        Response: DRF Response object with 403 error
    """
    return Response({'message': message, 'code': code}, status=status.HTTP_403_FORBIDDEN)


def server_error_response(message="An error occurred. Please try again.", code=ErrorCodes.INTERNAL_ERROR, log_error=True):
    """
    Create a server error response (500 Internal Server Error).
    
    Args:
        message (str): Error message (user-friendly, hide technical details)
        code (str): Error code (default: INTERNAL_ERROR)
        log_error (bool): Whether to log the error (default: True)
    
    Returns:
        Response: DRF Response object with 500 error
    """
    if log_error:
        logger.error(f"Server error response: {message}")
    return Response({'message': message, 'code': code}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def missing_field_response(field_name):
    """
    Create a standardized missing field error response.
    
    Args:
        field_name (str): Name of the missing field
    
    Returns:
        Response: DRF Response object with 400 error
    """
    return Response({
        'message': f'{field_name} is required',
        'code': ErrorCodes.MISSING_FIELD,
        'field': field_name
    }, status=status.HTTP_400_BAD_REQUEST)


def invalid_status_response(message, current_status=None):
    """
    Create a standardized invalid status error response.
    
    Args:
        message (str): Error message
        current_status (str): The current status that caused the error
    
    Returns:
        Response: DRF Response object with 400 error
    """
    response_data = {
        'message': message,
        'code': ErrorCodes.INVALID_STATUS
    }
    if current_status:
        response_data['current_status'] = current_status
    return Response(response_data, status=status.HTTP_400_BAD_REQUEST)