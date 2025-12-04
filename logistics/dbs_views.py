from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q
from datetime import datetime
from .models import Trip, StockRequest
from core.models import Station

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
            'DECANTING_STARTED', 'DECANTING_COMPLETED', 
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
                "scheduledTime": trip.started_at.isoformat() if trip.started_at else None, # Using started_at as proxy for scheduled
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
                "initiatedAt": initiated_at.isoformat() if initiated_at else None,
                "completedAt": completed_at.isoformat() if completed_at else None,
                "fromLocation": trip.ms.name,
                "toLocation": trip.dbs.name,
                "notes": f"Trip #{trip.id} - {trip.status}"
            })
        
        return Response({
            "transfers": transfers,
            "summary": summary
        })

