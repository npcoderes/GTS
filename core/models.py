"""
Gas Transportation System (GTS) - User Management Models
Handles User Authentication, Role-Based Access Control (RBAC), and related entities.
"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """
    Custom manager for User model with email as the unique identifier.
    """
    
    def create_user(self, email=None, password=None, **extra_fields):
        """
        Create and return a regular user with an email and password.
        Email is optional - phone can be used as primary identifier.
        """
        if email:
            email = self.normalize_email(email)
        
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and return a superuser with an email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model using email as the unique identifier for authentication.
    Supports Role-Based Access Control through UserRole relationship.
    """
    
    email = models.EmailField(
        unique=True,
        null=True,
        blank=True,
        verbose_name='Email Address',
        help_text='User email address (used for login)'
    )
    full_name = models.CharField(
        max_length=255,
        verbose_name='Full Name',
        help_text='User\'s full name'
    )
    phone = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Phone Number',
        help_text='Contact phone number'
    )
    is_password_reset_required = models.BooleanField(
        default=False,
        verbose_name='Password Reset Required',
        help_text='Designates whether the user must reset their password on next login'
    )
    mpin = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='MPIN',
        help_text='4-digit MPIN for quick login (hashed)'
    )
    role_in = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Role In Date',
        help_text='User\'s role in date-time'
    )
    role_out = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Role Out Date',
        help_text='User\'s role out date-time'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Active Status',
        help_text='Designates whether this user account is active'
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name='Staff Status',
        help_text='Designates whether the user can log into the admin site'
    )
    date_joined = models.DateTimeField(
        default=timezone.now,
        verbose_name='Date Joined'
    )
    fcm_token = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name='FCM Token',
        help_text='Firebase Cloud Messaging token for push notifications'
    )
    
    # SAP Integration Field
    sap_last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Last SAP Sync',
        help_text='Timestamp of the last successful sync with SAP.'
    )
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        db_table = 'users'
        ordering = ['-date_joined']
    
    def __str__(self):
        return f"{self.full_name} ({self.email})"
    
    def get_full_name(self):
        """Return the user's full name."""
        return self.full_name
    
    def get_short_name(self):
        """Return the user's email."""
        return self.email


class Station(models.Model):
    """
    Station details for Mother Stations (MS) and Daughter Booster Stations (DBS).
    """

    class StationType(models.TextChoices):
        MS = 'MS', 'Mother Station'
        DBS = 'DBS', 'Daughter Booster Station'

    type = models.CharField(
        max_length=3,
        choices=StationType.choices,
        verbose_name='Station Type',
        help_text='Station category: Mother Station (MS) or Daughter Booster Station (DBS).',
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Station Code',
        help_text='Unique identifier for the station (e.g., MS001).',
    )
    name = models.CharField(
        max_length=255,
        verbose_name='Station Name',
        help_text='Human-friendly station name.',
    )
    address = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name='Address',
        help_text='Station street address or site description.',
    )
    city = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='City',
        help_text='City where the station is located.',
    )
    lat = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name='Latitude',
        help_text='GPS latitude (decimal degrees).',
    )
    lng = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name='Longitude',
        help_text='GPS longitude (decimal degrees).',
    )
    geofence_radius_m = models.PositiveIntegerField(
        default=200,
        verbose_name='Geofence Radius (m)',
        help_text='Geofence radius in meters (default 200).',
    )
    parent_station = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='daughter_stations',
        verbose_name='Parent Station',
        help_text='Parent Mother Station (for DBS only).',
    )
    capacity_kg = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Capacity (kg)',
        help_text='Total storage capacity for the station in kilograms.',
    )
    current_stock_kg = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Current Stock (kg)',
        help_text='Latest recorded stock for the station in kilograms.',
    )
    stock_updated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Stock Updated At',
        help_text='Timestamp of the latest stock update.',
    )
    
    # SAP Integration Fields
    sap_station_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        unique=True,
        verbose_name='SAP Station ID',
        help_text='Station ID from SAP system (INPUT1). Used for synchronization.',
    )
    phone = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='Phone Number',
        help_text='Contact phone number for the station.',
    )
    sap_last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Last SAP Sync',
        help_text='Timestamp of the last successful sync with SAP.',
    )

    class Meta:
        verbose_name = 'Station'
        verbose_name_plural = 'Stations'
        db_table = 'stations'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.code})'
    
    
