"""
Logging utility functions for GTS application.
Provides easy-to-use logging helpers throughout the application.
"""
import logging
import json
from functools import wraps
from typing import Any, Dict, Optional

# Get loggers
app_logger = logging.getLogger('core')
auth_logger = logging.getLogger('auth')
api_logger = logging.getLogger('api')


def log_info(message: str, extra: Optional[Dict] = None, logger_name: str = 'core'):
    """Log an info message."""
    logger = logging.getLogger(logger_name)
    logger.info(message, extra=extra or {})


def log_debug(message: str, extra: Optional[Dict] = None, logger_name: str = 'core'):
    """Log a debug message."""
    logger = logging.getLogger(logger_name)
    logger.debug(message, extra=extra or {})


def log_warning(message: str, extra: Optional[Dict] = None, logger_name: str = 'core'):
    """Log a warning message."""
    logger = logging.getLogger(logger_name)
    logger.warning(message, extra=extra or {})


def log_error(message: str, exc_info: bool = False, extra: Optional[Dict] = None, logger_name: str = 'core'):
    """Log an error message."""
    logger = logging.getLogger(logger_name)
    logger.error(message, exc_info=exc_info, extra=extra or {})


def log_critical(message: str, exc_info: bool = True, extra: Optional[Dict] = None, logger_name: str = 'core'):
    """Log a critical message."""
    logger = logging.getLogger(logger_name)
    logger.critical(message, exc_info=exc_info, extra=extra or {})


def log_user_action(user, action: str, resource_type: str = None, resource_id: str = None, 
                    details: str = None, success: bool = True):
    """
    Log a user action with structured information.
    
    Args:
        user: User object performing the action
        action: Type of action (CREATE, UPDATE, DELETE, etc.)
        resource_type: Type of resource affected
        resource_id: ID of the affected resource
        details: Additional details about the action
        success: Whether the action was successful
    """
    user_email = user.email if hasattr(user, 'email') else str(user)
    status = "SUCCESS" if success else "FAILED"
    
    log_message = f"USER ACTION | {user_email} | {action}"
    if resource_type:
        log_message += f" | {resource_type}"
        if resource_id:
            log_message += f"#{resource_id}"
    if details:
        log_message += f" | {details}"
    log_message += f" | {status}"
    
    if success:
        app_logger.info(log_message)
    else:
        app_logger.warning(log_message)


def log_auth_event(event_type: str, user_identifier: str, ip_address: str = None, 
                   success: bool = True, reason: str = None):
    """
    Log authentication events.
    
    Args:
        event_type: Type of auth event (LOGIN, LOGOUT, PASSWORD_CHANGE, etc.)
        user_identifier: Email or username
        ip_address: Client IP address
        success: Whether the event was successful
        reason: Failure reason if not successful
    """
    status = "SUCCESS" if success else "FAILED"
    log_message = f"AUTH | {event_type} | {user_identifier} | {status}"
    
    if ip_address:
        log_message += f" | IP: {ip_address}"
    if not success and reason:
        log_message += f" | Reason: {reason}"
    
    if success:
        auth_logger.info(log_message)
    else:
        auth_logger.warning(log_message)


def log_api_call(endpoint: str, method: str, user, status_code: int, 
                 duration_ms: int = None, request_data: Dict = None, 
                 response_data: Dict = None):
    """
    Log API call details.
    
    Args:
        endpoint: API endpoint path
        method: HTTP method
        user: User making the request
        status_code: HTTP response status code
        duration_ms: Request duration in milliseconds
        request_data: Request payload (will be sanitized)
        response_data: Response data
    """
    user_email = user.email if hasattr(user, 'email') and user.is_authenticated else 'Anonymous'
    
    log_message = f"API | {method} {endpoint} | User: {user_email} | Status: {status_code}"
    if duration_ms:
        log_message += f" | Duration: {duration_ms}ms"
    
    # Determine log level based on status code
    if status_code >= 500:
        api_logger.error(log_message)
    elif status_code >= 400:
        api_logger.warning(log_message)
    else:
        api_logger.info(log_message)
    
    # Log request/response data at debug level
    if request_data:
        sanitized_request = sanitize_sensitive_data(request_data)
        api_logger.debug(f"API REQUEST DATA | {method} {endpoint} | {json.dumps(sanitized_request)}")
    
    if response_data and status_code >= 400:
        api_logger.debug(f"API RESPONSE DATA | {method} {endpoint} | {json.dumps(response_data)}")


