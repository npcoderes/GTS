
import os
import django
import sys
from datetime import timedelta

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.utils import timezone
from core.models import User, Station, Role, UserRole, Vehicle, Driver
from logistics.models import Trip, Token, StockRequest, VehicleToken, MSFilling
from rest_framework.test import APIRequestFactory, force_authenticate
from logistics.ms_views import MSConfirmArrivalView

def run_test():
    print("🚀 Starting MS Bay Management Test...")
    
    # 1. Setup Data
    print("\n1. Setting up test data...")
    
    # Create Test MS Station with 2 bays
    ms = Station.objects.create(
        type='MS', 
        code='TEST_MS_BAY', 
        name='Test MS Bay Station',
        no_of_bays=2
    )
    print(f"   - Created MS Station: {ms.name} with {ms.no_of_bays} bays")

    # Create Test User (MS Operator)
    operator = User.objects.create_user(
        email='test_ms_op@example.com', 
        password='password123',
        full_name='Test Operator',
        phone='9999999999'  # Added unique phone
    )
    role_ms_op = Role.objects.get(code='MS_OPERATOR')
    UserRole.objects.create(user=operator, role=role_ms_op, station=ms)
    print("   - Created Test Operator")

    # Create Test Vehicles & Drivers
    vehicles = []
    drivers = []
    trips = []
    
    # Helper to create trip
    def create_trip(idx):
        v = Vehicle.objects.create(registration_no=f"GJ01TEST{idx}", vendor=operator) # Simple vendor assignment
        d = Driver.objects.create(
            full_name=f"Driver {idx}", 
            license_no=f"LIC{idx}", 
            license_expiry=timezone.now().date(),
            vendor=operator
        )
        t = Token.objects.create(vehicle=v, ms=ms, token_no=f"TOKEN{idx}")
        
        # Create Trip
        trip = Trip.objects.create(
            vehicle=v, driver=d, ms=ms, token=t, 
            status='PENDING',
            dbs=ms # Self-loop for simple test
        )
        
        vehicles.append(v)
        drivers.append(d)
        trips.append(trip)
        return trip

    trip1 = create_trip(1)
    trip2 = create_trip(2)
    trip3 = create_trip(3)
    print("   - Created 3 Trips (Pending)")

    factory = APIRequestFactory()
    view = MSConfirmArrivalView.as_view()

    try:
        # 2. Test: Confirm Trip 1 (Occupies Bay 1)
        print("\n2. Confirming Trip 1 (Bay 1)...")
        # Create Pre-filling state manually to simulate bay occupancy
        # Note: In real flow, "Arrival Confirm" status -> "Start Filling" (occupies bay)
        # But our logic checks: MSFilling exists AND not confirmed
        
        # Wait - the validation is in ARRIVAL_CONFIRM.
        # But logic says: "Occupied = Trips with MSFilling created... but NOT confirmed"
        # Wait, if I just confirm arrival, does it occupy a bay? 
        # Code check: 
        # occupied_count = MSFilling.objects.filter(...)
        # So "Arrival Confirm" does NOT occupy a bay yet. It just lets them IN.
        # It's "Start Filling" that creates MSFilling record.
        
        # So to test the BLOCK in Arrival Confirm, we need to manually create MSFilling records 
        # for other trips to simulate them being "at the filling stage".
        
        # Scenario: 
        # Trip A & B are ALREADY filling (have MSFilling records)
        # Trip C arrives -> Try to confirm arrival -> Should be BLOCKED
        
        print("   - Simulating Trip 1 starting filling...")
        MSFilling.objects.create(trip=trip1, prefill_mfm=100) # Filling started
        
        print("   - Simulating Trip 2 starting filling...")
        MSFilling.objects.create(trip=trip2, prefill_mfm=100) # Filling started
        
        print(f"   - Current Occupied Bays: 2 (Trip 1, Trip 2)")

        # 3. Test: Try to Confirm Trip 3 Arrival (Should Fail)
        print("\n3. Attempting to confirm Trip 3 Arrival (Should FAIL)...")
        request = factory.post('/api/ms/arrival/confirm', {'tripToken': trip3.token.token_no}, format='json')
        force_authenticate(request, user=operator)
        response = view(request)
        
        if response.status_code == 400 and 'occupied' in str(response.data):
            print("   ✅ SUCCESS: Trip 3 blocked as expected.")
            print(f"   - Response: {response.data['error']}")
        else:
            print(f"   ❌ FAILED: Trip 3 was not blocked. Status: {response.status_code}")
            print(response.data)

        # 4. Test: Free up a bay (Confirm Trip 1 Filling)
        print("\n4. Confirming Trip 1 Filling (Freeing Bay 1)...")
        filling1 = MSFilling.objects.get(trip=trip1)
        filling1.confirmed_by_ms_operator = operator
        filling1.save()
        print("   - Trip 1 Filling confirmed. Bay 1 freed.")

        # 5. Test: Try to Confirm Trip 3 Arrival again (Should Success)
        print("\n5. Attempting to confirm Trip 3 Arrival again (Should SUCCEED)...")
        request = factory.post('/api/ms/arrival/confirm', {'tripToken': trip3.token.token_no}, format='json')
        force_authenticate(request, user=operator)
        response = view(request)
        
        if response.status_code == 200:
            print("   ✅ SUCCESS: Trip 3 confirmed successfully.")
            print(f"   - Trip Status: {response.data.get('trip', {}).get('status')}")
        else:
            print(f"   ❌ FAILED: Trip 3 fail to confirm. Status: {response.status_code}")
            print(response.data)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        with open('test_error.log', 'w') as f:
            f.write(str(e) + "\n")
            traceback.print_exc(file=f)
        traceback.print_exc()

    finally:
        # 6. Cleanup
        print("\n6. Cleaning up test data...")
        Trip.objects.filter(ms=ms).delete()
        Token.objects.filter(ms=ms).delete()
        Vehicle.objects.filter(registration_no__startswith='GJ01TEST').delete()
        Driver.objects.filter(full_name__startswith='Driver ').delete()
        UserRole.objects.filter(user=operator).delete()
        operator.delete()
        ms.delete()
        print("   - Cleanup complete.")

if __name__ == '__main__':
    run_test()
