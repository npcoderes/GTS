# MS Bay Management API Documentation

**Implementation Date**: 2026-01-08  
**Feature**: Dynamic bay management for MS (Mother Station) filling operations

---

## Overview

This feature adds dynamic bay tracking to MS stations, allowing control over how many trucks can fill simultaneously.

### Key Concepts

| Term | Description |
|------|-------------|
| **Bay** | A filling spot at MS station |
| **Occupied Bay** | A truck is actively filling (prefill submitted, not yet confirmed) |
| **Free Bay** | Available for next truck |
| **can_fill** | Flag indicating if truck is allowed to start filling |

---

## Database Changes

### Station Model - New Field

```python
# core/models.py - Station class

no_of_bays = models.PositiveIntegerField(
    default=2,
    verbose_name='Number of Bays',
    help_text='Number of filling bays available at this station (MS only).',
)
```

**Migration**: `core/migrations/XXXX_add_station_no_of_bays.py`

---

## API Endpoint Changes

### POST `/api/ms/fill/resume`

This endpoint has two modes:
1. **Without tripToken/tripId**: Returns list of trucks at MS
2. **With tripToken/tripId**: Returns specific trip details

---

## MODE 1: Truck List Response

### BEFORE (Old Response)

```json
{
  "trucks": [
    {
      "tripId": 123,
      "tripToken": "ABC123",
      "vehicleNumber": "GJ01AB1234",
      "currentStep": "arrived",
      "scada_available": true,
      "driverName": "John Doe",
      "dbsName": "DBS Station A",
      "status": "AT_MS"
    }
  ],
  "ms_no_bays": 2,
  "scada_available": true,
  "station": {
    "id": 1,
    "name": "MS Station 1",
    "code": "MS001"
  }
}
```

### AFTER (New Response)

```json
{
  "trucks": [
    {
      "tripId": 123,
      "tripToken": "ABC123",
      "vehicleNumber": "GJ01AB1234",
      "currentStep": "arrived",
      "scada_available": true,
      "driverName": "John Doe",
      "dbsName": "DBS Station A",
      "status": "AT_MS",
      "token_sequence": 1,
      "is_filling": false,
      "can_fill": true
    },
    {
      "tripId": 124,
      "tripToken": "DEF456",
      "vehicleNumber": "GJ01CD5678",
      "currentStep": "filling",
      "scada_available": true,
      "driverName": "Jane Smith",
      "dbsName": "DBS Station B",
      "status": "AT_MS",
      "token_sequence": 2,
      "is_filling": true,
      "can_fill": true
    }
  ],
  "bay_status": {
    "total_bays": 2,
    "occupied_bays": 1,
    "free_bays": 1
  },
  "scada_available": true,
  "station": {
    "id": 1,
    "name": "MS Station 1",
    "code": "MS001"
  }
}
```

### New Fields Explained

| Field | Type | Description |
|-------|------|-------------|
| `bay_status.total_bays` | int | Total bays at this MS (from `station.no_of_bays`) |
| `bay_status.occupied_bays` | int | Currently occupied bays |
| `bay_status.free_bays` | int | Available bays (total - occupied) |
| `trucks[].token_sequence` | int | Queue position (lower = arrived earlier) |
| `trucks[].is_filling` | bool | `true` if truck is currently occupying a bay |
| `trucks[].can_fill` | bool | `true` if truck can start filling |

### Sorting

Trucks are now sorted by:
1. `token_sequence` (ascending) - First arrived first
2. `origin_confirmed_at` (descending)
3. `created_at` (descending)

---

## MODE 2: Single Trip Response

### BEFORE (Old Response - No Filling Data)

```json
{
  "tripId": 123,
  "hasFillingData": false,
  "ms_no_bays": 2,
  "tripToken": "ABC123",
  "vehicleNumber": "GJ01AB1234",
  "ms_arrival_confirmed": true,
  "scada_available": true,
  "prefill_scada_reading": null
}
```

### AFTER (New Response - No Filling Data)

```json
{
  "tripId": 123,
  "hasFillingData": false,
  "bay_status": {
    "total_bays": 2,
    "occupied_bays": 1,
    "free_bays": 1
  },
  "tripToken": "ABC123",
  "vehicleNumber": "GJ01AB1234",
  "ms_arrival_confirmed": true,
  "scada_available": true,
  "prefill_scada_reading": null
}
```

### BEFORE (Old Response - With Filling Data)

