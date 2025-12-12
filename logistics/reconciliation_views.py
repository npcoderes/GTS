from rest_framework import views, status, generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Reconciliation
from core.models import UserRole, User

class ReconciliationListView(views.APIView):
    """
    API Path: GET /api/eic/reconciliation/
    List detailed data for reconciliation records.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 1. Verify Permission (EIC or Super Admin)
        user = request.user
        is_eic = user.user_roles.filter(role__code='EIC', active=True).exists()
        is_super_admin = user.user_roles.filter(role__code='SUPER_ADMIN', active=True).exists()
        
        if not (is_eic or is_super_admin):
            return Response(
                {'error': 'Permission denied. Only EIC can view reconciliation details.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
            
        # 2. Get Reconciliation Records
        # Filter by EIC's MS stations if not super admin
        queryset = Reconciliation.objects.select_related(
            'trip', 'trip__ms', 'trip__dbs', 'trip__driver', 'trip__vehicle', 'trip__token'
        ).order_by('-id')

        if not is_super_admin:
            eic_station_ids = UserRole.objects.filter(
                user=user, role__code='EIC', active=True, station__type='MS'
            ).values_list('station_id', flat=True)
            
            queryset = queryset.filter(trip__ms_id__in=eic_station_ids)

        reports = []
        for rec in queryset:
            trip = rec.trip
            if not trip:
                 continue

            # 3. Calculate Variance
            ms_qty = float(rec.ms_filled_qty_kg or 0)
            dbs_qty = float(rec.dbs_delivered_qty_kg or 0)
            variance = dbs_qty - ms_qty # Difference
            variance_abs = abs(variance)
            
            variance_pct = 0.0
            if ms_qty > 0:
                variance_pct = (variance_abs / ms_qty) * 100
            
            # 4. Construct Data for this item
            reports.append({
                "id": rec.id,
                "trip": {
                    "id": str(trip.id),
                    "token": trip.token.token_no if hasattr(trip, 'token') and trip.token else None,
                    "status": trip.status,
                    "startedAt": timezone.localtime(trip.started_at).isoformat() if trip.started_at else None,
                    "completedAt": timezone.localtime(trip.completed_at).isoformat() if trip.completed_at else None,
                },
                "station": {
                    "msId": trip.ms.code if trip.ms else None,
                    "msName": trip.ms.name if trip.ms else None,
                    "dbsId": trip.dbs.code if trip.dbs else None,
                    "dbsName": trip.dbs.name if trip.dbs else None,
                },
                "quantities": {
                    "msFilled": ms_qty,
                    "dbsDelivered": dbs_qty,
                    "difference": round(variance, 2),
                    "unit": "kg"
                },
                "variance": {
                    "percentage": round(variance_pct, 2),
                    "isAboveThreshold": variance_pct > 0.5, # Assuming 0.5% threshold
                    "severity": "HIGH" if variance_pct > 1.0 else ("MEDIUM" if variance_pct > 0.5 else "LOW"),
                    "financialImpact": round(variance_abs * 50, 2) # Example calc
                },
                "driver": {
                    "id": str(trip.driver.id) if trip.driver else None,
                    "name": trip.driver.full_name if trip.driver else None,
                    "vehicleNo": trip.vehicle.registration_no if trip.vehicle else None
                },
                "timeline": {
                    "filledAt": timezone.localtime(trip.ms_departure_at).isoformat() if trip.ms_departure_at else None,
                    "decantedAt": timezone.localtime(trip.completed_at).isoformat() if trip.completed_at else None,
                    "transitTimeMinutes": int((trip.completed_at - trip.started_at).total_seconds() / 60) if (trip.completed_at and trip.started_at) else 0
                },
                "status": rec.status # PENDING, APPROVED, FLAGGED, etc.
            })
        
        return Response({"reports": reports})
