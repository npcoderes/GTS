from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StockRequestViewSet, TripViewSet, DriverViewSet, ShiftViewSet, VehicleViewSet,
    DriverLocationView, DriverArrivalMSView, DriverArrivalDBSView,
    MeterReadingConfirmationView, TripCompleteView, EmergencyReportView
)
from .eic_views import (
    EICStockRequestViewSet, EICDashboardView, 
    EICDriverApprovalView, EICPermissionsView,
    EICNetworkOverviewView, EICReconciliationActionView, EICVehicleTrackingView, EICNetworkStationsView,EICNetworkTripsView,
    EICIncomingStockRequestsView, EICAlertListView, EICShiftHistoryView
)
from .reconciliation_views import ReconciliationListView
from .customer_views import (
    CustomerDashboardView,
    CustomerStocksView,
    CustomerTransportView,
    CustomerTransfersView,
    CustomerPendingTripsView,
    CustomerPermissionsView,
    CustomerTripAcceptView,
)
from .dbs_views import DBSDashboardView, DBSPendingArrivalsView
from .dbs_views import DBSStockTransferListView, DBSStockRequestViewSet
from .driver_views import DriverTripViewSet
from .ms_views import (
    MSFillPrefillView, MSFillStartView, MSFillEndView, MSStockTransferListView,
    MSTripScheduleView, MSDashboardView, MSConfirmArrivalView, MSConfirmFillingView,
    MSClusterView, MSStockTransferHistoryByDBSView, MSPendingArrivalsView, MSFillResumeView
)
from .eic_management_views import EICVehicleQueueView, EICClusterViewSet, EICStockTransferMSDBSView, EICStockTransfersByDBSView
from .timesheet_views import (
    TimesheetView, TimesheetAssignView, TimesheetUpdateView, TimesheetDeleteView,
    TimesheetCopyWeekView, TimesheetFillWeekView, TimesheetFillMonthView, TimesheetClearWeekView,
    ShiftTemplateViewSet
)
from .token_views import DriverTokenViewSet, EICQueueView, EICQueueAllocationView
# from .ocr_views import OCRExtractTextView
# from .ocr_paddleocr_views import PaddleOCRExtractTextView

# Notification Views
from core.notification_views import (
    DriverNotificationRegisterView, DriverNotificationUnregisterView,
    DBSNotificationRegisterView, DBSNotificationUnregisterView,
    MSNotificationRegisterView, MSNotificationUnregisterView
)

router = DefaultRouter()
router.register(r'stock-requests', StockRequestViewSet)
router.register(r'trips', TripViewSet)
router.register(r'drivers', DriverViewSet)
router.register(r'shifts', ShiftViewSet)
router.register(r'vehicles', VehicleViewSet)

# EIC Router
eic_router = DefaultRouter()
eic_router.register(r'stock-requests', EICStockRequestViewSet, basename='eic-stock-requests')
eic_router.register(r'clusters', EICClusterViewSet, basename='eic-clusters')

# Shift Template Router
template_router = DefaultRouter()
template_router.register(r'shift-templates', ShiftTemplateViewSet, basename='shift-templates')

# Driver Router
router.register(r'driver-trips', DriverTripViewSet, basename='driver-trips')

