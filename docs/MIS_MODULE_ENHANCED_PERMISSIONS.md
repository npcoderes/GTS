# MIS Module - Enhanced Permission System
## Granular Access Control with Override Capabilities

**Date:** January 8, 2026  
**Version:** 2.0 - Enhanced Permissions

---

## Overview

This enhancement adds a **flexible permission system** that allows administrators to grant specific users access to data beyond their default role-based restrictions. For example, an EIC can be granted access to all stations instead of just their assigned ones.

---

## Permission Levels

### 1. **Default Role-Based Access** (Base Level)
Standard access based on user role:
- **Super Admin**: All data
- **Admin**: All data
- **EIC**: Assigned stations only
- **Transport Admin**: Own vendor only
- **Vendor**: Own vendor only

### 2. **Custom Permission Overrides** (Enhanced Level)
Administrators can grant additional access:
- **Station Access Override**: Grant access to specific stations
- **All Stations Access**: Grant access to all stations
- **Vendor Access**: Grant access to specific vendors
- **Report Type Access**: Grant/restrict specific report types
- **Data Scope Override**: Expand or restrict data scope

---

## New Database Models

### 1. MISUserPermission

```python
class MISUserPermission(models.Model):
    """
    Custom permissions for MIS module access.
    Allows granting users access beyond their default role.
    """
    PERMISSION_TYPES = [
        ('ALL_STATIONS', 'Access All Stations'),
        ('SPECIFIC_STATIONS', 'Access Specific Stations'),
        ('ALL_VENDORS', 'Access All Vendors'),
        ('SPECIFIC_VENDORS', 'Access Specific Vendors'),
        ('ALL_CUSTOMERS', 'Access All Customers'),
        ('SPECIFIC_CUSTOMERS', 'Access Specific Customers'),
        ('FINANCIAL_DATA', 'Access Financial Data'),
        ('EXPORT_UNLIMITED', 'Unlimited Export (No Rate Limit)'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mis_permissions')
    permission_type = models.CharField(max_length=50, choices=PERMISSION_TYPES)
    
    # For specific access (e.g., specific stations)
    stations = models.ManyToManyField('Station', blank=True)
    vendors = models.ManyToManyField('Vendor', blank=True)
    customers = models.ManyToManyField('Customer', blank=True)
    
    # Metadata
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='granted_permissions')
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Optional expiration date")
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, help_text="Reason for granting this permission")
    
    class Meta:
        db_table = 'mis_user_permissions'
        unique_together = ['user', 'permission_type']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_permission_type_display()}"
    
    def is_valid(self):
        """Check if permission is still valid (not expired)"""
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True


class MISReportTypePermission(models.Model):
    """
    Control which report types a user can access.
    By default, users can access all report types based on their role.
    This allows restricting or granting specific report types.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='report_type_permissions')
    report_type = models.CharField(max_length=50)  # Matches ReportTemplate.REPORT_TYPES
    can_access = models.BooleanField(default=True, help_text="True=Grant, False=Deny")
    
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    granted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'mis_report_type_permissions'
        unique_together = ['user', 'report_type']
    
    def __str__(self):
        access = "Can Access" if self.can_access else "Cannot Access"
        return f"{self.user.username} - {self.report_type} - {access}"


class MISDataScopeOverride(models.Model):
    """
    Override data scope for specific users.
    Allows fine-grained control over what data a user can see.
    """
    SCOPE_TYPES = [
        ('EXPAND', 'Expand Scope'),  # Grant more access
        ('RESTRICT', 'Restrict Scope'),  # Limit access
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='data_scope_overrides')
    scope_type = models.CharField(max_length=20, choices=SCOPE_TYPES)
    
    # Date range restrictions
    date_from = models.DateField(null=True, blank=True)
    date_to = models.DateField(null=True, blank=True)
    
    # Entity restrictions/expansions
    allowed_drivers = models.ManyToManyField('Driver', blank=True)
    allowed_vehicles = models.ManyToManyField('Vehicle', blank=True)
    allowed_routes = models.ManyToManyField('Route', blank=True)
    
    # Status restrictions
    allowed_statuses = models.JSONField(
        default=list,
        blank=True,
        help_text="List of allowed trip statuses"
    )
    
    is_active = models.BooleanField(default=True)
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    granted_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'mis_data_scope_overrides'
        ordering = ['-granted_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_scope_type_display()}"
```

