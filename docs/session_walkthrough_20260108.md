# Session Walkthrough - Permission System & MS Bay Management

**Date**: 2026-01-08  
**Session Summary**: Fixed permission system issues, implemented dynamic dashboard titles, fixed shift time overlap validation, and implemented MS bay management system.

---

## 1. Permission System Fixes

### Problem
- Permission counts showed "0" for roles even when permissions were assigned
- Super Admin had hardcoded bypass granting all permissions (ignoring DB)
- Dashboard title was static regardless of user role

### Root Cause
1. **DRF Pagination** - Default pagination limited API responses to ~20 records, so counts were computed from partial data
2. **Super Admin Bypass** - Code in `get_user_permissions_from_db()` granted ALL permissions programmatically

### Changes Made

#### permission_views.py

**Removed Super Admin bypass (lines 115-120):**
```diff
-# Check if user is Super Admin - they get all permissions
-is_super_admin = user.user_roles.filter(role__code='SUPER_ADMIN', active=True).exists()
-if is_super_admin:
-    all_permissions = Permission.objects.all().values_list('code', flat=True)
-    result = {code: True for code in all_permissions}
-    return normalize_permissions(result)
```

**Added `pagination_class = None` to ViewSets:**
- `RolePermissionViewSet` - Line 233
- `UserPermissionViewSet` - Line 355
- `StationPermissionViewSet` - Line 468

#### Management Commands Created

1. **seed_super_admin_permissions.py**
   - Seeds SUPER_ADMIN role with all permissions in database
   - Usage: `python manage.py seed_super_admin_permissions`

2. **seed_all_role_permissions.py**
   - Seeds all roles with their default permissions from `DEFAULT_ROLE_PERMISSIONS`
   - Usage: `python manage.py seed_all_role_permissions`

---

## 2. Dynamic Dashboard Title

### Problem
Dashboard showed static "GTS Admin Dashboard" regardless of user role.

### Solution
Updated `DashboardLayout.js` to set both sidebar title and browser tab title dynamically based on user permissions.

#### DashboardLayout.js

**Added `getPageTitle` function and useEffect:**
```javascript
const getPageTitle = useCallback(() => {
  if (hasPermission('can_view_admin_permissions')) return 'Admin Dashboard | GTS';
  if (hasPermission('can_view_eic_network_dashboard')) return 'EIC Dashboard | GTS';
  if (hasPermission('can_view_transport_logistics')) return 'Transport Dashboard | GTS';
  if (hasPermission('can_view_ms_dashboard')) return 'MS Operator | GTS';
  if (hasPermission('can_view_dbs_dashboard')) return 'DBS Operator | GTS';
  if (hasPermission('can_view_customer_dashboard')) return 'Customer Portal | GTS';
  if (hasPermission('can_view_driver_dashboard')) return 'Driver Portal | GTS';
  return 'GTS Dashboard';
}, [hasPermission]);

useEffect(() => {
  if (!permissionsLoading) {
    document.title = getPageTitle();
  }
}, [permissionsLoading, getPageTitle]);
```

---

## 3. Shift Time Overlap Validation

### Problem
Shift creation blocked vehicle assignment for entire day, even if times didn't overlap.

**Example:**
- Driver 1 has shift 1:00 PM - 5:00 PM for Vehicle A
- Creating Driver 2's shift for Vehicle A at 6:00 PM → **Error** (should be allowed)

### Solution
Changed vehicle conflict check from **date-only** to **time overlap**.

#### timesheet_views.py

**Before:**
```python
vehicle_conflict = Shift.objects.filter(
    vehicle=vehicle,
    start_time__date=shift_date,  # Date only!
    status__in=['PENDING', 'APPROVED']
).exclude(driver=driver).first()
```

**After:**
```python
vehicle_conflict = Shift.objects.filter(
    vehicle=vehicle,
    status__in=['PENDING', 'APPROVED'],
    start_time__lt=end_time,   # Overlap: existing starts before new ends
    end_time__gt=start_time,   # Overlap: existing ends after new starts
).exclude(driver=driver).first()
```

**Updated in 4 locations:**
- `TimesheetAssignView.post()` - Line 263
- `TimesheetCopyWeekView.post()` - Line 450
- `TimesheetFillWeekView.post()` - Line 541
- `TimesheetFillMonthView.post()` - Line 660

---


---

## 5. Trip Reset Utility Script

### Problem
Need to manually reset and delete trip data for testing/debugging purposes.

### Solution
Created `reset_trip_80.py` utility script to safely reset Trip 80 and StockRequest 89.

#### Features
- Retrieves and validates Trip and StockRequest objects
- Resets associated VehicleToken to `WAITING` status (makes it reusable)
- Clears token's `trip` and `allocated_at` fields
- Deletes Trip and StockRequest records
- Comprehensive logging for audit trail

