"""
Django signals for logistics app.
Auto-creates User accounts for Drivers when they are created.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction

from .models import Driver, Trip, Reconciliation
from core.models import User, Role, UserRole
import logging

logger = logging.getLogger(__name__)


def generate_driver_email(driver):
    """Generate email for driver based on phone number or name."""
    if driver.phone:
        phone_clean = ''.join(filter(str.isdigit, driver.phone))
        return f"driver_{phone_clean}@gts.local"
    name_clean = driver.full_name.lower().replace(' ', '_')
    return f"driver_{name_clean}_{driver.id}@gts.local"


def generate_default_password(driver):
    """Generate default password for driver.
    Format: driver_<last4digits_of_phone>
    """
    if driver.phone:
        phone_clean = ''.join(filter(str.isdigit, driver.phone))[-4:]
        return f"driver_{phone_clean}"
    return f"driver_{driver.id}"


@receiver(post_save, sender=Driver)
def create_user_for_driver(sender, instance, created, **kwargs):
    """
    Auto-create User account when a Driver is created.
    This allows drivers to login from the mobile app.
    """
    if instance.user is not None:
        return
    
    if hasattr(instance, '_creating_user'):
        return
    
    try:
        instance._creating_user = True
        
        email = generate_driver_email(instance)
        password = generate_default_password(instance)
        
        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            instance.user = existing_user
            instance.save(update_fields=['user'])
            return
        
        user = User.objects.create_user(
            email=email,
            password=password,
            full_name=instance.full_name,
            phone=instance.phone or ''
        )
        
        instance.user = user
        instance.save(update_fields=['user'])
        
        driver_role, _ = Role.objects.get_or_create(
            code='DRIVER',
            defaults={
                'name': 'Driver',
                'description': 'HCV Truck Driver'
            }
        )
        
        UserRole.objects.get_or_create(
            user=user,
            role=driver_role,
            defaults={'active': True}
        )
        
        print(f"[Driver Signal] Created user {email} for driver {instance.full_name}")
        
    except Exception as e:
        print(f"[Driver Signal] Error creating user for driver {instance.full_name}: {e}")
    finally:
        delattr(instance, '_creating_user')


@receiver(post_save, sender=Trip)
def auto_create_reconciliation(sender, instance, created, **kwargs):
    """
    Auto-create reconciliation when trip status = COMPLETED.
    Prevents duplicates and sends variance alerts.
    """
    if not created and instance.status == 'COMPLETED':
        if Reconciliation.objects.filter(trip=instance).exists():
            return
        
        try:
            ms_filling = instance.ms_fillings.first()
            ms_filled_qty = float(ms_filling.filled_qty_kg) if ms_filling and ms_filling.filled_qty_kg else 0
            
            dbs_decanting = instance.dbs_decantings.first()
            dbs_delivered_qty = float(dbs_decanting.delivered_qty_kg) if dbs_decanting and dbs_decanting.delivered_qty_kg else 0
            
            if ms_filled_qty > 0:
                diff_qty = ms_filled_qty - dbs_delivered_qty
                variance_pct = (diff_qty / ms_filled_qty) * 100
                reconciliation_status = 'ALERT' if abs(variance_pct) > 0.5 else 'OK'
                
                Reconciliation.objects.create(
                    trip=instance,
                    ms_filled_qty_kg=ms_filled_qty,
                    dbs_delivered_qty_kg=dbs_delivered_qty,
                    diff_qty=diff_qty,
                    variance_pct=variance_pct,
                    status=reconciliation_status
                )
                logger.info(f"Auto-created reconciliation for trip {instance.id}")
                
                if reconciliation_status == 'ALERT':
                    try:
                        from core.notification_service import NotificationService
                        ms = instance.ms
                        if ms:
                            eic_roles = UserRole.objects.filter(station=ms, role__code='EIC', active=True).select_related('user')
                            notifier = NotificationService()
                            for eic_role in eic_roles:
                                if eic_role.user:
                                    notifier.send_to_user(
                                        user=eic_role.user,
                                        title="⚠️ Variance Alert",
                                        body=f"Trip {instance.token.token_no if instance.token else instance.id}: {abs(variance_pct):.2f}% variance",
                                        data={'type': 'VARIANCE_ALERT', 'trip_id': str(instance.id), 'variance_pct': str(round(abs(variance_pct), 2))},
                                        notification_type='alert'
                                    )
                    except Exception as e:
                        logger.error(f"Failed to send variance alert for trip {instance.id}: {e}")
        except Exception as e:
            logger.error(f"Failed to auto-create reconciliation for trip {instance.id}: {e}")