---

## Permission Checking Logic

### Enhanced Permission Checker

```python
class MISPermissionChecker:
    """
    Centralized permission checking for MIS module.
    Checks both role-based and custom permissions.
    """
    
    def __init__(self, user):
        self.user = user
        self.role = user.role.upper()
        self._load_custom_permissions()
    
    def _load_custom_permissions(self):
        """Load user's custom permissions"""
        self.custom_permissions = MISUserPermission.objects.filter(
            user=self.user,
            is_active=True
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        )
        
        self.permission_types = set(
            self.custom_permissions.values_list('permission_type', flat=True)
        )
    
    def has_all_stations_access(self):
        """Check if user has access to all stations"""
        # Super Admin and Admin always have access
        if self.role in ['SUPER_ADMIN', 'ADMIN']:
            return True
        
        # Check custom permission
        return 'ALL_STATIONS' in self.permission_types
    
    def get_accessible_stations(self):
        """Get list of stations user can access"""
        # Super Admin and Admin can access all
        if self.role in ['SUPER_ADMIN', 'ADMIN']:
            return Station.objects.all()
        
        # Check for all stations permission
        if 'ALL_STATIONS' in self.permission_types:
            return Station.objects.all()
        
        # Check for specific stations permission
        if 'SPECIFIC_STATIONS' in self.permission_types:
            perm = self.custom_permissions.filter(
                permission_type='SPECIFIC_STATIONS'
            ).first()
            if perm:
                return perm.stations.all()
        
        # Default: EIC gets assigned stations
        if self.role == 'EIC':
            return self.user.eic_stations.all()
        
        # Others get no station access by default
        return Station.objects.none()
    
    def get_accessible_vendors(self):
        """Get list of vendors user can access"""
        # Super Admin and Admin can access all
        if self.role in ['SUPER_ADMIN', 'ADMIN']:
            return Vendor.objects.all()
        
        # Check for all vendors permission
        if 'ALL_VENDORS' in self.permission_types:
            return Vendor.objects.all()
        
        # Check for specific vendors permission
        if 'SPECIFIC_VENDORS' in self.permission_types:
            perm = self.custom_permissions.filter(
                permission_type='SPECIFIC_VENDORS'
            ).first()
            if perm:
                return perm.vendors.all()
        
        # Default: Transport Admin/Vendor gets own vendor
        if self.role in ['TRANSPORT_ADMIN', 'SGL_TRANSPORT_VENDOR']:
            return Vendor.objects.filter(id=self.user.vendor_id)
        
        return Vendor.objects.none()
    
    def can_access_financial_data(self):
        """Check if user can access financial reports"""
        # Super Admin always can
        if self.role == 'SUPER_ADMIN':
            return True
        
        # Check custom permission
        return 'FINANCIAL_DATA' in self.permission_types
    
    def can_access_report_type(self, report_type):
        """Check if user can access specific report type"""
        # Check for explicit deny
        deny = MISReportTypePermission.objects.filter(
            user=self.user,
            report_type=report_type,
            can_access=False
        ).exists()
        
        if deny:
            return False
        
        # Check for explicit grant
        grant = MISReportTypePermission.objects.filter(
            user=self.user,
            report_type=report_type,
            can_access=True
        ).exists()
        
        if grant:
            return True
        
        # Default: Allow based on role
        # Financial reports only for Super Admin unless granted
        if report_type in ['REVENUE', 'COST_ANALYSIS']:
            return self.can_access_financial_data()
        
        return True
    
    def apply_data_filters(self, queryset):
        """
        Apply data filters to queryset based on permissions.
        This is the core function that filters data.
        """
        # Super Admin sees everything
        if self.role == 'SUPER_ADMIN':
            return queryset
        
        # Admin sees everything (unless restricted)
        if self.role == 'ADMIN':
            # Check for restrictions
            restrictions = MISDataScopeOverride.objects.filter(
                user=self.user,
                scope_type='RESTRICT',
                is_active=True
            )
            if restrictions.exists():
                # Apply restrictions
                for restriction in restrictions:
                    if restriction.allowed_drivers.exists():
                        queryset = queryset.filter(
                            driver__in=restriction.allowed_drivers.all()
                        )
                    if restriction.allowed_vehicles.exists():
                        queryset = queryset.filter(
                            vehicle__in=restriction.allowed_vehicles.all()
                        )
            return queryset
        
        # Get accessible stations
        accessible_stations = self.get_accessible_stations()
        
        # Filter by stations
        queryset = queryset.filter(
            Q(ms_station__in=accessible_stations) |
            Q(dbs_station__in=accessible_stations)
        )
        
        # Get accessible vendors
        accessible_vendors = self.get_accessible_vendors()
        
        # Filter by vendors (for Transport Admin/Vendor)
        if self.role in ['TRANSPORT_ADMIN', 'SGL_TRANSPORT_VENDOR']:
            queryset = queryset.filter(
                driver__vendor__in=accessible_vendors
            )
        
        # Apply scope expansions
        expansions = MISDataScopeOverride.objects.filter(
            user=self.user,
            scope_type='EXPAND',
            is_active=True
        )
        
        if expansions.exists():
            for expansion in expansions:
                # Add additional drivers
                if expansion.allowed_drivers.exists():
                    queryset = queryset | Trip.objects.filter(
                        driver__in=expansion.allowed_drivers.all()
                    )
                # Add additional vehicles
                if expansion.allowed_vehicles.exists():
                    queryset = queryset | Trip.objects.filter(
                        vehicle__in=expansion.allowed_vehicles.all()
                    )
        
        return queryset.distinct()
```

