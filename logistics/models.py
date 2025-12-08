from django.db import models
import uuid
from core.models import User, Station, Route

class Vehicle(models.Model):
    """
    Transport vehicles (HCVs).
    """
    vendor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vehicles', limit_choices_to={'user_roles__role__code': 'SGL_TRANSPORT_VENDOR'})
    registration_no = models.CharField(max_length=50, unique=True)
    hcv_code = models.CharField(max_length=50, unique=True, null=True, blank=True)
    ms_home = models.ForeignKey(Station, on_delete=models.SET_NULL, null=True, blank=True, related_name='home_vehicles')
    capacity_kg = models.DecimalField(max_digits=10, decimal_places=2)
    rfid_tag_id = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'vehicles'

    def __str__(self):
        return self.registration_no

class Driver(models.Model):
    """
    Drivers assigned to vendors.
    """
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('SUSPENDED', 'Suspended'),
    ]

    vendor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='drivers', limit_choices_to={'user_roles__role__code': 'SGL_TRANSPORT_VENDOR'})
    full_name = models.CharField(max_length=255)
    license_no = models.CharField(max_length=50)
    license_expiry = models.DateField()
    phone = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    trained = models.BooleanField(default=False)
    license_verified = models.BooleanField(default=False)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='driver_profile')
    assigned_vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_drivers')

    class Meta:
        db_table = 'drivers'

    def __str__(self):
        return self.full_name

class Shift(models.Model):
    """
    Driver shifts.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='shifts')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='shifts')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    is_recurring = models.BooleanField(default=False)
    recurrence_pattern = models.CharField(max_length=20, default='NONE') # DAILY, WEEKLY, etc.
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_shifts')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_shifts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    rejection_reason = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'shifts'

    def __str__(self):
        return f"{self.driver} - {self.start_time}"

class StockRequest(models.Model):
    """
    Gas stock requests from DBS.
    """
    SOURCE_CHOICES = [
        ('DBS_OPERATOR', 'DBS Operator'),
        ('FDODO_CUSTOMER', 'FDODO Customer'),
        ('AI', 'AI Engine'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('QUEUED', 'Queued'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
        ('APPROVED', 'Approved'),
        ('ASSIGNING', 'Assigning Driver'),
        ('ASSIGNED', 'Driver Assigned'),
        ('COMPLETED', 'Completed'),
    ]
    PRIORITY_CHOICES = [
        ('H', 'High'),
        ('C', 'Critical'),
        ('N', 'Normal'),
        ('FDODO', 'FDODO'),
    ]
    
    ASSIGNMENT_MODE_CHOICES = [
        ('AUTO', 'Auto-Push'),
        ('MANUAL', 'Manual Assignment'),
    ]

    source = models.CharField(max_length=50, choices=SOURCE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    dbs = models.ForeignKey(Station, on_delete=models.CASCADE, related_name='stock_requests')
    source_vendor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_requests_as_vendor')
    requested_by_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_requests_requested')
    requested_qty_kg = models.DecimalField(max_digits=10, decimal_places=2)
    current_stock_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    rate_of_sale_kg_per_min = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    dot_minutes = models.IntegerField(null=True, blank=True)
    rlt_minutes = models.IntegerField(null=True, blank=True)
    priority_preview = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='N')
    created_at = models.DateTimeField(auto_now_add=True)
    requested_by_date = models.DateField(null=True, blank=True)
    requested_by_time = models.TimeField(null=True, blank=True)
    
    # Rejection tracking
    rejection_reason = models.TextField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='rejected_stock_requests')
    approval_notes = models.TextField(null=True, blank=True)
    
    # Assignment State Tracking
    assignment_mode = models.CharField(max_length=10, choices=ASSIGNMENT_MODE_CHOICES, null=True, blank=True)
    assignment_started_at = models.DateTimeField(null=True, blank=True)
    target_driver = models.ForeignKey('Driver', on_delete=models.SET_NULL, null=True, blank=True, related_name='offered_requests')

    class Meta:
        db_table = 'stock_requests'

class Token(models.Model):
    """
    Tokens issued for trips.
    """
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    ms = models.ForeignKey(Station, on_delete=models.CASCADE)
    token_no = models.CharField(max_length=20, unique=True, null=True) # Renamed from sequence_no and changed to CharField
    issued_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.token_no:
            import uuid
            self.token_no = uuid.uuid4().hex[:12].upper()
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'tokens'

class Trip(models.Model):
    """
    Trips managing the transport lifecycle.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('AT_MS', 'At MS'),
        ('IN_TRANSIT', 'In Transit'),
        ('AT_DBS', 'At DBS'),
        ('DECANTING_CONFIRMED', 'Decanting Confirmed'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    stock_request = models.OneToOneField(StockRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name='trip')
    token = models.ForeignKey(Token, on_delete=models.SET_NULL, null=True, blank=True)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True)
    ms = models.ForeignKey(Station, on_delete=models.CASCADE, related_name='trips_origin')
    dbs = models.ForeignKey(Station, on_delete=models.CASCADE, related_name='trips_destination')
    route = models.ForeignKey(Route, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='PENDING')
    sto_number = models.CharField(max_length=100, null=True, blank=True)  # Stock Transfer Order number
    started_at = models.DateTimeField(null=True, blank=True)
    origin_confirmed_at = models.DateTimeField(null=True, blank=True)
    ms_departure_at = models.DateTimeField(null=True, blank=True)  # When vehicle left MS
    dbs_arrival_at = models.DateTimeField(null=True, blank=True)
    dbs_departure_at = models.DateTimeField(null=True, blank=True)
    ms_return_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    rtkm_km = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    route_deviation = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'trips'

