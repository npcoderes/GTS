# Complete API Guide - GTS Backend

## Base URL
```
http://localhost:8000/api/
```

---

## 🔐 Authentication APIs

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| POST | `/auth/login/` | `core.views.login_view` | Login with email/phone + password/MPIN |
| POST | `/auth/logout/` | `core.views.logout_view` | Logout and delete token |
| GET | `/auth/me/` | `core.views.current_user_view` | Get current user details |
| POST | `/auth/choose-role` | `core.views.choose_role_view` | Validate role exists |
| GET | `/auth/permissions/` | `core.permission_views.user_permissions_view` | Get user permissions |
| POST | `/auth/change-password/` | `core.views.change_password` | Change password |
| POST | `/auth/mpin/set/` | `core.views.set_mpin` | Set/update MPIN |

### Forgot Password Flow
| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| POST | `/auth/forgot-password/request/` | `core.views.request_password_reset` | Request OTP via email |
| POST | `/auth/forgot-password/verify/` | `core.views.verify_reset_otp` | Verify OTP, get reset token |
| POST | `/auth/forgot-password/confirm/` | `core.views.confirm_password_reset` | Reset password with token |

---

## 👥 User Management APIs

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/users/` | `core.views.UserViewSet.list` | List all users |
| POST | `/users/` | `core.views.UserViewSet.create` | Create new user |
| GET | `/users/{id}/` | `core.views.UserViewSet.retrieve` | Get user details |
| PUT | `/users/{id}/` | `core.views.UserViewSet.update` | Update user |
| DELETE | `/users/{id}/` | `core.views.UserViewSet.destroy` | Soft delete user |
| POST | `/users/{id}/sync_with_sap/` | `core.views.UserViewSet.sync_with_sap` | Sync user to SAP |
| GET | `/users/{id}/get_from_sap/` | `core.views.UserViewSet.get_from_sap` | Get user from SAP |
| POST | `/users/bulk_sync_sap/` | `core.views.UserViewSet.bulk_sync_sap` | Bulk sync users to SAP |

---

## 🎭 Role Management APIs

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/roles/` | `core.views.RoleViewSet.list` | List all roles |
| POST | `/roles/` | `core.views.RoleViewSet.create` | Create new role |
| GET | `/roles/{id}/` | `core.views.RoleViewSet.retrieve` | Get role details |
| PUT | `/roles/{id}/` | `core.views.RoleViewSet.update` | Update role |
| DELETE | `/roles/{id}/` | `core.views.RoleViewSet.destroy` | Delete role |
| GET | `/roles-with-permissions/` | `core.permission_views.RoleListWithPermissionsView` | Get roles with permissions |

---

## 👤 User-Role Assignment APIs

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/user-roles/` | `core.views.UserRoleViewSet.list` | List user-role assignments |
| POST | `/user-roles/` | `core.views.UserRoleViewSet.create` | Assign role to user |
| GET | `/user-roles/{id}/` | `core.views.UserRoleViewSet.retrieve` | Get assignment details |
| PUT | `/user-roles/{id}/` | `core.views.UserRoleViewSet.update` | Update assignment |
| DELETE | `/user-roles/{id}/` | `core.views.UserRoleViewSet.destroy` | Remove assignment |

---

## 🏢 Station Management APIs

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/stations/` | `core.views.StationViewSet.list` | List all stations |
| POST | `/stations/` | `core.views.StationViewSet.create` | Create new station |
| GET | `/stations/{id}/` | `core.views.StationViewSet.retrieve` | Get station details |
| PUT | `/stations/{id}/` | `core.views.StationViewSet.update` | Update station |
| DELETE | `/stations/{id}/` | `core.views.StationViewSet.destroy` | Delete station |

---

## 🛣️ Route Management APIs

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/routes/` | `core.views.RouteViewSet.list` | List all routes |
| POST | `/routes/` | `core.views.RouteViewSet.create` | Create new route |
| GET | `/routes/{id}/` | `core.views.RouteViewSet.retrieve` | Get route details |
| PUT | `/routes/{id}/` | `core.views.RouteViewSet.update` | Update route |
| DELETE | `/routes/{id}/` | `core.views.RouteViewSet.destroy` | Delete route |

---

## 🗺️ MS-DBS Mapping APIs

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/ms-dbs-maps/` | `core.views.MSDBSMapViewSet.list` | List MS-DBS mappings |
| POST | `/ms-dbs-maps/` | `core.views.MSDBSMapViewSet.create` | Create mapping |
| GET | `/ms-dbs-maps/{id}/` | `core.views.MSDBSMapViewSet.retrieve` | Get mapping details |
| PUT | `/ms-dbs-maps/{id}/` | `core.views.MSDBSMapViewSet.update` | Update mapping |
| DELETE | `/ms-dbs-maps/{id}/` | `core.views.MSDBSMapViewSet.destroy` | Delete mapping |

