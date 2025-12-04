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
    vendor = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(user_roles__role__code='SGL_TRANSPORT_VENDOR'))

    class Meta:
        model = Vehicle
        fields = '__all__'

class DriverSerializer(serializers.ModelSerializer):
    vendor_details = UserSerializer(source='vendor', read_only=True)
    user_details = UserSerializer(source='user', read_only=True)
    assigned_vehicle_details = VehicleSerializer(source='assigned_vehicle', read_only=True)
    vendor = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(user_roles__role__code='SGL_TRANSPORT_VENDOR'))

    class Meta:
        model = Driver
        fields = '__all__'

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
    
    class Meta:
        model = StockRequest
        fields = ['id', 'type', 'status', 'priority_preview', 'customer', 'dbsId', 'quantity', 'requestedAt']
        
    def get_id(self, obj):
        return f"{obj.id}"
        
    def get_customer(self, obj):
        return obj.dbs.name if obj.dbs else "Unknown"
        
    def get_dbsId(self, obj):
        return obj.dbs.name if obj.dbs else "Unknown"
        
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
