# MIS Module Models
# Management Information System - Reporting Models

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import json

User = get_user_model()


class ReportTemplate(models.Model):
    """
    Stores saved report configurations for reuse.
    Users can create, save, and share report templates.
    """
    REPORT_TYPES = [
        ('TRIP_SUMMARY', 'Trip Summary Report'),
        ('TRIP_DETAIL', 'Trip Detail Report'),
        ('TRIP_PERFORMANCE', 'Trip Performance Report'),
        ('DRIVER_PERFORMANCE', 'Driver Performance Report'),
        ('DRIVER_UTILIZATION', 'Driver Utilization Report'),
        ('VEHICLE_UTILIZATION', 'Vehicle Utilization Report'),
        ('VEHICLE_PERFORMANCE', 'Vehicle Performance Report'),
        ('MS_STATION', 'MS Station Report'),
        ('DBS_STATION', 'DBS Station Report'),
        ('CUSTOMER_DELIVERY', 'Customer Delivery Report'),
        ('CUSTOMER_JOURNEY', 'End-to-End Customer Journey'),
        ('QUANTITY_VARIANCE', 'Quantity Variance Report'),
        ('TIME_VARIANCE', 'Time Variance Report'),
        ('REVENUE', 'Revenue Report'),
        ('COST_ANALYSIS', 'Cost Analysis Report'),
        ('CUSTOM', 'Custom Report'),
    ]
    
    name = models.CharField(max_length=200, help_text="Template name")
    description = models.TextField(blank=True, help_text="Template description")
    report_type = models.CharField(max_length=50, choices=REPORT_TYPES)
    
    # Configuration stored as JSON
    configuration = models.JSONField(
        help_text="Report configuration including filters, columns, grouping, sorting"
    )
    """
    Configuration structure:
    {
        "filters": {
            "date_range": {"start": "2026-01-01", "end": "2026-01-31"},
            "drivers": [1, 2, 3],
            "vehicles": [5, 6],
            "ms_stations": [10],
            "dbs_stations": [20],
            "customers": [100],
            "status": ["COMPLETED"],
            "quantity_min": 1000,
            "quantity_max": 5000
        },
        "columns": ["trip_id", "date", "driver", "vehicle", "quantity", "variance"],
        "grouping": ["driver", "date"],
        "sorting": [{"field": "date", "order": "desc"}],
        "aggregations": {
            "quantity": "sum",
            "variance": "avg"
        }
    }
    """
    
    # Ownership and sharing
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='report_templates'
    )
    is_public = models.BooleanField(
        default=False, 
        help_text="If true, template is visible to all users"
    )
    is_system = models.BooleanField(
        default=False,
        help_text="System templates cannot be deleted"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    execution_count = models.IntegerField(default=0, help_text="Number of times executed")
    last_executed = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'mis_report_templates'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['created_by', 'report_type']),
            models.Index(fields=['is_public']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_report_type_display()})"
    
    def increment_execution_count(self):
        """Increment execution count and update last executed time"""
        self.execution_count += 1
        self.last_executed = timezone.now()
        self.save(update_fields=['execution_count', 'last_executed'])