---

## 🔔 Notification APIs

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| POST | `/notifications/register-token` | `core.views.register_fcm_token` | Register FCM token |
| POST | `/notifications/unregister-token` | `core.views.unregister_fcm_token` | Unregister FCM token |
| POST | `/notifications/send` | `core.views.send_notification` | Send notification to user |
| POST | `/notifications/send-to-me` | `core.views.send_notification_to_me` | Test notification |

### Role-Specific Notification Registration
| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| POST | `/driver/notifications/register` | `core.notification_views.DriverNotificationRegisterView` | Driver FCM registration |
| POST | `/driver/notifications/unregister` | `core.notification_views.DriverNotificationUnregisterView` | Driver FCM unregister |
| POST | `/ms/notifications/register` | `core.notification_views.MSNotificationRegisterView` | MS Operator FCM registration |
| POST | `/ms/notifications/unregister` | `core.notification_views.MSNotificationUnregisterView` | MS Operator FCM unregister |
| POST | `/dbs/notifications/register` | `core.notification_views.DBSNotificationRegisterView` | DBS Operator FCM registration |
| POST | `/dbs/notifications/unregister` | `core.notification_views.DBSNotificationUnregisterView` | DBS Operator FCM unregister |

---

## 🔑 Permission Management APIs

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/permissions/` | `core.permission_views.PermissionViewSet.list` | List all permissions |
| POST | `/permissions/` | `core.permission_views.PermissionViewSet.create` | Create permission |
| GET | `/permissions/{id}/` | `core.permission_views.PermissionViewSet.retrieve` | Get permission details |
| PUT | `/permissions/{id}/` | `core.permission_views.PermissionViewSet.update` | Update permission |
| DELETE | `/permissions/{id}/` | `core.permission_views.PermissionViewSet.destroy` | Delete permission |

### Role Permissions
| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/role-permissions/` | `core.permission_views.RolePermissionViewSet.list` | List role permissions |
| POST | `/role-permissions/` | `core.permission_views.RolePermissionViewSet.create` | Assign permission to role |
| DELETE | `/role-permissions/{id}/` | `core.permission_views.RolePermissionViewSet.destroy` | Remove permission from role |

### User Permissions
| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/user-permissions/` | `core.permission_views.UserPermissionViewSet.list` | List user permissions |
| POST | `/user-permissions/` | `core.permission_views.UserPermissionViewSet.create` | Assign permission to user |
| DELETE | `/user-permissions/{id}/` | `core.permission_views.UserPermissionViewSet.destroy` | Remove permission from user |

---

## 🔗 SAP Integration APIs

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/sap/stations/` | `core.sap_views.SAPStationView` | Get stations from SAP |

---

## 📦 Stock Request APIs

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/stock-requests/` | `logistics.views.StockRequestViewSet.list` | List stock requests |
| POST | `/stock-requests/` | `logistics.views.StockRequestViewSet.create` | Create stock request |
| GET | `/stock-requests/{id}/` | `logistics.views.StockRequestViewSet.retrieve` | Get request details |
| PUT | `/stock-requests/{id}/` | `logistics.views.StockRequestViewSet.update` | Update request |
| DELETE | `/stock-requests/{id}/` | `logistics.views.StockRequestViewSet.destroy` | Delete request |

---

## 🚛 Trip Management APIs

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/trips/` | `logistics.views.TripViewSet.list` | List all trips |
| POST | `/trips/` | `logistics.views.TripViewSet.create` | Create new trip |
| GET | `/trips/{id}/` | `logistics.views.TripViewSet.retrieve` | Get trip details |
| PUT | `/trips/{id}/` | `logistics.views.TripViewSet.update` | Update trip |
| DELETE | `/trips/{id}/` | `logistics.views.TripViewSet.destroy` | Delete trip |
| GET | `/trips/{id}/ms-fillings/` | `logistics.views.TripViewSet.ms_fillings` | Get MS filling records |
| GET | `/trips/{id}/dbs-decantings/` | `logistics.views.TripViewSet.dbs_decantings` | Get DBS decanting records |
| GET | `/trips/{id}/reconciliations/` | `logistics.views.TripViewSet.reconciliations` | Get reconciliation records |
| GET | `/driver/trip/status` | `logistics.views.TripViewSet.status` | Get trip status by token |

