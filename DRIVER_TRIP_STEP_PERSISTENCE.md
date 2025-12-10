# Driver Trip Step Persistence Feature

## Overview

This feature enables drivers to resume their trip progress from where they left off when they reopen the mobile app. Previously, if a driver closed the app during any step of the trip process, all progress would be lost and they would return to step 0. Now, the system tracks and persists each step of the journey along with partial data (like pre/post readings), allowing seamless recovery of the trip state.

## Problem Statement

**Before Implementation:**
- Driver accepts trip (Step 1)
- Driver arrives at MS (Step 2)
- MS operator enters pre-reading (Step 3a)
- **Driver closes app** ❌
- **Upon reopening: All progress lost, returns to Step 0** ❌

**After Implementation:**
- Driver accepts trip (Step 1) ✅
- Driver arrives at MS (Step 2) ✅
- MS operator enters pre-reading (Step 3a) ✅
- **Driver closes app** ✅
- **Upon reopening: Returns to Step 3 with pre-reading data intact** ✅

---

## Seven-Step Driver Trip Process

The driver trip workflow is divided into 7 distinct steps:

| Step | Description | Key Actions | Data Stored |
|------|-------------|-------------|-------------|
:wq
| **0** | No active trip / Initial state | - | - |
| **1** | Trip Accepted | Driver accepts trip offer | `trip_accepted: true` |
| **2** | Arrived at MS | Driver confirms arrival at Mother Station | `arrived_at_ms: true` |
| **3** | MS Filling Process | MS operator enters pre/post readings, driver/operator confirms | `ms_pre_reading_done`, `ms_post_reading_done`, `ms_pre_photo_uploaded`, `ms_post_photo_uploaded`, `ms_filling_confirmed` |
| **4** | Heading to DBS | Vehicle departs MS and travels to DBS | `ms_filling_confirmed: true` |
| **5** | DBS Decanting Process | DBS operator enters pre/post decant readings, confirms delivery | `arrived_at_dbs`, `dbs_pre_reading_done`, `dbs_post_reading_done`, `dbs_pre_photo_uploaded`, `dbs_post_photo_uploaded`, `dbs_decanting_confirmed` |
| **6** | Return to MS | Driver navigates back to MS after decanting | `dbs_decanting_confirmed: true` |
| **7** | Trip Completion | Trip complete screen | Trip status = `COMPLETED` |

---

## Database Schema Changes

### New Fields in `Trip` Model

```python
class Trip(models.Model):
    # ... existing fields ...

    # Step tracking for driver app resume functionality
    current_step = models.IntegerField(default=0)  # 0-7: tracks current trip step
    step_data = models.JSONField(default=dict, blank=True)  # Stores partial progress data
    last_activity_at = models.DateTimeField(auto_now=True)  # Auto-updated on any change
```

#### Field Descriptions:

**`current_step`** (Integer, default=0)
- Tracks the current step in the 7-step journey (0-7)
- Updated by each API endpoint as the trip progresses
- Used by resume API to determine which screen to show driver

**`step_data`** (JSONField, default={})
- Stores granular substep progress within each major step
- Particularly important for Step 3 (MS Filling) and Step 5 (DBS Decanting)
- Preserves partial data like "pre-reading entered but not post-reading"

**`last_activity_at`** (DateTimeField, auto_now=True)
- Automatically updated whenever any field in the Trip model changes
- Useful for monitoring trip activity and detecting stale trips

### Migration File

**File:** `logistics/migrations/0020_trip_step_tracking.py`

```python
operations = [
    migrations.AddField(
        model_name='trip',
        name='current_step',
        field=models.IntegerField(default=0),
    ),
    migrations.AddField(
        model_name='trip',
        name='step_data',
        field=models.JSONField(blank=True, default=dict),
    ),
    migrations.AddField(
        model_name='trip',
        name='last_activity_at',
        field=models.DateTimeField(auto_now=True),
    ),
]
```

**To apply migration:**
```bash
python manage.py migrate logistics
```

---

## API Updates

### 1. Trip Acceptance (`POST /api/driver-trips/accept/`)

**Updated Logic:**
```python
trip = Trip.objects.create(
    # ... existing fields ...
    started_at=timezone.now(),
    current_step=1,  # Step 1: Trip accepted
    step_data={'trip_accepted': True}
)
```

**Step Data:**
```json
{
  "trip_accepted": true
}
```

---

### 2. Arrival at MS (`POST /api/driver-trips/arrival/ms/`)

**Updated Logic:**
```python
trip.status = 'AT_MS'
trip.origin_confirmed_at = timezone.now()
trip.current_step = 2  # Step 2: Arrived at MS
trip.step_data = {**trip.step_data, 'arrived_at_ms': True}
trip.save()
```

