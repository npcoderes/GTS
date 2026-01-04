from decimal import Decimal

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import Station
from core.error_response import (
    validation_error_response, forbidden_response
)
from .models import Trip


def _get_user_dbs_station(request):
    """Resolve the DBS station from the authenticated user's active roles.

    Optional support for `dbs_id` query/body is kept for testing, but the
    primary source is the user's assigned DBS station from active roles.
    """
    # Explicit override for testing/admin tools
    dbs_id_param = request.query_params.get('dbs_id') or request.data.get('dbs_id')
    if dbs_id_param:
        return get_object_or_404(Station, id=dbs_id_param, type=Station.StationType.DBS)

    # Prefer a DBS_OPERATOR or SGL_CUSTOMER role assignment
    role_qs = request.user.user_roles.filter(active=True).select_related('role', 'station')

    # Try explicit DBS roles with a station of type DBS
    preferred = role_qs.filter(
        role__code__in=['DBS_OPERATOR', 'SGL_CUSTOMER'],
        station__type=Station.StationType.DBS,
        station__isnull=False,
    ).first()
    if preferred and preferred.station:
        return preferred.station

    # Fallback: any active role that has a DBS station
    any_dbs = role_qs.filter(station__type=Station.StationType.DBS, station__isnull=False).first()
    if any_dbs and any_dbs.station:
        return any_dbs.station

    # Last resort: any active role with a station (type not enforced)
    any_station = role_qs.filter(station__isnull=False).first()
    if any_station and any_station.station:
        return any_station.station

    # No DBS found for user
    return None


class CustomerDashboardView(views.APIView):
    """API Path: /api/customer/dashboard"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dbs = _get_user_dbs_station(request)
        if not dbs:
            return validation_error_response('DBS not found for user')

        relevant_statuses = [
            'DISPATCHED', 'IN_TRANSIT', 'ARRIVED_AT_DBS', 'AT_DBS',
            'DECANTING_STARTED', 'DECANTING_COMPLETED', 'DECANTING_CONFIRMED',
            'COMPLETED'
        ]

        trips = Trip.objects.filter(dbs=dbs, status__in=relevant_statuses).select_related(
            'ms', 'dbs', 'vehicle'
        ).prefetch_related('ms_fillings', 'dbs_decantings')

        summary = {
            'pending': 0,
            'inProgress': 0,
            'completed': 0
        }

        trip_list = []

        for trip in trips:
            category = 'pending'
            if trip.status in ['DISPATCHED', 'IN_TRANSIT', 'ARRIVED_AT_DBS', 'AT_DBS']:
                summary['pending'] += 1
            elif trip.status == 'DECANTING_STARTED':
                category = 'inProgress'
                summary['inProgress'] += 1
            elif trip.status in ['COMPLETED', 'DECANTING_COMPLETED']:
                category = 'completed'
                summary['completed'] += 1

            decanting = trip.dbs_decantings.first()
            filling = trip.ms_fillings.first()

            if decanting and decanting.delivered_qty_kg:
                quantity = float(decanting.delivered_qty_kg)
            elif filling and filling.filled_qty_kg:
                quantity = float(filling.filled_qty_kg)
            else:
                quantity = "Not Available"

            trip_list.append({
                "id": f"{trip.id}",
                "status": 'AT_DBS' if trip.status == 'DECANTING_CONFIRMED' else trip.status,
                "route": f"from {trip.ms.name} to {trip.dbs.name}",
                "msName": trip.ms.name,
                "dbsName": trip.dbs.name,
                "scheduledTime": timezone.localtime(trip.started_at).isoformat() if trip.started_at else None,
                "completedTime": timezone.localtime(trip.completed_at).isoformat() if trip.completed_at else None,
                "quantity": quantity,
                "vehicleNo": trip.vehicle.registration_no if trip.vehicle else None
            })

        response_data = {
            "station": {
                "dbsName": dbs.name,
                "location": dbs.city or dbs.address or "Unknown Location"
            },
            "summary": summary,
            "trips": trip_list
        }

        return Response(response_data)


class CustomerStocksView(views.APIView):
    """API Path: /api/customer/stocks"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dbs = _get_user_dbs_station(request)
        if not dbs:
            return validation_error_response('DBS not found for user')
        capacity = dbs.capacity_kg or 0
        current_stock = dbs.current_stock_kg or 0
        percentage = float(current_stock) / float(capacity) * 100 if capacity else 0
        percentage = max(0, min(percentage, 100))

        stock_item = {
            'id': dbs.code,
            'productName': 'LPG',
            'productType': 'DBS Storage',
            'currentStock': float(current_stock),
            'capacity': float(capacity),
            'percentage': round(percentage, 2),
            'lastUpdated': timezone.localtime(dbs.stock_updated_at).isoformat() if dbs.stock_updated_at else None,
        }

        summary = {
            'totalStock': float(current_stock),
        }

        return Response({'stocks': [stock_item], 'summary': summary})

    def post(self, request):
        dbs = _get_user_dbs_station(request)
        if not dbs:
            return validation_error_response('DBS not found for user')
        current_stock = request.data.get('currentStock')
        capacity = request.data.get('capacity')

        updated = False
        if current_stock is not None:
            try:
                dbs.current_stock_kg = Decimal(str(current_stock))
                updated = True
            except Exception:
                return validation_error_response('Invalid currentStock value')

        if capacity is not None:
            try:
                dbs.capacity_kg = Decimal(str(capacity))
                updated = True
            except Exception:
                return validation_error_response('Invalid capacity value')

        if updated:
            dbs.stock_updated_at = timezone.now()
            dbs.save(update_fields=['current_stock_kg', 'capacity_kg', 'stock_updated_at'])

        return self.get(request)


