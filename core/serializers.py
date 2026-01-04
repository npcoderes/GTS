from rest_framework import serializers
from core.models import User, Role, UserRole, Station, Route, MSDBSMap
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password

class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'phone', 'role_in', 'role_out', 
                  'is_active', 'is_staff', 'date_joined', 'password', 'roles', 
                  'is_password_reset_required', 'mpin']
        read_only_fields = ['date_joined', 'mpin']
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
            'email': {'required': False, 'allow_null': True, 'allow_blank': True}
        }

    def validate(self, data):
        if self.instance is None and not data.get('password'):
             raise serializers.ValidationError({"password": "Password is required for new users."})
        return data
    
    def get_roles(self, obj):
        active_roles = UserRole.objects.filter(user=obj, active=True)
        return [
            {
                'role_code': ur.role.code,
                'role_name': ur.role.name,
                'station_id': ur.station.id if ur.station else None,
                'station_name': ur.station.name if ur.station else None,
                'station_code': ur.station.code if ur.station else None,
                'station_type': ur.station.type if ur.station else None,
            }
            for ur in active_roles
        ]

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        # New users created by admin must reset password
        validated_data['is_password_reset_required'] = True
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class RoleSerializer(serializers.ModelSerializer):
    """Serializer for Role model"""
    
    class Meta:
        model = Role
        fields = ['id', 'code', 'name', 'description']


class StationSerializer(serializers.ModelSerializer):
    """Serializer for Station model"""
    
    class Meta:
        model = Station
        fields = ['id', 'type', 'code', 'name', 'address', 'city', 'lat', 'lng', 'geofence_radius_m', 'parent_station']


class UserRoleSerializer(serializers.ModelSerializer):
    """Serializer for UserRole model"""
    role_detail = RoleSerializer(source='role', read_only=True)
    station_detail = StationSerializer(source='station', read_only=True)
    user_detail = UserSerializer(source='user', read_only=True)
    
    class Meta:
        model = UserRole
        fields = ['id', 'user', 'role', 'station', 'active', 'created_at', 
                  'updated_at', 'role_detail', 'station_detail', 'user_detail']
        read_only_fields = ['created_at', 'updated_at']


class LoginSerializer(serializers.Serializer):
    """Serializer for login"""
    username = serializers.CharField()
    email = serializers.EmailField(required=False)
    password = serializers.CharField(write_only=True, required=False)
    mpin = serializers.CharField(write_only=True, required=False)
    role = serializers.CharField(write_only=True, required=False)

    def validate(self, data):
        if not data.get('password') and not data.get('mpin'):
            raise serializers.ValidationError("Either password or mpin is required.")
        return data


class MPINLoginSerializer(serializers.Serializer):
    """Serializer for MPIN login"""
    username = serializers.CharField()
    mpin = serializers.CharField(write_only=True, max_length=4)


class SetMPINSerializer(serializers.Serializer):
    """Serializer for setting MPIN"""
    mpin = serializers.CharField(write_only=True, max_length=4, min_length=4)
    password = serializers.CharField(write_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password"""
    old_password = serializers.CharField(write_only=True, required=False)
    new_password = serializers.CharField(write_only=True)
    mpin = serializers.CharField(write_only=True, required=False, max_length=4, min_length=4)


class PasswordResetRequestSerializer(serializers.Serializer):
    """Step 1: Request OTP by Email/Phone"""
    username = serializers.CharField() # Accepts Email or Phone

class PasswordResetVerifySerializer(serializers.Serializer):
    """Step 2: Verify OTP"""
    username = serializers.CharField()
    otp = serializers.CharField(min_length=6, max_length=6)

class PasswordResetConfirmSerializer(serializers.Serializer):
    """Step 3: Reset Password with Token"""
    reset_token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)
    mpin = serializers.CharField(write_only=True, min_length=4, max_length=4)


class RouteSerializer(serializers.ModelSerializer):
    """Serializer for Route model"""
    ms_detail = StationSerializer(source='ms', read_only=True)
    dbs_detail = StationSerializer(source='dbs', read_only=True)
    
    class Meta:
        model = Route
        fields = ['id', 'ms', 'dbs', 'code', 'name', 'planned_rtkm_km', 
                  'is_default', 'is_active', 'ms_detail', 'dbs_detail']


class MSDBSMapSerializer(serializers.ModelSerializer):
    """Serializer for MS-DBS Map model"""
    ms_detail = StationSerializer(source='ms', read_only=True)
    dbs_detail = StationSerializer(source='dbs', read_only=True)
    
    class Meta:
        model = MSDBSMap
        fields = ['id', 'ms', 'dbs', 'active', 'ms_detail', 'dbs_detail']
