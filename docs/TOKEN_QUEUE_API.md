# Token Queue System Documentation

## Overview

The Token Queue System manages driver queue positions at Mother Stations (MS). When drivers arrive at an MS, they request a token to enter the queue for trip allocation.

---

## Current Flow

### 1. Driver Requests Token
- Driver arrives at MS and calls `/api/driver/token/request` with `ms_id`
- System validates:
  - Driver has an active shift
  - Driver/Vehicle is not on an active trip
- **If driver already has a WAITING or ALLOCATED token for today → Returns existing token**
- Otherwise, token is created with a `sequence_number` (incremental for the day)
- If an approved stock request exists → Token is auto-allocated

### 2. Token Status
| Status | Description |
|--------|-------------|
| `WAITING` | Driver is waiting in queue for a trip |
| `ALLOCATED` | Token has been matched to a stock request |
| `EXPIRED` | Token was cancelled, shift ended, or **trip completed** |

### 3. Allocation Flow
- When EIC approves a stock request → System checks for waiting tokens
- First WAITING token (by sequence_number) gets allocated
- Driver receives notification about trip offer
- Driver accepts/rejects the trip

### 4. Trip Completion Flow
- Driver completes trip and returns to MS
- Calls `/api/driver/trip/complete`
- **VehicleToken is marked as EXPIRED** (expiry_reason: 'TRIP_COMPLETED')
- Driver can now request a new token for the next trip

---

## API Endpoints

### Request Token
```
POST /api/driver/token/request
Authorization: TOKEN <driver_token>

Payload:
{
    "ms_id": 123
}

Response (Success - Waiting):
{
    "success": true,
    "token": {
        "id": 1,
        "token_no": "MS5-20260106-0001",
        "sequence_number": 1,
        "status": "WAITING",
        "issued_at": "2026-01-06T10:00:00+05:30",
        "ms_id": 5,
        "ms_name": "MS Mumbai"
    }
}

Response (Success - Auto-Allocated):
{
    "success": true,
    "token": {
        "id": 1,
        "token_no": "MS5-20260106-0001",
        "sequence_number": 1,
        "status": "ALLOCATED",
        "issued_at": "2026-01-06T10:00:00+05:30",
        "ms_id": 5,
        "ms_name": "MS Mumbai",
        "allocated_at": "2026-01-06T10:00:01+05:30"
    }
}

Note: If driver already has an active token, the existing token is returned instead of creating a new one.

Error Responses:
- 400: NO_ACTIVE_SHIFT - Driver has no active shift
- 400: Driver or Vehicle is currently on an active trip
```

### Get Current Token
```
GET /api/driver/token/current
Authorization: TOKEN <driver_token>

Response (Has Token):
{
    "has_token": true,
    "token": {
        "id": 1,
        "token_no": "MS5-20260106-0001",
        "sequence_number": 1,
        "status": "WAITING",
        "ms_name": "MS Mumbai"
    }
}

Response (No Token):
{
    "has_token": false
}
```

### Cancel Token
```
POST /api/driver/token/cancel
Authorization: TOKEN <driver_token>

Payload (optional):
{
    "token_id": 123
}

Response:
{
    "success": true,
    "message": "Token cancelled"
}
```

---

## Data Model

### VehicleToken
| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Primary key |
| `token_no` | String | Format: MS{ms_id}-{date}-{sequence} |
| `sequence_number` | Integer | Queue position assigned at creation time |
| `status` | Enum | WAITING, ALLOCATED, EXPIRED |
| `driver` | FK | Driver who requested the token |
| `vehicle` | FK | Vehicle associated with the token |
| `ms` | FK | Mother Station |
| `shift` | FK | Shift at the time of token request |
| `token_date` | Date | Date the token was issued |
| `issued_at` | DateTime | When token was created |
| `allocated_at` | DateTime | When token was allocated to a trip |
| `expired_at` | DateTime | When token was expired/cancelled |
| `expiry_reason` | String | Reason for expiration (CANCELLED, SHIFT_ENDED, TRIP_COMPLETED) |
| `trip` | FK (OneToOne) | Trip assigned (after driver accepts) |

---

## Current Behavior: sequence_number

Currently, `sequence_number` is a **FIXED** number assigned when the token is created:

| Driver | Token Time | sequence_number | After Driver A is allocated |
|--------|------------|-----------------|----------------------------|
| Driver A | 10:00 AM | 1 | ALLOCATED (still 1) |
| Driver B | 10:05 AM | 2 | Still shows 2 |
| Driver C | 10:10 AM | 3 | Still shows 3 |

**Note:** Driver B's `sequence_number` stays as 2 even after Driver A is allocated/gone.

---

## Future Enhancement: Dynamic Queue Position

### Problem
The current `sequence_number` doesn't reflect the actual queue position when other drivers get allocated or leave the queue.

### Proposed Solution
Calculate queue position dynamically when returning API responses:

```python
# Count how many WAITING tokens are ahead of this one
queue_position = VehicleToken.objects.filter(
    ms=token.ms,
    status='WAITING',
    sequence_number__lt=token.sequence_number,
    token_date=today
).count() + 1
```

### Expected Behavior After Implementation

| Driver | sequence_number | After Driver A is allocated |
|--------|-----------------|----------------------------|
| Driver A | 1 | ALLOCATED |
| Driver B | 2 | `queue_position` = **1** |
| Driver C | 3 | `queue_position` = **2** |

### Updated Response Format (Future)
```json
{
    "has_token": true,
    "token": {
        "id": 1,
        "token_no": "MS5-20260106-0001",
        "sequence_number": 2,
        "queue_position": 1,
        "status": "WAITING",
        "ms_name": "MS Mumbai"
    }
}
```

### Implementation Checklist
- [ ] Add `queue_position` calculation to `/api/driver/token/request` response
- [ ] Add `queue_position` calculation to `/api/driver/token/current` response
- [ ] Update shift_details endpoint if needed
- [ ] Update mobile app to display `queue_position` instead of `sequence_number`
- [ ] Consider WebSocket/Push notification when queue position changes

---

## Related Files

- `logistics/token_views.py` - Token API endpoints
- `logistics/token_queue_service.py` - Token queue business logic
- `logistics/views.py` - Trip completion (TripCompleteView)
- `logistics/models.py` - VehicleToken model
- `TOKEN_QUEUE_SYSTEM.md` - Original system documentation

---

## Changelog

### 2026-01-07 (Update 2)
- **Request Token now returns existing token** if driver already has WAITING/ALLOCATED token for today
- Removed `TOKEN_EXISTS` error - now returns existing token instead
- **Trip completion now expires the VehicleToken** with `expiry_reason='TRIP_COMPLETED'`
- Driver can request a new token after completing a trip

### 2026-01-07 (Update 1)
- Simplified token request response (removed `queue_position`, `message`, `trip_offer`)
- Simplified current token response (removed `issued_at`, `ms_id`, trip details)
- `sequence_number` is now used as the queue number (fixed, not dynamic)
- Documented future enhancement for dynamic queue position