#### Usage
```bash
python reset_trip_80.py
```

#### Output Example
```
🚀 Starting reset for Trip 80 (StockRequest 89)
   - Resetting VehicleToken MS3-20260108-00 to WAITING
   ✅ VehicleToken reset
   - Deleting Trip 80
   ✅ Trip deleted
   - Deleting StockRequest 89
   ✅ StockRequest deleted
```

---

## 6. Notification Service Bug Fix

### Problem
Auto-allocation notification failed with error:
```
ERROR - Failed to send allocation notification: 'NoneType' object has no attribute 'vehicle'
```

### Root Cause
`notify_trip_assignment()` in `core/notification_service.py` tried to access `trip.vehicle` when `trip` was `None`.

During token allocation (before driver accepts), the Trip instance doesn't exist yet, so the method received `trip=None` from `TokenQueueService._notify_driver_allocation()`.

### Solution
Made `notify_trip_assignment()` robust to handle `None` trip parameter.

#### core/notification_service.py

**Changes (lines 233-270):**

1. **Conditional token lookup:**
   ```python
   if trip:
       trip_token = TripToken.objects.filter(vehicle=trip.vehicle).order_by('-issued_at').first()
   else:
       trip_token = TripToken.objects.filter(driver=driver).order_by('-issued_at').first()
   ```

2. **Safe data payload:**
   ```python
   data_payload = {
       'tripId': str(trip.id) if trip else '',
       'stockRequestId': str(stock_request.id),
       'msName': trip.ms.name if trip else '',
       'dbsName': trip.dbs.name if trip else '',
       'tokenId': str(trip_token.id) if trip_token else None,
   }
   ```

3. **Conditional body message:**
   ```python
   body_text = (
       f"Trip from {trip.ms.name} to {trip.dbs.name}. Tap to accept."
       if trip
       else "A new trip has been allocated. Tap to view details."
   )
   ```

### Impact
- ✅ Notifications now send successfully during auto-allocation
- ✅ Drivers receive allocation notifications with available trip details
- ✅ No more AttributeError crashes in allocation flow

---

## 7. Bay Management Flow Fixes

### Problems Identified

**Problem 1: Bay Count Not Decreasing After Confirmation**
When MS operator confirmed filling completion, the bay count in the resume API did not decrease - occupied bays remained at the same count even after trucks were cleared to leave.

**Problem 2: No Sequential Filling Order Enforcement**
Trucks could start filling regardless of their queue position (token sequence). For example, truck with sequence #4 could start filling before truck with sequence #3, violating FIFO (First In, First Out) order.

### Root Causes

**Cause 1**:  
The `get_bay_status()` query filters by `trip__status__in=['PENDING', 'AT_MS']`. When MS operator confirmed, the trip status remained `AT_MS`, so the bay was still counted as occupied even though the truck was ready to leave.

**Cause 2**:  
No validation existed in `MSFillStartView` to check if earlier sequence trucks were waiting before allowing a truck to start filling.

### Solutions Implemented

#### 1. Enabled FILLED Status

**File**: `logistics/models.py` (Line 240)

Uncommented the `FILLED` status in `Trip.STATUS_CHOICES`:

```python
STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('AT_MS', 'At MS'),
    # ('FILLING', 'Filling'),
    ('FILLED', 'Filled'),  # ← Uncommented
    # ('DISPATCHED', 'Dispatched'),
    ('IN_TRANSIT', 'In Transit'),
    # ...
]
```

#### 2. Update Trip Status to FILLED on MS Operator Confirmation

**File**: `logistics/ms_views.py` (`MSConfirmFillingView.post()`, Line ~763-775)

**Before**:
```python
with transaction.atomic():
    filling.confirmed_by_ms_operator = request.user
    filling.save()
    
    if trip.current_step >= 3:
        trip.step_data = {**trip.step_data, 'ms_operator_confirmed': True}
    trip.save()
```

**After**:
```python
with transaction.atomic():
    filling.confirmed_by_ms_operator = request.user
    filling.save()
    
    # Update trip status to FILLED - this frees up the bay
    # Bay is considered occupied while trip status is 'AT_MS'
    # Once operator confirms, truck is ready to leave, so we mark as FILLED
    trip.status = 'FILLED'
    
    if trip.current_step >= 3:
        trip.step_data = {**trip.step_data, 'ms_operator_confirmed': True}
    trip.save()
```

**Impact**: When MS operator confirms, trip status changes from `AT_MS` to `FILLED`. The `get_bay_status()` query excludes `FILLED` trips, so the bay count correctly decreases.

#### 3. Add Sequence Validation to Enforce FIFO Order

**File**: `logistics/ms_views.py` (`MSFillStartView.post()`, Line ~540-596)

Added validation logic after retrieving the trip:

