"""
URL configuration for core app API
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'roles', views.RoleViewSet, basename='role')
router.register(r'user-roles', views.UserRoleViewSet, basename='user-role')
router.register(r'stations', views.StationViewSet, basename='station')
router.register(r'routes', views.RouteViewSet, basename='route')
router.register(r'ms-dbs-maps', views.MSDBSMapViewSet, basename='ms-dbs-map')

urlpatterns = [
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('auth/me/', views.current_user_view, name='current-user'),
    path('auth/choose-role', views.choose_role_view, name='choose-role'),
    
    # FCM Notifications
    path('notifications/register-token', views.register_fcm_token, name='register-fcm-token'),
    path('notifications/unregister-token', views.unregister_fcm_token, name='unregister-fcm-token'),
    path('notifications/send', views.send_notification, name='send-notification'),
    path('notifications/send-to-me', views.send_notification_to_me, name='send-notification-to-me'),
    
    path('', include(router.urls)),
]
