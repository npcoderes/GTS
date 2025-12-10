# Permission Change Notifications via WebSocket

**Version:** 1.0
**Last Updated:** 2025-12-09

## Overview

This document describes the WebSocket-based real-time notification system for permission changes in the GTS application. When a user's permissions are modified (either through direct user permission overrides or role permission updates), they receive an immediate WebSocket notification prompting them to refetch their permissions.

## Features

- **Real-time Notifications**: Users are instantly notified when their permissions change
- **Token-based Authentication**: Secure WebSocket connections using API tokens
- **Automatic Permission Refresh**: Frontend apps can automatically refetch permissions upon receiving notifications
- **Role-based Notifications**: All users with a role are notified when that role's permissions change
- **User-specific Notifications**: Individual users are notified when their personal permission overrides change

## Architecture

### WebSocket Consumer

**File:** `logistics/consumers.py`

The `UserConsumer` class handles WebSocket connections for all authenticated users:

```python
class UserConsumer(AsyncWebsocketConsumer):
    """
    Generic consumer for all authenticated users.
    Used for permission change notifications and other user-specific events.
    """
```

**Connection Pattern:**
- Each user connects to their own unique channel group: `user_{user_id}`
- Multiple devices/sessions can connect simultaneously
- All connections for the same user receive the same notifications

### Notification Triggers

**File:** `core/permission_views.py`

#### 1. Role Permission Updates

When a role's permissions are updated via the bulk update endpoint, all users with that active role are notified:

```python
# Endpoint: POST /api/role-permissions/bulk-update/
def notify_role_users_permission_change(role):
    """
    Send WebSocket notification to all users with a specific role
    """
```

#### 2. User Permission Updates

When a specific user's permission overrides are updated, only that user is notified:

```python
# Endpoint: POST /api/user-permissions/bulk-update/
def notify_user_permission_change(user_id):
    """
    Send WebSocket notification to a specific user
    """
```

## WebSocket Connection

### Connection URL

```
ws://<your-domain>/ws/user/updates/?token=<user-api-token>
```

**Production (WSS):**
```
wss://<your-domain>/ws/user/updates/?token=<user-api-token>
```

### Authentication

WebSocket connections are authenticated using the user's REST API token passed as a query parameter.

**Example Connection Flow:**

1. User logs in and receives API token
2. Frontend establishes WebSocket connection with token
3. Backend validates token and adds user to their channel group
4. Connection is established and ready to receive notifications

## API Endpoints

### 1. Role Permission Bulk Update

**Endpoint:** `POST /api/role-permissions/bulk-update/`

**Purpose:** Update multiple permissions for a role and notify all users with that role

**Request:**
```json
{
  "role_id": 1,
  "permissions": {
    "can_raise_manual_request": true,
    "can_confirm_arrival": false,
    "can_view_trips": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "role": "MS_OPERATOR",
  "created": ["can_raise_manual_request"],
  "updated": ["can_confirm_arrival"]
}
```

**WebSocket Event Sent:**
All users with the `MS_OPERATOR` role receive:
```json
{
  "event_type": "permissions_changed",
  "message": "Your role (MS Operator) permissions have been updated. Please refresh.",
  "role": "MS_OPERATOR",
  "timestamp": "2025-12-09T10:30:00.123456Z"
}
```

### 2. User Permission Bulk Update

**Endpoint:** `POST /api/user-permissions/bulk-update/`

**Purpose:** Update permission overrides for a specific user and notify them

**Request:**
```json
{
  "user_id": 42,
  "permissions": {
    "can_raise_manual_request": true,
    "can_confirm_arrival": null
  }
}
```

**Note:** Set permission to `null` to remove user-specific override and fall back to role permissions

**Response:**
```json
{
  "success": true,
  "user_id": 42,
  "created": ["can_raise_manual_request"],
  "updated": [],
  "deleted": ["can_confirm_arrival"]
}
```

**WebSocket Event Sent:**
User 42 receives:
```json
{
  "event_type": "permissions_changed",
  "message": "Your permissions have been updated. Please refresh.",
  "timestamp": "2025-12-09T10:30:00.123456Z"
}
```

## Frontend Integration

### JavaScript/TypeScript Example

