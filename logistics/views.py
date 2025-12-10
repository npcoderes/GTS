import logging
from rest_framework import viewsets, status, views, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import (
    Vehicle, Driver, StockRequest, Token, Trip,
    MSFilling, DBSDecanting, Reconciliation, Alert, Shift
)
from .serializers import (
    VehicleSerializer, DriverSerializer, StockRequestSerializer,
    TokenSerializer, TripSerializer, MSFillingSerializer,
    DBSDecantingSerializer, ReconciliationSerializer, AlertSerializer, ShiftSerializer,
    TripHistorySerializer
)
from core.models import Station, User

logger = logging.getLogger(__name__)

# --- Helper Functions ---
def get_trip_by_token(token_id):
    return get_object_or_404(Trip, token__token_no=token_id)

# --- ViewSets ---

class StockRequestViewSet(viewsets.ModelViewSet):
    """
    API Path: /api/stock-requests/
    Methods: GET (list), POST (create), GET (retrieve), PUT (update), DELETE (delete)
    Actions:
      - GET /api/stock-requests/ - List all stock requests
      - POST /api/stock-requests/ - Create new stock request
      - GET /api/stock-requests/{id}/ - Get stock request detail
      - PUT /api/stock-requests/{id}/ - Update stock request
      - DELETE /api/stock-requests/{id}/ - Delete stock request
    """
    queryset = StockRequest.objects.all()
    serializer_class = StockRequestSerializer

    def perform_create(self, serializer):
        user = self.request.user
        
        # Get primary role to determine source and DBS
        # We import the helper from core.views to ensure consistency
        from core.views import get_primary_role
        
        primary_role_assign = get_primary_role(user)
        
        if not primary_role_assign:
            raise serializers.ValidationError("User has no active role assignment")
            
        role_code = primary_role_assign.role.code
        station = primary_role_assign.station
        
        # Determine source based on role
        source = 'DBS_OPERATOR' # Default
        if role_code == 'AI_ENGINE':
            source = 'AI'
        elif role_code == 'FDODO':
            source = 'FDODO'
            
        # Determine DBS
        dbs = None
        if station and station.type == 'DBS':
            dbs = station
        
        if not dbs and role_code == 'DBS_OPERATOR':
             raise serializers.ValidationError("DBS Operator must be assigned to a station")

        stock_request = serializer.save(
            requested_by_user=user,
            source=source,
            dbs=dbs
        )

        # Notify EIC users of parent MS when a DBS operator raises a request
        try:
            if role_code == 'DBS_OPERATOR' and dbs and dbs.parent_station:
                from core.models import UserRole
                from core.notification_service import NotificationService

                eic_roles = UserRole.objects.filter(
                    role__code='EIC', active=True, station=dbs.parent_station
                ).select_related('user')

                if eic_roles:
                    notifier = NotificationService()
                    ms_name = dbs.parent_station.name or ''
                    dbs_name = dbs.name or ''
                    for eic_role in eic_roles:
                        if eic_role.user:
                            logger.info(
                                "Sending stock request notification to EIC user",
                                extra={
                                    'eic_user_id': eic_role.user.id,
                                    'eic_user_email': eic_role.user.email,
                                    'stock_request_id': stock_request.id,
                                    'dbs_id': getattr(dbs, 'id', None),
                                    'ms_id': getattr(dbs.parent_station, 'id', None)
                                }
                            )
                            notifier.send_to_user(
                                user=eic_role.user,
                                title="New Stock Request",
                                body=f"{dbs_name} requested stock from {ms_name}.",
                                data={
                                    'type': 'STOCK_REQUEST',
                                    'stockRequestId': str(stock_request.id),
                                    'dbsId': dbs.code if hasattr(dbs, 'code') else None,
                                    'dbsName': dbs_name,
                                    'msId': dbs.parent_station.code if hasattr(dbs.parent_station, 'code') else None,
                                    'msName': ms_name,
                                },
                                notification_type='stock_request'
                            )
        except Exception:
            # Do not block creation on notification issues
            pass

