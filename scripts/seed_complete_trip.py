"""
Seed script for creating a complete trip lifecycle with all related data.
Following the DBS Manual Stock Request → MS Filling → Transit → DBS Decanting flow.

Based on the Business Process Blueprint.
"""
import os
import sys

# Add the backend directory to the path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from core.models import Station, User, Role, UserRole
from logistics.models import (
    StockRequest, Token, Trip, Vehicle, Driver, 
    MSFilling, DBSDecanting, Shift
)

def create_complete_trip():
    """Create a complete trip with all related records."""
    
    print("=" * 60)
    print("Creating Complete Trip Seed Data")
    print("=" * 60)
    
    # Get existing MS and DBS
    try:
        ms = Station.objects.filter(type='MS').first()
        dbs = Station.objects.filter(type='DBS').first()
        vehicle = Vehicle.objects.first()
        
        if not ms:
            print("[ERROR] No MS station found! Creating one...")
            ms = Station.objects.create(
                type='MS',
                code='MS001',
                name='SGL Mother Station',
                city='Ahmedabad',
                address='Industrial Area - Phase 1',
                lat=Decimal('23.0225'),
                lng=Decimal('72.5714'),
                geofence_radius_m=200
            )
        
        if not dbs:
            print("[ERROR] No DBS station found! Creating one...")
            dbs = Station.objects.create(
                type='DBS',
                code='DBS001',
                name='SGL DBS - Satellite',
                city='Ahmedabad',
                address='Satellite Road',
                lat=Decimal('23.0305'),
                lng=Decimal('72.5200'),
                geofence_radius_m=200,
                parent_station=ms
            )
        
        if not vehicle:
            print("[ERROR] No vehicle found! Creating one...")
            vehicle = Vehicle.objects.create(
                registration_no='GJ-01-CNG-1234',
                capacity_kg=Decimal('1500.00'),
                active=True
            )
        
        print(f"[OK] Using MS: {ms.name} (ID: {ms.id})")
        print(f"[OK] Using DBS: {dbs.name} (ID: {dbs.id})")
        print(f"[OK] Using Vehicle: {vehicle.registration_no} (ID: {vehicle.id})")
        
    except Exception as e:
        print(f"[ERROR] Error getting/creating base data: {e}")
        return
    
    # Get or create DBS operator user
    dbs_operator, _ = User.objects.get_or_create(
        email='dbs.operator@sgl.com',
        defaults={
            'full_name': 'Ramesh Kumar',
            'phone': '+91-9876500001',
            'is_active': True
        }
    )
    print(f"[OK] DBS Operator: {dbs_operator.full_name}")
    
    # Get or create vendor user  
    vendor_user, _ = User.objects.get_or_create(
        email='vendor@sgl.com',
        defaults={
            'full_name': 'SGL Transport Vendor',
            'phone': '+91-9876500003',
            'is_active': True
        }
    )
    
    # Get or create driver user
    driver_user, _ = User.objects.get_or_create(
        email='driver@sgl.com',
        defaults={
            'full_name': 'Vijay Singh',
            'phone': '+91-9876500002',
            'is_active': True
        }
    )
    
    # Get or create driver record
    driver, created = Driver.objects.get_or_create(
        full_name='Vijay Singh',
        defaults={
            'vendor': vendor_user,
            'license_no': 'GJ01-2024-123456',
            'license_expiry': timezone.now().date() + timedelta(days=365),
            'phone': '+91-9876500002',
            'status': 'ACTIVE',
            'trained': True,
            'user': driver_user
        }
    )
    if not created and driver.user is None:
        driver.user = driver_user
        driver.save()
    print(f"[OK] Driver: {driver.full_name}")
    
    # Create shift for driver
    now = timezone.now()
    shift, _ = Shift.objects.get_or_create(
        driver=driver,
        vehicle=vehicle,
        start_time=now.replace(hour=6, minute=0, second=0),
        defaults={
            'end_time': now.replace(hour=18, minute=0, second=0),
            'status': 'APPROVED'
        }
    )
    print(f"[OK] Shift: {shift.start_time.date()} ({shift.status})")
    
    # ============================================================
    # STEP 1: DBS Operator raises Manual Stock Request
    # ============================================================
    print("\n" + "-" * 40)
    print("STEP 1: Creating Manual Stock Request")
    print("-" * 40)
    
    today = timezone.now().date()
    
    stock_request = StockRequest.objects.create(
        source='DBS_OPERATOR',
        status='APPROVED',  # Already approved by EIC
        dbs=dbs,
        requested_by_user=dbs_operator,
        requested_qty_kg=Decimal('500.00'),
        current_stock_kg=Decimal('200.00'),
        rate_of_sale_kg_per_min=Decimal('0.5'),
        dot_minutes=400,  # 200kg / 0.5 kg/min = 400 minutes dry-out time
        rlt_minutes=120,  # 2 hours replenishment lead time
        priority_preview='H',  # High priority
        requested_by_date=today,
        requested_by_time=now.time(),
        approval_notes='Approved by EIC - Urgent refill needed'
    )
    print(f"[OK] Stock Request #{stock_request.id} created")
    print(f"   Source: {stock_request.source}")
    print(f"   Status: {stock_request.status}")
    print(f"   Requested Qty: {stock_request.requested_qty_kg} kg")
    print(f"   Priority: {stock_request.priority_preview}")
    
    # ============================================================
    # STEP 2: Token issued for the trip
    # ============================================================
    print("\n" + "-" * 40)
    print("STEP 2: Creating Token")
    print("-" * 40)
    
    token = Token.objects.create(
        vehicle=vehicle,
        ms=ms,
        sequence_no=1,
        issued_at=now - timedelta(hours=3)
    )
    print(f"[OK] Token #{token.id} issued (Seq: {token.sequence_no})")
    
    # ============================================================
    # STEP 3: Trip created and assigned to driver
    # ============================================================
    print("\n" + "-" * 40)
    print("STEP 3: Creating Trip")
    print("-" * 40)
    
    trip = Trip.objects.create(
        stock_request=stock_request,
        token=token,
        vehicle=vehicle,
        driver=driver,
        ms=ms,
        dbs=dbs,
        status='COMPLETED',  # Full lifecycle completed
        sto_number=f'STO-{ms.code}-{dbs.code}-{now.strftime("%Y%m%d%H%M%S")}',
        started_at=now - timedelta(hours=3),
        origin_confirmed_at=now - timedelta(hours=2, minutes=45),
        ms_departure_at=now - timedelta(hours=2),
        dbs_arrival_at=now - timedelta(hours=1),
        dbs_departure_at=now - timedelta(minutes=30),
        completed_at=now - timedelta(minutes=15),
        rtkm_km=Decimal('45.5'),
        route_deviation=False
    )
    print(f"[OK] Trip #{trip.id} created")
    print(f"   Route: {ms.name} → {dbs.name}")
    print(f"   STO: {trip.sto_number}")
    print(f"   Status: {trip.status}")
    
    # ============================================================
    # STEP 4: MS Filling - Pre/Post readings at Mother Station
    # ============================================================
    print("\n" + "-" * 40)
    print("STEP 4: MS Filling Record")
    print("-" * 40)
    
    ms_filling = MSFilling.objects.create(
        trip=trip,
        start_time=now - timedelta(hours=2, minutes=45),
        end_time=now - timedelta(hours=2, minutes=15),
        prefill_pressure_bar=Decimal('50.00'),
        postfill_pressure_bar=Decimal('250.00'),
        filled_qty_kg=Decimal('500.00'),
        confirmed_by_driver=driver_user
    )
    print(f"[OK] MS Filling #{ms_filling.id} recorded")
    print(f"   Pre-fill Pressure: {ms_filling.prefill_pressure_bar} bar")
    print(f"   Post-fill Pressure: {ms_filling.postfill_pressure_bar} bar")
    print(f"   Filled Qty: {ms_filling.filled_qty_kg} kg")
    
    # ============================================================
    # STEP 5: DBS Decanting - Delivery at DBS
    # ============================================================
    print("\n" + "-" * 40)
    print("STEP 5: DBS Decanting Record")
    print("-" * 40)
    
    dbs_decanting = DBSDecanting.objects.create(
        trip=trip,
        start_time=now - timedelta(hours=1),
        end_time=now - timedelta(minutes=30),
        pre_dec_reading=Decimal('250.00'),
        post_dec_reading=Decimal('15.00'),
        delivered_qty_kg=Decimal('498.50'),  # Slight variance (normal)
        confirmed_by_dbs_operator=dbs_operator,
        confirmed_by_driver=driver_user
    )
    print(f"[OK] DBS Decanting #{dbs_decanting.id} recorded")
    print(f"   Pre-dec Reading: {dbs_decanting.pre_dec_reading}")
    print(f"   Post-dec Reading: {dbs_decanting.post_dec_reading}")
    print(f"   Delivered Qty: {dbs_decanting.delivered_qty_kg} kg")
    
    # Calculate variance
    variance = ms_filling.filled_qty_kg - dbs_decanting.delivered_qty_kg
    variance_pct = (variance / ms_filling.filled_qty_kg) * 100
    print(f"   Variance: {variance} kg ({variance_pct:.2f}%)")
    
    # ============================================================
    # Summary
    # ============================================================
    print("\n" + "=" * 60)
    print("COMPLETE TRIP SEED DATA CREATED SUCCESSFULLY!")
    print("=" * 60)
    
    print(f"""
Trip Summary:
-------------
Trip ID: {trip.id}
STO Number: {trip.sto_number}
Route: {ms.name} → {dbs.name}
Vehicle: {vehicle.registration_no}
Driver: {driver.full_name}

Timeline:
- Stock Request Created: {stock_request.created_at}
- Trip Started: {trip.started_at}
- MS Filling Completed: {ms_filling.end_time}
- DBS Arrival: {trip.dbs_arrival_at}
- Trip Completed: {trip.completed_at}

Quantities:
- Requested: {stock_request.requested_qty_kg} kg
- Filled at MS: {ms_filling.filled_qty_kg} kg
- Delivered at DBS: {dbs_decanting.delivered_qty_kg} kg
- Variance: {variance} kg ({variance_pct:.2f}%)

Status: [OK] COMPLETED
""")
    
    return trip


def create_cancelled_trip():
    """Create a cancelled trip for testing."""
    from logistics.models import Trip, Vehicle, Driver, Token
    from core.models import Station
    from django.utils import timezone
    
    print("\n" + "=" * 60)
    print("Creating CANCELLED Trip")
    print("=" * 60)
    
    ms = Station.objects.filter(type='MS').first()
    dbs = Station.objects.filter(type='DBS').first()
    vehicle = Vehicle.objects.first()
    driver = Driver.objects.first()
    
    if ms and dbs and vehicle:
        trip = Trip.objects.create(
            ms=ms,
            dbs=dbs,
            vehicle=vehicle,
            driver=driver,
            status='CANCELLED',
            started_at=timezone.now(),
            ended_at=timezone.now()
        )
        print(f'[OK] Created CANCELLED trip: ID={trip.id}')
        print(f'   Route: {ms.name} → {dbs.name}')
        return trip
    else:
        print('[ERROR] Missing required data: MS, DBS, or Vehicle')
        return None


if __name__ == '__main__':
    create_complete_trip()
    create_cancelled_trip()