```javascript
class PermissionNotificationService {
  constructor(apiToken) {
    this.apiToken = apiToken;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }

  connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/user/updates/?token=${this.apiToken}`;

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('Permission notification WebSocket connected');
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket closed');
      this.attemptReconnect();
    };
  }

  handleMessage(data) {
    console.log('Received WebSocket message:', data);

    if (data.type === 'connection_established') {
      console.log('Connection established:', data.message);
      return;
    }

    if (data.event_type === 'permissions_changed') {
      console.log('Permissions changed:', data.message);

      // Refetch user permissions
      this.refetchPermissions();

      // Optionally show notification to user
      this.showNotification(data.message);
    }
  }

  async refetchPermissions() {
    try {
      const response = await fetch('/api/auth/permissions/', {
        headers: {
          'Authorization': `Token ${this.apiToken}`
        }
      });

      const data = await response.json();

      // Update permissions in your app state/store
      // Example: store.dispatch(setPermissions(data.permissions));
      console.log('Permissions refreshed:', data.permissions);

      // Optionally trigger UI updates based on new permissions
      this.onPermissionsUpdated(data.permissions);

    } catch (error) {
      console.error('Failed to refetch permissions:', error);
    }
  }

  showNotification(message) {
    // Show notification to user (browser notification, toast, banner, etc.)
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification('Permissions Updated', {
        body: message,
        icon: '/static/icon.png'
      });
    }
  }

  onPermissionsUpdated(permissions) {
    // Trigger any necessary UI updates
    // Example: Refresh menu items, disable/enable buttons, etc.
    console.log('Triggering UI updates for new permissions');
  }

  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);

      console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);

      setTimeout(() => this.connect(), delay);
    } else {
      console.error('Max reconnect attempts reached');
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

// Usage Example
const token = localStorage.getItem('api_token');
const permissionService = new PermissionNotificationService(token);
permissionService.connect();

// When user logs out
// permissionService.disconnect();
```

### React Example with Hooks

```javascript
import { useEffect, useRef, useState } from 'react';
import { useAuth } from './AuthContext';
import { usePermissions } from './PermissionsContext';

function usePermissionNotifications() {
  const { token } = useAuth();
  const { refetchPermissions } = usePermissions();
  const wsRef = useRef(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    if (!token) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/user/updates/?token=${token}`;

    wsRef.current = new WebSocket(wsUrl);

    wsRef.current.onopen = () => {
      console.log('Permission notifications connected');
      setIsConnected(true);
    };

    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.event_type === 'permissions_changed') {
        console.log('Permissions changed, refetching...');
        refetchPermissions();

        // Optionally show toast notification
        // toast.info(data.message);
      }
    };

    wsRef.current.onclose = () => {
      console.log('Permission notifications disconnected');
      setIsConnected(false);
    };

    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [token, refetchPermissions]);

  return { isConnected };
}

export default usePermissionNotifications;
```

### React Native Example

```javascript
import { useEffect, useRef } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { fetchUserPermissions } from './store/permissionsSlice';

export const usePermissionNotifications = () => {
  const token = useSelector((state) => state.auth.token);
  const dispatch = useDispatch();
  const wsRef = useRef(null);

  useEffect(() => {
    if (!token) return;

    // Use your backend URL
    const wsUrl = `ws://your-backend.com/ws/user/updates/?token=${token}`;

    wsRef.current = new WebSocket(wsUrl);

    wsRef.current.onopen = () => {
      console.log('WebSocket connected');
    };

    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.event_type === 'permissions_changed') {
        console.log('Permissions changed:', data.message);

        // Refetch permissions
        dispatch(fetchUserPermissions());

        // Show in-app notification
        // Alert.alert('Permissions Updated', data.message);
      }
    };

    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    wsRef.current.onclose = () => {
      console.log('WebSocket closed');
    };

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [token, dispatch]);
};
```

## Event Types

### Connection Established

Sent immediately after successful WebSocket connection.

```json
{
  "type": "connection_established",
  "message": "User notifications active"
}
```

### Permission Update

Sent when user's permissions are changed.

```json
{
  "event_type": "permissions_changed",
  "message": "Your permissions have been updated. Please refresh.",
  "timestamp": "2025-12-09T10:30:00.123456Z"
}
```

For role-based updates, additional field:
```json
{
  "event_type": "permissions_changed",
  "message": "Your role (MS Operator) permissions have been updated. Please refresh.",
  "role": "MS_OPERATOR",
  "timestamp": "2025-12-09T10:30:00.123456Z"
}
```

## Testing

### Manual Testing with Browser Console

```javascript
// Connect to WebSocket
const token = 'your-api-token-here';
const ws = new WebSocket(`ws://localhost:8000/ws/user/updates/?token=${token}`);

