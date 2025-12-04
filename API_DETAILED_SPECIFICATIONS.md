# GTS Backend - Detailed API Specifications for Pending Endpoints

**Last Updated:** 2025-01-16
**Status:** Implementation Guide for Missing APIs

---

## 📋 Table of Contents
1. [EIC (Transport Admin) APIs](#1-eic-transport-admin-apis)
2. [SGL Customer APIs](#2-sgl-customer-apis)
3. [DBS Additional APIs](#3-dbs-additional-apis)
4. [Schedule & Network APIs](#4-schedule--network-apis)

---

# 1. EIC (Transport Admin) APIs

## 1.1 GET `/api/eic/stock-requests`
### Purpose
Fetch all stock requests with filtering and sorting for EIC dashboard

### Request
**Method:** GET
**Auth:** Required (EIC role)
**Query Parameters:**
```
?status=PENDING,APPROVED     # Filter by status (comma-separated)
?type=DBS_OPERATOR,AI        # Filter by source type
?priority=H,C                # Filter by priority
?dbs_id=123                  # Filter by specific DBS
?page=1&limit=20             # Pagination
```

### Business Logic
1. Check if user has EIC role (`user_roles.role__code = 'EIC'`)
2. Query `stock_requests` table with filters
3. Join with `stations` (DBS details), `users` (requested by)
4. Sort by: priority (H>C>N>FDODO), then created_at DESC
5. Calculate derived fields:
   - Time since request (minutes)
   - Projected DOT status (critical/warning/normal)

### Database Tables
- **Primary:** `stock_requests`
- **Joins:** `stations` (dbs), `users` (requested_by_user)

### Response Example
```json
{
  "count": 25,
  "page": 1,
  "limit": 20,
  "results": [
    {
      "id": 101,
      "source": "DBS_OPERATOR",
      "status": "PENDING",
      "priority_preview": "H",
      "dbs": {
        "id": 5,
        "code": "DBS-005",
        "name": "Vastral DBS",
        "type": "DBS"
      },
      "requested_by_user": {
        "id": 45,
        "full_name": "Operator Name",
        "email": "operator@sgl.com"
      },
      "requested_qty_kg": 5000.00,
      "current_stock_kg": 1200.00,
      "rate_of_sale_kg_per_min": 25.50,
      "dot_minutes": 47,
      "rlt_minutes": 120,
      "created_at": "2025-01-16T10:30:00Z",
      "time_elapsed_minutes": 15
    }
  ]
}
```

### Implementation File
`logistics/views.py` - Create `EICStockRequestViewSet` or `EICStockRequestListView`

---

## 1.2 GET `/api/eic/stock-requests/{id}`
### Purpose
Get detailed view of a single stock request

### Request
**Method:** GET
**Auth:** Required (EIC role)
**Path Parameter:** `id` - Stock Request ID

### Business Logic
1. Verify EIC permission
2. Fetch stock request by ID with full details
3. Include related trip if one has been assigned
4. Calculate current status indicators

### Response Example
```json
{
  "id": 101,
  "source": "DBS_OPERATOR",
  "status": "PENDING",
  "priority_preview": "H",
  "dbs": {
    "id": 5,
    "code": "DBS-005",
    "name": "Vastral DBS",
    "address": "Vastral Road, Ahmedabad",
    "lat": 23.0765,
    "lng": 72.6360,
    "geofence_radius_m": 200
  },
  "requested_by_user": {
    "id": 45,
    "full_name": "Operator Name",
    "email": "operator@sgl.com",
    "phone": "+91-9876543210"
  },
  "requested_qty_kg": 5000.00,
  "current_stock_kg": 1200.00,
  "rate_of_sale_kg_per_min": 25.50,
  "dot_minutes": 47,
  "rlt_minutes": 120,
  "created_at": "2025-01-16T10:30:00Z",
  "assigned_trip": null,
  "notes": "Urgent - High demand expected"
}
```

---

## 1.3 POST `/api/eic/stock-requests/{id}/approve`
### Purpose
Approve a pending stock request and create a trip

### Request
**Method:** POST
**Auth:** Required (EIC role)
**Path Parameter:** `id` - Stock Request ID
**Body:**
```json
{
  "vehicle_id": 10,
  "driver_id": 25,
  "ms_id": 2,
  "approved_qty_kg": 5000.00,
  "route_id": 15,
  "notes": "Approved for immediate dispatch"
}
```

### Business Logic
1. Verify EIC permission
2. Validate stock request exists and status = PENDING
3. Check vehicle and driver availability
4. Check driver shift validity
5. **Create Trip:**
   - Status: PENDING
   - Link to stock_request
   - Assign vehicle, driver, MS, DBS, route
6. **Create Token:**
   - Generate sequence number
   - Link to trip
   - issued_at = now()
7. **Update Stock Request:**
   - status = APPROVED
8. **Send Notification** to driver (Firebase/WebSocket)

### Database Operations
```sql
-- 1. Update stock_requests
UPDATE stock_requests SET status='APPROVED' WHERE id=?

-- 2. Create token
INSERT INTO tokens (vehicle_id, ms_id, sequence_no, issued_at)
VALUES (?, ?, ?, NOW())

-- 3. Create trip
INSERT INTO trips (
  token_id, vehicle_id, driver_id, ms_id, dbs_id,
  route_id, status, started_at
) VALUES (?, ?, ?, ?, ?, ?, 'PENDING', NOW())

-- 4. Link stock_request to trip (optional field)
-- Update stock_requests.assigned_trip_id = new_trip.id
```

### Response Example
```json
{
  "status": "approved",
  "stock_request_id": 101,
  "trip": {
    "id": 550,
    "token": {
      "id": 780,
      "sequence_no": 45
    },
    "vehicle": {
      "id": 10,
      "registration_no": "GJ-01-AB-1234"
    },
    "driver": {
      "id": 25,
      "full_name": "Driver Name"
    },
    "status": "PENDING",
    "created_at": "2025-01-16T11:00:00Z"
  },
  "message": "Stock request approved and trip created"
}
```

### Implementation File
`logistics/views.py` - `@action(detail=True, methods=['post'])`

---

## 1.4 POST `/api/eic/stock-requests/{id}/reject`
### Purpose
Reject a pending stock request

### Request
**Method:** POST
**Auth:** Required (EIC role)
**Path Parameter:** `id` - Stock Request ID
**Body:**
```json
{
  "reason": "Insufficient vehicles available",
  "notes": "Retry after 2 hours"
}
```

### Business Logic
1. Verify EIC permission
2. Validate stock request exists and status = PENDING/QUEUED
3. Update status to REJECTED
4. Log rejection reason
5. Send notification to requester

### Database Operations
```sql
UPDATE stock_requests
SET status='REJECTED',
    rejection_reason=?,
    rejected_at=NOW(),
    rejected_by_user_id=?
WHERE id=?
```

### Response Example
```json
{
  "status": "rejected",
  "stock_request_id": 101,
  "message": "Stock request has been rejected"
}
```

---

## 1.5 GET `/api/eic/dashboard`
### Purpose
Get EIC dashboard statistics and overview

### Request
**Method:** GET
**Auth:** Required (EIC role)

### Business Logic
1. Count pending stock requests (status=PENDING)
2. Count active trips (status IN [PENDING, AT_MS, IN_TRANSIT, AT_DBS])
3. Count pending driver approvals (status=PENDING from shifts table)
4. Count alerts (last 24 hours)
5. Calculate average RLT today
6. Get recent reconciliation alerts (variance > 0.5%)

### Database Tables
- `stock_requests`, `trips`, `shifts`, `alerts`, `reconciliation`

### Response Example
```json
{
  "summary": {
    "pending_stock_requests": 8,
    "active_trips": 12,
    "pending_driver_approvals": 3,
    "alerts_today": 2,
    "avg_rlt_minutes": 95,
    "reconciliation_alerts": 1
  },
  "recent_stock_requests": [
    {
      "id": 101,
      "dbs_name": "Vastral DBS",
      "priority": "H",
      "created_at": "2025-01-16T10:30:00Z"
    }
  ],
  "active_trips": [
    {
      "id": 550,
      "vehicle_no": "GJ-01-AB-1234",
      "status": "IN_TRANSIT",
      "from_ms": "MS-002",
      "to_dbs": "DBS-005"
    }
  ],
  "alerts": [
    {
      "id": 89,
      "type": "VARIANCE_ALERT",
      "severity": "MEDIUM",
      "message": "Gas variance 0.8% detected on Trip #548",
      "created_at": "2025-01-16T09:15:00Z"
    }
  ]
}
```

---

## 1.6 GET `/api/eic/permissions`
### Purpose
Get current EIC user's permissions

### Request
**Method:** GET
**Auth:** Required (EIC role)

### Response Example
```json
{
  "can_approve_requests": true,
  "can_reject_requests": true,
  "can_override_tokens": false,
  "can_manage_clusters": true,
  "can_approve_drivers": true,
  "managed_stations": [2, 5, 8],
  "role": "EIC"
}
```

---

## 1.7 GET `/api/eic/driver-approvals/pending`
### Purpose
Get list of pending driver shift approvals

### Request
**Method:** GET
**Auth:** Required (EIC role)

### Business Logic
1. Query `shifts` table WHERE status='PENDING'
2. Join with `drivers`, `vehicles`
3. Sort by created_at ASC

### Database Tables
- **Primary:** `shifts`
- **Joins:** `drivers`, `vehicles`, `users`

### Response Example
```json
{
  "count": 3,
  "results": [
    {
      "id": 45,
      "driver": {
        "id": 25,
        "full_name": "Driver Name",
        "license_no": "DL-123456",
        "license_expiry": "2027-12-31",
        "phone": "+91-9876543210",
        "status": "ACTIVE",
        "trained": true
      },
      "vehicle": {
        "id": 10,
        "registration_no": "GJ-01-AB-1234",
        "capacity_kg": 1500.00
      },
      "start_time": "2025-01-17T06:00:00Z",
      "end_time": "2025-01-17T14:00:00Z",
      "status": "PENDING",
      "created_by": {
        "id": 30,
        "full_name": "Vendor Name"
      },
      "created_at": "2025-01-16T15:00:00Z"
    }
  ]
}
```

---

## 1.8 POST `/api/eic/driver-approvals/{id}/approve`
### Purpose
Approve a driver shift

### Request
**Method:** POST
**Auth:** Required (EIC role)
**Path Parameter:** `id` - Shift ID
**Body:**
```json
{
  "notes": "Approved"
}
```

### Business Logic
1. Verify EIC permission
2. Validate shift exists and status=PENDING
3. Check for overlapping approved shifts for same driver
4. Update status to APPROVED
5. Log approved_by user

### Database Operations
```sql
UPDATE shifts
SET status='APPROVED',
    approved_by_id=?,
    approved_at=NOW()
WHERE id=?
```

### Response Example
```json
{
  "status": "approved",
  "shift_id": 45,
  "message": "Driver shift approved"
}
```

---

## 1.9 POST `/api/eic/driver-approvals/{id}/reject`
### Purpose
Reject a driver shift

### Request
**Method:** POST
**Auth:** Required (EIC role)
**Path Parameter:** `id` - Shift ID
**Body:**
```json
{
  "reason": "License expired"
}
```

### Response Example
```json
{
  "status": "rejected",
  "shift_id": 45,
  "message": "Driver shift rejected"
}
```

---

## 1.10 GET `/api/eic/clusters`
### Purpose
Get all MS-DBS cluster mappings

### Business Logic
1. Query `stations` WHERE type='MS'
2. For each MS, get linked DBS from `ms_dbs_map` or `routes` table
3. Include active/inactive status

### Database Tables
- `stations`, `routes` (or `ms_dbs_map` if exists)

### Response Example
```json
{
  "clusters": [
    {
      "ms": {
        "id": 2,
        "code": "MS-002",
        "name": "Ahmedabad MS",
        "address": "Ahmedabad"
      },
      "linked_dbs": [
        {
          "id": 5,
          "code": "DBS-005",
          "name": "Vastral DBS",
          "is_active": true
        },
        {
          "id": 8,
          "code": "DBS-008",
          "name": "Narol DBS",
          "is_active": true
        }
      ]
    }
  ]
}
```

---

## 1.11 PUT `/api/eic/clusters/{clusterId}`
### Purpose
Update MS-DBS cluster mapping

### Request
**Method:** PUT
**Auth:** Required (EIC role)
**Path Parameter:** `clusterId` - MS station ID
**Body:**
```json
{
  "linked_dbs": [5, 8, 12],
  "default_route_ids": {
    "5": 15,
    "8": 18,
    "12": 22
  }
}
```

### Business Logic
1. Verify EIC permission
2. Validate MS exists
3. Validate all DBS IDs exist
4. Update route mappings in `routes` table
5. Set is_active flags

### Response Example
```json
{
  "status": "updated",
  "ms_id": 2,
  "linked_dbs_count": 3,
  "message": "Cluster mapping updated"
}
```

---

## 1.12 GET `/api/eic/reconciliation/reports`
### Purpose
Get reconciliation reports with variance alerts

### Request
**Method:** GET
**Auth:** Required (EIC role)
**Query Parameters:**
```
?status=ALERT               # Filter by status
?date_from=2025-01-01       # Date range
?date_to=2025-01-16
?min_variance=0.5           # Minimum variance %
```

### Business Logic
1. Query `reconciliation` table
2. Join with `trips`, `vehicles`, `drivers`
3. Filter by variance_pct > threshold
4. Sort by variance_pct DESC

### Database Tables
- **Primary:** `reconciliation`
- **Joins:** `trips`, `vehicles`, `drivers`, `stations`

### Response Example
```json
{
  "count": 5,
  "results": [
    {
      "id": 89,
      "trip": {
        "id": 548,
        "vehicle_no": "GJ-01-AB-1234",
        "driver_name": "Driver Name",
        "from_ms": "MS-002",
        "to_dbs": "DBS-005",
        "completed_at": "2025-01-16T14:30:00Z"
      },
      "ms_filled_qty_kg": 1500.00,
      "dbs_delivered_qty_kg": 1488.00,
      "diff_qty": 12.00,
      "variance_pct": 0.80,
      "status": "ALERT",
      "route_deviation": false
    }
  ]
}
```

---

## 1.13 POST `/api/eic/reconciliation/reports/{id}/actions`
### Purpose
Take action on reconciliation alert

### Request
**Method:** POST
**Auth:** Required (EIC role)
**Path Parameter:** `id` - Reconciliation ID
**Body:**
```json
{
  "action": "INVESTIGATE",
  "notes": "Equipment calibration check scheduled",
  "assigned_to_user_id": 45
}
```

### Response Example
```json
{
  "status": "action_recorded",
  "reconciliation_id": 89,
  "message": "Action has been logged"
}
```

---

## 1.14 GET `/api/eic/manual-tokens`
### Purpose
Get list of manually assigned tokens (for FDODO)

### Response Example
```json
{
  "tokens": [
    {
      "id": 780,
      "sequence_no": 45,
      "customer_name": "FDODO Customer Name",
      "ms_name": "MS-002",
      "quantity_kg": 500,
      "issued_at": "2025-01-16T11:00:00Z",
      "status": "ACTIVE"
    }
  ]
}
```

---

## 1.15 POST `/api/eic/manual-tokens`
### Purpose
Manually assign token to FDODO customer

### Request
**Method:** POST
**Auth:** Required (EIC role)
**Body:**
```json
{
  "customer_id": 50,
  "customer_name": "FDODO Customer",
  "ms_id": 2,
  "quantity_kg": 500
}
```

### Response Example
```json
{
  "status": "token_assigned",
  "token": {
    "id": 781,
    "sequence_no": 46,
    "issued_at": "2025-01-16T12:00:00Z"
  }
}
```

---

# 2. SGL Customer APIs

## 2.1 GET `/api/customer/{dbsId}/dashboard`
### Purpose
Get customer dashboard for specific DBS

### Request
**Method:** GET
**Auth:** Required (SGL_CUSTOMER role)
**Path Parameter:** `dbsId` - DBS Station ID

### Business Logic
1. Verify user has access to this DBS
2. Get recent trips (last 7 days)
3. Get current stock level
4. Get upcoming scheduled trips
5. Get delivery statistics

### Response Example
```json
{
  "dbs": {
    "id": 5,
    "code": "DBS-005",
    "name": "Vastral DBS",
    "current_stock_kg": 1200.00,
    "capacity_kg": 5000.00,
    "stock_percentage": 24.0
  },
  "stats": {
    "trips_today": 3,
    "trips_this_week": 18,
    "avg_delivery_qty_kg": 1400.00,
    "total_delivered_this_week_kg": 25200.00
  },
  "recent_trips": [
    {
      "id": 550,
      "vehicle_no": "GJ-01-AB-1234",
      "driver_name": "Driver Name",
      "from_ms": "MS-002",
      "status": "COMPLETED",
      "delivered_qty_kg": 1500.00,
      "completed_at": "2025-01-16T14:30:00Z"
    }
  ]
}
```

---

## 2.2 GET `/api/customer/{dbsId}/stocks`
### Purpose
Get current stock levels at DBS

### Response Example
```json
{
  "dbs_id": 5,
  "dbs_name": "Vastral DBS",
  "current_stock_kg": 1200.00,
  "capacity_kg": 5000.00,
  "stock_percentage": 24.0,
  "last_updated": "2025-01-16T15:00:00Z",
  "last_delivery": {
    "trip_id": 548,
    "delivered_qty_kg": 1500.00,
    "delivered_at": "2025-01-16T09:30:00Z"
  },
  "rate_of_sale_kg_per_min": 25.50,
  "estimated_dot_minutes": 47
}
```

---

## 2.3 GET `/api/customer/{dbsId}/transport`
### Purpose
Track active transports heading to this DBS

### Response Example
```json
{
  "active_transports": [
    {
      "trip_id": 552,
      "vehicle_no": "GJ-01-AB-5678",
      "driver_name": "Driver Name",
      "driver_phone": "+91-9876543210",
      "from_ms": "MS-002",
      "status": "IN_TRANSIT",
      "expected_qty_kg": 1500.00,
      "started_at": "2025-01-16T14:00:00Z",
      "estimated_arrival": "2025-01-16T16:00:00Z",
      "current_location": {
        "lat": 23.0500,
        "lng": 72.6200
      }
    }
  ]
}
```

---

## 2.4 GET `/api/customer/{dbsId}/transfers`
### Purpose
Get stock transfer history for DBS

### Request
**Query Parameters:**
```
?date_from=2025-01-01
?date_to=2025-01-16
?limit=50
```

### Response Example
```json
{
  "count": 45,
  "transfers": [
    {
      "trip_id": 548,
      "vehicle_no": "GJ-01-AB-1234",
      "from_ms": "MS-002",
      "to_dbs": "DBS-005",
      "ms_filled_qty_kg": 1500.00,
      "dbs_delivered_qty_kg": 1488.00,
      "variance_pct": 0.80,
      "completed_at": "2025-01-16T14:30:00Z",
      "status": "COMPLETED"
    }
  ]
}
```

---

## 2.5 GET `/api/customer/{dbsId}/pending-trips`
### Purpose
Get trips pending acceptance by customer

### Response Example
```json
{
  "pending_trips": [
    {
      "trip_id": 555,
      "vehicle_no": "GJ-01-AB-9999",
      "driver_name": "Driver Name",
      "from_ms": "MS-002",
      "expected_qty_kg": 1500.00,
      "created_at": "2025-01-16T15:30:00Z",
      "can_accept": true
    }
  ]
}
```

---

## 2.6 POST `/api/customer/trips/{tripId}/accept`
### Purpose
Customer accepts a trip on behalf of driver

### Request
**Method:** POST
**Auth:** Required (SGL_CUSTOMER role)
**Path Parameter:** `tripId` - Trip ID
**Body:**
```json
{
  "user_id": 60,
  "notes": "Accepted by customer"
}
```

### Business Logic
1. Verify customer has permission (Super Admin must grant)
2. Validate trip exists and status=PENDING
3. Check if driver hasn't already accepted
4. Update trip status
5. Log customer acceptance

### Response Example
```json
{
  "status": "accepted",
  "trip_id": 555,
  "message": "Trip accepted by customer"
}
```

---

## 2.7 GET `/api/customer/permissions/{userId}`
### Purpose
Get customer-specific permissions

### Response Example
```json
{
  "can_accept_trips": true,
  "can_view_all_trips": true,
  "assigned_dbs": [5, 8, 12]
}
```

---

# 3. DBS Additional APIs

## 3.1 POST `/api/dbs/requests`
### Purpose
DBS Operator creates manual stock request

### Request
**Method:** POST
**Auth:** Required (DBS_OPERATOR role)
**Body:**
```json
{
  "dbs_id": 5,
  "requested_qty_kg": 5000.00,
  "current_stock_kg": 1200.00,
  "rate_of_sale_kg_per_min": 25.50,
  "dot_minutes": 47,
  "rlt_minutes": 120,
  "notes": "Urgent request - high demand"
}
```

### Business Logic
1. Verify user is DBS_OPERATOR
2. Get operator's assigned DBS from `user_roles.station_id`
3. Validate DBS exists
4. Create stock request with source=DBS_OPERATOR
5. Calculate priority_preview based on DOT/RLT
6. Send notification to EIC

### Database Operations
```sql
INSERT INTO stock_requests (
  source, status, dbs_id, requested_by_user_id,
  requested_qty_kg, current_stock_kg,
  rate_of_sale_kg_per_min, dot_minutes, rlt_minutes,
  priority_preview, created_at
) VALUES (
  'DBS_OPERATOR', 'PENDING', ?, ?,
  ?, ?, ?, ?, ?, ?, NOW()
)
```

### Response Example
```json
{
  "status": "created",
  "stock_request": {
    "id": 102,
    "source": "DBS_OPERATOR",
    "status": "PENDING",
    "priority_preview": "H",
    "created_at": "2025-01-16T16:00:00Z"
  },
  "message": "Stock request submitted successfully"
}
```

---

## 3.2 GET `/api/dbs/deliveries`
### Purpose
Get list of deliveries for DBS operator's station

### Request
**Method:** GET
**Auth:** Required (DBS_OPERATOR role)

### Business Logic
1. Get operator's DBS from `user_roles.station_id`
2. Query trips WHERE dbs_id = operator's DBS
3. Filter status IN [PENDING, AT_DBS, IN_TRANSIT]
4. Join with vehicles, drivers

### Response Example
```json
{
  "deliveries": [
    {
      "trip_id": 552,
      "vehicle_no": "GJ-01-AB-5678",
      "driver_name": "Driver Name",
      "from_ms": "MS-002",
      "status": "IN_TRANSIT",
      "expected_qty_kg": 1500.00,
      "started_at": "2025-01-16T14:00:00Z"
    }
  ]
}
```

---

## 3.3 GET `/api/dbs/history`
### Purpose
Get historical deliveries for DBS

### Request
**Query Parameters:**
```
?date_from=2025-01-01
?date_to=2025-01-16
?limit=50
```

### Response Example
```json
{
  "history": [
    {
      "trip_id": 548,
      "vehicle_no": "GJ-01-AB-1234",
      "from_ms": "MS-002",
      "delivered_qty_kg": 1488.00,
      "completed_at": "2025-01-16T14:30:00Z"
    }
  ]
}
```

---

## 3.4 GET `/api/dbs/reconcile`
### Purpose
Get reconciliation records for DBS

### Response Example
```json
{
  "reconciliations": [
    {
      "trip_id": 548,
      "ms_filled_qty_kg": 1500.00,
      "dbs_delivered_qty_kg": 1488.00,
      "diff_qty": 12.00,
      "variance_pct": 0.80,
      "status": "ALERT"
    }
  ]
}
```

---

# 4. Schedule & Network APIs

## 4.1 GET `/api/dbs/{id}/schedule`
### Purpose
Get trip schedule for specific DBS

### Response Example
```json
{
  "dbs_id": 5,
  "dbs_name": "Vastral DBS",
  "scheduled_trips": [
    {
      "trip_id": 555,
      "vehicle_no": "GJ-01-AB-9999",
      "scheduled_time": "2025-01-17T08:00:00Z",
      "expected_qty_kg": 1500.00,
      "status": "PENDING"
    }
  ]
}
```

---

## 4.2 GET `/api/ms/{id}/schedule`
### Purpose
Get trip schedule for specific MS

### Response Example
```json
{
  "ms_id": 2,
  "ms_name": "Ahmedabad MS",
  "scheduled_trips": [
    {
      "trip_id": 555,
      "vehicle_no": "GJ-01-AB-9999",
      "to_dbs": "DBS-005",
      "scheduled_time": "2025-01-17T08:00:00Z",
      "expected_qty_kg": 1500.00,
      "status": "PENDING"
    }
  ]
}
```

---

## 4.3 GET `/api/ms/{id}/cluster`
### Purpose
Get cluster information for specific MS

### Response Example
```json
{
  "ms": {
    "id": 2,
    "code": "MS-002",
    "name": "Ahmedabad MS"
  },
  "linked_dbs": [
    {
      "id": 5,
      "code": "DBS-005",
      "name": "Vastral DBS",
      "distance_km": 15.5,
      "avg_rlt_minutes": 95
    }
  ]
}
```

---

## 4.4 GET `/api/network/overview`
### Purpose
Get complete network overview of all MS-DBS connections

### Response Example
```json
{
  "total_ms": 3,
  "total_dbs": 12,
  "total_routes": 28,
  "network_map": [
    {
      "ms": {
        "id": 2,
        "name": "Ahmedabad MS",
        "active_trips": 5
      },
      "connected_dbs": [
        {
          "id": 5,
          "name": "Vastral DBS",
          "active_trips": 2
        }
      ]
    }
  ]
}
```

---

## 📊 Implementation Priority Matrix

| API Category | Total APIs | Priority | Estimated Effort |
|--------------|------------|----------|------------------|
| EIC Stock Requests | 4 | 🔴 CRITICAL | 2 days |
| EIC Driver Approvals | 3 | 🔴 CRITICAL | 1 day |
| DBS Manual Request | 1 | 🔴 CRITICAL | 0.5 day |
| SGL Customer Dashboard | 7 | 🔴 HIGH | 2 days |
| EIC Clusters | 2 | 🟡 MEDIUM | 1 day |
| EIC Reconciliation | 2 | 🟡 MEDIUM | 1 day |
| DBS Additional | 3 | 🟡 MEDIUM | 1 day |
| Schedule & Network | 4 | 🟡 MEDIUM | 1.5 days |
| EIC Manual Tokens | 2 | 🟢 LOW | 1 day |

**Total Estimated:** ~12 development days

---

## 🛠️ Common Implementation Patterns

### Permission Decorator Pattern
```python
from functools import wraps
from rest_framework.response import Response
from rest_framework import status

def require_eic_role(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.user_roles.filter(
            role__code='EIC', active=True
        ).exists():
            return Response(
                {'error': 'EIC role required'},
                status=status.HTTP_403_FORBIDDEN
            )
        return view_func(request, *args, **kwargs)
    return wrapper
```

### Standard Response Format
```python
{
  "status": "success|error",
  "data": {...},
  "message": "Optional message",
  "errors": [...] # Only if status=error
}
```

### Pagination Pattern
```python
from rest_framework.pagination import PageNumberPagination

class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'limit'
    max_page_size = 100
```

---

**End of Detailed Specifications**
