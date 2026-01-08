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
        ('screens', 'Screen Access'),
        ('system', 'System'),
    ]
    
    PLATFORM_CHOICES = [
        ('all', 'All Platforms'),
        ('mobile', 'Mobile App Only'),
        ('dashboard', 'Web Dashboard Only'),
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
    platform = models.CharField(
        max_length=20,
        choices=PLATFORM_CHOICES,
        default='all',
        verbose_name='Platform',
        help_text='Which platform this permission applies to (mobile, dashboard, or all)'
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
    # =============================================
    # ACTION PERMISSIONS (shared across platforms)
    # =============================================
    {
        'code': 'can_submit_manual_request',
        'name': 'Submit Manual Request',
        'description': 'Can submit manual stock requests',
        'category': 'requests',
        'platform': 'all'
    },
    {
        'code': 'can_approve_request',
        'name': 'Approve Request',
        'description': 'Can approve or reject stock requests',
        'category': 'requests',
        'platform': 'all'
    },
    {
        'code': 'can_manage_drivers',
        'name': 'Manage Drivers',
        'description': 'Can manage driver records and assignments',
        'category': 'drivers',
        'platform': 'all'
    },
    {
        'code': 'can_override_tokens',
        'name': 'Manual Tokens Generation',
        'description': 'Can Generate manual tokens',
        'category': 'tokens',
        'platform': 'all'
    },
    {
        'code': 'can_manage_clusters',
        'name': 'Manage Clusters',
        'description': 'Can manage station clusters and mappings',
        'category': 'stations',
        'platform': 'all'
    },
    {
        'code': 'can_trigger_correction_actions',
        'name': 'Trigger Correction Actions',
        'description': 'Can trigger correction actions for trips',
        'category': 'trips',
        'platform': 'all'
    },
    {
        'code': 'can_approve_shift',
        'name': 'Approve Driver Shift',
        'description': 'Can approve driver shift requests',
        'category': 'drivers',
        'platform': 'all'
    },
    {
        'code': 'can_reject_shift',
        'name': 'Reject Driver Shift',
        'description': 'Can reject driver shift requests',
        'category': 'drivers',
        'platform': 'all'
    },
    
    # =============================================
    # SCREEN PERMISSIONS - Admin Dashboard (Web Only)
    # =============================================
    {
        'code': 'can_view_admin_users',
        'name': 'View User Management',
        'description': 'Can access User Management screen',
        'category': 'screens',
        'platform': 'dashboard'
    },
    {
        'code': 'can_view_admin_roles',
        'name': 'View Role Management',
        'description': 'Can access Role Management screen',
        'category': 'screens',
        'platform': 'dashboard'
    },
    {
        'code': 'can_view_admin_permissions',
        'name': 'View Permission Management',
        'description': 'Can access Permission Management screen',
        'category': 'screens',
        'platform': 'dashboard'
    },
    {
        'code': 'can_view_admin_stations',
        'name': 'View Station Management',
        'description': 'Can access Station Management screen',
        'category': 'screens',
        'platform': 'dashboard'
    },
    
    # =============================================
    # SCREEN PERMISSIONS - EIC Dashboard (Web Only)
    # =============================================
    {
        'code': 'can_view_eic_network_dashboard',
        'name': 'View EIC Network Dashboard',
        'description': 'Can access EIC Logistics Overview screen',
        'category': 'screens',
        'platform': 'dashboard'
    },
    {
        'code': 'can_view_eic_driver_approvals',
        'name': 'View Driver Shift Approvals',
        'description': 'Can access EIC Driver Shift Approvals screen',
        'category': 'screens',
        'platform': 'dashboard'
    },
    {
        'code': 'can_view_eic_alerts',
        'name': 'View EIC Alerts',
        'description': 'Can access EIC Alerts screen',
        'category': 'screens',
        'platform': 'dashboard'
    },
    {
        'code': 'can_view_eic_incoming_stock_requests',
        'name': 'View Incoming Stock Requests',
        'description': 'Can access EIC Incoming Stock Requests screen',
        'category': 'screens',
        'platform': 'dashboard'
    },
    {
        'code': 'can_view_eic_stock_transfers',
        'name': 'View EIC Stock Transfers',
        'description': 'Can access EIC Stock Transfers screen',
        'category': 'screens',
        'platform': 'dashboard'
    },
    {
        'code': 'can_view_eic_cluster_management',
        'name': 'View Cluster Management',
        'description': 'Can access EIC Cluster Management screen',
        'category': 'screens',
        'platform': 'dashboard'
    },
    {
        'code': 'can_view_eic_reconciliation',
        'name': 'View Reconciliation',
        'description': 'Can access EIC Reconciliation screen',
        'category': 'screens',
        'platform': 'dashboard'
    },
    {
        'code': 'can_view_eic_vehicle_tracking',
        'name': 'View Vehicle Tracking',
        'description': 'Can access EIC Vehicle Tracking screen',
        'category': 'screens',
        'platform': 'dashboard'
    },
    {
        'code': 'can_view_eic_vehicle_queue',
        'name': 'View Vehicle Queue',
        'description': 'Can access EIC Vehicle Queue screen',
        'category': 'screens',
        'platform': 'dashboard'
    },
    {
        'code': 'can_view_eic_manual_token_assignment',
        'name': 'View Manual Token Assignment',
        'description': 'Can access EIC Manual Token Assignment screen',
        'category': 'screens',
        'platform': 'dashboard'
    },
    
    # =============================================
    # SCREEN PERMISSIONS - Transport Dashboard (Web Only)
    # =============================================
    {
        'code': 'can_view_transport_logistics',
        'name': 'View Transport Trips',
        'description': 'Can access Transport Logistics/Trips screen',
        'category': 'screens',
        'platform': 'dashboard'
    },
    {
        'code': 'can_view_transport_vehicles',
        'name': 'View Vehicles',
        'description': 'Can access Vehicle Management screen',
        'category': 'screens',
        'platform': 'dashboard'
    },
    {
        'code': 'can_view_transport_drivers',
        'name': 'View Drivers',
        'description': 'Can access Driver Management screen',
        'category': 'screens',
        'platform': 'dashboard'
    },
    {
        'code': 'can_view_transport_timesheet',
        'name': 'View Timesheet',
        'description': 'Can access Timesheet Management screen',
        'category': 'screens',
        'platform': 'dashboard'
    },
    
    # =============================================
    # SCREEN PERMISSIONS - MS (Mother Station - Mobile Only)
    # =============================================
    {
        'code': 'can_view_ms_dashboard',
        'name': 'View MS Dashboard',
        'description': 'Can access Mother Station Dashboard',
        'category': 'screens',
        'platform': 'mobile'
    },
    {
        'code': 'can_view_ms_operations',
        'name': 'View MS Operations',
        'description': 'Can access Mother Station Operations screen',
        'category': 'screens',
        'platform': 'mobile'
    },
    {
        'code': 'can_view_ms_stock_transfers',
        'name': 'View MS Stock Transfers',
        'description': 'Can access Mother Station Stock Transfers screen',
        'category': 'screens',
        'platform': 'mobile'
    },
    
    # =============================================
    # SCREEN PERMISSIONS - DBS (Daughter Bowser Station - Mobile Only)
    # =============================================
    {
        'code': 'can_view_dbs_dashboard',
        'name': 'View DBS Dashboard',
        'description': 'Can access Daughter Bowser Station Dashboard',
        'category': 'screens',
        'platform': 'mobile'
    },
    {
        'code': 'can_view_dbs_decanting',
        'name': 'View DBS Decanting',
        'description': 'Can access DBS Decanting screen',
        'category': 'screens',
        'platform': 'mobile'
    },
    {
        'code': 'can_view_dbs_manual_request',
        'name': 'View DBS Manual Request',
        'description': 'Can access DBS Manual Request screen',
        'category': 'screens',
        'platform': 'mobile'
    },
    {
        'code': 'can_view_dbs_request_status',
        'name': 'View DBS Request Status',
        'description': 'Can access DBS Request Status screen',
        'category': 'screens',
        'platform': 'mobile'
    },
    {
        'code': 'can_view_dbs_stock_transfers',
        'name': 'View DBS Stock Transfers',
        'description': 'Can access DBS Stock Transfers screen',
        'category': 'screens',
        'platform': 'mobile'
    },
    
    # =============================================
    # SCREEN PERMISSIONS - Customer (Mobile Only)
    # =============================================
    {
        'code': 'can_view_customer_dashboard',
        'name': 'View Customer Dashboard',
        'description': 'Can access Customer Dashboard',
        'category': 'screens',
        'platform': 'mobile'
    },
    {
        'code': 'can_view_customer_current_stocks',
        'name': 'View Current Stocks',
        'description': 'Can access Customer Current Stocks screen',
        'category': 'screens',
        'platform': 'mobile'
    },
    {
        'code': 'can_view_customer_transport_tracking',
        'name': 'View Transport Tracking',
        'description': 'Can access Customer Transport Tracking screen',
        'category': 'screens',
        'platform': 'mobile'
    },
    {
        'code': 'can_view_customer_trip_acceptance',
        'name': 'View Trip Acceptance',
        'description': 'Can access Customer Trip Acceptance screen',
        'category': 'screens',
        'platform': 'mobile'
    },
    {
        'code': 'can_view_customer_stock_transfers',
        'name': 'View Customer Stock Transfers',
        'description': 'Can access Customer Stock Transfers screen',
        'category': 'screens',
        'platform': 'mobile'
    },
    
    # =============================================
    # SCREEN PERMISSIONS - Driver (Mobile App Only)
    # =============================================
    {
        'code': 'can_view_driver_dashboard',
        'name': 'View Driver Dashboard',
        'description': 'Can access Driver Dashboard',
        'category': 'screens',
        'platform': 'mobile'
    },
    {
        'code': 'can_view_driver_trips',
        'name': 'View Driver Trips',
        'description': 'Can access Driver Trips screen',
        'category': 'screens',
        'platform': 'mobile'
    },
    {
        'code': 'can_view_driver_emergency',
        'name': 'View Driver Emergency',
        'description': 'Can access Driver Emergency screen',
        'category': 'screens',
        'platform': 'mobile'
    },
    
    # =============================================
    # OTHER PERMISSIONS
    # =============================================
    {
        'code': 'can_view_settings',
        'name': 'View Settings',
        'description': 'Can access Settings screen',
        'category': 'screens',
        'platform': 'all'
    },
    
    # =============================================
    # STATION CAPABILITY PERMISSIONS
    # These are used for station-level features/capabilities
    # =============================================
    {
        'code': 'station_has_scada',
        'name': 'Station Has SCADA',
        'description': 'Station has SCADA integration enabled for automated meter readings',
        'category': 'stations',
        'platform': 'all'
    },
]

# Default role-permission mappings
DEFAULT_ROLE_PERMISSIONS = {
    'DBS_OPERATOR': [
        'can_view_dbs_dashboard', 'can_view_dbs_decanting', 'can_view_dbs_manual_request',
        'can_view_dbs_request_status', 'can_view_dbs_stock_transfers', 'can_submit_manual_request',
    ],
    'MS_OPERATOR': [
        'can_view_ms_dashboard', 'can_view_ms_operations', 'can_view_ms_stock_transfers',
    ],
    'EIC': [
        'can_view_eic_network_dashboard', 'can_view_eic_driver_approvals', 'can_view_eic_alerts',
        'can_view_eic_incoming_stock_requests', 'can_view_eic_stock_transfers',
        'can_view_eic_cluster_management', 'can_view_eic_reconciliation',
        'can_view_eic_vehicle_tracking', 'can_view_eic_vehicle_queue',
        'can_view_eic_manual_token_assignment', 'can_view_transport_logistics',
        'can_view_transport_vehicles', 'can_view_transport_drivers', 'can_view_transport_timesheet',
        'can_manage_clusters', 'can_manage_drivers', 'can_trigger_correction_actions',
        'can_override_tokens', 'can_approve_request', 'can_approve_shift', 'can_reject_shift',
    ],
    'SGL_TRANSPORT_VENDOR': [
        'can_view_transport_logistics', 'can_view_transport_vehicles',
        'can_view_transport_drivers', 'can_view_transport_timesheet', 'can_manage_drivers',
    ],
    'DRIVER': [
        'can_view_driver_dashboard', 'can_view_driver_trips', 'can_view_driver_emergency',
    ],
    'SUPER_ADMIN': [
        'can_view_admin_users', 'can_view_admin_roles', 'can_view_admin_permissions',
        'can_view_admin_stations', 'can_view_eic_network_dashboard', 'can_view_eic_driver_approvals',
        'can_view_eic_alerts', 'can_view_eic_incoming_stock_requests', 'can_view_eic_stock_transfers',
        'can_view_eic_cluster_management', 'can_view_eic_reconciliation', 'can_view_eic_vehicle_tracking',
        'can_view_eic_vehicle_queue', 'can_view_eic_manual_token_assignment',
        'can_view_transport_logistics', 'can_view_transport_vehicles', 'can_view_transport_drivers',
        'can_view_transport_timesheet', 'can_view_ms_dashboard', 'can_view_ms_operations',
        'can_view_ms_stock_transfers', 'can_view_dbs_dashboard', 'can_view_dbs_decanting',
        'can_view_dbs_manual_request', 'can_view_dbs_request_status', 'can_view_dbs_stock_transfers',
        'can_view_customer_dashboard', 'can_view_customer_current_stocks',
        'can_view_customer_transport_tracking', 'can_view_customer_trip_acceptance',
        'can_view_customer_stock_transfers', 'can_view_driver_dashboard', 'can_view_driver_trips',
        'can_view_driver_emergency', 'can_view_settings', 'can_submit_manual_request',
        'can_approve_request', 'can_manage_drivers', 'can_override_tokens',
        'can_manage_clusters', 'can_trigger_correction_actions', 'can_approve_shift', 'can_reject_shift',
    ],
    'SGL_CUSTOMER': [
        'can_view_customer_dashboard', 'can_view_customer_current_stocks',
        'can_view_customer_transport_tracking', 'can_view_customer_trip_acceptance',
        'can_view_customer_stock_transfers',
    ],
}

class StationPermission(models.Model):
    """
    Station-specific permissions.
    Used for permissions that apply to a specific station context (e.g. MS/DBS specific ops).
    """
    
    station = models.ForeignKey(
        'core.Station',
        on_delete=models.CASCADE,
        related_name='station_permissions',
        verbose_name='Station',
        help_text='Station this permission applies to'
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name='station_permissions',
        verbose_name='Permission',
        help_text='Permission granted/revoked'
    )
    granted = models.BooleanField(
        default=True,
        verbose_name='Granted',
        help_text='Whether this permission is granted'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Station Permission'
        verbose_name_plural = 'Station Permissions'
        db_table = 'station_permissions'
        unique_together = ['station', 'permission']
        ordering = ['station__name', 'permission__category', 'permission__name']
    
    def __str__(self):
        status = "granted" if self.granted else "denied"
        return f"{self.station.name} - {self.permission.name} ({status})"