**Step Data:**
```json
{
  "trip_accepted": true,
  "arrived_at_ms": true
}
```

---

### 3. MS Filling Process (Step 3)

#### 3a. Start Filling - Pre-Reading (`POST /api/ms/fill/start`)

**MS Operator App**

```python
trip.status = 'FILLING'
trip.current_step = 3  # Step 3: MS Filling in progress
trip.step_data = {**trip.step_data, 'ms_pre_reading_done': True}
trip.save()
```

**Step Data:**
```json
{
  "trip_accepted": true,
  "arrived_at_ms": true,
  "ms_pre_reading_done": true
}
```

#### 3b. End Filling - Post-Reading (`POST /api/ms/fill/end`)

**MS Operator App**

```python
trip.status = 'FILLED'
trip.step_data = {**trip.step_data, 'ms_post_reading_done': True}
trip.save()
```

**Step Data:**
```json
{
  "trip_accepted": true,
  "arrived_at_ms": true,
  "ms_pre_reading_done": true,
  "ms_post_reading_done": true
}
```

#### 3c. Confirm Filling (`POST /api/ms/fill/confirm`)

**MS Operator App**

```python
trip.status = 'DISPATCHED'
trip.ms_departure_at = timezone.now()
trip.current_step = 4  # Step 4: Departed MS, heading to DBS
trip.step_data = {**trip.step_data, 'ms_filling_confirmed': True}
trip.save()
```

**Step Data:**
```json
{
  "trip_accepted": true,
  "arrived_at_ms": true,
  "ms_pre_reading_done": true,
  "ms_post_reading_done": true,
  "ms_filling_confirmed": true
}
```

#### 3d. Driver Meter Reading Confirmation (`POST /api/driver-trips/meter-reading/confirm/`)

**Driver App** (Alternative method)

```python
# For MS Pre-Reading
if station_type == 'MS' and reading_type == 'pre':
    trip.current_step = 3
    trip.step_data = {
        **trip.step_data,
        'ms_pre_reading_done': True,
        'ms_pre_photo_uploaded': bool(photo_file)
    }

# For MS Post-Reading
if station_type == 'MS' and reading_type == 'post':
    trip.step_data = {
        **trip.step_data,
        'ms_post_reading_done': True,
        'ms_post_photo_uploaded': bool(photo_file)
    }

    if request.data.get('confirmed'):
        trip.status = 'IN_TRANSIT'
        trip.current_step = 4
        trip.step_data = {**trip.step_data, 'ms_filling_confirmed': True}
```

---

### 4. Arrival at DBS (`POST /api/driver-trips/arrival/dbs/`)

**Updated Logic:**
```python
trip.status = 'AT_DBS'
trip.dbs_arrival_at = timezone.now()
trip.current_step = 5  # Step 5: Arrived at DBS / Decanting process
trip.step_data = {**trip.step_data, 'arrived_at_dbs': True}
trip.save()
```

**Step Data:**
```json
{
  "trip_accepted": true,
  "arrived_at_ms": true,
  "ms_pre_reading_done": true,
  "ms_post_reading_done": true,
  "ms_filling_confirmed": true,
  "arrived_at_dbs": true
}
```

---

### 5. DBS Decanting Process (Step 5)

#### 5a. Start Decanting - Pre-Reading (`POST /api/dbs/stock-requests/decant/start`)

**DBS Operator App**

```python
trip.current_step = 5  # Step 5: DBS Decanting in progress
trip.step_data = {**trip.step_data, 'dbs_pre_reading_done': True}
trip.save()
```

**Step Data:**
```json
{
  "arrived_at_dbs": true,
  "dbs_pre_reading_done": true
}
```

#### 5b. End Decanting - Post-Reading (`POST /api/dbs/stock-requests/decant/end`)

**DBS Operator App**

```python
trip.step_data = {**trip.step_data, 'dbs_post_reading_done': True}
trip.save()
```

**Step Data:**
```json
{
  "arrived_at_dbs": true,
  "dbs_pre_reading_done": true,
  "dbs_post_reading_done": true
}
```

#### 5c. Confirm Decanting (`POST /api/dbs/stock-requests/decant/confirm`)

**DBS Operator App**

```python
trip.status = 'DECANTING_CONFIRMED'
trip.current_step = 6  # Step 6: Navigate back to MS
trip.step_data = {**trip.step_data, 'dbs_decanting_confirmed': True}
trip.save()
```

**Step Data:**
```json
{
  "arrived_at_dbs": true,
  "dbs_pre_reading_done": true,
  "dbs_post_reading_done": true,
  "dbs_decanting_confirmed": true
}
```

#### 5d. Driver Meter Reading Confirmation at DBS (`POST /api/driver-trips/meter-reading/confirm/`)

**Driver App** (Alternative method)

