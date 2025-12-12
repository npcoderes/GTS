from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Trip, MSFilling, Token
from core.models import Station
from datetime import datetime, timedelta


class MSDashboardView(views.APIView):
    """
    API Path: GET /api/ms/dashboard/
    Returns MS dashboard data including station info, summary counts, and trips.
    """
    
    def get(self, request, ms_id=None):
        # Determine MS Station
        user = request.user
        ms = None
        
        # 1. Try getting from URL param (if provided)
        if ms_id:
             ms = get_object_or_404(Station, id=ms_id, type='MS')
        
        # 2. Try query param (testing)
        if not ms:
            ms_id_param = request.query_params.get('ms_id')
            if ms_id_param:
                ms = get_object_or_404(Station, id=ms_id_param, type='MS')
        
        # 3. Try from User Role
        if not ms:
            user_role = user.user_roles.filter(role__code='MS_OPERATOR', active=True).first()
            if user_role and user_role.station and user_role.station.type == 'MS':
                ms = user_role.station
                
        # 4. Fallback/Error
        if not ms:
             return Response(
                {'error': 'User is not assigned to an MS station and no ms_id provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Date Filtering
        end_date_str = request.query_params.get('end_date')
        start_date_str = request.query_params.get('start_date')
        
        try:
            current_date = timezone.now().date()
            if end_date_str:
                end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            else:
                end_date_obj = current_date
            
            # Make end_date inclusive (end of day)
            # Filter logic: created_at or started_at? Typically started_at for trips.
            # Using simple date comparison or ranges.
            
            if start_date_str:
                start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            else:
                start_date_obj = end_date_obj - timedelta(days=30)
                
        except ValueError:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch Trips
        # Relevant statuses for MS dashboard
        # 'filling' card -> PENDING, AT_MS, FILLING, FILLED
        # 'dispatched' card -> DISPATCHED, IN_TRANSIT, ARRIVED_AT_DBS, AT_DBS, DECANTING_STARTED, DECANTING_COMPLETE, DECANTING_CONFIRMED
        # 'completed' card -> COMPLETED
        # 'cancelled' card -> CANCELLED
        trips = Trip.objects.filter(
            ms=ms,
            created_at__date__gte=start_date_obj,
            created_at__date__lte=end_date_obj
        ).select_related(
            'dbs', 'vehicle'
        ).prefetch_related('ms_fillings').order_by('-created_at', '-id')[:100] # Limit to recent 100 for dashboard
        
        summary = {
            'pending': 0,
            'inProgress': 0,
            'completed': 0
        }
        
        trip_list = []
        
        for trip in trips:
            status_val = trip.status
            display_status = status_val
            
            # Map status for display
            if status_val == 'DECANTING_CONFIRMED':
                display_status = 'AT_DBS'
            
            # Map to summary counts
            # Pending: At MS (Pending, Arrived, Filling, Filled but not dispatch)
            if status_val in ['PENDING', 'AT_MS', 'FILLING', 'FILLED']:
                summary['pending'] += 1
            # In Progress: On the road or at DBS
            elif status_val in ['DISPATCHED', 'IN_TRANSIT', 'AT_DBS', 'DECANTING_CONFIRMED']: 
                summary['inProgress'] += 1
            # Completed
            elif status_val == 'COMPLETED':
                summary['completed'] += 1
            
            # Get Quantity (Filled quantity)
            filling = trip.ms_fillings.first()
            quantity = float(filling.filled_qty_kg) if filling and filling.filled_qty_kg else 0
            if quantity == 0 and trip.vehicle:
                # Fallback to capacity if not filled yet? Or keep 0? User asked for 5000 example.
                # Let's keep 0 if not filled, but user example shows quantity present.
                pass 
                
            trip_list.append({
                "id": f"{trip.id}",
                "dbsId": trip.dbs.code if trip.dbs else "",
                "status": display_status,
                "quantity": quantity,
                "scheduledTime": timezone.localtime(trip.started_at).isoformat() if trip.started_at else timezone.localtime(timezone.now()).isoformat(), # Fallback
                "completedTime": timezone.localtime(trip.completed_at).isoformat() if trip.completed_at else None,
                "dbsName": trip.dbs.name if trip.dbs else "Unknown",
                "route": f"{ms.name} -> {trip.dbs.name}" if trip.dbs else f"{ms.name} -> ?"
            })
            
        return Response({
            "station": {
                "msName": ms.name,
                "location": ms.city or ms.address or "Unknown Location"
            },
            "summary": summary,
            "trips": trip_list
        })

class MSTripScheduleView(views.APIView):
    """
    API Path: GET /api/ms/{ms_id}/schedule
    Get trip schedule for specific MS.
    """
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
                'id': f'{trip.id}',
                'tripId': trip.id,
                'dbsId': trip.dbs.code if trip.dbs else None,
                'dbsName': trip.dbs.name if trip.dbs else None,
                'status': trip.status,
                'scheduledTime': timezone.localtime(trip.started_at).isoformat() if trip.started_at else None,
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
    """
    API Path: None (Not mapped in urls.py)
    Legacy prefill view - not currently used.
    """
    """Get prefill data for MS filling operation"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, token_id):
        # Get trip by token
        token = get_object_or_404(Token, token_no=token_id, status='ACTIVE')
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


class MSConfirmArrivalView(views.APIView):
    """
    API Path: POST /api/ms/arrival/confirm
    MS operator confirms driver arrival at MS.
    """
    """
    Step 1: MS Arrival Confirm  POST /ms/arrival/confirm
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token_val = request.data.get('tripToken')
        if not token_val:
            return Response({'error': 'tripToken is required'}, status=status.HTTP_400_BAD_REQUEST)

        trip = get_object_or_404(Trip, token__token_no=token_val)

        # Verify user is from correct MS?
        # Assuming permissions handle general MS access for now.

        if trip.status == 'PENDING': # Or other valid statuses?
             trip.status = 'AT_MS'
             trip.ms_return_at = timezone.now() # Are they returning? Or starting?
             # Initial flow: PENDING -> AT_MS. Return flow: ARRIVED_AT_MS?
             # If trip just started, it's PENDING or AT_MS.
             # If user says "Arrival Confirm", it usually means driver arrived.
             # If status is already AT_MS, just return success.
             trip.save()
        elif trip.status != 'AT_MS':
             # Maybe force update?
             trip.status = 'AT_MS'
             trip.save()

        trip.started_at = timezone.now()
        trip.save()

        return Response({
            "success": True,
            "trip": {
                "id": f"{trip.id}",
                "status": "AT_MS",
                "truckNumber": trip.vehicle.registration_no if trip.vehicle else ""
            }
        })


class MSFillResumeView(views.APIView):
    """
    API Path: POST /api/ms/fill/resume
    Resume filling process and get current state.
    """
    """
    Resume MS Filling - Get current filling state when operator reopens app

    POST /api/ms/fill/resume
    Payload: { "tripToken": "TOKEN123" }

    Returns existing MSFilling data if operator closed app after entering pre-reading
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token_val = request.data.get('tripToken')
        if not token_val:
            return Response({'error': 'tripToken is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            trip = Trip.objects.select_related(
                'token', 'vehicle', 'driver', 'ms', 'dbs'
            ).prefetch_related('ms_fillings').get(token__token_no=token_val)

            # Get MSFilling record if exists
            filling = trip.ms_fillings.first()

            if not filling:
                # No filling record yet, return empty state
                return Response({
                    'hasFillingData': False,
                    'tripToken': token_val,
                    'trip': {
                        'id': trip.id,
                        'status': trip.status,
                        'currentStep': trip.current_step,
                        'vehicle': {
                            'registrationNo': trip.vehicle.registration_no if trip.vehicle else None,
                            'capacity_kg': str(trip.vehicle.capacity_kg) if trip.vehicle else None,
                        },
                        'driver': {
                            'name': trip.driver.full_name if trip.driver else None,
                        },
                        'route': {
                            'from': trip.ms.name if trip.ms else None,
                            'to': trip.dbs.name if trip.dbs else None,
                        }
                    }
                })

            # Return existing filling data
            return Response({
                'hasFillingData': True,
                'tripToken': token_val,
                'trip': {
                    'id': trip.id,
                    'status': trip.status,
                    'currentStep': trip.current_step,
                    'stepData': trip.step_data,
                    'vehicle': {
                        'registrationNo': trip.vehicle.registration_no if trip.vehicle else None,
                        'capacity_kg': str(trip.vehicle.capacity_kg) if trip.vehicle else None,
                    },
                    'driver': {
                        'name': trip.driver.full_name if trip.driver else None,
                    },
                    'route': {
                        'from': trip.ms.name if trip.ms else None,
                        'to': trip.dbs.name if trip.dbs else None,
                    }
                },
                'fillingData': {
                    'id': filling.id,
                    'prefill_pressure_bar': str(filling.prefill_pressure_bar) if filling.prefill_pressure_bar else None,
                    'prefill_mfm': str(filling.prefill_mfm) if filling.prefill_mfm else None,
                    'postfill_pressure_bar': str(filling.postfill_pressure_bar) if filling.postfill_pressure_bar else None,
                    'postfill_mfm': str(filling.postfill_mfm) if filling.postfill_mfm else None,
                    'filled_qty_kg': str(filling.filled_qty_kg) if filling.filled_qty_kg else None,
                    'prefill_photo_url': filling.prefill_photo.url if filling.prefill_photo else None,
                    'postfill_photo_url': filling.postfill_photo.url if filling.postfill_photo else None,
                    'confirmed_by_ms_operator': filling.confirmed_by_ms_operator_id is not None,
                    'start_time': filling.start_time.isoformat() if filling.start_time else None,
                    'end_time': filling.end_time.isoformat() if filling.end_time else None,

                    # Helper flags for UI
                    'has_prefill_data': filling.prefill_pressure_bar is not None or filling.prefill_mfm is not None,
                    'has_postfill_data': filling.postfill_pressure_bar is not None or filling.postfill_mfm is not None,
                    'is_complete': filling.confirmed_by_ms_operator_id is not None,
                }
            })

        except Trip.DoesNotExist:
            return Response({'error': 'Trip not found for this token'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MSFillStartView(views.APIView):
    """
    API Path: POST /api/ms/fill/start
    Start filling process with pre-fill readings.
    """
    """
    Step 2: Start Filling (Pre-Readings) POST /ms/fill/start  app
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        token_val = request.data.get('tripToken')
        pressure = request.data.get('pressure')
        mfm = request.data.get('mfm')
        
        if not token_val:
            return Response({'error': 'tripToken is required'}, status=status.HTTP_400_BAD_REQUEST)

        trip = get_object_or_404(Trip, token__token_no=token_val)
        
        # Get or create MSFilling record
        filling, created = MSFilling.objects.get_or_create(trip=trip)
        
        # Update filling start time and readings
        filling.start_time = timezone.now()
        if pressure: filling.prefill_pressure_bar = pressure
        if mfm: filling.prefill_mfm = mfm
        filling.save()

        # Update trip status and step tracking
        trip.status = 'FILLING'
        trip.current_step = 3  # Step 3: MS Filling in progress
        trip.step_data = {**trip.step_data, 'ms_pre_reading_done': True}
        trip.save()

        # Send WebSocket update to Driver
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            if trip.driver:
                group_name = f"driver_{trip.driver.id}"
                async_to_sync(channel_layer.group_send)(
                    group_name,
                    {
                        'type': 'driver.update',
                        'data': {
                            'type': 'MS_FILL_START',
                            'trip_id': trip.id,
                            'prefill_reading': float(filling.prefill_mfm or 0),
                            'pressure': float(filling.prefill_pressure_bar or 0),
                            'message': 'Filling started at MS'
                        }
                    }
                )
        except Exception as e:
            print(f"WebSocket Error: {e}")
        
        return Response({
            "success": True,
            "message": "Filling started successfully",
            "trip": {
                "status": "FILLING"
            }
        })


class MSFillEndView(views.APIView):
    """
    API Path: POST /api/ms/fill/end
    End filling process with post-fill readings.
    """
    """
    Step 3: End Filling (Post-Readings) POST /ms/fill/end app
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        token_val = request.data.get('tripToken')
        pressure = request.data.get('pressure')
        mfm = request.data.get('mfm')
        
        if not token_val:
             return Response({'error': 'tripToken is required'}, status=status.HTTP_400_BAD_REQUEST)

        trip = get_object_or_404(Trip, token__token_no=token_val)
        
        # Get MSFilling record
        filling = get_object_or_404(MSFilling, trip=trip)
        
        # Update filling end time and readings
        filling.end_time = timezone.now()
        if pressure: filling.postfill_pressure_bar = pressure
        if mfm: filling.postfill_mfm = mfm
        
        # Calculate filled quantity
        if filling.prefill_mfm and filling.postfill_mfm:
            try:
                filling.filled_qty_kg = float(filling.postfill_mfm) - float(filling.prefill_mfm)
            except ValueError:
                pass

        filling.save()

        # Update trip status and step tracking
        trip.status = 'FILLED'
        trip.step_data = {**trip.step_data, 'ms_post_reading_done': True}
        trip.save()

        # Send WebSocket update to Driver
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            if trip.driver:
                group_name = f"driver_{trip.driver.id}"
                async_to_sync(channel_layer.group_send)(
                    group_name,
                    {
                        'type': 'driver.update',
                        'data': {
                            'type': 'MS_FILL_END',
                            'trip_id': trip.id,
                            'postfill_reading': float(filling.postfill_mfm or 0),
                            'pressure': float(filling.postfill_pressure_bar or 0),
                            'filled_qty': float(filling.filled_qty_kg or 0),
                            'message': 'Filling completed at MS'
                        }
                    }
                )
        except Exception as e:
            print(f"WebSocket Error: {e}")
        
        return Response({
            "success": True,
            "message": "Filling ended successfully",
            "trip": {
                "status": "FILLED"
            }
        })


class MSConfirmFillingView(views.APIView):
    """
    API Path: POST /api/ms/fill/confirm
    Confirm filling completion.
    """
    """
    Step 4: Final Confirmation     POST /ms/fill/confirm:  app
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        token_val = request.data.get('tripToken')
        delivered_qty = request.data.get('deliveredQty')
        
        if not token_val:
             return Response({'error': 'tripToken is required'}, status=status.HTTP_400_BAD_REQUEST)

        trip = get_object_or_404(Trip, token__token_no=token_val)
        filling = get_object_or_404(MSFilling, trip=trip)
        
        if delivered_qty:
             filling.filled_qty_kg = delivered_qty
             filling.save()

        # Generate STO logic here or just mark status?
        # User says "Operation confirmed" -> status: COMPLETED (or similar)
        # We will set to DISPATCHED as it leaves MS?
        # But payload expectation says "trip": {"status": "COMPLETED"}
        # Let's verify if COMPLETED is appropriate. If it's the *filling* completion, maybe FILLED is enough?
        # If the trip is starting, DISPATCHED is the correct flow.
        # But if the user wants "COMPLETED" in response, we can send that string key for frontend
        # while keeping internal status correct.

        trip.status = 'DISPATCHED'
        trip.sto_number = f"STO-{trip.ms.code}-{trip.dbs.code}-{trip.id}-{timezone.now().strftime('%Y%m%d%H%M')}"
        trip.ms_departure_at = timezone.now()
        trip.current_step = 4  # Step 4: Departed MS, heading to DBS
        trip.step_data = {**trip.step_data, 'ms_filling_confirmed': True}
        trip.save()
        
        return Response({
            "success": True,
            "message": "Operation confirmed",
            "trip": {
                "status": "COMPLETED" # For frontend UI as requested
            }
        })


class MSStockTransferListView(views.APIView):
    """
    API Path: GET /api/ms/{ms_id}/transfers
    List stock transfers for specific MS.
    """
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
                "id": f"{trip.id}",
                "route": f"{trip.ms.name} → {trip.dbs.name}",
                "product": "CNG",
                "quantity": qty,
                "status": trip.status,
                "vehicleNo": trip.vehicle.registration_no,
                "transferredAt": timezone.localtime(transfer_time).isoformat() if transfer_time else None,
                "stoNumber": trip.sto_number
            })
        
        return Response(data)


