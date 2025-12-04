"""
Notification Service for GTS Backend
Handles FCM device token registration and push notification sending.
"""
from django.db import models
from django.conf import settings
from core.models import User


class DeviceToken(models.Model):
    """
    Stores FCM device tokens for push notifications.
    Each user can have multiple devices (phone, tablet, etc.)
    """
    TYPE_CHOICES = [
        ('DRIVER', 'Driver'),
        ('DBS', 'DBS Operator'),
        ('MS', 'MS Operator'),
        ('EIC', 'EIC/Transport Admin'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='device_tokens')
    token = models.CharField(max_length=500, unique=True)
    device_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='DRIVER')
    platform = models.CharField(max_length=20, default='unknown')  # ios, android
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'device_tokens'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['token']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.device_type} ({self.token[:20]}...)"


class NotificationLog(models.Model):
    """
    Logs all sent notifications for audit and debugging.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SENT', 'Sent'),
        ('DELIVERED', 'Delivered'),
        ('FAILED', 'Failed'),
    ]
    
    TYPE_CHOICES = [
        ('trip_assignment', 'Trip Assignment'),
        ('trip_update', 'Trip Update'),
        ('dbs_arrival', 'DBS Arrival'),
        ('ms_arrival', 'MS Arrival'),
        ('stock_approved', 'Stock Request Approved'),
        ('variance_alert', 'Variance Alert'),
        ('emergency', 'Emergency'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    title = models.CharField(max_length=255)
    body = models.TextField()
    data = models.JSONField(default=dict)  # Custom payload
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    fcm_message_id = models.CharField(max_length=255, null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'notification_logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.notification_type} to {self.user.email} - {self.status}"
