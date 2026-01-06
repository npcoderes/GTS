# Token Queue System Documentation

**Created:** 2026-01-06  
**Feature:** Vehicle Token Queue with Auto-Allocation

---

## Overview

The Token Queue System manages vehicle queues at Mother Stations (MS). Drivers request tokens when arriving at MS, creating a FCFS (First-Come, First-Served) queue. When EIC approves stock requests, the system automatically allocates the first waiting token to the first approved request.

---

## Key Concepts

### Token Lifecycle
1. **WAITING** - Driver has token, waiting for stock request
2. **ALLOCATED** - Token matched to stock request, trip created
3. **EXPIRED** - Token cancelled or shift ended

### Daily Sequence Reset
- Token numbers reset each day at midnight
- Format: `MS{ms_id}-{YYYYMMDD}-{0001}`
- Example: `MS5-20260106-0001`

### Shift Enforcement
- Token request requires active APPROVED shift
- Trip acceptance requires active shift
- **Once trip starts, it can continue even if shift expires**

---

## API Endpoints

### Driver Token APIs

#### Request Token
```
POST /api/driver/token/request
Authorization: Bearer <driver_token>

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
    },
    "message": "Token issued. Waiting for stock request allocation.",
    "queue_position": 1
}

Response (Success - Auto-Allocated):
{
    "success": true,
    "token": {
        "id": 1,
        "token_no": "MS5-20260106-0001",
        "status": "ALLOCATED",
        "allocated_at": "2026-01-06T10:00:01+05:30"
    },
    "trip": {
        "id": 456,
        "dbs_id": 10,
        "dbs_name": "DBS Thane",
        "status": "PENDING"
    },
    "message": "Token allocated to trip immediately"
}

Error Responses:
- 400: NO_ACTIVE_SHIFT - Driver has no active shift
- 400: TOKEN_EXISTS - Driver already has waiting token
```

#### Get Current Token
```
GET /api/driver/token/current
Authorization: Bearer <driver_token>

Response:
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
```

#### Cancel Token
```
POST /api/driver/token/cancel
Authorization: Bearer <driver_token>

Payload (optional):
{
    "token_id": 123  // If omitted, cancels current token
}

Response:
{
    "success": true,
    "message": "Token MS5-20260106-0001 cancelled"
}
```

---

### EIC Queue APIs

#### View Queue Status
```
GET /api/eic/token-queue
GET /api/eic/token-queue?ms_id=5
Authorization: Bearer <eic_token>

Response (Single MS):
{
    "ms_id": 5,
    "ms_name": "MS Mumbai",
    "date": "2026-01-06",
    "waiting_tokens": [
        {
            "token_no": "MS5-20260106-0001",
            "sequence": 1,
            "driver_id": 10,
            "driver_name": "Rajesh Kumar",
            "vehicle_reg": "MH12AB1234",
            "issued_at": "2026-01-06T10:00:00+05:30"
        }
    ],
    "pending_requests": [
        {
            "id": 789,
            "dbs_id": 10,
            "dbs_name": "DBS Thane",
            "requested_qty": "500.00",
            "approved_at": "2026-01-06T09:55:00+05:30",
            "priority": "N"
        }
    ],
    "waiting_count": 1,
    "pending_count": 1
}

Response (All MS):
{
    "queues": [...],
    "total_waiting": 5,
    "total_pending": 3
}
```

#### Manual Allocation (Override FCFS)
```
POST /api/eic/token-queue/allocate
Authorization: Bearer <eic_token>

Payload:
{
    "token_id": 1,
    "stock_request_id": 789
}

Response:
{
    "success": true,
    "message": "Manual allocation successful",
    "trip_id": 456,
    "token_no": "MS5-20260106-0001",
    "driver_name": "Rajesh Kumar",
    "dbs_name": "DBS Thane"
}
```

---

## Database Changes

### New Model: VehicleToken
```python
class VehicleToken(models.Model):
    vehicle = ForeignKey(Vehicle)
    driver = ForeignKey(Driver)
    ms = ForeignKey(Station)
    shift = ForeignKey(Shift)  # Active shift at token request
    
    token_no = CharField(unique=True)  # MS{id}-{date}-{seq}
    sequence_number = PositiveIntegerField()
    token_date = DateField()
    
    status = CharField(choices=['WAITING', 'ALLOCATED', 'EXPIRED'])
    issued_at = DateTimeField(auto_now_add=True)
    allocated_at = DateTimeField(null=True)
    expired_at = DateTimeField(null=True)
    expiry_reason = CharField(null=True)
    
    trip = OneToOneField(Trip, null=True)  # Created when allocated
```

### Updated: StockRequest
Added fields:
- `queue_position` - FCFS ordering position
- `approved_at` - Timestamp when EIC approved
- `approved_by` - FK to User who approved
- `allocated_vehicle_token` - FK to VehicleToken when matched

---

## Files Changed/Created

| File | Action | Purpose |
|------|--------|---------|
| `logistics/models.py` | Modified | Added `VehicleToken` model, queue fields to `StockRequest` |
| `logistics/token_queue_service.py` | **New** | Token generation, queue matching, auto-allocation |
| `logistics/token_views.py` | **New** | API endpoints for driver and EIC |
| `logistics/urls.py` | Modified | Added token and queue routes |
| `logistics/eic_views.py` | Modified | Updated `approve()` to trigger auto-allocation |
| `migrations/0030_token_queue_system.py` | **New** | Database migration |

---

## Flow Diagrams

### Token Request Flow
```
Driver → POST /driver/token/request
    ↓
Validate Active Shift
    ↓
Generate Sequential Token (WAITING)
    ↓
Check for APPROVED StockRequests
    ↓
    ├─ Request Found → Auto-Allocate → Create Trip → Status: ALLOCATED
    └─ No Request → Stay in Queue → Status: WAITING
```

### Stock Request Approval Flow
```
EIC → POST /eic/stock-requests/{id}/approve
    ↓
Update StockRequest (APPROVED, approved_at, approved_by)
    ↓
Check for WAITING Tokens at MS
    ↓
    ├─ Token Found → Auto-Allocate → Create Trip → Return trip_id
    └─ No Token → Queue Request → Return "Waiting for vehicle"
```

---

## Configuration

No new environment variables required. Uses existing shift timeout and notification settings.

---

## Testing

### Manual Test Steps

1. **Setup**: Ensure driver has approved shift for current time
2. **Token Request**: Login as driver, call `/api/driver/token/request`
3. **Verify Queue**: Login as EIC, check `/api/eic/token-queue`
4. **Approve Request**: Approve a pending stock request
5. **Verify Allocation**: Check token status changed to ALLOCATED, trip created

### Run Django Tests
```powershell
cd c:\Users\userd\OneDrive\Desktop\SGL\backend
python manage.py test logistics.test_token_queue
```
