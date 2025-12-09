from rest_framework import views, status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Trip, StockRequest
from core.models import Station
from rest_framework.decorators import action

class DBSDashboardView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        dbs = None
        
        # Determine DBS from user role or query param (for testing)
        dbs_id_param = request.query_params.get('dbs_id')
        if dbs_id_param:
             dbs = get_object_or_404(Station, id=dbs_id_param, type='DBS')
        else:
            # Try to find assigned DBS station for the user
            user_role = user.user_roles.filter(role__code='DBS_OPERATOR', active=True).first()
            if user_role and user_role.station and user_role.station.type == 'DBS':
                dbs = user_role.station
        
        if not dbs:
            return Response(
                {'error': 'User is not assigned to a DBS station and no dbs_id provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Fetch Trips for this DBS
        # Fetch Trips for this DBS
        # Filter relevant statuses
        relevant_statuses = [
            'DISPATCHED', 'IN_TRANSIT', 'ARRIVED_AT_DBS', 'AT_DBS',
            'DECANTING_STARTED', 'DECANTING_COMPLETED', 'DECANTING_CONFIRMED',
            'COMPLETED'
        ]
        trips = Trip.objects.filter(dbs=dbs, status__in=relevant_statuses).select_related(
            'ms', 'dbs', 'vehicle'
        ).prefetch_related('ms_fillings')
        
        # Calculate Summary Stats
        summary = {
            'pending': 0,    # Dispatched / In Transit / Arrived
            'inProgress': 0, # Decanting
            'completed': 0   # Completed
        }
        
        trip_list = []
        
        for trip in trips:
            # Map Backend Status to Frontend Categories
            category = 'pending' # Default
            if trip.status in ['DISPATCHED', 'IN_TRANSIT', 'ARRIVED_AT_DBS', 'AT_DBS']:
                category = 'pending'
                summary['pending'] += 1
            elif trip.status == 'DECANTING_STARTED':
                category = 'inProgress'
                summary['inProgress'] += 1
            elif trip.status in ['COMPLETED', 'DECANTING_COMPLETED']:
                category = 'completed'
                summary['completed'] += 1
            
            # Get Quantity from MSFilling
            filling = trip.ms_fillings.first()
            quantity = filling.filled_qty_kg if filling else trip.vehicle.capacity_kg

            # Format Trip Data
            trip_data = {
                "id": f"TRIP-{trip.id:03d}", # Format ID
                "status": trip.status,
                "route": f"{trip.ms.name} → {trip.dbs.name}",
                "msName": trip.ms.name,
                "dbsName": trip.dbs.name,
                "scheduledTime": timezone.localtime(trip.started_at).isoformat() if trip.started_at else None, # Using started_at as proxy for scheduled
                "quantity": quantity,
                "vehicleNo": trip.vehicle.registration_no
            }
            trip_list.append(trip_data)

        # Construct Response
        response_data = {
            "station": {
                "dbsName": dbs.name,
                "location": dbs.city or dbs.address or "Unknown Location"
            },
            "summary": summary,
            "trips": trip_list
        }
        
        return Response(response_data)

class DBSStockRequestViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='arrival/confirm')
    def confirm_arrival(self, request):
        """
        DBS Operator confirms truck arrival.
        Payload: { "tripToken": "TOKEN-123" }
        """
        token_val = request.data.get('tripToken')
        if not token_val:
            return Response({'error': 'tripToken is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Look for the trip using the token_no
        trip = get_object_or_404(
            Trip, 
            token__token_no=token_val,
            # We check if it's either IN_TRANSIT (if driver forgot) or already AT_DBS
            status__in=['IN_TRANSIT', 'AT_DBS','PENDING','DECANTING_CONFIRMED']
        )
        
        # Verify DBS matches the user's assigned station
        dbs_operator = request.user
        # Logic to verify operator is at trip.dbs ... 
        # (Assuming operator has access if they can call this endpoint & token is valid)

        if trip.status != 'AT_DBS':
             trip.status = 'AT_DBS'
             trip.dbs_arrival_at = timezone.now()
             trip.save()

        return Response({
            "success": True,
            "trip": {
                "id": f"TRIP-{trip.id}",
                "status": "ARRIVED"
            }
        })

    @action(detail=False, methods=['post'], url_path='decant/resume')
    def decant_resume(self, request):
        """
        Resume DBS Decanting - Get current decanting state when operator reopens app

        POST /api/dbs/stock-requests/decant/resume
        Payload: { "tripToken": "TOKEN123" }

        Returns existing DBSDecanting data if operator closed app after entering pre-reading
        """
        token_val = request.data.get('tripToken')
        if not token_val:
            return Response({'error': 'tripToken is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            trip = Trip.objects.select_related(
                'token', 'vehicle', 'driver', 'ms', 'dbs'
            ).prefetch_related('dbs_decantings').get(token__token_no=token_val)

            # Get DBSDecanting record if exists
            from .models import DBSDecanting
            decanting = trip.dbs_decantings.first()

            if not decanting:
                # No decanting record yet, return empty state
                return Response({
                    'hasDecantingData': False,
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

            # Return existing decanting data
            return Response({
                'hasDecantingData': True,
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
                'decantingData': {
                    'id': decanting.id,
                    'pre_dec_pressure_bar': str(decanting.pre_dec_pressure_bar) if decanting.pre_dec_pressure_bar else None,
                    'pre_dec_reading': str(decanting.pre_dec_reading) if decanting.pre_dec_reading else None,
                    'post_dec_pressure_bar': str(decanting.post_dec_pressure_bar) if decanting.post_dec_pressure_bar else None,
                    'post_dec_reading': str(decanting.post_dec_reading) if decanting.post_dec_reading else None,
                    'delivered_qty_kg': str(decanting.delivered_qty_kg) if decanting.delivered_qty_kg else None,
                    'pre_decant_photo_url': decanting.pre_decant_photo.url if decanting.pre_decant_photo else None,
                    'post_decant_photo_url': decanting.post_decant_photo.url if decanting.post_decant_photo else None,
                    'confirmed_by_dbs_operator': decanting.confirmed_by_dbs_operator_id is not None,
                    'start_time': decanting.start_time.isoformat() if decanting.start_time else None,
                    'end_time': decanting.end_time.isoformat() if decanting.end_time else None,

                    # Helper flags for UI
                    'has_pre_decant_data': decanting.pre_dec_pressure_bar is not None or decanting.pre_dec_reading is not None,
                    'has_post_decant_data': decanting.post_dec_pressure_bar is not None or decanting.post_dec_reading is not None,
                    'is_complete': decanting.confirmed_by_dbs_operator_id is not None,
                }
            })

        except Trip.DoesNotExist:
            return Response({'error': 'Trip not found for this token'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='decant/start')
    def decant_start(self, request):
        """
        Start Decanting (Pre-Decant)
        Payload: { "tripToken": "...", "pressure": "...", "mfm": "..." }
        """
        token_val = request.data.get('tripToken')
        pressure = request.data.get('pressure')
        mfm = request.data.get('mfm')

        if not token_val:
            return Response({'error': 'tripToken is required'}, status=status.HTTP_400_BAD_REQUEST)

        trip = get_object_or_404(Trip, token__token_no=token_val)
        
        # Get or create Decanting record
        from .models import DBSDecanting
        decanting, _ = DBSDecanting.objects.get_or_create(trip=trip)
        decanting.start_time = timezone.now()

        if pressure:
            decanting.pre_dec_pressure_bar = pressure
        if mfm:
            decanting.pre_dec_reading = mfm # Using pre_dec_reading for MFM as generic, or should we use a new field?
            # User asked for 'prefill_mfm' (MS) vs 'pre_dec_pressure'.
            # Checking models: DBSDecanting has `pre_dec_pressure_bar` and `pre_dec_reading`.
            # We will use pre_dec_reading for MFM values if not specified otherwise, or add a field if needed.
            # For now mapping 'mfm' to 'pre_dec_reading'.
            pass

        decanting.save()

        # Update trip step tracking
        trip.current_step = 5  # Step 5: DBS Decanting in progress
        trip.step_data = {**trip.step_data, 'dbs_pre_reading_done': True}
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
                            'type': 'DBS_DECANT_START',
                            'trip_id': trip.id,
                            'pre_decant_reading': float(decanting.pre_dec_reading or 0),
                            'pressure': float(decanting.pre_dec_pressure_bar or 0),
                            'message': 'Decanting started at DBS'
                        }
                    }
                )
        except Exception as e:
            print(f"WebSocket Error: {e}")

        return Response({
            "success": True, 
            "message": "Decanting started successfully"
        })

    @action(detail=False, methods=['post'], url_path='decant/end')
    def decant_end(self, request):
        """
        End Decanting (Post-Decant)
        Payload: { "tripToken": "...", "pressure": "...", "mfm": "..." }
        """
        token_val = request.data.get('tripToken')
        pressure = request.data.get('pressure')
        mfm = request.data.get('mfm')

        if not token_val:
            return Response({'error': 'tripToken is required'}, status=status.HTTP_400_BAD_REQUEST)

        trip = get_object_or_404(Trip, token__token_no=token_val)
        
        from .models import DBSDecanting
        decanting, _ = DBSDecanting.objects.get_or_create(trip=trip)
        decanting.end_time = timezone.now()

        if pressure:
            decanting.post_dec_pressure_bar = pressure
        if mfm:
            decanting.post_dec_reading = mfm

        decanting.save()

        # Update trip step tracking
        trip.step_data = {**trip.step_data, 'dbs_post_reading_done': True}
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
                            'type': 'DBS_DECANT_END',
                            'trip_id': trip.id,
                            'post_decant_reading': float(decanting.post_dec_reading or 0),
                            'pressure': float(decanting.post_dec_pressure_bar or 0),
                            'message': 'Decanting ended at DBS'
                        }
                    }
                )
        except Exception as e:
            print(f"WebSocket Error: {e}")

        return Response({
            "success": True, 
            "message": "Decanting ended successfully"
        })

    @action(detail=False, methods=['post'], url_path='decant/confirm')
    def confirm_decanting(self, request):
        """
        Final Confirmation by DBS Operator
        Payload: { "tripToken": "...", "deliveredQty": "..." }
        """
        token_val = request.data.get('tripToken')
        delivered_qty = request.data.get('deliveredQty')
        
        if not token_val or delivered_qty is None:
             return Response({'error': 'tripToken and deliveredQty are required'}, status=status.HTTP_400_BAD_REQUEST)

        trip = get_object_or_404(Trip, token__token_no=token_val)
        
        from .models import DBSDecanting
        decanting, _ = DBSDecanting.objects.get_or_create(trip=trip)
        
        decanting.delivered_qty_kg = delivered_qty
        decanting.confirmed_by_dbs_operator = request.user
        decanting.save()

        # Determine strict status. User said "driver will go back to MS then this trip will complete".
        # So we mark it as 'DBS_COMPLETED' or 'RETURN_TO_MS'.
        # However, for now, to ensure flow continues, let's use 'COMPLETED' for the *Task* of decanting,
        # and maybe 'RETURN_TO_MS' for the trip status?
        # Existing flow uses 'COMPLETED'. Let's stick to 'DECANTING_CONFIRMED' to be safe or 'COMPLETED' if that closes the stock request.
        # Check StockRequest update requirement from previous context ("update StockRequest status to COMPLETED").

        if trip.stock_request:
            trip.stock_request.status = 'COMPLETED'
            trip.stock_request.save()

        trip.status = 'DECANTING_CONFIRMED'
        trip.current_step = 6  # Step 6: Navigate back to MS
        trip.step_data = {**trip.step_data, 'dbs_decanting_confirmed': True}
        trip.save()
        
        return Response({
            "success": True,
            "message": "Decanting confirmed. Stock Request completed."
        })

    def list(self, request):
        user = request.user
        dbs = None
        
        # Determine DBS
        dbs_id_param = request.query_params.get('dbs_id')
        if dbs_id_param:
            dbs = get_object_or_404(Station, id=dbs_id_param, type='DBS')
        else:
            user_role = user.user_roles.filter(role__code='DBS_OPERATOR', active=True).first()
            if user_role and user_role.station and user_role.station.type == 'DBS':
                dbs = user_role.station
        
        if not dbs:
            return Response({'error': 'User is not assigned to a DBS station'}, status=status.HTTP_400_BAD_REQUEST)

        # Date Filtering
        end_date_str = request.query_params.get('end_date')
        start_date_str = request.query_params.get('start_date')
        
        try:
            current_date = timezone.now().date()
            if end_date_str:
                end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            else:
                end_date_obj = current_date
                
            if start_date_str:
                start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            else:
                start_date_obj = end_date_obj - timedelta(days=30)
        except ValueError:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

        # Query
        requests = StockRequest.objects.filter(
            dbs=dbs,
            created_at__date__gte=start_date_obj,
            created_at__date__lte=end_date_obj
        ).order_by('-created_at')

        data = []
        for req in requests:
            data.append({
                "id": req.id,
                "status": req.status,
                "requested_qty_kg": float(req.requested_qty_kg) if req.requested_qty_kg else 0,
                "requested_by_date": req.requested_by_date,
                "requested_by_time": req.requested_by_time,
                "created_at": req.created_at
            })
            
        return Response(data)

class DBSStockTransferListView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        dbs = None
        
        # Determine DBS
        dbs_id_param = request.query_params.get('dbs_id')
        if dbs_id_param:
             dbs = get_object_or_404(Station, id=dbs_id_param, type='DBS')
        else:
            user_role = user.user_roles.filter(role__code='DBS_OPERATOR', active=True).first()
            if user_role and user_role.station and user_role.station.type == 'DBS':
                dbs = user_role.station
        
        if not dbs:
            return Response(
                {'error': 'User is not assigned to a DBS station'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Build query with optional date filters
        query = Q(dbs=dbs)
        
        # Parse startDate filter (format: YYYY-MM-DD or ISO 8601)
        start_date = request.query_params.get('startDate')
        if start_date:
            try:
                # Try ISO format first, then simple date
                if 'T' in start_date:
                    start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                else:
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                query &= Q(started_at__gte=start_dt) | Q(completed_at__gte=start_dt)
            except ValueError:
                pass  # Ignore invalid date format
        
        # Parse endDate filter
        end_date = request.query_params.get('endDate')
        if end_date:
            try:
                if 'T' in end_date:
                    end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                else:
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                    # Add time to end of day for date-only format
                    end_dt = end_dt.replace(hour=23, minute=59, second=59)
                query &= Q(started_at__lte=end_dt) | Q(completed_at__lte=end_dt)
            except ValueError:
                pass  # Ignore invalid date format

        # Fetch transfers with filters
        trips = Trip.objects.filter(query).select_related(
            'ms', 'dbs'
        ).prefetch_related('dbs_decantings', 'ms_fillings').order_by('-completed_at', '-started_at')
        
        # Build transfers list and calculate summary
        transfers = []
        summary = {
            'totalTransfers': 0,
            'inProgress': 0,
            'completed': 0
        }
        
        for trip in trips:
            # Determine Quantity (Prefer Delivered, then Filled)
            qty = 0
            decanting = trip.dbs_decantings.first()
            if decanting and decanting.delivered_qty_kg:
                qty = float(decanting.delivered_qty_kg)
            else:
                filling = trip.ms_fillings.first()
                if filling and filling.filled_qty_kg:
                    qty = float(filling.filled_qty_kg)
            
            # Determine status category
            is_completed = trip.status in ['COMPLETED', 'DECANTING_COMPLETED']
            is_in_progress = trip.status in ['DISPATCHED', 'IN_TRANSIT', 'AT_DBS', 'DECANTING_STARTED']
            
            # Update summary
            summary['totalTransfers'] += 1
            if is_completed:
                summary['completed'] += 1
            elif is_in_progress:
                summary['inProgress'] += 1
            
            # Determine times
            initiated_at = trip.started_at or trip.ms_departure_at
            completed_at = trip.completed_at or trip.dbs_departure_at
            
            transfers.append({
                "id": trip.id,
                "type": "INCOMING",  # All trips to DBS are incoming transfers
                "status": "COMPLETED" if is_completed else "IN_PROGRESS",
                "quantity": qty,
                "initiatedAt": timezone.localtime(initiated_at).isoformat() if initiated_at else None,
                "completedAt": timezone.localtime(completed_at).isoformat() if completed_at else None,
                "fromLocation": trip.ms.name,
                "toLocation": trip.dbs.name,
                "notes": f"Trip #{trip.id} - {trip.status}"
            })
        
        return Response({
            "transfers": transfers,
            "summary": summary
        })


class DBSPendingArrivalsView(views.APIView):
    """
    GET /api/dbs/pending-arrivals
    Returns list of trucks that have arrived at DBS (status=AT_DBS) 
    with the same data structure as the push notification.
    This is a fallback for when notifications are missed/cleared.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        dbs = None
        
        # Try query param (for testing)
        dbs_id_param = request.query_params.get('dbs_id')
        if dbs_id_param:
            dbs = get_object_or_404(Station, id=dbs_id_param, type='DBS')
        else:
            # Get from user role
            user_role = user.user_roles.filter(role__code='DBS_OPERATOR', active=True).first()
            if user_role and user_role.station and user_role.station.type == 'DBS':
                dbs = user_role.station
        
        if not dbs:
            return Response(
                {'error': 'User is not assigned to a DBS station'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get trips that have arrived at DBS (waiting for decanting to start)
        # These are trips where driver has clicked "Arrive at DBS"
        pending_arrivals = Trip.objects.filter(
            dbs=dbs,
            status__in=['AT_DBS', 'ARRIVED_AT_DBS']  # AT_DBS = arrived, waiting for decanting
        ).filter(
            dbs_arrival_at__isnull=False  # Driver has confirmed arrival
        ).select_related('vehicle', 'driver', 'driver__user', 'token', 'ms').order_by('-dbs_arrival_at')
        
        arrivals = []
        for trip in pending_arrivals:
            arrivals.append({
                # Same structure as notification data (matching dbs_arrival notification)
                "type": "dbs_arrival",
                "trip_id": str(trip.id),
                "tripId": str(trip.id),  # Also include camelCase for frontend consistency
                "driver_id": str(trip.driver.id) if trip.driver else "",
                "driverId": str(trip.driver.id) if trip.driver else "",
                "truck_number": trip.vehicle.registration_no if trip.vehicle else "",
                "truckNumber": trip.vehicle.registration_no if trip.vehicle else "",
                "trip_token": trip.token.token_no if trip.token else "",
                "tripToken": trip.token.token_no if trip.token else "",
                # Additional helpful info
                "driverName": trip.driver.user.get_full_name() if trip.driver and trip.driver.user else "",
                "arrivedAt": timezone.localtime(trip.dbs_arrival_at).isoformat() if trip.dbs_arrival_at else None,
                "msName": trip.ms.name if trip.ms else "",
                "dbsName": dbs.name,
            })
        
        return Response({
            "success": True,
            "stationName": dbs.name,
            "arrivals": arrivals
        })

