from rest_framework import views, viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from django.utils import timezone
from .models import Trip, Vehicle, Token
from core.models import Station
from .serializers import TripSerializer


class EICVehicleQueueView(views.APIView):
    """Get vehicle queue at MS stations"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get MS ID from query params (optional)
        ms_id = request.query_params.get('ms_id')
        
        # Build query for trips at MS
        query = Q(status__in=['PENDING', 'AT_MS', 'FILLING'])
        if ms_id:
            query &= Q(ms_id=ms_id)
        
        # Get trips grouped by MS
        trips = Trip.objects.filter(query).select_related(
            'ms', 'vehicle', 'driver', 'driver__user', 'token'
        ).order_by('ms__name', 'token__token_no', 'started_at')
        
        # Group by MS
        queue_by_ms = {}
        for trip in trips:
            ms_name = trip.ms.name
            if ms_name not in queue_by_ms:
                queue_by_ms[ms_name] = {
                    'msId': trip.ms.id,
                    'msName': ms_name,
                    'totalVehicles': 0,
                    'queue': []
                }
            
            queue_by_ms[ms_name]['totalVehicles'] += 1
            queue_by_ms[ms_name]['queue'].append({
                'tripId': trip.id,
                'tokenNumber': trip.token.token_no if trip.token else None,
                'vehicleNo': trip.vehicle.registration_no,
                'driverName': trip.driver.user.full_name if trip.driver else 'Unassigned',
                'destination': trip.dbs.name,
                'status': trip.status,
                'arrivalTime': timezone.localtime(trip.origin_confirmed_at).isoformat() if trip.origin_confirmed_at else None,
                'position': queue_by_ms[ms_name]['totalVehicles']
            })
        
        # Convert to list
        result = list(queue_by_ms.values())
        
        return Response(result)


class EICClusterViewSet(viewsets.ModelViewSet):
    """Cluster management for EIC"""
    permission_classes = [IsAuthenticated]
    serializer_class = TripSerializer  # Placeholder, will need ClusterSerializer
    
    def get_queryset(self):
        # For now, return MS stations as "clusters"
        # In a real system, you'd have a Cluster model
        return Station.objects.filter(type='MS')
    
    def list(self, request):
        """Get list of clusters (MS stations with their assigned DBS)"""
        from core.models import MSDBSMap, UserRole
        
        # Get MS stations that EIC user is assigned to
        eic_assigned_ms_ids = UserRole.objects.filter(
            user=request.user,
            role__code='EIC',
            active=True,
            station__type='MS'
        ).values_list('station_id', flat=True)
        
        # Check if user is super admin
        is_super_admin = request.user.user_roles.filter(
            role__code='SUPER_ADMIN',
            active=True
        ).exists()
        
        # Only return MS stations assigned to this EIC user (or all for super admin)
        if is_super_admin:
            ms_stations = Station.objects.filter(type='MS').prefetch_related('dbs_mappings', 'daughter_stations')
        elif eic_assigned_ms_ids:
            ms_stations = Station.objects.filter(
                type='MS',
                id__in=eic_assigned_ms_ids
            ).prefetch_related('dbs_mappings', 'daughter_stations')
        else:
            # No assigned stations
            return Response({
                'clusters': [],
                'unassignedDBS': []
            })
        
        # Get all DBS stations
        all_dbs = Station.objects.filter(type='DBS')
        
        # Get DBS IDs that are already assigned to any MS (via MSDBSMap)
        assigned_dbs_ids = set(MSDBSMap.objects.filter(active=True).values_list('dbs_id', flat=True))
        
        # Also get DBS with parent_station set
        dbs_with_parent = Station.objects.filter(type='DBS', parent_station__isnull=False).values_list('id', flat=True)
        assigned_dbs_ids.update(dbs_with_parent)
        
        # Get unassigned DBS (not in MSDBSMap AND no parent_station)
        unassigned_dbs = all_dbs.exclude(id__in=assigned_dbs_ids)
        
        clusters = []
        for ms in ms_stations:
            # Get mapped DBS stations from BOTH sources
            dbs_list = []
            seen_dbs_ids = set()
            
            # 1. From MSDBSMap
            for mapping in ms.dbs_mappings.filter(active=True):
                if mapping.dbs.id not in seen_dbs_ids:
                    seen_dbs_ids.add(mapping.dbs.id)
                    dbs_list.append({
                        'dbsId': mapping.dbs.id,
                        'dbsName': mapping.dbs.name,
                        'dbsCode': mapping.dbs.code,
                        'city': mapping.dbs.city
                    })
            
            # 2. From parent_station (daughter_stations)
            for dbs in ms.daughter_stations.filter(type='DBS'):
                if dbs.id not in seen_dbs_ids:
                    seen_dbs_ids.add(dbs.id)
                    dbs_list.append({
                        'dbsId': dbs.id,
                        'dbsName': dbs.name,
                        'dbsCode': dbs.code,
                        'city': dbs.city
                    })
            
            # Get active trips count
            active_trips = Trip.objects.filter(
                ms=ms,
                status__in=['PENDING', 'AT_MS', 'FILLING', 'DISPATCHED', 'IN_TRANSIT', 'AT_DBS']
            ).count()
            
            clusters.append({
                'id': ms.id,
                'msName': ms.name,
                'msCode': ms.code,
                'city': ms.city,
                'location': {
                    'lat': float(ms.lat) if ms.lat else None,
                    'lng': float(ms.lng) if ms.lng else None
                },
                'assignedDBS': dbs_list,
                'linkedDbsCount': len(dbs_list),
                # 'activeTrips': active_trips,
                'status': 'OPERATIONAL'
            })
        
        # Prepare unassigned DBS list
        unassigned_dbs_list = [{
            'dbsId': dbs.id,
            'dbsName': dbs.name,
            'dbsCode': dbs.code,
            'city': dbs.city
        } for dbs in unassigned_dbs]
        
        return Response({
            'clusters': clusters,
            'unassignedDBS': unassigned_dbs_list
        })
    
    def retrieve(self, request, pk=None):
        """Get cluster details"""
        ms = get_object_or_404(Station, id=pk, type='MS')
        
        # Get mapped DBS stations
        dbs_list = []
        for mapping in ms.dbs_mappings.filter(active=True):
            dbs_list.append({
                'dbsId': mapping.dbs.id,
                'dbsName': mapping.dbs.name,
                'dbsCode': mapping.dbs.code,
                'city': mapping.dbs.city
            })
        
        # Get active trips
        active_trips = Trip.objects.filter(
            ms=ms,
            status__in=['PENDING', 'AT_MS', 'FILLING', 'DISPATCHED', 'IN_TRANSIT', 'AT_DBS']
        ).count()
        
        cluster = {
            'id': ms.id,
            'msName': ms.name,
            'msCode': ms.code,
            'city': ms.city,
            'address': ms.address,
            'location': {
                'lat': float(ms.lat) if ms.lat else None,
                'lng': float(ms.lng) if ms.lng else None
            },
            'geofenceRadius': ms.geofence_radius_m,
            'assignedDBS': dbs_list,
            'linkedDbsCount': len(dbs_list),
            'activeTrips': active_trips,
            'status': 'OPERATIONAL'
        }
        
        return Response(cluster)
    
    def update(self, request, pk=None):
        """Update cluster configuration"""
        from core.models import UserRole
        
        ms = get_object_or_404(Station, id=pk, type='MS')
        
        # Check if user has permission to modify this MS
        # User must be assigned to this MS as EIC OR be a Super Admin
        is_assigned = UserRole.objects.filter(
            user=request.user,
            role__code='EIC',
            active=True,
            station=ms
        ).exists()
        
        is_super_admin = request.user.user_roles.filter(
            role__code='SUPER_ADMIN',
            active=True
        ).exists()
        
        if not is_assigned and not is_super_admin:
            return Response({
                'error': 'Permission denied',
                'message': 'You can only modify MS stations that you are assigned to'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Update basic MS info if provided
        if 'msName' in request.data:
            ms.name = request.data['msName']
        if 'city' in request.data:
            ms.city = request.data['city']
        if 'address' in request.data:
            ms.address = request.data['address']
        if 'location' in request.data:
            location = request.data['location']
            if 'lat' in location:
                ms.lat = location['lat']
            if 'lng' in location:
                ms.lng = location['lng']
        if 'geofenceRadius' in request.data:
            ms.geofence_radius_m = request.data['geofenceRadius']
        
        ms.save()
        
        # Handle DBS assignments if provided
        if 'assignedDBS' in request.data:
            from core.models import MSDBSMap
            
            # Get list of DBS IDs to assign
            new_dbs_ids = [dbs['dbsId'] for dbs in request.data['assignedDBS']]
            
            # Deactivate mappings not in the new list
            ms.dbs_mappings.exclude(dbs_id__in=new_dbs_ids).update(active=False)
            
            # Create or activate mappings for new list
            for dbs_id in new_dbs_ids:
                MSDBSMap.objects.update_or_create(
                    ms=ms,
                    dbs_id=dbs_id,
                    defaults={'active': True}
                )
        
        return Response({
            'status': 'updated',
            'id': ms.id,
            'message': f'Cluster {ms.name} updated successfully'
        })


class EICStockTransferMSDBSView(views.APIView):
    """
    GET /api/eic/stock-transfers/ms-dbs
    Returns MS station with its linked DBS stations.
    
    Response:
    {
        "ms": { "msId": "MS001", "msName": "Main Station Alpha" },
        "dbs": [
            { "dbsId": "DBS001", "dbsName": "Depot Station 1", "msId": "MS001", "location": "Mumbai" }
        ]
    }
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from core.models import UserRole, MSDBSMap
        
        # Get MS stations assigned to this EIC user
        eic_station_ids = UserRole.objects.filter(
            user=request.user,
            role__code='EIC',
            active=True,
            station__type='MS'
        ).values_list('station_id', flat=True)
        
        # Check if super admin
        is_super_admin = request.user.user_roles.filter(
            role__code='SUPER_ADMIN', 
            active=True
        ).exists()
        
        # Get ALL assigned MS stations (or all MS for super admin)
        if eic_station_ids:
            ms_stations = Station.objects.filter(id__in=eic_station_ids, type='MS')
        elif is_super_admin:
            ms_stations = Station.objects.filter(type='MS')
        else:
            return Response({'ms': None, 'dbs': []})
        
        ms = ms_stations.first()
        if not ms:
            return Response({'ms': None, 'dbs': []})
        
        # Get ALL linked DBS stations for ALL assigned MS stations
        # Combine from both MSDBSMap and parent_station relationships
        dbs_list = []
        seen_dbs_ids = set()
        
        for ms_station in ms_stations:
            # 1. Get DBS from MSDBSMap
            for mapping in ms_station.dbs_mappings.filter(active=True).select_related('dbs'):
                dbs = mapping.dbs
                if dbs.id not in seen_dbs_ids:
                    seen_dbs_ids.add(dbs.id)
                    dbs_list.append({
                        'dbsId': dbs.id,
                        'dbsCode': dbs.code,
                        'dbsName': dbs.name,
                        'msId': ms_station.id,
                        'msCode': ms_station.code,
                        'location': dbs.city or dbs.address or '',
                        'region': dbs.city or '',
                        'primaryMsName': ms_station.name
                    })
            
            # 2. Get DBS from parent_station relationship (daughter_stations)
            for dbs in ms_station.daughter_stations.filter(type='DBS'):
                if dbs.id not in seen_dbs_ids:
                    seen_dbs_ids.add(dbs.id)
                    dbs_list.append({
                        'dbsId': dbs.id,
                        'dbsCode': dbs.code,
                        'dbsName': dbs.name,
                        'msId': ms_station.id,
                        'msCode': ms_station.code,
                        'location': dbs.city or dbs.address or '',
                        'region': dbs.city or '',
                        'primaryMsName': ms_station.name
                    })
        
        return Response({
            'ms': {
                'msId': ms.id,
                'msCode': ms.code,
                'msName': ms.name
            },
            'dbs': dbs_list
        })


