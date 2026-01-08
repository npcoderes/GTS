# Real-Time Notification System Implementation Plan
## WebSocket + Notification UI for EIC Dashboard

---

## 🎯 **Objective**

Implement a production-ready real-time notification system where:
1. **EIC Dashboard** receives instant notifications when transport vendors create shifts
2. **Auto-reload** shift list when new shifts arrive
3. **Notification Bell Icon** shows unread count
4. **Feature Flag** controls whether notifications are enabled
5. **Scalable** WebSocket architecture using Django Channels

---

## 📋 **System Architecture**

### Backend Components

```
┌─────────────────────────────────────────────────────────┐
│                    Django Backend                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐      ┌──────────────┐                │
│  │   HTTP API   │      │  WebSocket   │                │
│  │  (REST API)  │      │   (Channels) │                │
│  └──────────────┘      └──────────────┘                │
│         │                      │                         │
│         │                      │                         │
│  ┌──────▼──────────────────────▼──────┐                │
│  │     Notification Service            │                │
│  │  - Create notifications             │                │
│  │  - Send WebSocket events            │                │
│  │  - Mark as read/unread              │                │
│  └─────────────────────────────────────┘                │
│                                                          │
└─────────────────────────────────────────────────────────┘
                         │
                         │ WebSocket
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  Frontend (React)                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐      ┌──────────────┐                │
│  │ Notification │      │  WebSocket   │                │
│  │  Bell Icon   │◄─────┤   Client     │                │
│  │  (Badge)     │      │              │                │
│  └──────────────┘      └──────────────┘                │
│         │                                                │
│         │                                                │
│  ┌──────▼──────────────────────────────┐                │
│  │   Notification Dropdown              │                │
│  │  - List of notifications             │                │
│  │  - Mark as read                      │                │
│  │  - Click to navigate                 │                │
│  └──────────────────────────────────────┘                │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 🔧 **Implementation Plan**

### **Phase 1: Backend - Django Channels Setup**

#### 1.1 Install Dependencies
```bash
pip install channels channels-redis daphne
```

#### 1.2 Update Django Settings
**File**: `backend/backend/settings.py`

```python
INSTALLED_APPS = [
    'daphne',  # Must be first
    'channels',
    # ... existing apps
]

# Channels Configuration
ASGI_APPLICATION = 'backend.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [os.getenv('REDIS_URL', 'redis://localhost:6379/0')],
        },
    },
}

# Feature Flags
ENABLE_REALTIME_NOTIFICATIONS = os.getenv('ENABLE_REALTIME_NOTIFICATIONS', 'true').lower() == 'true'
```

#### 1.3 Create ASGI Configuration
**File**: `backend/backend/asgi.py`

```python
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

django_asgi_app = get_asgi_application()

from core.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
```

#### 1.4 Create WebSocket Consumer
**File**: `backend/core/consumers.py`

```python
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Get user from scope (authenticated via middleware)
        self.user = self.scope['user']
        
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Create user-specific channel group
        self.user_group_name = f'notifications_{self.user.id}'
        
        # Join user's notification group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial unread count
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': unread_count
        }))
    
    async def disconnect(self, close_code):
        # Leave user's notification group
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
    
    # Receive message from WebSocket
    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')
        
        if action == 'mark_read':
            notification_id = data.get('notification_id')
            await self.mark_notification_read(notification_id)
        elif action == 'mark_all_read':
            await self.mark_all_read()
    
    # Receive message from channel layer
    async def notification_message(self, event):
        # Send notification to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification']
        }))
    
    async def unread_count_update(self, event):
        # Send updated unread count
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': event['count']
        }))
    
    @database_sync_to_async
    def get_unread_count(self):
        from core.models import InAppNotification
        return InAppNotification.objects.filter(
            user=self.user,
            is_read=False
        ).count()
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        from core.models import InAppNotification
        try:
            notification = InAppNotification.objects.get(
                id=notification_id,
                user=self.user
            )
            notification.is_read = True
            notification.save()
            return True
        except InAppNotification.DoesNotExist:
            return False
    
    @database_sync_to_async
    def mark_all_read(self):
        from core.models import InAppNotification
        InAppNotification.objects.filter(
            user=self.user,
            is_read=False
        ).update(is_read=True)
