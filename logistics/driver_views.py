from rest_framework import viewsets, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404
from .models import StockRequest, Trip, Shift, Token
import json
import logging
import uuid 
logger = logging.getLogger(__name__)

# Get assignment timeout from settings (default 5 minutes)
DRIVER_ASSIGNMENT_TIMEOUT = getattr(settings, 'DRIVER_ASSIGNMENT_TIMEOUT_SECONDS', 300)


class DriverTripViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='pending-offers')
    def pending_offers(self, request):
        """
        Get pending trip offers assigned to this driver.
        
        GET /api/driver/trips/pending-offers/
        
        Returns list of stock requests that are:
        - Status = ASSIGNING
        - target_driver = current driver
        - Not expired (within timeout window)
        
        This is the "pull" mechanism for when driver clears notification
        and opens the app - they can still see their pending offers.
        """
        driver = getattr(request.user, 'driver_profile', None)
        if not driver:
            return Response({'error': 'User is not a driver'}, status=status.HTTP_403_FORBIDDEN)
        
        now = timezone.now()
        
        # Find pending offers for this driver
        pending_requests = StockRequest.objects.filter(
            status='ASSIGNING',
            target_driver=driver
        ).select_related('dbs', 'dbs__parent_station')
        
        offers = []
        for req in pending_requests:
            # Check if expired
            is_expired = False
            remaining_seconds = DRIVER_ASSIGNMENT_TIMEOUT
            
            if req.assignment_started_at:
                elapsed = (now - req.assignment_started_at).total_seconds()
                remaining_seconds = max(0, DRIVER_ASSIGNMENT_TIMEOUT - elapsed)
                if elapsed > DRIVER_ASSIGNMENT_TIMEOUT:
                    is_expired = True
                    # Skip expired offers (Celery will clean them up)
                    continue
            
            ms = req.dbs.parent_station if req.dbs else None
            
            offers.append({
                'stock_request_id': req.id,
                'dbs': {
                    'id': req.dbs.id if req.dbs else None,
                    'name': req.dbs.name if req.dbs else None,
                    'address': req.dbs.address if req.dbs else None,
                },
                'ms': {
                    'id': ms.id if ms else None,
                    'name': ms.name if ms else None,
                    'address': ms.address if ms else None,
                } if ms else None,
                'quantity_kg': float(req.requested_qty_kg) if req.requested_qty_kg else None,
                'priority': req.priority_preview,
                'assigned_at': req.assignment_started_at.isoformat() if req.assignment_started_at else None,
                'remaining_seconds': int(remaining_seconds),
                'expires_in': f"{int(remaining_seconds // 60)}m {int(remaining_seconds % 60)}s",
            })
        
        return Response({
            'pending_offers': offers,
            'count': len(offers),
            'timeout_seconds': DRIVER_ASSIGNMENT_TIMEOUT
        })

    @action(detail=False, methods=['post'], url_path='accept')
    def accept_trip(self, request):
        """
        Driver accepts a trip offer.
        
        POST /api/driver/trips/accept/
        Payload: {"stock_request_id": 123}
        
        Creates Trip when driver accepts.
        """
        driver = getattr(request.user, 'driver_profile', None)
        if not driver:
             return Response({'error': 'User is not a driver'}, status=status.HTTP_403_FORBIDDEN)
             
        stock_req_id = request.data.get('stock_request_id')
        if not stock_req_id:
            return Response({'error': 'stock_request_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            with transaction.atomic():
                # LOCK the row to prevent race conditions
                stock_req = StockRequest.objects.select_for_update().get(id=stock_req_id)
                
                # 1. Validate Status - Must be ASSIGNING
                if stock_req.status != 'ASSIGNING':
                    return Response({
                        'error': 'Trip is no longer available',
                        'current_status': stock_req.status
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
                # 2. Validate Timeout
                if stock_req.assignment_started_at:
                    elapsed = (timezone.now() - stock_req.assignment_started_at).total_seconds()
                    if elapsed > DRIVER_ASSIGNMENT_TIMEOUT:
                        # Reset to PENDING for EIC to reassign
                        stock_req.status = 'PENDING'
                        stock_req.assignment_started_at = None
                        stock_req.target_driver = None
                        stock_req.save()
                        logger.warning(f"Driver {driver.id} tried to accept expired offer for StockRequest {stock_req.id} (elapsed: {elapsed:.0f}s)")
                        return Response({
                            'error': 'Offer has expired. The 5-minute acceptance window has passed.',
                            'expired': True
                        }, status=status.HTTP_400_BAD_REQUEST)
                     
                # 3. Validate Target Driver (Must be assigned to this driver)
                if stock_req.target_driver and stock_req.target_driver != driver:
                    return Response({
                        'error': 'This trip was not offered to you'
                    }, status=status.HTTP_403_FORBIDDEN)
                    
                # 4. Find driver's active shift for vehicle
                from .services import find_active_shift
                active_shift = find_active_shift(driver, timezone.now())
                
                # Was:
                # active_shift = Shift.objects.filter(
                #    driver=driver, 
                #    status='APPROVED',
                #    start_time__lte=timezone.now(),
                #    end_time__gte=timezone.now()
                # ).first()
                
                # Note: find_active_shift handles both one-time and recurring
                
                if not active_shift:
                    return Response({
                        'error': 'No active shift found. Please ensure you have an approved shift.'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # 5. Create Token (Refactored to token_no hash)
                ms = stock_req.dbs.parent_station
                # sequence_no removed in favor of hashed unique code
                
                token = Token.objects.create(
                    vehicle=active_shift.vehicle,
                    ms=ms,
                    # token_no auto-generated
                )
                
                # 6. Create Trip
                trip = Trip.objects.create(
                    stock_request=stock_req,
                    token=token,
                    driver=driver,
                    vehicle=active_shift.vehicle,
                    ms=ms,
                    dbs=stock_req.dbs,
                    status='PENDING'
                )
                
                # 7. Update StockRequest
                stock_req.status = 'ASSIGNED'
                stock_req.save()
                
                # 8. Send notification to DBS Operator
                try:
                    from core.notification_service import NotificationService
                    notification_service = NotificationService()
                    
                    # Find DBS operator
                    from core.models import UserRole
                    dbs_operator_role = UserRole.objects.filter(
                        station=stock_req.dbs,
                        role__code='DBS_OPERATOR',
                        active=True
                    ).first()
                    
                    if dbs_operator_role and dbs_operator_role.user:
                        notification_service.send_to_user(
                            user=dbs_operator_role.user,
                            title="Driver Assigned",
                            body=f"Token #{token.token_no} - Driver: {driver.full_name}, Vehicle: {active_shift.vehicle.registration_no}",
                            data={
                                'type': 'DRIVER_ASSIGNED',
                                'trip_id': trip.id,
                                'token_number': token.token_no,
                                'driver_name': driver.full_name,
                                'vehicle_no': active_shift.vehicle.registration_no
                            }
                        )
                        
                        
                    # Notify EIC Operators (specific to the MS of the DBS)
                    from core.models import User, UserRole
                    ms = stock_req.dbs.parent_station if stock_req.dbs else None
                    if ms:
                        eic_roles = UserRole.objects.filter(
                            station=ms,
                            role__code='EIC',
                            active=True
                        )
                        for eic_role in eic_roles:
                            if eic_role.user:
                                notification_service.send_to_user(
                                    user=eic_role.user,
                                    title="Trip Accepted",
                                    body=f"Driver {driver.full_name} accepted trip to {stock_req.dbs.name}. Token: {token.token_no}",
                                    data={
                                        'type': 'TRIP_ACCEPTED',
                                        'trip_id': str(trip.id),
                                        'driver_id': str(driver.id),
                                        'token_number': str(token.token_no),
                                        'dbs_name': str(stock_req.dbs.name)
                                    }
                                )
                except Exception as e:
                    print(f"Notification error: {e}")

                response_data = {
                    'success': True,
                    'status': 'accepted',
                    'trip_id': trip.id,
                    'token_number': token.token_no,
                    'message': 'Trip accepted successfully'
                }

                logger.info("Trip Accept Response:\n" + json.dumps(response_data, indent=4))

                return Response(response_data)
                
        except StockRequest.DoesNotExist:
            return Response({'error': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='reject')
    def reject_trip(self, request):
        """
        Driver rejects a trip offer with reason.
        
        POST /api/driver/trips/reject/
        Payload: {
            "stock_request_id": 123,
            "reason": "Vehicle breakdown"
        }
        
        Notifies EIC to choose another driver.
        """
        driver = getattr(request.user, 'driver_profile', None)
        if not driver:
            return Response({'error': 'User is not a driver'}, status=status.HTTP_403_FORBIDDEN)
        
        stock_req_id = request.data.get('stock_request_id')
        reason = request.data.get('reason', 'No reason provided')
        
        if not stock_req_id:
            return Response({'error': 'stock_request_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():
                stock_req = StockRequest.objects.select_for_update().get(id=stock_req_id)
                
                # Validate status
                if stock_req.status != 'ASSIGNING':
                    return Response({
                        'error': 'Trip is no longer available for rejection',
                        'current_status': stock_req.status
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Validate target driver
                if stock_req.target_driver and stock_req.target_driver != driver:
                    return Response({
                        'error': 'This trip was not offered to you'
                    }, status=status.HTTP_403_FORBIDDEN)
                
                # Reset the stock request for EIC to reassign
                stock_req.status = 'PENDING'
                stock_req.assignment_started_at = None
                stock_req.target_driver = None
                stock_req.assignment_mode = None
                stock_req.save()
                
                # Notify EIC about rejection
                try:
                    from core.notification_service import NotificationService
                    from core.models import UserRole
                    notification_service = NotificationService()
                    
                    # Find EIC for this MS
                    ms = stock_req.dbs.parent_station if stock_req.dbs else None
                    dbs_name = stock_req.dbs.name if stock_req.dbs else ''
                    
                    if ms:
                        eic_roles = UserRole.objects.filter(
                            station=ms,
                            role__code='EIC',
                            active=True
                        )
                        
                        print(f"Found {eic_roles.count()} EIC roles for MS: {ms.name}")
                        
                        for eic_role in eic_roles:
                            if eic_role.user:
                                print(f"Sending rejection notification to EIC: {eic_role.user.email}")
                                result = notification_service.send_to_user(
                                    user=eic_role.user,
                                    title="Driver Rejected Trip",
                                    body=f"Driver: {driver.full_name}\nDBS: {dbs_name}\nReason: {reason}\n\nPlease assign another driver.",
                                    data={
                                        'type': 'DRIVER_REJECTED',
                                        'stock_request_id': str(stock_req.id),
                                        'driver_name': str(driver.full_name),
                                        'to_dbs': str(dbs_name),
                                        'reason': str(reason)
                                    }
                                )
                                print(f"Notification result: {result}")
                    else:
                        print("No MS found for DBS - cannot notify EIC")
                except Exception as e:
                    import traceback
                    print(f"Notification error: {e}")
                    traceback.print_exc()
                
                return Response({
                    'success': True,
                    'status': 'rejected',
                    'message': 'Trip rejected. EIC has been notified to assign another driver.'
                })

        except StockRequest.DoesNotExist:
            return Response({'error': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='arrival/ms')
    def arrival_at_ms(self, request):   # app arivead at ms app 
        """
        Confirm arrival at Mother Station.
        Payload: { "token": "TRIP_TOKEN_XYZ" }
        """
        driver = getattr(request.user, 'driver_profile', None)
        if not driver:
            return Response({'error': 'User is not a driver'}, status=status.HTTP_403_FORBIDDEN)
            
        token_val = request.data.get('token')
        if not token_val:
            return Response({'error': 'Token is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # Find trip by token
            trip = Trip.objects.select_related('token', 'vehicle', 'dbs').get(
                driver=driver,
                token__token_no=token_val,
                status__in=['PENDING', 'AT_MS'] # Allow idempotent retry
            )
            
            if trip.status == 'PENDING':
                trip.status = 'AT_MS'
                trip.origin_confirmed_at = timezone.now() 
                trip.save()
                
                # Notify MS Operator
                try:
                    from core.notification_service import NotificationService
                    from core.models import UserRole
                    notification_service = NotificationService()
                    
                    # Find MS Operator
                    ms_operator_role = UserRole.objects.filter(
                        station=trip.ms,
                        role__code='MS_OPERATOR',
                        active=True
                    ).first()
                    
                    if ms_operator_role and ms_operator_role.user:
                        notification_service.send_to_user(
                            user=ms_operator_role.user,
                            title="Truck Arrived",
                            body=f"Truck {trip.vehicle.registration_no} has arrived at {trip.ms.name}",
                            data={
                                "type": "ms_arrival",
                                "tripId": f"{trip.id}",
                                "driverId": str(driver.id),
                                "truckNumber": trip.vehicle.registration_no,
                                "tripToken": trip.token.token_no if trip.token else ""
                            }
                        )
                except Exception as e:
                    print(f"Error sending MS arrival notification: {e}")
            
            return Response({
                "success": True, 
                "message": "Arrival confirmed"
            })
        except Trip.DoesNotExist:
            return Response({'error': 'Active trip not found for this token'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'], url_path='arrival/dbs')
    def arrival_at_dbs(self, request):
        """
        Confirm arrival at Daughter Booster Station.
        Payload: { "token": "TRIP_TOKEN_XYZ" }
        """
        driver = getattr(request.user, 'driver_profile', None)
        if not driver:
             return Response({'error': 'User is not a driver'}, status=status.HTTP_403_FORBIDDEN)
             
        token_val = request.data.get('token')
        if not token_val:
            return Response({'error': 'Token is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            trip = Trip.objects.select_related('token', 'vehicle', 'dbs').get(
                driver=driver,
                token__token_no=token_val,
                status__in=['IN_TRANSIT', 'AT_DBS','DISPATCHED']
            )
            
            # Update status if not already
            if trip.status == 'IN_TRANSIT' or trip.status == 'DISPATCHED':
                trip.status = 'AT_DBS'
                trip.dbs_arrival_at = timezone.now()
                trip.save()
                
                # Send Notification to DBS Operator
                try:
                    from core.notification_service import NotificationService
                    from core.models import UserRole
                    notification_service = NotificationService()
                    
                    # Find DBS Operator
                    dbs_operator_role = UserRole.objects.filter(
                        station=trip.dbs,
                        role__code='DBS_OPERATOR',
                        active=True
                    ).first()
                    
                    if dbs_operator_role and dbs_operator_role.user:
                         notification_service.send_to_user(
                            user=dbs_operator_role.user,
                            title="Despatch Arrived",
                            body=f"Truck {trip.vehicle.registration_no} has arrived at {trip.dbs.name}",
                            data={
                                "type": "dbs_arrival",
                                "trip_id": str(trip.id),
                                "driver_id": str(driver.id),
                                "truck_number": trip.vehicle.registration_no,
                                "trip_token": trip.token.token_no if trip.token else ""
                            }
                        )
                except Exception as e:
                    print(f"Error sending DBS arrival notification: {e}")

            return Response({
                "success": True,
                "message": "Arrival at DBS confirmed"
            })
            
        except Trip.DoesNotExist:
             return Response({'error': 'Active trip not found for this token'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'], url_path='meter-reading/confirm')
    def confirm_meter_reading(self, request):
        """
        Confirm meter reading (Pre/Post) at MS or DBS.
        """
        driver = getattr(request.user, 'driver_profile', None)
        if not driver:
            return Response({'error': 'User is not a driver'}, status=status.HTTP_403_FORBIDDEN)
            
        token_val = request.data.get('token')
        station_type = request.data.get('stationType') # MS or DBS
        reading_type = request.data.get('readingType') # pre or post
        reading_val = request.data.get('reading')
        photo_base64 = request.data.get('photoBase64') # Not saving yet
        
        try:
            trip = Trip.objects.get(driver=driver, token__token_no=token_val)
            
            from .models import MSFilling, DBSDecanting
            
            # Handle Photo Upload
            photo_file = None
            if photo_base64:
                try:
                    import base64
                    from django.core.files.base import ContentFile
                    
                    # Handle both formats:
                    # 1. "data:image/png;base64,<base64_data>" (with prefix)
                    # 2. "<base64_data>" (raw base64 string)
                    if ';base64,' in photo_base64:
                        format, imgstr = photo_base64.split(';base64,')
                        ext = format.split('/')[-1] if '/' in format else 'jpg'
                    else:
                        # Raw base64 string without prefix, default to jpg
                        imgstr = photo_base64
                        ext = 'jpg'
                    
                    file_name = f"reading_{trip.id}_{station_type}_{reading_type}_{uuid.uuid4().hex[:6]}.{ext}"
                    photo_file = ContentFile(base64.b64decode(imgstr), name=file_name)
                except Exception as e:
                    print(f"Error decoding photo: {e}")
                    # Don't fail the whole request? Or fail? User said "add this field", implies it's important.
                    # But driver might have issues. Log and continue or fail? 
                    # Let's log but continue for now, unless strict requirement.
                    pass
            
            if station_type == 'MS':
                # Ensure MSFilling record exists
                filling, _ = MSFilling.objects.get_or_create(trip=trip)
                
                if reading_type == 'pre':
                    filling.prefill_pressure_bar = reading_val
                    filling.start_time = timezone.now()
                    if photo_file:
                        filling.prefill_photo = photo_file
                elif reading_type == 'post':
                    filling.postfill_pressure_bar = reading_val
                    filling.end_time = timezone.now()
                    if photo_file:
                       filling.postfill_photo = photo_file
                    
                    if request.data.get('confirmed'):
                        filling.confirmed_by_driver = request.user
                        # Also update trip status if post-fill?
                        trip.status = 'IN_TRANSIT'
                        trip.ms_departure_at = timezone.now()
                        trip.save()
                filling.save()
                
            elif station_type == 'DBS':
                # Ensure DBSDecanting record exists
                decanting, _ = DBSDecanting.objects.get_or_create(trip=trip)
                
                if reading_type == 'pre':
                    decanting.pre_dec_reading = reading_val
                    decanting.start_time = timezone.now()
                    if photo_file:
                        decanting.pre_decant_photo = photo_file
                        
                    trip.status = 'AT_DBS'
                    trip.dbs_arrival_at = timezone.now()
                    trip.save()
                elif reading_type == 'post':
                    decanting.post_dec_reading = reading_val
                    decanting.end_time = timezone.now()
                    if photo_file:
                        decanting.post_decant_photo = photo_file
                        
                    if request.data.get('confirmed'):
                        decanting.confirmed_by_driver = request.user
                        trip.status = 'DECANTING_CONFIRMED'
                        trip.dbs_departure_at = timezone.now()
                        trip.save()
                decanting.save()
                
            return Response({"success": True})
            
        except Trip.DoesNotExist:
             return Response({'error': 'Trip not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
             return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
