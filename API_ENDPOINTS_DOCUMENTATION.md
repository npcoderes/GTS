# Complete API Endpoints Documentation

## Base URL
All endpoints are prefixed with `/api/`

---

## Authentication APIs
**Handler:** `core.views`

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| POST | `/api/auth/login/` | `login_view` | User login with email/password |
| POST | `/api/auth/logout/` | `logout_view` | User logout (deletes token) |
| GET | `/api/auth/me/` | `current_user_view` | Get current authenticated user |
| POST | `/api/auth/choose-role` | `choose_role_view` | Select active role context |

---

## User Management APIs
**Handler:** `core.views.UserViewSet`

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/api/users/` | `UserViewSet.list` | List all users |
| POST | `/api/users/` | `UserViewSet.create` | Create new user |
| GET | `/api/users/{id}/` | `UserViewSet.retrieve` | Get user details |
| PUT | `/api/users/{id}/` | `UserViewSet.update` | Update user |
| PATCH | `/api/users/{id}/` | `UserViewSet.partial_update` | Partial update user |
| DELETE | `/api/users/{id}/` | `UserViewSet.destroy` | Delete user |

---

## Role Management APIs
**Handler:** `core.views.RoleViewSet`

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/api/roles/` | `RoleViewSet.list` | List all roles |
| POST | `/api/roles/` | `RoleViewSet.create` | Create new role |
| GET | `/api/roles/{id}/` | `RoleViewSet.retrieve` | Get role details |
| PUT | `/api/roles/{id}/` | `RoleViewSet.update` | Update role |
| DELETE | `/api/roles/{id}/` | `RoleViewSet.destroy` | Delete role |

---

## User Role Assignment APIs
**Handler:** `core.views.UserRoleViewSet`

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/api/user-roles/` | `UserRoleViewSet.list` | List user role assignments |
| POST | `/api/user-roles/` | `UserRoleViewSet.create` | Assign role to user |
| GET | `/api/user-roles/{id}/` | `UserRoleViewSet.retrieve` | Get role assignment details |
| PUT | `/api/user-roles/{id}/` | `UserRoleViewSet.update` | Update role assignment |
| DELETE | `/api/user-roles/{id}/` | `UserRoleViewSet.destroy` | Remove role assignment |

**Query Parameters:**
- `user` - Filter by user ID

---

## Station Management APIs
**Handler:** `core.views.StationViewSet`

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/api/stations/` | `StationViewSet.list` | List all stations |
| POST | `/api/stations/` | `StationViewSet.create` | Create new station |
| GET | `/api/stations/{id}/` | `StationViewSet.retrieve` | Get station details |
| PUT | `/api/stations/{id}/` | `StationViewSet.update` | Update station |
| DELETE | `/api/stations/{id}/` | `StationViewSet.destroy` | Delete station |

**Query Parameters:**
- `type` - Filter by station type (MS/DBS)

---

## Route Management APIs
**Handler:** `core.views.RouteViewSet`

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/api/routes/` | `RouteViewSet.list` | List all routes |
| POST | `/api/routes/` | `RouteViewSet.create` | Create new route |
| GET | `/api/routes/{id}/` | `RouteViewSet.retrieve` | Get route details |
| PUT | `/api/routes/{id}/` | `RouteViewSet.update` | Update route |
| DELETE | `/api/routes/{id}/` | `RouteViewSet.destroy` | Delete route |

**Query Parameters:**
- `ms` - Filter by MS station ID
- `dbs` - Filter by DBS station ID
- `is_active` - Filter by active status

---

## MS-DBS Mapping APIs
**Handler:** `core.views.MSDBSMapViewSet`

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/api/ms-dbs-maps/` | `MSDBSMapViewSet.list` | List MS-DBS mappings |
| POST | `/api/ms-dbs-maps/` | `MSDBSMapViewSet.create` | Create mapping |
| GET | `/api/ms-dbs-maps/{id}/` | `MSDBSMapViewSet.retrieve` | Get mapping details |
| PUT | `/api/ms-dbs-maps/{id}/` | `MSDBSMapViewSet.update` | Update mapping |
| DELETE | `/api/ms-dbs-maps/{id}/` | `MSDBSMapViewSet.destroy` | Delete mapping |

**Query Parameters:**
- `ms` - Filter by MS station ID
- `dbs` - Filter by DBS station ID
- `active` - Filter by active status

