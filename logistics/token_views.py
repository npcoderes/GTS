"""
Token Queue Views for GTS Backend

API endpoints for driver token requests and EIC queue visibility.
"""
import logging
from rest_framework import views, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import VehicleToken, Driver, Vehicle
from .token_queue_service import (
    token_queue_service, TokenQueueError, NoActiveShiftError, DriverAlreadyHasTokenError
)
from core.models import Station
from core.error_response import (
    validation_error_response, not_found_response, server_error_response
)

logger = logging.getLogger(__name__)


class DriverTokenViewSet(viewsets.ViewSet):
    """
    API Path: /api/driver/token/
    
    Driver token management endpoints.
    
    Actions:
      - POST /api/driver/token/request - Request queue token at MS
      - GET /api/driver/token/current - Get current token status
      - POST /api/driver/token/cancel - Cancel waiting token
    """
    permission_classes = [IsAuthenticated]
    
    @action(methods=['post'], detail=False)
    def request(self, request):
        """
        Request a queue token at Mother Station.
        
        POST /api/driver/token/request
        Payload: { "ms_id": 123 }
        
        Requires:
        - Driver must have an active APPROVED shift
        - Driver must not have an existing WAITING token
        
        Returns:
        - Token details including sequence number and status
        - If auto-allocated, includes trip details
        """
        ms_id = request.data.get('ms_id')
        
        if not ms_id:
            return validation_error_response("ms_id is required")
        
        # Get driver from authenticated user
        try:
            driver = Driver.objects.select_related('assigned_vehicle').get(user=request.user)
        except Driver.DoesNotExist:
            return validation_error_response("User is not a registered driver")
        
        # Validate vehicle
        vehicle = driver.assigned_vehicle
        if not vehicle:
            return validation_error_response("Driver has no assigned vehicle")
        
        # Validate MS
        try:
            ms = Station.objects.get(id=ms_id, type__in=['MS','Mother Station'])
        except Station.DoesNotExist:
            return not_found_response("Mother Station not found")
        
        # Request token
        try:
            token = token_queue_service.request_token(driver, vehicle, ms)
            
            response_data = {
                'success': True,
                'token': {
                    'id': token.id,
                    'token_no': token.token_no,
                    'sequence_number': token.sequence_number,
                    'status': token.status,
                    'issued_at': token.issued_at.isoformat(),
                    'ms_id': token.ms_id,
                    'ms_name': ms.name,
                }
            }
            
            # Include trip info if allocated
            if token.status == 'ALLOCATED' and token.trip:
                response_data['token']['allocated_at'] = token.allocated_at.isoformat()
                response_data['trip'] = {
                    'id': token.trip.id,
                    'dbs_id': token.trip.dbs_id,
                    'dbs_name': token.trip.dbs.name if token.trip.dbs else None,
                    'status': token.trip.status,
                    'token_no': token.trip.token.token_no if token.trip.token else None,
                }
                response_data['message'] = 'Token allocated to trip immediately'
            else:
                response_data['message'] = 'Token issued. Waiting for stock request allocation.'
                response_data['queue_position'] = token.sequence_number
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except NoActiveShiftError as e:
            return validation_error_response(str(e), error_code='NO_ACTIVE_SHIFT')
        
        except DriverAlreadyHasTokenError as e:
            return validation_error_response(str(e), error_code='TOKEN_EXISTS')
        
        except TokenQueueError as e:
            return validation_error_response(str(e))
        
        except Exception as e:
            logger.exception(f"Error requesting token: {e}")
            return server_error_response("Failed to request token")
    
    @action(methods=['get'], detail=False)
    def current(self, request):
        """
        Get driver's current token status.
        
        GET /api/driver/token/current
        
        Returns current WAITING or ALLOCATED token for today.
        """
        try:
            driver = Driver.objects.get(user=request.user)
        except Driver.DoesNotExist:
            return validation_error_response("User is not a registered driver")
        
        token = token_queue_service.get_driver_current_token(driver)
        
        if not token:
            return Response({
                'has_token': False,
                'message': 'No active token for today'
            })
        
        response_data = {
            'has_token': True,
            'token': {
                'id': token.id,
                'token_no': token.token_no,
                'sequence_number': token.sequence_number,
                'status': token.status,
                'issued_at': token.issued_at.isoformat(),
                'ms_id': token.ms_id,
                'ms_name': token.ms.name if token.ms else None,
            }
        }
        
        if token.status == 'ALLOCATED' and token.trip:
            response_data['token']['allocated_at'] = token.allocated_at.isoformat()
            response_data['trip'] = {
                'id': token.trip.id,
                'dbs_id': token.trip.dbs_id,
                'dbs_name': token.trip.dbs.name if token.trip.dbs else None,
                'status': token.trip.status,
            }
        
        return Response(response_data)
    
    @action(methods=['post'], detail=False)
    def cancel(self, request):
        """
        Cancel waiting token (driver leaves queue).
        
        POST /api/driver/token/cancel
        Payload: { "token_id": 123 } or {} to cancel current token
        """
        try:
            driver = Driver.objects.get(user=request.user)
        except Driver.DoesNotExist:
            return validation_error_response("User is not a registered driver")
        
        token_id = request.data.get('token_id')
        
        if token_id:
            try:
                token = VehicleToken.objects.get(id=token_id, driver=driver)
            except VehicleToken.DoesNotExist:
                return not_found_response("Token not found")
        else:
            token = token_queue_service.get_driver_current_token(driver)
            if not token:
                return validation_error_response("No active token to cancel")
        
        if token.status != 'WAITING':
            return validation_error_response(
                f"Cannot cancel token in {token.status} status"
            )
        
        try:
            token_queue_service.cancel_token(token, reason='CANCELLED_BY_DRIVER')
            return Response({
                'success': True,
                'message': f'Token {token.token_no} cancelled',
                'token_no': token.token_no
            })
        except TokenQueueError as e:
            return validation_error_response(str(e))
    
    @action(methods=['get'], detail=False, url_path='shift-details')
    def shift_details(self, request):
        """
        Get driver's current active shift with vehicle details.
        
        GET /api/driver/token/shift-details
        
        Returns:
        - Active shift info (start/end time, status)
        - Assigned vehicle details
        - MS home station info
        """
        try:
            driver = Driver.objects.select_related('assigned_vehicle').get(user=request.user)
        except Driver.DoesNotExist:
            return validation_error_response("User is not a registered driver")
        
        # Get active shift using existing service
        from .services import find_active_shift
        active_shift = find_active_shift(driver)
        
        if not active_shift:
            return Response({
                'has_active_shift': False,
                'message': 'No active shift at this time'
            })
        
        # Build response with shift and vehicle details
        vehicle = active_shift.vehicle
        response_data = {
            'has_active_shift': True,
            'shift': {
                'id': active_shift.id,
                'start_time': active_shift.start_time.isoformat(),
                'end_time': active_shift.end_time.isoformat(),
                'status': active_shift.status,
                'is_recurring': active_shift.is_recurring,
                'recurrence_pattern': active_shift.recurrence_pattern,
            },
            'vehicle': {
                'id': vehicle.id,
                'registration_no': vehicle.registration_no,
            } if vehicle else None,
            'driver': {
                'id': driver.id,
                'full_name': driver.full_name,
                'license_no': driver.license_no,
                'phone': driver.phone,
                'status': driver.status,
            }
        }
        
        # Add MS home if vehicle has one
        if vehicle and vehicle.ms_home:
            response_data['vehicle']['ms_home'] = {
                'id': vehicle.ms_home.id,
                'name': vehicle.ms_home.name,
                'code': vehicle.ms_home.code,
            }
        
        return Response(response_data)