class CustomerTransportView(views.APIView):
    """API Path: /api/customer/transport"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dbs = _get_user_dbs_station(request)
        if not dbs:
            return validation_error_response('DBS not found for user')
        trips = Trip.objects.select_related('ms', 'dbs', 'vehicle', 'driver').filter(dbs=dbs).exclude(status__in=['COMPLETED', 'CANCELLED']).order_by('-created_at')[:30]

        transports = []
        for trip in trips:
            status_value = 'FILLING' if trip.status in ['PENDING', 'AT_MS'] else 'ACTIVE'
            transports.append({
                'id': f'{trip.id}',
                'vehicleNumber': trip.vehicle.registration_no if trip.vehicle else 'NA',
                'driverName': trip.driver.full_name if trip.driver else 'Unassigned',
                'status': status_value,
                'origin': trip.ms.name if trip.ms else '',
                'destination': trip.dbs.name if trip.dbs else '',
                'departureTime': timezone.localtime(trip.ms_departure_at or trip.started_at or trip.created_at).isoformat() if (trip.ms_departure_at or trip.started_at or trip.created_at) else None,
                'estimatedArrival': timezone.localtime(trip.dbs_arrival_at).isoformat() if trip.dbs_arrival_at else None,
            })

        summary = {
            'active': sum(1 for t in transports if (t['status'] or '').upper() != 'FILLING'),
            'filling': sum(1 for t in transports if (t['status'] or '').upper() == 'FILLING'),
        }

        return Response({'transports': transports, 'summary': summary})


class CustomerTransfersView(views.APIView):  
    """
    API Path: /api/customer/transfers
    
    Returns stock request transfers for the authenticated customer's DBS.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .models import StockRequest
        from datetime import timedelta
        from django.utils.dateparse import parse_datetime
        
        dbs = _get_user_dbs_station(request)
        if not dbs:
            return validation_error_response('DBS not found for user')
        
        # Parse date filters from query params
        start_date_str = request.query_params.get('startDate')
        end_date_str = request.query_params.get('endDate')
        
        if start_date_str:
            start_date = parse_datetime(start_date_str)
        else:
            # Default: 1 month ago
            start_date = timezone.now() - timedelta(days=30)
        
        if end_date_str:
            end_date = parse_datetime(end_date_str)
        else:
            end_date = timezone.now()
        
        # Get stock requests for this DBS within date range
        stock_requests = StockRequest.objects.select_related(
            'dbs', 'dbs__parent_station'
        ).filter(
            dbs=dbs,
            created_at__gte=start_date,
            created_at__lte=end_date
        ).order_by('-created_at')
        
        transfers = []
        for sr in stock_requests:
            # Get completed_at from associated trip if exists
            completed_at = None
            trip = getattr(sr, 'trip', None)
            if trip and trip.completed_at:
                completed_at = timezone.localtime(trip.completed_at).isoformat()
            
            # fromLocation = MS (parent of DBS)
            ms_name = sr.dbs.parent_station.name if sr.dbs and sr.dbs.parent_station else 'Unknown MS'
            # toLocation = DBS
            dbs_name = sr.dbs.name if sr.dbs else 'Unknown DBS'
            
            transfers.append({
                'id': sr.id,
                'fromLocation': ms_name,
                'toLocation': dbs_name,
                'status': sr.status,
                'quantity': float(sr.requested_qty_kg) if sr.requested_qty_kg else 0,
                'initiatedAt': timezone.localtime(sr.created_at).isoformat() if sr.created_at else None,
                'completedAt': completed_at,
                'estimatedCompletion': None,  # No field for this currently
                'notes': sr.approval_notes or None,
            })
        
        return Response({'transfers': transfers})