```

#### 1.5 Create WebSocket Routing
**File**: `backend/core/routing.py`

```python
from django.urls import path
from core.consumers import NotificationConsumer

websocket_urlpatterns = [
    path('ws/notifications/', NotificationConsumer.as_asgi()),
]
```

#### 1.6 Create In-App Notification Model
**File**: `backend/core/models.py` (add to existing)

```python
class InAppNotification(models.Model):
    """
    In-app notifications for real-time updates.
    Separate from FCM notifications (mobile push).
    """
    TYPE_CHOICES = [
        ('SHIFT_CREATED', 'Shift Created'),
        ('SHIFT_APPROVED', 'Shift Approved'),
        ('SHIFT_REJECTED', 'Shift Rejected'),
        ('TRIP_ASSIGNED', 'Trip Assigned'),
        ('STOCK_REQUEST', 'Stock Request'),
        ('EMERGENCY', 'Emergency Alert'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='in_app_notifications')
    notification_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    data = models.JSONField(default=dict)  # Additional context
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Action link (optional)
    action_url = models.CharField(max_length=500, null=True, blank=True)
    
    class Meta:
        db_table = 'in_app_notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.notification_type} for {self.user.email}"
```

#### 1.7 Create Notification Service
**File**: `backend/core/realtime_notification_service.py`

```python
import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.conf import settings
from django.utils import timezone
from core.models import InAppNotification, User

logger = logging.getLogger(__name__)

class RealtimeNotificationService:
    """
    Service for sending real-time in-app notifications via WebSocket.
    """
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
        self.enabled = getattr(settings, 'ENABLE_REALTIME_NOTIFICATIONS', True)
    
    def send_notification(self, user, notification_type, title, message, data=None, action_url=None):
        """
        Send real-time notification to user.
        
        Args:
            user: User instance or user ID
            notification_type: Type from InAppNotification.TYPE_CHOICES
            title: Notification title
            message: Notification message
            data: Optional dict with additional context
            action_url: Optional URL for action button
        """
        if not self.enabled:
            logger.debug("Real-time notifications disabled")
            return None
        
        # Get user instance
        if isinstance(user, int):
            try:
                user = User.objects.get(id=user)
            except User.DoesNotExist:
                logger.error(f"User {user} not found")
                return None
        
        # Create in-app notification
        notification = InAppNotification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            data=data or {},
            action_url=action_url
        )
        
        # Send via WebSocket
        self._send_to_user(user.id, notification)
        
        # Update unread count
        self._update_unread_count(user.id)
        
        logger.info(f"Real-time notification sent to user {user.id}: {notification_type}")
        return notification
    
    def _send_to_user(self, user_id, notification):
        """Send notification to user's WebSocket channel."""
        if not self.channel_layer:
            return
        
        group_name = f'notifications_{user_id}'
        
        async_to_sync(self.channel_layer.group_send)(
            group_name,
            {
                'type': 'notification_message',
                'notification': {
                    'id': notification.id,
                    'type': notification.notification_type,
                    'title': notification.title,
                    'message': notification.message,
                    'data': notification.data,
                    'action_url': notification.action_url,
                    'created_at': notification.created_at.isoformat(),
                    'is_read': notification.is_read,
                }
            }
        )
    
    def _update_unread_count(self, user_id):
        """Send updated unread count to user."""
        if not self.channel_layer:
            return
        
        unread_count = InAppNotification.objects.filter(
            user_id=user_id,
            is_read=False
        ).count()
        
        group_name = f'notifications_{user_id}'
        
        async_to_sync(self.channel_layer.group_send)(
            group_name,
            {
                'type': 'unread_count_update',
                'count': unread_count
            }
        )
    
    def notify_shift_created(self, shift, eic_users):
        """
        Notify EIC users when a new shift is created.
        
        Args:
            shift: Shift instance
            eic_users: List of EIC User instances
        """
        driver_name = shift.driver.full_name if shift.driver else 'Unknown'
        vehicle_reg = shift.vehicle.registration_no if shift.vehicle else 'Unknown'
        shift_start = timezone.localtime(shift.start_time).strftime('%Y-%m-%d %I:%M %p')
        
        for eic_user in eic_users:
            self.send_notification(
                user=eic_user,
                notification_type='SHIFT_CREATED',
                title='New Shift Created',
                message=f'Driver {driver_name} created a shift for vehicle {vehicle_reg} starting at {shift_start}. Please review and approve.',
                data={
                    'shift_id': shift.id,
                    'driver_id': shift.driver_id,
                    'driver_name': driver_name,
                    'vehicle_id': shift.vehicle_id,
                    'vehicle_reg': vehicle_reg,
                    'start_time': shift.start_time.isoformat(),
                    'end_time': shift.end_time.isoformat(),
                },
                action_url=f'/shifts/{shift.id}'
            )

