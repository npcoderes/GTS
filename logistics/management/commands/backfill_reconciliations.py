from django.core.management.base import BaseCommand
from logistics.models import Trip, Reconciliation


class Command(BaseCommand):
    help = 'Backfill missing reconciliation records for completed trips'

    def handle(self, *args, **options):
        completed_trips = Trip.objects.filter(status='COMPLETED').prefetch_related('ms_fillings', 'dbs_decantings')
        
        created_count = 0
        skipped_count = 0
        
        for trip in completed_trips:
            if Reconciliation.objects.filter(trip=trip).exists():
                skipped_count += 1
                continue
            
            ms_filling = trip.ms_fillings.first()
            ms_filled_qty = float(ms_filling.filled_qty_kg) if ms_filling and ms_filling.filled_qty_kg else 0
            
            dbs_decanting = trip.dbs_decantings.first()
            dbs_delivered_qty = float(dbs_decanting.delivered_qty_kg) if dbs_decanting and dbs_decanting.delivered_qty_kg else 0
            
            if ms_filled_qty > 0:
                diff_qty = ms_filled_qty - dbs_delivered_qty
                variance_pct = (diff_qty / ms_filled_qty) * 100
                reconciliation_status = 'ALERT' if abs(variance_pct) > 0.5 else 'OK'
                
                Reconciliation.objects.create(
                    trip=trip,
                    ms_filled_qty_kg=ms_filled_qty,
                    dbs_delivered_qty_kg=dbs_delivered_qty,
                    diff_qty=diff_qty,
                    variance_pct=variance_pct,
                    status=reconciliation_status
                )
                created_count += 1
                self.stdout.write(f"Created reconciliation for trip {trip.id}")
        
        self.stdout.write(self.style.SUCCESS(f'\nBackfill complete: {created_count} created, {skipped_count} skipped'))
