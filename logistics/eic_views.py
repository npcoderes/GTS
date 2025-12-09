from rest_framework import viewsets, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q, Count, Avg
from .models import (
    Vehicle, Driver, StockRequest, Token, Trip,
    MSFilling, DBSDecanting, Reconciliation, Alert, Shift
)
from .serializers import (
    VehicleSerializer, DriverSerializer, StockRequestSerializer,
    TokenSerializer, TripSerializer, MSFillingSerializer,
    DBSDecantingSerializer, ReconciliationSerializer, AlertSerializer, ShiftSerializer,
    EICStockRequestListSerializer
)
from .services import get_available_drivers
from core.models import Station, User

# --- Helper Functions ---
def get_trip_by_token(token_id):
    return get_object_or_404(Trip, token__id=token_id)

def check_eic_permission(user):
    """Check if user has EIC role"""
    return user.user_roles.filter(role__code='EIC', active=True).exists()

# --- EIC ViewSets ---

class EICStockRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    EIC-specific Stock Request management
    Provides list, detail, approve, and reject actions
    """
    queryset = StockRequest.objects.all()
    serializer_class = StockRequestSerializer
    
    def get_serializer_class(self):
        if self.action == 'list':
            return EICStockRequestListSerializer
        return StockRequestSerializer

    def get_queryset(self):
        # Verify EIC permission
        if not check_eic_permission(self.request.user):
            return StockRequest.objects.none()
        
        queryset = StockRequest.objects.select_related(
            'dbs', 'requested_by_user', 'rejected_by'
        ).all()
        
        # Filter by EIC's assigned MS
        # EIC should only see requests from DBSs that are children of their assigned MS
        user_role = self.request.user.user_roles.filter(role__code='EIC', active=True).first()
        if user_role and user_role.station and user_role.station.type == 'MS':
            queryset = queryset.filter(dbs__parent_station=user_role.station)
        
        # Filter by status
        status_param = self.request.query_params.get('status')
        if status_param:
            statuses = status_param.split(',')
            queryset = queryset.filter(status__in=statuses)
        
        # Filter by source type
        type_param = self.request.query_params.get('type')
        if type_param:
            types = type_param.split(',')
            queryset = queryset.filter(source__in=types)
        
        # Filter by priority
        priority_param = self.request.query_params.get('priority')
        if priority_param:
            priorities = priority_param.split(',')
            queryset = queryset.filter(priority_preview__in=priorities)
        
        # Filter by DBS
        dbs_id = self.request.query_params.get('dbs_id')
        if dbs_id:
            queryset = queryset.filter(dbs_id=dbs_id)
        
        # Sort by priority (H>C>N>FDODO), then created_at DESC
        priority_order = {'H': 1, 'C': 2, 'N': 3, 'FDODO': 4}
        queryset = queryset.order_by('-created_at')
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Approve or Reject stock request based on status in payload.
        If driver_id is provided with APPROVED status, assigns driver immediately.
        
        POST /api/eic/stock-requests/{id}/approve/
        
        Payload:
        {
            "status": "APPROVED" or "REJECTED",
            "driver_id": 123,  // Optional - if provided, assigns driver immediately
            "notes": "Optional notes",
            "reason": "Optional rejection reason"
        }
        """
        if not check_eic_permission(request.user):
            return Response(
                {'error': 'Permission denied. Only EIC can approve/reject stock requests.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        stock_request = self.get_object()
        
        # Get status from payload
        new_status = request.data.get('status', 'APPROVED').upper()
        notes = request.data.get('notes', '')
        reason = request.data.get('reason', '')
        driver_id = request.data.get('driverId')  # NEW: Optional driver assignment (camelCase for frontend)
        
        # Validate status value
        if new_status not in ['APPROVED', 'REJECTED']:
            return Response(
                {'error': f'Invalid status: {new_status}. Must be APPROVED or REJECTED.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate current status
        if stock_request.status not in ['PENDING', 'QUEUED']:
            return Response(
                {'error': f'Cannot modify request with status: {stock_request.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                if new_status == 'APPROVED':
                    # If driver_id is provided, approve AND assign in one step
                    if driver_id:
                        # Get driver details
                        try:
                            driver = Driver.objects.select_related('user', 'assigned_vehicle').get(id=driver_id)
                        except Driver.DoesNotExist:
                            return Response({'error': 'Driver not found'}, status=status.HTTP_404_NOT_FOUND)
                        
                        # Verify driver is available (has active shift and not on trip)
                        now = timezone.now()
                        from .services import find_active_shift
                        active_shift = find_active_shift(driver, now)
                        
                        if not active_shift:
                            return Response({
                                'error': 'Driver does not have an active shift'
                            }, status=status.HTTP_400_BAD_REQUEST)
                        
                        # Check if driver is on an active trip
                        active_trip = Trip.objects.filter(
                            driver=driver,
                            status__in=['PENDING', 'AT_MS', 'IN_TRANSIT', 'AT_DBS']
                        ).exists()
                        
                        if active_trip:
                            return Response({
                                'error': 'Driver is currently on another trip'
                            }, status=status.HTTP_400_BAD_REQUEST)
                        
                        # Update stock request - approve and assign
                        stock_request.status = 'ASSIGNING'
                        stock_request.approval_notes = notes
                        stock_request.assignment_mode = 'MANUAL'
                        stock_request.assignment_started_at = timezone.now()
                        stock_request.target_driver_id = driver_id
                        stock_request.save()
                        
                        # Send FCM notification to driver
                        driver_notified = False
                        try:
                            from core.notification_service import NotificationService
                            notification_service = NotificationService()
                            
                            if driver.user:
                                # Reload stock_request with related data
                                stock_request.refresh_from_db()
                                dbs = stock_request.dbs
                                ms_name = ''
                                dbs_name = ''
                                
                                if dbs:
                                    dbs_name = dbs.name or ''
                                    # Get parent MS
                                    if dbs.parent_station:
                                        ms_name = dbs.parent_station.name or ''
                                
                                notification_service.send_to_user(
                                    user=driver.user,
                                    title="New Trip Assignment",
                                    body="Tap to view trip details",
                                    data={
                                        'type': 'TRIP_OFFER',
                                        'stock_request_id': str(stock_request.id),
                                        'from_ms': ms_name,
                                        'to_dbs': dbs_name,
                                        'quantity': str(stock_request.requested_qty_kg)
                                    }
                                )
                                driver_notified = True
                        except Exception as e:
                            print(f"Notification error: {e}")
                        
                        return Response({
                            'success': True,
                            'status': 'assigning',
                            'stock_request_id': stock_request.id,
                            'driver_id': driver_id,
                            'driver_name': driver.full_name,
                            'driver_phone': driver.phone,
                            'vehicle_no': active_shift.vehicle.registration_no,
                            'notification_sent': driver_notified,
                            'message': 'Stock request approved. Driver has been notified.',
                            'expires_in_seconds': 300
                        })
                    else:
                        # Just approve without assigning driver
                        stock_request.status = 'APPROVED'
                        stock_request.approval_notes = notes
                        stock_request.save()
                        
                        return Response({
                            'success': True,
                            'status': 'approved',
                            'stock_request_id': stock_request.id,
                            'message': 'Stock request approved. Please assign a driver.'
                        })
                else:
                    # Reject the request
                    stock_request.status = 'REJECTED'
                    stock_request.rejection_reason = f"{reason}. {notes}".strip() if reason or notes else 'No reason provided'
                    stock_request.rejected_at = timezone.now()
                    stock_request.rejected_by = request.user
                    stock_request.save()
                    
                    return Response({
                        'success': True,
                        'status': 'rejected',
                        'stock_request_id': stock_request.id,
                        'message': 'Stock request has been rejected'
                    })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        Reject a pending stock request
        """
        if not check_eic_permission(request.user):
            return Response(
                {'error': 'Permission denied. Only EIC can reject stock requests.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        stock_request = self.get_object()
        
        # Validate status
        if stock_request.status not in ['PENDING', 'QUEUED']:
            return Response(
                {'error': f'Cannot reject request with status: {stock_request.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reason = request.data.get('reason', 'No reason provided')
        notes = request.data.get('notes', '')
        
        # Update stock request
        stock_request.status = 'REJECTED'
        stock_request.rejection_reason = f"{reason}. {notes}".strip()
        stock_request.rejected_at = timezone.now()
        stock_request.rejected_by = request.user
        stock_request.save()
        
        # TODO: Send notification to requester
        
        return Response({
            'status': 'rejected',
            'stock_request_id': stock_request.id,
            'message': 'Stock request has been rejected'
        })

    @action(detail=True, methods=['get'], url_path='available-drivers')
    def available_drivers(self, request, pk=None):
        """
        Get list of available drivers for assignment
        """
        if not check_eic_permission(request.user):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
            
        stock_request = self.get_object()
        
        # Get parent MS
        ms = stock_request.dbs.parent_station
        if not ms:
            return Response({'error': 'DBS has no parent MS'}, status=status.HTTP_400_BAD_REQUEST)
            
        candidates = get_available_drivers(ms.id)
        
        data = []
        for item in candidates:
            data.append({
                'driver_id': item['driver'].id,
                'driver_name': item['driver'].full_name,
                'vehicle_no': item['vehicle'].registration_no,
                'trip_count': item['trip_count'],
                'phone': item['driver'].phone
            })
            
        return Response(data)

    # @action(detail=True, methods=['post'], url_path='assign-auto')
    # def assign_auto(self, request, pk=None):
    #     """
    #     Trigger Auto-Push assignment
    #     """
    #     if not check_eic_permission(request.user):
    #         return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
            
    #     stock_request = self.get_object()
        
    #     if stock_request.status != 'APPROVED':
    #         return Response({'error': 'Request must be APPROVED to assign'}, status=status.HTTP_400_BAD_REQUEST)
            
    #     # Update State
    #     stock_request.status = 'ASSIGNING'
    #     stock_request.assignment_mode = 'AUTO'
    #     stock_request.assignment_started_at = timezone.now()
    #     stock_request.target_driver = None
    #     stock_request.save()
        
    #     # TODO: Send FCM to all available drivers
    #     # candidates = get_available_drivers(stock_request.dbs.parent_station.id)
    #     # send_push_notification(candidates, ...)
        
    #     return Response({'status': 'assigning', 'mode': 'AUTO', 'message': 'Auto-push triggered'})

    # @action(detail=True, methods=['post'], url_path='assign-manual')
    # def assign_manual(self, request, pk=None):
    #     """
    #     Assign a specific driver to the stock request.
        
    #     POST /api/eic/stock-requests/{id}/assign-manual/
        
    #     Payload: {
    #         "driver_id": 123
    #     }
        
    #     Sends FCM notification to the driver.
    #     """
    #     if not check_eic_permission(request.user):
    #         return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
            
    #     stock_request = self.get_object()
    #     driver_id = request.data.get('driver_id')
        
    #     if not driver_id:
    #         return Response({'error': 'driver_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
    #     if stock_request.status != 'APPROVED':
    #         return Response({'error': 'Request must be APPROVED to assign'}, status=status.HTTP_400_BAD_REQUEST)
        
    #     # Get driver details
    #     try:
    #         driver = Driver.objects.select_related('user', 'assigned_vehicle').get(id=driver_id)
    #     except Driver.DoesNotExist:
    #         return Response({'error': 'Driver not found'}, status=status.HTTP_404_NOT_FOUND)
        
    #     # Verify driver is available (has active shift and not on trip)
    #     now = timezone.now()
    #     active_shift = Shift.objects.filter(
    #         driver=driver,
    #         status='APPROVED',
    #         start_time__lte=now,
    #         end_time__gte=now
    #     ).first()
        
    #     if not active_shift:
    #         return Response({
    #             'error': 'Driver does not have an active shift'
    #         }, status=status.HTTP_400_BAD_REQUEST)
        
    #     # Check if driver is on an active trip
    #     active_trip = Trip.objects.filter(
    #         driver=driver,
    #         status__in=['PENDING', 'AT_MS', 'IN_TRANSIT', 'AT_DBS']
    #     ).exists()
        
    #     if active_trip:
    #         return Response({
    #             'error': 'Driver is currently on another trip'
    #         }, status=status.HTTP_400_BAD_REQUEST)
            
    #     # Update State
    #     stock_request.status = 'ASSIGNING'
    #     stock_request.assignment_mode = 'MANUAL'
    #     stock_request.assignment_started_at = timezone.now()
    #     stock_request.target_driver_id = driver_id
    #     stock_request.save()
        
    #     # Send FCM notification to driver
    #     driver_notified = False
    #     try:
    #         from core.notification_service import NotificationService
    #         notification_service = NotificationService()
            
    #         if driver.user:
    #             notification_service.send_to_user(
    #                 user=driver.user,
    #                 title="New Trip Assignment",
    #                 body=f"You have been assigned a trip to {stock_request.dbs.name}. Tap to accept or reject.",
    #                 data={
    #                     'type': 'TRIP_OFFER',
    #                     'stock_request_id': stock_request.id,
    #                     'dbs_name': stock_request.dbs.name,
    #                     'dbs_id': stock_request.dbs.id,
    #                     'quantity_kg': str(stock_request.requested_qty_kg),
    #                     'priority': stock_request.priority_preview,
    #                     'expires_in_seconds': '300'
    #                 }
    #             )
    #             driver_notified = True
    #     except Exception as e:
    #         print(f"Notification error: {e}")
        
    #     return Response({
    #         'success': True,
    #         'status': 'assigning',
    #         'mode': 'MANUAL',
    #         'driver_id': driver_id,
    #         'driver_name': driver.full_name,
    #         'driver_phone': driver.phone,
    #         'vehicle_no': active_shift.vehicle.registration_no,
    #         'notification_sent': driver_notified,
    #         'message': 'Driver has been notified. Waiting for confirmation.',
    #         'expires_in_seconds': 300
    #     })

class EICDashboardView(views.APIView):
    """
    EIC dashboard statistics and overview
    """
    def get(self, request):
        if not check_eic_permission(request.user):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Count pending stock requests
        pending_stock_requests = StockRequest.objects.filter(status='PENDING').count()
        
        # Count active trips
        active_trips = Trip.objects.filter(
            status__in=['PENDING', 'AT_MS', 'IN_TRANSIT', 'AT_DBS']
        ).count()
        
        # Count pending driver approvals
        pending_driver_approvals = Shift.objects.filter(status='PENDING').count()
        
        # Count alerts today
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        alerts_today = Alert.objects.filter(created_at__gte=today_start).count()
        
        # Average RLT
        avg_rlt = StockRequest.objects.filter(
            created_at__gte=today_start
        ).aggregate(avg=Avg('rlt_minutes'))['avg'] or 0
        
        # Reconciliation alerts
        reconciliation_alerts = Reconciliation.objects.filter(status='ALERT').count()
        
        # Recent stock requests
        recent_stock_requests = StockRequest.objects.select_related('dbs').filter(
            status='PENDING'
        ).order_by('-created_at')[:5]
        
        # Active trips
        active_trips_list = Trip.objects.select_related(
            'vehicle', 'ms', 'dbs'
        ).filter(
            status__in=['PENDING', 'AT_MS', 'IN_TRANSIT', 'AT_DBS']
        ).order_by('-started_at')[:5]
        
        # Recent alerts
        recent_alerts = Alert.objects.order_by('-created_at')[:5]
        
        return Response({
            'summary': {
                'pending_stock_requests': pending_stock_requests,
                'active_trips': active_trips,
                'pending_driver_approvals': pending_driver_approvals,
                'alerts_today': alerts_today,
                'avg_rlt_minutes': round(avg_rlt, 2),
                'reconciliation_alerts': reconciliation_alerts
            },
            'recent_stock_requests': [
                {
                    'id': sr.id,
                    'dbs_name': sr.dbs.name,
                    'priority': sr.priority_preview,
                    'created_at': sr.created_at
                } for sr in recent_stock_requests
            ],
            'active_trips': [
                {
                    'id': trip.id,
                    'vehicle_no': trip.vehicle.registration_no,
                    'status': trip.status,
                    'from_ms': trip.ms.code,
                    'to_dbs': trip.dbs.code
                } for trip in active_trips_list
            ],
            'alerts': [
                {
                    'id': alert.id,
                    'type': alert.type,
                    'severity': alert.severity,
                    'message': alert.message,
                    'created_at': alert.created_at
                } for alert in recent_alerts
            ]
        })

class EICDriverApprovalView(views.APIView):
    """
    EIC Driver Approval - List pending driver shifts
    
    Returns format:
    {
        "pending": [
            {
                "id": "driver_id",
                "name": "Driver Name",
                "phone": "1234567890",
                "licenseNumber": "DL123456",
                "licenseExpiry": "2025-12-31",
                "preferredShift": "Morning",
                "requestedShiftStart": "08:00",
                "requestedShiftEnd": "16:00",
                "trainingCompleted": true,
                "trainingModules": [],
                "remarks": "",
                "documents": null,
                "shiftId": 1,
                "vehicleNumber": "MH12AB1234",
                "vehicleCapacity": 1000.0
            }
        ]
    }
    """
    def get(self, request):
        if not check_eic_permission(request.user):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get pending shifts with driver and vehicle details
        pending_shifts = Shift.objects.select_related(
            'driver', 'vehicle', 'created_by'
        ).filter(status__in=['PENDING']).order_by('created_at')
        
        pending_list = []
        for shift in pending_shifts:
            driver = shift.driver

            # Normalize datetimes to target display timezone (default IST +05:30)
            def _local_dt(dt):
                if not dt:
                    return None
                display_tz = timezone.get_fixed_timezone(330)  # minutes offset
                try:
                    aware = dt
                    if timezone.is_naive(aware):
                        aware = timezone.make_aware(aware, timezone.utc)
                    return aware.astimezone(display_tz)
                except Exception:
                    return dt

            local_start = _local_dt(shift.start_time)
            local_end = _local_dt(shift.end_time)
            local_created = _local_dt(shift.created_at)
            
            # Determine preferred shift based on time
            start_hour = local_start.hour if local_start else 8
            if start_hour < 12:
                preferred_shift = "Morning"
            elif start_hour < 17:
                preferred_shift = "Afternoon"
            else:
                preferred_shift = "Evening"
            
            pending_list.append({
                'id': str(driver.id),
                'name': driver.full_name,
                'phone': driver.phone or '',
                'licenseNumber': driver.license_no or '',
                'licenseExpiry': driver.license_expiry.isoformat() if driver.license_expiry else None,
                'preferredShift': preferred_shift,
                'requestedShiftStart': local_start.strftime('%H:%M') if local_start else '08:00',
                'requestedShiftEnd': local_end.strftime('%H:%M') if local_end else '16:00',
                'trainingCompleted': driver.trained,
                'trainingVerified': driver.trained,
                'licenseVerified': driver.license_verified,
                'trainingModules': [],  # Not implemented yet
                'remarks': '',
                'documents': None,  # Currently null as requested
                
                # Additional useful fields
                'shiftId': shift.id,
                'shiftDate': local_start.strftime('%Y-%m-%d') if local_start else None,
                'vehicleNumber': shift.vehicle.registration_no if shift.vehicle else None,
                'vehicleCapacity': float(shift.vehicle.capacity_kg) if shift.vehicle else None,
                'createdBy': shift.created_by.get_full_name() if shift.created_by else 'System',
                'createdAt': local_created.isoformat() if local_created else None
            })
        
        return Response({
            'pending': pending_list
        })

class EICPermissionsView(views.APIView):
    """
    Get current EIC user's permissions
    """
    def get(self, request):
        if not check_eic_permission(request.user):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get user's EIC role assignments
        eic_roles = request.user.user_roles.filter(
            role__code='EIC',
            active=True
        ).select_related('station')
        
        managed_stations = [ur.station.id for ur in eic_roles if ur.station]
        
        # TODO: Implement granular permissions from Super Admin settings
        # For now, return default EIC permissions
        return Response({
            'can_approve_requests': True,
            'can_reject_requests': True,
            'can_override_tokens': False,  # Requires Super Admin permission
            'can_manage_clusters': True,
            'can_approve_drivers': True,
            'canManageDrivers': True,  # Frontend expects this format
            'canApproveDemand': True,
            'canManageClusters': True,
            'canTriggerCorrectiveActions': True,
            'canViewReconciliation': True,
            'managed_stations': managed_stations,
            'role': 'EIC'
        })


# =============================================================================
# NEW EIC APIs - Network Overview, Reconciliation, Vehicle Tracking, Queue
# =============================================================================

class EICNetworkOverviewView(views.APIView):
    """
    GET /api/eic/network-overview
    Returns MS stations, DBS stations, and their trip schedules for the dashboard.
    NOTE: Vehicle location is derived from trip status (no VTS available).
    NOTE: Only shows MS stations assigned to this EIC user.
    """
    def get(self, request):
        from core.models import UserRole
        
        # Get MS stations assigned to this EIC user
        eic_station_ids = UserRole.objects.filter(
            user=request.user,
            role__code='EIC',
            active=True,
            station__type='MS'
        ).values_list('station_id', flat=True)
        
        # If no stations assigned, return empty (or all if super admin)
        if not eic_station_ids:
            # Check if user is super admin
            is_super_admin = request.user.user_roles.filter(
                role__code='SUPER_ADMIN', 
                active=True
            ).exists()
            if not is_super_admin:
                return Response({
                    'msStations': [],
                    'dbsStations': [],
                    'message': 'No MS stations assigned to this EIC user'
                })
            # Super admin sees all
            ms_stations = Station.objects.filter(type='MS').prefetch_related(
                'trips_origin__dbs', 'trips_origin__driver', 'trips_origin__vehicle'
            )
        else:
            # Filter by assigned stations only
            ms_stations = Station.objects.filter(
                type='MS',
                id__in=eic_station_ids
            ).prefetch_related(
                'trips_origin__dbs', 'trips_origin__driver', 'trips_origin__vehicle'
            )
        
        # Get DBS stations from BOTH MSDBSMap AND parent_station
        from core.models import MSDBSMap
        
        # 1. Get DBS from MSDBSMap
        dbs_mappings = MSDBSMap.objects.filter(
            ms_id__in=[ms.id for ms in ms_stations],
            active=True
        ).select_related('ms', 'dbs')
        
        dbs_to_ms_map = {mapping.dbs_id: mapping.ms.code for mapping in dbs_mappings}
        dbs_ids_from_map = set([mapping.dbs_id for mapping in dbs_mappings])
        
        # 2. Get DBS from parent_station relationship
        dbs_from_parent = Station.objects.filter(
            type='DBS',
            parent_station_id__in=[ms.id for ms in ms_stations]
        )
        
        for dbs in dbs_from_parent:
            if dbs.id not in dbs_ids_from_map:
                dbs_ids_from_map.add(dbs.id)
                # Get parent MS code
                parent_ms = next((ms for ms in ms_stations if ms.id == dbs.parent_station_id), None)
                if parent_ms:
                    dbs_to_ms_map[dbs.id] = parent_ms.code
        
        # Combine all DBS IDs
        all_dbs_ids = list(dbs_ids_from_map)
        
        dbs_stations = Station.objects.filter(
            type='DBS',
            id__in=all_dbs_ids
        ).prefetch_related(
            'trips_destination__ms', 'trips_destination__driver', 'trips_destination__vehicle'
        )
        
        ms_data = []
        for ms in ms_stations:
            trips = []
            # Use actual Trip model status values
            for trip in ms.trips_origin.filter(
                status__in=['PENDING', 'AT_MS', 'IN_TRANSIT', 'AT_DBS', 'COMPLETED', 'CANCELLED']
            ).order_by('-started_at'):
                trips.append({
                    'id': f'TRIP-{trip.id}',
                    'msId': ms.code,
                    'msName': ms.name,
                    'dbsId': trip.dbs.code if trip.dbs else None,
                    'dbsName': trip.dbs.name if trip.dbs else None,
                    'status': trip.status,
                    'scheduledTime': timezone.localtime(trip.started_at).isoformat() if trip.started_at else None,
                    'driverName': trip.driver.full_name if trip.driver else None,
                    'vehicleNumber': trip.vehicle.registration_no if trip.vehicle else None,
                })
            
            ms_data.append({
                'msId': ms.code,
                'msName': ms.name,
                'location': ms.address or ms.city or '',
                'trips': trips
            })
        
        dbs_data = []
        for dbs in dbs_stations:
            trips = []
            # Use actual Trip model status values
            for trip in dbs.trips_destination.filter(
                status__in=['PENDING', 'AT_MS', 'IN_TRANSIT', 'AT_DBS', 'COMPLETED', 'CANCELLED']
            ).order_by('-started_at'):
                trips.append({
                    'id': f'TRIP-{trip.id}',
                    'msId': trip.ms.code if trip.ms else None,
                    'msName': trip.ms.name if trip.ms else None,
                    'dbsId': dbs.code,
                    'dbsName': dbs.name,
                    'status': trip.status,
                    'scheduledTime': timezone.localtime(trip.started_at).isoformat() if trip.started_at else None,
                    'driverName': trip.driver.full_name if trip.driver else None,
                    'vehicleNumber': trip.vehicle.registration_no if trip.vehicle else None,
                })
            
            dbs_data.append({
                'dbsId': dbs.code,
                'dbsName': dbs.name,
                'msId': dbs_to_ms_map.get(dbs.id),
                'location': dbs.address or dbs.city or '',
                'trips': trips
            })
        
        return Response({
            'msStations': ms_data,
            'dbsStations': dbs_data
        })



class EICReconciliationReportView(views.APIView):
    """
    GET /api/eic/reconciliation-reports/
    Returns reconciliation reports with variance analysis.
    POST /api/eic/reconciliation-reports/{id}/action/ - Trigger corrective action
    """
    def get(self, request):
        # Filter params
        status_filter = request.query_params.get('status', 'ALL')
        severity_filter = request.query_params.get('severity', 'ALL')
        
        # Get reconciliation records with variance
        reconciliations = Reconciliation.objects.select_related(
            'trip', 'trip__ms', 'trip__dbs'
        ).order_by('-created_at')
        
        reports = []
        for rec in reconciliations:
            trip = rec.trip
            if not trip:
                continue
                
            # Calculate variance
            ms_qty = rec.ms_quantity or 0
            dbs_qty = rec.dbs_quantity or 0
            variance = abs(ms_qty - dbs_qty)
            variance_pct = (variance / ms_qty * 100) if ms_qty > 0 else 0
            
            # Determine severity
            if variance_pct > 1.0:
                severity = 'HIGH'
            elif variance_pct > 0.5:
                severity = 'MEDIUM'
            else:
                severity = 'LOW'
            
            # Map status
            if rec.status == 'PENDING':
                report_status = 'REVIEW_PENDING'
            elif rec.status == 'APPROVED':
                report_status = 'RESOLVED'
            elif rec.status == 'FLAGGED':
                report_status = 'ACTION_PENDING'
            else:
                report_status = rec.status
            
            # Apply filters
            if status_filter != 'ALL' and report_status != status_filter:
                continue
            if severity_filter != 'ALL' and severity != severity_filter:
                continue
            
            # Root cause signals based on variance type
            signals = []
            if variance_pct > 0.5:
                signals.append('Variance exceeds threshold')
            if ms_qty > dbs_qty:
                signals.append('Transit loss detected')
            elif dbs_qty > ms_qty:
                signals.append('Meter discrepancy')
            
            reports.append({
                'id': rec.id,
                'msName': trip.ms.name if trip.ms else None,
                'msStation': trip.ms.code if trip.ms else None,
                'dbsStation': trip.dbs.code if trip.dbs else None,
                'dbsName': trip.dbs.name if trip.dbs else None,
                'reportingPeriod': rec.created_at.strftime('%b %Y'),
                'variancePercentage': round(variance_pct, 2),
                'volumeDiscrepancy': variance,
                'financialImpact': int(variance * 50),  # Approx INR 50/scm
                'currency': 'INR',
                'severity': severity,
                'status': report_status,
                'rootCauseSignals': signals,
                'recommendedAction': 'Review meter readings and conduct audit' if variance_pct > 0.5 else 'Monitor for next transfer',
                'correctiveActions': [],  # Would come from separate model
                'tripId': trip.id,
                'msQuantity': ms_qty,
                'dbsQuantity': dbs_qty
            })
        
        return Response({'reports': reports})


class EICReconciliationActionView(views.APIView):
    """
    POST /api/eic/reconciliation-reports/{reportId}/action/
    Trigger corrective action on a reconciliation report
    """
    def post(self, request, report_id):
        rec = get_object_or_404(Reconciliation, id=report_id)
        
        action_type = request.data.get('actionType', 'FOLLOW_UP')
        notes = request.data.get('notes', '')
        next_status = request.data.get('nextStatus', '')
        user_id = request.data.get('userId')
        
        # Update reconciliation status
        if next_status == 'RESOLVED':
            rec.status = 'APPROVED'
        elif next_status == 'ACTION_TRIGGERED':
            rec.status = 'FLAGGED'
        rec.notes = f"{rec.notes or ''}\n[{action_type}] {notes}"
        rec.save()
        
        # Create alert for the action
        Alert.objects.create(
            trip=rec.trip,
            alert_type='RECONCILIATION_ACTION',
            severity='HIGH' if action_type == 'AUDIT' else 'MEDIUM',
            message=f"Corrective action triggered: {action_type}. {notes}",
            acknowledged=False
        )
        
        return Response({
            'status': 'action_triggered',
            'action': {
                'actionId': f'ACT-{rec.id}-{timezone.now().strftime("%H%M%S")}',
                'actionType': action_type,
                'status': 'PENDING',
                'triggeredAt': timezone.localtime(timezone.now()).isoformat()
            }
        })


class EICVehicleTrackingView(views.APIView):
    """
    GET /api/eic/vehicles/active
    Returns active vehicles with location derived from trip status.
    NOTE: No VTS integration. Location is simulated based on trip status.
    """
    def get(self, request):
        # Get active trips (vehicles in transit)
        active_trips = Trip.objects.filter(
            status__in=['EN_ROUTE_TO_MS', 'AT_MS', 'FILLING', 'FILLED', 
                       'EN_ROUTE_TO_DBS', 'AT_DBS', 'DECANTING']
        ).select_related('vehicle', 'driver', 'ms', 'dbs')
        
        vehicles = []
        for trip in active_trips:
            if not trip.vehicle:
                continue
            
            # Derive location from trip status (No VTS)
            if trip.status in ['EN_ROUTE_TO_MS']:
                current_location = {
                    'latitude': 23.0225,  # Simulated
                    'longitude': 72.5714,
                    'address': f'En route to {trip.ms.name if trip.ms else "MS"}'
                }
                destination = {
                    'latitude': float(trip.ms.lat) if trip.ms and trip.ms.lat else 23.05,
                    'longitude': float(trip.ms.lng) if trip.ms and trip.ms.lng else 72.55,
                    'address': trip.ms.address if trip.ms else 'MS Station'
                }
                route_status = 'IN_TRANSIT'
            elif trip.status in ['AT_MS', 'FILLING', 'FILLED']:
                current_location = {
                    'latitude': float(trip.ms.lat) if trip.ms and trip.ms.lat else 23.05,
                    'longitude': float(trip.ms.lng) if trip.ms and trip.ms.lng else 72.55,
                    'address': trip.ms.address if trip.ms else 'MS Station'
                }
                destination = {
                    'latitude': float(trip.dbs.lat) if trip.dbs and trip.dbs.lat else 23.02,
                    'longitude': float(trip.dbs.lng) if trip.dbs and trip.dbs.lng else 72.57,
                    'address': trip.dbs.address if trip.dbs else 'DBS Station'
                }
                route_status = 'ARRIVED' if trip.status in ['FILLING', 'FILLED'] else 'APPROACHING_DESTINATION'
            elif trip.status in ['EN_ROUTE_TO_DBS']:
                current_location = {
                    'latitude': 23.0350,  # Simulated mid-point
                    'longitude': 72.5500,
                    'address': f'En route to {trip.dbs.name if trip.dbs else "DBS"}'
                }
                destination = {
                    'latitude': float(trip.dbs.lat) if trip.dbs and trip.dbs.lat else 23.02,
                    'longitude': float(trip.dbs.lng) if trip.dbs and trip.dbs.lng else 72.57,
                    'address': trip.dbs.address if trip.dbs else 'DBS Station'
                }
                route_status = 'IN_TRANSIT'
            else:  # AT_DBS, DECANTING
                current_location = {
                    'latitude': float(trip.dbs.lat) if trip.dbs and trip.dbs.lat else 23.02,
                    'longitude': float(trip.dbs.lng) if trip.dbs and trip.dbs.lng else 72.57,
                    'address': trip.dbs.address if trip.dbs else 'DBS Station'
                }
                destination = current_location.copy()
                route_status = 'ARRIVED'
            
            vehicles.append({
                'vehicleId': trip.vehicle.registration_no,
                'tripId': trip.id,
                'driverId': trip.driver.id if trip.driver else None,
                'driverName': trip.driver.full_name if trip.driver else 'Unassigned',
                'currentLocation': current_location,
                'destination': destination,
                'speed': 0 if route_status == 'ARRIVED' else 45,  # Simulated
                'eta': timezone.localtime(timezone.now() + timezone.timedelta(hours=1)).isoformat(),  # Simulated
                'fuelLevel': 75,  # Simulated (no VTS)
                'status': route_status,
                'routeAdherence': 'ON_ROUTE',  # No VTS to detect deviation
                'deviationDistance': 0,
                'lastUpdated': timezone.localtime(timezone.now()).isoformat(),
                'tripStatus': trip.status
            })
        
        return Response({
            'totalActive': len(vehicles),
            'vehicles': vehicles,
            'note': 'Vehicle locations are derived from trip status. No real-time VTS integration.'
        })


class EICVehicleQueueView(views.APIView):
    """
    GET /api/eic/vehicle-queue
    Returns vehicle queue for MS bays (filling) or DBS bays (decanting).
    """
    def get(self, request):
        station_type = request.query_params.get('type', 'MS')  # MS or DBS
        station_id = request.query_params.get('stationId')
        
        # Get trips in queue (waiting for filling/decanting)
        if station_type == 'MS':
            queue_statuses = ['AT_MS', 'FILLING']
            trips = Trip.objects.filter(status__in=queue_statuses)
            if station_id:
                trips = trips.filter(ms_id=station_id)
        else:
            queue_statuses = ['AT_DBS', 'DECANTING']
            trips = Trip.objects.filter(status__in=queue_statuses)
            if station_id:
                trips = trips.filter(dbs_id=station_id)
        
        trips = trips.select_related('vehicle', 'driver', 'ms', 'dbs').order_by('dbs_arrival_at')
        
        # Build queue
        queue = []
        for idx, trip in enumerate(trips, 1):
            queue.append({
                'queuePosition': idx,
                'vehicleId': trip.vehicle.vehicle_number if trip.vehicle else f'V-{trip.id}',
                'driverId': trip.driver.id if trip.driver else None,
                'driverName': trip.driver.name if trip.driver else 'Unknown',
                'cargoType': 'LPG',
                'quantity': f'{trip.scheduled_quantity or 0} KL',
                'arrivalTime': timezone.localtime(trip.ms_arrival_at or trip.dbs_arrival_at or timezone.now()).isoformat(),
                'estimatedWaitTime': f'{idx * 30} min',  # Simulated
                'status': 'loading' if trip.status in ['FILLING', 'DECANTING'] else 'waiting',
                'bayAssigned': None,  # Would come from bay management
                'tripId': trip.id
            })
        
        # Simulated bays (no actual bay management system)
        bays = [
            {'bayId': 'BAY-A', 'status': 'occupied' if len(queue) > 0 else 'free', 
             'currentVehicle': queue[0]['vehicleId'] if queue else None},
            {'bayId': 'BAY-B', 'status': 'occupied' if len(queue) > 1 else 'free',
             'currentVehicle': queue[1]['vehicleId'] if len(queue) > 1 else None},
            {'bayId': 'BAY-C', 'status': 'maintenance', 'currentVehicle': None},
        ]
        
        return Response({
            'stationType': station_type,
            'stationId': station_id,
            'bays': bays,
            'queue': queue,
            'totalInQueue': len(queue)
        })


class EICIncomingStockRequestsView(views.APIView):
    """
    GET /api/eic/incoming-stock-requests
    Returns incoming stock requests from FDODO, DBS operators, and AI predictions.
    """
    def get(self, request):
        type_filter = request.query_params.get('type', 'ALL')
        status_filter = request.query_params.get('status', 'ALL')
        priority_filter = request.query_params.get('priority', 'ALL')
        
        requests = StockRequest.objects.select_related(
            'dbs', 'requested_by_user'
        ).order_by('-created_at')
        
        # Apply filters
        if status_filter != 'ALL':
            requests = requests.filter(status=status_filter)
        if type_filter != 'ALL':
            requests = requests.filter(request_type=type_filter)
        if priority_filter != 'ALL':
            requests = requests.filter(priority=priority_filter)
        
        results = []
        for req in requests[:50]:  # Limit to 50
            results.append({
                'id': f'REQ-{req.id:03d}',
                'type': req.request_type or 'DBS',
                'status': req.status,
                'priority': req.priority or 'MEDIUM',
                'customer': req.customer_name or (req.dbs.name if req.dbs else 'Unknown'),
                'dbsId': req.dbs.code if req.dbs else None,
                'dbsName': req.dbs.name if req.dbs else None,
                'quantity': req.quantity,
                'product': 'LPG',
                'requestedAt': timezone.localtime(req.created_at).isoformat(),
                'notes': req.notes or '',
                'requestedBy': req.requested_by_user.username if req.requested_by_user else None
            })
        
        return Response({'requests': results})