```json
{
  "tripId": 123,
  "hasFillingData": true,
  "ms_no_bays": 2,
  "tripToken": "ABC123",
  "vehicleNumber": "GJ01AB1234",
  "ms_arrival_confirmed": true,
  "scada_available": true,
  "prefill_scada_reading": "1500.50",
  "fillingData": { ... }
}
```

### AFTER (New Response - With Filling Data)

```json
{
  "tripId": 123,
  "hasFillingData": true,
  "bay_status": {
    "total_bays": 2,
    "occupied_bays": 2,
    "free_bays": 0
  },
  "tripToken": "ABC123",
  "vehicleNumber": "GJ01AB1234",
  "ms_arrival_confirmed": true,
  "scada_available": true,
  "prefill_scada_reading": "1500.50",
  "fillingData": { ... }
}
```

---

## POST `/api/ms/arrival/confirm` - Bay Validation

### New Validation

Before allowing the MS operator to confirm a truck's arrival, the API now checks bay availability:

```python
# Check bay availability before confirming arrival
if free_bays <= 0:
    return validation_error_response(
        'All filling bays are currently occupied. Please wait for a bay to become available.'
    )
```

### Error Response (All Bays Occupied)

```json
{
  "success": false,
  "error": "All filling bays are currently occupied. Please wait for a bay to become available."
}
```

### Bypass Conditions

The validation is **skipped** if:
- Truck status is not moving to `AT_MS` (e.g. force update on already confirmed trip)

---

## Bay Lifecycle

```
┌────────────────────────────────────────────────────────────────┐
│                       BAY STATUS FLOW                          │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│   Truck Arrives at MS                                          │
│         │                                                      │
│         ▼                                                      │
│   ┌─────────────────┐                                          │
│   │ is_filling=false│  Bay NOT occupied                        │
│   │ can_fill=true   │  (if free bays > 0)                      │
│   └────────┬────────┘                                          │
│            │                                                   │
│            ▼  Prefill Submitted                                │
│   ┌─────────────────┐                                          │
│   │ is_filling=true │  Bay OCCUPIED                            │
│   │ can_fill=true   │                                          │
│   └────────┬────────┘                                          │
│            │                                                   │
│            ▼  Postfill Submitted                               │
│   ┌─────────────────┐                                          │
│   │ is_filling=true │  Bay still OCCUPIED                      │
│   │ can_fill=true   │                                          │
│   └────────┬────────┘                                          │
│            │                                                   │
│            ▼  MS Operator Confirms                             │
│   ┌─────────────────┐                                          │
│   │ is_filling=false│  Bay FREED                               │
│   │ can_fill=n/a    │  (truck leaving)                         │
│   └─────────────────┘                                          │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## Code Reference

### get_bay_status Method

**File**: `logistics/ms_views.py`  
**Class**: `MSFillResumeView`  
**Lines**: 296-320

```python
def get_bay_status(self, ms):
    """
    Calculate occupied and free bays for an MS station.
    
    Occupied = Trips with MSFilling created (prefill submitted) 
               but NOT confirmed by MS operator.
    """
    occupied_count = MSFilling.objects.filter(
        trip__ms=ms,
        trip__status__in=['PENDING', 'AT_MS'],
        confirmed_by_ms_operator__isnull=True,
    ).exclude(
        prefill_mfm__isnull=True,
        prefill_pressure_bar__isnull=True,
    ).count()
    
    total_bays = getattr(ms, 'no_of_bays', 2) or 2
    free_bays = max(0, total_bays - occupied_count)
    
    return {
        'total_bays': total_bays,
        'occupied_bays': occupied_count,
        'free_bays': free_bays,
    }
```

---

## Mobile App Integration Notes

### UI Changes Required

1. **Truck List Screen**:
   - Show bay status header: "Bays: 1/2 available"
   - Disable "Start Filling" button when `can_fill=false`
   - Show badge/indicator for trucks with `is_filling=true`
   - Sort trucks by `token_sequence`

2. **Filling Screen**:
   - Handle new error response when bays full
   - Show waiting message: "All bays occupied. Please wait..."

3. **Badge Colors**:
   - `is_filling=true`: Blue (In Progress)
   - `can_fill=false`: Gray (Waiting)
   - `can_fill=true`: Green (Ready)

---

## Admin Dashboard Notes

To change number of bays for a station:

1. Go to Station Management
2. Edit MS station
3. Change "Number of Bays" field
4. Save

Default: 2 bays per MS station