class MSClusterView(views.APIView):
    """
    API Path: GET /api/ms/cluster
    Get MS cluster data (parent MS and child DBSs).
    """
    """
    GET /api/ms/cluster
    Fetches the list of DBS stations linked to the logged-in MS. app
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Determine MS (similar logic to dashboard)
        ms = None
        # 1. From URL/Query param (for testing/admin)
        ms_id_param = request.query_params.get('ms_id')
        if ms_id_param:
             ms = Station.objects.filter(id=ms_id_param, type='MS').first()
        
        # 2. From User Role
        if not ms:
            user_role = user.user_roles.filter(role__code='MS_OPERATOR', active=True).first()
            if user_role and user_role.station and user_role.station.type == 'MS':
                ms = user_role.station
        
        if not ms:
             return Response(
                {'error': 'User is not assigned to an MS station'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get Linked DBS
        linked_dbs = Station.objects.filter(parent_station=ms, type='DBS')
        
        dbs_list = []
        for dbs in linked_dbs:
            dbs_list.append({
                "dbsId": dbs.id, # Or dbs.code? User example shows "DBS-01" which looks like code or ID.
                "dbsName": dbs.name,
                "location": dbs.address or dbs.city or "Unknown",
                "region": dbs.city or "Unknown", # Fallback to city as state/region not on model
                "primaryMsName": ms.name
            })
            
        return Response({
            "ms": {
                "msName": ms.name
            },
            "dbs": dbs_list
        })


class MSStockTransferHistoryByDBSView(views.APIView):
    """
    API Path: GET /api/ms/stock-transfers/by-dbs
    Get stock transfer history grouped by DBS.
    """
    """
    GET /api/ms/stock-transfers/by-dbs
    Fetches history of stock transfers for a specific DBS.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Determine MS
        ms = None
        ms_id_param = request.query_params.get('ms_id') # Optional override
        if ms_id_param:
             ms = Station.objects.filter(id=ms_id_param, type='MS').first()
        
        if not ms:
            user_role = user.user_roles.filter(role__code='MS_OPERATOR', active=True).first()
            if user_role and user_role.station and user_role.station.type == 'MS':
                ms = user_role.station
        
        if not ms:
             return Response({'error': 'MS not identified'}, status=status.HTTP_400_BAD_REQUEST)

        # Get Parameters
        dbs_id = request.query_params.get('dbs_id')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        
        if not dbs_id:
            return Response({'error': 'dbs_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Get DBS
        dbs = get_object_or_404(Station, id=dbs_id, type='DBS', parent_station=ms)
        
        # Filter Trips
        trips = Trip.objects.filter(ms=ms, dbs=dbs)
        
        # Date Filtering
        if start_date_str and end_date_str:
            try:
                from django.utils.dateparse import parse_datetime
                start_date = parse_datetime(start_date_str)
                end_date = parse_datetime(end_date_str)
                
                # If parse_datetime returns None (e.g. YYYY-MM-DD only), try strptime
                if not start_date:
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                if not end_date:
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)
                
                trips = trips.filter(created_at__range=[start_date, end_date])
            except Exception as e:
                print(f"Date filter error: {e}")
                pass
                
        trips = trips.select_related('dbs', 'vehicle').prefetch_related('ms_fillings').order_by('-created_at')

        # Summary Calculation
        total_transfers = 0
        in_progress = 0
        completed = 0
        
        transfer_list = []
        
        for trip in trips:
            status_val = trip.status
            total_transfers += 1
            
            # Map status
            # In Progress: PENDING, AT_MS, FILLING, FILLED, DISPATCHED, IN_TRANSIT, ARRIVED_at_DBS, AT_DBS, DECANTING...
            # Completed: COMPLETED
            # User example: COMPLETED vs IN_PROGRESS
            
            trip_status_mapped = "IN_PROGRESS"
            if status_val == 'COMPLETED':
                completed += 1
                trip_status_mapped = "COMPLETED"
            elif status_val == 'CANCELLED':
                 trip_status_mapped = "CANCELLED"
                 # Do we count cancelled? User summary didn't explicitly say.
            else:
                in_progress += 1
                
            # Values
            filling = trip.ms_fillings.first()
            qty = float(filling.filled_qty_kg) if filling and filling.filled_qty_kg else 0
            
            transfer_list.append({
                "id": f"{trip.id}", # User requested TRF-1001 like ID, using TRIP check
                "type": "OUTGOING", # From MS perspective
                "status": trip_status_mapped,
                "productName": "CNG",
                "quantity": qty,
                "initiatedAt": timezone.localtime(trip.created_at).isoformat() if trip.created_at else None, # or started_at
                "completedAt": timezone.localtime(trip.completed_at).isoformat() if trip.completed_at else None,
                "estimatedCompletion": timezone.localtime(trip.created_at + timedelta(hours=4)).isoformat() if trip.created_at else None, # Dummy estimate
                "fromLocation": ms.name,
                "toLocation": dbs.name,
                "notes": trip.sto_number or ""
            })

        return Response({
            "summary": {
                "totalTransfers": total_transfers,
                "inProgress": in_progress,
                "completed": completed,
                "outgoingTotal": total_transfers,
                "outgoingInProgress": in_progress,
                "outgoingCompleted": completed
            },
            "transfers": transfer_list
        })


class MSPendingArrivalsView(views.APIView):
    """
    API Path: GET /api/ms/pending-arrivals
    Get pending vehicle arrivals at MS.
    """
    """
    GET /api/ms/pending-arrivals
    Returns list of trucks that have arrived at MS (status=AT_MS) 
    with the same data structure as the push notification.
    This is a fallback for when notifications are missed/cleared.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        ms = None
        
        # Try query param (for testing)
        ms_id_param = request.query_params.get('ms_id')
        if ms_id_param:
            ms = get_object_or_404(Station, id=ms_id_param, type='MS')
        else:
            # Get from user role
            user_role = user.user_roles.filter(role__code='MS_OPERATOR', active=True).first()
            if user_role and user_role.station and user_role.station.type == 'MS':
                ms = user_role.station
        
        if not ms:
            return Response(
                {'error': 'User is not assigned to an MS station'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get trips that have arrived at MS (waiting for filling to start)
        # These are trips where driver has clicked "Arrive at MS"
        pending_arrivals = Trip.objects.filter(
            ms=ms,
            status__in=['AT_MS', 'PENDING']  # AT_MS = arrived, PENDING might also be waiting
        ).filter(
            origin_confirmed_at__isnull=False  # Driver has confirmed arrival
        ).select_related('vehicle', 'driver', 'driver__user', 'token').order_by('-origin_confirmed_at')
        
        arrivals = []
        for trip in pending_arrivals:
            arrivals.append({
                # Same structure as notification data
                "type": "ms_arrival",
                "tripId": str(trip.id),
                "driverId": str(trip.driver.id) if trip.driver else "",
                "truckNumber": trip.vehicle.registration_no if trip.vehicle else "",
                "tripToken": trip.token.token_no if trip.token else "",
                # Additional helpful info
                "driverName": trip.driver.user.get_full_name() if trip.driver and trip.driver.user else "",
                "arrivedAt": timezone.localtime(trip.origin_confirmed_at).isoformat() if trip.origin_confirmed_at else None,
                "msName": ms.name,
                "dbsName": trip.dbs.name if trip.dbs else "",
            })
        
        return Response({
            "success": True,
            "stationName": ms.name,
            "arrivals": arrivals
        })