# Singleton instance
realtime_notification_service = RealtimeNotificationService()
```

#### 1.8 Update Shift Creation to Send Notifications
**File**: `backend/logistics/views.py` - Update `ShiftViewSet.create()`

```python
def create(self, request, *args, **kwargs):
    # ... existing validation code ...
    
    serializer = self.get_serializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    shift = serializer.save(
        created_by=request.user,
        is_recurring=is_recurring,
        recurrence_pattern=recurrence_pattern
    )
    
    # Send real-time notifications to EIC users
    try:
        from core.realtime_notification_service import realtime_notification_service
        from core.models import UserRole
        
        # Find EIC users for this shift's MS (if vehicle has ms_home)
        if shift.vehicle and shift.vehicle.ms_home:
            eic_roles = UserRole.objects.filter(
                station=shift.vehicle.ms_home,
                role__code='EIC',
                active=True
            ).select_related('user')
            
            eic_users = [role.user for role in eic_roles if role.user]
            
            if eic_users:
                realtime_notification_service.notify_shift_created(shift, eic_users)
                logger.info(f"Sent real-time notifications to {len(eic_users)} EIC users for shift {shift.id}")
    except Exception as e:
        logger.error(f"Failed to send real-time notification for shift {shift.id}: {e}")
    
    # Return success response
    return Response({
        'success': True,
        'message': 'Shift created successfully. Pending EIC approval.',
        'shift_id': shift.id,
        # ... rest of response
    }, status=status.HTTP_201_CREATED)
```

#### 1.9 Create Notification API Endpoints
**File**: `backend/core/notification_views.py`

```python
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from core.models import InAppNotification

class NotificationListView(views.APIView):
    """
    GET /api/notifications/ - Get user's notifications
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        notifications = InAppNotification.objects.filter(
            user=request.user
        ).order_by('-created_at')[:50]  # Last 50 notifications
        
        return Response({
            'notifications': [
                {
                    'id': n.id,
                    'type': n.notification_type,
                    'title': n.title,
                    'message': n.message,
                    'data': n.data,
                    'action_url': n.action_url,
                    'is_read': n.is_read,
                    'created_at': n.created_at.isoformat(),
                }
                for n in notifications
            ],
            'unread_count': InAppNotification.objects.filter(
                user=request.user,
                is_read=False
            ).count()
        })

class NotificationMarkReadView(views.APIView):
    """
    POST /api/notifications/{id}/mark-read/ - Mark notification as read
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, notification_id):
        try:
            notification = InAppNotification.objects.get(
                id=notification_id,
                user=request.user
            )
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save()
            
            return Response({'success': True})
        except InAppNotification.DoesNotExist:
            return Response(
                {'error': 'Notification not found'},
                status=status.HTTP_404_NOT_FOUND
            )

