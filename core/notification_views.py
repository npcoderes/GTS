"""
Notification API Views for GTS Backend
Handles device token registration and unregistration for push notifications.
"""
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from core.models import User
from core.notification_models import DeviceToken


class DriverNotificationRegisterView(views.APIView):
    """
    POST /driver/notifications/register
    Register a device token for driver push notifications.
    
    Request: { userId: number, deviceToken: string, platform?: string }
    Response: { status: 'registered', message: string }
    """
    permission_classes = [AllowAny]  # Token sent before full auth in some flows
    
    def post(self, request):
        user_id = request.data.get('userId')
        device_token = request.data.get('deviceToken')
        platform = request.data.get('platform', 'unknown')
        
        if not user_id or not device_token:
            return Response(
                {'error': 'userId and deviceToken are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = get_object_or_404(User, id=user_id)
            
            # Update or create device token
            token_obj, created = DeviceToken.objects.update_or_create(
                token=device_token,
                defaults={
                    'user': user,
                    'device_type': 'DRIVER',
                    'platform': platform,
                    'is_active': True
                }
            )
            
            return Response({
                'status': 'registered',
                'message': f"Device token {'created' if created else 'updated'} for driver",
                'tokenId': token_obj.id
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DriverNotificationUnregisterView(views.APIView):
    """
    POST /driver/notifications/unregister
    Unregister a device token (on logout or token refresh).
    
    Request: { userId: number, deviceToken: string }
    Response: { status: 'unregistered', message: string }
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        user_id = request.data.get('userId')
        device_token = request.data.get('deviceToken')
        
        if not device_token:
            return Response(
                {'error': 'deviceToken is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Deactivate the token (or delete if preferred)
            count = DeviceToken.objects.filter(token=device_token).update(is_active=False)
            
            return Response({
                'status': 'unregistered',
                'message': f"Device token deactivated" if count > 0 else "Token not found"
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DBSNotificationRegisterView(views.APIView):
    """
    POST /dbs/notifications/register
    Register a device token for DBS operator notifications.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        user_id = request.data.get('userId')
        device_token = request.data.get('deviceToken')
        platform = request.data.get('platform', 'unknown')
        
        if not user_id or not device_token:
            return Response(
                {'error': 'userId and deviceToken are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = get_object_or_404(User, id=user_id)
            
            token_obj, created = DeviceToken.objects.update_or_create(
                token=device_token,
                defaults={
                    'user': user,
                    'device_type': 'DBS',
                    'platform': platform,
                    'is_active': True
                }
            )
            
            return Response({
                'status': 'registered',
                'message': f"Device token {'created' if created else 'updated'} for DBS operator",
                'tokenId': token_obj.id
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DBSNotificationUnregisterView(views.APIView):
    """
    POST /dbs/notifications/unregister
    Unregister a DBS operator device token.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        device_token = request.data.get('deviceToken')
        
        if not device_token:
            return Response(
                {'error': 'deviceToken is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            count = DeviceToken.objects.filter(token=device_token).update(is_active=False)
            
            return Response({
                'status': 'unregistered',
                'message': f"Device token deactivated" if count > 0 else "Token not found"
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MSNotificationRegisterView(views.APIView):
    """
    POST /ms/notifications/register
    Register a device token for MS operator notifications.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        user_id = request.data.get('userId')
        device_token = request.data.get('deviceToken')
        platform = request.data.get('platform', 'unknown')
        
        if not user_id or not device_token:
            return Response(
                {'error': 'userId and deviceToken are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = get_object_or_404(User, id=user_id)
            
            token_obj, created = DeviceToken.objects.update_or_create(
                token=device_token,
                defaults={
                    'user': user,
                    'device_type': 'MS',
                    'platform': platform,
                    'is_active': True
                }
            )
            
            return Response({
                'status': 'registered',
                'message': f"Device token {'created' if created else 'updated'} for MS operator",
                'tokenId': token_obj.id
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MSNotificationUnregisterView(views.APIView):
    """
    POST /ms/notifications/unregister
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        device_token = request.data.get('deviceToken')
        
        if not device_token:
            return Response(
                {'error': 'deviceToken is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            count = DeviceToken.objects.filter(token=device_token).update(is_active=False)
            
            return Response({
                'status': 'unregistered',
                'message': f"Device token deactivated" if count > 0 else "Token not found"
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