```python
# For DBS Pre-Reading
if station_type == 'DBS' and reading_type == 'pre':
    trip.current_step = 5
    trip.step_data = {
        **trip.step_data,
        'dbs_pre_reading_done': True,
        'dbs_pre_photo_uploaded': bool(photo_file)
    }

# For DBS Post-Reading
if station_type == 'DBS' and reading_type == 'post':
    trip.step_data = {
        **trip.step_data,
        'dbs_post_reading_done': True,
        'dbs_post_photo_uploaded': bool(photo_file)
    }

    if request.data.get('confirmed'):
        trip.status = 'DECANTING_CONFIRMED'
        trip.current_step = 6
        trip.step_data = {**trip.step_data, 'dbs_decanting_confirmed': True}
```

---

### NEW: Resume API Endpoint

#### `GET /api/driver-trips/resume/`

**Purpose:** Called by driver app when reopening to restore trip state

**Request:** No payload required (uses authenticated driver)

**Response (Has Active Trip):**

```json
{
  "hasActiveTrip": true,
  "trip": {
    "id": 123,
    "token": "A1B2C3D4E5F6",
    "currentStep": 3,
    "stepData": {
      "trip_accepted": true,
      "arrived_at_ms": true,
      "ms_pre_reading_done": true,
      "ms_pre_photo_uploaded": true,
      "ms_post_reading_done": false
    },
    "status": "FILLING",
    "tripDetails": {
      "stockRequestId": 456,
      "ms": {
        "id": 10,
        "name": "Mother Station Alpha",
        "code": "MS001",
        "address": "123 Main St, City"
      },
      "dbs": {
        "id": 20,
        "name": "DBS Beta",
        "code": "DBS005",
        "address": "456 Oak Ave, Town"
      },
      "vehicle": {
        "id": 30,
        "registrationNo": "ABC-1234",
        "capacity_kg": "5000.00"
      },
      "started_at": "2025-12-09T10:30:00Z",
      "sto_number": "STO-MS001-DBS005-123-202512091030"
    },
    "msFillingData": {
      "id": 789,
      "prefill_pressure_bar": "200.00",
      "prefill_mfm": "1000.00",
      "postfill_pressure_bar": null,
      "postfill_mfm": null,
      "filled_qty_kg": null,
      "prefill_photo_url": "/media/ms_fillings/pre/reading_123_MS_pre_a1b2c3.jpg",
      "postfill_photo_url": null,
      "confirmed_by_ms_operator": false,
      "start_time": "2025-12-09T10:45:00Z",
      "end_time": null
    },
    "dbsDecantingData": null
  }
}
```

**Response (No Active Trip):**

```json
{
  "hasActiveTrip": false,
  "message": "No active trip found"
}
```

**Implementation:**

```python
@action(detail=False, methods=['get'], url_path='resume')
def resume_trip(self, request):
    """Resume trip - Get current trip state for driver when app reopens."""
    driver = getattr(request.user, 'driver_profile', None)

    # Find active trip
    active_trip = Trip.objects.filter(
        driver=driver,
        status__in=['PENDING', 'AT_MS', 'IN_TRANSIT', 'AT_DBS', 'DECANTING_CONFIRMED']
    ).select_related('token', 'vehicle', 'ms', 'dbs', 'stock_request')
     .prefetch_related('ms_fillings', 'dbs_decantings')
     .first()

    if not active_trip:
        return Response({'hasActiveTrip': False, 'message': 'No active trip found'})

    # Get step details including partial data
    step_details = active_trip.get_step_details()

    # Return comprehensive trip state
    return Response({...})
```

---

## Model Helper Methods

### `calculate_current_step()` Method

**Purpose:** Automatically calculates the current step based on trip state, status, and related records. Used as a fallback to ensure `current_step` accuracy.

**File:** `logistics/models.py` in `Trip` model

```python
def calculate_current_step(self):
    """
    Auto-calculate current step based on trip state.

    Returns: int (0-7)
    """
    # Cancelled trips reset to 0
    if self.status == 'CANCELLED':
        return 0

    # Completed trips are at step 7
    if self.status == 'COMPLETED':
        return 7

    # Decanting confirmed, navigating back to MS (step 6)
    if self.status == 'DECANTING_CONFIRMED':
        return 6

    # Check if at DBS or decanting (step 5)
    if self.status == 'AT_DBS' or self.dbs_decantings.exists():
        if self.dbs_decantings.filter(confirmed_by_dbs_operator__isnull=False).exists():
            return 6
        return 5

    # Check if left MS and heading to DBS (step 4)
    if self.status == 'IN_TRANSIT' or self.ms_departure_at:
        return 4

    # Check if at MS or filling in progress (step 3)
    if self.status == 'AT_MS' or self.ms_fillings.exists():
        if self.ms_departure_at:
            return 4
        return 3 if self.ms_fillings.exists() else 2

    # Arrived at MS (step 2)
    if self.origin_confirmed_at:
        return 2

    # Trip accepted (step 1)
    if self.started_at:
        return 1

    # No active trip (step 0)
    return 0
```

