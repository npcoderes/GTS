"""
Request Logging Middleware
Logs full URL and payload for every request to requests.log
Logs errors (400, 401, 500, etc.) with full details to error.log
"""
import logging
import json
import traceback
from django.utils import timezone
from django.http import JsonResponse
from django.core.exceptions import RequestDataTooBig

request_logger = logging.getLogger('request_logger')
error_logger = logging.getLogger('django.request')


class RequestLoggingMiddleware:
    """
    Middleware to log all requests with full URL and payload.
    Logs errors with full details to error.log.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Try to get request details BEFORE processing
        try:
            request_data = self._get_request_data(request)
        except RequestDataTooBig as e:
            # Log the oversized request
            error_message = (
                f"\n{'='*60}\n"
                f"REQUEST TOO LARGE at {timezone.now().isoformat()}\n"
                f"{'='*60}\n"
                f"URL: {request.build_absolute_uri()}\n"
                f"Method: {request.method}\n"
                f"IP: {self._get_client_ip(request)}\n"
                f"Content-Length: {request.META.get('CONTENT_LENGTH', 'unknown')} bytes\n"
                f"Content-Type: {request.META.get('CONTENT_TYPE', 'unknown')}\n"
                f"Error: Request payload too large. Max allowed is 50MB.\n"
                f"{'='*60}\n"
            )
            error_logger.error(error_message)
            request_logger.error(f"REQUEST TOO LARGE: {request.method} {request.build_absolute_uri()} | Content-Length: {request.META.get('CONTENT_LENGTH', 'unknown')}")
            
            return JsonResponse({
                'success': False,
                'error': 'Request payload too large. Maximum allowed size is 50MB.',
                'max_size_mb': 50
            }, status=413)
        except Exception as e:
            # Log any other error reading request
            error_logger.error(f"Error reading request data: {e}")
            request_data = {
                'method': request.method,
                'path': request.path,
                'full_url': request.build_absolute_uri(),
                'user': 'Unknown',
                'ip': self._get_client_ip(request),
                'timestamp': timezone.now().isoformat(),
                'payload': f'[Error reading payload: {e}]'
            }
        
        # Process the request
        response = self.get_response(request)
        
        # Log the request
        self._log_request(request, response, request_data)
        
        # Log errors
        if response.status_code >= 400:
            self._log_error(request, response, request_data)
        
        return response
    
    def _get_request_data(self, request):
        """Extract request data before processing."""
        data = {
            'method': request.method,
            'path': request.path,
            'full_url': request.build_absolute_uri(),
            'user': str(request.user) if hasattr(request, 'user') and request.user.is_authenticated else 'Anonymous',
            'ip': self._get_client_ip(request),
            'timestamp': timezone.now().isoformat(),
        }
        
        # Get query params
        if request.GET:
            data['query_params'] = dict(request.GET)
        
        # Get body/payload
        try:
            if request.body:
                try:
                    data['payload'] = json.loads(request.body.decode('utf-8'))
                except json.JSONDecodeError:
                    data['payload'] = request.body.decode('utf-8', errors='replace')[:500]
        except Exception:
            data['payload'] = None
        
        return data
    
    def _get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
    
    def _log_request(self, request, response, request_data):
        """Log request to requests.log"""
        try:
            log_message = (
                f"{request_data['method']} {request_data['full_url']} | "
                f"Status: {response.status_code} | "
                f"User: {request_data['user']} | "
                f"IP: {request_data['ip']}"
            )
            
            # Add payload for POST/PUT/PATCH
            if request_data['method'] in ['POST', 'PUT', 'PATCH'] and request_data.get('payload'):
                payload_str = json.dumps(request_data['payload']) if isinstance(request_data['payload'], dict) else str(request_data['payload'])
                # Truncate long payloads
                if len(payload_str) > 1000:
                    payload_str = payload_str[:1000] + '...[truncated]'
                log_message += f" | Payload: {payload_str}"
            
            # Add query params for GET
            if request_data.get('query_params'):
                log_message += f" | Params: {json.dumps(request_data['query_params'])}"
            
            request_logger.info(log_message)
            
        except Exception as e:
            request_logger.error(f"Error logging request: {e}")
    
    def _log_error(self, request, response, request_data):
        """Log error to error.log with full details."""
        try:
            # Get response body if possible
            response_body = ''
            try:
                if hasattr(response, 'content'):
                    response_body = response.content.decode('utf-8', errors='replace')[:500]
            except Exception:
                pass
            
            error_message = (
                f"\n{'='*60}\n"
                f"ERROR {response.status_code} at {request_data['timestamp']}\n"
                f"{'='*60}\n"
                f"URL: {request_data['full_url']}\n"
                f"Method: {request_data['method']}\n"
                f"User: {request_data['user']}\n"
                f"IP: {request_data['ip']}\n"
            )
            
            if request_data.get('query_params'):
                error_message += f"Query Params: {json.dumps(request_data['query_params'], indent=2)}\n"
            
            if request_data.get('payload'):
                payload_str = json.dumps(request_data['payload'], indent=2) if isinstance(request_data['payload'], dict) else str(request_data['payload'])
                error_message += f"Request Payload:\n{payload_str}\n"
            
            error_message += f"Response Status: {response.status_code}\n"
            
            if response_body:
                error_message += f"Response Body: {response_body}\n"
            
            error_message += f"{'='*60}\n"
            
            error_logger.warning(error_message)
            
        except Exception as e:
            error_logger.error(f"Error logging error: {e}")
    
    def process_exception(self, request, exception):
        """Log unhandled exceptions."""
        try:
            error_message = (
                f"\n{'='*60}\n"
                f"EXCEPTION at {timezone.now().isoformat()}\n"
                f"{'='*60}\n"
                f"URL: {request.build_absolute_uri()}\n"
                f"Method: {request.method}\n"
                f"User: {str(request.user) if hasattr(request, 'user') else 'Unknown'}\n"
                f"Exception: {type(exception).__name__}: {str(exception)}\n"
                f"Traceback:\n{traceback.format_exc()}\n"
                f"{'='*60}\n"
            )
            error_logger.error(error_message)
        except Exception:
            pass
        return None