class TripViewSet(viewsets.ModelViewSet):
    """
    API Path: /api/trips/
    Methods: GET (list), POST (create), GET (retrieve), PUT (update), DELETE (delete)
    Actions:
      - GET /api/trips/ - List all trips
      - POST /api/trips/ - Create new trip
      - GET /api/trips/{id}/ - Get trip detail
      - PUT /api/trips/{id}/ - Update trip
      - DELETE /api/trips/{id}/ - Delete trip
      - GET /api/driver/trip/status?token={token} - Get trip status by token
    """
    queryset = Trip.objects.all()
    serializer_class = TripSerializer

    def get_queryset(self):
        queryset = Trip.objects.all()
        
        # Filter by DBS ID
        dbs_id = self.request.query_params.get('dbs_id')
        if dbs_id:
            queryset = queryset.filter(dbs_id=dbs_id)
            
        # Filter by Status (comma separated)
        status_param = self.request.query_params.get('status')
        if status_param:
            statuses = status_param.split(',')
            queryset = queryset.filter(status__in=statuses)
            
        return queryset.order_by('-id')



    @action(detail=False, methods=['get'])
    def status(self, request):
        token_id = request.query_params.get('token')
        if not token_id:
            return Response({'error': 'Token required'}, status=400)
        trip = get_trip_by_token(token_id)
        return Response(TripSerializer(trip).data)

