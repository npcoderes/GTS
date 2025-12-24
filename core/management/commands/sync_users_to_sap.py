"""
Django management command to sync users to SAP.
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from core.models import User
from core.sap_integration import sap_service
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync users to SAP system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Sync all users to SAP',
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='Sync a specific user by ID',
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Sync a specific user by email',
        )
        parser.add_argument(
            '--active-only',
            action='store_true',
            help='Sync only active users',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Dry run - show what would be synced without actually syncing',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sync even for recently synced users',
        )

    def handle(self, *args, **options):
        # Build queryset based on arguments
        queryset = User.objects.all()

        if options['user_id']:
            queryset = queryset.filter(id=options['user_id'])
            self.stdout.write(f"Syncing user with ID: {options['user_id']}")
        elif options['email']:
            queryset = queryset.filter(email=options['email'])
            self.stdout.write(f"Syncing user with email: {options['email']}")
        elif options['all']:
            self.stdout.write("Syncing all users")
        else:
            self.stdout.write(self.style.ERROR('Please specify --all, --user-id, or --email'))
            return

        if options['active_only']:
            queryset = queryset.filter(is_active=True)
            self.stdout.write("Filtering for active users only")

        users = queryset.select_related().order_by('id')
        total_count = users.count()

        if total_count == 0:
            self.stdout.write(self.style.WARNING('No users found matching criteria'))
            return

        self.stdout.write(f"\nFound {total_count} user(s) to sync")
        self.stdout.write("-" * 60)

        if options['dry_run']:
            self.stdout.write(self.style.WARNING('\n🧪 DRY RUN MODE - No actual syncing will occur\n'))

        success_count = 0
        failed_count = 0
        errors = []

        for index, user in enumerate(users, 1):
            self.stdout.write(f"\n[{index}/{total_count}] Processing user: {user.email} (ID: {user.id})")
            
            # Get user role info
            primary_role = user.user_roles.filter(active=True).order_by('-created_at').first()
            if primary_role:
                role_info = f"{primary_role.role.code}"
                if primary_role.station:
                    role_info += f" @ {primary_role.station.code}"
                self.stdout.write(f"  Role: {role_info}")
            else:
                self.stdout.write(self.style.WARNING("  No active role assigned"))

            if options['dry_run']:
                self.stdout.write(self.style.SUCCESS("  ✓ Would sync to SAP (dry run)"))
                success_count += 1
                continue

            try:
                # Check if user was recently synced (within last hour)
                from django.utils import timezone
                from datetime import timedelta
                
                recently_synced = False
                if user.sap_last_synced_at and not options['force']:
                    time_diff = timezone.now() - user.sap_last_synced_at
                    recently_synced = time_diff < timedelta(hours=1)
                
                if recently_synced:
                    self.stdout.write(self.style.WARNING(f"  ⊘ Skipped (synced {time_diff} ago)"))
                    success_count += 1
                    continue
                
                # Sync user to SAP
                result = sap_service.sync_user_to_sap(user, operation='CREATE')
                
                if result['success']:
                    success_count += 1
                    # Update sync timestamp
                    user.sap_last_synced_at = timezone.now()
                    user.save(update_fields=['sap_last_synced_at'])
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Synced successfully"))
                    if result.get('response'):
                        logger.debug(f"SAP response for {user.email}: {result['response']}")
                else:
                    failed_count += 1
                    error_msg = result.get('error', 'Unknown error')
                    self.stdout.write(self.style.ERROR(f"  ✗ Failed: {error_msg}"))
                    errors.append({
                        'user_id': user.id,
                        'email': user.email,
                        'error': error_msg
                    })
                    
            except Exception as e:
                failed_count += 1
                error_msg = str(e)
                self.stdout.write(self.style.ERROR(f"  ✗ Exception: {error_msg}"))
                errors.append({
                    'user_id': user.id,
                    'email': user.email,
                    'error': error_msg
                })
                logger.error(f"Error syncing user {user.email} to SAP", exc_info=True)

        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(f"\n📊 SUMMARY"))
        self.stdout.write(f"Total users processed: {total_count}")
        self.stdout.write(self.style.SUCCESS(f"✓ Successful: {success_count}"))
        
        if failed_count > 0:
            self.stdout.write(self.style.ERROR(f"✗ Failed: {failed_count}"))
            
            if errors:
                self.stdout.write("\n❌ Errors:")
                for error in errors:
                    self.stdout.write(f"  - User {error['email']} (ID {error['user_id']}): {error['error']}")
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING("\n⚠️  This was a dry run. No changes were made to SAP."))
        
        self.stdout.write("\n" + "=" * 60)