**Usage:**
```python
trip = Trip.objects.get(id=123)
calculated_step = trip.calculate_current_step()

# Verify consistency
if trip.current_step != calculated_step:
    print(f"Warning: current_step mismatch! DB: {trip.current_step}, Calculated: {calculated_step}")
```

---

### `get_step_details()` Method

**Purpose:** Returns comprehensive step information including substep progress and partial data for MS Filling (step 3) and DBS Decanting (step 5).

**File:** `logistics/models.py` in `Trip` model

```python
def get_step_details(self):
    """
    Get detailed step information including substep progress.

    Returns: dict with current_step, step_data, and filling/decanting details
    """
    step = self.calculate_current_step()

    details = {
        'current_step': step,
        'step_data': self.step_data,
        'trip_id': self.id,
        'token': self.token.token_no if self.token else None,
        'status': self.status,
    }

    # Step 3: MS Filling details
    if step == 3:
        ms_filling = self.ms_fillings.first()
        if ms_filling:
            details['ms_filling'] = {
                'id': ms_filling.id,
                'prefill_pressure_bar': str(ms_filling.prefill_pressure_bar) if ms_filling.prefill_pressure_bar else None,
                'prefill_mfm': str(ms_filling.prefill_mfm) if ms_filling.prefill_mfm else None,
                'postfill_pressure_bar': str(ms_filling.postfill_pressure_bar) if ms_filling.postfill_pressure_bar else None,
                'postfill_mfm': str(ms_filling.postfill_mfm) if ms_filling.postfill_mfm else None,
                'filled_qty_kg': str(ms_filling.filled_qty_kg) if ms_filling.filled_qty_kg else None,
                'prefill_photo_url': ms_filling.prefill_photo.url if ms_filling.prefill_photo else None,
                'postfill_photo_url': ms_filling.postfill_photo.url if ms_filling.postfill_photo else None,
                'confirmed_by_ms_operator': ms_filling.confirmed_by_ms_operator_id is not None,
                'start_time': ms_filling.start_time.isoformat() if ms_filling.start_time else None,
                'end_time': ms_filling.end_time.isoformat() if ms_filling.end_time else None,
            }

    # Step 5: DBS Decanting details
    if step == 5:
        dbs_decanting = self.dbs_decantings.first()
        if dbs_decanting:
            details['dbs_decanting'] = {
                'id': dbs_decanting.id,
                'pre_dec_pressure_bar': str(dbs_decanting.pre_dec_pressure_bar) if dbs_decanting.pre_dec_pressure_bar else None,
                'pre_dec_reading': str(dbs_decanting.pre_dec_reading) if dbs_decanting.pre_dec_reading else None,
                'post_dec_pressure_bar': str(dbs_decanting.post_dec_pressure_bar) if dbs_decanting.post_dec_pressure_bar else None,
                'post_dec_reading': str(dbs_decanting.post_dec_reading) if dbs_decanting.post_dec_reading else None,
                'delivered_qty_kg': str(dbs_decanting.delivered_qty_kg) if dbs_decanting.delivered_qty_kg else None,
                'pre_decant_photo_url': dbs_decanting.pre_decant_photo.url if dbs_decanting.pre_decant_photo else None,
                'post_decant_photo_url': dbs_decanting.post_decant_photo.url if dbs_decanting.post_decant_photo else None,
                'confirmed_by_dbs_operator': dbs_decanting.confirmed_by_dbs_operator_id is not None,
                'start_time': dbs_decanting.start_time.isoformat() if dbs_decanting.start_time else None,
                'end_time': dbs_decanting.end_time.isoformat() if dbs_decanting.end_time else None,
            }

    return details
```

**Usage:**
```python
trip = Trip.objects.get(id=123)
details = trip.get_step_details()

print(f"Current Step: {details['current_step']}")
print(f"Step Data: {details['step_data']}")

if details.get('ms_filling'):
    print(f"MS Pre-Reading: {details['ms_filling']['prefill_pressure_bar']}")
    print(f"MS Post-Reading: {details['ms_filling']['postfill_pressure_bar']}")
```

---

## Edge Cases Handled

### Step 3 (MS Filling) Edge Cases

#### Case 1: Only Pre-Reading Entered
```json
{
  "ms_pre_reading_done": true,
  "ms_pre_photo_uploaded": true
}
```

**Frontend Action:** Show MS filling screen with pre-reading fields pre-filled, post-reading fields empty.

#### Case 2: Both Pre and Post Readings Entered
```json
{
  "ms_pre_reading_done": true,
  "ms_post_reading_done": true,
  "ms_pre_photo_uploaded": true,
  "ms_post_photo_uploaded": true
}
```

