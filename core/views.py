"""
API Views for GTS
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth.hashers import make_password, check_password
from core.models import User, Role, UserRole, Station, Route, MSDBSMap
from core.serializers import (
    UserSerializer, RoleSerializer, UserRoleSerializer,
    StationSerializer, LoginSerializer, RouteSerializer, MSDBSMapSerializer,
    MPINLoginSerializer, SetMPINSerializer, ChangePasswordSerializer,
    PasswordResetRequestSerializer, PasswordResetVerifySerializer, PasswordResetConfirmSerializer
)
from core.logging_utils import log_auth_event, log_user_action
from core.sap_integration import sap_service

from core.utils import send_welcome_email, send_otp_email, send_reset_success_email
from core.models import PasswordResetSession
from core.error_response import (
    error_response, validation_error_response, not_found_response,
    unauthorized_response, forbidden_response, server_error_response
)
import uuid
import random

logger = logging.getLogger(__name__)


def snake_to_camel(snake_str):
    """Convert snake_case string to camelCase."""
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def normalize_permissions(permissions_dict):
    """
    Normalize permissions to include both snake_case and camelCase keys.
    This ensures frontend compatibility regardless of which format they use.
    
    Example: {'can_view_trips': True} becomes {'can_view_trips': True, 'canViewTrips': True}
    """
    normalized = {}
    for key, value in permissions_dict.items():
        # Keep original snake_case
        normalized[key] = value
        # Add camelCase version
        camel_key = snake_to_camel(key)
        normalized[camel_key] = value
    return normalized


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

def get_user_permissions(role_code, user=None):
    """
    Get permissions based on role code.
    Uses database-driven permissions with fallback to hardcoded defaults.
    
    Args:
        role_code: The primary role code of the user
        user: Optional User object for database permission lookup
    """
    # Default permissions structure
    default_permissions = {
        'can_submit_manual_request': False,
        'can_accept_trips': False,
        'can_confirm_arrival': False,
        'can_record_readings': False,
        'can_start_filling': False,
        'can_approve_request': False,
        'can_manage_drivers': False,
        'can_view_trips': True,  # Base permission
        'can_override_tokens': False,
        'can_manage_clusters': False,
        'can_trigger_correction_actions': False,
    }
    
    # If we have a user object, try to get permissions from database
    if user:
        try:
            from core.permission_views import get_user_permissions_from_db
            db_permissions = get_user_permissions_from_db(user)
            if db_permissions:
                return db_permissions
        except Exception as e:
            logger.warning(f"Failed to get permissions from database for user {user.id}: {e}")
    
    # Fallback to hardcoded role-based permissions
    permissions = default_permissions.copy()
    
    if role_code == 'DBS_OPERATOR':
        permissions.update({
            'can_submit_manual_request': True
        })
    elif role_code == 'MS_OPERATOR':
        # MS dashboard is default - no special permissions needed
        pass
    elif role_code == 'EIC':
        permissions.update({
            'can_manage_clusters': True,
            'can_manage_drivers': True,
            'can_trigger_correction_actions': True,
        })
    elif role_code == 'SUPER_ADMIN':
        # Super admin gets all permissions
        permissions = {key: True for key in permissions}
    elif role_code == 'SGL_TRANSPORT_VENDOR':
        permissions.update({
            'can_manage_drivers': True
        })
    elif role_code == 'DRIVER':
        # No permissions for driver
        pass
    elif role_code == 'SGL_CUSTOMER':
        permissions.update({
            'can_accept_trips': True
        })
    
    # Normalize to include both snake_case and camelCase
    return normalize_permissions(permissions)

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Unified Login endpoint (Email/Phone + Password/MPIN).
    Checks for Force Reset.
    """
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        username = serializer.validated_data['username']
        password = serializer.validated_data.get('password')
        role = serializer.validated_data.get('role')
        mpin = serializer.validated_data.get('mpin')
        
        # 1. Resolve User (Email or Phone)
        user = None
        user_input = username # Keep original input for logging
        
        if '@' not in username:
            # Assume phone, find user by phone first
            try:
                user_obj = User.objects.get(phone=username)
                username = user_obj.email # Use email for authenticate() if using password
                user = user_obj # We have the user object directly
            except User.DoesNotExist:
                # If using password, authenticate might still find it if username was actually email? 
                # But we checked '@'. So it's likely invalid user.
                pass
        else:
             # It's an email
             try:
                 user = User.objects.get(email=username)
             except User.DoesNotExist:
                 pass

        # 2. Authenticate
        auth_success = False
        login_method = 'UNKNOWN'
        
        if password:
            login_method = 'PASSWORD'
            # Use Django's authenticate which handles hashing
            # It expects 'username' (which we set to email above) and 'password'
            # Pass request._request to ensure it's a Django HttpRequest, avoiding AssertionError
            authenticated_user = authenticate(request=request._request, username=username, password=password)
            if authenticated_user:
                 user = authenticated_user
                 auth_success = True
        
        elif mpin:
            login_method = 'MPIN'
            # Verify MPIN manually
            if user:
                 if user.mpin and check_password(mpin, user.mpin):
                      auth_success = True
                 else:
                      # MPIN specific error handling could be here
                      pass
        
        if auth_success and user:
            # Success Flow
            token, created = Token.objects.get_or_create(user=user)
            
            # Check for force password reset
            reset_required = user.is_password_reset_required
            
            # Get primary role and context
            primary_role_assign = get_primary_role(user)
            role_code = primary_role_assign.role.code if primary_role_assign else None
            role_name = primary_role_assign.role.name if primary_role_assign else None
            station = primary_role_assign.station if primary_role_assign else None
            
            # Validate Role (if provided) - Case insensitive, check both code and name
            # if role:
            #     input_role = str(role).strip().upper()
            #     user_role_code = str(role_code).upper() if role_code else ''
            #     user_role_name = str(role_name).upper() if role_name else ''
                
            #     if input_role != user_role_code and input_role != user_role_name:
            #          return unauthorized_response('User role does not match')
            
            # if not role_code:   
            #     return unauthorized_response('User role or station not found')
            # Construct response
            user_data = {
                'id': user.id,
                'role': role_code,
                'name': user.full_name,
                'dbsId': station.id if station and station.type == 'DBS' else None,
                'dbsName': station.name if station and station.type == 'DBS' else None,
                'msId': station.id if station and station.type == 'MS' else None,
                'msName': station.name if station and station.type == 'MS' else None,
                'permissions': get_user_permissions(role_code, user),
                'mpin_set': bool(user.mpin) # Inform client if MPIN is set
            }
            
            # Log successful login
            ip_address = request.META.get('REMOTE_ADDR', '')
            log_auth_event(f'LOGIN_{login_method}', user.email, ip_address, True)
            
            return Response({
                'token': token.key,
                'user': user_data,
                'message': f'Login successful ({login_method})',
                'reset_required': reset_required
            })
        else:
            # Log failed login
            ip_address = request.META.get('REMOTE_ADDR', '')
            log_auth_event(f'LOGIN_{login_method}', user_input, ip_address, False, 'Invalid credentials')
            
            return unauthorized_response('Invalid credentials')
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_mpin(request):
    """
    Set or Update MPIN for the authenticated user.
    Requires current password for verification if setting for first time? 
    The serializer checks for password field.
    """
    serializer = SetMPINSerializer(data=request.data)
    if serializer.is_valid():
        password = serializer.validated_data['password']
        mpin = serializer.validated_data['mpin']
        
        user = request.user
        
        # Verify password
        if not user.check_password(password):
             return unauthorized_response('Invalid password')
        
        # Save hashed MPIN
        user.mpin = make_password(mpin)
        user.save(update_fields=['mpin'])
        
        log_user_action(user, 'UPDATE', 'User', user.id, 'Set MPIN', True)
        
        return Response({'message': 'MPIN set successfully'})
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny]) # Modified: Effectively requires auth context if no username provided, but let's handle permissive for now.
# Revised: Since login now returns token even for reset, we can rely on IsAuthenticated for simplest flow? 
# BUT `login_view` returns token. So Client will have token.
# Let's support both: Token based (no old password needed if reset required?) or Credentials based.
# User asked "do not ask old password". Assuming they are logged in.
def change_password(request):
    """
    Change password.
    Supports authenticated user (via Token).
    If authenticated, `old_password` is Optional (if we trust the active session, especially for force reset).
    Or strict: Always require old password unless `is_password_reset_required` is True?
    Let's go with: If Authenticated, old_password is OPTIONAL.
    """
    serializer = ChangePasswordSerializer(data=request.data)
    
    if serializer.is_valid():
        old_password = serializer.validated_data.get('old_password')
        new_password = serializer.validated_data['new_password']
        
        user = None
        if request.user.is_authenticated:
            user = request.user
        else:
             # Fallback for unauthenticated requests (legacy force reset flow if they didn't use token)
             username = request.data.get('username')
             if username:
                if '@' in username:
                    user = User.objects.filter(email=username).first()
                else:
                    user = User.objects.filter(phone=username).first()
        
        if not user:
             return unauthorized_response('Authentication required')

        # Verify old password ONLY if provided.
        # If NOT provided, we assume the Token/Session is sufficient proof (simpler flow requested by user).
        # We might want to enforce "Only if reset_required" for security, but user asked for simple flow.
        if old_password:
            if not user.check_password(old_password):
                return validation_error_response('Invalid old password')
        
        # Security Check: If NO old password, ensure user IS authenticated.
        if not old_password and not request.user.is_authenticated:
             return validation_error_response('Old password required for unauthenticated request')

        # Set new password
        user.set_password(new_password)
        user.is_password_reset_required = False
        
        # Set MPIN if provided
        mpin = serializer.validated_data.get('mpin')
        if mpin:
             user.mpin = make_password(mpin)
             user.save(update_fields=['password', 'is_password_reset_required', 'mpin', 'sap_last_synced_at']) # Include any others? simplified.
        else:
             user.save(update_fields=['password', 'is_password_reset_required'])
        
        log_auth_event('PASSWORD_CHANGE', user.email, request.META.get('REMOTE_ADDR', ''), True)
        
        return Response({
            'message': 'Password changed successfully. Please login with new password.',
             'mpin_set': bool(mpin)
        })
        
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
        logger.error(f"Logout error for user {request.user.email}: {str(e)}", exc_info=True)
        return server_error_response('Failed to logout. Please try again.')



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user_view(request):
    """Get current user"""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


