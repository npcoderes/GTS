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
    rfid_tag_id = models.CharField(max_length=100, null=True, blank=True)
    registration_document = models.FileField(
        upload_to='vehicles/documents/',
        null=True,
        blank=True,
        help_text='Vehicle registration document (PDF, PNG, JPG). Max 5MB.'
    )

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
    license_document = models.FileField(
        upload_to='drivers/licenses/',
        null=True,
        blank=True,
        help_text='Driver license document (PDF, PNG, JPG). Max 5MB.'
    )

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
        ('EXPIRED', 'Expired'),
    ]

    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='shifts')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='shifts')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    is_recurring = models.BooleanField(default=False)
    recurrence_pattern = models.CharField(max_length=20, default='NONE') # DAILY, WEEKLY, etc.
    shift_template = models.ForeignKey('ShiftTemplate', on_delete=models.SET_NULL, null=True, blank=True, related_name='shifts')
    notes = models.TextField(null=True, blank=True)
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
        ('QUEUED', 'Queued'),   #not reuired 
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'), #not reuired 
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
    
    # Queue fields for auto-allocation
    queue_position = models.PositiveIntegerField(null=True, blank=True, help_text='Position in approval queue for FCFS ordering')
    approved_at = models.DateTimeField(null=True, blank=True, help_text='When EIC approved this request')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_stock_requests')
    allocated_vehicle_token = models.ForeignKey('VehicleToken', on_delete=models.SET_NULL, null=True, blank=True, related_name='allocated_requests')

    class Meta:
        db_table = 'stock_requests'
        indexes = [
            models.Index(fields=['status', 'approved_at']),  # For queue queries
        ]

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


class VehicleToken(models.Model):
    """
    Vehicle queue tokens at Mother Stations.
    
    Drivers request tokens when arriving at MS during active shift.
    Token grants queue position (FCFS). When approved stock request 
    exists, system auto-allocates to first waiting token.
    
    Daily sequence resets at midnight. Once allocated to a trip,
    token is consumed and cannot be reused.
    """
    STATUS_CHOICES = [
        ('WAITING', 'Waiting in Queue'),
        ('ALLOCATED', 'Allocated to Trip'),
        ('EXPIRED', 'Expired/Cancelled'),
    ]
    
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='queue_tokens')
    driver = models.ForeignKey('Driver', on_delete=models.CASCADE, related_name='queue_tokens')
    ms = models.ForeignKey(Station, on_delete=models.CASCADE, related_name='vehicle_tokens')
    shift = models.ForeignKey('Shift', on_delete=models.SET_NULL, null=True, blank=True, related_name='tokens')
    
    # Queue identification
    token_no = models.CharField(max_length=30, unique=True, help_text='Format: MS{ms_id}-{date}-{seq}')
    sequence_number = models.PositiveIntegerField(help_text='Daily sequence per MS, resets at midnight')
    token_date = models.DateField(help_text='Date for sequence reset tracking')
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='WAITING')
    issued_at = models.DateTimeField(auto_now_add=True)
    allocated_at = models.DateTimeField(null=True, blank=True)
    expired_at = models.DateTimeField(null=True, blank=True)
    expiry_reason = models.CharField(max_length=100, null=True, blank=True)
    
    # Link to created trip when allocated
    trip = models.OneToOneField('Trip', on_delete=models.SET_NULL, null=True, blank=True, related_name='vehicle_token')
    
    class Meta:
        db_table = 'vehicle_tokens'
        ordering = ['token_date', 'sequence_number']
        indexes = [
            models.Index(fields=['ms', 'status', 'token_date']),
            models.Index(fields=['driver', 'status']),
            models.Index(fields=['token_date', 'sequence_number']),
        ]
        # Ensure unique sequence per MS per day
        unique_together = [['ms', 'token_date', 'sequence_number']]
    
    def __str__(self):
        return f"{self.token_no} ({self.status})"


