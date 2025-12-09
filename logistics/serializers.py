from rest_framework import serializers
from .models import (
    Vehicle, Driver, StockRequest, Token, Trip,
    MSFilling, DBSDecanting, Reconciliation, Alert, Shift
)
from core.serializers import UserSerializer, StationSerializer
from core.models import User

class VehicleSerializer(serializers.ModelSerializer):
    vendor_details = UserSerializer(source='vendor', read_only=True)
    ms_home_details = StationSerializer(source='ms_home', read_only=True)

    class Meta:
        model = Vehicle
        fields = '__all__'

class DriverSerializer(serializers.ModelSerializer):
    vendor_details = UserSerializer(source='vendor', read_only=True)
    user_details = UserSerializer(source='user', read_only=True)
    assigned_vehicle_details = VehicleSerializer(source='assigned_vehicle', read_only=True)
    
    email = serializers.EmailField(write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=False, style={'input_type': 'password'})

    class Meta:
        model = Driver
        fields = '__all__'
        extra_kwargs = {
            'user': {'read_only': True},
            'vendor': {'required': False},
        }

    def create(self, validated_data):
        email = validated_data.pop('email', None)
        password = validated_data.pop('password', None)
        
        request = self.context.get('request')
        if request and hasattr(request, 'user') and not validated_data.get('vendor'):
            validated_data['vendor'] = request.user
            
        if not email or not password:
            raise serializers.ValidationError("Email and Password are required for new driver.")
            
        from core.models import User, Role, UserRole
        from django.db import transaction
        
        with transaction.atomic():
            if User.objects.filter(email=email).exists():
                raise serializers.ValidationError({"email": "User with this email already exists."})
                
            user = User.objects.create_user(
                email=email, 
                password=password, 
                full_name=validated_data.get('full_name', '')
            )
            
            role, _ = Role.objects.get_or_create(code='DRIVER', defaults={'name': 'Driver'})
            UserRole.objects.create(user=user, role=role)
            
            validated_data['user'] = user
            driver = super().create(validated_data)
                    
        return driver

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
    quantity = serializers.DecimalField(source='requested_qty_kg', max_digits=10, decimal_places=2)
    requestedAt = serializers.DateTimeField(source='created_at')
    availableDrivers = serializers.SerializerMethodField()
    
    class Meta:
        model = StockRequest
        fields = ['id', 'type', 'status', 'priority_preview', 'customer', 'dbsId', 'quantity', 'requestedAt', 'availableDrivers']
        
    def get_id(self, obj):
        return f"{obj.id}"
        
    def get_customer(self, obj):
        return obj.dbs.name if obj.dbs else "Unknown"
        
    def get_dbsId(self, obj):
        return obj.dbs.name if obj.dbs else "Unknown"
    
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

    class Meta:
        model = Trip
        fields = '__all__'

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

    class Meta:
        model = MSFilling
        fields = '__all__'

class DBSDecantingSerializer(serializers.ModelSerializer):
    trip_details = TripSerializer(source='trip', read_only=True)
    confirmed_by_dbs_operator_details = UserSerializer(source='confirmed_by_dbs_operator', read_only=True)

    class Meta:
        model = DBSDecanting
        fields = '__all__'

class ReconciliationSerializer(serializers.ModelSerializer):
    trip_details = TripSerializer(source='trip', read_only=True)

    class Meta:
        model = Reconciliation
        fields = '__all__'

class AlertSerializer(serializers.ModelSerializer):
    trip_details = TripSerializer(source='trip', read_only=True)
    station_details = StationSerializer(source='station', read_only=True)

    class Meta:
        model = Alert
        fields = '__all__'
