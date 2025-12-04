from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StockRequestViewSet, TripViewSet, DriverViewSet, ShiftViewSet, VehicleViewSet,
    DriverLocationView, DriverArrivalMSView, DriverArrivalDBSView,
    MeterReadingConfirmationView, TripCompleteView, EmergencyReportView,
    MSConfirmArrivalView, MSPreReadingView, MSPostReadingView, MSConfirmSAPView,
    DBSDecantArriveView, DBSDecantPreView, DBSDecantStartView, DBSDecantEndView, DBSDecantConfirmView
)
from .eic_views import (
    EICStockRequestViewSet, EICDashboardView, 
    EICDriverApprovalView, EICPermissionsView,
    EICNetworkOverviewView, EICReconciliationReportView, EICReconciliationActionView,
    EICVehicleTrackingView, EICIncomingStockRequestsView
)
from .dbs_views import DBSDashboardView
from .dbs_views import DBSStockTransferListView
from .driver_views import DriverTripViewSet
from .ms_views import MSFillPrefillView, MSFillStartView, MSFillEndView, STOGenerateView, MSStockTransferListView, MSTripScheduleView
from .eic_management_views import EICVehicleQueueView, EICClusterViewSet, EICStockTransferMSDBSView, EICStockTransfersByDBSView

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

# Driver Router
router.register(r'driver-trips', DriverTripViewSet, basename='driver-trips')

urlpatterns = [
    path('', include(router.urls)),
    
    # EIC API
    path('eic/', include(eic_router.urls)),
    path('eic/dashboard', EICDashboardView.as_view(), name='eic-dashboard'),
    path('eic/driver-approvals/pending', EICDriverApprovalView.as_view(), name='eic-driver-approvals'),
    path('eic/permissions', EICPermissionsView.as_view(), name='eic-permissions'),
    path('eic/network-overview', EICNetworkOverviewView.as_view(), name='eic-network-overview'),
    path('eic/reconciliation-reports', EICReconciliationReportView.as_view(), name='eic-reconciliation-reports'),
    path('eic/reconciliation-reports/<int:report_id>/action', EICReconciliationActionView.as_view(), name='eic-reconciliation-action'),
    path('eic/vehicles/active', EICVehicleTrackingView.as_view(), name='eic-vehicle-tracking'),
    path('eic/incoming-stock-requests', EICIncomingStockRequestsView.as_view(), name='eic-incoming-stock-requests'),
    path('eic/stock-transfers', EICStockTransfersByDBSView.as_view(), name='eic-stock-transfers'),
    path('eic/stock-transfers/ms-dbs', EICStockTransferMSDBSView.as_view(), name='eic-stock-transfers-ms-dbs'),
    path('eic/stock-transfers/by-dbs', EICStockTransfersByDBSView.as_view(), name='eic-stock-transfers-by-dbs'),

    
    # DBS API
    path('dbs/dashboard/', DBSDashboardView.as_view(), name='dbs-dashboard'),
    path('dbs/transfers', DBSStockTransferListView.as_view(), name='dbs-transfers'),
    
    # Note: Approve/reject uses existing shift endpoints: /api/shifts/{id}/approve/ and /api/shifts/{id}/reject/
    
    # Driver API
    path('driver/location', DriverLocationView.as_view()),
    path('driver/arrival/ms', DriverArrivalMSView.as_view()),
    path('driver/arrival/dbs', DriverArrivalDBSView.as_view()),
    path('driver/meter-reading/confirm', MeterReadingConfirmationView.as_view()),
    path('driver/trip/complete', TripCompleteView.as_view()),
    path('driver/emergency', EmergencyReportView.as_view()),
    path('driver/trip/<int:pk>/accept', TripViewSet.as_view({'post': 'accept'})),
    path('driver/trip/<int:pk>/reject', TripViewSet.as_view({'post': 'reject'})),
    path('driver/trip/status', TripViewSet.as_view({'get': 'status'})),
    path('driver/<int:pk>/token', DriverViewSet.as_view({'get': 'token'})),
    path('driver/<int:pk>/trips', DriverViewSet.as_view({'get': 'trips'})),
    
    # Driver Notification Registration
    path('driver/notifications/register', DriverNotificationRegisterView.as_view(), name='driver-notif-register'),
    path('driver/notifications/unregister', DriverNotificationUnregisterView.as_view(), name='driver-notif-unregister'),

    # MS API
    path('ms/confirm-arrival', MSConfirmArrivalView.as_view()),
    path('ms/pre-reading', MSPreReadingView.as_view()),
    path('ms/post-reading', MSPostReadingView.as_view()),
    path('ms/confirm-sap', MSConfirmSAPView.as_view()),
    
    # MS Filling API (Token-based for mobile app)
    path('ms/fill/<str:token_id>/prefill', MSFillPrefillView.as_view(), name='ms-fill-prefill'),
    path('ms/fill/<str:token_id>/start', MSFillStartView.as_view(), name='ms-fill-start'),
    path('ms/fill/<str:token_id>/end', MSFillEndView.as_view(), name='ms-fill-end'),
    path('sto/<int:trip_id>/generate', STOGenerateView.as_view(), name='sto-generate'),
    path('ms/<str:ms_id>/transfers', MSStockTransferListView.as_view(), name='ms-transfers'),
    path('ms/<str:ms_id>/schedule', MSTripScheduleView.as_view(), name='ms-trip-schedule'),
    
    # MS Notification Registration
    path('ms/notifications/register', MSNotificationRegisterView.as_view(), name='ms-notif-register'),
    path('ms/notifications/unregister', MSNotificationUnregisterView.as_view(), name='ms-notif-unregister'),
    
    # EIC Management
    path('eic/vehicle-queue', EICVehicleQueueView.as_view(), name='eic-vehicle-queue'),

    # DBS Decanting API
    path('dbs/decant/arrive', DBSDecantArriveView.as_view()),
    path('dbs/decant/pre', DBSDecantPreView.as_view()),
    path('dbs/decant/start', DBSDecantStartView.as_view()),
    path('dbs/decant/end', DBSDecantEndView.as_view()),
    path('dbs/decant/confirm', DBSDecantConfirmView.as_view()),
    
    # DBS Notification Registration
    path('dbs/notifications/register', DBSNotificationRegisterView.as_view(), name='dbs-notif-register'),
    path('dbs/notifications/unregister', DBSNotificationUnregisterView.as_view(), name='dbs-notif-unregister'),
]

