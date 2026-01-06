from rest_framework import serializers
from .models import (
    Vehicle, Driver, StockRequest, Token, Trip,
    MSFilling, DBSDecanting, Reconciliation, Alert, Shift, ShiftTemplate
)
from core.serializers import UserSerializer, StationSerializer
from core.models import User

class VehicleSerializer(serializers.ModelSerializer):
    vendor_details = UserSerializer(source='vendor', read_only=True)
    ms_home_details = StationSerializer(source='ms_home', read_only=True)
    registration_document_url = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = '__all__'
        extra_kwargs = {
            'vendor': {'required': False},
            'registration_document': {'required': False, 'write_only': True},
        }

    def get_registration_document_url(self, obj):
        if obj.registration_document:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.registration_document.url)
            return obj.registration_document.url
        return None

    def validate_registration_document(self, value):
        if value:
            # 5MB limit
            max_size = 5 * 1024 * 1024
            if value.size > max_size:
                raise serializers.ValidationError("Document size must be less than 5MB.")
            # Validate file type
            allowed_types = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg']
            if hasattr(value, 'content_type') and value.content_type not in allowed_types:
                raise serializers.ValidationError("Only PDF, PNG, and JPG files are allowed.")
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and not validated_data.get('vendor'):
            validated_data['vendor'] = request.user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Don't allow changing vendor during update, keep the original
        validated_data.pop('vendor', None)
        return super().update(instance, validated_data)

class DriverSerializer(serializers.ModelSerializer):
    vendor_details = UserSerializer(source='vendor', read_only=True)
    user_details = UserSerializer(source='user', read_only=True)
    assigned_vehicle_details = VehicleSerializer(source='assigned_vehicle', read_only=True)
    license_document_url = serializers.SerializerMethodField()
    
    email = serializers.EmailField(write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=False, style={'input_type': 'password'})

    class Meta:
        model = Driver
        fields = '__all__'
        extra_kwargs = {
            'user': {'read_only': True},
            'vendor': {'required': False},
            'license_document': {'required': False, 'write_only': True},
        }

    def get_license_document_url(self, obj):
        if obj.license_document:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.license_document.url)
            return obj.license_document.url
        return None

    def validate_license_document(self, value):
        if value:
            # 5MB limit
            max_size = 5 * 1024 * 1024
            if value.size > max_size:
                raise serializers.ValidationError("Document size must be less than 5MB.")
            # Validate file type
            allowed_types = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg']
            if hasattr(value, 'content_type') and value.content_type not in allowed_types:
                raise serializers.ValidationError("Only PDF, PNG, and JPG files are allowed.")
        return value

    def validate_assigned_vehicle(self, value):
        """Validate that a vehicle can have maximum 2 drivers assigned."""
        if value is None:
            return value
            
        # Get current instance (for update case)
        instance = getattr(self, 'instance', None)
        
        # Count drivers currently assigned to this vehicle
        current_driver_count = Driver.objects.filter(assigned_vehicle=value).count()
        
        # If updating and driver already has this vehicle, don't count them
        if instance and instance.assigned_vehicle_id == value.id:
            return value
            
        # Check if vehicle already has 2 drivers
        if current_driver_count >= 2:
            raise serializers.ValidationError(
                f"Vehicle {value.registration_no} already has 2 drivers assigned. Maximum 2 drivers per vehicle allowed."
            )
        
        return value

    def create(self, validated_data):
        email = validated_data.pop('email', None)
        password = validated_data.pop('password', None)
        phone = validated_data.get('phone')
        
        request = self.context.get('request')
        if request and hasattr(request, 'user') and not validated_data.get('vendor'):
            validated_data['vendor'] = request.user
            
        if not email or not password or not phone:
            raise serializers.ValidationError("Email, Phone, and Password are required for new driver.")
            
        from core.models import User, Role, UserRole
        from core.utils import send_welcome_email
        from django.db import transaction
        import logging
        
        logger = logging.getLogger(__name__)
        
        with transaction.atomic():
            if User.objects.filter(email=email).exists():
                raise serializers.ValidationError({"email": "User with this email already exists."})
            if User.objects.filter(phone=phone).exists():
                raise serializers.ValidationError({"phone": "User with this phone already exists."})
                
            user = User.objects.create_user(
                email=email, 
                password=password, 
                full_name=validated_data.get('full_name', ''),
                phone=phone
            )
            # Force password reset on first login
            user.is_password_reset_required = True
            user.save(update_fields=['is_password_reset_required'])
            
            role, _ = Role.objects.get_or_create(code='DRIVER', defaults={'name': 'Driver'})
            UserRole.objects.create(user=user, role=role)
            
            validated_data['user'] = user
            driver = super().create(validated_data)
            
            # Send welcome email with credentials
            try:
                send_welcome_email(user, password)
            except Exception as e:
                logger.error(f"Failed to send welcome email to driver {user.email}: {e}", exc_info=True)
                    
        return driver

    def update(self, instance, validated_data):
        # Don't allow changing vendor during update, keep the original
        validated_data.pop('vendor', None)
        # Remove email/password from update - can't change driver credentials here
        validated_data.pop('email', None)
        validated_data.pop('password', None)
        return super().update(instance, validated_data)

