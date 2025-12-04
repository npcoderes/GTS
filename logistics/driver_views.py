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
                
                # 1. Validate Status
                if stock_req.status != 'ASSIGNING':
                    return Response({'error': 'Trip is no longer available'}, status=status.HTTP_400_BAD_REQUEST)
                    
                # 2. Validate Timeout (5 minutes)
                if stock_req.assignment_started_at and (timezone.now() - stock_req.assignment_started_at).total_seconds() > 300:
                     return Response({'error': 'Offer expired'}, status=status.HTTP_400_BAD_REQUEST)
                     
                # 3. Validate Target (Manual Mode)
                if stock_req.target_driver and stock_req.target_driver != driver:
                    return Response({'error': 'This trip was not offered to you'}, status=status.HTTP_403_FORBIDDEN)
                    
                # 4. Success - Create Trip
                # Find the vehicle from the driver's active shift
                # We assume the driver has an active approved shift for the vehicle at the MS
                # Ideally we should query this again to be safe
                active_shift = Shift.objects.filter(
                    driver=driver, 
                    status='APPROVED',
                    start_time__lte=timezone.now(),
                    end_time__gte=timezone.now()
                ).first()
                
                if not active_shift:
                     return Response({'error': 'No active shift found for driver'}, status=status.HTTP_400_BAD_REQUEST)

                # Create Token (Optional, but usually required for Trip)
                # Logic from previous approve method
                ms = stock_req.dbs.parent_station
                last_token = Token.objects.filter(ms=ms).order_by('-sequence_no').first()
                sequence_no = (last_token.sequence_no + 1) if last_token else 1
                
                token = Token.objects.create(
                    vehicle=active_shift.vehicle,
                    ms=ms,
                    sequence_no=sequence_no
                )
                
                trip = Trip.objects.create(
                    stock_request=stock_req,
                    token=token,
                    driver=driver,
                    vehicle=active_shift.vehicle,
                    ms=ms,
                    dbs=stock_req.dbs,
                    status='PENDING',
                    started_at=timezone.now() # Or maybe not started yet? PENDING usually means not started.
                    # But for now let's keep it consistent with previous logic or leave null if PENDING means "Accepted but not left"
                )
                
                stock_req.status = 'ASSIGNED'
                stock_req.save()
                
                # TODO: Trigger background task to cancel other notifications (if possible)
                
                return Response({
                    'status': 'accepted',
                    'trip_id': trip.id,
                    'message': 'Trip accepted successfully'
                })
                
        except StockRequest.DoesNotExist:
            return Response({'error': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
