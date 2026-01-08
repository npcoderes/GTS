# Changes Log - January 8, 2026 (Part 2)

## Timesheet Management - Vehicle Selection Enhancement

### Date: 2026-01-08

### Modified Files:
- `backend/logistics/timesheet_views.py`
- `backend/frontend-dashboard/src/pages/TimesheetManagement.js`

---

## Changes Made:

### 1. **Backend API Updates**

#### Modified: `TimesheetFillWeekView` (timesheet_views.py)
- **Added Parameter**: `vehicle_id` (optional)
- **Behavior**: 
  - If `vehicle_id` is provided, uses that vehicle for all selected drivers
  - If `vehicle_id` is not provided, falls back to each driver's assigned vehicle
  - Returns 404 error if specified vehicle doesn't exist
- **Validation**: Checks if specified vehicle exists before processing

#### Modified: `TimesheetFillMonthView` (timesheet_views.py)
- **Added Parameter**: `vehicle_id` (optional)
- **Behavior**: Same as Fill Week - uses specified vehicle or defaults to driver's assigned vehicle
- **Validation**: Checks if specified vehicle exists before processing

**API Payload Example:**
```json
{
  "driver_ids": [1, 2, 3],
  "template_id": 5,
  "start_date": "2026-01-08",  // For Fill Week
  "vehicle_id": 10,  // Optional - if omitted, uses each driver's assigned vehicle
  "skip_existing": true
}
```

---

### 2. **Frontend UI Updates**

#### Fill Week Modal Enhancements
- **Added**: Vehicle selection dropdown
- **Features**:
  - Optional field with clear label indicating it defaults to driver's assigned vehicle
  - Searchable dropdown with all available vehicles
  - Shows vehicle registration number with car icon
  - Smart default: Auto-selects driver's vehicle when only one driver is selected
  - Clear button to remove selection and use default behavior
  - Placeholder text: "Use driver's assigned vehicle"

#### Fill Month Modal Enhancements
- **Added**: Vehicle selection dropdown (identical to Fill Week)
- **Features**: Same as Fill Week modal

#### Smart Default Behavior
```javascript
// When only one driver is selected:
if (selectedDriverIds.length === 1) {
    const driver = drivers.find(d => d.id === selectedDriverIds[0]);
    if (driver && driver.vehicle_id) {
        // Auto-populate with driver's assigned vehicle
        form.setFieldsValue({ vehicle_id: driver.vehicle_id });
    }
}
```

---

## User Experience Improvements:

### Before:
- ❌ Vehicle was automatically selected from driver's assigned vehicle
- ❌ No way to override vehicle selection
- ❌ Had to manually create shifts if different vehicle needed

### After:
- ✅ **Flexibility**: Can choose any vehicle for bulk operations
- ✅ **Smart Defaults**: Auto-selects driver's vehicle when applicable
- ✅ **Clear UI**: Label clearly indicates the field is optional
- ✅ **Search**: Can search vehicles by registration number
- ✅ **Visual Feedback**: Car icon and clear placeholder text

---

## Use Cases:

### Use Case 1: Standard Operation (Default Behavior)
**Scenario**: Assign shifts using each driver's assigned vehicle
**Action**: Leave vehicle dropdown empty
**Result**: Each driver gets shifts with their assigned vehicle

### Use Case 2: Temporary Vehicle Assignment
**Scenario**: Driver's vehicle is in maintenance, need to use a different vehicle for the week
**Action**: Select specific vehicle from dropdown
**Result**: All selected drivers get shifts with the specified vehicle

### Use Case 3: Pool Vehicle Assignment
**Scenario**: Multiple drivers share a pool vehicle
**Action**: Select the pool vehicle from dropdown
**Result**: All drivers get shifts with the pool vehicle (with conflict detection)

---

## Technical Details:

### Backend Logic Flow:
```python
# 1. Check if vehicle_id is provided
specified_vehicle = None
if vehicle_id:
    specified_vehicle = Vehicle.objects.get(id=vehicle_id)

# 2. For each driver, determine which vehicle to use
for driver in drivers:
    vehicle = specified_vehicle if specified_vehicle else driver.assigned_vehicle
    
    # 3. Create shifts with the determined vehicle
    # ... (rest of shift creation logic)
```

### Frontend Form Structure:
```javascript
<Form.Item shouldUpdate={(prev, curr) => prev.driver_ids !== curr.driver_ids}>
    {() => {
        // Smart default logic
        const selectedDriverIds = form.getFieldValue('driver_ids') || [];
        if (selectedDriverIds.length === 1) {
            // Auto-select driver's vehicle
        }
        return (
            <Form.Item name="vehicle_id" label="Vehicle (Optional)">
                <Select allowClear showSearch>
                    {/* Vehicle options */}
                </Select>
            </Form.Item>
        );
    }}
</Form.Item>
```

---

## Validation & Error Handling:

### Backend Validations:
1. **Vehicle Existence**: Returns 404 if specified vehicle_id doesn't exist
2. **Vehicle Conflicts**: Checks if vehicle is already assigned to another driver at the same time
3. **No Vehicle**: Skips shifts if neither specified nor assigned vehicle exists

### Frontend Validations:
1. **Optional Field**: Not required, can be left empty
2. **Search Validation**: Filters vehicles by registration number
3. **Clear Functionality**: Can clear selection to revert to default

---

## Testing Recommendations:

### Test Scenarios:
1. **Default Behavior**: 
   - Select multiple drivers
   - Leave vehicle field empty
   - Verify each driver gets their assigned vehicle

2. **Override Behavior**:
   - Select multiple drivers
   - Choose a specific vehicle
   - Verify all drivers get the specified vehicle

3. **Single Driver Smart Default**:
   - Select one driver
   - Verify vehicle dropdown auto-populates with driver's vehicle
   - Can still change to different vehicle

4. **No Assigned Vehicle**:
   - Select driver with no assigned vehicle
   - Leave vehicle field empty
   - Verify appropriate error message

5. **Vehicle Conflict**:
   - Try to assign same vehicle to multiple drivers at overlapping times
   - Verify conflict detection works

---

## Database Impact:
- **No Schema Changes**: Uses existing `vehicle_id` foreign key in Shift model
- **No Migrations Required**: Only logic changes

---

## Backward Compatibility:
✅ **Fully Backward Compatible**
- `vehicle_id` parameter is optional
- If not provided, behaves exactly as before
- Existing API calls continue to work without modification

---

## Summary:
This enhancement provides Transport Admins with greater flexibility in vehicle assignment during bulk shift operations. The smart default behavior ensures ease of use while the optional override capability handles special cases like vehicle maintenance, pool vehicles, or temporary assignments. The UI clearly communicates the optional nature of the field and provides helpful defaults when applicable.