**Frontend Action:** Show MS filling screen with all readings visible, awaiting operator confirmation.

#### Case 3: Waiting for MS Operator Confirmation
```json
{
  "ms_pre_reading_done": true,
  "ms_post_reading_done": true,
  "ms_waiting_confirmation": true
}
```

**Frontend Action:** Show "Waiting for MS operator to confirm" status screen.

---

### Step 5 (DBS Decanting) Edge Cases

#### Case 1: Arrived at DBS, No Readings Yet
```json
{
  "arrived_at_dbs": true
}
```

**Frontend Action:** Show DBS arrival confirmation screen, ready for decanting process.

#### Case 2: Pre-Reading Entered
```json
{
  "arrived_at_dbs": true,
  "dbs_pre_reading_done": true,
  "dbs_pre_photo_uploaded": true
}
```

**Frontend Action:** Show DBS decanting screen with pre-reading data, awaiting post-reading.

#### Case 3: Both Readings Entered, Waiting for Confirmation
```json
{
  "dbs_pre_reading_done": true,
  "dbs_post_reading_done": true,
  "dbs_waiting_confirmation": true
}
```

**Frontend Action:** Show "Waiting for DBS operator to confirm" status screen.

---

## Frontend Integration Guide

### App Launch Flow

```javascript
// 1. On app open, check for active trip
async function onAppLaunch() {
  const response = await fetch('/api/driver-trips/resume/', {
    method: 'GET',
    headers: { 'Authorization': `Bearer ${authToken}` }
  });

  const data = await response.json();

  if (data.hasActiveTrip) {
    // Navigate to appropriate screen based on currentStep
    navigateToStep(data.trip.currentStep, data.trip);
  } else {
    // Show home screen / available trips
    navigateToHome();
  }
}

// 2. Navigate to correct step
function navigateToStep(step, tripData) {
  switch(step) {
    case 0:
      navigateTo('Home');
      break;
    case 1:
      navigateTo('TripAccepted', { tripData });
      break;
    case 2:
      navigateTo('ArrivedAtMS', { tripData });
      break;
    case 3:
      navigateTo('MSFilling', {
        tripData,
        preReadingDone: tripData.stepData.ms_pre_reading_done,
        postReadingDone: tripData.stepData.ms_post_reading_done,
        msFillingData: tripData.msFillingData
      });
      break;
    case 4:
      navigateTo('HeadingToDBS', { tripData });
      break;
    case 5:
      navigateTo('DBSDecanting', {
        tripData,
        preReadingDone: tripData.stepData.dbs_pre_reading_done,
        postReadingDone: tripData.stepData.dbs_post_reading_done,
        dbsDecantingData: tripData.dbsDecantingData
      });
      break;
    case 6:
      navigateTo('ReturningToMS', { tripData });
      break;
    case 7:
      navigateTo('TripCompleted', { tripData });
      break;
  }
}
```

### Pre-filling Form Data

```javascript
// Example: MS Filling Screen
function MSFillingScreen({ msFillingData, stepData }) {
  const [preReading, setPreReading] = useState(
    msFillingData?.prefill_pressure_bar || ''
  );
  const [postReading, setPostReading] = useState(
    msFillingData?.postfill_pressure_bar || ''
  );
  const [preMFM, setPreMFM] = useState(
    msFillingData?.prefill_mfm || ''
  );
  const [postMFM, setPostMFM] = useState(
    msFillingData?.postfill_mfm || ''
  );

  const [prePhoto, setPrePhoto] = useState(
    msFillingData?.prefill_photo_url || null
  );
  const [postPhoto, setPostPhoto] = useState(
    msFillingData?.postfill_photo_url || null
  );

  // Disable pre-reading fields if already completed
  const preReadingDisabled = stepData.ms_pre_reading_done;
  const postReadingDisabled = stepData.ms_post_reading_done;

  return (
    <View>
      <Text>MS Filling Process</Text>

      {/* Pre-Reading Section */}
      <TextInput
        value={preReading}
        onChangeText={setPreReading}
        placeholder="Pre-Fill Pressure"
        editable={!preReadingDisabled}
      />
      <TextInput
        value={preMFM}
        onChangeText={setPreMFM}
        placeholder="Pre-Fill MFM"
        editable={!preReadingDisabled}
      />
      {prePhoto && <Image source={{ uri: prePhoto }} />}

      {/* Post-Reading Section */}
      <TextInput
        value={postReading}
        onChangeText={setPostReading}
        placeholder="Post-Fill Pressure"
        editable={!postReadingDisabled}
      />
      <TextInput
        value={postMFM}
        onChangeText={setPostMFM}
        placeholder="Post-Fill MFM"
        editable={!postReadingDisabled}
      />
      {postPhoto && <Image source={{ uri: postPhoto }} />}

      {/* Confirmation Button */}
      {stepData.ms_post_reading_done && !stepData.ms_filling_confirmed && (
        <Button title="Confirm Filling" onPress={confirmFilling} />
      )}
    </View>
  );
}
```

