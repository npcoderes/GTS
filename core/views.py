"""
API Views for GTS
"""
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from core.models import User, Role, UserRole, Station, Route, MSDBSMap
from core.serializers import (
    UserSerializer, RoleSerializer, UserRoleSerializer,
    StationSerializer, LoginSerializer, RouteSerializer, MSDBSMapSerializer
)
from core.logging_utils import log_auth_event, log_user_action


def get_primary_role(user):
    """
    Determine primary role for user login context.
    Priority: SUPER_ADMIN > EIC > MS_OPERATOR > DBS_OPERATOR > VENDOR > DRIVER
    """
    roles = user.user_roles.filter(active=True).select_related('role', 'station')
    role_map = {ur.role.code: ur for ur in roles}
    
    priority_order = ['SUPER_ADMIN', 'EIC', 'MS_OPERATOR', 'DBS_OPERATOR', 'VENDOR', 'DRIVER']
    
    for code in priority_order:
        if code in role_map:
            return role_map[code]
    
    return roles.first() if roles.exists() else None

def get_user_permissions(role_code):
    """
    Get permissions based on role code (from BPB)
    """
    permissions = {
        'can_raise_manual_request': False,
        'can_confirm_arrival': False,
        'can_record_readings': False,
        'can_start_filling': False,
        'can_approve_request': False,
        'can_manage_drivers': False,
        'can_view_trips': True, # Base permission
        'can_override_tokens': False
    }
    
    if role_code == 'DBS_OPERATOR':
        permissions.update({
            'can_raise_manual_request': True,
            'can_confirm_arrival': True,
            'can_record_readings': True
        })
    elif role_code == 'MS_OPERATOR':
        permissions.update({
            'can_confirm_arrival': True,
            'can_record_readings': True,
            'can_start_filling': True
        })
    elif role_code == 'EIC':
        permissions.update({
            'can_approve_request': True,
            'can_manage_drivers': True,
            'can_override_tokens': True,
            'can_manage_clusters': True,
        })
    elif role_code == 'VENDOR':
        permissions.update({
            'can_manage_drivers': True
        })
    elif role_code == 'DRIVER':
        permissions.update({
            'can_confirm_arrival': True
        })
        
    return permissions

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Login endpoint with enhanced response"""
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        user = authenticate(request, username=email, password=password)
        
        if user:
            token, created = Token.objects.get_or_create(user=user)
            
            # Get primary role and context
            primary_role_assign = get_primary_role(user)
            role_code = primary_role_assign.role.code if primary_role_assign else 'GUEST'
            station = primary_role_assign.station if primary_role_assign else None
            
            # Construct response
            user_data = {
                'id': user.id,
                'role': role_code,
                'name': user.full_name,
                'dbsId': station.id if station and station.type == 'DBS' else None,
                'dbsName': station.name if station and station.type == 'DBS' else None,
                'msId': station.id if station and station.type == 'MS' else None,
                'msName': station.name if station and station.type == 'MS' else None,
                'permissions': get_user_permissions(role_code)
            }
            
            # Log successful login
            ip_address = request.META.get('REMOTE_ADDR', '')
            log_auth_event('LOGIN', email, ip_address, True)
            
            return Response({
                'token': token.key,
                'user': user_data,
                'message': 'Login successful'
            })
        else:
            # Log failed login
            ip_address = request.META.get('REMOTE_ADDR', '')
            log_auth_event('LOGIN', email, ip_address, False, 'Invalid credentials')
            
            return Response({
                'message': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Logout endpoint"""
    try:
        # Delete the token
        request.user.auth_token.delete()
        
        # Log logout
        ip_address = request.META.get('REMOTE_ADDR', '')
        log_auth_event('LOGOUT', request.user.email, ip_address, True)
        
        return Response({'message': 'Logged out successfully'})
    except Exception as e:
        return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user_view(request):
    """Get current user"""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def choose_role_view(request):
    """
    Endpoint for user to select their active role context.
    For now, this is stateless and just logs/validates the choice.
    """
    role_code = request.data.get('role')
    if not role_code:
        return Response({'error': 'Role code required'}, status=status.HTTP_400_BAD_REQUEST)
        
    # Verify user has this role
    if not request.user.user_roles.filter(role__code=role_code, active=True).exists():
        return Response({'error': 'Invalid role for user'}, status=status.HTTP_403_FORBIDDEN)

    # In a stateful session, we would save this. 
    # For stateless JWT, the client just needs to know it's valid.
    return Response({'status': 'role_selected', 'role': role_code})


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for User CRUD operations"""
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        user = serializer.save()
        log_user_action(
            self.request.user,
            'CREATE',
            'User',
            user.id,
            f'Created user: {user.email}',
            True
        )
    
    def perform_update(self, serializer):
        user = serializer.save()
        log_user_action(
            self.request.user,
            'UPDATE',
            'User',
            user.id,
            f'Updated user: {user.email}',
            True
        )
    
    def perform_destroy(self, instance):
        log_user_action(
            self.request.user,
            'DELETE',
            'User',
            instance.id,
            f'Deleted user: {instance.email}',
            True
        )
        instance.delete()


class RoleViewSet(viewsets.ModelViewSet):
    """ViewSet for Role CRUD operations"""
    queryset = Role.objects.all().order_by('name')
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]


class UserRoleViewSet(viewsets.ModelViewSet):
    """ViewSet for UserRole CRUD operations"""
    queryset = UserRole.objects.all().order_by('-created_at')
    serializer_class = UserRoleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user_id = self.request.query_params.get('user', None)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        return queryset
    
    def perform_create(self, serializer):
        user_role = serializer.save()
        log_user_action(
            self.request.user,
            'CREATE',
            'UserRole',
            user_role.id,
            f'Assigned role {user_role.role.name} to user {user_role.user.email}',
            True
        )


class StationViewSet(viewsets.ModelViewSet):
    """ViewSet for Station CRUD operations"""
    queryset = Station.objects.all().order_by('name')
    serializer_class = StationSerializer
    permission_classes = [IsAuthenticated]


class RouteViewSet(viewsets.ModelViewSet):
    """ViewSet for Route CRUD operations"""
    queryset = Route.objects.all().order_by('name')
    serializer_class = RouteSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        ms_id = self.request.query_params.get('ms', None)
        dbs_id = self.request.query_params.get('dbs', None)
        is_active = self.request.query_params.get('is_active', None)
        
        if ms_id:
            queryset = queryset.filter(ms_id=ms_id)
        if dbs_id:
            queryset = queryset.filter(dbs_id=dbs_id)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
            
        return queryset


class MSDBSMapViewSet(viewsets.ModelViewSet):
    """ViewSet for MS-DBS Map CRUD operations"""
    queryset = MSDBSMap.objects.all().order_by('ms__name', 'dbs__name')
    serializer_class = MSDBSMapSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        ms_id = self.request.query_params.get('ms', None)
        dbs_id = self.request.query_params.get('dbs', None)
        active = self.request.query_params.get('active', None)
        
        if ms_id:
            queryset = queryset.filter(ms_id=ms_id)
        if dbs_id:
            queryset = queryset.filter(dbs_id=dbs_id)
        if active is not None:
            queryset = queryset.filter(active=active.lower() == 'true')
            
        return queryset


# ==========================================
# FCM Token Registration
# ==========================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def register_fcm_token(request):
    """
    Register FCM token for push notifications.
    Works for all user roles (Driver, DBS Operator, MS Operator, EIC, etc.)
    
    POST /api/notifications/register-token
    
    Request Body:
    {
        "deviceToken": "firebase-token-string"
    }
    
    Response:
    {
        "message": "FCM token registered successfully",
        "user_id": 1,
        "user_name": "John Doe"
    }
    """
    device_token = request.data.get('deviceToken')
    
    if not device_token:
        return Response(
            {'error': 'deviceToken is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Update the user's FCM token
    user = request.user
    user.fcm_token = device_token
    user.save(update_fields=['fcm_token'])
    
    return Response({
        'message': 'FCM token registered successfully',
        'user_id': user.id,
        'user_name': user.full_name
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def unregister_fcm_token(request):
    """
    Unregister FCM token (logout from notifications).
    
    POST /api/notifications/unregister-token
    """
    user = request.user
    user.fcm_token = None
    user.save(update_fields=['fcm_token'])
    
    return Response({
        'message': 'FCM token unregistered successfully'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_notification(request):
    """
    Send push notification to a user.
    
    POST /api/notifications/send
    
    Request Body:
    {
        "user_id": 1,           // Target user ID
        "title": "Hello",       // Notification title
        "body": "Test message", // Notification body
        "data": {},             // Optional: extra data payload
        "type": "general"       // Optional: notification type
    }
    
    Response:
    {
        "status": "sent",
        "message_id": "abc123"
    }
    """
    from core.notification_service import notification_service
    
    user_id = request.data.get('user_id')
    title = request.data.get('title')
    body = request.data.get('body')
    data = request.data.get('data', {})
    notification_type = request.data.get('type', 'general')
    
    if not user_id:
        return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not title:
        return Response({'error': 'title is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not body:
        return Response({'error': 'body is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        target_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if not target_user.fcm_token:
        return Response({
            'status': 'skipped',
            'error': 'User has no FCM token registered'
        })
    
    result = notification_service.send_to_user(
        user=target_user,
        title=title,
        body=body,
        data=data,
        notification_type=notification_type
    )
    
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_notification_to_me(request):
    """
    Send push notification to yourself (for testing).
    
    POST /api/notifications/send-to-me
    
    Request Body:
    {
        "title": "Test",
        "body": "This is a test notification"
    }
    """
    from core.notification_service import notification_service
    
    title = request.data.get('title', 'Test Notification')
    body = request.data.get('body', 'This is a test message')
    data = request.data.get('data', {})
    
    user = request.user
    
    if not user.fcm_token:
        return Response({
            'status': 'error',
            'message': 'You have no FCM token registered. Please register first.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    result = notification_service.send_to_user(
        user=user,
        title=title,
        body=body,
        data=data,
        notification_type='test'
    )
    
    return Response(result)
