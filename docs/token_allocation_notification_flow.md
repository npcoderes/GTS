# Token Request with Auto-Allocation Notification Flow

## Overview
When a driver requests a token at an MS, if an approved stock request is available, the system:
1. **Auto-allocates** the token to the stock request
2. **Sends FCM notification** to the driver with trip details
3. **Returns API response** with trip offer details

---

## API Endpoint

**POST** `/api/driver/token/request`

### Request Payload
```json
{
  "ms_id": 3
}
```

### Response - Token Allocated (Trip Available)
```json
{
  "success": true,
  "message": "Token allocated! Trip offer available.",
  "token": {
    "id": 123,
    "token_no": "MS3-20260108-0007",
    "sequence_number": 7,
    "status": "ALLOCATED",
    "issued_at": "2026-01-08T18:21:47+05:30",
    "allocated_at": "2026-01-08T18:21:47+05:30",
    "ms_id": 3,
    "ms_name": "Mother Station 3"
  },
  "trip_offer": {
    "stock_request_id": 96,
    "ms": {
      "id": 3,
      "name": "Mother Station 3"
    },
    "dbs": {
      "id": 15,
      "name": "Arbuda Petroleum",
      "address": "123 Main St, City"
    },
    "quantity_kg": 5000.0,
    "priority": "HIGH",
    "message": "Trip offer: Mother Station 3 → Arbuda Petroleum. Tap to accept."
  }
}
```

### Response - Token Waiting (No Trip Yet)
```json
{
  "success": true,
  "message": "Token issued. You are #7 in queue.",
  "token": {
    "id": 123,
    "token_no": "MS3-20260108-0007",
    "sequence_number": 7,
    "status": "WAITING",
    "issued_at": "2026-01-08T18:21:47+05:30",
    "ms_id": 3,
    "ms_name": "Mother Station 3"
  }
}
```

---

## FCM Notification (Sent Automatically)

When token is auto-allocated, the system sends a push notification to the driver.

### Notification Payload
```json
{
  "notification": {
    "title": "New Trip Assignment",
    "body": "New trip offer: Mother Station 3 → Arbuda Petroleum. Tap to accept."
  },
  "data": {
    "type": "trip_assignment",
    "tripId": "",
    "stockRequestId": "96",
    "msName": "Mother Station 3",
    "dbsName": "Arbuda Petroleum",
    "tokenId": "123",
    "tokenNumber": "MS3-20260108-0007"
  }
}
```

### Notification Format Details
- **Title**: "New Trip Assignment"
- **Body**: "New trip offer: {MS Name} → {DBS Name}. Tap to accept."
- **Data**:
  - `type`: "trip_assignment" (for app routing)
  - `tripId`: Empty string (trip not created until driver accepts)
  - `stockRequestId`: ID of the stock request
  - `msName`: Mother Station name
  - `dbsName`: Daughter Booster Station name
  - `tokenId`: VehicleToken ID
  - `tokenNumber`: Token number (e.g., "MS3-20260108-0007")

---

## Complete Flow

### Scenario 1: Token Auto-Allocated (Trip Available)

```
1. Driver → POST /api/driver/token/request { "ms_id": 3 }
   ↓
2. System creates VehicleToken (status: WAITING)
   ↓
3. System checks for approved stock requests at MS3
   ↓
4. ✅ Approved request found!
   ↓
5. System allocates token to request:
   - VehicleToken.status → ALLOCATED
   - StockRequest.status → ASSIGNING
   - StockRequest.allocated_vehicle_token → token
   - StockRequest.target_driver → driver
   ↓
6. 📱 FCM Notification sent to driver:
   Title: "New Trip Assignment"
   Body: "New trip offer: MS3 → Arbuda Petroleum. Tap to accept."
   Data: { type: "trip_assignment", stockRequestId: "96", ... }
   ↓
7. API Response returned with trip_offer details
   ↓
8. Driver sees notification + API response with trip details
   ↓
9. Driver → POST /api/driver-trips/accept { "stock_request_id": 96 }
   ↓
10. Trip created, driver starts journey
```

### Scenario 2: Token Waiting (No Trip Yet)

```
1. Driver → POST /api/driver/token/request { "ms_id": 3 }
   ↓
2. System creates VehicleToken (status: WAITING)
   ↓
3. System checks for approved stock requests at MS3
   ↓
4. ❌ No approved requests found
   ↓
5. Token remains WAITING
   ↓
6. ❌ No notification sent (nothing to notify about)
   ↓
7. API Response: "Token issued. You are #7 in queue."
   ↓
8. Driver waits in queue...
   ↓
9. Later: EIC approves stock request
   ↓
10. System auto-allocates first waiting token
   ↓
11. 📱 FCM Notification sent to driver (same format as Scenario 1)
   ↓
12. Driver accepts trip
```

---

## Code Implementation

### 1. Token Request API
**File**: `backend/logistics/token_views.py`
- Enhanced to include `trip_offer` in response when allocated
- Provides immediate feedback to driver about available trip

### 2. Auto-Allocation Logic
**File**: `backend/logistics/token_queue_service.py`
- `_try_auto_allocate()` - Matches first waiting token with first approved request
- `_allocate_token_to_request()` - Performs allocation and sends notification

### 3. Notification Service
**File**: `backend/core/notification_service.py`
- `notify_trip_assignment()` - Sends FCM notification with trip details
- Fixed to use VehicleToken (not Token) when trip is None
- Includes proper MS/DBS names and token number

---

## Notification Consistency

Both allocation scenarios send **identical notification format**:

### When EIC Approves Request (Manual Allocation)
```python
# From: logistics/eic_views.py (stock request approval)
notification_service.notify_trip_assignment(
    driver=driver,
    trip=None,
    stock_request=stock_request
)
```

### When Driver Requests Token (Auto-Allocation)
```python
# From: logistics/token_queue_service.py (_allocate_token_to_request)
notification_service.notify_trip_assignment(
    driver=driver,
    trip=None,
    stock_request=stock_request
)
```

**Result**: Same notification format in both cases! ✅

---

## Testing

### Test Auto-Allocation Notification

1. **Setup**:
   - Create approved stock request for DBS under MS3
   - Ensure driver has active shift

2. **Request Token**:
   ```bash
   POST /api/driver/token/request
   {
     "ms_id": 3
   }
   ```

3. **Expected**:
   - ✅ API returns `trip_offer` object
   - ✅ FCM notification sent to driver
   - ✅ Notification includes MS/DBS names and token number
   - ✅ Log shows: "Auto-allocated: Token MS3-20260108-0007 → Request #96"

4. **Verify Notification**:
   - Check logs for: `"FCM notification sent: projects/..."`
   - Check notification data includes all fields
   - Verify driver receives push notification on mobile

---

## Summary

✅ **Notification is already implemented and working!**

When driver requests token and trip is available:
1. ✅ Token auto-allocated
2. ✅ FCM notification sent (same format as manual allocation)
3. ✅ API response includes trip details
4. ✅ Driver gets both notification + API response

**No additional changes needed** - the notification flow is complete and consistent across all allocation scenarios!
