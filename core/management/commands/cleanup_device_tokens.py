"""
Management command to clean up invalid FCM device tokens.

This command helps identify and deactivate device tokens that may be invalid
by checking their last usage and providing options to clean them up.

Usage:
    python manage.py cleanup_device_tokens --dry-run  # Preview what will be cleaned
    python manage.py cleanup_device_tokens             # Actually clean up tokens
    python manage.py cleanup_device_tokens --days 90   # Clean tokens older than 90 days
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.notification_models import DeviceToken
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clean up invalid or old FCM device tokens'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be cleaned without making changes',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=180,
            help='Deactivate tokens not updated in this many days (default: 180)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force deactivation without confirmation',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        days_threshold = options['days']
        force = options['force']
        
        cutoff_date = timezone.now() - timedelta(days=days_threshold)
        
        self.stdout.write(self.style.NOTICE(
            f"\n{'=' * 60}\n"
            f"FCM Device Token Cleanup\n"
            f"{'=' * 60}\n"
        ))
        
        # Find old tokens
        old_tokens = DeviceToken.objects.filter(
            is_active=True,
            updated_at__lt=cutoff_date
        ).select_related('user')
        
        # Find duplicate tokens (same user, same platform)
        from django.db.models import Count
        duplicate_users = DeviceToken.objects.filter(
            is_active=True
        ).values('user', 'platform').annotate(
            count=Count('id')
        ).filter(count__gt=3)  # More than 3 devices of same type is suspicious
        
        self.stdout.write(f"\n📊 Statistics:")
        self.stdout.write(f"  • Total active tokens: {DeviceToken.objects.filter(is_active=True).count()}")
        self.stdout.write(f"  • Tokens older than {days_threshold} days: {old_tokens.count()}")
        self.stdout.write(f"  • Users with 3+ devices of same type: {len(duplicate_users)}")
        
        if old_tokens.exists():
            self.stdout.write(f"\n🔍 Old tokens to deactivate:")
            for token in old_tokens[:10]:  # Show first 10
                days_old = (timezone.now() - token.updated_at).days
                self.stdout.write(
                    f"  • User: {token.user.email} | "
                    f"Platform: {token.platform} | "
                    f"Last updated: {days_old} days ago"
                )
            
            if old_tokens.count() > 10:
                self.stdout.write(f"  ... and {old_tokens.count() - 10} more")
        
        if duplicate_users:
            self.stdout.write(f"\n⚠️  Users with many devices:")
            for dup in duplicate_users[:5]:
                user_id = dup['user']
                platform = dup['platform']
                count = dup['count']
                try:
                    from core.models import User
                    user = User.objects.get(id=user_id)
                    self.stdout.write(f"  • {user.email}: {count} {platform} devices")
                except:
                    pass
        
        # Perform cleanup
        if not dry_run:
            if not force and old_tokens.exists():
                self.stdout.write(f"\n⚠️  About to deactivate {old_tokens.count()} tokens.")
                confirm = input("Continue? (yes/no): ")
                if confirm.lower() != 'yes':
                    self.stdout.write(self.style.WARNING("Cancelled."))
                    return
            
            if old_tokens.exists():
                count = old_tokens.update(is_active=False)
                self.stdout.write(self.style.SUCCESS(
                    f"\n✅ Deactivated {count} old tokens"
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f"\n✅ No old tokens to clean up"
                ))
        else:
            self.stdout.write(self.style.WARNING(
                f"\n🔍 DRY RUN - No changes made. "
                f"Run without --dry-run to actually clean up tokens."
            ))
        
        self.stdout.write(f"\n{'=' * 60}\n")
