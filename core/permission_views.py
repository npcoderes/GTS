"""
Permission Views for GTS
Handles API endpoints for permission management.
"""

from rest_framework import viewsets, status, views
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .permission_models import Permission, RolePermission, UserPermission, StationPermission, DEFAULT_ROLE_PERMISSIONS
from .permission_serializers import (
    PermissionSerializer,
    RolePermissionSerializer, RolePermissionCreateSerializer,
    UserPermissionSerializer, UserPermissionCreateSerializer,
    StationPermissionSerializer, StationPermissionCreateSerializer,
    RoleWithPermissionsSerializer
)
from .models import Role, User
from .error_response import validation_error_response, not_found_response


def snake_to_camel(snake_str):
    """Convert snake_case string to camelCase."""
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def normalize_permissions(permissions_dict):
    """
    Normalize permissions to include both snake_case and camelCase keys.
    This ensures frontend compatibility regardless of which format they use.
    """
    normalized = {}
    for key, value in permissions_dict.items():
        normalized[key] = value
        camel_key = snake_to_camel(key)
        normalized[camel_key] = value
    return normalized


def notify_user_permission_change(user_id):
    """
    Send WebSocket notification to a specific user about permission changes.
    """
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{user_id}",
            {
                'type': 'permission.update',
                'data': {
                    'event_type': 'permissions_changed',
                    'message': 'Your permissions have been updated. Please refresh.',
                    'timestamp': str(timezone.now())
                }
            }
        )
    except Exception as e:
        # Log but don't fail the request if WebSocket fails
        print(f"WebSocket notification failed for user {user_id}: {e}")


def notify_role_users_permission_change(role):
    """
    Send WebSocket notification to all users with a specific role about permission changes.
    """
    try:
        # Get all users with this role (active role assignments)
        from core.models import UserRole
        user_ids = UserRole.objects.filter(
            role=role,
            active=True
        ).values_list('user_id', flat=True)

        channel_layer = get_channel_layer()
        for user_id in user_ids:
            async_to_sync(channel_layer.group_send)(
                f"user_{user_id}",
                {
                    'type': 'permission.update',
                    'data': {
                        'event_type': 'permissions_changed',
                        'message': f'Your role ({role.name}) permissions have been updated. Please refresh.',
                        'role': role.code,
                        'timestamp': str(timezone.now())
                    }
                }
            )
    except Exception as e:
        # Log but don't fail the request if WebSocket fails
        print(f"WebSocket notification failed for role {role.code}: {e}")


def get_user_permissions_from_db(user):
    """
    Get computed permissions for a user.
    
    Logic:
    1. Start with empty dict
    2. Apply role-based permissions (from all active roles)
    3. Apply user-specific overrides (takes precedence)
    4. Return only granted permissions (true values)
    
    Returns dict of {permission_code: bool} with only granted permissions or None if tables don't exist
    """
    try:
        # Start with empty result - only add granted permissions
        result = {}
        
        # Get user's active role codes
        user_role_codes = list(user.user_roles.filter(active=True).values_list('role__code', flat=True))
        
        # Apply role-based permissions from database
        role_perms = RolePermission.objects.filter(
            role__code__in=user_role_codes,
            granted=True
        ).select_related('permission').values_list('permission__code', flat=True)
        
        for perm_code in role_perms:
            result[perm_code] = True
        
        # If no database permissions found, fall back to hardcoded defaults
        # This ensures backward compatibility during migration
        if not role_perms.exists():
            for role_code in user_role_codes:
                if role_code in DEFAULT_ROLE_PERMISSIONS:
                    for perm_code in DEFAULT_ROLE_PERMISSIONS[role_code]:
                        result[perm_code] = True
        
        # Apply user-specific overrides
        user_perms = UserPermission.objects.filter(user=user).select_related('permission')
        for up in user_perms:
            if up.granted:
                result[up.permission.code] = True
            else:
                # If explicitly revoked, remove from result
                result.pop(up.permission.code, None)
        
        # Normalize to include both snake_case and camelCase
        return normalize_permissions(result)
    except Exception:
        # Table doesn't exist (migrations not run), return None to trigger fallback
        return None


