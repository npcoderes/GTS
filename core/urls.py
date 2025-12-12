"""
URL configuration for core app API
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core import views
from core.sap_views import SAPStationView
from core.permission_views import (
    user_permissions_view, PermissionViewSet, RolePermissionViewSet, 
    UserPermissionViewSet, RoleListWithPermissionsView
)



router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'roles', views.RoleViewSet, basename='role')
router.register(r'user-roles', views.UserRoleViewSet, basename='user-role')
router.register(r'stations', views.StationViewSet, basename='station')
router.register(r'routes', views.RouteViewSet, basename='route')
router.register(r'ms-dbs-maps', views.MSDBSMapViewSet, basename='ms-dbs-map')

# Permission management routers
router.register(r'permissions', PermissionViewSet, basename='permission')
router.register(r'role-permissions', RolePermissionViewSet, basename='role-permission')
router.register(r'user-permissions', UserPermissionViewSet, basename='user-permission')

urlpatterns = [
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('auth/me/', views.current_user_view, name='current-user'),
    path('auth/choose-role', views.choose_role_view, name='choose-role'),
    path('auth/permissions/', user_permissions_view, name='user-permissions'),
    path('auth/change-password/', views.change_password, name='change-password'),
    path('auth/mpin/set/', views.set_mpin, name='set-mpin'),
    
    # Forgot Password Flow
    path('auth/forgot-password/request/', views.request_password_reset, name='forgot-password-request'),
    path('auth/forgot-password/verify/', views.verify_reset_otp, name='forgot-password-verify'),
    path('auth/forgot-password/confirm/', views.confirm_password_reset, name='forgot-password-confirm'),
    
    # Permission management
    path('roles-with-permissions/', RoleListWithPermissionsView.as_view(), name='roles-with-permissions'),
    
    # FCM Notifications
    path('notifications/register-token', views.register_fcm_token, name='register-fcm-token'),
    path('notifications/unregister-token', views.unregister_fcm_token, name='unregister-fcm-token'),
    path('notifications/send', views.send_notification, name='send-notification'),
    path('notifications/send-to-me', views.send_notification_to_me, name='send-notification-to-me'),
    
    # SAP Integration
    path('sap/stations/', SAPStationView.as_view(), name='sap-stations'),
    
    path('', include(router.urls)),
]