---

## Testing Scenarios

### Test Case 1: App Closed After Trip Acceptance

**Steps:**
1. Driver accepts trip
2. Close app
3. Reopen app

**Expected Result:**
- Resume API returns `currentStep: 1`
- App navigates to "Trip Accepted" screen
- Driver can continue to "Arrive at MS"

---

### Test Case 2: App Closed During MS Filling (Pre-Reading Done)

**Steps:**
1. Driver accepts trip
2. Driver arrives at MS
3. MS operator enters pre-reading (pressure: 200, MFM: 1000)
4. Close app
5. Reopen app

**Expected Result:**
- Resume API returns `currentStep: 3`
- Step data shows: `ms_pre_reading_done: true`
- MS Filling screen shows pre-filled values (200, 1000)
- Post-reading fields are empty and editable
- Driver/operator can continue with post-reading

---

### Test Case 3: App Closed After Both Readings, Before Confirmation

**Steps:**
1. Complete pre-reading and post-reading
2. Close app before clicking "Confirm"
3. Reopen app

**Expected Result:**
- Resume API returns `currentStep: 3`
- Step data shows: `ms_pre_reading_done: true`, `ms_post_reading_done: true`
- All readings are pre-filled
- "Confirm Filling" button is visible
- Clicking confirm moves to Step 4

---

### Test Case 4: App Closed During DBS Decanting

**Steps:**
1. Complete MS process, travel to DBS
2. DBS operator enters pre-decant reading
3. Close app
4. Reopen app

**Expected Result:**
- Resume API returns `currentStep: 5`
- Step data shows: `dbs_pre_reading_done: true`
- DBS Decanting screen shows pre-filled pre-decant values
- Post-decant fields are empty

---

## Backward Compatibility

### Existing Trips Without Step Tracking

**Problem:** Trips created before this feature will have `current_step = 0` and empty `step_data`.

**Solution:** The `calculate_current_step()` method acts as a fallback:

```python
def get_step_details(self):
    # Always calculate step based on current state
    step = self.calculate_current_step()

    # If current_step in DB is 0 but calculated step is higher,
    # the calculated value takes precedence
    ...
```

**Manual Migration (Optional):**

To backfill existing active trips:

```python
# Django management command or script
from logistics.models import Trip

active_trips = Trip.objects.filter(
    status__in=['PENDING', 'AT_MS', 'IN_TRANSIT', 'AT_DBS', 'DECANTING_CONFIRMED']
)

for trip in active_trips:
    calculated_step = trip.calculate_current_step()
    if trip.current_step != calculated_step:
        trip.current_step = calculated_step
        trip.save()
        print(f"Updated Trip {trip.id}: Step {calculated_step}")
```

---

## Benefits

✅ **Seamless User Experience:** Drivers can resume trips without re-entering data
✅ **Data Integrity:** Partial readings (pre but not post) are preserved
✅ **No Workflow Disruption:** Existing APIs work unchanged, new fields are additive
✅ **Backward Compatible:** Old trips without step tracking still function correctly
✅ **Automatic Recovery:** `calculate_current_step()` provides failsafe logic
✅ **Photo Preservation:** Uploaded images are retained in MSFilling/DBSDecanting tables

---

## Future Enhancements

### Potential Improvements:

1. **Trip Timeout Handling:**
   - Add automatic trip cancellation if `last_activity_at` is older than X hours
   - Notify driver of stale trip when reopening app

2. **Offline Mode Support:**
   - Cache step data locally on device
   - Sync with backend when connectivity restored

3. **Step History Tracking:**
   - Log each step transition with timestamp
   - Useful for analytics and trip duration analysis

4. **Driver-Initiated Resume:**
   - Add "Resume Last Trip" button on home screen
   - Show trip summary before resuming

5. **Multi-Trip Support:**
   - Handle edge case where driver has multiple incomplete trips
   - Show list of active trips to choose from

---

## Troubleshooting

### Issue: Resume API Returns `currentStep: 0` Despite Active Trip

**Cause:** Trip status is not in the active status list

**Solution:** Check trip status and add to filter if needed:

```python
active_trip = Trip.objects.filter(
    driver=driver,
    status__in=['PENDING', 'AT_MS', 'IN_TRANSIT', 'AT_DBS', 'DECANTING_CONFIRMED']
).first()
```

---

### Issue: Step Data Not Updating

**Cause:** Code not using spread operator to merge step_data

**Incorrect:**
```python
trip.step_data = {'ms_pre_reading_done': True}  # Overwrites existing data!
```