---

## Permission Management UI

### Admin Interface for Managing Permissions

```javascript
// Permission Management Page Component

const MISPermissionManagement = () => {
    const [users, setUsers] = useState([]);
    const [selectedUser, setSelectedUser] = useState(null);
    const [permissionModalVisible, setPermissionModalVisible] = useState(false);
    
    // Grant All Stations Access
    const grantAllStationsAccess = async (userId, expiresAt = null) => {
        await apiClient.post('/api/mis/permissions/grant/', {
            user_id: userId,
            permission_type: 'ALL_STATIONS',
            expires_at: expiresAt,
            notes: 'Granted access to all stations'
        });
        message.success('All stations access granted');
    };
    
    // Grant Specific Stations Access
    const grantSpecificStations = async (userId, stationIds, expiresAt = null) => {
        await apiClient.post('/api/mis/permissions/grant/', {
            user_id: userId,
            permission_type: 'SPECIFIC_STATIONS',
            station_ids: stationIds,
            expires_at: expiresAt,
            notes: 'Granted access to specific stations'
        });
        message.success('Station access granted');
    };
    
    // Revoke Permission
    const revokePermission = async (permissionId) => {
        await apiClient.delete(`/api/mis/permissions/${permissionId}/`);
        message.success('Permission revoked');
    };
    
    return (
        <div>
            <Card title="MIS Permission Management">
                <Table
                    dataSource={users}
                    columns={[
                        {
                            title: 'User',
                            render: (_, record) => (
                                <div>
                                    <Text strong>{record.username}</Text>
                                    <br />
                                    <Tag>{record.role}</Tag>
                                </div>
                            )
                        },
                        {
                            title: 'Default Access',
                            render: (_, record) => {
                                if (record.role === 'EIC') {
                                    return (
                                        <Text>
                                            {record.assigned_stations.length} Assigned Stations
                                        </Text>
                                    );
                                }
                                return <Text>{getRoleDefaultAccess(record.role)}</Text>;
                            }
                        },
                        {
                            title: 'Custom Permissions',
                            render: (_, record) => (
                                <div>
                                    {record.custom_permissions.map(perm => (
                                        <Tag
                                            key={perm.id}
                                            color="blue"
                                            closable
                                            onClose={() => revokePermission(perm.id)}
                                        >
                                            {perm.permission_type}
                                        </Tag>
                                    ))}
                                </div>
                            )
                        },
                        {
                            title: 'Actions',
                            render: (_, record) => (
                                <Space>
                                    <Button
                                        type="primary"
                                        onClick={() => {
                                            setSelectedUser(record);
                                            setPermissionModalVisible(true);
                                        }}
                                    >
                                        Manage Permissions
                                    </Button>
                                </Space>
                            )
                        }
                    ]}
                />
            </Card>
            
            {/* Permission Modal */}
            <Modal
                title={`Manage Permissions - ${selectedUser?.username}`}
                visible={permissionModalVisible}
                onCancel={() => setPermissionModalVisible(false)}
                width={700}
                footer={null}
            >
                <PermissionForm
                    user={selectedUser}
                    onSuccess={() => {
                        setPermissionModalVisible(false);
                        fetchUsers();
                    }}
                />
            </Modal>
        </div>
    );
};
```

