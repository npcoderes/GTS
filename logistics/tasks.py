"""
Celery tasks for logistics app.

Handles background jobs like expired assignment cleanup and EIC notifications.
"""
import logging
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)

# Get timeout from Django settings (default 5 minutes)
ASSIGNMENT_TIMEOUT_SECONDS = getattr(settings, 'DRIVER_ASSIGNMENT_TIMEOUT_SECONDS', 300)


@shared_task(name='logistics.check_expired_driver_assignments')
def check_expired_driver_assignments():
    """
    Periodic task to check for expired driver assignments.
    
    If a driver hasn't accepted a trip within 5 minutes:
    1. Reset StockRequest status from ASSIGNING to PENDING
    2. Clear assignment fields (target_driver, assignment_started_at)
    3. Notify EIC users to reassign
    
    This task should run every 1-2 minutes via Celery Beat.
    """
    from .models import StockRequest, Driver
    from core.models import UserRole
    
    now = timezone.now()
    cutoff = now - timedelta(seconds=ASSIGNMENT_TIMEOUT_SECONDS)
    
    # Find expired assignments
    expired_requests = StockRequest.objects.filter(
        status='ASSIGNING',
        assignment_started_at__isnull=False,
        assignment_started_at__lt=cutoff
    ).select_related('dbs', 'dbs__parent_station', 'target_driver', 'target_driver__user')
    
    expired_count = 0
    
    for stock_request in expired_requests:
        driver = stock_request.target_driver
        driver_name = driver.full_name if driver else 'Unknown Driver'
        driver_id = driver.id if driver else None
        dbs_name = stock_request.dbs.name if stock_request.dbs else 'Unknown DBS'
        ms = stock_request.dbs.parent_station if stock_request.dbs else None
        
        logger.info(
            f"Assignment expired for StockRequest #{stock_request.id}: "
            f"Driver {driver_name} (ID: {driver_id}) did not accept within 5 minutes. "
            f"DBS: {dbs_name}"
        )
        
        # Reset stock request for reassignment (back to PENDING so EIC can reassign)
        stock_request.status = 'PENDING'
        stock_request.target_driver = None
        stock_request.assignment_started_at = None
        stock_request.assignment_mode = None
        stock_request.save(update_fields=[
            'status', 'target_driver', 'assignment_started_at', 'assignment_mode'
        ])
        
        expired_count += 1
        
        # Notify EIC users
        notify_eic_assignment_expired.delay(
            stock_request_id=stock_request.id,
            driver_id=driver_id,
            driver_name=driver_name,
            dbs_name=dbs_name,
            ms_id=ms.id if ms else None
        )
    
    if expired_count > 0:
        logger.info(f"Processed {expired_count} expired driver assignment(s)")
    
    return {'expired_count': expired_count}


@shared_task(name='logistics.notify_eic_assignment_expired')
def notify_eic_assignment_expired(stock_request_id, driver_id, driver_name, dbs_name, ms_id=None):
    """
    Send notification to EIC users when a driver assignment expires.
    
    Finds EIC users assigned to the relevant MS station and sends FCM push.
    """
    from core.models import UserRole
    
    logger.info(
        f"Notifying EIC about expired assignment: StockRequest #{stock_request_id}, "
        f"Driver: {driver_name}"
    )
    
    # Find EIC users to notify
    eic_roles_qs = UserRole.objects.filter(
        role__code='EIC',
        active=True
    ).select_related('user', 'station')
    
    # Filter by MS if known
    if ms_id:
        eic_roles_qs = eic_roles_qs.filter(station_id=ms_id)
    
    eic_users = [ur.user for ur in eic_roles_qs if ur.user]
    
    if not eic_users:
        logger.warning(f"No EIC users found to notify for StockRequest #{stock_request_id}")
        return {'notified': 0}
    
    # Send FCM notifications
    notified_count = 0
    try:
        from core.notification_service import NotificationService
        notification_service = NotificationService()
        
        for user in eic_users:
            try:
                notification_service.send_to_user(
                    user=user,
                    title="Driver Assignment Expired",
                    body=f"{driver_name} did not accept the trip to {dbs_name}. Please reassign.",
                    data={
                        'type': 'ASSIGNMENT_EXPIRED',
                        'stock_request_id': str(stock_request_id),
                        'driver_id': str(driver_id) if driver_id else '',
                        'driver_name': driver_name,
                        'dbs_name': dbs_name,
                        'action': 'REASSIGN_REQUIRED'
                    }
                )
                notified_count += 1
                logger.info(f"Notified EIC user {user.email} about expired assignment")
            except Exception as e:
                logger.error(f"Failed to notify EIC user {user.email}: {e}")
    except Exception as e:
        logger.error(f"Notification service error: {e}")
    
    return {'notified': notified_count}
