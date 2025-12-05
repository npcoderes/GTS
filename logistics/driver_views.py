from rest_framework import viewsets, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404
from .models import StockRequest, Trip, Shift, Token

class DriverTripViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

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
                    
                # 2. Validate Timeout (5 minutes)
                if stock_req.assignment_started_at:
                    elapsed = (timezone.now() - stock_req.assignment_started_at).total_seconds()
                    if elapsed > 300:  # 5 minutes
                        stock_req.status = 'APPROVED'  # Reset for EIC to reassign
                        stock_req.assignment_started_at = None
                        stock_req.target_driver = None
                        stock_req.save()
                        return Response({'error': 'Offer expired'}, status=status.HTTP_400_BAD_REQUEST)
                     
                # 3. Validate Target Driver (Must be assigned to this driver)
                if stock_req.target_driver and stock_req.target_driver != driver:
                    return Response({
                        'error': 'This trip was not offered to you'
                    }, status=status.HTTP_403_FORBIDDEN)
                    
                # 4. Find driver's active shift for vehicle
                active_shift = Shift.objects.filter(
                    driver=driver, 
                    status='APPROVED',
                    start_time__lte=timezone.now(),
                    end_time__gte=timezone.now()
                ).first()
                
                if not active_shift:
                    return Response({
                        'error': 'No active shift found. Please ensure you have an approved shift.'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # 5. Create Token
                ms = stock_req.dbs.parent_station
                last_token = Token.objects.filter(ms=ms).order_by('-sequence_no').first()
                sequence_no = (last_token.sequence_no + 1) if last_token else 1
                
                token = Token.objects.create(
                    vehicle=active_shift.vehicle,
                    ms=ms,
                    sequence_no=sequence_no
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
                            body=f"Token #{token.sequence_no} - Driver: {driver.full_name}, Vehicle: {active_shift.vehicle.registration_no}",
                            data={
                                'type': 'DRIVER_ASSIGNED',
                                'trip_id': trip.id,
                                'token_number': token.sequence_no,
                                'driver_name': driver.full_name,
                                'vehicle_no': active_shift.vehicle.registration_no
                            }
                        )
                except Exception as e:
                    print(f"Notification error: {e}")
                
                return Response({
                    'success': True,
                    'status': 'accepted',
                    'trip_id': trip.id,
                    'token_number': token.sequence_no,
                    'message': 'Trip accepted successfully'
                })
                
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
                stock_req.status = 'PENDING'  # Go back to pending
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

    @action(detail=False, methods=['get'], url_path='pending')
    def pending_offers(self, request):
        """
        Get pending trip offers for the current driver.
        
        GET /api/driver/trips/pending/
        """
        driver = getattr(request.user, 'driver_profile', None)
        if not driver:
            return Response({'error': 'User is not a driver'}, status=status.HTTP_403_FORBIDDEN)
        
        # Find offers assigned to this driver
        pending_offers = StockRequest.objects.filter(
            status='ASSIGNING',
            target_driver=driver
        ).select_related('dbs', 'dbs__parent_station')
        
        offers = []
        for req in pending_offers:
            # Check if not expired
            if req.assignment_started_at:
                elapsed = (timezone.now() - req.assignment_started_at).total_seconds()
                if elapsed > 300:  # Expired
                    continue
            
            offers.append({
                'stock_request_id': req.id,
                'dbs_name': req.dbs.name if req.dbs else 'Unknown',
                'ms_name': req.dbs.parent_station.name if req.dbs and req.dbs.parent_station else 'Unknown',
                'quantity_kg': float(req.requested_qty_kg),
                'priority': req.priority_preview,
                'requested_at': req.created_at.isoformat(),
                'expires_in_seconds': max(0, 300 - int(elapsed)) if req.assignment_started_at else 300
            })
        
        return Response({
            'pending_offers': offers,
            'count': len(offers)
        })