class ShiftSerializer(serializers.ModelSerializer):
    driver_details = DriverSerializer(source='driver', read_only=True)
    vehicle_details = VehicleSerializer(source='vehicle', read_only=True)
    approved_by_details = UserSerializer(source='approved_by', read_only=True)

    class Meta:
        model = Shift
        fields = '__all__'

class StockRequestSerializer(serializers.ModelSerializer):
    dbs_details = StationSerializer(source='dbs', read_only=True)
    source_vendor_details = UserSerializer(source='source_vendor', read_only=True)
    requested_by_user_details = UserSerializer(source='requested_by_user', read_only=True)

    class Meta:
        model = StockRequest
        fields = '__all__'
        read_only_fields = ['dbs', 'source', 'status', 'created_at', 'requested_by_user', 'priority_preview']

class EICStockRequestListSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    type = serializers.CharField(source='source')
    customer = serializers.SerializerMethodField()
    dbsId = serializers.SerializerMethodField()
    quantity = serializers.DecimalField(source='requested_qty_kg', max_digits=10, decimal_places=2, allow_null=True, required=False)
    requestedAt = serializers.DateTimeField(source='created_at')
    requiredBy = serializers.SerializerMethodField()
    availableDrivers = serializers.SerializerMethodField()
    
    class Meta:
        model = StockRequest
        fields = ['id', 'type', 'status', 'priority_preview', 'customer', 'dbsId', 'quantity', 'requestedAt', 'requiredBy', 'availableDrivers']
        
    def get_id(self, obj):
        return f"{obj.id}"
        
    def get_customer(self, obj):
        return obj.dbs.name if obj.dbs else "Unknown"
        
    def get_dbsId(self, obj):
        return obj.dbs.name if obj.dbs else "Unknown"
    
    def get_requiredBy(self, obj):
        """Combine requested_by_date and requested_by_time into ISO format"""
        if obj.requested_by_date and obj.requested_by_time:
            from datetime import datetime
            from django.utils import timezone
            dt = datetime.combine(obj.requested_by_date, obj.requested_by_time)
            dt = timezone.make_aware(dt)
            return dt.isoformat()
        return None
    
    def get_availableDrivers(self, obj):
        """Get available drivers for this stock request's MS"""
        from .services import get_available_drivers
        
        # Only show available drivers for PENDING or APPROVED requests
        if obj.status not in ['PENDING', 'APPROVED']:
            return []
        
        # Get the parent MS of the DBS
        if not obj.dbs or not obj.dbs.parent_station:
            return []
        
        ms_id = obj.dbs.parent_station.id
        available = get_available_drivers(ms_id)
        
        # Format driver details
        drivers = []
        for item in available:
            driver = item['driver']
            vehicle = item['vehicle']
            drivers.append({
                'driverId': driver.id,
                'driverName': driver.full_name,
                'driverPhone': driver.phone or '',
                'vehicleId': vehicle.id,
                'vehicleRegNo': vehicle.registration_no,
                'tripCountToday': item['trip_count']
            })
        
        return drivers
        
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Rename priority_preview to priority and map to full name
        priority_map = {
            'H': 'High',
            'C': 'Critical',
            'N': 'Normal',
            'FDODO': 'FDODO'
        }
        raw_priority = data.pop('priority_preview')
        data['priority'] = priority_map.get(raw_priority, raw_priority)
        return data

