from django.utils import timezone
from django.db.models import Q, Count
from .models import Shift, Trip


def find_active_shift(driver, check_time=None):
    """
    Find an active shift for a driver at a specific time.
    Handles both one-time and recurring shifts.
    """
    if not check_time:
        check_time = timezone.now()
        
    # 1. Check One-time Shifts
    one_time = Shift.objects.filter(
        driver=driver,
        status='APPROVED',
        is_recurring=False,
        start_time__lte=check_time,
        end_time__gte=check_time
    ).first()
    
    if one_time:
        return one_time
        
    # 2. Check Recurring Shifts
    # Filter by APPROVED and is_recurring=True
    # Then check time of day match
    recurring_shifts = Shift.objects.filter(
        driver=driver,
        status='APPROVED',
        is_recurring=True
    )
    
    check_time_obj = check_time.time() if hasattr(check_time, 'time') else check_time
    
    for shift in recurring_shifts:
        # Assuming start_time and end_time store the time-of-day in their time components
        # Logic: Valid if check_time is between start and end (handling overnight if needed)
        start = shift.start_time.time()
        end = shift.end_time.time()
        
        if start <= end:
            if start <= check_time_obj <= end:
                return shift
        else: # Overnight shift (e.g. 22:00 to 06:00)
            if check_time_obj >= start or check_time_obj <= end:
                return shift
                
    return None

def get_available_drivers(ms_id):
    """
    Find drivers who:
    1. Have an APPROVED active shift (One-time or Recurring) at the given MS.
    2. Are NOT on an active trip.
    """
    now = timezone.now()
    
    # 1. Get all drivers assigned to vendors/MS?
    # Better approach: Get all APPROVED shifts associated with this MS (via vehicle home)
    # Then filter down to those currently active
    
    # Get all potential candidate shifts for this MS
    # (Recurring OR One-time overlapping now)
    
    # Note: Complex filtering on Recurring time-of-day difficult in ORM across DBs
    # Strategy: Fetch all 'Active' drivers for this MS, then filter in python
    
    candidate_shifts = Shift.objects.filter(
        vehicle__ms_home_id=ms_id,
        status='APPROVED'
    ).select_related('driver', 'vehicle')
    
    active_shifts = []
    
    processed_drivers = set()
    
    for shift in candidate_shifts:
        if shift.driver.id in processed_drivers:
            continue
            
        # Check if this specific shift is active NOW
        is_active = False
        
        if not shift.is_recurring:
            if shift.start_time <= now <= shift.end_time:
                is_active = True
        else:
            # Recurring check
            check_time = now.time()
            start = shift.start_time.time()
            end = shift.end_time.time()
            if start <= end:
                if start <= check_time <= end:
                    is_active = True
            else:
                if check_time >= start or check_time <= end:
                    is_active = True
        
        if is_active:
            active_shifts.append(shift)
            processed_drivers.add(shift.driver.id)
    
    # 2. Drivers currently on active trips
    busy_driver_ids = Trip.objects.filter(
        status__in=['PENDING', 'AT_MS', 'IN_TRANSIT', 'AT_DBS','DECANTING_CONFIRMED']
    ).values_list('driver_id', flat=True)
    
    # 3. Exclude busy drivers
    available_shifts = [s for s in active_shifts if s.driver.id not in busy_driver_ids]
    
    # 4. Annotate with trip count for today
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
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