class NotificationMarkAllReadView(views.APIView):
    """
    POST /api/notifications/mark-all-read/ - Mark all notifications as read
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        InAppNotification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        
        return Response({'success': True})
```

---

### **Phase 2: Frontend - React Components**

#### 2.1 Environment Configuration
**File**: `frontend-dashboard/.env`

```env
# WebSocket Configuration
REACT_APP_WS_URL=ws://localhost:8000/ws/notifications/
REACT_APP_WS_URL_PRODUCTION=wss://your-domain.com/ws/notifications/

# Feature Flags
REACT_APP_ENABLE_REALTIME_NOTIFICATIONS=true
```

#### 2.2 WebSocket Client Service
**File**: `frontend-dashboard/src/services/websocket.js`

```javascript
class WebSocketService {
  constructor() {
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 3000;
    this.listeners = new Map();
    this.enabled = process.env.REACT_APP_ENABLE_REALTIME_NOTIFICATIONS === 'true';
  }

  connect(token) {
    if (!this.enabled) {
      console.log('Real-time notifications disabled');
      return;
    }

    const wsUrl = process.env.NODE_ENV === 'production'
      ? process.env.REACT_APP_WS_URL_PRODUCTION
      : process.env.REACT_APP_WS_URL;

    this.ws = new WebSocket(`${wsUrl}?token=${token}`);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      this.emit('connected');
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.emit(data.type, data);
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.emit('error', error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.emit('disconnected');
      this.attemptReconnect(token);
    };
  }

  attemptReconnect(token) {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`Reconnecting... Attempt ${this.reconnectAttempts}`);
      setTimeout(() => this.connect(token), this.reconnectDelay);
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  off(event, callback) {
    if (this.listeners.has(event)) {
      const callbacks = this.listeners.get(event);
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => callback(data));
    }
  }

  markAsRead(notificationId) {
    this.send({
      action: 'mark_read',
      notification_id: notificationId
    });
  }

  markAllAsRead() {
    this.send({
      action: 'mark_all_read'
    });
  }
}

export default new WebSocketService();
```

#### 2.3 Notification Bell Component
**File**: `frontend-dashboard/src/components/NotificationBell.jsx`

```jsx
import React, { useState, useEffect, useRef } from 'react';
import { Badge, Dropdown, List, Button, Empty, Spin } from 'antd';
import { BellOutlined, CheckOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import websocketService from '../services/websocket';
import { notificationAPI } from '../services/api';
import './NotificationBell.css';

const NotificationBell = () => {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [dropdownVisible, setDropdownVisible] = useState(false);
  const navigate = useNavigate();
  const audioRef = useRef(null);

  // Check if feature is enabled
  const enabled = process.env.REACT_APP_ENABLE_REALTIME_NOTIFICATIONS === 'true';

  useEffect(() => {
    if (!enabled) return;

    // Load initial notifications
    loadNotifications();

    // Setup WebSocket listeners
    websocketService.on('notification', handleNewNotification);
    websocketService.on('unread_count', handleUnreadCount);

    return () => {
      websocketService.off('notification', handleNewNotification);
      websocketService.off('unread_count', handleUnreadCount);
    };
  }, [enabled]);

  const loadNotifications = async () => {
    setLoading(true);
    try {
      const response = await notificationAPI.getNotifications();
      setNotifications(response.data.notifications);
      setUnreadCount(response.data.unread_count);
    } catch (error) {
      console.error('Failed to load notifications:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleNewNotification = (data) => {
    const newNotification = data.notification;
    
    // Add to list
    setNotifications(prev => [newNotification, ...prev]);
    
    // Play sound
    if (audioRef.current) {
      audioRef.current.play().catch(e => console.log('Audio play failed:', e));
    }
    
    // Show browser notification if permitted
    if (Notification.permission === 'granted') {
      new Notification(newNotification.title, {
        body: newNotification.message,
        icon: '/logo192.png',
        tag: newNotification.id
      });
    }
  };

  const handleUnreadCount = (data) => {
    setUnreadCount(data.count);
  };

  const handleNotificationClick = async (notification) => {
    // Mark as read
    if (!notification.is_read) {
      try {
        await notificationAPI.markAsRead(notification.id);
        websocketService.markAsRead(notification.id);
        
        // Update local state
        setNotifications(prev =>
          prev.map(n => n.id === notification.id ? { ...n, is_read: true } : n)
        );
      } catch (error) {
        console.error('Failed to mark as read:', error);
      }
    }

    // Navigate to action URL
    if (notification.action_url) {
      navigate(notification.action_url);
      setDropdownVisible(false);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationAPI.markAllAsRead();
      websocketService.markAllAsRead();
      
      // Update local state
      setNotifications(prev =>
        prev.map(n => ({ ...n, is_read: true }))
      );
      setUnreadCount(0);
    } catch (error) {
      console.error('Failed to mark all as read:', error);
    }
  };

  const getNotificationIcon = (type) => {
    const icons = {
      SHIFT_CREATED: '📋',
      SHIFT_APPROVED: '✅',
      SHIFT_REJECTED: '❌',
      TRIP_ASSIGNED: '🚚',
      STOCK_REQUEST: '📦',
      EMERGENCY: '🚨',
    };
    return icons[type] || '🔔';
  };

  const dropdownMenu = (
    <div className="notification-dropdown">
      <div className="notification-header">
        <h3>Notifications</h3>
        {unreadCount > 0 && (
          <Button
            type="link"
            size="small"
            onClick={handleMarkAllRead}
            icon={<CheckOutlined />}
          >
            Mark all read
          </Button>
        )}
      </div>

      <div className="notification-list">
        {loading ? (
          <div style={{ textAlign: 'center', padding: '20px' }}>
            <Spin />
          </div>
        ) : notifications.length === 0 ? (
          <Empty
            description="No notifications"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        ) : (
          <List
            dataSource={notifications}
            renderItem={(notification) => (
              <List.Item
                className={`notification-item ${!notification.is_read ? 'unread' : ''}`}
                onClick={() => handleNotificationClick(notification)}
              >
                <div className="notification-content">
                  <div className="notification-icon">
                    {getNotificationIcon(notification.type)}
                  </div>
                  <div className="notification-text">
                    <div className="notification-title">{notification.title}</div>
                    <div className="notification-message">{notification.message}</div>
                    <div className="notification-time">
                      {new Date(notification.created_at).toLocaleString()}
                    </div>
                  </div>
                  {!notification.is_read && (
                    <div className="notification-badge">
                      <Badge status="processing" />
                    </div>
                  )}
                </div>
              </List.Item>
            )}
          />
        )}
      </div>
    </div>
  );

  if (!enabled) {
    return null; // Don't render if feature is disabled
  }

  return (
    <>
      <Dropdown
        overlay={dropdownMenu}
        trigger={['click']}
        placement="bottomRight"
        visible={dropdownVisible}
        onVisibleChange={setDropdownVisible}
      >
        <Badge count={unreadCount} offset={[-5, 5]}>
          <Button
            type="text"
            icon={<BellOutlined style={{ fontSize: '20px' }} />}
            className="notification-bell-button"
          />
        </Badge>
      </Dropdown>

      {/* Notification sound */}
      <audio ref={audioRef} src="/notification.mp3" preload="auto" />
    </>
  );
};

export default NotificationBell;
```

#### 2.4 Notification Bell CSS
**File**: `frontend-dashboard/src/components/NotificationBell.css`

```css
.notification-bell-button {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 40px;
  width: 40px;
  border-radius: 50%;
  transition: all 0.3s;
}

.notification-bell-button:hover {
  background-color: rgba(0, 0, 0, 0.04);
}

.notification-dropdown {
  width: 380px;
  max-height: 500px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.notification-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.notification-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.notification-list {
  max-height: 400px;
  overflow-y: auto;
}

.notification-item {
  padding: 12px 16px;
  cursor: pointer;
  transition: background-color 0.2s;
  border-bottom: 1px solid #f0f0f0;
}

.notification-item:hover {
  background-color: #f5f5f5;
}

.notification-item.unread {
  background-color: #e6f7ff;
}

.notification-item.unread:hover {
  background-color: #d9f0ff;
}

.notification-content {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.notification-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.notification-text {
  flex: 1;
}

.notification-title {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 4px;
  color: #262626;
}

.notification-message {
  font-size: 13px;
  color: #595959;
  margin-bottom: 4px;
  line-height: 1.4;
}

.notification-time {
  font-size: 12px;
  color: #8c8c8c;
}

.notification-badge {
  flex-shrink: 0;
}
```

#### 2.5 Update App.jsx to Initialize WebSocket
**File**: `frontend-dashboard/src/App.jsx`

```jsx
import { useEffect } from 'react';
import { useAuth } from './contexts/AuthContext';
import websocketService from './services/websocket';
import NotificationBell from './components/NotificationBell';

function App() {
  const { user, token } = useAuth();

  useEffect(() => {
    if (user && token) {
      // Connect WebSocket
      websocketService.connect(token);

      // Request notification permission
      if (Notification.permission === 'default') {
        Notification.requestPermission();
      }

      return () => {
        websocketService.disconnect();
      };
    }
  }, [user, token]);

  return (
    <Layout>
      <Header>
        {/* ... other header content ... */}
        <NotificationBell />
      </Header>
      {/* ... rest of app ... */}
    </Layout>
  );
}
```

#### 2.6 Update Shift List to Auto-Reload
**File**: `frontend-dashboard/src/pages/Shifts/ShiftList.jsx`

```jsx
import { useEffect } from 'react';
import websocketService from '../../services/websocket';

const ShiftList = () => {
  const [shifts, setShifts] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadShifts();

    // Listen for new shift notifications
    const handleNewShift = (data) => {
      if (data.notification.type === 'SHIFT_CREATED') {
        // Auto-reload shifts
        loadShifts();
      }
    };

    websocketService.on('notification', handleNewShift);

    return () => {
      websocketService.off('notification', handleNewShift);
    };
  }, []);

  const loadShifts = async () => {
    setLoading(true);
    try {
      const response = await shiftsAPI.getShifts();
      setShifts(response.data);
    } catch (error) {
      console.error('Failed to load shifts:', error);
    } finally {
      setLoading(false);
    }
  };

  // ... rest of component
};
```

---

## 📦 **Deliverables**

### Backend
1. ✅ Django Channels setup with Redis
2. ✅ WebSocket consumer for notifications
3. ✅ InAppNotification model
4. ✅ RealtimeNotificationService
5. ✅ Notification API endpoints
6. ✅ Integration with shift creation
7. ✅ Feature flag support

### Frontend
1. ✅ WebSocket client service
2. ✅ NotificationBell component
3. ✅ Auto-reload on new notifications
4. ✅ Browser notification support
5. ✅ Sound notification
6. ✅ Feature flag support
7. ✅ Environment configuration

---

## 🚀 **Deployment Checklist**

### Backend
- [ ] Install Redis server
- [ ] Install Python packages: `channels`, `channels-redis`, `daphne`
- [ ] Run migrations: `python manage.py makemigrations && python manage.py migrate`
- [ ] Set `ENABLE_REALTIME_NOTIFICATIONS=true` in environment
- [ ] Configure `REDIS_URL` in environment
- [ ] Update ASGI server (use Daphne instead of Gunicorn for WebSocket)

### Frontend
- [ ] Set `REACT_APP_ENABLE_REALTIME_NOTIFICATIONS=true`
- [ ] Configure WebSocket URLs for dev/prod
- [ ] Add notification sound file to public folder
- [ ] Test WebSocket connection
- [ ] Test notification display

---

## 🎯 **Success Criteria**

1. ✅ EIC sees notification bell with unread count
2. ✅ When vendor creates shift, EIC gets instant notification
3. ✅ Shift list auto-reloads when new shift arrives
4. ✅ Clicking notification navigates to shift details
5. ✅ Feature can be disabled via environment variable
6. ✅ System works in production with WSS (secure WebSocket)

---

## 📊 **Testing Plan**

1. **Unit Tests**: WebSocket consumer, notification service
2. **Integration Tests**: Shift creation → notification flow
3. **E2E Tests**: Full user journey from shift creation to notification
4. **Load Tests**: Multiple concurrent WebSocket connections
5. **Browser Tests**: Chrome, Firefox, Safari compatibility

---

**Ready for review! Should I proceed with implementation?**