urlpatterns = [
    path('', include(router.urls)),
    
    # EIC API
    path('eic/', include(eic_router.urls)),
    path('eic/dashboard', EICDashboardView.as_view(), name='eic-dashboard'),
    path('eic/driver-approvals/pending', EICDriverApprovalView.as_view(), name='eic-driver-approvals'),
    path('eic/driver-approvals/history', EICShiftHistoryView.as_view(), name='eic-shift-history'),
    path('eic/permissions', EICPermissionsView.as_view(), name='eic-permissions'),
    path('eic/network-overview', EICNetworkOverviewView.as_view(), name='eic-network-overview'),
    path('eic/network-stations', EICNetworkStationsView.as_view(), name='eic-network-stations'),
    path('eic/network-trips', EICNetworkTripsView.as_view(), name='eic-network-trips'),
    # path('eic/reconciliation-reports', EICReconciliationReportView.as_view(), name='eic-reconciliation-reports'),
    path('eic/reconciliation/', ReconciliationListView.as_view(), name='reconciliation-list'),
    path('eic/reconciliation-reports/<int:report_id>/action', EICReconciliationActionView.as_view(), name='eic-reconciliation-action'),
    path('eic/vehicles/active', EICVehicleTrackingView.as_view(), name='eic-vehicle-tracking'),
    path('eic/incoming-stock-requests', EICIncomingStockRequestsView.as_view(), name='eic-incoming-stock-requests'),
    path('eic/alerts', EICAlertListView.as_view(), name='eic-alerts'),
    path('eic/stock-transfers', EICStockTransfersByDBSView.as_view(), name='eic-stock-transfers'),
    path('eic/stock-transfers/ms-dbs', EICStockTransferMSDBSView.as_view(), name='eic-stock-transfers-ms-dbs'),
    path('eic/stock-transfers/by-dbs', EICStockTransfersByDBSView.as_view(), name='eic-stock-transfers-by-dbs'),
    
    # EIC Vehicle Queue (Token Queue System)
    path('eic/token-queue', EICQueueView.as_view(), name='eic-token-queue'),
    path('eic/token-queue/allocate', EICQueueAllocationView.as_view(), name='eic-token-allocate'),

    # DBS API
    path('dbs/dashboard/', DBSDashboardView.as_view(), name='dbs-dashboard'),
    path('dbs/transfers', DBSStockTransferListView.as_view(), name='dbs-transfers'),
    
    # Note: Approve/reject uses existing shift endpoints: /api/shifts/{id}/approve/ and /api/shifts/{id}/reject/
    
    # Driver API
    path('driver/location', DriverLocationView.as_view()),
    path('driver/pending-offers', DriverTripViewSet.as_view({'get': 'pending_offers'}), name='driver-pending-offers'),
    path('driver/arrival/ms', DriverTripViewSet.as_view({'post': 'arrival_at_ms'})),
    path('driver/arrival/dbs', DriverTripViewSet.as_view({'post': 'arrival_at_dbs'})), 
    path('driver/meter-reading/confirm', DriverTripViewSet.as_view({'post': 'confirm_meter_reading'})),
    path('driver/trip/complete', TripCompleteView.as_view()),
    path('driver/emergency', EmergencyReportView.as_view()),
    path('driver/trip/status', TripViewSet.as_view({'get': 'status'})),
    path('driver/<int:pk>/token', DriverViewSet.as_view({'get': 'token'})),
    path('driver/trips', DriverViewSet.as_view({'get': 'current_driver_trips'})),
    path('driver/<int:pk>/trips', DriverViewSet.as_view({'get': 'trips'})),
    
    # Driver Notification Registration
    path('driver/notifications/register', DriverNotificationRegisterView.as_view(), name='driver-notif-register'),
    path('driver/notifications/unregister', DriverNotificationUnregisterView.as_view(), name='driver-notif-unregister'),
    
    # Driver Token Queue
    path('driver/token/request', DriverTokenViewSet.as_view({'post': 'request'}), name='driver-token-request'),
    path('driver/token/current', DriverTokenViewSet.as_view({'get': 'current'}), name='driver-token-current'),
    path('driver/token/cancel', DriverTokenViewSet.as_view({'post': 'cancel'}), name='driver-token-cancel'),
    path('driver/token/shift-details', DriverTokenViewSet.as_view({'get': 'shift_details'}), name='driver-shift-details'),

    # MS API
    path('ms/dashboard/', MSDashboardView.as_view(), name='ms-dashboard'),
    path('ms/arrival/confirm', MSConfirmArrivalView.as_view(), name='ms-arrival-confirm'),
    path('ms/fill/resume', MSFillResumeView.as_view(), name='ms-fill-resume'),
    path('ms/fill/start', MSFillStartView.as_view(), name='ms-fill-start'),
    path('ms/fill/end', MSFillEndView.as_view(), name='ms-fill-end'),
    path('ms/fill/confirm', MSConfirmFillingView.as_view(), name='ms-fill-confirm'),

    path('ms/<str:ms_id>/transfers', MSStockTransferListView.as_view(), name='ms-transfers'),
    path('ms/<str:ms_id>/schedule', MSTripScheduleView.as_view(), name='ms-trip-schedule'),
    
    # MS App Stock Transfer Screens  APP  APIS 
    path('ms/cluster', MSClusterView.as_view(), name='ms-cluster'),
    path('ms/stock-transfers/by-dbs', MSStockTransferHistoryByDBSView.as_view(), name='ms-stock-transfers-by-dbs'),
    
    # MS Notification Registration
    path('ms/notifications/register', MSNotificationRegisterView.as_view(), name='ms-notif-register'),
    path('ms/notifications/unregister', MSNotificationUnregisterView.as_view(), name='ms-notif-unregister'),
    
    # MS Pending Arrivals (fallback for missed notifications)
    path('ms/pending-arrivals', MSPendingArrivalsView.as_view(), name='ms-pending-arrivals'),
    
    # EIC Management
    path('eic/vehicle-queue', EICVehicleQueueView.as_view(), name='eic-vehicle-queue'),

    # DBS Notification Registration apps
    path('dbs/notifications/register', DBSNotificationRegisterView.as_view(), name='dbs-notif-register'),
    path('dbs/notifications/unregister', DBSNotificationUnregisterView.as_view(), name='dbs-notif-unregister'),
    
    # DBS Pending Arrivals (fallback for missed notifications)
    path('dbs/pending-arrivals', DBSPendingArrivalsView.as_view(), name='dbs-pending-arrivals'),
    
    # DBS Stock Requests apps
    path('dbs/stock-requests', DBSStockRequestViewSet.as_view({'get': 'list'}), name='dbs-stock-requests'),
    path('dbs/stock-requests/arrival/confirm', DBSStockRequestViewSet.as_view({'post': 'confirm_arrival'}), name='dbs-stock-request-confirm-arrival'),
    path('dbs/stock-requests/decant/resume', DBSStockRequestViewSet.as_view({'post': 'decant_resume'}), name='dbs-decant-resume'),
    path('dbs/stock-requests/decant/start', DBSStockRequestViewSet.as_view({'post': 'decant_start'}), name='dbs-decant-start'),
    path('dbs/stock-requests/decant/end', DBSStockRequestViewSet.as_view({'post': 'decant_end'}), name='dbs-decant-end'),
    path('dbs/stock-requests/decant/confirm', DBSStockRequestViewSet.as_view({'post': 'confirm_decanting'}), name='dbs-decant-confirm'),

    # Customer API (DBS-facing) - DBS resolved from token
    path('customer/dashboard', CustomerDashboardView.as_view(), name='customer-dashboard'),
    path('customer/stocks', CustomerStocksView.as_view(), name='customer-stocks'),
    path('customer/transport', CustomerTransportView.as_view(), name='customer-transport'),
    path('customer/transfers', CustomerTransfersView.as_view(), name='customer-transfers'),
    path('customer/pending-trips', CustomerPendingTripsView.as_view(), name='customer-pending-trips'),
    path('customer/permissions', CustomerPermissionsView.as_view(), name='customer-permissions'),
    path('customer/trips/<int:trip_id>/accept', CustomerTripAcceptView.as_view(), name='customer-trip-accept'),

    # OCR
    # path('ocr/extract-text', OCRExtractTextView.as_view(), name='ocr-extract-text'),
    # path('ocr/extract-text-paddle', PaddleOCRExtractTextView.as_view(), name='ocr-extract-text-paddle'),

    # Timesheet Management
    path('', include(template_router.urls)),
    path('timesheet/', TimesheetView.as_view(), name='timesheet'),
    path('timesheet/assign/', TimesheetAssignView.as_view(), name='timesheet-assign'),
    path('timesheet/update/', TimesheetUpdateView.as_view(), name='timesheet-update'),
    path('timesheet/delete/', TimesheetDeleteView.as_view(), name='timesheet-delete'),
    path('timesheet/copy-week/', TimesheetCopyWeekView.as_view(), name='timesheet-copy-week'),
    path('timesheet/fill-week/', TimesheetFillWeekView.as_view(), name='timesheet-fill-week'),
    path('timesheet/fill-month/', TimesheetFillMonthView.as_view(), name='timesheet-fill-month'),
    path('timesheet/clear-week/', TimesheetClearWeekView.as_view(), name='timesheet-clear-week'),
]