class EICStockTransfersByDBSView(views.APIView):
    """
    GET /api/eic/stock-transfers/by-dbs?dbs_id={dbsId}
    Returns stock transfers for a specific DBS.
    
    Response:
    {
        "transfers": [
            {
                "id": "TRF001",
                "fromLocation": "MS Station Name",
                "toLocation": "DBS Station Name",
                "productName": "CNG",
                "quantity": 5000,
                "status": "COMPLETED",
                "initiatedAt": "2025-12-04T10:30:00Z",
                "completedAt": "2025-12-04T12:45:00Z",
                "estimatedCompletion": "2025-12-04T13:00:00Z",
                "priority": "standard",
                "notes": null
            }
        ],
        "summary": {
            "totalTransfers": 10,
            "inProgress": 2,
            "completed": 8,
            "incomingTotal": 10,
            "incomingInProgress": 2,
            "incomingCompleted": 8,
            "outgoingTotal": 0,
            "outgoingInProgress": 0,
            "outgoingCompleted": 0
        }
    }
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from .models import MSFilling
        from datetime import datetime
        from django.utils import timezone as tz
        
        dbs_id = request.query_params.get('dbs_id')
        start_date = request.query_params.get('start_date')  # Format: YYYY-MM-DD
        end_date = request.query_params.get('end_date')      # Format: YYYY-MM-DD
        include_cancelled = request.query_params.get('include_cancelled', 'false').lower() == 'true'
        
        if not dbs_id:
            return Response({
                'error': 'dbs_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Find DBS by code or id
        try:
            dbs_id_int = int(dbs_id)
            dbs = Station.objects.filter(Q(id=dbs_id_int) | Q(code=dbs_id), type='DBS').first()
        except ValueError:
            dbs = Station.objects.filter(code=dbs_id, type='DBS').first()
        
        if not dbs:
            return Response({
                'error': 'DBS not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get trips to this DBS - exclude CANCELLED by default
        if include_cancelled:
            trips_query = Trip.objects.filter(dbs=dbs)
        else:
            trips_query = Trip.objects.filter(dbs=dbs).exclude(status='CANCELLED')
        
        # Apply date filters if provided
        if start_date:
            try:
                # Try ISO format first (2025-05-01T10:43:00.000Z)
                if 'T' in start_date:
                    start_date_clean = start_date.replace('Z', '+00:00')
                    start_dt = datetime.fromisoformat(start_date_clean)
                else:
                    # Simple date format (YYYY-MM-DD)
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                    start_dt = tz.make_aware(start_dt)
                trips_query = trips_query.filter(started_at__gte=start_dt)
            except (ValueError, TypeError):
                pass  # Invalid date format, ignore
        
        if end_date:
            try:
                # Try ISO format first (2025-08-02T10:43:00.000Z)
                if 'T' in end_date:
                    end_date_clean = end_date.replace('Z', '+00:00')
                    end_dt = datetime.fromisoformat(end_date_clean)
                else:
                    # Simple date format (YYYY-MM-DD)
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                    end_dt = end_dt.replace(hour=23, minute=59, second=59)
                    end_dt = tz.make_aware(end_dt)
                trips_query = trips_query.filter(started_at__lte=end_dt)
            except (ValueError, TypeError):
                pass  # Invalid date format, ignore
        
        trips = trips_query.select_related(
            'ms', 'dbs', 'vehicle', 'driver', 'stock_request'
        ).order_by('-started_at')
        
        transfers = []
        in_progress_count = 0
        completed_count = 0
        
        for trip in trips:
            # Get filling data for quantity
            filling = MSFilling.objects.filter(trip=trip).first()
            quantity = float(filling.filled_qty_kg) if filling and filling.filled_qty_kg else 0
            
            # Determine priority from stock request
            priority = 'standard'
            if trip.stock_request:
                if trip.stock_request.priority_preview in ['H', 'C']:
                    priority = 'high'
                elif trip.stock_request.priority_preview == 'FDODO':
                    priority = 'urgent'
            
            # Map status
            if trip.status == 'COMPLETED':
                completed_count += 1
                status_str = 'COMPLETED'
            elif trip.status == 'CANCELLED':
                status_str = 'CANCELLED'
            else:
                in_progress_count += 1
                status_str = 'IN_PROGRESS'
            
            transfers.append({
                'id': f'TRF{trip.id:03d}',
                'fromLocation': trip.ms.name if trip.ms else 'Unknown MS',
                'toLocation': trip.dbs.name if trip.dbs else 'Unknown DBS',
                'productName': 'CNG',
                'quantity': quantity,
                'status': status_str,
                'initiatedAt': timezone.localtime(trip.started_at).isoformat() if trip.started_at else None,
                'completedAt': timezone.localtime(trip.completed_at).isoformat() if trip.completed_at else None,
                'estimatedCompletion': timezone.localtime(trip.dbs_arrival_at).isoformat() if trip.dbs_arrival_at else None,
                'priority': priority,
                'notes': trip.stock_request.approval_notes if trip.stock_request else None
            })
        
        total_transfers = len(transfers)
        
        return Response({
            'transfers': transfers,
            'summary': {
                'totalTransfers': total_transfers,
                'inProgress': in_progress_count,
                'completed': completed_count,
                'incomingTotal': total_transfers,
                'incomingInProgress': in_progress_count,
                'incomingCompleted': completed_count,
                'outgoingTotal': 0,
                'outgoingInProgress': 0,
                'outgoingCompleted': 0
            }
        })