class EICQueueView(views.APIView):
    """
    API Path: GET /api/eic/vehicle-queue
    
    Get vehicle queue status for all MS or specific MS.
    Shows waiting tokens and pending stock requests.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Get queue status.
        
        Query params:
        - ms_id: Filter by specific MS (optional)
        """
        # Verify EIC permission
        role_codes = list(
            request.user.user_roles.filter(active=True)
            .values_list('role__code', flat=True)
        )
        if 'EIC' not in role_codes and 'SUPER_ADMIN' not in role_codes:
            return Response({'error': 'Permission denied'}, status=403)
        
        ms_id = request.query_params.get('ms_id')
        
        if ms_id:
            # Single MS queue
            queue_data = token_queue_service.get_queue_status(int(ms_id))
            return Response(queue_data)
        
        # All MS queues
        ms_stations = Station.objects.filter(type='MS')
        queues = []
        
        for ms in ms_stations:
            queue_data = token_queue_service.get_queue_status(ms.id)
            queues.append(queue_data)
        
        return Response({
            'queues': queues,
            'total_waiting': sum(q.get('waiting_count', 0) for q in queues),
            'total_pending': sum(q.get('pending_count', 0) for q in queues),
        })


class EICQueueAllocationView(views.APIView):
    """
    API Path: POST /api/eic/vehicle-queue/allocate
    
    Manual queue allocation override by EIC.
    Allows EIC to allocate specific token to specific request.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Manually allocate token to stock request.
        
        Payload: {
            "token_id": 123,
            "stock_request_id": 456
        }
        """
        # Verify EIC permission
        role_codes = list(
            request.user.user_roles.filter(active=True)
            .values_list('role__code', flat=True)
        )
        if 'EIC' not in role_codes and 'SUPER_ADMIN' not in role_codes:
            return Response({'error': 'Permission denied'}, status=403)
        
        token_id = request.data.get('token_id')
        stock_request_id = request.data.get('stock_request_id')
        
        if not token_id or not stock_request_id:
            return validation_error_response("token_id and stock_request_id required")
        
        try:
            from .models import StockRequest
            from django.db import transaction
            
            with transaction.atomic():
                token = VehicleToken.objects.select_for_update().get(
                    id=token_id, status='WAITING'
                )
                stock_request = StockRequest.objects.select_for_update().get(
                    id=stock_request_id, status='APPROVED'
                )
                
                # Validate MS match
                if stock_request.dbs.parent_station_id != token.ms_id:
                    return validation_error_response(
                        f"DBS {stock_request.dbs.name} is not under MS {token.ms.name}"
                    )
                
                trip = token_queue_service._allocate_token_to_request(token, stock_request)
                
                return Response({
                    'success': True,
                    'message': 'Manual allocation successful',
                    'trip_id': trip.id,
                    'token_no': token.token_no,
                    'driver_name': token.driver.full_name,
                    'dbs_name': stock_request.dbs.name,
                })
                
        except VehicleToken.DoesNotExist:
            return not_found_response("Waiting token not found")
        except StockRequest.DoesNotExist:
            return not_found_response("Approved stock request not found")
        except Exception as e:
            logger.exception(f"Manual allocation error: {e}")
            return server_error_response("Allocation failed")