class ScheduledReport(models.Model):
    """
    Scheduled reports that run automatically and email results.
    """
    SCHEDULE_TYPES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
    ]
    
    EXPORT_FORMATS = [
        ('PDF', 'PDF'),
        ('EXCEL', 'Excel'),
        ('CSV', 'CSV'),
    ]
    
    WEEKDAYS = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.CASCADE,
        related_name='schedules'
    )
    name = models.CharField(max_length=200, help_text="Schedule name")
    
    # Schedule configuration
    schedule_type = models.CharField(max_length=20, choices=SCHEDULE_TYPES)
    schedule_time = models.TimeField(help_text="Time to run the report")
    schedule_day = models.IntegerField(
        choices=WEEKDAYS,
        null=True,
        blank=True,
        help_text="Day of week for weekly reports (0=Monday)"
    )
    schedule_date = models.IntegerField(
        null=True,
        blank=True,
        help_text="Day of month for monthly reports (1-31)"
    )
    
    # Recipients
    recipients = models.JSONField(
        help_text="List of email addresses to send report to"
    )
    # Example: ["user1@example.com", "user2@example.com"]
    
    # Export settings
    export_format = models.CharField(max_length=10, choices=EXPORT_FORMATS, default='PDF')
    include_charts = models.BooleanField(default=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField()
    last_status = models.CharField(max_length=20, blank=True)
    last_error = models.TextField(blank=True)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'mis_scheduled_reports'
        ordering = ['next_run']
        indexes = [
            models.Index(fields=['is_active', 'next_run']),
            models.Index(fields=['created_by']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.get_schedule_type_display()}"
    
    def calculate_next_run(self):
        """Calculate next run time based on schedule type"""
        from datetime import datetime, timedelta
        
        now = timezone.now()
        next_run = now.replace(
            hour=self.schedule_time.hour,
            minute=self.schedule_time.minute,
            second=0,
            microsecond=0
        )
        
        if self.schedule_type == 'DAILY':
            if next_run <= now:
                next_run += timedelta(days=1)
        
        elif self.schedule_type == 'WEEKLY':
            days_ahead = self.schedule_day - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            next_run += timedelta(days=days_ahead)
        
        elif self.schedule_type == 'MONTHLY':
            if next_run.day != self.schedule_date:
                # Move to next month
                if next_run.month == 12:
                    next_run = next_run.replace(year=next_run.year + 1, month=1, day=self.schedule_date)
                else:
                    next_run = next_run.replace(month=next_run.month + 1, day=self.schedule_date)
        
        self.next_run = next_run
        self.save(update_fields=['next_run'])


class ReportExecution(models.Model):
    """
    Logs every report execution for audit and history.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='executions'
    )
    scheduled_report = models.ForeignKey(
        ScheduledReport,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='executions'
    )
    
    # Execution details
    executed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    parameters = models.JSONField(help_text="Filters and parameters used")
    
    # Results
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    row_count = models.IntegerField(default=0)
    execution_time = models.DateTimeField(auto_now_add=True)
    duration = models.FloatField(null=True, help_text="Execution duration in seconds")
    
    # File storage
    file_path = models.CharField(max_length=500, blank=True)
    file_format = models.CharField(max_length=10, blank=True)
    file_size = models.IntegerField(default=0, help_text="File size in bytes")
    
    # Error handling
    error_message = models.TextField(blank=True)
    error_traceback = models.TextField(blank=True)
    
    class Meta:
        db_table = 'mis_report_executions'
        ordering = ['-execution_time']
        indexes = [
            models.Index(fields=['executed_by', '-execution_time']),
            models.Index(fields=['status']),
            models.Index(fields=['template']),
        ]
    
    def __str__(self):
        template_name = self.template.name if self.template else "Ad-hoc Report"
        return f"{template_name} - {self.execution_time.strftime('%Y-%m-%d %H:%M')}"


class ReportFavorite(models.Model):
    """
    User's favorite/bookmarked reports for quick access.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_reports')
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'mis_report_favorites'
        unique_together = ['user', 'template']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.template.name}"


class ReportShare(models.Model):
    """
    Share reports with specific users or roles.
    """
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, related_name='shares')
    shared_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shared_reports')
    shared_with = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reports_shared_with_me'
    )
    shared_with_role = models.CharField(
        max_length=50,
        blank=True,
        help_text="Share with all users of this role"
    )
    can_edit = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'mis_report_shares'
        ordering = ['-created_at']
    
    def __str__(self):
        if self.shared_with:
            return f"{self.template.name} shared with {self.shared_with.username}"
        return f"{self.template.name} shared with {self.shared_with_role} role"


# ============================================================================
# ENHANCED PERMISSION MODELS
# ============================================================================

class MISUserPermission(models.Model):
    """
    Custom permissions for MIS module access.
    Allows granting users access beyond their default role.
    Example: Grant an EIC access to all stations instead of just assigned ones.
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
    # Note: Import Station, Vendor, Customer models as needed
    # stations = models.ManyToManyField('Station', blank=True)
    # vendors = models.ManyToManyField('Vendor', blank=True)
    # customers = models.ManyToManyField('Customer', blank=True)
    
    # Storing as JSON for flexibility (can be converted to M2M later)
    entity_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="List of entity IDs (station_ids, vendor_ids, etc.)"
    )
    
    # Metadata
    granted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='granted_mis_permissions'
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional expiration date for temporary access"
    )
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
    
    granted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='granted_report_type_permissions'
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
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
    Can expand (grant more access) or restrict (limit access).
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
    
    # Entity restrictions/expansions (stored as JSON)
    allowed_driver_ids = models.JSONField(default=list, blank=True)
    allowed_vehicle_ids = models.JSONField(default=list, blank=True)
    allowed_route_ids = models.JSONField(default=list, blank=True)
    
    # Status restrictions
    allowed_statuses = models.JSONField(
        default=list,
        blank=True,
        help_text="List of allowed trip statuses"
    )
    
    is_active = models.BooleanField(default=True)
    granted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='granted_scope_overrides'
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'mis_data_scope_overrides'
        ordering = ['-granted_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_scope_type_display()}"


class MISPermissionAudit(models.Model):
    """
    Audit trail for all permission changes.
    Tracks who granted/revoked permissions and when.
    """
    ACTION_TYPES = [
        ('GRANT', 'Permission Granted'),
        ('REVOKE', 'Permission Revoked'),
        ('EXPIRE', 'Permission Expired'),
        ('MODIFY', 'Permission Modified'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='permission_audits',
        help_text="User whose permissions were changed"
    )
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    permission_type = models.CharField(max_length=50)
    
    # Details
    details = models.JSONField(
        help_text="Permission details (entity IDs, expiration, etc.)"
    )
    
    # Who and when
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='performed_permission_audits'
    )
    performed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        db_table = 'mis_permission_audits'
        ordering = ['-performed_at']
        indexes = [
            models.Index(fields=['user', '-performed_at']),
            models.Index(fields=['performed_by']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_action_type_display()} - {self.performed_at}"