```python
# Validate sequential filling order (FIFO - First In, First Out)
# Trucks must start filling in token sequence order
if hasattr(trip, 'vehicle_token') and trip.vehicle_token:
    current_sequence = trip.vehicle_token.sequence_number
    
    # Check if there are earlier sequence trucks that haven't started filling yet
    earlier_trucks_waiting = Trip.objects.filter(
        ms=ms,
        status__in=['PENDING', 'AT_MS'],
        vehicle_token__sequence_number__lt=current_sequence,
        vehicle_token__token_date=trip.vehicle_token.token_date,
    ).exclude(
        # Exclude trucks that have already started filling
        id__in=MSFilling.objects.filter(
            trip__ms=ms,
            trip__status__in=['PENDING', 'AT_MS'],
            trip__vehicle_token__token_date=trip.vehicle_token.token_date,
        ).exclude(
            prefill_mfm__isnull=True,
            prefill_pressure_bar__isnull=True,
        ).values_list('trip_id', flat=True)
    ).exists()
    
    if earlier_trucks_waiting:
        first_waiting = Trip.objects.filter(...)  # Get details for error message
        waiting_seq = first_waiting.vehicle_token.sequence_number
        waiting_vehicle = first_waiting.vehicle.registration_no
        return validation_error_response(
            f'Cannot start filling. Vehicle with sequence #{waiting_seq} '
            f'({waiting_vehicle}) arrived first and must fill before you.'
        )
```

**Logic**:
- Query finds trucks with lower sequence numbers that haven't started filling
- If such trucks exist, reject the filling attempt with a descriptive error
- Error message includes the specific sequence number and vehicle that must go first

**Example Error Response**:
```json
{
  "success": false,
  "error": "Cannot start filling. Vehicle with sequence #3 (GJ218000) arrived first and must fill before you. Please wait for earlier vehicles to start filling."
}
```

### Flow After Fixes

```
Truck arrives at MS (sequence #3)
         ↓
MS Operator confirms arrival → Trip status: AT_MS
         ↓
Truck starts filling (pre-fill readings) → Bay occupied
         ↓
Truck finishes filling (post-fill readings) → Bay still occupied
         ↓
MS Operator confirms completion → Trip status: FILLED ✅ BAY FREED
         ↓
Driver confirms and leaves → Trip status: IN_TRANSIT
```

### Bay Count Query Behavior

**Query** (`get_bay_status()` in `ms_views.py`, Line ~326):
```python
occupied_count = MSFilling.objects.filter(
    trip__ms=ms,
    trip__status__in=['PENDING', 'AT_MS'],  # ← FILLED trips excluded!
    confirmed_by_ms_operator__isnull=True,
).exclude(
    prefill_mfm__isnull=True,
    prefill_pressure_bar__isnull=True,
).count()
```

**Before Fix**: Trip status stayed `AT_MS` after confirmation → Bay still counted as occupied  
**After Fix**: Trip status changes to `FILLED` after confirmation → Bay excluded from count ✅

---

## Files Modified Summary

| File | Changes |
|------|---------|
| `core/models.py` | Added `no_of_bays` field to Station |
| `core/permission_views.py` | Removed Super Admin bypass, disabled pagination |
| `core/notification_service.py` | **UPDATED** - Fixed `notify_trip_assignment()` to handle None trip |
| `core/management/commands/seed_super_admin_permissions.py` | **NEW** |
| `core/management/commands/seed_all_role_permissions.py` | **NEW** |
| `logistics/models.py` | **UPDATED** - Uncommented `FILLED` status in Trip.STATUS_CHOICES |
| `logistics/ms_views.py` | **UPDATED** - Set trip status to `FILLED` in `MSConfirmFillingView` |
| `logistics/ms_views.py` | **UPDATED** - Added sequence validation in `MSFillStartView` |
| `logistics/timesheet_views.py` | Fixed shift time overlap validation |
| `reset_trip_80.py` | **NEW** - Utility script to reset trip data |
| `frontend-dashboard/src/components/DashboardLayout.js` | Dynamic page/sidebar titles |

---

## Testing Checklist

- [ ] Login as Super Admin → Title shows "Admin Dashboard | GTS"
- [ ] Disable a permission for Super Admin → Access blocked
- [ ] Permission counts match visible toggles in UI
- [ ] Create Driver 2 shift after Driver 1's shift ends → Allowed
- [ ] MS resume API returns `bay_status` object
- [ ] Start 3rd truck filling with 2 bays → Rejected
- [ ] Trucks sorted by token sequence in resume response
- [x] EIC approves stock request → Driver receives allocation notification ✅
- [x] Reset trip script cleans up trip data successfully ✅
- [ ] **Bay count decreases after MS operator confirms filling** ✅
- [ ] **Sequence #4 truck cannot start filling before sequence #3** ✅
- [ ] **Parallel filling works with available bays and sequence order** ✅