def log_database_query(query_type: str, model: str, count: int = None, 
                       duration_ms: int = None, filters: Dict = None):
    """
    Log database query information.
    
    Args:
        query_type: Type of query (SELECT, INSERT, UPDATE, DELETE)
        model: Django model name
        count: Number of records affected
        duration_ms: Query duration in milliseconds
        filters: Query filters applied
    """
    db_logger = logging.getLogger('django.db.backends')
    
    log_message = f"DB | {query_type} | {model}"
    if count is not None:
        log_message += f" | Records: {count}"
    if duration_ms:
        log_message += f" | Duration: {duration_ms}ms"
    if filters:
        log_message += f" | Filters: {json.dumps(filters)}"
    
    db_logger.debug(log_message)


def sanitize_sensitive_data(data: Dict) -> Dict:
    """
    Remove sensitive information from data before logging.
    
    Args:
        data: Dictionary containing data to sanitize
    
    Returns:
        Sanitized dictionary
    """
    if not isinstance(data, dict):
        return data
    
    sensitive_keys = ['password', 'token', 'secret', 'api_key', 'authorization', 
                      'credit_card', 'ssn', 'private_key']
    
    sanitized = data.copy()
    for key in sanitized.keys():
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            sanitized[key] = '***REDACTED***'
        elif isinstance(sanitized[key], dict):
            sanitized[key] = sanitize_sensitive_data(sanitized[key])
    
    return sanitized


def log_function_call(logger_name: str = 'core'):
    """
    Decorator to automatically log function calls with arguments and results.
    
    Usage:
        @log_function_call()
        def my_function(arg1, arg2):
            return result
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(logger_name)
            func_name = func.__name__
            
            # Log function call
            logger.debug(f"FUNCTION CALL | {func_name} | Args: {args[:2]}... | Kwargs: {list(kwargs.keys())}")
            
            try:
                result = func(*args, **kwargs)
                logger.debug(f"FUNCTION SUCCESS | {func_name}")
                return result
            except Exception as e:
                logger.error(f"FUNCTION ERROR | {func_name} | Error: {type(e).__name__}: {str(e)}", exc_info=True)
                raise
        
        return wrapper
    return decorator


def log_model_change(action: str, model_name: str, instance_id: Any, user=None, 
                     changed_fields: Dict = None):
    """
    Log model changes (create, update, delete).
    
    Args:
        action: Action performed (CREATE, UPDATE, DELETE)
        model_name: Name of the model
        instance_id: ID of the model instance
        user: User who made the change
        changed_fields: Dictionary of changed fields and their new values
    """
    user_email = user.email if user and hasattr(user, 'email') else 'System'
    
    log_message = f"MODEL {action} | {model_name}#{instance_id} | By: {user_email}"
    
    if changed_fields:
        sanitized_fields = sanitize_sensitive_data(changed_fields)
        log_message += f" | Changes: {json.dumps(sanitized_fields)}"
    
    app_logger.info(log_message)


# Example usage functions
def example_usage():
    """
    Example usage of logging utilities.
    """
    # Simple logging
    log_info("Application started successfully")
    log_debug("Debug information for developers")
    log_warning("This is a warning message")
    log_error("An error occurred", exc_info=True)
    
    # User action logging
    # log_user_action(
    #     user=current_user,
    #     action="CREATE",
    #     resource_type="Trip",
    #     resource_id="12345",
    #     details="New trip created from MS1 to DBS3",
    #     success=True
    # )
    
    # Auth event logging
    log_auth_event(
        event_type="LOGIN",
        user_identifier="user@example.com",
        ip_address="192.168.1.1",
        success=True
    )
    
    # API call logging
    # log_api_call(
    #     endpoint="/api/v1/trips",
    #     method="POST",
    #     user=current_user,
    #     status_code=201,
    #     duration_ms=45
    # )