---

## API Endpoints

### Permission Management APIs

```python
# New API Endpoints

# List user's permissions
GET /api/mis/permissions/user/{user_id}/

# Grant permission
POST /api/mis/permissions/grant/
{
    "user_id": 123,
    "permission_type": "ALL_STATIONS",
    "expires_at": "2026-12-31",  # Optional
    "notes": "Special access for audit"
}

# Grant specific stations
POST /api/mis/permissions/grant/
{
    "user_id": 123,
    "permission_type": "SPECIFIC_STATIONS",
    "station_ids": [1, 2, 3],
    "expires_at": null,
    "notes": "Access to regional stations"
}

# Revoke permission
DELETE /api/mis/permissions/{permission_id}/

# List all permissions (admin only)
GET /api/mis/permissions/all/

# Check user's effective permissions
GET /api/mis/permissions/check/{user_id}/
Response:
{
    "user_id": 123,
    "role": "EIC",
    "default_access": {
        "stations": [1, 2],
        "vendors": [],
        "scope": "assigned_stations"
    },
    "custom_permissions": [
        {
            "type": "ALL_STATIONS",
            "granted_by": "admin",
            "granted_at": "2026-01-08",
            "expires_at": null
        }
    ],
    "effective_access": {
        "stations": "all",
        "vendors": [],
        "financial_data": false
    }
}
```

---

## Use Cases

### Use Case 1: Grant EIC Access to All Stations

**Scenario**: An EIC needs temporary access to all stations for a company-wide audit.

**Solution**:
```python
# Admin grants all stations access
permission = MISUserPermission.objects.create(
    user=eic_user,
    permission_type='ALL_STATIONS',
    granted_by=admin_user,
    expires_at=datetime(2026, 2, 1),  # Expires after audit
    notes='Granted for Q1 2026 audit'
)
```

**Result**: EIC can now generate reports for all stations, not just assigned ones.

---

### Use Case 2: Grant Specific Vendor Access to EIC

**Scenario**: An EIC needs to monitor a specific vendor's performance.

**Solution**:
```python
# Admin grants specific vendor access
permission = MISUserPermission.objects.create(
    user=eic_user,
    permission_type='SPECIFIC_VENDORS',
    granted_by=admin_user,
    notes='Monitor ABC Transport performance'
)
permission.vendors.add(abc_vendor)
```

**Result**: EIC can see reports for ABC Transport's drivers and vehicles.

---

### Use Case 3: Restrict Admin Access

**Scenario**: An admin should only see data from specific regions.

**Solution**:
```python
# Super Admin restricts admin's scope
restriction = MISDataScopeOverride.objects.create(
    user=admin_user,
    scope_type='RESTRICT',
    granted_by=super_admin,
    notes='Regional admin for North zone only'
)
restriction.allowed_stations.add(*north_zone_stations)
```

**Result**: Admin only sees data from North zone stations.

---

### Use Case 4: Temporary Financial Data Access

**Scenario**: An EIC needs to access financial reports for budget planning.