# ==========================================
# Forgot Password Flow
# ==========================================

@api_view(['POST'])
@permission_classes([AllowAny])
def request_password_reset(request):
    """
    Step 1: User provides Email/Phone -> Send OTP.
    """
    serializer = PasswordResetRequestSerializer(data=request.data)
    if serializer.is_valid():
        username = serializer.validated_data['username']
        
        # Resolve User
        user = None
        if '@' in username:
            user = User.objects.filter(email=username).first()
        else:
            user = User.objects.filter(phone=username).first()
            
        if not user:
            # We return 200 even if user not found to prevent enumeration, 
            # OR return 404 if client UX needs it. User asked for "error msg user not found".
            return Response({'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if OTP was sent in the last 2 minutes (throttle to prevent abuse)
        recent = PasswordResetSession.objects.filter(
            user=user,
            is_used=False,
            created_at__gt=timezone.now() - timezone.timedelta(minutes=2)
        ).first()

        if recent:
            # Calculate remaining seconds
            elapsed = (timezone.now() - recent.created_at).total_seconds()
            remaining = max(0, 120 - int(elapsed))
            return Response({
                'message': 'OTP recently sent. Please wait before requesting again.',
                'resend_after_seconds': remaining
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        # Invalidate all previous active (unused, unexpired) OTP sessions for this user
        # This ensures old OTPs become invalid when a new one is requested
        PasswordResetSession.objects.filter(
            user=user,
            is_used=False,
            expires_at__gt=timezone.now()
        ).update(is_used=True)
            
        # Generate OTP
        otp = f"{random.randint(100000, 999999)}"
        
        # Create Session
        expiry = timezone.now() + timezone.timedelta(minutes=10)
        
        PasswordResetSession.objects.create(
            user=user,
            otp_code=otp,
            expires_at=expiry
        )
        
        # Send Email
        # We need to ensure we have the email to send to.
        if user.email:
            try:
                send_otp_email(user, otp)
            except Exception as e:
                logger.error(f"Failed to send OTP email: {e}")
                return Response({'message': 'Failed to send OTP email'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
             return Response({'message': 'User has no email linked for OTP'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'message': 'OTP sent to registered email',
            'resend_after_seconds': 120  # Client can use this to throttle resends
            })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_reset_otp(request):
    """
    Step 2: User provides OTP -> Verify and return Reset Token.
    """
    serializer = PasswordResetVerifySerializer(data=request.data)
    if serializer.is_valid():
        username = serializer.validated_data['username']
        otp = serializer.validated_data['otp']
        
        # Resolve User
        user = None
        if '@' in username:
            user = User.objects.filter(email=username).first()
        else:
            user = User.objects.filter(phone=username).first()
            
        if not user:
            return Response({'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
            
        # Verify OTP
        # Check for valid, unexpired, unused session matching user & otp
        session = PasswordResetSession.objects.filter(
            user=user,
            otp_code=otp,
            is_used=False,
            expires_at__gt=timezone.now()
        ).order_by('-created_at').first()
        
        if not session:
            return Response({'message': 'Invalid or expired OTP'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Valid OTP -> Generate Token
        reset_token = str(uuid.uuid4())
        session.reset_token = reset_token
        session.save()
        
        return Response({
            'message': 'OTP Verified',
            'reset_token': reset_token
        })
        
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def confirm_password_reset(request):
    """
    Step 3: User provides Reset Token + New Creds -> Reset Password & MPIN.
    """
    serializer = PasswordResetConfirmSerializer(data=request.data)
    if serializer.is_valid():
        reset_token = serializer.validated_data['reset_token']
        new_password = serializer.validated_data['new_password']
        mpin = serializer.validated_data['mpin']
        
        # Validate User & Token
        session = PasswordResetSession.objects.filter(
            reset_token=reset_token,
            is_used=False,
            expires_at__gt=timezone.now()
        ).first()
        
        if not session:
            return Response({'message': 'Invalid or expired reset token'}, status=status.HTTP_400_BAD_REQUEST)
            
        user = session.user
        
        # Update Credentials
        user.set_password(new_password)
        user.mpin = make_password(mpin)
        user.is_password_reset_required = False # Clear force reset flag if present
        user.save()
        
        # Mark session used
        session.is_used = True
        session.save()
        
        # Send Success Email
        try:
            send_reset_success_email(user)
        except Exception as e:
            logger.error(f"Failed to send success email: {e}")
            
        return Response({'message': 'Password and MPIN reset successfully'})
        
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def choose_role_view(request):
    """
    Endpoint to validate if a role exists in the system (by code or name).
    Accessible without login (AllowAny).
    """
    input_role = request.data.get('role')
    if not input_role:
        return Response({'message': 'Role is required'}, status=status.HTTP_400_BAD_REQUEST)
        
    input_role = str(input_role).strip().upper()
    
    # Check Role table for existence (Case Insensitive)
    # We check if any role matches the code OR the name
    role_exists = Role.objects.filter(
        Q(code__iexact=input_role) | Q(name__iexact=input_role)
    ).first()

    if not role_exists:
        return Response({'message': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)

    # Return success details
    return Response({
        'message': 'Role valid',
        'role_code': role_exists.code,
        'role_name': role_exists.name
    })


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for User CRUD operations"""
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = User.objects.all().order_by('-date_joined')
        
        # Search filter - search by email or full_name
        search = self.request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search) | Q(full_name__icontains=search)
            )
        
        return queryset
    
    def perform_create(self, serializer):
        # We need to capture the raw password before it's hashed in serializer.save()?
        # Actually ModelSerializer.save() calls create() which calls set_password(). 
        # But we can access the raw password from `serializer.validated_data` or `self.request.data` BEFORE save, 
        # or capture it if the serializer returns the user instance. 
        # The `UserSerializer` pops 'password' from validated_data in `create`. 
        # So we should grab it from initial_data or validated_data if still there?
        # UserSerializer.create pops it. So we need to grab it here.
        
        raw_password = serializer.validated_data.get('password') or self.request.data.get('password')
        
        user = serializer.save()
        log_user_action(
            self.request.user,
            'CREATE',
            'User',
            user.id,
            f'Created user: {user.email}',
            True
        )
        
        # Send Welcome Email
        if raw_password:
             try:
                 send_welcome_email(user, raw_password)
             except Exception as e:
                 logger.error(f"Failed to send welcome email to {user.email}: {e}", exc_info=True)

        # Note: SAP sync is now handled in UserRoleViewSet when roles are assigned
        # This prevents sending incomplete data (missing station/role)
    
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
        
        # Sync to SAP after user update
        try:
            sap_result = sap_service.sync_user_to_sap(user, operation='CREATE')
            if sap_result['success']:
                logger.info(f"User {user.email} updated in SAP successfully")
                # Update sync timestamp
                user.sap_last_synced_at = timezone.now()
                user.save(update_fields=['sap_last_synced_at'])
            else:
                logger.error(f"SAP sync failed for user {user.email}: {sap_result.get('error')}")
        except Exception as e:
            logger.error(f"SAP sync error for user {user.email}: {str(e)}", exc_info=True)
    
    def perform_destroy(self, instance):
        """Soft delete: Mark user as inactive and sync to SAP"""
        log_user_action(
            self.request.user,
            'DELETE',
            'User',
            instance.id,
            f'Deleted user: {instance.email}',
            True
        )
        
        # Soft delete: Mark as inactive instead of deleting
        instance.is_active = False
        instance.save()
        
        # Sync inactive status to SAP
        try:
            sap_result = sap_service.sync_user_to_sap(instance, operation='CREATE')
            if sap_result['success']:
                logger.info(f"User {instance.email} marked inactive in SAP successfully")
            else:
                logger.error(f"SAP sync failed for user {instance.email}: {sap_result.get('error')}")
        except Exception as e:
            logger.error(f"SAP sync error for user {instance.email}: {str(e)}", exc_info=True)
    
    @action(detail=True, methods=['post'])
    def sync_with_sap(self, request, pk=None):
        """
        Manually sync a user with SAP.
        
        POST /api/users/{id}/sync_with_sap/
        """
        user = self.get_object()
        
        try:
            sap_result = sap_service.sync_user_to_sap(user, operation='CREATE')
            
            if sap_result['success']:
                return Response({
                    'message': f'User {user.email} synced to SAP successfully',
                    'sap_response': sap_result.get('response')
                })
            else:
                return Response({
                    'message': 'SAP sync failed',
                    'error': sap_result.get('error')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"SAP sync error: {str(e)}", exc_info=True)
            return Response({
                'message': 'Unexpected error during SAP sync',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def get_from_sap(self, request, pk=None):
        """
        Retrieve user data from SAP (DISP operation).
        
        GET /api/users/{id}/get_from_sap/
        """
        user = self.get_object()
        
        try:
            sap_result = sap_service.get_user_from_sap(user.full_name or user.email.split('@')[0])
            
            if sap_result['success']:
                return Response({
                    'message': 'User data retrieved from SAP',
                    'sap_data': sap_result.get('data')
                })
            else:
                return Response({
                    'message': 'Failed to retrieve from SAP',
                    'error': sap_result.get('error')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"SAP DISP error: {str(e)}", exc_info=True)
            return Response({
                'message': 'Unexpected error during SAP DISP',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def bulk_sync_sap(self, request):
        """
        Bulk sync all users to SAP.
        
        POST /api/users/bulk_sync_sap/
        
        Optional query params:
        - user_ids: Comma-separated list of user IDs to sync
        """
        user_ids_param = request.query_params.get('user_ids', '')
        
        if user_ids_param:
            user_ids = [int(uid) for uid in user_ids_param.split(',') if uid.strip().isdigit()]
            users = User.objects.filter(id__in=user_ids)
        else:
            users = User.objects.all()
        
        results = {
            'total': users.count(),
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        for user in users:
            try:
                sap_result = sap_service.sync_user_to_sap(user, operation='CREATE')
                if sap_result['success']:
                    results['success'] += 1
                    # Update sync timestamp
                    user.sap_last_synced_at = timezone.now()
                    user.save(update_fields=['sap_last_synced_at'])
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        'user_id': user.id,
                        'email': user.email,
                        'error': sap_result.get('error')
                    })
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'user_id': user.id,
                    'email': user.email,
                    'error': str(e)
                })
        
        return Response(results)
    
    @action(detail=False, methods=['post'])
    def sync_all_with_sap(self, request):
        """
        Bidirectional sync: Compare local users with SAP and synchronize.
        - Push new/updated local users to SAP
        - Mark deleted users as inactive
        
        POST /api/users/sync_all_with_sap/
        
        Response:
        {
            'message': 'Sync completed',
            'pushed_to_sap': 5,
            'marked_inactive': 2,
            'errors': [...]
        }
        """
        results = {
            'message': 'User sync with SAP completed',
            'pushed_to_sap': 0,
            'marked_inactive': 0,
            'errors': [],
            'details': []
        }
        
        try:
            # Get all active local users
            local_users = User.objects.filter(is_active=True)
            
            # Push all active users to SAP
            for user in local_users:
                try:
                    sap_result = sap_service.sync_user_to_sap(user, operation='CREATE')
                    if sap_result['success']:
                        results['pushed_to_sap'] += 1
                        user.sap_last_synced_at = timezone.now()
                        user.save(update_fields=['sap_last_synced_at'])
                        results['details'].append({
                            'user_id': user.id,
                            'email': user.email,
                            'action': 'synced_to_sap',
                            'status': 'success'
                        })
                    else:
                        results['errors'].append({
                            'user_id': user.id,
                            'email': user.email,
                            'action': 'sync_to_sap',
                            'error': sap_result.get('error')
                        })
                except Exception as e:
                    results['errors'].append({
                        'user_id': user.id,
                        'email': user.email,
                        'action': 'sync_to_sap',
                        'error': str(e)
                    })
            
            # Note: SAP doesn't provide a list endpoint, so we can't pull deleted users
            # Inactive users are already marked in local DB
            
            return Response(results)
            
        except Exception as e:
            logger.error(f"Error during user SAP sync: {str(e)}", exc_info=True)
            return Response({
                'message': 'Sync failed',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
            f'Assigned role {user_role.role.code} to user {user_role.user.email}',
            True
        )
        
        # Sync to SAP (ensures Station/Role info is sent)
        try:
            sap_service.sync_user_to_sap(user_role.user, operation='CREATE')
        except Exception as e:
            logger.error(f"Failed to sync user-role change to SAP for user {user_role.user.email}: {e}", exc_info=True)

    def perform_update(self, serializer):
        user_role = serializer.save()
        log_user_action(
            self.request.user,
            'UPDATE',
            'UserRole',
            user_role.id,
            f'Updated role assignment for user {user_role.user.email}',
            True
        )
        
        # Sync to SAP
        try:
            sap_service.sync_user_to_sap(user_role.user, operation='CREATE')
        except Exception as e:
            logger.error(f"Failed to sync user-role update to SAP for user {user_role.user.email}: {e}", exc_info=True)


class StationViewSet(viewsets.ModelViewSet):
    """ViewSet for Station CRUD operations"""
    queryset = Station.objects.all().order_by('name')
    serializer_class = StationSerializer
    permission_classes = [IsAuthenticated]
    
    def list(self, request, *args, **kwargs):
        """
        List stations - automatically imports/syncs from SAP before returning.
        This eliminates the need for a manual 'Import from SAP' button.
        Auto-sync is throttled to once every 5 minutes to improve performance.
        """
        # Auto-sync from SAP in the background (non-blocking for the response)
        # Only sync if last sync was more than 5 minutes ago
        try:
            from django.core.cache import cache
            last_sync_key = 'stations_last_auto_sync'
            last_sync = cache.get(last_sync_key)
            
            # If no recent sync (within 5 minutes), trigger auto-import
            if not last_sync:
                self._auto_import_from_sap(request.user)
                # Set cache for 5 minutes
                cache.set(last_sync_key, timezone.now(), 300)
        except Exception as e:
            logger.warning(f"Auto-import from SAP failed (non-critical): {str(e)}")
        
        # Return the standard list response
        return super().list(request, *args, **kwargs)
    
    def _auto_import_from_sap(self, user):
        """
        Internal method to auto-import stations from SAP.
        Called automatically when listing stations.
        """
        try:
            sap_result = sap_service.get_stations_from_sap()
            
            if not sap_result.get('success'):
                logger.warning(f"Failed to get stations from SAP: {sap_result.get('error')}")
                return
            
            sap_stations = sap_result.get('stations', [])
            
            for sap_station in sap_stations:
                try:
                    station_code = sap_station.get('code')
                    station_name = sap_station.get('name')
                    station_sap_type = sap_station.get('type', '')
                    
                    if not station_code or not station_name:
                        continue
                    
                    # Map SAP type to local type
                    local_type = 'DBS' if station_sap_type == 'DB' else 'MS'
                    
                    # Check if station exists
                    existing_station = Station.objects.filter(
                        Q(sap_station_id=station_code) | Q(code=station_code)
                    ).first()
                    
                    station_data = {
                        'name': station_name,
                        'type': local_type,
                        'city': sap_station.get('city', ''),
                        'phone': sap_station.get('phone', ''),
                        'sap_station_id': station_code,
                        'sap_last_synced_at': timezone.now()
                    }
                    
                    if existing_station:
                        # Update existing station
                        for key, value in station_data.items():
                            setattr(existing_station, key, value)
                        existing_station.save()
                    else:
                        # Create new station
                        station_data['code'] = station_code
                        Station.objects.create(**station_data)
                        
                except Exception as e:
                    logger.warning(f"Error importing station {sap_station.get('code')}: {str(e)}")
                    continue
                    
            logger.info(f"Auto-imported {len(sap_stations)} stations from SAP")
            
        except Exception as e:
            logger.error(f"Auto-import from SAP error: {str(e)}", exc_info=True)
    
    def perform_create(self, serializer):
        """Create station and sync to SAP"""
        station = serializer.save()
        log_user_action(
            self.request.user,
            'CREATE',
            'Station',
            station.id,
            f'Created station: {station.code}',
            True
        )
        
        # Sync to SAP
        try:
            sap_result = sap_service.sync_station_to_sap(station, operation='CREATE')
            if sap_result['success']:
                logger.info(f"Station {station.code} synced to SAP successfully")
                station.sap_last_synced_at = timezone.now()
                station.save(update_fields=['sap_last_synced_at'])
            else:
                logger.error(f"SAP sync failed for station {station.code}: {sap_result.get('error')}")
        except Exception as e:
            logger.error(f"SAP sync error for station {station.code}: {str(e)}", exc_info=True)
    
    def perform_update(self, serializer):
        """Update station and sync to SAP"""
        station = serializer.save()
        log_user_action(
            self.request.user,
            'UPDATE',
            'Station',
            station.id,
            f'Updated station: {station.code}',
            True
        )
        
        # Sync to SAP
        try:
            sap_result = sap_service.sync_station_to_sap(station, operation='CREATE')
            if sap_result['success']:
                logger.info(f"Station {station.code} updated in SAP successfully")
                station.sap_last_synced_at = timezone.now()
                station.save(update_fields=['sap_last_synced_at'])
            else:
                logger.error(f"SAP sync failed for station {station.code}: {sap_result.get('error')}")
        except Exception as e:
            logger.error(f"SAP sync error for station {station.code}: {str(e)}", exc_info=True)
    
    @action(detail=False, methods=['post'])
    def import_from_sap(self, request):
        """
        Import stations from SAP and create/update in local database.
        
        POST /api/stations/import_from_sap/
        
        Optional query params:
        - station_type: 'MS' or 'DBS' (default: import both)
        - station_id: Specific station ID to import
        
        Response:
        {
            'message': 'Import completed',
            'created': 5,
            'updated': 3,
            'skipped': 1,
            'errors': [...]
        }
        """
        station_type = request.query_params.get('station_type', None)
        station_id = request.query_params.get('station_id', None)
        
        # Map frontend type to SAP type
        sap_type = None
        if station_type:
            if station_type.upper() == 'DBS':
                sap_type = 'DB'  # SAP uses 'DB' instead of 'DBS'
            elif station_type.upper() == 'MS':
                sap_type = 'MS'
        
        results = {
            'message': 'Station import from SAP completed',
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': [],
            'details': []
        }
        
        try:
            # Get stations from SAP
            sap_result = sap_service.get_stations_from_sap(
                station_id=station_id,
                station_type=sap_type
            )
            
            if not sap_result['success']:
                return Response({
                    'message': 'Failed to retrieve stations from SAP',
                    'error': sap_result.get('error')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            sap_stations = sap_result.get('stations', [])
            
            if not sap_stations:
                return Response({
                    'message': 'No stations found in SAP',
                    'created': 0,
                    'updated': 0,
                    'skipped': 0
                })
            
            # Process each station
            for sap_station in sap_stations:
                try:
                    station_code = sap_station.get('code')
                    station_name = sap_station.get('name')
                    station_sap_type = sap_station.get('type', '')
                    
                    if not station_code or not station_name:
                        results['skipped'] += 1
                        results['errors'].append({
                            'station': sap_station.get('id'),
                            'error': 'Missing code or name'
                        })
                        continue
                    
                    # Map SAP type to local type
                    local_type = 'DBS' if station_sap_type == 'DB' else 'MS'
                    
                    # Check if station exists
                    existing_station = Station.objects.filter(
                        Q(sap_station_id=station_code) | Q(code=station_code)
                    ).first()
                    
                    station_data = {
                        'name': station_name,
                        'type': local_type,
                        'city': sap_station.get('city', ''),
                        'phone': sap_station.get('phone', ''),
                        'sap_station_id': station_code,
                        'sap_last_synced_at': timezone.now()
                    }
                    
                    if existing_station:
                        # Update existing station
                        for key, value in station_data.items():
                            setattr(existing_station, key, value)
                        existing_station.save()
                        
                        results['updated'] += 1
                        results['details'].append({
                            'station_id': existing_station.id,
                            'code': station_code,
                            'name': station_name,
                            'action': 'updated'
                        })
                        
                        log_user_action(
                            request.user,
                            'UPDATE',
                            'Station',
                            existing_station.id,
                            f'Updated station from SAP: {station_code}',
                            True
                        )
                    else:
                        # Create new station
                        station_data['code'] = station_code
                        new_station = Station.objects.create(**station_data)
                        
                        results['created'] += 1
                        results['details'].append({
                            'station_id': new_station.id,
                            'code': station_code,
                            'name': station_name,
                            'action': 'created'
                        })
                        
                        log_user_action(
                            request.user,
                            'CREATE',
                            'Station',
                            new_station.id,
                            f'Imported station from SAP: {station_code}',
                            True
                        )
                    
                except Exception as e:
                    results['errors'].append({
                        'station': sap_station.get('code'),
                        'error': str(e)
                    })
                    logger.error(f"Error importing station {sap_station.get('code')}: {str(e)}", exc_info=True)
            
            return Response(results)
            
        except Exception as e:
            logger.error(f"Error during station import: {str(e)}", exc_info=True)
            return Response({
                'message': 'Import failed',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def sync_to_sap(self, request):
        """
        Push all local stations to SAP.
        
        POST /api/stations/sync_to_sap/
        
        Optional query params:
        - station_ids: Comma-separated list of station IDs to sync
        
        Response:
        {
            'message': 'Sync completed',
            'success': 10,
            'failed': 2,
            'errors': [...]
        }
        """
        station_ids_param = request.query_params.get('station_ids', '')
        
        if station_ids_param:
            station_ids = [int(sid) for sid in station_ids_param.split(',') if sid.strip().isdigit()]
            stations = Station.objects.filter(id__in=station_ids)
        else:
            stations = Station.objects.all()
        
        results = {
            'message': 'Station sync to SAP completed',
            'total': stations.count(),
            'success': 0,
            'failed': 0,
            'errors': [],
            'details': []
        }
        
        for station in stations:
            try:
                sap_result = sap_service.sync_station_to_sap(station, operation='CREATE')
                if sap_result['success']:
                    results['success'] += 1
                    station.sap_last_synced_at = timezone.now()
                    station.save(update_fields=['sap_last_synced_at'])
                    results['details'].append({
                        'station_id': station.id,
                        'code': station.code,
                        'status': 'success'
                    })
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        'station_id': station.id,
                        'code': station.code,
                        'error': sap_result.get('error')
                    })
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'station_id': station.id,
                    'code': station.code,
                    'error': str(e)
                })
        
        return Response(results)
    
    @action(detail=False, methods=['post'])
    def sync_all_with_sap(self, request):
        """
        Bidirectional sync: Import from SAP and push local changes.
        - Import new/updated stations from SAP
        - Push local stations to SAP
        - Remove stations that exist locally but not in SAP (optional)
        
        POST /api/stations/sync_all_with_sap/
        
        Request body (optional):
        {
            'remove_deleted': false  // Whether to delete local stations not in SAP
        }
        
        Response:
        {
            'message': 'Bidirectional sync completed',
            'imported_from_sap': {'created': 5, 'updated': 3},
            'pushed_to_sap': {'success': 10, 'failed': 1},
            'removed_local': 2,
            'errors': [...]
        }
        """
        remove_deleted = request.data.get('remove_deleted', False)
        
        results = {
            'message': 'Bidirectional station sync completed',
            'imported_from_sap': {'created': 0, 'updated': 0, 'skipped': 0},
            'pushed_to_sap': {'success': 0, 'failed': 0},
            'removed_local': 0,
            'errors': []
        }
        
        try:
            # Step 1: Import from SAP
            logger.info("Starting SAP import...")
            sap_result = sap_service.get_stations_from_sap()
            
            if not sap_result['success']:
                results['errors'].append({
                    'step': 'import_from_sap',
                    'error': sap_result.get('error')
                })
            else:
                sap_stations = sap_result.get('stations', [])
                sap_station_codes = set()
                
                # Process SAP stations
                for sap_station in sap_stations:
                    try:
                        station_code = sap_station.get('code')
                        station_name = sap_station.get('name')
                        station_sap_type = sap_station.get('type', '')
                        
                        if not station_code or not station_name:
                            results['imported_from_sap']['skipped'] += 1
                            continue
                        
                        sap_station_codes.add(station_code)
                        local_type = 'DBS' if station_sap_type == 'DB' else 'MS'
                        
                        existing_station = Station.objects.filter(
                            Q(sap_station_id=station_code) | Q(code=station_code)
                        ).first()
                        
                        station_data = {
                            'name': station_name,
                            'type': local_type,
                            'city': sap_station.get('city', ''),
                            'phone': sap_station.get('phone', ''),
                            'sap_station_id': station_code,
                            'sap_last_synced_at': timezone.now()
                        }
                        
                        if existing_station:
                            for key, value in station_data.items():
                                setattr(existing_station, key, value)
                            existing_station.save()
                            results['imported_from_sap']['updated'] += 1
                        else:
                            station_data['code'] = station_code
                            Station.objects.create(**station_data)
                            results['imported_from_sap']['created'] += 1
                        
                    except Exception as e:
                        results['errors'].append({
                            'step': 'import_station',
                            'station': sap_station.get('code'),
                            'error': str(e)
                        })
                
                # Step 2: Remove deleted stations (if requested)
                if remove_deleted and sap_station_codes:
                    deleted_stations = Station.objects.exclude(
                        Q(sap_station_id__in=sap_station_codes) | Q(code__in=sap_station_codes)
                    ).filter(sap_station_id__isnull=False)
                    
                    deleted_count = deleted_stations.count()
                    deleted_stations.delete()
                    results['removed_local'] = deleted_count
            
            # Step 3: Push local stations to SAP
            logger.info("Starting push to SAP...")
            local_stations = Station.objects.all()
            
            for station in local_stations:
                try:
                    sap_result = sap_service.sync_station_to_sap(station, operation='CREATE')
                    if sap_result['success']:
                        results['pushed_to_sap']['success'] += 1
                        station.sap_last_synced_at = timezone.now()
                        station.save(update_fields=['sap_last_synced_at'])
                    else:
                        results['pushed_to_sap']['failed'] += 1
                        results['errors'].append({
                            'step': 'push_to_sap',
                            'station_id': station.id,
                            'code': station.code,
                            'error': sap_result.get('error')
                        })
                except Exception as e:
                    results['pushed_to_sap']['failed'] += 1
                    results['errors'].append({
                        'step': 'push_to_sap',
                        'station_id': station.id,
                        'code': station.code,
                        'error': str(e)
                    })
            
            return Response(results)
            
        except Exception as e:
            logger.error(f"Error during bidirectional sync: {str(e)}", exc_info=True)
            return Response({
                'message': 'Sync failed',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
    Supports multiple devices per user.
    Works for all user roles (Driver, DBS Operator, MS Operator, EIC, etc.)
    
    POST /api/notifications/register-token
    
    Request Body:
    {
        "deviceToken": "firebase-token-string",
        "platform": "android" // Optional: android/ios/web
    }
    
    Response:
    {
        "message": "FCM token registered successfully",
        "user_id": 1,
        "user_name": "John Doe",
        "device_id": 123
    }
    """
    from core.notification_models import DeviceToken
    
    try:
        device_token = request.data.get('deviceToken')
        platform = request.data.get('platform', 'unknown')
        
        # Validate deviceToken
        if not device_token:
            logger.warning(f"FCM token registration failed: deviceToken is missing for user {request.user.email}")
            return validation_error_response('deviceToken is required')
        
        # Validate deviceToken is a non-empty string
        if not isinstance(device_token, str) or not device_token.strip():
            logger.warning(f"FCM token registration failed: invalid deviceToken format for user {request.user.email}")
            return validation_error_response('deviceToken must be a valid non-empty string')
        
        device_token = device_token.strip()
        user = request.user
        
        # Determine device type from user's primary role
        primary_role = get_primary_role(user)
        device_type = 'GENERAL'
        if primary_role:
            role_code = primary_role.role.code
            if role_code == 'DRIVER':
                device_type = 'DRIVER'
            elif role_code == 'MS_OPERATOR':
                device_type = 'MS'
            elif role_code == 'DBS_OPERATOR':
                device_type = 'DBS'
            elif role_code == 'EIC':
                device_type = 'EIC'
        
        # Register or update device token
        try:
            token_obj, created = DeviceToken.objects.update_or_create(
                token=device_token,
                defaults={
                    'user': user,
                    'device_type': device_type,
                    'platform': platform,
                    'is_active': True
                }
            )
        except Exception as db_error:
            logger.error(f"Database error while registering FCM token for user {user.email}: {str(db_error)}", exc_info=True)
            return server_error_response('Failed to save device token. Please try again.')

        if created:
            logger.info(f"Registered new FCM token for user {user.email} on device {device_type}")
        else:
            logger.info(f"Updated FCM token for user {user.email} on device {device_type}")
        
        return Response({
            'message': f"FCM token {'registered' if created else 'updated'} successfully",
            'user_id': user.id,
            'user_name': user.full_name,
            'device_id': token_obj.id,
            'device_type': device_type
        })
    
    except Exception as e:
        logger.error(f"Unexpected error in register_fcm_token: {str(e)}", exc_info=True)
        return server_error_response('An unexpected error occurred. Please try again.')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def unregister_fcm_token(request):
    """
    Unregister FCM token (logout from notifications).
    Deactivates the specific device token.
    
    POST /api/notifications/unregister-token
    
    Request Body:
    {
        "deviceToken": "firebase-token-string" // Optional: if not provided, deactivates all user's tokens
    }
    """
    from core.notification_models import DeviceToken
    
    device_token = request.data.get('deviceToken')
    user = request.user
    
    try:
        if device_token:
            # Deactivate specific device
            logger.info(f"Unregistering specific FCM token for user {user.email} (ID: {user.id})")
            
            count = DeviceToken.objects.filter(
                user=user,
                token=device_token
            ).update(is_active=False)
            
            if count > 0:
                message = "Device token deactivated"
                logger.info(f"Successfully deactivated FCM token for user {user.email}")
            else:
                message = "Token not found"
                logger.warning(f"FCM token not found for user {user.email} - token may have already been removed")
        else:
            # Deactivate all user's devices (logout from all)
            logger.info(f"Unregistering ALL FCM tokens for user {user.email} (ID: {user.id})")
            
            count = DeviceToken.objects.filter(user=user).update(is_active=False)
            message = f"{count} device(s) deactivated"
            
            logger.info(f"Successfully deactivated {count} FCM token(s) for user {user.email}")
        
        return Response({
            'message': message,
            'deactivated_count': count
        })
    
    except Exception as e:
        logger.error(f"Error unregistering FCM token for user {user.email}: {str(e)}", exc_info=True)
        return server_error_response('Failed to unregister device token. Please try again.')


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
        return validation_error_response('user_id is required')
    if not title:
        return validation_error_response('title is required')
    if not body:
        return validation_error_response('body is required')
    
    try:
        target_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return not_found_response('User not found')
    
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
