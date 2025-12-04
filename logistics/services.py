from django.utils import timezone
from django.db.models import Q, Count
from .models import Shift, Trip

def get_available_drivers(ms_id):
    """
    Find drivers who:
    1. Have an APPROVED shift at the given MS.
    2. Current time is within shift window.
    3. Are NOT on an active trip.
    """
    now = timezone.now()
    
    # 1. Active Approved Shifts at the MS
    active_shifts = Shift.objects.filter(
        vehicle__ms_home_id=ms_id,
        status='APPROVED',
        start_time__lte=now,
        end_time__gte=now
    ).select_related('driver', 'vehicle')
    
    # 2. Drivers currently on active trips
    busy_driver_ids = Trip.objects.filter(
        status__in=['PENDING', 'AT_MS', 'IN_TRANSIT', 'AT_DBS']
    ).values_list('driver_id', flat=True)
    
    # 3. Exclude busy drivers
    available_shifts = active_shifts.exclude(
        driver_id__in=busy_driver_ids
    )
    
    # 4. Annotate with trip count for today (Load Balancing)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # We need to return a list of dicts or objects with driver, vehicle, and trip_count
    results = []
    
    for shift in available_shifts:
        trip_count = Trip.objects.filter(
            driver=shift.driver,
            started_at__gte=today_start
        ).count()
        
        results.append({
            'driver': shift.driver,
            'vehicle': shift.vehicle,
            'trip_count': trip_count
        })
        
    # Sort by trip count (ASC)
    results.sort(key=lambda x: x['trip_count'])
    
    return results
