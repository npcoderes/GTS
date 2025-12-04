"""
Script to provision User accounts for existing Drivers.
Drivers need User accounts with passwords to login from the mobile app.

When SGL Transport Vendor creates a Driver, this script ensures a corresponding
User account is created with the DRIVER role.

Usage:
    python manage.py shell < scripts/provision_driver_users.py
Or:
    python manage.py runscript provision_driver_users
"""

import os
import sys
import django

# Setup Django if running standalone
if 'django' not in sys.modules:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
    django.setup()

from django.db import transaction
from core.models import User, Role, UserRole
from logistics.models import Driver


def generate_driver_email(driver):
    """Generate email for driver based on phone number or name."""
    # Use phone number as email prefix if available
    if driver.phone:
        phone_clean = ''.join(filter(str.isdigit, driver.phone))
        return f"driver_{phone_clean}@gts.local"
    # Fallback to name-based
    name_clean = driver.full_name.lower().replace(' ', '_')
    return f"driver_{name_clean}_{driver.id}@gts.local"


def generate_default_password(driver):
    """Generate default password for driver.
    Format: driver_<last4digits_of_phone>
    Should be changed by driver on first login.
    """
    if driver.phone:
        phone_clean = ''.join(filter(str.isdigit, driver.phone))[-4:]
        return f"driver_{phone_clean}"
    return f"driver_{driver.id}"


@transaction.atomic
def provision_driver_user(driver, force_recreate=False):
    """
    Create User account for a Driver if not exists.
    Links the User to Driver via driver.user field.
    Assigns DRIVER role to the User.
    """
    # Skip if driver already has a user account
    if driver.user and not force_recreate:
        print(f"Driver {driver.full_name} already has user account: {driver.user.email}")
        return driver.user
    
    # Generate credentials
    email = generate_driver_email(driver)
    password = generate_default_password(driver)
    
    # Check if email already exists
    existing_user = User.objects.filter(email=email).first()
    if existing_user:
        # Link existing user to driver
        driver.user = existing_user
        driver.save()
        print(f"Linked existing user {email} to driver {driver.full_name}")
        return existing_user
    
    # Create new User
    user = User.objects.create_user(
        email=email,
        password=password,
        full_name=driver.full_name,
        phone=driver.phone or ''
    )
    
    # Link to Driver
    driver.user = user
    driver.save()
    
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
    
    print(f"Created user for driver: {driver.full_name}")
    print(f"  Email: {email}")
    print(f"  Default Password: {password}")
    print(f"  (Driver should change password on first login)")
    
    return user


def provision_all_drivers():
    """Provision User accounts for all drivers without existing accounts."""
    drivers_without_users = Driver.objects.filter(user__isnull=True)
    
    print(f"\nFound {drivers_without_users.count()} drivers without user accounts\n")
    
    for driver in drivers_without_users:
        try:
            provision_driver_user(driver)
            print("---")
        except Exception as e:
            print(f"Error provisioning user for driver {driver.full_name}: {e}")
            print("---")
    
    print("\nDriver user provisioning complete!")
    print(f"Total drivers: {Driver.objects.count()}")
    print(f"Drivers with users: {Driver.objects.filter(user__isnull=False).count()}")


if __name__ == '__main__':
    provision_all_drivers()
