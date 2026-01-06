"""
Permission Serializers for GTS
Handles serialization/deserialization of permission-related models.
"""

from rest_framework import serializers
from .permission_models import Permission, RolePermission, UserPermission
from .models import Role, User


class PermissionSerializer(serializers.ModelSerializer):
    """Serializer for Permission model"""
    
    class Meta:
        model = Permission
        fields = ['id', 'code', 'name', 'description', 'category', 'platform']
        read_only_fields = ['id']


class RolePermissionSerializer(serializers.ModelSerializer):
    """Serializer for RolePermission model"""
    
    permission_code = serializers.CharField(source='permission.code', read_only=True)
    permission_name = serializers.CharField(source='permission.name', read_only=True)
    permission_category = serializers.CharField(source='permission.category', read_only=True)
    permission_platform = serializers.CharField(source='permission.platform', read_only=True)
    role_code = serializers.CharField(source='role.code', read_only=True)
    role_name = serializers.CharField(source='role.name', read_only=True)
    
    class Meta:
        model = RolePermission
        fields = [
            'id', 'role', 'role_code', 'role_name',
            'permission', 'permission_code', 'permission_name', 'permission_category',
            'permission_platform', 'granted', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RolePermissionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating RolePermission"""
    
    class Meta:
        model = RolePermission
        fields = ['role', 'permission', 'granted']


class UserPermissionSerializer(serializers.ModelSerializer):
    """Serializer for UserPermission model"""
    
    permission_code = serializers.CharField(source='permission.code', read_only=True)
    permission_name = serializers.CharField(source='permission.name', read_only=True)
    permission_category = serializers.CharField(source='permission.category', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    
    class Meta:
        model = UserPermission
        fields = [
            'id', 'user', 'user_name', 'user_email',
            'permission', 'permission_code', 'permission_name', 'permission_category',
            'granted', 'created_at', 'updated_at', 'created_by', 'created_by_name'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']


class UserPermissionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating UserPermission"""
    
    class Meta:
        model = UserPermission
        fields = ['user', 'permission', 'granted']


class RoleWithPermissionsSerializer(serializers.ModelSerializer):
    """Serializer for Role with all its permissions"""
    
    permissions = serializers.SerializerMethodField()
    
    class Meta:
        model = Role
        fields = ['id', 'code', 'name', 'description', 'permissions']
    
    def get_permissions(self, obj):
        """Get all permissions for this role as a dictionary"""
        from .permission_models import Permission, RolePermission
        
        # Get all permissions
        all_permissions = Permission.objects.all()
        
        # Get role's granted permissions
        role_perms = RolePermission.objects.filter(role=obj).select_related('permission')
        granted_codes = {rp.permission.code: rp.granted for rp in role_perms}
        
        # Build permission dict
        result = {}
        for perm in all_permissions:
            result[perm.code] = granted_codes.get(perm.code, False)
        
        return result


class UserPermissionsResponseSerializer(serializers.Serializer):
    """Serializer for user permissions response"""
    
    permissions = serializers.DictField(child=serializers.BooleanField())
