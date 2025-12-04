"""
Seed cancelled trip for testing
Run: python manage.py runscript seed_cancelled_trip
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from logistics.models import Trip, Vehicle, Driver
from core.models import Station
from django.utils import timezone

def run():
    # Get existing data
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
        print(f'Created CANCELLED trip: ID={trip.id}, MS={ms.name}, DBS={dbs.name}')
    else:
        print('Missing required data: MS, DBS, or Vehicle')

if __name__ == '__main__':
    run()