ws.onopen = () => console.log('Connected');
ws.onmessage = (e) => console.log('Message:', JSON.parse(e.data));
ws.onerror = (e) => console.error('Error:', e);
ws.onclose = () => console.log('Closed');
```

### Testing Permission Updates

1. **Connect WebSocket** using the user's token
2. **Update permissions** via API:
   ```bash
   curl -X POST http://localhost:8000/api/user-permissions/bulk-update/ \
     -H "Authorization: Token admin-token" \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": 42,
       "permissions": {
         "can_raise_manual_request": true
       }
     }'
   ```
3. **Verify notification** appears in WebSocket console
4. **Confirm permission refetch** works correctly

### Testing with Multiple Devices

1. Open app on two different devices/browsers with same user
2. Both should connect to WebSocket successfully
3. Update permissions via admin panel
4. Both devices should receive notification simultaneously
5. Both should refetch and update permissions

## Error Handling

### WebSocket Connection Failures

The WebSocket implementation includes automatic error handling:

- **Invalid Token**: Connection is immediately closed
- **User Not Found**: Connection is rejected
- **Connection Lost**: Frontend should implement reconnection logic with exponential backoff

### Notification Failures

If a WebSocket notification fails to send:
- The error is logged but doesn't affect the API response
- The permission update still succeeds
- Users will see updated permissions on next app reload/login

### Best Practices

1. **Always implement reconnection logic** with exponential backoff
2. **Limit reconnection attempts** to avoid infinite loops
3. **Handle connection state** in your UI (show online/offline indicator)
4. **Fallback to polling** if WebSocket connection repeatedly fails
5. **Close WebSocket** when user logs out

## Security Considerations

1. **Token-based Auth**: Only authenticated users can connect
2. **User Isolation**: Users can only connect to their own channel (`user_{user_id}`)
3. **No Sensitive Data**: Notifications only indicate a change occurred, not what changed
4. **Permission Validation**: Always validate permissions on backend, never trust frontend state

## Troubleshooting

### WebSocket connection fails immediately

**Symptom:** Connection closes right after opening

**Possible Causes:**
- Invalid or expired token
- User doesn't exist
- Token doesn't match any user

**Solution:**
- Verify token is valid and not expired
- Check user authentication status
- Ensure token is passed correctly in query params

### No notifications received

**Symptom:** WebSocket connected but no messages arrive when permissions change

**Possible Causes:**
- User not in correct group
- Channel layer not configured
- Redis not running (if using Redis channel layer)

**Solution:**
- Check channel layer configuration in Django settings
- Verify Redis is running: `redis-cli ping`
- Check Django logs for channel layer errors

### Notifications received but permissions not updating

**Symptom:** Message arrives but UI doesn't reflect new permissions

**Possible Causes:**
- Frontend not calling refetch function
- Permission endpoint failing
- State management not updating

**Solution:**
- Verify refetch function is called in message handler
- Check network tab for permission API call
- Debug state management updates

## Configuration

### Django Settings

Ensure your Django settings include WebSocket configuration:

```python
# settings.py

INSTALLED_APPS = [
    # ...
    'channels',
    # ...
]

ASGI_APPLICATION = 'your_project.asgi.application'

# Channel layers configuration (example with Redis)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}
```

### ASGI Configuration

```python
# asgi.py

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from logistics.routing import websocket_urlpatterns

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
```

## Performance Considerations

### Scalability

- **Connection Limit**: Each WebSocket connection consumes server resources
- **Channel Layer**: Use Redis for production to handle multiple server instances
- **Group Broadcasting**: Efficient for notifying multiple users with same role

### Optimization Tips

1. **Use Redis** for channel layer in production
2. **Implement connection pooling** for database queries
3. **Batch notifications** if updating permissions for many users
4. **Monitor WebSocket connections** and set reasonable limits

## Related Documentation

- [Driver Trip Step Persistence](./DRIVER_TRIP_STEP_PERSISTENCE.md)
- [Django Channels Documentation](https://channels.readthedocs.io/)
- [WebSocket API Documentation](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

## Support

For issues or questions:
1. Check Django logs for errors
2. Verify Redis/channel layer is running
3. Test WebSocket connection manually
4. Review this documentation

## Changelog

### Version 1.0 (2025-12-09)
- Initial implementation of permission change notifications
- Support for role-based and user-specific notifications
- WebSocket consumer with token authentication
- Integration with bulk permission update endpoints
