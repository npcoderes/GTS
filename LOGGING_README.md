# GTS Logging System

## Overview
Comprehensive Python logging system that records all interactions to separate log files with automatic rotation.

## Log Files Structure

```
backend/logs/
├── app.log          # All application logs (DEBUG and above)
├── info.log         # INFO level logs
├── warning.log      # WARNING level logs
├── error.log        # ERROR level and CRITICAL logs
├── debug.log        # DEBUG level logs (detailed)
├── auth.log         # Authentication events (login, logout, password changes)
├── requests.log     # HTTP requests and responses
└── database.log     # Database queries (when enabled)
```

## Features

### 1. Automatic Log Rotation
- Files rotate when they reach size limits (5-20MB depending on type)
- Keeps 3-10 backup files
- Prevents disk space issues

### 2. Request/Response Logging
Middleware automatically logs:
- HTTP method, path, user, IP address
- Request duration in milliseconds
- Response status codes
- User agent information

### 3. Authentication Logging
Tracks:
- Login attempts (successful and failed)
- Logout events
- IP addresses and timestamps

### 4. Structured Logging
Multiple log formats:
- **Simple**: Level, timestamp, message
- **Verbose**: Includes logger name, module, process/thread IDs
- **Detailed**: Includes function name and line number

## Usage Examples

### Basic Logging

```python
from core.logging_utils import log_info, log_debug, log_warning, log_error

# Simple messages
log_info("User completed action successfully")
log_debug("Variable value: x=123, y=456")
log_warning("Low disk space detected")
log_error("Failed to connect to database", exc_info=True)
```

### User Action Logging

```python
from core.logging_utils import log_user_action

log_user_action(
    user=request.user,
    action="CREATE",
    resource_type="Trip",
    resource_id="T-12345",
    details="Created trip from MS-001 to DBS-005",
    success=True
)
```

### Authentication Logging

```python
from core.logging_utils import log_auth_event

# Successful login
log_auth_event(
    event_type="LOGIN",
    user_identifier=user.email,
    ip_address=request.META['REMOTE_ADDR'],
    success=True
)

# Failed login
log_auth_event(
    event_type="LOGIN",
    user_identifier="user@example.com",
    ip_address=ip_address,
    success=False,
    reason="Invalid credentials"
)
```

### API Call Logging

```python
from core.logging_utils import log_api_call

log_api_call(
    endpoint="/api/v1/trips",
    method="POST",
    user=request.user,
    status_code=201,
    duration_ms=85,
    request_data=request.data,
    response_data=response.data
)
```

### Model Change Logging

```python
from core.logging_utils import log_model_change

log_model_change(
    action="UPDATE",
    model_name="Vehicle",
    instance_id=vehicle.id,
    user=request.user,
    changed_fields={"status": "ACTIVE", "mileage": 12500}
)
```

### Function Call Decorator

```python
from core.logging_utils import log_function_call

@log_function_call()
def calculate_trip_distance(origin, destination):
    """This function's calls will be automatically logged."""
    # Your code here
    return distance
```

## Testing

Run the test script to verify logging:

```bash
python test_logging.py
```

Then check the log files in the `logs/` directory:

```bash
# View all logs
cat logs/app.log

# View only errors
cat logs/error.log

# View authentication events
cat logs/auth.log

# Tail logs in real-time
tail -f logs/app.log

# On Windows PowerShell:
Get-Content logs/app.log -Tail 50
Get-Content logs/error.log -Wait  # Real-time monitoring
```

## Log Levels

1. **DEBUG**: Detailed diagnostic information
2. **INFO**: Confirmation that things are working as expected
3. **WARNING**: Something unexpected happened, but the app is still working
4. **ERROR**: A serious problem occurred, some functionality failed
5. **CRITICAL**: A very serious error, the program might not be able to continue

## Middleware

### RequestLoggingMiddleware
Automatically logs every HTTP request and response:
- Request: method, path, user, IP
- Response: status code, duration
- Exceptions during processing

### AuthenticationLoggingMiddleware
Automatically logs authentication events:
- Login attempts
- Successful logins
- Failed logins
- Logout events

## Configuration

All logging configuration is in `backend/settings.py`. You can adjust:
- Log file sizes and rotation counts
- Log levels per logger
- Log formats
- File paths

### Enable SQL Query Logging

To see all database queries in `logs/database.log`, change in settings.py:

```python
'django.db.backends': {
    'handlers': ['file_database'],
    'level': 'DEBUG',  # Change from WARNING to DEBUG
    'propagate': False,
},
```

## Security

- Sensitive data (passwords, tokens, API keys) is automatically redacted
- User agents and IP addresses are logged for security auditing
- Failed login attempts are tracked for intrusion detection

## Best Practices

1. **Use appropriate log levels**: Don't log everything as ERROR
2. **Include context**: Add user, resource IDs, and relevant details
3. **Don't log sensitive data**: Passwords, tokens, credit cards
4. **Use structured logging**: Use the utility functions for consistency
5. **Monitor error logs**: Set up alerts for critical errors
6. **Rotate logs regularly**: Already configured, but monitor disk space

## Performance

- Asynchronous file writes don't block requests
- Log rotation prevents large file sizes
- Separate files allow targeted reading
- Indexes on common queries

## Troubleshooting

### Logs not appearing?
1. Check logs directory exists: `ls logs/`
2. Check file permissions
3. Verify middleware is in `MIDDLEWARE` setting
4. Check log level configuration

### Logs too verbose?
Change log level in settings.py:
```python
'core': {
    'level': 'INFO',  # Change from DEBUG to INFO or WARNING
}
```

### Need more detail?
Change level to DEBUG and check `logs/debug.log`
