# SCADA Integration Implementation - Changes Summary

## Overview
Implemented station-level permission system for SCADA (Supervisory Control and Data Acquisition) capability. This allows defining which stations have SCADA integration enabled, and the relevant APIs now return SCADA availability flags.

## Changes Made

### 1. Permission Models (`core/permission_models.py`)
**Added new permission:**
```python
{
    'code': 'station_has_scada',
    'name': 'Station Has SCADA',
    'description': 'Station has SCADA integration enabled for automated meter readings',
    'category': 'stations',
    'platform': 'all'
}
```

### 2. Permission Views (`core/permission_views.py`)
**Added helper function:**
```python
def station_has_scada(station):
    """
    Check if a station has SCADA capability enabled.
    Returns True if the station has the 'station_has_scada' permission granted.
    """
```

### 3. MS Fill Resume API (`logistics/ms_views.py`)
**Endpoint:** `POST /api/ms/fill/resume`

**Two modes:**

**Mode 1: Without tripToken (Get Truck List)**
```json
POST /api/ms/fill/resume
Body: {}

Response:
{
  "trucks": [
    {
      "tripId": 101,
      "tripToken": "TOKEN_ABC",
      "vehicleNumber": "HR-12-AB-1234",
      "currentStep": "filling",
      "scada_available": true,
      "driverName": "John Doe",
      "dbsName": "DBS Station 1",
      "status": "AT_MS"
    }
  ],
  "scada_available": true,
  "station": {
    "id": 1,
    "name": "MS Station 1",
    "code": "MS001"
  }
}
```

**Mode 2: With tripToken (Get Truck Details)**
```json
POST /api/ms/fill/resume
Body: { "tripToken": "TOKEN_ABC" }

Response:
{
  "tripId": 101,
  "tripToken": "TOKEN_ABC",
  "vehicleNumber": "HR-12-AB-1234",
  "ms_arrival_confirmed": true,
  "hasFillingData": true,
  "scada_available": true,
  "prefill_scada_reading": "12345.678",
  "fillingData": { ... }
}
```

### 4. DBS Decant Resume API (`logistics/dbs_views.py`)
**Endpoint:** `POST /api/dbs/stock-requests/decant/resume`

**Two modes:**

**Mode 1: Without tripToken (Get Truck List)**
```json
POST /api/dbs/stock-requests/decant/resume
Body: {}

Response:
{
  "trucks": [
    {
      "tripId": 101,
      "tripToken": "TOKEN_ABC",
      "vehicleNumber": "HR-12-AB-1234",
      "currentStep": "decanting",
      "scada_available": true,
      "driverName": "John Doe",
      "msName": "MS Station 1",
      "status": "AT_DBS"
    }
  ],
  "scada_available": true,
  "station": {
    "id": 2,
    "name": "DBS Station 1",
    "code": "DBS001"
  }
}
```

**Mode 2: With tripToken (Get Truck Details)**
```json
POST /api/dbs/stock-requests/decant/resume
Body: { "tripToken": "TOKEN_ABC" }

Response:
{
  "tripId": 101,
  "tripToken": "TOKEN_ABC",
  "vehicleNumber": "HR-12-AB-1234",
  "dbs_arrival_confirmed": true,
  "hasDecantingData": true,
  "scada_available": true,
  "prefill_scada_reading": "12345.678",
  "decantingData": { ... }
}
```

### 5. New SCADA Fetch APIs (`logistics/scada_views.py`)
Created new file with 4 SCADA fetch endpoints (placeholder implementations ready for integration):

| API | Payload | Response |
|-----|---------|----------|
| `POST /api/ms/scada/prefill` | `{ "tripToken": "xxx" }` | `{ "mfm": "12345.678" }` |
| `POST /api/ms/scada/postfill` | `{ "tripToken": "xxx" }` | `{ "mfm": "12500.321" }` |
| `POST /api/dbs/scada/prefill` | `{ "tripToken": "xxx" }` | `{ "mfm": "12345.678" }` |
| `POST /api/dbs/scada/postfill` | `{ "tripToken": "xxx" }` | `{ "mfm": "12500.321" }` |

**Note:** These are placeholder implementations. When the client provides actual SCADA APIs, update the `fetch_scada_reading()` method in `BaseSCADAView` class to make HTTP requests to the client's SCADA endpoint.

### 6. URL Routes (`logistics/urls.py`)
Added routes for SCADA endpoints:
- `ms/scada/prefill`
- `ms/scada/postfill`
- `dbs/scada/prefill`
- `dbs/scada/postfill`

## How to Enable SCADA for a Station

### Option 1: Via Admin Dashboard
1. Go to Permission Management
2. Select Station Permissions tab
3. Find the target station (MS or DBS)
4. Enable the `station_has_scada` permission

### Option 2: Via API
```json
POST /api/station-permissions/bulk-update/
{
    "station_id": 1,
    "permissions": {
        "station_has_scada": true
    }
}
```

### Option 3: Via Django Admin or Shell
```python
from core.models import Station
from core.permission_models import Permission, StationPermission

station = Station.objects.get(code='MS001')
scada_perm = Permission.objects.get(code='station_has_scada')

StationPermission.objects.create(
    station=station,
    permission=scada_perm,
    granted=True
)
```

## Files Changed
1. `core/permission_models.py` - Added SCADA permission
2. `core/permission_views.py` - Added `station_has_scada()` helper
3. `logistics/ms_views.py` - Updated MSFillResumeView with SCADA fields
4. `logistics/dbs_views.py` - Updated decant_resume with SCADA fields
5. `logistics/scada_views.py` - **NEW** SCADA fetch views
6. `logistics/urls.py` - Added SCADA endpoint routes

## Testing
After running `python manage.py seed_permissions`, the new `station_has_scada` permission will be available in the system. Enable it for specific stations to test the SCADA functionality.

## Future Integration
When the client provides actual SCADA APIs, update `logistics/scada_views.py`:
1. Add SCADA API configuration to settings (base URL, API key, etc.)
2. Implement the actual HTTP call in `fetch_scada_reading()` method
3. Parse the response and return the MFM reading
