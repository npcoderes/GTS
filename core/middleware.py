"""
Logging middleware for GTS application.
Logs all HTTP requests and responses with timing information.
"""
import logging
import time
import json
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('core')
request_logger = logging.getLogger('api')


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log all incoming HTTP requests and outgoing responses.
    Captures timing, user info, request details, and response status.
    """
    
    def process_request(self, request):
        """Log request details and start timing."""
        request.start_time = time.time()
        
        # Extract request information
        user = getattr(request, 'user', None)
        user_info = user.email if user and user.is_authenticated else 'Anonymous'
        
        method = request.method
        path = request.path
        ip_address = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
        
        # Log request
        request_logger.info(
            f"REQUEST | {method} {path} | User: {user_info} | IP: {ip_address}"
        )
        
        # Detailed debug log
        logger.debug(
            f"REQUEST DETAILS | {method} {path} | User: {user_info} | "
            f"IP: {ip_address} | User-Agent: {user_agent[:50]}"
        )
        
        return None
    
    def process_response(self, request, response):
        """Log response details and timing."""
        # Calculate request duration
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            duration_ms = int(duration * 1000)
        else:
            duration_ms = 0
        
        # Extract information
        user = getattr(request, 'user', None)
        user_info = user.email if user and user.is_authenticated else 'Anonymous'
        
        method = request.method
        path = request.path
        status_code = response.status_code
        
        # Determine log level based on status code
        if status_code >= 500:
            log_level = logging.ERROR
        elif status_code >= 400:
            log_level = logging.WARNING
        else:
            log_level = logging.INFO
        
        # Log response
        request_logger.log(
            log_level,
            f"RESPONSE | {method} {path} | Status: {status_code} | "
            f"Duration: {duration_ms}ms | User: {user_info}"
        )
        
        return response
    
    def process_exception(self, request, exception):
        """Log exceptions that occur during request processing."""
        user = getattr(request, 'user', None)
        user_info = user.email if user and user.is_authenticated else 'Anonymous'
        
        method = request.method
        path = request.path
        
        logger.error(
            f"EXCEPTION | {method} {path} | User: {user_info} | "
            f"Error: {type(exception).__name__}: {str(exception)}",
            exc_info=True
        )
        
        return None
    
    @staticmethod
    def get_client_ip(request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class AuthenticationLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log authentication events (login, logout, failed attempts).
    """
    
    def process_request(self, request):
        """Check for authentication-related requests."""
        auth_logger = logging.getLogger('auth')
        
        # Check if this is a login request
        if 'login' in request.path.lower():
            user = getattr(request, 'user', None)
            ip_address = RequestLoggingMiddleware.get_client_ip(request)
            
            if request.method == 'POST':
                auth_logger.info(
                    f"LOGIN ATTEMPT | IP: {ip_address} | Path: {request.path}"
                )
        
        return None
    
    def process_response(self, request, response):
        """Log successful authentication events."""
        auth_logger = logging.getLogger('auth')
        
        # Check for login/logout
        if 'login' in request.path.lower() or 'logout' in request.path.lower():
            user = getattr(request, 'user', None)
            user_info = user.email if user and user.is_authenticated else 'Unknown'
            ip_address = RequestLoggingMiddleware.get_client_ip(request)
            
            if response.status_code < 400:
                if 'login' in request.path.lower():
                    auth_logger.info(
                        f"LOGIN SUCCESS | User: {user_info} | IP: {ip_address}"
                    )
                elif 'logout' in request.path.lower():
                    auth_logger.info(
                        f"LOGOUT | User: {user_info} | IP: {ip_address}"
                    )
            else:
                if 'login' in request.path.lower():
                    auth_logger.warning(
                        f"LOGIN FAILED | Status: {response.status_code} | IP: {ip_address}"
                    )
        
        return response