---

## 👨‍✈️ Driver Management APIs

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/drivers/` | `logistics.views.DriverViewSet.list` | List all drivers |
| POST | `/drivers/` | `logistics.views.DriverViewSet.create` | Create new driver |
| GET | `/drivers/{id}/` | `logistics.views.DriverViewSet.retrieve` | Get driver details |
| PUT | `/drivers/{id}/` | `logistics.views.DriverViewSet.update` | Update driver |
| DELETE | `/drivers/{id}/` | `logistics.views.DriverViewSet.destroy` | Delete driver |
| GET | `/driver/{id}/token` | `logistics.views.DriverViewSet.token` | Get active token |
| GET | `/driver/trips` | `logistics.views.DriverViewSet.current_driver_trips` | Get authenticated driver trips |
| GET | `/driver/{id}/trips` | `logistics.views.DriverViewSet.trips` | Get specific driver trips |

---

## 🚗 Vehicle Management APIs

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/vehicles/` | `logistics.views.VehicleViewSet.list` | List all vehicles |
| POST | `/vehicles/` | `logistics.views.VehicleViewSet.create` | Create new vehicle |
| GET | `/vehicles/{id}/` | `logistics.views.VehicleViewSet.retrieve` | Get vehicle details |
| PUT | `/vehicles/{id}/` | `logistics.views.VehicleViewSet.update` | Update vehicle |
| DELETE | `/vehicles/{id}/` | `logistics.views.VehicleViewSet.destroy` | Delete vehicle |

---

## ⏰ Shift Management APIs

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/shifts/` | `logistics.views.ShiftViewSet.list` | List all shifts |
| POST | `/shifts/` | `logistics.views.ShiftViewSet.create` | Create new shift |
| GET | `/shifts/{id}/` | `logistics.views.ShiftViewSet.retrieve` | Get shift details |
| PUT | `/shifts/{id}/` | `logistics.views.ShiftViewSet.update` | Update shift |
| DELETE | `/shifts/{id}/` | `logistics.views.ShiftViewSet.destroy` | Delete shift |
| POST | `/shifts/{id}/approve/` | `logistics.views.ShiftViewSet.approve` | Approve shift (EIC only) |
| POST | `/shifts/{id}/reject/` | `logistics.views.ShiftViewSet.reject` | Reject shift (EIC only) |

---

## 🚚 Driver Trip APIs

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/driver-trips/` | `logistics.driver_views.DriverTripViewSet.list` | List driver trips |
| GET | `/driver-trips/{id}/` | `logistics.driver_views.DriverTripViewSet.retrieve` | Get trip details |
| GET | `/driver-trips/{id}/resume/` | `logistics.driver_views.DriverTripViewSet.resume` | Resume trip |
| POST | `/driver-trips/{id}/accept/` | `logistics.driver_views.DriverTripViewSet.accept` | Accept trip |
| POST | `/driver-trips/{id}/reject/` | `logistics.driver_views.DriverTripViewSet.reject` | Reject trip |
| GET | `/driver/pending-offers` | `logistics.driver_views.DriverTripViewSet.pending_offers` | Get pending trip offers |
| POST | `/driver/arrival/ms` | `logistics.driver_views.DriverTripViewSet.arrival_at_ms` | Confirm arrival at MS |
| POST | `/driver/arrival/dbs` | `logistics.driver_views.DriverTripViewSet.arrival_at_dbs` | Confirm arrival at DBS |
| POST | `/driver/meter-reading/confirm` | `logistics.driver_views.DriverTripViewSet.confirm_meter_reading` | Confirm meter reading |
| POST | `/driver/location` | `logistics.views.DriverLocationView` | Update driver location |
| POST | `/driver/trip/complete` | `logistics.views.TripCompleteView` | Complete trip |
| POST | `/driver/emergency` | `logistics.views.EmergencyReportView` | Report emergency |

---