class CustomerPendingTripsView(views.APIView):
    """API Path: /api/customer/pending-trips"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dbs = _get_user_dbs_station(request)
        if not dbs:
            return validation_error_response('DBS not found for user')
        trips = Trip.objects.select_related('ms', 'dbs', 'vehicle').filter(dbs=dbs, status__in=['PENDING', 'AT_MS']).order_by('created_at')

        payload = []
        for trip in trips:
            stock_req = getattr(trip, 'stock_request', None)
            priority_raw = getattr(stock_req, 'priority_preview', None)
            priority = {
                'H': 'HIGH',
                'C': 'CRITICAL',
                'N': 'NORMAL',
                'FDODO': 'FDODO',
            }.get(priority_raw, 'MEDIUM')

            payload.append({
                'id': f'{trip.id}',
                'route': f"from {trip.ms.name if trip.ms else 'MS'} to {trip.dbs.name if trip.dbs else 'DBS'}",
                'scheduledTime': timezone.localtime(trip.started_at or trip.created_at).isoformat() if (trip.started_at or trip.created_at) else None,
                'vehicleNumber': trip.vehicle.registration_no if trip.vehicle else 'NA',
                'priority': priority,
            })

        return Response({'trips': payload})


class CustomerTripAcceptView(views.APIView):
    """API Path: /api/customer/trips/<int:trip_id>/accept"""
    permission_classes = [IsAuthenticated]

    def post(self, request, trip_id):
        dbs = _get_user_dbs_station(request)
        if not dbs:
            return validation_error_response('DBS not found for user')

        trip = get_object_or_404(Trip, id=trip_id)
        if trip.dbs and trip.dbs != dbs:
            return forbidden_response('Trip does not belong to your DBS')

        trip.status = trip.status or 'IN_TRANSIT'
        if trip.status == 'PENDING':
            trip.status = 'IN_TRANSIT'
        if not trip.origin_confirmed_at:
            trip.origin_confirmed_at = timezone.now()
        trip.save(update_fields=['status', 'origin_confirmed_at'])
        return Response({'status': 'accepted', 'tripId': trip.id})


class CustomerPermissionsView(views.APIView):
    """API Path: /api/customer/permissions"""
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id=None):
        return Response({'canAcceptTrips': True})