---

## Notification APIs
**Handler:** `core.views`

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| POST | `/api/notifications/register-token` | `register_fcm_token` | Register FCM device token |
| POST | `/api/notifications/unregister-token` | `unregister_fcm_token` | Unregister FCM token |
| POST | `/api/notifications/send` | `send_notification` | Send notification to user |
| POST | `/api/notifications/send-to-me` | `send_notification_to_me` | Test notification |

---

## Vehicle Management APIs
**Handler:** `logistics.views.VehicleViewSet`

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/api/vehicles/` | `VehicleViewSet.list` | List all vehicles |
| POST | `/api/vehicles/` | `VehicleViewSet.create` | Create new vehicle |
| GET | `/api/vehicles/{id}/` | `VehicleViewSet.retrieve` | Get vehicle details |
| PUT | `/api/vehicles/{id}/` | `VehicleViewSet.update` | Update vehicle |
| DELETE | `/api/vehicles/{id}/` | `VehicleViewSet.destroy` | Delete vehicle |

---

## Driver Management APIs
**Handler:** `logistics.views.DriverViewSet`

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/api/drivers/` | `DriverViewSet.list` | List all drivers |
| POST | `/api/drivers/` | `DriverViewSet.create` | Create new driver |
| GET | `/api/drivers/{id}/` | `DriverViewSet.retrieve` | Get driver details |
| PUT | `/api/drivers/{id}/` | `DriverViewSet.update` | Update driver |
| DELETE | `/api/drivers/{id}/` | `DriverViewSet.destroy` | Delete driver |
| GET | `/api/driver/{id}/token` | `DriverViewSet.token` | Get driver's active token |
| GET | `/api/driver/{id}/trips` | `DriverViewSet.trips` | Get driver's trip history |

---

## Shift Management APIs
**Handler:** `logistics.views.ShiftViewSet`

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/api/shifts/` | `ShiftViewSet.list` | List all shifts |
| POST | `/api/shifts/` | `ShiftViewSet.create` | Create new shift |
| GET | `/api/shifts/{id}/` | `ShiftViewSet.retrieve` | Get shift details |
| PUT | `/api/shifts/{id}/` | `ShiftViewSet.update` | Update shift |
| DELETE | `/api/shifts/{id}/` | `ShiftViewSet.destroy` | Delete shift |
| POST | `/api/shifts/{id}/approve/` | `ShiftViewSet.approve` | Approve shift (EIC only) |
| POST | `/api/shifts/{id}/reject/` | `ShiftViewSet.reject` | Reject shift (EIC only) |

**Query Parameters:**
- `status` - Filter by shift status

---

## Stock Request APIs
**Handler:** `logistics.views.StockRequestViewSet`

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/api/stock-requests/` | `StockRequestViewSet.list` | List stock requests |
| POST | `/api/stock-requests/` | `StockRequestViewSet.create` | Create stock request |
| GET | `/api/stock-requests/{id}/` | `StockRequestViewSet.retrieve` | Get request details |
| PUT | `/api/stock-requests/{id}/` | `StockRequestViewSet.update` | Update request |
| DELETE | `/api/stock-requests/{id}/` | `StockRequestViewSet.destroy` | Delete request |

---

