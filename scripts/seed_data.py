import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import Station, User, Role, UserRole
from logistics.models import Partner

import traceback

def seed():
    ms = None
    partner = None
    
    try:
        # 1. Ensure MS Station
        ms, created = Station.objects.get_or_create(
            name="SGL Mother Station 1",
            defaults={
                'code': 'MS001',
                'type': 'MS',
                'lat': 12.9716,
                'lng': 77.5946,
                'address': 'Bangalore',
                'city': 'Bangalore'
            }
        )
        if created:
            print(f"Created Station: {ms.name}")
        else:
            print(f"Station exists: {ms.name}")
    except Exception:
        traceback.print_exc()

    try:
        # 2. Ensure Partner (Vendor) & Role
        vendor_role, _ = Role.objects.get_or_create(code='SGL_TRANSPORT_VENDOR', defaults={'name': 'Transport Vendor'})

        vendor_user, created = User.objects.get_or_create(
            email='vendor@sgl.com',
            defaults={
                'full_name': 'Vendor Admin',
                'is_active': True
            }
        )
        if created:
            vendor_user.set_password('1234')
            vendor_user.save()
            print(f"Created User: {vendor_user.email}")
        else:
            print(f"User exists: {vendor_user.email}")

        # Assign Vendor Role
        UserRole.objects.get_or_create(user=vendor_user, role=vendor_role, defaults={'station': None})
        print(f"Assigned Vendor role to {vendor_user.email}")

        partner, created = Partner.objects.get_or_create(
            name="SGL Transport Services",
            defaults={
                'type': 'SGL_TRANSPORT_VENDOR',
                'user': vendor_user,
                'contact_name': 'Ramesh',
                'email': 'ramesh@sgltransport.com',
                'phone': '9876543210'
            }
        )
        if created:
            print(f"Created Partner: {partner.name}")
        else:
            print(f"Partner exists: {partner.name}")
    except Exception:
        traceback.print_exc()

    try:
        # 3. Ensure EIC User and Role
        if not ms:
            ms = Station.objects.get(code='MS001')
            
        eic_role, _ = Role.objects.get_or_create(code='EIC', defaults={'name': 'Engineer In Charge'})
        
        eic_user, created = User.objects.get_or_create(
            email='eic@sgl.com',
            defaults={
                'full_name': 'EIC Officer',
                'is_active': True
            }
        )
        if created:
            eic_user.set_password('1234')
            eic_user.save()
            print(f"Created User: {eic_user.email}")
        
        # Assign EIC role
        UserRole.objects.get_or_create(user=eic_user, role=eic_role, station=ms)
        print(f"Assigned EIC role to {eic_user.email}")

    except Exception:
        traceback.print_exc()

if __name__ == '__main__':
    seed()