class Role(models.Model):
    """
    Role model representing different user roles in the GTS system.
    Examples: SUPER_ADMIN, MS_OPERATOR, DBS_OPERATOR, EIC, DRIVER, etc.
    """
    
    code = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Role Code',
        help_text='Unique role code identifier (e.g., SUPER_ADMIN, MS_OPERATOR)'
    )
    name = models.CharField(
        max_length=100,
        verbose_name='Role Name',
        help_text='Human-readable role name'
    )
    description = models.TextField(
        null=True,
        blank=True,
        verbose_name='Description',
        help_text='Detailed description of the role'
    )
    
    class Meta:
        verbose_name = 'Role'
        verbose_name_plural = 'Roles'
        db_table = 'roles'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class UserRole(models.Model):
    """
    Junction table managing the many-to-many relationship between Users and Roles.
    Supports station-specific role assignments (e.g., MS Operator at Station A).
    Super Admins may not have a station assignment (station can be NULL).
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_roles',
        verbose_name='User',
        help_text='User assigned to this role'
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='user_roles',
        verbose_name='Role',
        help_text='Role assigned to the user'
    )
    station = models.ForeignKey(
        Station,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_roles',
        verbose_name='Station',
        help_text='Station where this role is assigned (optional for Super Admins)'
    )
    active = models.BooleanField(
        default=True,
        verbose_name='Active Status',
        help_text='Whether this role assignment is currently active'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At'
    )
    
    class Meta:
        verbose_name = 'User Role'
        verbose_name_plural = 'User Roles'
        db_table = 'user_roles'
        unique_together = ['user', 'role', 'station']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'active']),
            models.Index(fields=['role', 'active']),
            models.Index(fields=['station', 'active']),
        ]
    
    def __str__(self):
        station_info = f" at {self.station.name}" if self.station else ""
        active_status = "Active" if self.active else "Inactive"
        return f"{self.user.full_name} - {self.role.name}{station_info} ({active_status})"


class MSDBSMap(models.Model):
    """
    Mapping between Mother Stations (MS) and Daughter Booster Stations (DBS).
    """
    ms = models.ForeignKey(Station, on_delete=models.CASCADE, related_name='dbs_mappings')
    dbs = models.ForeignKey(Station, on_delete=models.CASCADE, related_name='ms_mappings')
    active = models.BooleanField(default=True)

    class Meta:
        db_table = 'ms_dbs_map'
        unique_together = ['ms', 'dbs']

    def __str__(self):
        return f"{self.ms.code} -> {self.dbs.code}"


class Route(models.Model):
    """
    Route Master for MS -> DBS.
    """
    ms = models.ForeignKey(Station, on_delete=models.CASCADE, related_name='routes_from')
    dbs = models.ForeignKey(Station, on_delete=models.CASCADE, related_name='routes_to')
    code = models.CharField(max_length=50, unique=True, null=True, blank=True)
    name = models.CharField(max_length=255)
    planned_rtkm_km = models.DecimalField(max_digits=10, decimal_places=2)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'routes'

    def __str__(self):
        return f"{self.name} ({self.code})"


class PasswordResetSession(models.Model):
    """
    Manages the 3-step Password Reset flow:
    1. Request (OTP created)
    2. Verify (Reset token created if OTP valid)
    3. Confirm (Used token to reset password)
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_sessions')
    otp_code = models.CharField(max_length=6, verbose_name="OTP Code")
    reset_token = models.CharField(max_length=64, null=True, blank=True, unique=True, verbose_name="Secure Reset Token")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'password_reset_sessions'
        
    def __str__(self):
        return f"Reset Session ({self.user.email}) - Used: {self.is_used}"
