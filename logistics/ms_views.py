from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Trip, MSFilling, Token
from core.models import Station


class MSTripScheduleView(views.APIView):
    """
    GET /api/ms/{msId}/schedule
    Returns trip schedule for MS operator dashboard (mobile app)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, ms_id):
        # Get MS station (support both ID and code)
        try:
            ms = Station.objects.get(id=ms_id, type='MS')
        except (Station.DoesNotExist, ValueError):
            ms = Station.objects.filter(code=ms_id, type='MS').first()
            if not ms:
                return Response(
                    {'error': f'MS station not found: {ms_id}'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Fetch trips for this MS (today and future, plus recent past)
        trips = Trip.objects.filter(ms=ms).select_related(
            'dbs', 'vehicle', 'driver'
        ).prefetch_related('ms_fillings').order_by('-started_at', '-id')[:50]
        
        trip_data = []
        for trip in trips:
            # Get filled quantity if available
            filling = trip.ms_fillings.first()
            qty = filling.filled_qty_kg if filling and filling.filled_qty_kg else None
            
            trip_data.append({
                'id': f'TRIP-{trip.id:03d}',
                'tripId': trip.id,
                'dbsId': trip.dbs.code if trip.dbs else None,
                'dbsName': trip.dbs.name if trip.dbs else None,
                'status': trip.status,
                'scheduledTime': trip.started_at.isoformat() if trip.started_at else None,
                'product': 'CNG',  # Default product
                'quantity': qty,
                'vehicleNumber': trip.vehicle.registration_no if trip.vehicle else None,
                'driverName': trip.driver.full_name if trip.driver else None,
                'stoNumber': trip.sto_number,
                'route': f'{ms.name} → {trip.dbs.name}' if trip.dbs else ms.name
            })
        
        return Response({
            'station': {
                'msId': ms.id,
                'msName': ms.name,
                'msCode': ms.code,
                'location': ms.address or ms.city or '',
                'status': 'OPERATIONAL'  # Could be dynamic based on station status
            },
            'trips': trip_data
        })



class MSFillPrefillView(views.APIView):
    """Get prefill data for MS filling operation"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, token_id):
        # Get trip by token
        token = get_object_or_404(Token, id=token_id, status='ACTIVE')
        trip = token.trip
        
        # Get or create MSFilling record
        filling, created = MSFilling.objects.get_or_create(trip=trip)
        
        # Return prefill data
        return Response({
            'tripId': trip.id,
            'tokenId': token_id,
            'vehicle': {
                'registrationNo': trip.vehicle.registration_no,
                'capacity': trip.vehicle.capacity_kg
            },
            'driver': {
                'name': trip.driver.user.full_name if trip.driver else 'Unknown',
                'phone': trip.driver.user.phone if trip.driver else None
            },
            'route': {
                'from': trip.ms.name,
                'to': trip.dbs.name
            },
            'currentReading': {
                'pressure': filling.prefill_pressure_bar if filling.prefill_pressure_bar else 0,
                'mfm': filling.prefill_mfm if filling.prefill_mfm else 0
            }
        })


class MSFillStartView(views.APIView):
    """Start MS filling operation"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, token_id):
        token = get_object_or_404(Token, id=token_id, status='ACTIVE')
        trip = token.trip
        
        # Get or create MSFilling record
        filling, created = MSFilling.objects.get_or_create(trip=trip)
        
        # Update filling start time and readings
        filling.start_time = timezone.now()
        filling.prefill_pressure_bar = request.data.get('pressure', 0)
        filling.prefill_mfm = request.data.get('mfm', 0)
        filling.save()
        
        # Update trip status
        trip.status = 'FILLING'
        trip.save()
        
        return Response({
            'status': 'started',
            'tripId': trip.id,
            'sessionId': trip.id,  # Use trip ID as session ID
            'startTime': filling.start_time.isoformat()
        })


class MSFillEndView(views.APIView):
    """End MS filling operation"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, token_id):
        token = get_object_or_404(Token, id=token_id, status='ACTIVE')
        trip = token.trip
        
        # Get MSFilling record
        filling = get_object_or_404(MSFilling, trip=trip)
        
        # Update filling end time and readings
        filling.end_time = timezone.now()
        filling.postfill_pressure_bar = request.data.get('pressure', 0)
        filling.postfill_mfm = request.data.get('mfm', 0)
        
        # Calculate filled quantity
        if filling.prefill_mfm and filling.postfill_mfm:
            filling.filled_qty_kg = float(filling.postfill_mfm) - float(filling.prefill_mfm)
        
        filling.save()
        
        # Update trip status
        trip.status = 'FILLED'
        trip.save()
        
        return Response({
            'status': 'completed',
            'tripId': trip.id,
            'filledQuantity': filling.filled_qty_kg,
            'endTime': filling.end_time.isoformat(),
            'readings': {
                'preFill': {
                    'pressure': filling.prefill_pressure_bar,
                    'mfm': filling.prefill_mfm
                },
                'postFill': {
                    'pressure': filling.postfill_pressure_bar,
                    'mfm': filling.postfill_mfm
                }
            }
        })


class STOGenerateView(views.APIView):
    """Generate STO (Stock Transfer Order) for trip"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, trip_id):
        trip = get_object_or_404(Trip, id=trip_id)
        filling = get_object_or_404(MSFilling, trip=trip)
        
        # Generate STO number (in real system, this would integrate with SAP)
        sto_number = f"STO-{trip.ms.code}-{trip.dbs.code}-{trip.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        
        # Update trip with STO info
        trip.sto_number = sto_number
        trip.status = 'DISPATCHED'
        trip.ms_departure_at = timezone.now()
        trip.save()
        
        return Response({
            'status': 'generated',
            'stoNumber': sto_number,
            'tripId': trip.id,
            'quantity': filling.filled_qty_kg,
            'generatedAt': timezone.now().isoformat(),
            'route': {
                'from': trip.ms.name,
                'to': trip.dbs.name
            }
        })


class MSStockTransferListView(views.APIView):
    """Get completed stock transfers for MS"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, ms_id):
        # Get MS station
        ms = get_object_or_404(Station, id=ms_id, type='MS')
        
        # Fetch Completed Trips (Transfers from this MS)
        trips = Trip.objects.filter(
            ms=ms,
            status__in=['COMPLETED', 'DISPATCHED', 'IN_TRANSIT', 'AT_DBS']
        ).select_related('ms', 'dbs', 'vehicle').prefetch_related('ms_fillings').order_by('-started_at')
        
        data = []
        for trip in trips:
            # Get filled quantity
            filling = trip.ms_fillings.first()
            qty = filling.filled_qty_kg if filling and filling.filled_qty_kg else 0
            
            # Determine completion/dispatch time
            transfer_time = trip.ms_departure_at or trip.started_at
            
            data.append({
                "id": f"TRIP-{trip.id:03d}",
                "route": f"{trip.ms.name} → {trip.dbs.name}",
                "product": "CNG",
                "quantity": qty,
                "status": trip.status,
                "vehicleNo": trip.vehicle.registration_no,
                "transferredAt": transfer_time.isoformat() if transfer_time else None,
                "stoNumber": trip.sto_number
            })
        
        return Response(data)

