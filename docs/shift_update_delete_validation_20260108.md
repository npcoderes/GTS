# Shift Management Update/Delete Validation - 2026-01-08

## Problem Statement

Previously, the shift management system allowed:
- ❌ Updating shifts that had already started
- ❌ Updating shifts in the past
- ❌ Deleting shifts that were in progress
- ❌ Deleting shifts associated with active trips

This caused data integrity issues and confusion.

---

## Solution Implemented

Added validation rules to **UPDATE** and **DELETE** operations for shifts.

### Update Shift Validation

**Endpoint**: `PUT /api/shifts/{id}/`

**Rules**:
1. ✅ **Can update**: Future shifts (start_time > now)
2. ❌ **Cannot update**: Shifts that have already started (start_time <= now)
3. ❌ **Cannot update**: REJECTED or EXPIRED shifts

**Error Response** (when trying to update started shift):
```json
{
  "error": "Cannot update shift",
  "message": "This shift has already started at 2026-01-08 10:00 AM. You cannot modify shifts that are in progress or have passed.",
  "shift_id": 123,
  "shift_start": "2026-01-08T10:00:00+05:30"
}
```

**Error Response** (when trying to update rejected shift):
```json
{
  "error": "Cannot update shift",
  "message": "This shift has status \"REJECTED\" and cannot be updated. Please create a new shift instead.",
  "shift_id": 123,
  "status": "REJECTED"
}
```

---

### Delete Shift Validation

**Endpoint**: `DELETE /api/shifts/{id}/`

**Rules**:
1. ✅ **Can delete**: Future shifts (start_time > now)
2. ❌ **Cannot delete**: Shifts that have already started (start_time <= now)
3. ❌ **Cannot delete**: Shifts associated with active trips

**Error Response** (when trying to delete started shift):
```json
{
  "error": "Cannot delete shift",
  "message": "This shift has already started at 2026-01-08 10:00 AM. You cannot delete shifts that are in progress or have passed.",
  "shift_id": 123,
  "shift_start": "2026-01-08T10:00:00+05:30"
}
```

**Error Response** (when shift has active trip):
```json
{
  "error": "Cannot delete shift",
  "message": "This shift is associated with an active trip (Trip #456). Complete or cancel the trip first.",
  "shift_id": 123,
  "trip_id": 456
}
```

**Success Response**:
```json
{
  "success": true,
  "message": "Shift deleted successfully: John Doe - 2026-01-10 09:00 AM",
  "shift_id": 123
}
```

---

## Use Cases

### ✅ Allowed Operations

#### 1. Update Future Shift
```
Shift: 2026-01-10 09:00 AM - 05:00 PM
Current Time: 2026-01-08 10:00 PM
Status: PENDING or APPROVED

Action: PUT /api/shifts/123/
Result: ✅ Success - Shift updated, status reset to PENDING for re-approval
```

#### 2. Delete Future Shift
```
Shift: 2026-01-10 09:00 AM - 05:00 PM
Current Time: 2026-01-08 10:00 PM
Active Trips: None

Action: DELETE /api/shifts/123/
Result: ✅ Success - Shift deleted
```

---

### ❌ Blocked Operations

#### 1. Update Shift That Already Started
```
Shift: 2026-01-08 09:00 AM - 05:00 PM
Current Time: 2026-01-08 10:00 PM (shift started 13 hours ago)

Action: PUT /api/shifts/123/
Result: ❌ Error - "This shift has already started at 2026-01-08 09:00 AM"
```

#### 2. Update Shift Currently In Progress
```
Shift: 2026-01-08 02:00 PM - 10:00 PM
Current Time: 2026-01-08 06:00 PM (shift in progress)

Action: PUT /api/shifts/123/
Result: ❌ Error - "This shift has already started at 2026-01-08 02:00 PM"
```

#### 3. Delete Shift With Active Trip
```
Shift: 2026-01-10 09:00 AM - 05:00 PM
Active Trip: Trip #456 (status: AT_MS)

Action: DELETE /api/shifts/123/
Result: ❌ Error - "This shift is associated with an active trip (Trip #456)"
```

#### 4. Update Rejected Shift
```
Shift: 2026-01-10 09:00 AM - 05:00 PM
Status: REJECTED

Action: PUT /api/shifts/123/
Result: ❌ Error - "This shift has status 'REJECTED' and cannot be updated"
```

---

## Implementation Details

### Update Method Changes

**File**: `backend/logistics/views.py` - `ShiftViewSet.update()`

