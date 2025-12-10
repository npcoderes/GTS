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
    requested_qty_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
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

    # Step tracking for driver app resume functionality
    current_step = models.IntegerField(default=0)  # 0-7: tracks current trip step
    step_data = models.JSONField(default=dict, blank=True)  # Stores partial progress data
    last_activity_at = models.DateTimeField(auto_now=True)  # Auto-updated on any change

    class Meta:
        db_table = 'trips'

    def calculate_current_step(self):
        """
        Auto-calculate current step based on trip state.
        Used by resume API to ensure accuracy.

        Step Mapping:
        0: No trip / Initial state
        1: Trip accepted (status=PENDING)
        2: Arrived at MS (status=AT_MS)
        3: MS Filling in progress (has MSFilling record)
        4: Departed MS, heading to DBS (status=IN_TRANSIT/DISPATCHED)
        5: At DBS / Decanting in progress (status=AT_DBS or has DBSDecanting)
        6: Decanting confirmed, navigating back to MS (status=DECANTING_CONFIRMED)
        7: Trip completion screen (status=COMPLETED)
        """
        # Cancelled trips reset to 0
        if self.status == 'CANCELLED':
            return 0

        # Completed trips are at step 7
        if self.status == 'COMPLETED':
            return 7

        # Decanting confirmed, navigating back to MS (step 6)
        if self.status == 'DECANTING_CONFIRMED':
            return 6

        # Check if at DBS or decanting (step 5)
        if self.status == 'AT_DBS' or self.dbs_decantings.exists():
            # If decanting confirmed by operator, move to step 6
            if self.dbs_decantings.filter(confirmed_by_dbs_operator__isnull=False).exists():
                return 6
            return 5

        # Check if left MS and heading to DBS (step 4)
        if self.status == 'IN_TRANSIT' or self.ms_departure_at:
            return 4

        # Check if at MS or filling in progress (step 3)
        if self.status == 'AT_MS' or self.ms_fillings.exists():
            # If already left MS, should be step 4
            if self.ms_departure_at:
                return 4
            # If at MS or filling in progress
            return 3 if self.ms_fillings.exists() else 2

        # Arrived at MS (step 2)
        if self.origin_confirmed_at:
            return 2

        # Trip accepted (step 1)
        if self.started_at:
            return 1

        # No active trip (step 0)
        return 0

    def get_step_details(self):
        """
        Get detailed step information including substep progress.
        Returns comprehensive data for resume functionality.
        """
        step = self.calculate_current_step()
        details = {
            'current_step': step,
            'step_data': self.step_data,
            'trip_id': self.id,
            'token': self.token.token_no if self.token else None,
            'status': self.status,
        }

        # Step 3: MS Filling details
        if step == 3:
            ms_filling = self.ms_fillings.first()
            if ms_filling:
                details['ms_filling'] = {
                    'id': ms_filling.id,
                    'prefill_pressure_bar': str(ms_filling.prefill_pressure_bar) if ms_filling.prefill_pressure_bar else None,
                    'prefill_mfm': str(ms_filling.prefill_mfm) if ms_filling.prefill_mfm else None,
                    'postfill_pressure_bar': str(ms_filling.postfill_pressure_bar) if ms_filling.postfill_pressure_bar else None,
                    'postfill_mfm': str(ms_filling.postfill_mfm) if ms_filling.postfill_mfm else None,
                    'filled_qty_kg': str(ms_filling.filled_qty_kg) if ms_filling.filled_qty_kg else None,
                    'prefill_photo_url': ms_filling.prefill_photo.url if ms_filling.prefill_photo else None,
                    'postfill_photo_url': ms_filling.postfill_photo.url if ms_filling.postfill_photo else None,
                    'confirmed_by_ms_operator': ms_filling.confirmed_by_ms_operator_id is not None,
                    'start_time': ms_filling.start_time.isoformat() if ms_filling.start_time else None,
                    'end_time': ms_filling.end_time.isoformat() if ms_filling.end_time else None,
                }

        # Step 5: DBS Decanting details
        if step == 5:
            dbs_decanting = self.dbs_decantings.first()
            if dbs_decanting:
                details['dbs_decanting'] = {
                    'id': dbs_decanting.id,
                    'pre_dec_pressure_bar': str(dbs_decanting.pre_dec_pressure_bar) if dbs_decanting.pre_dec_pressure_bar else None,
                    'pre_dec_reading': str(dbs_decanting.pre_dec_reading) if dbs_decanting.pre_dec_reading else None,
                    'post_dec_pressure_bar': str(dbs_decanting.post_dec_pressure_bar) if dbs_decanting.post_dec_pressure_bar else None,
                    'post_dec_reading': str(dbs_decanting.post_dec_reading) if dbs_decanting.post_dec_reading else None,
                    'delivered_qty_kg': str(dbs_decanting.delivered_qty_kg) if dbs_decanting.delivered_qty_kg else None,
                    'pre_decant_photo_url': dbs_decanting.pre_decant_photo.url if dbs_decanting.pre_decant_photo else None,
                    'post_decant_photo_url': dbs_decanting.post_decant_photo.url if dbs_decanting.post_decant_photo else None,
                    'confirmed_by_dbs_operator': dbs_decanting.confirmed_by_dbs_operator_id is not None,
                    'start_time': dbs_decanting.start_time.isoformat() if dbs_decanting.start_time else None,
                    'end_time': dbs_decanting.end_time.isoformat() if dbs_decanting.end_time else None,
                }

        return details

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
