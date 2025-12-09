"""
Permission Views for GTS
Handles API endpoints for permission management.
"""

from rest_framework import viewsets, status, views
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from .permission_models import Permission, RolePermission, UserPermission, DEFAULT_ROLE_PERMISSIONS
from .permission_serializers import (
    PermissionSerializer, 
    RolePermissionSerializer, RolePermissionCreateSerializer,
    UserPermissionSerializer, UserPermissionCreateSerializer,
    RoleWithPermissionsSerializer
)
from .models import Role, User


def get_user_permissions_from_db(user):
    """
    Get computed permissions for a user.
    
    Logic:
    1. Start with default False for all permissions
    2. Apply role-based permissions (from all active roles)
    3. Apply user-specific overrides (takes precedence)
    
    Returns dict of {permission_code: bool} or None if tables don't exist
    """
    try:
        # Get all permission codes
        all_permissions = Permission.objects.all().values_list('code', flat=True)
        result = {code: False for code in all_permissions}
        
        # If no permissions in database, return None to trigger fallback
        if not result:
            return None
        
        # Set can_view_trips to True by default (base permission)
        if 'can_view_trips' in result:
            result['can_view_trips'] = True
        
        # Check if user is Super Admin - they get all permissions
        is_super_admin = user.user_roles.filter(role__code='SUPER_ADMIN', active=True).exists()
        if is_super_admin:
            return {code: True for code in result}
        
        # Get user's active role codes
        user_role_codes = list(user.user_roles.filter(active=True).values_list('role__code', flat=True))
        
        # Apply role-based permissions from database
        role_perms = RolePermission.objects.filter(
            role__code__in=user_role_codes,
            granted=True
        ).select_related('permission').values_list('permission__code', flat=True)
        
        for perm_code in role_perms:
            if perm_code in result:
                result[perm_code] = True
        
        # If no database permissions found, fall back to hardcoded defaults
        # This ensures backward compatibility during migration
        if not role_perms.exists():
            for role_code in user_role_codes:
                if role_code in DEFAULT_ROLE_PERMISSIONS:
                    for perm_code in DEFAULT_ROLE_PERMISSIONS[role_code]:
                        if perm_code in result:
                            result[perm_code] = True
        
        # Apply user-specific overrides
        user_perms = UserPermission.objects.filter(user=user).select_related('permission')
        for up in user_perms:
            if up.permission.code in result:
                result[up.permission.code] = up.granted
        
        return result
    except Exception:
        # Table doesn't exist (migrations not run), return None to trigger fallback
        return None


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
        
        return queryset


class RolePermissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for RolePermission CRUD operations.
    Manages default permissions for roles.
    """
    queryset = RolePermission.objects.all().select_related('role', 'permission')
    permission_classes = [IsAuthenticated]
    
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
            return Response({'error': 'role_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            role = Role.objects.get(id=role_id)
        except Role.DoesNotExist:
            return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)
        
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
        
        return Response({
            'success': True,
            'role': role.code,
            'created': created,
            'updated': updated
        })


class UserPermissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for UserPermission CRUD operations.
    Manages user-specific permission overrides.
    """
    queryset = UserPermission.objects.all().select_related('user', 'permission', 'created_by')
    permission_classes = [IsAuthenticated]
    
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
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
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
