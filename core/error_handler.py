"""
Centralized Error Handling Utility
Provides consistent error logging without interrupting app flow
"""
import logging
import traceback
from functools import wraps

logger = logging.getLogger(__name__)


def log_exception(context="", level="error", reraise=False):
    """
    Decorator to log exceptions without breaking app flow
    
    Args:
        context: Description of what was being attempted
        level: Logging level (error, warning, info)
        reraise: Whether to re-raise the exception after logging
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log_func = getattr(logger, level, logger.error)
                log_func(
                    f"{context or func.__name__} failed: {str(e)}",
                    exc_info=True,
                    extra={
                        'function': func.__name__,
                        'args': str(args)[:200],
                        'kwargs': str(kwargs)[:200]
                    }
                )
                if reraise:
                    raise
                return None
        return wrapper
    return decorator


def safe_execute(func, *args, default=None, context="", log_level="warning", **kwargs):
    """
    Execute a function safely, logging errors without crashing
    
    Args:
        func: Function to execute
        *args: Positional arguments for func
        default: Default value to return on error
        context: Description for logging
        log_level: Logging level for errors
        **kwargs: Keyword arguments for func
    
    Returns:
        Function result or default value on error
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        log_func = getattr(logger, log_level, logger.warning)
        log_func(
            f"{context or func.__name__} failed: {str(e)}",
            exc_info=True
        )
        return default