## 🏭 MS (Mother Station) APIs

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/ms/dashboard/` | `logistics.ms_views.MSDashboardView` | MS dashboard data |
| POST | `/ms/arrival/confirm` | `logistics.ms_views.MSConfirmArrivalView` | Confirm driver arrival |
| GET | `/ms/fill/resume` | `logistics.ms_views.MSFillResumeView` | Resume filling process |
| POST | `/ms/fill/start` | `logistics.ms_views.MSFillStartView` | Start filling |
| POST | `/ms/fill/end` | `logistics.ms_views.MSFillEndView` | End filling |
| POST | `/ms/fill/confirm` | `logistics.ms_views.MSConfirmFillingView` | Confirm filling |
| GET | `/ms/{ms_id}/transfers` | `logistics.ms_views.MSStockTransferListView` | Get stock transfers |
| GET | `/ms/{ms_id}/schedule` | `logistics.ms_views.MSTripScheduleView` | Get trip schedule |
| GET | `/ms/cluster` | `logistics.ms_views.MSClusterView` | Get MS cluster info |
| GET | `/ms/stock-transfers/by-dbs` | `logistics.ms_views.MSStockTransferHistoryByDBSView` | Get transfers by DBS |
| GET | `/ms/pending-arrivals` | `logistics.ms_views.MSPendingArrivalsView` | Get pending arrivals |

---

## 🏪 DBS (Daughter Booster Station) APIs

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/dbs/dashboard/` | `logistics.dbs_views.DBSDashboardView` | DBS dashboard data |
| GET | `/dbs/transfers` | `logistics.dbs_views.DBSStockTransferListView` | Get stock transfers |
| GET | `/dbs/pending-arrivals` | `logistics.dbs_views.DBSPendingArrivalsView` | Get pending arrivals |
| GET | `/dbs/stock-requests` | `logistics.dbs_views.DBSStockRequestViewSet.list` | List stock requests |
| POST | `/dbs/stock-requests/arrival/confirm` | `logistics.dbs_views.DBSStockRequestViewSet.confirm_arrival` | Confirm arrival |
| POST | `/dbs/stock-requests/decant/start` | `logistics.dbs_views.DBSStockRequestViewSet.decant_start` | Start decanting |
| POST | `/dbs/stock-requests/decant/end` | `logistics.dbs_views.DBSStockRequestViewSet.decant_end` | End decanting |
| POST | `/dbs/stock-requests/decant/confirm` | `logistics.dbs_views.DBSStockRequestViewSet.confirm_decanting` | Confirm decanting |

---

## 👔 EIC (Engineer-in-Charge) APIs

### Dashboard & Overview
| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/eic/dashboard` | `logistics.eic_views.EICDashboardView` | EIC dashboard data |
| GET | `/eic/permissions` | `logistics.eic_views.EICPermissionsView` | Get EIC permissions |
| GET | `/eic/network-overview` | `logistics.eic_views.EICNetworkOverviewView` | Network overview |
| GET | `/eic/network-stations` | `logistics.eic_views.EICNetworkStationsView` | Network stations |
| GET | `/eic/network-trips` | `logistics.eic_views.EICNetworkTripsView` | Network trips |

### Stock Requests
| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/eic/stock-requests/` | `logistics.eic_views.EICStockRequestViewSet.list` | List stock requests |
| POST | `/eic/stock-requests/{id}/approve/` | `logistics.eic_views.EICStockRequestViewSet.approve` | Approve request |
| POST | `/eic/stock-requests/{id}/reject/` | `logistics.eic_views.EICStockRequestViewSet.reject` | Reject request |
| POST | `/eic/stock-requests/{id}/assign-driver/` | `logistics.eic_views.EICStockRequestViewSet.assign_driver` | Assign driver |
| GET | `/eic/incoming-stock-requests` | `logistics.eic_views.EICIncomingStockRequestsView` | Get incoming requests |

### Cluster Management
| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/eic/clusters/` | `logistics.eic_management_views.EICClusterViewSet.list` | List clusters |
| POST | `/eic/clusters/` | `logistics.eic_management_views.EICClusterViewSet.create` | Create cluster |
| GET | `/eic/clusters/{id}/` | `logistics.eic_management_views.EICClusterViewSet.retrieve` | Get cluster details |
| PUT | `/eic/clusters/{id}/` | `logistics.eic_management_views.EICClusterViewSet.update` | Update cluster |
| DELETE | `/eic/clusters/{id}/` | `logistics.eic_management_views.EICClusterViewSet.destroy` | Delete cluster |

### Vehicle & Driver Management
| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/eic/driver-approvals/pending` | `logistics.eic_views.EICDriverApprovalView` | Get pending driver approvals |
| GET | `/eic/vehicles/active` | `logistics.eic_views.EICVehicleTrackingView` | Track active vehicles |
| GET | `/eic/vehicle-queue` | `logistics.eic_management_views.EICVehicleQueueView` | Get vehicle queue |

