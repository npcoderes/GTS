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
import os

class DBSDashboardView(views.APIView):
    """
    API Path: GET /api/dbs/dashboard/
    DBS dashboard with station info, summary counts, and pending arrivals.
    """
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
        # Valid statuses: PENDING, AT_MS, IN_TRANSIT, AT_DBS, DECANTING_CONFIRMED, RETURNED_TO_MS, COMPLETED, CANCELLED
        # Invalid (not in model): DISPATCHED, ARRIVED_AT_DBS, DECANTING_STARTED, DECANTING_COMPLETED
        relevant_statuses = [
            'IN_TRANSIT', 'AT_DBS',  # 'DISPATCHED', 'ARRIVED_AT_DBS' - not in model
            'DECANTING_CONFIRMED',  # 'DECANTING_STARTED', 'DECANTING_COMPLETED' - not in model
            'COMPLETED'
        ]
        trips = Trip.objects.filter(dbs=dbs, status__in=relevant_statuses).select_related(
            'ms', 'dbs', 'vehicle'
        ).prefetch_related('ms_fillings', 'dbs_decantings').order_by('-started_at')
        
        # Calculate Summary Stats
        summary = {
            'pending': 0,    # Dispatched / In Transit / Arrived
            'inProgress': 0, # Decanting
            'completed': 0   # Completed
        }
        
        trip_list = []
        
        for trip in trips:
            # Map Backend Status to Frontend Categories
            # Valid statuses only
            category = 'pending' # Default
            if trip.status in ['IN_TRANSIT', 'AT_DBS']:  # 'DISPATCHED', 'ARRIVED_AT_DBS' - not in model
                category = 'pending'
                summary['pending'] += 1
            elif trip.status == 'DECANTING_CONFIRMED':  # 'DECANTING_STARTED' - not in model
                category = 'inProgress'
                summary['inProgress'] += 1
            elif trip.status in ['COMPLETED']:  # 'DECANTING_COMPLETED' - not in model
                category = 'completed'
                summary['completed'] += 1
            
            # Smart Quantity Display based on Trip Progress
            # 1. If DBS decanting done → use DBS delivered quantity
            # 2. Else if MS filling done → use MS filled quantity  
            # 3. Else (trip just started/pending) → show "Not Available"
            decanting = trip.dbs_decantings.first()
            filling = trip.ms_fillings.first()
            
            if decanting and decanting.delivered_qty_kg:
                # DBS decanting completed - use actual delivered quantity
                quantity = float(decanting.delivered_qty_kg)
            elif filling and filling.filled_qty_kg:
                # MS filling completed - use filled quantity
                quantity = float(filling.filled_qty_kg)
            else:
                # Trip just started or in early stages - quantity not yet known
                quantity = "Not Available"

            # Format Trip Data
            trip_data = {
                "id": f"{trip.id}", # Format ID
                "status": 'AT_DBS' if trip.status == 'DECANTING_CONFIRMED' else trip.status,
                "route": f"from {trip.ms.name} to {trip.dbs.name}",
                "msName": trip.ms.name,
                "dbsName": trip.dbs.name,
                "scheduledTime": timezone.localtime(trip.started_at).isoformat() if trip.started_at else None, # Using started_at as proxy for scheduled
                "completedTime": timezone.localtime(trip.completed_at).isoformat() if trip.completed_at else None,
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
    """
    API Path: /api/dbs/stock-requests/
    DBS Stock Request management ViewSet.
    
    Actions:
      - GET /api/dbs/stock-requests - List stock requests for DBS
      - POST /api/dbs/stock-requests/arrival/confirm - Confirm truck arrival
      - POST /api/dbs/stock-requests/decant/start - Start decanting with pre-readings
      - POST /api/dbs/stock-requests/decant/end - End decanting with post-readings
      - POST /api/dbs/stock-requests/decant/confirm - Confirm decanting completion
    """
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
        
        # Mark DBS operator confirmation
        trip.dbs_arrival_confirmed = True
        trip.dbs_arrival_confirmed_at = timezone.now()
        trip.save()

        return Response({
            "success": True,
            "trip": {
                "id": f"{trip.id}",
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
        trip_id = request.data.get('tripId')
        user = request.user

        try:
            # Try to find trip by token first, then by tripId, then by DBS station
            if token_val:
                trip = Trip.objects.select_related(
                    'token', 'vehicle', 'driver', 'ms', 'dbs'
                ).prefetch_related('dbs_decantings').get(token__token_no=token_val)
            elif trip_id:
                trip = Trip.objects.select_related(
                    'token', 'vehicle', 'driver', 'ms', 'dbs'
                ).prefetch_related('dbs_decantings').get(id=trip_id)
            else:
                # Auto-find trip by DBS station where dbs_arrival_confirmed is True
                # Get user's DBS station
                dbs = None
                user_role = user.user_roles.filter(role__code='DBS_OPERATOR', active=True).first()
                if user_role and user_role.station and user_role.station.type == 'DBS':
                    dbs = user_role.station
                
                if not dbs:
                    return Response({'error': 'User is not assigned to a DBS station'}, status=status.HTTP_400_BAD_REQUEST)
                
                # Find trip at this DBS that is confirmed and in progress
                # Valid statuses: PENDING, AT_MS, IN_TRANSIT, AT_DBS, DECANTING_CONFIRMED, RETURNED_TO_MS, COMPLETED, CANCELLED
                # Invalid (not in model): DECANTING_STARTED, DECANTING_COMPLETE
                trip = Trip.objects.select_related(
                    'token', 'vehicle', 'driver', 'ms', 'dbs'
                ).prefetch_related('dbs_decantings').filter(
                    dbs=dbs,
                    status__in=['AT_DBS']  # 'DECANTING_STARTED', 'DECANTING_COMPLETE' - not in model STATUS_CHOICES
                ).first()
                
                if not trip:
                    return Response({
                        'hasDecantingData': False,
                        'tripToken': None,
                        'vehicleNumber': None,
                        'dbs_arrival_confirmed': False,
                        'message': 'No confirmed trip found at this DBS'
                    })
            
            # Get token value for response
            actual_token = trip.token.token_no if trip.token else token_val
            vehicle_number = trip.vehicle.registration_no if trip.vehicle else None

            # Get DBSDecanting record if exists
            from .models import DBSDecanting
            decanting = trip.dbs_decantings.first()

            if not decanting:
                # No decanting record yet, return empty state
                return Response({
                    'hasDecantingData': False,
                    'tripToken': actual_token,
                    'vehicleNumber': vehicle_number,
                    'dbs_arrival_confirmed': trip.dbs_arrival_confirmed,
                    # 'trip': {
                    #     'id': trip.id,
                    #     'status': trip.status,
                    #     'currentStep': trip.current_step,
                    #     'vehicle': {
                    #         'registrationNo': trip.vehicle.registration_no if trip.vehicle else None,
                    #         'capacity_kg': str(trip.vehicle.capacity_kg) if trip.vehicle else None,
                    #     },
                    #     'driver': {
                    #         'name': trip.driver.full_name if trip.driver else None,
                    #     },
                    #     'route': {
                    #         'from': trip.ms.name if trip.ms else None,
                    #         'to': trip.dbs.name if trip.dbs else None,
                    #     }
                    # }
                })
            base_url = os.getenv('BASE_URL', 'http://localhost:8000')

            if decanting.confirmed_by_dbs_operator_id:
                return Response({
                        'hasDecantingData': False,
                        'tripToken': None,
                        'vehicleNumber': None,
                        'dbs_arrival_confirmed': False,
                        'message': 'No confirmed trip found at this DBS'
                    })

            # Return existing decanting data
            return Response({
                'hasDecantingData': True,
                'tripToken': actual_token,
                'vehicleNumber': vehicle_number,
                'dbs_arrival_confirmed': trip.dbs_arrival_confirmed,
                'decantingData': {
                    'id': decanting.id,
                    'trip_id': trip.id,
                    'pre_dec_pressure_bar': str(decanting.pre_dec_pressure_bar) if decanting.pre_dec_pressure_bar else None,
                    'pre_dec_reading': str(decanting.pre_dec_reading) if decanting.pre_dec_reading else None,
                    'post_dec_pressure_bar': str(decanting.post_dec_pressure_bar) if decanting.post_dec_pressure_bar else None,
                    'post_dec_reading': str(decanting.post_dec_reading) if decanting.post_dec_reading else None,
                    'delivered_qty_kg': str(decanting.delivered_qty_kg) if decanting.delivered_qty_kg else None,
                    'pre_decant_photo_url': True if decanting.pre_decant_photo_operator else False,
                    'post_decant_photo_url': True if decanting.post_decant_photo_operator else False,
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
        Payload: { "tripToken": "...", "pressure": "...", "mfm": "...", "photoBase64": "base64..." }
        """
        token_val = request.data.get('tripToken')
        pressure = request.data.get('pressure')
        mfm = request.data.get('mfm')
        photo_base64 = request.data.get('photoBase64')

        if not token_val:
            return Response({'error': 'tripToken is required'}, status=status.HTTP_400_BAD_REQUEST)

        trip = get_object_or_404(Trip, token__token_no=token_val)
        
        # Handle photo upload
        photo_file = None
        if photo_base64:
            try:
                import base64
                from django.core.files.base import ContentFile
                import uuid
                
                if ';base64,' in photo_base64:
                    format, imgstr = photo_base64.split(';base64,')
                    ext = format.split('/')[-1] if '/' in format else 'jpg'
                else:
                    imgstr = photo_base64
                    ext = 'jpg'
                
                file_name = f"dbs_pre_decant_{trip.id}_{uuid.uuid4().hex[:6]}.{ext}"
                photo_file = ContentFile(base64.b64decode(imgstr), name=file_name)
            except Exception as e:
                print(f"Error decoding pre_decant photo: {e}")
        
        # Get or create Decanting record
        from .models import DBSDecanting
        decanting, _ = DBSDecanting.objects.get_or_create(trip=trip)
        decanting.start_time = timezone.now()

        if pressure:
            decanting.pre_dec_pressure_bar = pressure
        if mfm:
            decanting.pre_dec_reading = mfm
        if photo_file:
            decanting.pre_decant_photo_operator = photo_file

        decanting.save()

        # Update trip step tracking
        if trip.update_step(5):
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
        Payload: { "tripToken": "...", "pressure": "...", "mfm": "...", "photoBase64": "base64..." }
        """
        token_val = request.data.get('tripToken')
        pressure = request.data.get('pressure')
        mfm = request.data.get('mfm')
        photo_base64 = request.data.get('photoBase64')

        if not token_val:
            return Response({'error': 'tripToken is required'}, status=status.HTTP_400_BAD_REQUEST)

        trip = get_object_or_404(Trip, token__token_no=token_val)
        
        # Handle photo upload
        photo_file = None
        if photo_base64:
            try:
                import base64
                from django.core.files.base import ContentFile
                import uuid
                
                if ';base64,' in photo_base64:
                    format, imgstr = photo_base64.split(';base64,')
                    ext = format.split('/')[-1] if '/' in format else 'jpg'
                else:
                    imgstr = photo_base64
                    ext = 'jpg'
                
                file_name = f"dbs_post_decant_{trip.id}_{uuid.uuid4().hex[:6]}.{ext}"
                photo_file = ContentFile(base64.b64decode(imgstr), name=file_name)
            except Exception as e:
                print(f"Error decoding post_decant photo: {e}")
        
        from .models import DBSDecanting
        decanting, _ = DBSDecanting.objects.get_or_create(trip=trip)
        decanting.end_time = timezone.now()

        if pressure:
            decanting.post_dec_pressure_bar = pressure
        if mfm:
            decanting.post_dec_reading = mfm
        if photo_file:
            decanting.post_decant_photo_operator = photo_file

        delivered_qty = None
        if decanting.pre_dec_reading and decanting.post_dec_reading:
            try:
                delivered_qty = float(decanting.post_dec_reading) - float(decanting.pre_dec_reading)
                decanting.delivered_qty_kg = delivered_qty
            except ValueError:
                pass  # Invalid readings, cannot calculate
        decanting.save()

        # Update trip step tracking - stay at step 5 until both parties confirm
        if trip.current_step >= 5:
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
        
        if not token_val:
             return Response({'error': 'tripToken is required'}, status=status.HTTP_400_BAD_REQUEST)

        trip = get_object_or_404(Trip, token__token_no=token_val)
        
        from .models import DBSDecanting
        decanting, _ = DBSDecanting.objects.get_or_create(trip=trip)
        
        # Validate: post_dec_reading - pre_dec_reading should match delivered_qty_kg
        if decanting.pre_dec_reading and decanting.post_dec_reading and decanting.delivered_qty_kg:
            calculated_qty = float(decanting.post_dec_reading) - float(decanting.pre_dec_reading)
            if abs(calculated_qty - float(decanting.delivered_qty_kg)) > 0.01:
                return Response({
                    'error': 'Quantity mismatch',
                    'message': f'Calculated quantity ({calculated_qty} kg) does not match delivered quantity ({decanting.delivered_qty_kg} kg)'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        decanting.confirmed_by_dbs_operator = request.user
        decanting.save()

        # Mark operator confirmed in step_data  
        # Stay at step 5 until driver also confirms
        if trip.current_step >= 5:
            trip.step_data = {**trip.step_data, 'dbs_operator_confirmed': True}
        trip.save()
        
        return Response({
            "success": True,
            "message": "Decanting confirmed by operator. Waiting for driver confirmation."
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
                "requested_by_date": req.requested_by_date,
                "requested_by_time": req.requested_by_time,
                "created_at": req.created_at
            })
            
        return Response(data)

class DBSStockTransferListView(views.APIView):
    """
    API Path: GET /api/dbs/transfers
    List stock transfers for DBS.
    """
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
            is_in_progress = trip.status in ['DISPATCHED', 'IN_TRANSIT', 'AT_DBS']
            
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
    API Path: GET /api/dbs/pending-arrivals
    Get pending vehicle arrivals at DBS.
    """
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
        # Exclude trips where DBS operator has already confirmed
        # Valid statuses: PENDING, AT_MS, IN_TRANSIT, AT_DBS, DECANTING_CONFIRMED, RETURNED_TO_MS, COMPLETED, CANCELLED
        # Invalid (not in model): ARRIVED_AT_DBS
        pending_arrivals = Trip.objects.filter(
            dbs=dbs,
            status__in=['AT_DBS'],  # 'ARRIVED_AT_DBS' - not in model STATUS_CHOICES
            dbs_arrival_confirmed=False  # Only show unconfirmed arrivals
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

