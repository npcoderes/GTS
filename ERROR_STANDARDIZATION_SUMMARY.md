# API Error Response Standardization - Summary

## Overview
All API endpoints have been updated to return consistent error responses with a `message` field (and optional `code` field) as required by the frontend. The login API and token expiration errors remain unchanged with their specific formats.

## Error Response Format

All API error responses now follow this consistent format:
```json
{
  "message": "Clear error description for user",
  "code": "ERROR_CODE"  // Optional - for programmatic handling
}
```

### Error Codes Available
- `VALIDATION_ERROR` - General validation errors
- `MISSING_FIELD` - Required field not provided
- `INVALID_FORMAT` - Invalid data format
- `INVALID_VALUE` - Invalid data value
- `UNAUTHORIZED` - Authentication required
- `FORBIDDEN` - Permission denied
- `TOKEN_EXPIRED` - Auth token expired (handled separately in exception_handlers.py)
- `PERMISSION_DENIED` - Access not allowed
- `NOT_FOUND` - Resource not found
- `ALREADY_EXISTS` - Resource already exists
- `CONFLICT` - Conflicting operation
- `INVALID_STATUS` - Invalid status for operation
- `OPERATION_NOT_ALLOWED` - Operation not permitted
- `EXPIRED` - Resource/offer expired
- `INTERNAL_ERROR` - Server error
- `SERVICE_UNAVAILABLE` - Service unavailable

## Changes Made

### 1. Enhanced Error Response Utility (`core/error_response.py`)
- Added `ErrorCodes` class with standard error codes
- Enhanced `error_response()` with optional `code` parameter
- Enhanced `validation_error_response()` with `code` parameter
- Enhanced `not_found_response()` with `code` parameter
- Enhanced `unauthorized_response()` with `code` parameter
- Enhanced `forbidden_response()` with `code` parameter
- Enhanced `server_error_response()` with `code` parameter and logging
- Added `missing_field_response()` helper
- Added `invalid_status_response()` helper

### 2. Updated Core Views (`core/views.py`)
- FCM token registration errors
- Notification send errors  
- All error responses use standardized utilities

### 3. Updated Core Notification Views (`core/notification_views.py`)
- Device token registration/unregistration errors for Driver, DBS, MS operators

### 4. Updated Core Permission Views (`core/permission_views.py`)
- Role and user permission CRUD errors

### 5. Updated Logistics DBS Views (`logistics/dbs_views.py`)
- Dashboard, decanting, stock request, transfer errors

### 6. Updated Logistics EIC Views (`logistics/eic_views.py`)
- Stock request approval/rejection errors
- Driver assignment errors
- Dashboard, driver approval, permissions errors

### 7. Updated Logistics Customer Views (`logistics/customer_views.py`)
- Dashboard, stocks, transport, transfers, pending trips errors

### 8. Updated Logistics Driver Views (`logistics/driver_views.py`)
- Trip management errors

### 9. Updated Logistics Reconciliation Views (`logistics/reconciliation_views.py`)
- Permission errors

## Token Expiration Format (UNCHANGED)
Token expiration errors are handled separately in `core/exception_handlers.py` and return:
```json
{
  "detail": {
    "code": "TOKEN_EXPIRED",
    "message": "Token has expired."
  }
}
```
This format is preserved for frontend compatibility.

## Key Benefits

1. **Frontend Consistency** - All APIs return `message` field for display
2. **Programmatic Handling** - Optional `code` field for error type identification  
3. **Better User Experience** - Clear, consistent error messages
4. **Easier Debugging** - Standardized error format across all endpoints
5. **Maintainable Code** - Centralized error response utilities
6. **Type Safety** - Consistent response structure for frontend TypeScript

## Files Modified

1. `core/error_response.py` - Enhanced with error codes
2. `core/views.py` - Updated error responses
3. `core/notification_views.py` - Updated error responses
4. `core/permission_views.py` - Updated error responses
5. `logistics/views.py` - Previously updated
6. `logistics/dbs_views.py` - Updated error responses
7. `logistics/eic_views.py` - Updated error responses
8. `logistics/customer_views.py` - Updated error responses
9. `logistics/driver_views.py` - Updated error responses
10. `logistics/reconciliation_views.py` - Updated error responses

## Status: ✅ COMPLETE

All API endpoints now return consistent error responses with the `message` field as required by the frontend. The login API continues to work as expected, and all other APIs have been standardized to match the same format.