class MSFilling(models.Model):
    """
    Filling data at MS.
    """
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='ms_fillings')
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    prefill_pressure_bar = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    topup_pressure_bar = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True) # Renamed or added if needed, but sticking to user request
    postfill_pressure_bar = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    prefill_mfm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    postfill_mfm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    filled_qty_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    confirmed_by_ms_operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='confirmed_fillings')
    confirmed_by_driver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='driver_confirmed_fillings')
    
    # Photo Evidence
    prefill_photo = models.ImageField(upload_to='ms_fillings/pre/', null=True, blank=True)
    postfill_photo = models.ImageField(upload_to='ms_fillings/post/', null=True, blank=True)

    class Meta:
        db_table = 'ms_filling'

class DBSDecanting(models.Model):
    """
    Decanting data at DBS.
    """
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='dbs_decantings')
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    pre_dec_reading = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    post_dec_reading = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    pre_dec_pressure_bar = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    post_dec_pressure_bar = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    delivered_qty_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    confirmed_by_dbs_operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='confirmed_decantings')
    confirmed_by_driver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='driver_confirmed_decantings')
    
    # Photo Evidence
    pre_decant_photo = models.ImageField(upload_to='dbs_decantings/pre/', null=True, blank=True)
    post_decant_photo = models.ImageField(upload_to='dbs_decantings/post/', null=True, blank=True)

    class Meta:
        db_table = 'dbs_decanting'

class Reconciliation(models.Model):
    """
    Reconciliation of trip quantities.
    """
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='reconciliations')
    ms_filled_qty_kg = models.DecimalField(max_digits=10, decimal_places=2)
    dbs_delivered_qty_kg = models.DecimalField(max_digits=10, decimal_places=2)
    diff_qty = models.DecimalField(max_digits=10, decimal_places=2)
    variance_pct = models.DecimalField(max_digits=5, decimal_places=2)
    status = models.CharField(max_length=20) # OK, ALERT

    class Meta:
        db_table = 'reconciliation'

class Alert(models.Model):
    """
    System alerts.
    """
    type = models.CharField(max_length=50)
    severity = models.CharField(max_length=20)
    message = models.TextField()
    trip = models.ForeignKey(Trip, on_delete=models.SET_NULL, null=True, blank=True)
    station = models.ForeignKey(Station, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'alerts'