### Reconciliation & Alerts
| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/eic/reconciliation/` | `logistics.reconciliation_views.ReconciliationListView` | List reconciliations |
| POST | `/eic/reconciliation-reports/{id}/action` | `logistics.eic_views.EICReconciliationActionView` | Take action on report |
| GET | `/eic/alerts` | `logistics.eic_views.EICAlertListView` | List alerts |

### Stock Transfers
| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/eic/stock-transfers` | `logistics.eic_management_views.EICStockTransfersByDBSView` | Get stock transfers |
| GET | `/eic/stock-transfers/ms-dbs` | `logistics.eic_management_views.EICStockTransferMSDBSView` | Get MS-DBS transfers |
| GET | `/eic/stock-transfers/by-dbs` | `logistics.eic_management_views.EICStockTransfersByDBSView` | Get transfers by DBS |

---

## 👤 Customer (FDODO) APIs

| Method | Endpoint | View Handler | Description |
|--------|----------|--------------|-------------|
| GET | `/customer/dashboard` | `logistics.customer_views.CustomerDashboardView` | Customer dashboard |
| GET | `/customer/stocks` | `logistics.customer_views.CustomerStocksView` | Get stock levels |
| GET | `/customer/transport` | `logistics.customer_views.CustomerTransportView` | Get transport info |
| GET | `/customer/transfers` | `logistics.customer_views.CustomerTransfersView` | Get transfer history |
| GET | `/customer/pending-trips` | `logistics.customer_views.CustomerPendingTripsView` | Get pending trips |
| GET | `/customer/permissions` | `logistics.customer_views.CustomerPermissionsView` | Get permissions |
| POST | `/customer/trips/{trip_id}/accept` | `logistics.customer_views.CustomerTripAcceptView` | Accept trip |

---

## 📊 Summary by Module

| Module | Total Endpoints | View Files |
|--------|----------------|------------|
| **Authentication** | 9 | `core/views.py` |
| **User Management** | 9 | `core/views.py` |
| **Role Management** | 6 | `core/views.py`, `core/permission_views.py` |
| **Permissions** | 12 | `core/permission_views.py` |
| **Stations & Routes** | 15 | `core/views.py` |
| **Notifications** | 10 | `core/views.py`, `core/notification_views.py` |
| **Stock Requests** | 5 | `logistics/views.py` |
| **Trips** | 10 | `logistics/views.py` |
| **Drivers** | 7 | `logistics/views.py` |
| **Vehicles** | 5 | `logistics/views.py` |
| **Shifts** | 7 | `logistics/views.py` |
| **Driver Operations** | 11 | `logistics/driver_views.py`, `logistics/views.py` |
| **MS Operations** | 11 | `logistics/ms_views.py` |
| **DBS Operations** | 8 | `logistics/dbs_views.py` |
| **EIC Operations** | 20 | `logistics/eic_views.py`, `logistics/eic_management_views.py` |
| **Customer Operations** | 7 | `logistics/customer_views.py` |
| **SAP Integration** | 1 | `core/sap_views.py` |
| **TOTAL** | **153 APIs** | **15 View Files** |

---

## 🔍 Quick Search by Role

### Driver APIs
- `/driver/*` - 11 endpoints in `logistics/driver_views.py`, `logistics/views.py`

### MS Operator APIs
- `/ms/*` - 11 endpoints in `logistics/ms_views.py`

### DBS Operator APIs
- `/dbs/*` - 8 endpoints in `logistics/dbs_views.py`

### EIC APIs
- `/eic/*` - 20 endpoints in `logistics/eic_views.py`, `logistics/eic_management_views.py`

### Customer APIs
- `/customer/*` - 7 endpoints in `logistics/customer_views.py`

### Admin APIs
- `/users/*`, `/roles/*`, `/permissions/*` - 27 endpoints in `core/views.py`, `core/permission_views.py`

---

## 📝 Notes

1. **Authentication Required**: Most endpoints require authentication token in header: `Authorization: Token <token>`
2. **Permissions**: Some endpoints require specific role permissions
3. **Pagination**: List endpoints support pagination (default 50 items per page)
4. **Filtering**: Many list endpoints support query parameters for filtering
5. **ViewSets**: Endpoints with ViewSets automatically support CRUD operations

---

**Last Updated**: 2024
**Total APIs**: 153
**View Files**: 15