**Solution**:
```python
# Admin grants temporary financial access
permission = MISUserPermission.objects.create(
    user=eic_user,
    permission_type='FINANCIAL_DATA',
    granted_by=admin_user,
    expires_at=datetime(2026, 1, 31),
    notes='Budget planning for February'
)
```

**Result**: EIC can access Revenue and Cost Analysis reports until Jan 31.

---

## Permission Audit Trail

### Track All Permission Changes

```python
class MISPermissionAudit(models.Model):
    """
    Audit trail for all permission changes.
    """
    ACTION_TYPES = [
        ('GRANT', 'Permission Granted'),
        ('REVOKE', 'Permission Revoked'),
        ('EXPIRE', 'Permission Expired'),
        ('MODIFY', 'Permission Modified'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='permission_audits')
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    permission_type = models.CharField(max_length=50)
    
    # Details
    details = models.JSONField(help_text="Permission details")
    
    # Who and when
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    performed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True)
    
    class Meta:
        db_table = 'mis_permission_audits'
        ordering = ['-performed_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_action_type_display()} - {self.performed_at}"
```

---

## Updated Permission Flow

```
┌─────────────────────────────────────────────────────────┐
│  User Requests Report                                    │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  1. Check Role-Based Default Access                      │
│     - Super Admin: All data                              │
│     - Admin: All data                                    │
│     - EIC: Assigned stations                             │
│     - Transport Admin: Own vendor                        │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  2. Check Custom Permissions                             │
│     - ALL_STATIONS permission?                           │
│     - SPECIFIC_STATIONS permission?                      │
│     - VENDOR access permission?                          │
│     - FINANCIAL_DATA permission?                         │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  3. Check Data Scope Overrides                           │
│     - Expand scope (grant more access)                   │
│     - Restrict scope (limit access)                      │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  4. Apply Combined Filters to Query                      │
│     - Station filters                                    │
│     - Vendor filters                                     │
│     - Date filters                                       │
│     - Entity filters                                     │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  5. Generate Report with Filtered Data                   │
└─────────────────────────────────────────────────────────┘
```

---

## Security Considerations

### 1. **Permission Hierarchy**
- Only Super Admin can grant ALL_STATIONS to others
- Only Super Admin can grant FINANCIAL_DATA access
- Admins can grant SPECIFIC_STATIONS within their scope
- Users cannot grant permissions to themselves

### 2. **Expiration Enforcement**
- Automatic expiration checking on every request
- Daily cron job to deactivate expired permissions
- Email notifications before expiration

### 3. **Audit Trail**
- All permission grants/revokes logged
- IP address tracking
- Timestamp recording
- Reason/notes required

### 4. **Validation**
- Cannot grant permissions that exceed granter's own access
- Cannot grant conflicting permissions
- Expiration date must be in future

---

## Implementation Checklist

- [ ] Create new database models
- [ ] Create migrations
- [ ] Implement MISPermissionChecker class
- [ ] Update report generation to use permission checker
- [ ] Create permission management APIs
- [ ] Build permission management UI
- [ ] Add audit trail logging
- [ ] Create expiration cron job
- [ ] Add permission indicators in UI
- [ ] Write tests for permission logic
- [ ] Document permission system
- [ ] Train administrators

---

## Benefits of Enhanced Permission System

### 1. **Flexibility**
- Grant exceptions without changing roles
- Temporary access for special projects
- Fine-grained control

### 2. **Security**
- Principle of least privilege
- Time-limited access
- Full audit trail

### 3. **Scalability**
- Easy to add new permission types
- No code changes needed for new scenarios
- Self-service for admins

### 4. **Compliance**
- Track who has access to what
- Automatic expiration
- Detailed audit logs

---

## Conclusion

This enhanced permission system provides the flexibility to grant specific users access beyond their default role-based restrictions while maintaining security and auditability. Administrators can easily grant an EIC access to all stations, specific vendors, or financial data as needed, with optional expiration dates and full audit trails.

**The system is designed to be:**
- ✅ Flexible (grant any combination of permissions)
- ✅ Secure (audit trail, expiration, validation)
- ✅ User-friendly (simple UI for admins)
- ✅ Scalable (easy to add new permission types)
- ✅ Compliant (full audit trail)
