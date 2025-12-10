"""
Notification Service for GTS Backend
Handles sending FCM push notifications to mobile devices.
"""
import json
import logging
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for sending push notifications via Firebase Cloud Messaging (FCM).
    
    For production:
    - Install firebase-admin: pip install firebase-admin
    - Set FIREBASE_CREDENTIALS_FILE in settings to path of service account JSON
    
    For development:
    - Uses mock mode that logs notifications without sending
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        # Always reset on new import to pick up settings changes
        if cls._instance is not None:
            cls._initialized = False
            cls._instance = None
        cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.mock_mode = getattr(settings, 'FCM_MOCK_MODE', True)
            self._firebase_app = None
            
            logger.info(f"FCM_MOCK_MODE setting: {self.mock_mode}")
            
            if not self.mock_mode:
                self._init_firebase()
            else:
                logger.info("NotificationService running in MOCK mode (FCM_MOCK_MODE=True)")
            
            NotificationService._initialized = True
    
    def _init_firebase(self):
        """Initialize Firebase Admin SDK."""
        try:
            import firebase_admin
            from firebase_admin import credentials
            import os
            
            # Check if Firebase app already exists
            try:
                self._firebase_app = firebase_admin.get_app()
                logger.info("Firebase app already initialized, reusing existing app")
                return
            except ValueError:
                # App doesn't exist, continue with initialization
                pass
            
            # Try environment variables first (for Render deployment)
            firebase_private_key = os.getenv('FIREBASE_PRIVATE_KEY')
            if firebase_private_key:
                cred_dict = {
                    "type": os.getenv('FIREBASE_TYPE', 'service_account'),
                    "project_id": os.getenv('FIREBASE_PROJECT_ID'),
                    "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID'),
                    "private_key": firebase_private_key.replace('\\n', '\n'),
                    "client_email": os.getenv('FIREBASE_CLIENT_EMAIL'),
                    "client_id": os.getenv('FIREBASE_CLIENT_ID'),
                    "token_uri": os.getenv('FIREBASE_TOKEN_URI', 'https://oauth2.googleapis.com/token'),
                }
                cred = credentials.Certificate(cred_dict)
                self._firebase_app = firebase_admin.initialize_app(cred)
                logger.info("Firebase initialized from environment variables")
            else:
                # Fallback to JSON file (for local development)
                cred_file = getattr(settings, 'FIREBASE_CREDENTIALS_FILE', None)
                if cred_file and os.path.exists(cred_file):
                    cred = credentials.Certificate(cred_file)
                    self._firebase_app = firebase_admin.initialize_app(cred)
                    logger.info("Firebase initialized from JSON file")
                else:
                    logger.warning("No Firebase credentials found")
                    self.mock_mode = True
        except ImportError:
            logger.warning("firebase-admin not installed, running in mock mode")
            self.mock_mode = True
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            self.mock_mode = True
    
    def send_to_device(self, token, title, body, data=None, notification_type='general'):
        """
        Send a push notification to a specific device.
        
        Args:
            token: FCM device token
            title: Notification title
            body: Notification body text
            data: Optional dict of custom data payload
            notification_type: Type of notification for routing in app
            
        Returns:
            dict with status and message_id (or error)
        """
        if self.mock_mode:
            return self._mock_send(token, title, body, data, notification_type)
        
        try:
            from firebase_admin import messaging
            
            # Build data payload - merge custom data with defaults
            message_data = {
                'click_action': 'FLUTTER_NOTIFICATION_CLICK',
            }
            # Add notification_type only if not already in data
            if data and 'type' in data:
                message_data['type'] = data['type']
            else:
                message_data['type'] = notification_type
            
            # Merge all custom data
            if data:
                for key, value in data.items():
                    message_data[key] = str(value) if value is not None else ''
            
            # Build the message
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=message_data,
                token=token,
            )
            
            # Send the message
            response = messaging.send(message)
            logger.info(f"FCM notification sent: {response}, data: {message_data}")
            return {'status': 'sent', 'message_id': response}
            
        except Exception as e:
            logger.error(f"FCM send error: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    def send_to_user(self, user, title, body, data=None, notification_type='general'):
        """
        Send notification to a user using their stored FCM token.
        
        Args:
            user: User model instance
            title: Notification title
            body: Notification body
            data: Custom data payload
            notification_type: Type for app routing
            
        Returns:
            dict with status and message_id
        """
        from core.notification_models import NotificationLog
        
        # Check if user has FCM token
        if not user.fcm_token:
            logger.warning(f"User {user.id} has no FCM token registered")
            return {'status': 'skipped', 'error': 'No FCM token registered'}
        
        result = self.send_to_device(
            user.fcm_token, title, body, data, notification_type
        )
        
        # Log the notification
        NotificationLog.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            body=body,
            data=data or {},
            status='SENT' if result['status'] == 'sent' else 'FAILED',
            sent_at=timezone.now()
        )

        logger.info(f"Notification logged: {user.email} - {notification_type}")
        
        return result
    
    def _mock_send(self, token, title, body, data, notification_type):
        """Mock send for development - logs instead of sending."""
        mock_id = f"mock-{timezone.now().timestamp()}"
        
        logger.info(f"""
        ========== MOCK FCM NOTIFICATION ==========
        Token: {token[:30]}...
        Type: {notification_type}
        Title: {title}
        Body: {body}
        Data: {json.dumps(data or {}, indent=2)}
        Mock ID: {mock_id}
        ============================================
        """)
        
        return {'status': 'sent', 'message_id': mock_id, 'mock': True}
    
    # ==========================================
    # Convenience methods for specific notifications
    # ==========================================
    
    def notify_trip_assignment(self, driver, trip, stock_request):
        """Notify driver about a new trip assignment."""
        from logistics.models import Token as TripToken
        
        trip_token = TripToken.objects.filter(
            vehicle=trip.vehicle
        ).order_by('-issued_at').first()
        
        return self.send_to_user(
            user=driver.user,
            title="New Trip Assignment",
            body=f"Trip from {trip.ms.name} to {trip.dbs.name}. Tap to accept.",
            data={
                'tripId': str(trip.id),
                'stockRequestId': str(stock_request.id),
                'msName': trip.ms.name,
                'dbsName': trip.dbs.name,
                'tokenId': str(trip_token.id) if trip_token else None,
            },
            notification_type='trip_assignment'
        )
    
    def notify_dbs_arrival(self, dbs_operator, trip, driver):
        """Notify DBS operator that truck has arrived."""
        return self.send_to_user(
            user=dbs_operator,
            title="Truck Arrived at DBS",
            body=f"Vehicle {trip.vehicle.registration_no} has arrived for delivery.",
            data={
                'tripId': str(trip.id),
                'driverId': str(driver.id) if driver else None,
                'vehicleNo': trip.vehicle.registration_no,
                'msName': trip.ms.name,
            },
            notification_type='dbs_arrival'
        )
    
    def notify_ms_arrival(self, ms_operator, trip, driver):
        """Notify MS operator that truck has arrived for filling."""
        return self.send_to_user(
            user=ms_operator,
            title="Truck Arrived at MS",
            body=f"Vehicle {trip.vehicle.registration_no} ready for filling.",
            data={
                'tripId': str(trip.id),
                'driverId': str(driver.id) if driver else None,
                'vehicleNo': trip.vehicle.registration_no,
                'dbsName': trip.dbs.name,
            },
            notification_type='ms_arrival'
        )
    
    def notify_stock_approved(self, dbs_operator, stock_request):
        """Notify DBS operator that their stock request was approved."""
        qty_text = f"{stock_request.requested_qty_kg}kg" if stock_request.requested_qty_kg else "stock"
        return self.send_to_user(
            user=dbs_operator,
            title="Stock Request Approved",
            body=f"Your request for {qty_text} has been approved.",
            data={
                'stockRequestId': str(stock_request.id),
                'approvedQty': str(stock_request.requested_qty_kg) if stock_request.requested_qty_kg else 'Not Available',
            },
            notification_type='stock_approved'
        )
    
    def notify_variance_alert(self, eic_user, trip, variance_pct):
        """Alert EIC about gas variance exceeding threshold."""
        return self.send_to_user(
            user=eic_user,
            title="Variance Alert",
            body=f"Trip {trip.id} has {variance_pct:.2f}% variance (threshold: 0.5%)",
            data={
                'tripId': str(trip.id),
                'variancePct': str(variance_pct),
                'alert': 'true',
            },
            notification_type='variance_alert'
        )


# Singleton instance
notification_service = NotificationService()