class Trip(models.Model):
    """
    Trips managing the transport lifecycle.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('AT_MS', 'At MS'),
        # ('FILLING', 'Filling'),
        ('FILLED', 'Filled'),
        # ('DISPATCHED', 'Dispatched'),
        ('IN_TRANSIT', 'In Transit'),
        ('AT_DBS', 'At DBS'),
        # ('DECANTING_STARTED', 'Decanting Started'),
        # ('DECANTING_COMPLETE', 'Decanting Complete'),
        ('DECANTING_CONFIRMED', 'Decanting Confirmed'),
        ('RETURNED_TO_MS', 'Returned to MS'),
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
    
    # MS arrival confirmation by operator
    ms_arrival_confirmed = models.BooleanField(default=False)
    ms_arrival_confirmed_at = models.DateTimeField(null=True, blank=True)
    
    # DBS arrival confirmation by operator
    dbs_arrival_confirmed = models.BooleanField(default=False)
    dbs_arrival_confirmed_at = models.DateTimeField(null=True, blank=True)

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
        
        IMPORTANT: This method uses direct database queries to avoid stale prefetch cache.
        It is a read-only method and does NOT modify the trip status (no side effects).

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
        # Import here to avoid circular imports
        from .models import MSFilling, DBSDecanting
        
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
        # Use direct query to avoid stale prefetch cache
        dbs_decanting_exists = DBSDecanting.objects.filter(trip_id=self.id).exists()
        if self.status == 'AT_DBS' or dbs_decanting_exists:
            dbs_decanting = DBSDecanting.objects.filter(trip_id=self.id).first()
            
            if dbs_decanting:
                # Step 6: Both confirmed AND post-decant photo uploaded = Decanting complete, heading back to MS
                # Both confirmations mean they've reviewed and approved the post-decant data/photos
                if (dbs_decanting.confirmed_by_dbs_operator and 
                    dbs_decanting.confirmed_by_driver and
                    dbs_decanting.post_decant_photo):
                    # Update status and save to database
                    if self.status != 'DECANTING_CONFIRMED':
                        self.status = 'DECANTING_CONFIRMED'
                        self.save(update_fields=['status'])
                    return 6
                
                # Step 5: Decanting in progress but not fully confirmed yet
                # This includes: pre-decant done, decanting happening, or post-decant photo uploaded but not confirmed
                return 5
            
            # Should not reach here if status is AT_DBS but no decanting record
            return 5

        # Check if left MS and heading to DBS (step 4)
        if self.status == 'IN_TRANSIT' or self.ms_departure_at:
            return 4

        # Check if at MS or filling in progress (step 3)
        # Use direct query to avoid stale prefetch cache
        ms_filling_exists = MSFilling.objects.filter(trip_id=self.id).exists()
        if self.status == 'AT_MS' or ms_filling_exists:
            ms_filling = MSFilling.objects.filter(trip_id=self.id).first()
            
            if ms_filling:
                # Step 4: Both confirmed AND postfill photo uploaded = Filling complete, left MS
                # Both confirmations mean they've reviewed and approved the postfill data/photos
                if (ms_filling.confirmed_by_ms_operator and 
                    ms_filling.confirmed_by_driver and
                    ms_filling.postfill_photo):
                    # Update status and save to database
                    if self.status != 'IN_TRANSIT':
                        self.status = 'IN_TRANSIT'
                        self.save(update_fields=['status'])
                    return 4
                
                # Step 3: Filling in progress but not fully confirmed yet
                # This includes: prefill done, filling happening, or postfill photo uploaded but not confirmed
                return 3
            
            # Step 2: At MS but filling not started yet
            return 2

        # Arrived at MS (step 2)
        if self.origin_confirmed_at:
            return 2

        # Trip accepted (step 1)
        if self.started_at:
            return 1

        # No active trip (step 0)
        return 0

    def update_step(self, new_step):
        """
        Safely update current_step with validation.
        Ensures steps are updated sequentially (no skipping).
        """
        if new_step < 0 or new_step > 8:
            return False
        
        # Allow same step (idempotent)
        if new_step == self.current_step:
            return True
        
        # Allow backward movement (for corrections)
        if new_step < self.current_step:
            self.current_step = new_step
            return True
        
        # Only allow forward movement by 1 step at a time
        if new_step == self.current_step + 1:
            self.current_step = new_step
            return True
        
        # Reject skipping steps
        return False
    
    def get_step_details(self):
        """
        Get detailed step information including substep progress.
        Returns comprehensive data for resume functionality.
        
        IMPORTANT: This method forces a fresh database query for related objects
        to avoid stale prefetch cache issues when DBS/MS operators have just saved data.
        """
        # Force refresh from database to get latest data (avoid stale prefetch cache)
        from .models import MSFilling, DBSDecanting
        
        step = self.calculate_current_step()
        details = {
            'current_step': step,
            'step_data': self.step_data,
            'trip_id': self.id,
            'token': self.token.token_no if self.token else None,
            'status': self.status,
        }

        # MS Filling details - include for step 3 and beyond (filling started or completed)
        # Use direct query to avoid stale prefetch cache
        if step >= 3:
            ms_filling = MSFilling.objects.filter(trip_id=self.id).first()
            if ms_filling:
                details['ms_filling'] = {
                    'id': ms_filling.id,
                    'prefill_pressure_bar': str(ms_filling.prefill_pressure_bar) if ms_filling.prefill_pressure_bar else None,
                    'prefill_mfm': str(ms_filling.prefill_mfm) if ms_filling.prefill_mfm else None,
                    'postfill_pressure_bar': str(ms_filling.postfill_pressure_bar) if ms_filling.postfill_pressure_bar else None,
                    'postfill_mfm': str(ms_filling.postfill_mfm) if ms_filling.postfill_mfm else None,
                    'filled_qty_kg': str(ms_filling.filled_qty_kg) if ms_filling.filled_qty_kg else None,
                    # Driver photos
                    'prefill_photo_url': ms_filling.prefill_photo.url if ms_filling.prefill_photo else None,
                    'postfill_photo_url': ms_filling.postfill_photo.url if ms_filling.postfill_photo else None,
                    # Operator photos
                    'prefill_photo_operator_url': ms_filling.prefill_photo_operator.url if ms_filling.prefill_photo_operator else None,
                    'postfill_photo_operator_url': ms_filling.postfill_photo_operator.url if ms_filling.postfill_photo_operator else None,
                    'confirmed_by_ms_operator': ms_filling.confirmed_by_ms_operator_id is not None,
                    'confirmed_by_driver': ms_filling.confirmed_by_driver_id is not None,
                    'start_time': ms_filling.start_time.isoformat() if ms_filling.start_time else None,
                    'end_time': ms_filling.end_time.isoformat() if ms_filling.end_time else None,
                }

        # DBS Decanting details - include for step 5 and beyond (decanting started or completed)
        # Use direct query to avoid stale prefetch cache
        if step >= 5:
            dbs_decanting = DBSDecanting.objects.filter(trip_id=self.id).first()
            if dbs_decanting:
                details['dbs_decanting'] = {
                    'id': dbs_decanting.id,
                    'pre_dec_pressure_bar': str(dbs_decanting.pre_dec_pressure_bar) if dbs_decanting.pre_dec_pressure_bar else None,
                    'pre_dec_reading': str(dbs_decanting.pre_dec_reading) if dbs_decanting.pre_dec_reading else None,
                    'post_dec_pressure_bar': str(dbs_decanting.post_dec_pressure_bar) if dbs_decanting.post_dec_pressure_bar else None,
                    'post_dec_reading': str(dbs_decanting.post_dec_reading) if dbs_decanting.post_dec_reading else None,
                    'delivered_qty_kg': str(dbs_decanting.delivered_qty_kg) if dbs_decanting.delivered_qty_kg else None,
                    # Driver photos
                    'pre_decant_photo_url': dbs_decanting.pre_decant_photo.url if dbs_decanting.pre_decant_photo else None,
                    'post_decant_photo_url': dbs_decanting.post_decant_photo.url if dbs_decanting.post_decant_photo else None,
                    # Operator photos
                    'pre_decant_photo_operator_url': dbs_decanting.pre_decant_photo_operator.url if dbs_decanting.pre_decant_photo_operator else None,
                    'post_decant_photo_operator_url': dbs_decanting.post_decant_photo_operator.url if dbs_decanting.post_decant_photo_operator else None,
                    'confirmed_by_dbs_operator': dbs_decanting.confirmed_by_dbs_operator_id is not None,
                    'confirmed_by_driver': dbs_decanting.confirmed_by_driver_id is not None,
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
    topup_pressure_bar = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    postfill_pressure_bar = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    prefill_mfm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    postfill_mfm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    filled_qty_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    confirmed_by_ms_operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='confirmed_fillings')
    confirmed_by_driver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='driver_confirmed_fillings')
    
    # Photo Evidence - Driver
    prefill_photo = models.ImageField(upload_to='ms_fillings/pre/driver/', null=True, blank=True)
    postfill_photo = models.ImageField(upload_to='ms_fillings/post/driver/', null=True, blank=True)
    
    # Photo Evidence - MS Operator
    prefill_photo_operator = models.ImageField(upload_to='ms_fillings/pre/operator/', null=True, blank=True)
    postfill_photo_operator = models.ImageField(upload_to='ms_fillings/post/operator/', null=True, blank=True)

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
    
    # Photo Evidence - Driver
    pre_decant_photo = models.ImageField(upload_to='dbs_decantings/pre/driver/', null=True, blank=True)
    post_decant_photo = models.ImageField(upload_to='dbs_decantings/post/driver/', null=True, blank=True)
    
    # Photo Evidence - DBS Operator
    pre_decant_photo_operator = models.ImageField(upload_to='dbs_decantings/pre/operator/', null=True, blank=True)
    post_decant_photo_operator = models.ImageField(upload_to='dbs_decantings/post/operator/', null=True, blank=True)

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


class ShiftTemplate(models.Model):
    """
    Reusable shift templates for quick assignment.
    E.g., Morning (06:00-14:00), Night (22:00-06:00)
    """
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    color = models.CharField(max_length=20, default='#1890ff')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'shift_templates'
        ordering = ['start_time']

    def __str__(self):
        return f"{self.name} ({self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')})"