def station_has_scada(station):
    """
    Check if a station has SCADA capability enabled.
    
    Args:
        station: Station object to check
        
    Returns:
        bool: True if the station has SCADA permission granted, False otherwise
    """
    if not station:
        return False
    
    try:
        # Check if the station has the 'station_has_scada' permission granted
        scada_perm = StationPermission.objects.filter(
            station=station,
            permission__code='station_has_scada',
            granted=True
        ).exists()
        return scada_perm
    except Exception:
        # Table doesn't exist or other error
        return False


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_permissions_view(request):
    """
    GET /api/auth/permissions/
    
    Returns the logged-in user's computed permissions based on:
    1. Their role(s)' default permissions
    2. Any user-specific permission overrides
    
    Response:
    {
        "permissions": {
            "can_raise_manual_request": false,
            "can_confirm_arrival": true,
            ...
        }
    }
    """
    permissions = get_user_permissions_from_db(request.user)
    return Response({'permissions': permissions})


class PermissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Permission CRUD operations.
    Only Super Admins should be able to create/update/delete permissions.
    """
    queryset = Permission.objects.all().order_by('category', 'name')
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # Filter by platform (dashboard, mobile, or all)
        platform = self.request.query_params.get('platform')
        if platform and platform != 'all':
            # Include permissions for the specific platform + 'all' platform permissions
            queryset = queryset.filter(platform__in=[platform, 'all'])
        
        return queryset


class RolePermissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for RolePermission CRUD operations.
    Manages default permissions for roles.
    """
    queryset = RolePermission.objects.all().select_related('role', 'permission')
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Disable pagination to return all records for count calculation
    
    def get_serializer_class(self):
        if self.action in ['create']:
            return RolePermissionCreateSerializer
        return RolePermissionSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by role
        role_id = self.request.query_params.get('role')
        if role_id:
            queryset = queryset.filter(role_id=role_id)
        
        # Filter by role code
        role_code = self.request.query_params.get('role_code')
        if role_code:
            queryset = queryset.filter(role__code=role_code)
        
        # Filter by permission
        permission_id = self.request.query_params.get('permission')
        if permission_id:
            queryset = queryset.filter(permission_id=permission_id)
        
        return queryset
    
    @action(detail=False, methods=['post'], url_path='bulk-update')
    def bulk_update(self, request):
        """
        Bulk update role permissions.
        
        POST /api/role-permissions/bulk-update/
        {
            "role_id": 1,
            "permissions": {
                "can_raise_manual_request": true,
                "can_confirm_arrival": false
            }
        }
        """
        role_id = request.data.get('role_id')
        permissions_data = request.data.get('permissions', {})
        
        if not role_id:
            return validation_error_response('role_id is required')
        
        try:
            role = Role.objects.get(id=role_id)
        except Role.DoesNotExist:
            return not_found_response('Role not found')
        
        updated = []
        created = []
        
        for perm_code, granted in permissions_data.items():
            try:
                permission = Permission.objects.get(code=perm_code)
            except Permission.DoesNotExist:
                continue
            
            role_perm, was_created = RolePermission.objects.update_or_create(
                role=role,
                permission=permission,
                defaults={'granted': granted}
            )
            
            if was_created:
                created.append(perm_code)
            else:
                updated.append(perm_code)

        # Notify all users with this role about permission changes
        notify_role_users_permission_change(role)

        return Response({
            'success': True,
            'role': role.code,
            'created': created,
            'updated': updated
        })

    @action(detail=False, methods=['get'], url_path='matrix')
    def matrix(self, request):
        """
        Get ALL permissions with their status for a specific role.
        Useful for UI toggles to show both enabled and disabled permissions.
        
        GET /api/role-permissions/matrix/?role_id=1
        """
        role_id = request.query_params.get('role_id')
        if not role_id:
            return validation_error_response('role_id is required')
            
        # Get all permissions first
        all_perms = Permission.objects.all().order_by('platform', 'name')
        
        # Get existing role permissions
        role_perms = RolePermission.objects.filter(role_id=role_id)
        granted_map = {rp.permission.code: rp.granted for rp in role_perms}
        
        result = []
        for perm in all_perms:
            result.append({
                'code': perm.code,
                'name': perm.name,
                'description': perm.description,
                'category': perm.category,
                'platform': perm.platform,
                'granted': granted_map.get(perm.code, False)  # Default to False if not found
            })
            
        return Response(result)


class UserPermissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for UserPermission CRUD operations.
    Manages user-specific permission overrides.
    """
    queryset = UserPermission.objects.all().select_related('user', 'permission', 'created_by')
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Disable pagination to return all records
    
    def get_serializer_class(self):
        if self.action in ['create']:
            return UserPermissionCreateSerializer
        return UserPermissionSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by user
        user_id = self.request.query_params.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Filter by permission
        permission_id = self.request.query_params.get('permission')
        if permission_id:
            queryset = queryset.filter(permission_id=permission_id)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['post'], url_path='bulk-update')
    def bulk_update(self, request):
        """
        Bulk update user permissions.
        
        POST /api/user-permissions/bulk-update/
        {
            "user_id": 1,
            "permissions": {
                "can_raise_manual_request": true,
                "can_confirm_arrival": null  // null to remove override
            }
        }
        """
        user_id = request.data.get('user_id')
        permissions_data = request.data.get('permissions', {})
        
        if not user_id:
            return validation_error_response('user_id is required')
        
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return not_found_response('User not found')
        
        updated = []
        created = []
        deleted = []
        
        for perm_code, granted in permissions_data.items():
            try:
                permission = Permission.objects.get(code=perm_code)
            except Permission.DoesNotExist:
                continue
            
            if granted is None:
                # Remove override
                deleted_count, _ = UserPermission.objects.filter(
                    user=target_user,
                    permission=permission
                ).delete()
                if deleted_count > 0:
                    deleted.append(perm_code)
            else:
                user_perm, was_created = UserPermission.objects.update_or_create(
                    user=target_user,
                    permission=permission,
                    defaults={'granted': granted, 'created_by': request.user}
                )
                
                if was_created:
                    created.append(perm_code)
                else:
                    updated.append(perm_code)

        # Notify the user about their permission changes
        notify_user_permission_change(user_id)

        return Response({
            'success': True,
            'user_id': user_id,
            'created': created,
            'updated': updated,
            'deleted': deleted
        })


class RoleListWithPermissionsView(views.APIView):
    """
    GET /api/roles-with-permissions/
    
    Returns all roles with their permission settings.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        roles = Role.objects.all().order_by('name')
        serializer = RoleWithPermissionsSerializer(roles, many=True)
        return Response(serializer.data)


class StationPermissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for StationPermission CRUD operations.
    Manages station-specific permissions.
    """
    queryset = StationPermission.objects.all().select_related('station', 'permission')
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Disable pagination to return all records
    
    def get_serializer_class(self):
        if self.action in ['create']:
            return StationPermissionCreateSerializer
        return StationPermissionSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by station
        station_id = self.request.query_params.get('station')
        if station_id:
            queryset = queryset.filter(station_id=station_id)
        
        # Filter by permission
        permission_id = self.request.query_params.get('permission')
        if permission_id:
            queryset = queryset.filter(permission_id=permission_id)
        
        return queryset
    
    @action(detail=False, methods=['post'], url_path='bulk-update')
    def bulk_update(self, request):
        """
        Bulk update station permissions.
        
        POST /api/station-permissions/bulk-update/
        {
            "station_id": 1,
            "permissions": {
                "can_view_dbs_dashboard": true,
                "can_view_ms_dashboard": false
            }
        }
        """
        station_id = request.data.get('station_id')
        permissions_data = request.data.get('permissions', {})
        
        if not station_id:
            return validation_error_response('station_id is required')
        
        # We need Station model. Assuming it's in core.models
        from core.models import Station
        try:
            station = Station.objects.get(id=station_id)
        except Station.DoesNotExist:
            return not_found_response('Station not found')
        
        updated = []
        created = []
        
        for perm_code, granted in permissions_data.items():
            try:
                permission = Permission.objects.get(code=perm_code)
            except Permission.DoesNotExist:
                continue
            
            station_perm, was_created = StationPermission.objects.update_or_create(
                station=station,
                permission=permission,
                defaults={'granted': granted}
            )
            
            if was_created:
                created.append(perm_code)
            else:
                updated.append(perm_code)

        return Response({
            'success': True,
            'station': station.name,
            'created': created,
            'updated': updated
        })

    @action(detail=False, methods=['get'], url_path='matrix')
    def matrix(self, request):
        """
        Get ALL permissions with their status for a specific station.
        Useful for UI toggles to show both enabled and disabled permissions.
        
        GET /api/station-permissions/matrix/?station_id=1
        """
        station_id = request.query_params.get('station_id')
        if not station_id:
            return validation_error_response('station_id is required')
            
        # Get all permissions first
        all_perms = Permission.objects.all().order_by('category', 'name')
        
        # Get existing station permissions
        station_perms = StationPermission.objects.filter(station_id=station_id)
        granted_map = {sp.permission.code: sp.granted for sp in station_perms}
        
        result = []
        for perm in all_perms:
            result.append({
                'code': perm.code,
                'name': perm.name,
                'description': perm.description,
                'category': perm.category,
                'platform': perm.platform,
                'granted': granted_map.get(perm.code, False)  # Default to False if not found
            })
            
        return Response(result)

