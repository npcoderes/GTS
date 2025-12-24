"""
Permission Management Models for GTS
Handles granular permission control for roles and individual users.
"""

from django.db import models
from django.conf import settings


class Permission(models.Model):
    """
    Individual permission definition.
    Stores all possible permissions in the system.
    """
    
    CATEGORY_CHOICES = [
        ('requests', 'Stock Requests'),
        ('trips', 'Trips'),
        ('drivers', 'Drivers'),
        ('stations', 'Stations'),
        ('tokens', 'Tokens'),
        ('system', 'System'),
    ]
    
    code = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Permission Code',
        help_text='Unique permission identifier (e.g., can_raise_manual_request)'
    )
    name = models.CharField(
        max_length=100,
        verbose_name='Permission Name',
        help_text='Human-readable permission name'
    )
    description = models.TextField(
        null=True,
        blank=True,
        verbose_name='Description',
        help_text='Detailed description of what this permission allows'
    )
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='system',
        verbose_name='Category',
        help_text='Permission category for grouping in UI'
    )
    
    class Meta:
        verbose_name = 'Permission'
        verbose_name_plural = 'Permissions'
        db_table = 'permissions'
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class RolePermission(models.Model):
    """
    Default permissions assigned to a role.
    When a user has a role, they inherit these permissions.
    """
    
    role = models.ForeignKey(
        'core.Role',
        on_delete=models.CASCADE,
        related_name='role_permissions',
        verbose_name='Role',
        help_text='Role this permission is assigned to'
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name='role_permissions',
        verbose_name='Permission',
        help_text='Permission granted to this role'
    )
    granted = models.BooleanField(
        default=True,
        verbose_name='Granted',
        help_text='Whether this permission is granted (True) or denied (False)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Role Permission'
        verbose_name_plural = 'Role Permissions'
        db_table = 'role_permissions'
        unique_together = ['role', 'permission']
        ordering = ['role__name', 'permission__category', 'permission__name']
    
    def __str__(self):
        status = "granted" if self.granted else "denied"
        return f"{self.role.name} - {self.permission.name} ({status})"


class UserPermission(models.Model):
    """
    User-specific permission overrides.
    Takes precedence over role permissions.
    Allows granting or revoking permissions for specific users.
    """
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_permissions_custom',
        verbose_name='User',
        help_text='User this permission override applies to'
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name='user_permissions',
        verbose_name='Permission',
        help_text='Permission being overridden'
    )
    granted = models.BooleanField(
        default=True,
        verbose_name='Granted',
        help_text='Whether this permission is granted (True) or revoked (False)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_user_permissions',
        verbose_name='Created By',
        help_text='Admin who created this override'
    )
    
    class Meta:
        verbose_name = 'User Permission'
        verbose_name_plural = 'User Permissions'
        db_table = 'user_permissions'
        unique_together = ['user', 'permission']
        ordering = ['user__full_name', 'permission__category', 'permission__name']
    
    def __str__(self):
        status = "granted" if self.granted else "revoked"
        return f"{self.user.full_name} - {self.permission.name} ({status})"


# Default permissions to be seeded
DEFAULT_PERMISSIONS = [
    {
        'code': 'can_submit_manual_request',
        'name': 'Submit Manual Request',
        'description': 'Can submit manual stock requests',
        'category': 'requests'
    },
    {
        'code': 'can_approve_request',
        'name': 'Approve Request',
        'description': 'Can approve or reject stock requests',
        'category': 'requests'
    },
    {
        'code': 'can_manage_drivers',
        'name': 'Manage Drivers',
        'description': 'Can manage driver records and assignments',
        'category': 'drivers'
    },
    {
        'code': 'can_override_tokens',
        'name': 'Manual Tokens Generation',
        'description': 'Can Generate manual tokens',
        'category': 'tokens'
    },
    {
        'code': 'can_manage_clusters',
        'name': 'Manage Clusters',
        'description': 'Can manage station clusters and mappings',
        'category': 'stations'
    },
    {
        'code': 'can_trigger_correction_actions',
        'name': 'Trigger Correction Actions',
        'description': 'Can trigger correction actions for trips',
        'category': 'trips'
    },
]

# Default role-permission mappings (matching current hardcoded logic)
DEFAULT_ROLE_PERMISSIONS = {
    'DBS_OPERATOR': ['can_submit_manual_request'],
    'MS_OPERATOR': [],  # MS dashboard is default - no special permissions needed
    'EIC': ['can_manage_clusters', 'can_manage_drivers', 'can_trigger_correction_actions', 'can_override_tokens', 'can_approve_request'],
    'SGL_TRANSPORT_VENDOR': ['can_manage_drivers'],
    'DRIVER': [],  # No permissions for driver
    'SUPER_ADMIN': [  # All permissions
        'can_submit_manual_request', 'can_approve_request', 
        'can_manage_drivers', 'can_override_tokens', 
        'can_manage_clusters', 'can_trigger_correction_actions'
    ],
    'SGL_CUSTOMER': [],
}