**Correct:**
```python
trip.step_data = {**trip.step_data, 'ms_pre_reading_done': True}  # Merges data
```

---

### Issue: Photos Not Appearing in Resume Response

**Cause:** Photo field is None or file doesn't exist

**Solution:** Check if photo exists before accessing URL:

```python
'prefill_photo_url': ms_filling.prefill_photo.url if ms_filling.prefill_photo else None
```

---

## Operator Resume APIs

In addition to the driver resume functionality, MS and DBS operators also need to retrieve partial filling/decanting data when they reopen their apps. This prevents data loss if an operator closes the app after entering pre-readings.

### MS Operator Resume API

#### `POST /api/ms/fill/resume`

**Purpose:** Retrieve current MS filling state when operator reopens app

**Request:**
```json
{
  "tripToken": "A1B2C3D4E5F6"
}
```

**Response (Has Filling Data):**
```json
{
  "hasFillingData": true,
  "tripToken": "A1B2C3D4E5F6",
  "trip": {
    "id": 123,
    "status": "FILLING",
    "currentStep": 3,
    "stepData": {
      "trip_accepted": true,
      "arrived_at_ms": true,
      "ms_pre_reading_done": true
    },
    "vehicle": {
      "registrationNo": "ABC-1234",
      "capacity_kg": "5000.00"
    },
    "driver": {
      "name": "John Driver"
    },
    "route": {
      "from": "Mother Station Alpha",
      "to": "DBS Beta"
    }
  },
  "fillingData": {
    "id": 789,
    "prefill_pressure_bar": "200.00",
    "prefill_mfm": "1000.00",
    "postfill_pressure_bar": null,
    "postfill_mfm": null,
    "filled_qty_kg": null,
    "prefill_photo_url": "/media/ms_fillings/pre/reading_123_MS_pre_a1b2c3.jpg",
    "postfill_photo_url": null,
    "confirmed_by_ms_operator": false,
    "start_time": "2025-12-09T10:45:00Z",
    "end_time": null,
    "has_prefill_data": true,
    "has_postfill_data": false,
    "is_complete": false
  }
}
```

**Response (No Filling Data Yet):**
```json
{
  "hasFillingData": false,
  "tripToken": "A1B2C3D4E5F6",
  "trip": {
    "id": 123,
    "status": "AT_MS",
    "currentStep": 2,
    "vehicle": {
      "registrationNo": "ABC-1234",
      "capacity_kg": "5000.00"
    },
    "driver": {
      "name": "John Driver"
    },
    "route": {
      "from": "Mother Station Alpha",
      "to": "DBS Beta"
    }
  }
}
```

**Use Case:**
- MS operator enters pre-reading (pressure: 200, MFM: 1000)
- Operator closes app
- Upon reopening, call resume API with tripToken
- Display pre-filled values in form
- Operator can continue with post-reading

---

### DBS Operator Resume API

#### `POST /api/dbs/stock-requests/decant/resume`

**Purpose:** Retrieve current DBS decanting state when operator reopens app

**Request:**
```json
{
  "tripToken": "A1B2C3D4E5F6"
}
```

**Response (Has Decanting Data):**
```json
{
  "hasDecantingData": true,
  "tripToken": "A1B2C3D4E5F6",
  "trip": {
    "id": 123,
    "status": "AT_DBS",
    "currentStep": 5,
    "stepData": {
      "arrived_at_dbs": true,
      "dbs_pre_reading_done": true
    },
    "vehicle": {
      "registrationNo": "ABC-1234",
      "capacity_kg": "5000.00"
    },
    "driver": {
      "name": "John Driver"
    },
    "route": {
      "from": "Mother Station Alpha",
      "to": "DBS Beta"
    }
  },
  "decantingData": {
    "id": 890,
    "pre_dec_pressure_bar": "250.00",
    "pre_dec_reading": "6000.00",
    "post_dec_pressure_bar": null,
    "post_dec_reading": null,
    "delivered_qty_kg": null,
    "pre_decant_photo_url": "/media/dbs_decantings/pre/reading_123_DBS_pre_x1y2z3.jpg",
    "post_decant_photo_url": null,
    "confirmed_by_dbs_operator": false,
    "start_time": "2025-12-09T12:15:00Z",
    "end_time": null,
    "has_pre_decant_data": true,
    "has_post_decant_data": false,
    "is_complete": false
  }
}
```

**Response (No Decanting Data Yet):**
```json
{
  "hasDecantingData": false,
  "tripToken": "A1B2C3D4E5F6",
  "trip": {
    "id": 123,
    "status": "AT_DBS",
    "currentStep": 5,
    "vehicle": {
      "registrationNo": "ABC-1234",
      "capacity_kg": "5000.00"
    },
    "driver": {
      "name": "John Driver"
    },
    "route": {
      "from": "Mother Station Alpha",
      "to": "DBS Beta"
    }
  }
}
```