class DriverViewSet(viewsets.ModelViewSet):
    """
    API Path: /api/drivers/
    Methods: GET (list), POST (create), GET (retrieve), PUT (update), DELETE (delete)
    Actions:
      - GET /api/drivers/ - List all drivers
      - POST /api/drivers/ - Create new driver
      - GET /api/drivers/{id}/ - Get driver detail
      - PUT /api/drivers/{id}/ - Update driver
      - DELETE /api/drivers/{id}/ - Delete driver
      - GET /api/driver/{id}/token - Get active token for driver
      - GET /api/driver/trips - Get trips for authenticated driver
      - GET /api/driver/{id}/trips - Get trips for specific driver
    """
    queryset = Driver.objects.all()
    serializer_class = DriverSerializer

    @action(detail=True, methods=['get'])
    def token(self, request, pk=None):
        driver = self.get_object()
        trip = Trip.objects.filter(
            driver=driver, 
            status__in=['PENDING', 'AT_MS', 'IN_TRANSIT', 'AT_DBS']
        ).first()
        
        if trip and trip.token:
            return Response(TokenSerializer(trip.token).data)
        return Response({'error': 'No active token'}, status=404)

    @action(detail=True, methods=['get'])
    def trips(self, request, pk=None):
        driver = self.get_object()
        trips = Trip.objects.filter(driver=driver).order_by('-id')
        
        page = self.paginate_queryset(trips)
        if page is not None:
            serializer = TripSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = TripSerializer(trips, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def current_driver_trips(self, request):
        """Get trip history for authenticated driver."""
        try:
            driver = request.user.driver_profile
        except (AttributeError, Driver.DoesNotExist):
            return Response({'error': 'User is not a driver'}, status=403)
        
        trips = (
        Trip.objects
        .filter(driver=driver)
        .exclude(status='COMPLETED')   # <-- IMPORTANT: filter only non-completed trips
        .select_related('ms', 'dbs', 'stock_request')
        .prefetch_related('dbs_decantings', 'ms_fillings')
        .order_by('-id')
        )
        
        serializer = TripHistorySerializer(trips, many=True)
        return Response({'trips': serializer.data})

class ShiftViewSet(viewsets.ModelViewSet):
    """
    API Path: /api/shifts/
    Methods: GET (list), POST (create), GET (retrieve), PUT (update), DELETE (delete)
    Actions:
      - GET /api/shifts/ - List all shifts
      - POST /api/shifts/ - Create new shift
      - GET /api/shifts/{id}/ - Get shift detail
      - PUT /api/shifts/{id}/ - Update shift
      - DELETE /api/shifts/{id}/ - Delete shift
      - POST /api/shifts/{id}/approve/ - Approve shift (EIC only)
      - POST /api/shifts/{id}/reject/ - Reject shift (EIC only)
    """
    queryset = Shift.objects.all()
    serializer_class = ShiftSerializer

    def get_queryset(self):
        queryset = Shift.objects.all()
        status_param = self.request.query_params.get('status', None)
        if status_param:
            queryset = queryset.filter(status=status_param)
        return queryset.order_by('-created_at')

    def create(self, request, *args, **kwargs):
        """
        Create shift with overlap validation.
        Prevents creating shifts for the same driver at overlapping times.
        """
        driver_id = request.data.get('driver')
        start_time = request.data.get('start_time')
        end_time = request.data.get('end_time')
        

        if driver_id and start_time and end_time:
            # 1. Check against One-time shifts (Standard overlap)
            overlapping_onetime = Shift.objects.filter(
                driver_id=driver_id,
                status__in=['PENDING', 'APPROVED'], 
                start_time__lt=end_time,
                end_time__gt=start_time,
                is_recurring=False
            )
            
            if overlapping_onetime.exists():
                overlap = overlapping_onetime.first()
                return Response({
                    'error': 'Overlapping shift exists',
                    'message': f'Driver already has a one-time shift from {overlap.start_time.strftime("%Y-%m-%d %H:%M")} to {overlap.end_time.strftime("%Y-%m-%d %H:%M")}',
                    'existing_shift_id': overlap.id
                }, status=status.HTTP_400_BAD_REQUEST)

            # 2. Check against Recurring shifts (Time-of-day overlap)
            # Fetch all active recurring shifts for driver
            existing_recurring = Shift.objects.filter(
                driver_id=driver_id,
                status__in=['PENDING', 'APPROVED'],
                is_recurring=True
            )
            
            new_start_time = start_time.time() if hasattr(start_time, 'time') else parse_datetime(start_time).time()
            new_end_time = end_time.time() if hasattr(end_time, 'time') else parse_datetime(end_time).time()
            
            for shift in existing_recurring:
                exist_start = shift.start_time.time()
                exist_end = shift.end_time.time()
                
                # Check time overlap
                overlap = False
                if exist_start <= exist_end:
                    if new_start_time < exist_end and new_end_time > exist_start:
                        overlap = True
                else: # Overnight
                    # Simplified overnight check: if ranges touch
                    overlap = True # Assume conflict for safety with overnight recurring
                
                if overlap:
                     return Response({
                        'error': 'Overlapping recurring shift',
                        'message': f'Driver has a daily shift from {shift.start_time.strftime("%H:%M")} to {shift.end_time.strftime("%H:%M")}',
                        'existing_shift_id': shift.id
                    }, status=status.HTTP_400_BAD_REQUEST)
             
        # Set created_by to current user
        # Extract recurring flags from request
        is_recurring = request.data.get('is_recurring', False)
        recurrence_pattern = request.data.get('recurrence_pattern', 'NONE')
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shift = serializer.save(
            created_by=request.user,
            is_recurring=is_recurring,
            recurrence_pattern=recurrence_pattern
        )
        
        # Return success with clear message
        return Response({
            'success': True,
            'message': 'Shift created successfully. Pending EIC approval.',
            'shift_id': shift.id,
            'status': shift.status,
            'driver_id': shift.driver_id,
            'start_time': timezone.localtime(shift.start_time).isoformat(),
            'end_time': timezone.localtime(shift.end_time).isoformat(),
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        if not request.user.user_roles.filter(role__code='EIC', active=True).exists():
            return Response(
                {'error': 'Permission denied. Only EIC can approve shifts.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        shift = self.get_object()
        shift.status = 'APPROVED'
        shift.approved_by = request.user
        shift.rejection_reason = None
        # On approval, mark driver trained and license verified
        try:
            driver = shift.driver
            if driver:
                driver.trained = True
                driver.license_verified = True
                driver.save(update_fields=['trained', 'license_verified'])
        except Exception:
            pass
        shift.save()
        return Response({'status': 'approved'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        if not request.user.user_roles.filter(role__code='EIC', active=True).exists():
            return Response(
                {'error': 'Permission denied. Only EIC can reject shifts.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        shift = self.get_object()
        reason = request.data.get('reason', '').strip()
        shift.status = 'REJECTED'
        shift.approved_by = request.user
        shift.rejection_reason = reason or 'No reason provided'
        shift.save()
        return Response({
            'status': 'rejected',
            'reason': shift.rejection_reason,
            'shift_id': shift.id
        })

class VehicleViewSet(viewsets.ModelViewSet):
    """
    API Path: /api/vehicles/
    Methods: GET (list), POST (create), GET (retrieve), PUT (update), DELETE (delete)
    Actions:
      - GET /api/vehicles/ - List all vehicles
      - POST /api/vehicles/ - Create new vehicle
      - GET /api/vehicles/{id}/ - Get vehicle detail
      - PUT /api/vehicles/{id}/ - Update vehicle
      - DELETE /api/vehicles/{id}/ - Delete vehicle
    """
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer

# --- Driver Operations ---

class DriverLocationView(views.APIView):
    """
    API Path: POST /api/driver/location
    Updates driver's current location.
    """
    def post(self, request):
        return Response({'status': 'updated'})

class DriverArrivalMSView(views.APIView):
    """
    API Path: None (Not mapped in urls.py - use /api/driver/arrival/ms via DriverTripViewSet instead)
    Legacy view for driver arrival at MS.
    """
    def post(self, request):
        token_id = request.data.get('token')
        trip = get_trip_by_token(token_id)
        trip.status = 'AT_MS'
        trip.origin_confirmed_at = timezone.now()
        trip.save()
        return Response({'status': 'confirmed', 'trip_id': trip.id})

class DriverArrivalDBSView(views.APIView):
    """
    API Path: None (Not mapped in urls.py - use /api/driver/arrival/dbs via DriverTripViewSet instead)
    Legacy view for driver arrival at DBS.
    """
    def post(self, request):
        token_id = request.data.get('token')
        trip = get_trip_by_token(token_id)
        trip.status = 'AT_DBS'
        trip.dbs_arrival_at = timezone.now()
        trip.save()
        return Response({'status': 'confirmed', 'trip_id': trip.id})

class MeterReadingConfirmationView(views.APIView):
    """
    API Path: None (Not mapped in urls.py - use /api/driver/meter-reading/confirm via DriverTripViewSet instead)
    Legacy view for meter reading confirmation.
    """
    def post(self, request):
        token_id = request.data.get('token')
        reading_value = request.data.get('reading')
        reading_type = request.data.get('type') # PRE_FILL_MFM, POST_FILL_MFM, PRE_DEC_PRESSURE, POST_DEC_PRESSURE
        
        trip = get_trip_by_token(token_id)
        
        if not reading_value or not reading_type:
            return Response({'error': 'Missing reading or type'}, status=400)
            
        try:
            val = float(reading_value)
        except ValueError:
            return Response({'error': 'Invalid reading value'}, status=400)

        if reading_type == 'PRE_FILL_MFM':
             filling, _ = MSFilling.objects.get_or_create(trip=trip)
             filling.prefill_mfm = val
             filling.save()
        elif reading_type == 'POST_FILL_MFM':
             filling, _ = MSFilling.objects.get_or_create(trip=trip)
             filling.postfill_mfm = val
             filling.save()
        elif reading_type == 'PRE_DEC_PRESSURE':
             decanting, _ = DBSDecanting.objects.get_or_create(trip=trip)
             decanting.pre_dec_pressure_bar = val
             decanting.save()
        elif reading_type == 'POST_DEC_PRESSURE':
             decanting, _ = DBSDecanting.objects.get_or_create(trip=trip)
             decanting.post_dec_pressure_bar = val
             decanting.save()
        else:
            return Response({'error': 'Invalid reading type'}, status=400)
            
        return Response({'status': 'confirmed', 'updated': reading_type})

class TripCompleteView(views.APIView):
    """
    API Path: POST /api/driver/trip/complete
    Marks trip as completed when driver returns to MS.
    """
    def post(self, request):
        token_id = request.data.get('token')
        trip = get_trip_by_token(token_id)
        trip.status = 'COMPLETED'
        trip.current_step = '7'
        trip.ms_return_at = timezone.now()
        trip.completed_at = timezone.now()
        trip.save()
        return Response({'status': 'completed'})

class EmergencyReportView(views.APIView):
    """
    API Path: POST /api/driver/emergency
    
    Register an emergency alert. Gets trip from token, stores MS station ID.
    Notifies all EICs assigned to the MS station.
    
    Request Payload:
    {
        "token": "TRIP_TOKEN_123",    # Required - trip token to identify the trip
        "type": "ACCIDENT",           # Required - any emergency type from frontend
        "message": "Vehicle collision",# Required - description of the emergency
        "severity": "CRITICAL"        # Required - LOW, MEDIUM, HIGH, CRITICAL
    }
    
    Response:
    {
        "success": true,
        "alert_id": 123,
        "message": "Emergency reported. EICs have been notified.",
        "notifications_sent": 2
    }
    """
    def post(self, request):
        from core.notification_service import notification_service
        from core.models import UserRole
        
        # Parse request data from frontend
        token_id = request.data.get('token')
        emergency_type = request.data.get('type', 'OTHER')
        message = request.data.get('message', '')
        severity = request.data.get('severity', 'CRITICAL')
        
        # Validate required fields
        if not token_id:
            return Response({'error': 'Token is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not message:
            message = 'No additional details provided.'
        # Get trip from token
        try:
            trip = get_trip_by_token(token_id)
        except:
            return Response({'error': 'Invalid token or trip not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get MS station from trip
        ms = trip.ms
        if not ms and trip.dbs:
            ms = trip.dbs.parent_station
        
        # Create the alert with trip_id and station_id (MS)
        alert = Alert.objects.create(
            type=emergency_type,  # Store the actual emergency type from frontend
            severity=severity,
            message=message,
            trip=trip,
            station=ms  # Store MS station ID
        )
        
        # Update trip status to EMERGENCY
        # if trip.status not in ['COMPLETED', 'CANCELLED', 'EMERGENCY']:
        #     trip.status = 'EMERGENCY'
        #     trip.step_data = {
        #         **trip.step_data, 
        #         'emergency_reported': True,
        #         'emergency_type': emergency_type,
        #         'emergency_at': timezone.now().isoformat(),
        #         'alert_id': alert.id
        #     }
        #     trip.save(update_fields=['status', 'step_data'])
        
        # Send notifications to all EICs for this MS
        notifications_sent = 0
        driver = trip.driver
        if ms:
            try:
                eic_roles = UserRole.objects.filter(
                    station=ms,
                    role__code='EIC',
                    active=True
                )
                
                for eic_role in eic_roles:
                    if eic_role.user:
                        notification_service.send_to_user(
                            user=eic_role.user,
                            title=f"🚨 EMERGENCY: {emergency_type}",
                            body=f"Driver: {driver.full_name if driver else 'Unknown'}\n{message[:100]}",
                            data={
                                'type': 'EMERGENCY',
                                'emergency_type': emergency_type,
                                'alert_id': str(alert.id),
                                'trip_id': str(trip.id),
                                'token': token_id,
                                'driver_name': driver.full_name if driver else None,
                                'vehicle_no': trip.vehicle.registration_no if trip.vehicle else None,
                                'severity': severity
                            }
                        )
                        notifications_sent += 1
            except Exception as e:
                logger.error(f"Error sending emergency notifications: {e}")
        
        return Response({
            'success': True,
            'message': f'Emergency reported. {notifications_sent} EIC(s) have been notified.',
        })

# --- MS Operations ---

class MSConfirmArrivalView(views.APIView):
    """
    API Path: None (Not mapped - use /api/ms/arrival/confirm in ms_views.py instead)
    Legacy view for MS arrival confirmation.
    """
    def post(self, request):
        token_id = request.data.get('token')
        trip = get_trip_by_token(token_id)
        trip.status = 'AT_MS'
        trip.save()
        return Response({'status': 'confirmed'})



# --- DBS Operations ---