**Added Validation**:
```python
def update(self, request, *args, **kwargs):
    shift = self.get_object()
    now = timezone.now()
    
    # Validation: Cannot update shifts that have already started
    if shift.start_time <= now:
        return Response({
            'error': 'Cannot update shift',
            'message': f'This shift has already started...',
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Validation: Cannot update REJECTED or EXPIRED shifts
    if shift.status in ['REJECTED', 'EXPIRED']:
        return Response({
            'error': 'Cannot update shift',
            'message': f'This shift has status "{shift.status}"...',
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # ... rest of update logic
```

### Delete Method Implementation

**File**: `backend/logistics/views.py` - `ShiftViewSet.destroy()`

**New Method**:
```python
def destroy(self, request, *args, **kwargs):
    shift = self.get_object()
    now = timezone.now()
    
    # Validation: Cannot delete shifts that have already started
    if shift.start_time <= now:
        return Response({
            'error': 'Cannot delete shift',
            'message': f'This shift has already started...',
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if shift is being used in an active trip
    active_trip = Trip.objects.filter(
        driver=shift.driver,
        vehicle=shift.vehicle,
        status__in=['PENDING', 'AT_MS', 'IN_TRANSIT', 'AT_DBS', ...]
    ).first()
    
    if active_trip:
        return Response({
            'error': 'Cannot delete shift',
            'message': f'This shift is associated with an active trip...',
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Perform deletion
    shift.delete()
    return Response({'success': True, ...})
```

---

## Business Logic

### Why These Rules?

1. **Cannot Update/Delete Started Shifts**:
   - Shifts that have started are part of historical record
   - Drivers may already be working based on this shift
   - Trips may have been created using this shift
   - Prevents data corruption and confusion

2. **Cannot Delete Shifts With Active Trips**:
   - Trips reference the shift for validation
   - Deleting would break referential integrity
   - Driver needs shift record for trip completion

3. **Cannot Update Rejected Shifts**:
   - Rejected shifts are final decisions
   - Should create new shift instead
   - Maintains audit trail

---

## Frontend Implications

### UI Changes Needed

1. **Shift List/Table**:
   - Disable "Edit" button for shifts where `start_time <= now`
   - Disable "Delete" button for shifts where `start_time <= now`
   - Show tooltip: "Cannot modify shifts that have started"

2. **Shift Edit Form**:
   - Check shift start time before allowing edit
   - Show warning if trying to edit started shift
   - Redirect to shift list with error message

3. **Shift Delete Confirmation**:
   - Check for active trips before showing confirmation
   - Show specific error if trip exists
   - Provide link to trip details

### Example Frontend Logic

```javascript
// Check if shift can be edited
const canEditShift = (shift) => {
  const now = new Date();
  const shiftStart = new Date(shift.start_time);
  return shiftStart > now && !['REJECTED', 'EXPIRED'].includes(shift.status);
};

// Check if shift can be deleted
const canDeleteShift = (shift) => {
  const now = new Date();
  const shiftStart = new Date(shift.start_time);
  return shiftStart > now;
};

// In shift table
<Button 
  disabled={!canEditShift(shift)}
  onClick={() => editShift(shift.id)}
  title={!canEditShift(shift) ? "Cannot modify shifts that have started" : "Edit shift"}
>
  Edit
</Button>

<Button 
  disabled={!canDeleteShift(shift)}
  onClick={() => deleteShift(shift.id)}
  title={!canDeleteShift(shift) ? "Cannot delete shifts that have started" : "Delete shift"}
>
  Delete
</Button>
```

---

## Testing Checklist

### Update Validation
- [ ] Try to update future shift → Should succeed
- [ ] Try to update shift that started 1 hour ago → Should fail
- [ ] Try to update shift currently in progress → Should fail
- [ ] Try to update rejected shift → Should fail
- [ ] Try to update expired shift → Should fail

### Delete Validation
- [ ] Try to delete future shift with no trips → Should succeed
- [ ] Try to delete shift that started 1 hour ago → Should fail
- [ ] Try to delete shift with active trip → Should fail
- [ ] Try to delete shift with completed trip → Should succeed

### Edge Cases
- [ ] Shift starting in 1 minute → Can update/delete
- [ ] Shift that just started (1 second ago) → Cannot update/delete
- [ ] Recurring shift → Same rules apply
- [ ] One-time shift → Same rules apply

---

## Migration Notes

**No database migration required** - This is purely business logic validation.

---

## Files Modified

1. **`backend/logistics/views.py`**
   - Enhanced `ShiftViewSet.update()` with validation
   - Added `ShiftViewSet.destroy()` with validation

---

## Summary

✅ **Before**: Could update/delete any shift regardless of status or time
❌ **Problem**: Data integrity issues, confusion, broken trips

✅ **After**: Strict validation prevents modifying started shifts
✅ **Result**: Clean data, clear rules, better user experience

**Key Rule**: **Only future shifts can be modified or deleted!**