## Trip Management APIs
**Handler:** `logistics.views.TripViewSet`

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/api/trips/` | `TripViewSet.list` | List all trips |
| POST | `/api/trips/` | `TripViewSet.create` | Create new trip |
| GET | `/api/trips/{id}/` | `TripViewSet.retrieve` | Get trip details |
| PUT | `/api/trips/{id}/` | `TripViewSet.update` | Update trip |
| DELETE | `/api/trips/{id}/` | `TripViewSet.destroy` | Delete trip |
| POST | `/api/driver/trip/{id}/accept` | `TripViewSet.accept` | Driver accepts trip |
| POST | `/api/driver/trip/{id}/reject` | `TripViewSet.reject` | Driver rejects trip |
| GET | `/api/driver/trip/status` | `TripViewSet.status` | Get trip status by token |

**Query Parameters:**
- `dbs_id` - Filter by DBS station ID
- `status` - Filter by status (comma-separated)

---

## Driver Operations APIs
**Handler:** `logistics.views` & `logistics.driver_views`

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| POST | `/api/driver/location` | `DriverLocationView` | Update driver location |
| POST | `/api/driver/arrival/ms` | `DriverArrivalMSView` | Confirm arrival at MS |
| POST | `/api/driver/arrival/dbs` | `DriverArrivalDBSView` | Confirm arrival at DBS |
| POST | `/api/driver/meter-reading/confirm` | `MeterReadingConfirmationView` | Confirm meter reading |
| POST | `/api/driver/trip/complete` | `TripCompleteView` | Complete trip |
| POST | `/api/driver/emergency` | `EmergencyReportView` | Report emergency |

---

## Driver Trip APIs
**Handler:** `logistics.driver_views.DriverTripViewSet`

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| POST | `/api/driver-trips/accept/` | `DriverTripViewSet.accept_trip` | Accept trip offer |
| POST | `/api/driver-trips/reject/` | `DriverTripViewSet.reject_trip` | Reject trip offer |
| POST | `/api/driver-trips/arrival/ms/` | `DriverTripViewSet.arrival_at_ms` | Confirm MS arrival |
| POST | `/api/driver-trips/meter-reading/confirm/` | `DriverTripViewSet.confirm_meter_reading` | Confirm meter reading |
| GET | `/api/driver-trips/pending/` | `DriverTripViewSet.pending_offers` | Get pending trip offers |

---

## Driver Notification APIs
**Handler:** `core.notification_views`

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| POST | `/api/driver/notifications/register` | `DriverNotificationRegisterView` | Register driver FCM token |
| POST | `/api/driver/notifications/unregister` | `DriverNotificationUnregisterView` | Unregister driver FCM token |

---

## MS Operations APIs
**Handler:** `logistics.views` & `logistics.ms_views`

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| POST | `/api/ms/confirm-arrival` | `MSConfirmArrivalView` | Confirm vehicle arrival |
| POST | `/api/ms/pre-reading` | `MSPreReadingView` | Record pre-fill reading |
| POST | `/api/ms/post-reading` | `MSPostReadingView` | Record post-fill reading |
| POST | `/api/ms/confirm-sap` | `MSConfirmSAPView` | Confirm SAP posting |
| GET | `/api/ms/fill/{token_id}/prefill` | `MSFillPrefillView` | Get prefill data |
| POST | `/api/ms/fill/{token_id}/start` | `MSFillStartView` | Start filling operation |
| POST | `/api/ms/fill/{token_id}/end` | `MSFillEndView` | End filling operation |
| POST | `/api/sto/{trip_id}/generate` | `STOGenerateView` | Generate STO number |
| GET | `/api/ms/{ms_id}/transfers` | `MSStockTransferListView` | Get MS stock transfers |
| GET | `/api/ms/{ms_id}/schedule` | `MSTripScheduleView` | Get MS trip schedule |

---

## MS Notification APIs
**Handler:** `core.notification_views`

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| POST | `/api/ms/notifications/register` | `MSNotificationRegisterView` | Register MS operator FCM token |
| POST | `/api/ms/notifications/unregister` | `MSNotificationUnregisterView` | Unregister MS operator FCM token |

---

## DBS Operations APIs
**Handler:** `logistics.views` & `logistics.dbs_views`

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| POST | `/api/dbs/decant/arrive` | `DBSDecantArriveView` | Confirm truck arrival |
| POST | `/api/dbs/decant/pre` | `DBSDecantPreView` | Get pre-decant metrics |
| POST | `/api/dbs/decant/start` | `DBSDecantStartView` | Start decanting |
| POST | `/api/dbs/decant/end` | `DBSDecantEndView` | End decanting |
| POST | `/api/dbs/decant/confirm` | `DBSDecantConfirmView` | Confirm delivery |
| GET | `/api/dbs/dashboard/` | `DBSDashboardView` | Get DBS dashboard data |
| GET | `/api/dbs/transfers` | `DBSStockTransferListView` | Get DBS stock transfers |

**Query Parameters (transfers):**
- `dbs_id` - DBS station ID
- `startDate` - Start date filter
- `endDate` - End date filter

---

## DBS Notification APIs
**Handler:** `core.notification_views`

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| POST | `/api/dbs/notifications/register` | `DBSNotificationRegisterView` | Register DBS operator FCM token |
| POST | `/api/dbs/notifications/unregister` | `DBSNotificationUnregisterView` | Unregister DBS operator FCM token |

---

## EIC Management APIs
**Handler:** `logistics.eic_views`

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/api/eic/dashboard` | `EICDashboardView` | Get EIC dashboard statistics |
| GET | `/api/eic/driver-approvals/pending` | `EICDriverApprovalView` | Get pending driver approvals |
| GET | `/api/eic/permissions` | `EICPermissionsView` | Get EIC user permissions |
| GET | `/api/eic/network-overview` | `EICNetworkOverviewView` | Get network overview |
| GET | `/api/eic/reconciliation-reports` | `EICReconciliationReportView` | Get reconciliation reports |
| POST | `/api/eic/reconciliation-reports/{id}/action` | `EICReconciliationActionView` | Trigger corrective action |
| GET | `/api/eic/vehicles/active` | `EICVehicleTrackingView` | Get active vehicle tracking |
| GET | `/api/eic/incoming-stock-requests` | `EICIncomingStockRequestsView` | Get incoming stock requests |
| GET | `/api/eic/vehicle-queue` | `EICVehicleQueueView` | Get vehicle queue at MS/DBS |

