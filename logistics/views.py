from rest_framework import viewsets, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import (
    Vehicle, Driver, StockRequest, Token, Trip,
    MSFilling, DBSDecanting, Reconciliation, Alert, Shift
)
from .serializers import (
    VehicleSerializer, DriverSerializer, StockRequestSerializer,
    TokenSerializer, TripSerializer, MSFillingSerializer,
    DBSDecantingSerializer, ReconciliationSerializer, AlertSerializer, ShiftSerializer
)
from core.models import Station, User

# --- Helper Functions ---
def get_trip_by_token(token_id):
    return get_object_or_404(Trip, token__id=token_id)

# --- ViewSets ---

class StockRequestViewSet(viewsets.ModelViewSet):
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

        serializer.save(
            requested_by_user=user,
            source=source,
            dbs=dbs
        )

class TripViewSet(viewsets.ModelViewSet):
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

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        trip = self.get_object()
        driver_id = request.data.get('driverId')
        if driver_id:
            driver = get_object_or_404(Driver, id=driver_id)
            trip.driver = driver
        trip.status = 'PENDING'
        trip.save()
        return Response({'status': 'accepted'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        trip = self.get_object()
        trip.status = 'CANCELLED'
        trip.save()
        return Response({'status': 'rejected'})

    @action(detail=False, methods=['get'])
    def status(self, request):
        token_id = request.query_params.get('token')
        if not token_id:
            return Response({'error': 'Token required'}, status=400)
        trip = get_trip_by_token(token_id)
        return Response(TripSerializer(trip).data)

class DriverViewSet(viewsets.ModelViewSet):
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

class ShiftViewSet(viewsets.ModelViewSet):
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
            # Check for overlapping shifts for the same driver
            # A shift overlaps if: existing.start < new.end AND existing.end > new.start
            overlapping_shifts = Shift.objects.filter(
                driver_id=driver_id,
                status__in=['PENDING', 'APPROVED'],  # Only check active shifts
                start_time__lt=end_time,
                end_time__gt=start_time
            )
            
            if overlapping_shifts.exists():
                overlap = overlapping_shifts.first()
                return Response({
                    'error': 'Overlapping shift exists',
                    'message': f'Driver already has a shift from {overlap.start_time.strftime("%Y-%m-%d %H:%M")} to {overlap.end_time.strftime("%Y-%m-%d %H:%M")}',
                    'existing_shift_id': overlap.id
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Set created_by to current user
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shift = serializer.save(created_by=request.user)
        
        # Return success with clear message
        return Response({
            'success': True,
            'message': 'Shift created successfully. Pending EIC approval.',
            'shift_id': shift.id,
            'status': shift.status,
            'driver_id': shift.driver_id,
            'start_time': shift.start_time.isoformat(),
            'end_time': shift.end_time.isoformat(),
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
        shift.status = 'REJECTED'
        shift.approved_by = request.user
        shift.save()
        return Response({'status': 'rejected'})

class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer

# --- Driver Operations ---

class DriverLocationView(views.APIView):
    def post(self, request):
        return Response({'status': 'updated'})

class DriverArrivalMSView(views.APIView):
    def post(self, request):
        token_id = request.data.get('token')
        trip = get_trip_by_token(token_id)
        trip.status = 'AT_MS'
        trip.origin_confirmed_at = timezone.now()
        trip.save()
        return Response({'status': 'confirmed', 'trip_id': trip.id})

class DriverArrivalDBSView(views.APIView):
    def post(self, request):
        token_id = request.data.get('token')
        trip = get_trip_by_token(token_id)
        trip.status = 'AT_DBS'
        trip.dbs_arrival_at = timezone.now()
        trip.save()
        return Response({'status': 'confirmed', 'trip_id': trip.id})

class MeterReadingConfirmationView(views.APIView):
    def post(self, request):
        return Response({'status': 'confirmed'})

class TripCompleteView(views.APIView):
    def post(self, request):
        token_id = request.data.get('token')
        trip = get_trip_by_token(token_id)
        trip.status = 'COMPLETED'
        trip.completed_at = timezone.now()
        trip.save()
        return Response({'status': 'completed'})

class EmergencyReportView(views.APIView):
    def post(self, request):
        token_id = request.data.get('token')
        desc = request.data.get('description')
        trip = None
        if token_id:
            try:
                trip = get_trip_by_token(token_id)
            except:
                pass
        
        Alert.objects.create(
            type='EMERGENCY',
            severity='CRITICAL',
            message=desc or 'Emergency reported by driver',
            trip=trip
        )
        return Response({'status': 'reported'})

# --- MS Operations ---

class MSConfirmArrivalView(views.APIView):
    def post(self, request):
        token_id = request.data.get('token')
        trip = get_trip_by_token(token_id)
        trip.status = 'AT_MS'
        trip.save()
        return Response({'status': 'confirmed'})

class MSPreReadingView(views.APIView):
    def post(self, request):
        session_id = request.data.get('sessionId') 
        reading = request.data.get('reading')
        trip = get_object_or_404(Trip, id=session_id)
        
        filling, created = MSFilling.objects.get_or_create(trip=trip)
        filling.start_time = timezone.now()
        filling.prefill_pressure_bar = reading.get('pressure')
        filling.prefill_mfm = reading.get('mfm')
        filling.save()
        
        return Response({'status': 'saved'})

class MSPostReadingView(views.APIView):
    def post(self, request):
        session_id = request.data.get('sessionId')
        reading = request.data.get('reading')
        
        trip = get_object_or_404(Trip, id=session_id)
        filling = get_object_or_404(MSFilling, trip=trip)
        
        filling.end_time = timezone.now()
        filling.postfill_pressure_bar = reading.get('pressure')
        filling.postfill_mfm = reading.get('mfm')
        
        if filling.prefill_mfm and filling.postfill_mfm:
            filling.filled_qty_kg = float(filling.postfill_mfm) - float(filling.prefill_mfm)
            
        filling.save()
        
        return Response({'status': 'saved', 'filled_qty': filling.filled_qty_kg})

class MSConfirmSAPView(views.APIView):
    def post(self, request):
        session_id = request.data.get('sessionId')
        trip = get_object_or_404(Trip, id=session_id)
        
        trip.status = 'IN_TRANSIT'
        trip.dbs_departure_at = timezone.now()
        trip.save()
        
        return Response({'status': 'posted', 'sto_number': f'STO-{trip.id}-MOCK'})

# --- DBS Operations ---

class DBSDecantArriveView(views.APIView):
    """
    POST /dbs/decant/arrive
    DBS operator confirms truck arrival at DBS station.
    Request: { token: "TOKEN-ID" }
    Response: { trip: {...}, status: "confirmed" }
    """
    def post(self, request):
        token_id = request.data.get('token')
        trip = get_trip_by_token(token_id)
        trip.status = 'AT_DBS'
        trip.dbs_arrival_at = timezone.now()
        trip.save()
        
        return Response({
            'status': 'confirmed',
            'trip': {
                'id': trip.id,
                'status': trip.status,
                'msName': trip.ms.name if trip.ms else None,
                'dbsName': trip.dbs.name if trip.dbs else None,
                'vehicleNo': trip.vehicle.registration_no if trip.vehicle else None,
                'driverName': trip.driver.full_name if trip.driver else None,
                'arrivedAt': trip.dbs_arrival_at.isoformat() if trip.dbs_arrival_at else None
            }
        })

class DBSDecantPreView(views.APIView):
    """
    POST /dbs/decant/pre
    Gets or fetches pre-decant metrics from SCADA/manual input.
    Request: { token: "TOKEN-ID", reading: {pressure, mfm} } (optional reading for manual input)
    Response: { pressure, flow, mfm, status }
    """
    def post(self, request):
        token_id = request.data.get('token')
        reading = request.data.get('reading', {})
        trip = get_trip_by_token(token_id)
        
        decanting, created = DBSDecanting.objects.get_or_create(trip=trip)
        
        # If manual reading provided, save it
        if reading:
            decanting.start_time = timezone.now()
            if 'mfm' in reading:
                decanting.pre_dec_reading = reading['mfm']
            decanting.save()
        
        # Get MS filling data (what was filled at MS)
        ms_filling = MSFilling.objects.filter(trip=trip).first()
        post_fill_pressure = float(ms_filling.postfill_pressure_bar) if ms_filling and ms_filling.postfill_pressure_bar else 250.0
        filled_qty = float(ms_filling.filled_qty_kg) if ms_filling and ms_filling.filled_qty_kg else 500.0
        
        # Return pre-decant metrics (simulated SCADA data for now)
        return Response({
            'status': 'ready',
            'pressure': f"{post_fill_pressure:.1f} bar",  # Pressure should be high before decanting
            'flow': "0.0 kg/min",  # No flow yet
            'mfm': f"{filled_qty:.2f} kg",  # MFM shows filled quantity
            'tripId': trip.id,
            'vehicleNo': trip.vehicle.registration_no if trip.vehicle else None
        })

class DBSDecantStartView(views.APIView):
    """
    POST /dbs/decant/start
    Starts the decanting process - records start time.
    Request: { token: "TOKEN-ID" }
    Response: { status, startTime }
    """
    def post(self, request):
        token_id = request.data.get('token')
        trip = get_trip_by_token(token_id)
        
        # Update trip status
        trip.status = 'DECANTING_STARTED'
        trip.save()
        
        # Create or update decanting record
        decanting, created = DBSDecanting.objects.get_or_create(trip=trip)
        decanting.start_time = timezone.now()
        decanting.save()
        
        return Response({
            'status': 'started',
            'startTime': decanting.start_time.isoformat(),
            'tripId': trip.id
        })

class DBSDecantEndView(views.APIView):
    """
    POST /dbs/decant/end
    Ends the decanting process - records end metrics.
    Request: { token: "TOKEN-ID" }
    Response: { pressure, flow, mfm, endTime, deliveredQty }
    """
    def post(self, request):
        token_id = request.data.get('token')
        trip = get_trip_by_token(token_id)
        
        # Update trip status
        trip.status = 'DECANTING_COMPLETED'
        trip.save()
        
        # Update decanting record
        decanting, created = DBSDecanting.objects.get_or_create(trip=trip)
        decanting.end_time = timezone.now()
        
        # Get MS filling data
        ms_filling = MSFilling.objects.filter(trip=trip).first()
        filled_qty = float(ms_filling.filled_qty_kg) if ms_filling and ms_filling.filled_qty_kg else 500.0
        
        # Simulate post-decant metrics (after gas transferred to DBS storage)
        post_pressure = 15.0  # Low pressure after decanting
        delivered_qty = filled_qty * 0.997  # 0.3% typical loss
        
        decanting.post_dec_reading = post_pressure
        decanting.delivered_qty_kg = delivered_qty
        decanting.save()
        
        return Response({
            'status': 'ended',
            'pressure': f"{post_pressure:.1f} bar",
            'flow': "0.0 kg/min",  # Flow stopped
            'mfm': f"{delivered_qty:.2f} kg",
            'endTime': decanting.end_time.isoformat(),
            'deliveredQty': delivered_qty,
            'tripId': trip.id
        })

class DBSDecantConfirmView(views.APIView):
    """
    POST /dbs/decant/confirm
    Confirms delivery, performs reconciliation, closes STO.
    Request: { token, deliveredQty, operatorAck, driverAck }
    Response: { status, reconciliation, tripId }
    """
    def post(self, request):
        token_id = request.data.get('token')
        payload = request.data
        trip = get_trip_by_token(token_id)
        
        decanting, created = DBSDecanting.objects.get_or_create(trip=trip)
        decanting.end_time = decanting.end_time or timezone.now()
        decanting.post_dec_reading = payload.get('finalReading')
        decanting.delivered_qty_kg = payload.get('deliveredQty')
        
        # Store acknowledgments
        if payload.get('operatorAck'):
            decanting.confirmed_by_dbs_operator = request.user if request.user.is_authenticated else None
        if payload.get('driverAck'):
            decanting.confirmed_by_driver = trip.driver.user if trip.driver and trip.driver.user else None
            
        decanting.save()
        
        ms_filling = MSFilling.objects.filter(trip=trip).first()
        ms_qty = float(ms_filling.filled_qty_kg) if ms_filling and ms_filling.filled_qty_kg else 0
        dbs_qty = float(decanting.delivered_qty_kg or 0)
        
        diff = ms_qty - dbs_qty
        variance = (diff / ms_qty) * 100 if ms_qty > 0 else 0
        
        recon = Reconciliation.objects.create(
            trip=trip,
            ms_filled_qty_kg=ms_qty,
            dbs_delivered_qty_kg=dbs_qty,
            diff_qty=diff,
            variance_pct=variance,
            status='ALERT' if abs(variance) > 0.5 else 'OK'
        )
        
        trip.status = 'COMPLETED'
        trip.dbs_departure_at = timezone.now()
        trip.completed_at = timezone.now()
        trip.save()
        
        return Response({
            'status': 'confirmed',
            'tripId': trip.id,
            'reconciliation': {
                'msFilled': ms_qty,
                'dbsDelivered': dbs_qty,
                'difference': diff,
                'variancePct': round(variance, 2),
                'reconStatus': recon.status
            },
            'stoNumber': trip.sto_number
        })