class TokenSerializer(serializers.ModelSerializer):
    vehicle_details = VehicleSerializer(source='vehicle', read_only=True)
    ms_details = StationSerializer(source='ms', read_only=True)

    class Meta:
        model = Token
        fields = '__all__'

class TripSerializer(serializers.ModelSerializer):
    vehicle_details = VehicleSerializer(source='vehicle', read_only=True)
    driver_details = DriverSerializer(source='driver', read_only=True)
    ms_details = StationSerializer(source='ms', read_only=True)
    dbs_details = StationSerializer(source='dbs', read_only=True)
    token_details = TokenSerializer(source='token', read_only=True)
    reconciliations = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = '__all__'
    
    def get_reconciliations(self, obj):
        """Include reconciliation data for completed trips"""
        if obj.status == 'COMPLETED':
            recons = obj.reconciliations.all()
            return ReconciliationSerializer(recons, many=True).data
        return []

class TripHistorySerializer(serializers.ModelSerializer):
    """Serializer for driver trip history with specific frontend format."""
    tripId = serializers.IntegerField(source='id', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    acceptedAt = serializers.DateTimeField(source='started_at', read_only=True, allow_null=True)
    completedAt = serializers.DateTimeField(source='completed_at', read_only=True, allow_null=True)
    msLocation = serializers.SerializerMethodField()
    dbsLocation = serializers.SerializerMethodField()
    deliveredQty = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = ['tripId', 'status', 'createdAt', 'acceptedAt', 'completedAt', 
                  'msLocation', 'dbsLocation', 'deliveredQty']

    def get_msLocation(self, obj):
        return {'name': obj.ms.name} if obj.ms else None

    def get_dbsLocation(self, obj):
        return {'name': obj.dbs.name} if obj.dbs else None

    def get_deliveredQty(self, obj):
        # Priority: DBSDecanting -> MSFilling -> StockRequest
        decanting = obj.dbs_decantings.first()
        if decanting and decanting.delivered_qty_kg:
            return float(decanting.delivered_qty_kg)
        
        filling = obj.ms_fillings.first()
        if filling and filling.filled_qty_kg:
            return float(filling.filled_qty_kg)
        
        if obj.stock_request and obj.stock_request.requested_qty_kg:
            return float(obj.stock_request.requested_qty_kg)
        
        return None

class MSFillingSerializer(serializers.ModelSerializer):
    trip_details = TripSerializer(source='trip', read_only=True)
    confirmed_by_ms_operator_details = UserSerializer(source='confirmed_by_ms_operator', read_only=True)
    prefill_photo_operator = serializers.ImageField(read_only=True)
    postfill_photo_operator = serializers.ImageField(read_only=True)

    class Meta:
        model = MSFilling
        fields = '__all__'

class DBSDecantingSerializer(serializers.ModelSerializer):
    trip_details = TripSerializer(source='trip', read_only=True)
    confirmed_by_dbs_operator_details = UserSerializer(source='confirmed_by_dbs_operator', read_only=True)
    pre_decant_photo_operator = serializers.ImageField(read_only=True)
    post_decant_photo_operator = serializers.ImageField(read_only=True)

    class Meta:
        model = DBSDecanting
        fields = '__all__'

class ReconciliationSerializer(serializers.ModelSerializer):
    # Remove trip_details to avoid circular reference
    # trip_details = TripSerializer(source='trip', read_only=True)

    class Meta:
        model = Reconciliation
        fields = '__all__'

class AlertSerializer(serializers.ModelSerializer):
    trip_details = TripSerializer(source='trip', read_only=True)
    station_details = StationSerializer(source='station', read_only=True)

    class Meta:
        model = Alert
        fields = '__all__'


class ShiftTemplateSerializer(serializers.ModelSerializer):
    """Serializer for ShiftTemplate model."""
    
    class Meta:
        model = ShiftTemplate
        fields = ['id', 'name', 'code', 'start_time', 'end_time', 'color', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']
