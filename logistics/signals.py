"""
Django signals for logistics app.
Auto-creates User accounts for Drivers when they are created.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction

from .models import Driver
from core.models import User, Role, UserRole


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
    # Only process new drivers without user accounts
    if instance.user is not None:
        return
    
    # Avoid recursive saves
    if hasattr(instance, '_creating_user'):
        return
    
    try:
        instance._creating_user = True
        
        email = generate_driver_email(instance)
        password = generate_default_password(instance)
        
        # Check if email already exists
        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            instance.user = existing_user
            instance.save(update_fields=['user'])
            return
        
        # Create new User
        user = User.objects.create_user(
            email=email,
            password=password,
            full_name=instance.full_name,
            phone=instance.phone or ''
        )
        
        # Link to Driver
        instance.user = user
        instance.save(update_fields=['user'])
        
        # Assign DRIVER role
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
