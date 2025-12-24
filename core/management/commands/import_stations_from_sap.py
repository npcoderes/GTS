"""
Django management command to import stations from SAP into Django database.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Station
from core.sap_integration import sap_service
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Import stations from SAP into Django database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--station-type',
            type=str,
            choices=['MS', 'DB'],
            help='Import only specific station type (MS or DB)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Dry run - show what would be imported without actually importing',
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing stations if they already exist',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force import even for recently synced stations',
        )

    def handle(self, *args, **options):
        station_type = options.get('station_type')
        dry_run = options['dry_run']
        update_existing = options['update_existing']
        force_import = options['force']

        if dry_run:
            self.stdout.write(self.style.WARNING('\n🧪 DRY RUN MODE - No actual changes will be made\n'))

        self.stdout.write(f"Fetching stations from SAP...")
        if station_type:
            self.stdout.write(f"Filtering by type: {station_type}")

        # Fetch stations from SAP
        try:
            sap_result = sap_service.get_stations_from_sap(station_type=station_type)
            
            if not sap_result['success']:
                self.stdout.write(self.style.ERROR(f"Failed to fetch from SAP: {sap_result.get('error')}"))
                return

            stations_data = sap_result.get('stations', [])
            
            if not stations_data:
                self.stdout.write(self.style.WARNING('No stations found in SAP'))
                return

            self.stdout.write(f"\nFound {len(stations_data)} station(s) from SAP")
            self.stdout.write("-" * 60)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error fetching from SAP: {str(e)}"))
            return

        # Process each station
        created_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []

        for index, sap_station in enumerate(stations_data, 1):
            sap_id = sap_station.get('id')
            name = sap_station.get('name')
            station_type_value = sap_station.get('type')
            
            self.stdout.write(f"\n[{index}/{len(stations_data)}] Processing: {name} (SAP ID: {sap_id})")
            self.stdout.write(f"  Type: {station_type_value}")
            self.stdout.write(f"  City: {sap_station.get('city', 'N/A')}")
            self.stdout.write(f"  Phone: {sap_station.get('phone', 'N/A')}")
            
            if dry_run:
                self.stdout.write(self.style.SUCCESS("  ✓ Would import (dry run)"))
                created_count += 1
                continue

            # Check if station already exists
            existing_station = None
            try:
                existing_station = Station.objects.get(sap_station_id=sap_id)
            except Station.DoesNotExist:
                pass

            # Prepare station data
            # Map SAP type to Django type (DB -> DBS)
            django_type = 'DBS' if station_type_value == 'DB' else 'MS'
            
            # Get parent MS if it's a DBS
            parent_station = None
            if station_type_value == 'DB' and sap_station.get('parent_ms_id'):
                try:
                    parent_station = Station.objects.get(sap_station_id=sap_station['parent_ms_id'])
                except Station.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"  ⚠ Parent MS {sap_station['parent_ms_id']} not found"))

            station_data = {
                'sap_station_id': sap_id,
                'code': sap_id,  # Use SAP ID as code
                'name': name,
                'type': django_type,
                'city': sap_station.get('city', ''),
                'phone': sap_station.get('phone', ''),
                'parent_station': parent_station,
                'sap_last_synced_at': timezone.now(),
            }

            try:
                if existing_station:
                    # Check if recently synced (within last hour)
                    from datetime import timedelta
                    
                    recently_synced = False
                    if existing_station.sap_last_synced_at:
                        time_diff = timezone.now() - existing_station.sap_last_synced_at
                        recently_synced = time_diff < timedelta(hours=1)
                    
                    if recently_synced and not update_existing and not force_import:
                        skipped_count += 1
                        self.stdout.write(self.style.WARNING(f"  ⊘ Skipped (synced {time_diff} ago)"))
                    elif update_existing:
                        # Update existing station
                        for key, value in station_data.items():
                            setattr(existing_station, key, value)
                        existing_station.sap_last_synced_at = timezone.now()
                        existing_station.save()
                        updated_count += 1
                        self.stdout.write(self.style.SUCCESS(f"  ✓ Updated existing station"))
                    else:
                        skipped_count += 1
                        self.stdout.write(self.style.WARNING(f"  ⊘ Skipped (already exists, use --update-existing to update)"))
                else:
                    # Create new station
                    station_data['sap_last_synced_at'] = timezone.now()
                    new_station = Station.objects.create(**station_data)
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Created new station (ID: {new_station.id})"))

            except Exception as e:
                errors.append({
                    'sap_id': sap_id,
                    'name': name,
                    'error': str(e)
                })
                self.stdout.write(self.style.ERROR(f"  ✗ Error: {str(e)}"))

        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(f"\n📊 SUMMARY"))
        self.stdout.write(f"Total SAP stations processed: {len(stations_data)}")
        
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"✓ Would create: {created_count}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"✓ Created: {created_count}"))
            self.stdout.write(self.style.SUCCESS(f"✓ Updated: {updated_count}"))
            if skipped_count > 0:
                self.stdout.write(self.style.WARNING(f"⊘ Skipped: {skipped_count}"))
        
        if errors:
            self.stdout.write(self.style.ERROR(f"\n✗ Errors: {len(errors)}"))
            for error in errors:
                self.stdout.write(f"  - {error['name']} (SAP ID {error['sap_id']}): {error['error']}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("\n⚠️  This was a dry run. No changes were made."))
        
        self.stdout.write("\n" + "=" * 60)
        
        # Recommendations
        if created_count > 0 or updated_count > 0:
            self.stdout.write("\n💡 Next steps:")
            if station_type == 'MS' or not station_type:
                self.stdout.write("  1. Import DBS stations: python manage.py import_stations_from_sap --station-type DB")
            self.stdout.write("  2. Verify stations in admin or database")
            self.stdout.write(f"  3. Stations are now available in your Django app!")