**Use Case:**
- DBS operator enters pre-decant reading (pressure: 250, MFM: 6000)
- Operator closes app
- Upon reopening, call resume API with tripToken
- Display pre-filled values in form
- Operator can continue with post-decant reading

---

### Operator App Integration Example

```javascript
// MS Operator App - On App Launch
async function onMSOperatorAppLaunch(tripToken) {
  const response = await fetch('/api/ms/fill/resume', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${authToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ tripToken })
  });

  const data = await response.json();

  if (data.hasFillingData) {
    // Pre-fill form with existing data
    const { fillingData } = data;

    setPreFillPressure(fillingData.prefill_pressure_bar || '');
    setPreFillMFM(fillingData.prefill_mfm || '');
    setPostFillPressure(fillingData.postfill_pressure_bar || '');
    setPostFillMFM(fillingData.postfill_mfm || '');

    // Disable fields that already have data
    setPreFieldsDisabled(fillingData.has_prefill_data);

    // Show appropriate UI state
    if (fillingData.is_complete) {
      showCompletionScreen();
    } else if (fillingData.has_postfill_data) {
      showConfirmButton();
    } else if (fillingData.has_prefill_data) {
      showPostReadingForm();
    } else {
      showPreReadingForm();
    }
  } else {
    // No data yet, show fresh form
    showPreReadingForm();
  }
}

// DBS Operator App - On App Launch
async function onDBSOperatorAppLaunch(tripToken) {
  const response = await fetch('/api/dbs/stock-requests/decant/resume', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${authToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ tripToken })
  });

  const data = await response.json();

  if (data.hasDecantingData) {
    // Pre-fill form with existing data
    const { decantingData } = data;

    setPreDecantPressure(decantingData.pre_dec_pressure_bar || '');
    setPreDecantReading(decantingData.pre_dec_reading || '');
    setPostDecantPressure(decantingData.post_dec_pressure_bar || '');
    setPostDecantReading(decantingData.post_dec_reading || '');

    // Disable fields that already have data
    setPreFieldsDisabled(decantingData.has_pre_decant_data);

    // Show appropriate UI state
    if (decantingData.is_complete) {
      showCompletionScreen();
    } else if (decantingData.has_post_decant_data) {
      showConfirmButton();
    } else if (decantingData.has_pre_decant_data) {
      showPostDecantForm();
    } else {
      showPreDecantForm();
    }
  } else {
    // No data yet, show fresh form
    showPreDecantForm();
  }
}
```

---

## API Endpoint Summary

| Endpoint | Method | Purpose | Updates Step |
|----------|--------|---------|--------------|
| `/api/driver-trips/accept/` | POST | Accept trip | Step 1 |
| `/api/driver-trips/arrival/ms/` | POST | Arrive at MS | Step 2 |
| `/api/ms/fill/start` | POST | MS start filling | Step 3 |
| `/api/ms/fill/end` | POST | MS end filling | Step 3 |
| `/api/ms/fill/confirm` | POST | MS confirm filling | Step 4 |
| `/api/driver-trips/meter-reading/confirm/` | POST | Driver meter reading (MS/DBS) | Step 3 or 5 |
| `/api/driver-trips/arrival/dbs/` | POST | Arrive at DBS | Step 5 |
| `/api/dbs/stock-requests/decant/start` | POST | DBS start decanting | Step 5 |
| `/api/dbs/stock-requests/decant/end` | POST | DBS end decanting | Step 5 |
| `/api/dbs/stock-requests/decant/confirm` | POST | DBS confirm decanting | Step 6 |
| **`/api/driver-trips/resume/`** | **GET** | **Resume driver trip state** | **N/A (Read-only)** |
| **`/api/ms/fill/resume`** | **POST** | **Resume MS filling state** | **N/A (Read-only)** |
| **`/api/dbs/stock-requests/decant/resume`** | **POST** | **Resume DBS decanting state** | **N/A (Read-only)** |

---

## Conclusion

The Driver Trip Step Persistence feature ensures that driver and operator app states are preserved across app restarts, providing a robust and user-friendly experience. The implementation includes:

- **Driver Resume API**: Allows drivers to resume trips from where they left off
- **MS Operator Resume API**: Allows MS operators to retrieve partial filling data (pre/post readings)
- **DBS Operator Resume API**: Allows DBS operators to retrieve partial decanting data (pre/post readings)

All implementations are backward compatible, require no changes to existing workflows, and provide comprehensive step tracking with partial data preservation. Photos, readings, and confirmation states are all preserved across app sessions.

For questions or issues, please contact the development team.

---

**Document Version:** 1.1
**Last Updated:** December 9, 2025
**Author:** Development Team