---

## EIC Stock Request APIs
**Handler:** `logistics.eic_views.EICStockRequestViewSet`

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/api/eic/stock-requests/` | `EICStockRequestViewSet.list` | List stock requests (EIC view) |
| GET | `/api/eic/stock-requests/{id}/` | `EICStockRequestViewSet.retrieve` | Get request details |
| POST | `/api/eic/stock-requests/{id}/approve/` | `EICStockRequestViewSet.approve` | Approve/reject request |
| POST | `/api/eic/stock-requests/{id}/reject/` | `EICStockRequestViewSet.reject` | Reject request |
| GET | `/api/eic/stock-requests/{id}/available-drivers/` | `EICStockRequestViewSet.available_drivers` | Get available drivers |

**Query Parameters:**
- `status` - Filter by status (comma-separated)
- `type` - Filter by source type
- `priority` - Filter by priority
- `dbs_id` - Filter by DBS station ID

---

## EIC Cluster Management APIs
**Handler:** `logistics.eic_management_views.EICClusterViewSet`

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/api/eic/clusters/` | `EICClusterViewSet.list` | List clusters (MS with DBS) |
| GET | `/api/eic/clusters/{id}/` | `EICClusterViewSet.retrieve` | Get cluster details |
| PUT | `/api/eic/clusters/{id}/` | `EICClusterViewSet.update` | Update cluster configuration |

---

## EIC Stock Transfer APIs
**Handler:** `logistics.eic_management_views`

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/api/eic/stock-transfers` | `EICStockTransfersByDBSView` | Get stock transfers by DBS |
| GET | `/api/eic/stock-transfers/ms-dbs` | `EICStockTransferMSDBSView` | Get MS with linked DBS |
| GET | `/api/eic/stock-transfers/by-dbs` | `EICStockTransfersByDBSView` | Get transfers for specific DBS |

**Query Parameters:**
- `dbs_id` - DBS station ID (required for by-dbs)
- `start_date` - Start date filter
- `end_date` - End date filter
- `include_cancelled` - Include cancelled trips

---

## Summary by Module

### Core Module (Authentication & User Management)
- **Total Endpoints:** 35
- **ViewSets:** UserViewSet, RoleViewSet, UserRoleViewSet, StationViewSet, RouteViewSet, MSDBSMapViewSet
- **Function Views:** login_view, logout_view, current_user_view, choose_role_view, FCM notification views

### Logistics Module (Operations & Management)
- **Total Endpoints:** 60+
- **ViewSets:** VehicleViewSet, DriverViewSet, ShiftViewSet, StockRequestViewSet, TripViewSet, DriverTripViewSet, EICStockRequestViewSet, EICClusterViewSet
- **Class Views:** MS operations (8), DBS operations (6), Driver operations (6), EIC management (10+)

### Total API Endpoints: 95+

---

## Authentication
All endpoints except `/api/auth/login/` require authentication using Token-based authentication.

**Header Format:**
```
Authorization: Token <your-token-here>
```

---

## Common Response Formats

### Success Response
```json
{
  "success": true,
  "data": {},
  "message": "Operation successful"
}
```

### Error Response
```json
{
  "error": "Error message",
  "details": {}
}
```

### Paginated Response
```json
{
  "count": 100,
  "next": "http://api/endpoint/?page=2",
  "previous": null,
  "results": []
}
```

---

## Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `500` - Internal Server Error
