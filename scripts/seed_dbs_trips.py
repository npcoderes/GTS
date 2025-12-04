import os
import django
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import Station, User
from logistics.models import Trip, Token, Vehicle, Driver

def seed_data():
    print("Seeding DBS Dashboard Data...")

    # 1. Create Stations
    ms, _ = Station.objects.get_or_create(
        name="Mother Station 1",
        defaults={'type': 'MS', 'code': 'MS-001'}
    )
    dbs, _ = Station.objects.get_or_create(
        name="DBS 1",
        defaults={'type': 'DBS', 'code': 'DBS-001', 'parent_station': ms}
    )
    print(f"Stations: {ms.name}, {dbs.name}")

    # 2. Create Vendor, Vehicle & Driver
    vendor, _ = User.objects.get_or_create(
        email="vendor_seed@sgl.com",
        defaults={'full_name': "Seed Vendor", 'is_active': True}
    )

    vehicle, _ = Vehicle.objects.get_or_create(
        registration_no="GJ-01-AB-1234",
        defaults={'capacity_kg': 1000, 'vendor': vendor}
    )
    
    driver, _ = Driver.objects.get_or_create(
        full_name="Ramesh Driver",
        defaults={
            'license_no': 'DL-12345', 
            'phone': '9876543210',
            'vendor': vendor,
            'license_expiry': timezone.now().date() + timedelta(days=365)
        }
    )
    print(f"Vehicle: {vehicle.registration_no}, Driver: {driver.full_name}")

    # 3. Create Trips
    # Trip 1: Dispatched (Pending in Frontend)
    token1 = Token.objects.create(vehicle=vehicle, ms=ms, sequence_no=101)
    Trip.objects.create(
        token=token1,
        vehicle=vehicle,
        driver=driver,
        ms=ms,
        dbs=dbs,
        status='DISPATCHED',
        started_at=timezone.now() - timedelta(hours=2)
    )
    print("Created Trip: DISPATCHED")

    # Trip 2: Arrived at DBS (Pending in Frontend)
    token2 = Token.objects.create(vehicle=vehicle, ms=ms, sequence_no=102)
    Trip.objects.create(
        token=token2,
        vehicle=vehicle,
        driver=driver,
        ms=ms,
        dbs=dbs,
        status='ARRIVED_AT_DBS',
        started_at=timezone.now() - timedelta(hours=1)
    )
    print("Created Trip: ARRIVED_AT_DBS")

    # Trip 3: Decanting (In Progress in Frontend)
    token3 = Token.objects.create(vehicle=vehicle, ms=ms, sequence_no=103)
    Trip.objects.create(
        token=token3,
        vehicle=vehicle,
        driver=driver,
        ms=ms,
        dbs=dbs,
        status='DECANTING_STARTED',
        started_at=timezone.now() - timedelta(minutes=30)
    )
    print("Created Trip: DECANTING_STARTED")

    # Trip 4: Completed
    token4 = Token.objects.create(vehicle=vehicle, ms=ms, sequence_no=104)
    Trip.objects.create(
        token=token4,
        vehicle=vehicle,
        driver=driver,
        ms=ms,
        dbs=dbs,
        status='COMPLETED',
        started_at=timezone.now() - timedelta(hours=5),
        completed_at=timezone.now() - timedelta(hours=1)
    )
    print("Created Trip: COMPLETED")
    
    # Trip 5: Completed (Another one)
    token5 = Token.objects.create(vehicle=vehicle, ms=ms, sequence_no=105)
    Trip.objects.create(
        token=token5,
        vehicle=vehicle,
        driver=driver,
        ms=ms,
        dbs=dbs,
        status='DECANTING_COMPLETED',
        started_at=timezone.now() - timedelta(hours=6),
        completed_at=timezone.now() - timedelta(hours=2)
    )
    print("Created Trip: DECANTING_COMPLETED")

    print("Seeding Complete!")

if __name__ == '__main__':
    seed_data()
