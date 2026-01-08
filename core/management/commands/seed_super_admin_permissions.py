"""
Seed Super Admin Role with All Permissions

This command creates RolePermission entries for the SUPER_ADMIN role
with all available permissions granted. This allows the Super Admin
to be managed through the UI like any other role.

Usage:
    python manage.py seed_super_admin_permissions
"""

from django.core.management.base import BaseCommand
from core.models import Role
from core.permission_models import Permission, RolePermission


class Command(BaseCommand):
    help = 'Seed SUPER_ADMIN role with all permissions granted'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Get or create Super Admin role
        try:
            super_admin = Role.objects.get(code='SUPER_ADMIN')
        except Role.DoesNotExist:
            self.stderr.write(self.style.ERROR('SUPER_ADMIN role not found. Run seed_roles first.'))
            return

        # Get all permissions
        all_permissions = Permission.objects.all()
        
        if not all_permissions.exists():
            self.stderr.write(self.style.ERROR('No permissions found. Run seed_permissions first.'))
            return
        
        self.stdout.write(f"Found {all_permissions.count()} permissions")
        self.stdout.write(f"Seeding permissions for role: {super_admin.name}")
        
        created = 0
        updated = 0
        
        for perm in all_permissions:
            if dry_run:
                self.stdout.write(f"  [DRY-RUN] Would grant: {perm.code}")
            else:
                obj, was_created = RolePermission.objects.update_or_create(
                    role=super_admin,
                    permission=perm,
                    defaults={'granted': True}
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f'\nDry run complete. Would create/update {all_permissions.count()} permissions.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'\nComplete! Created: {created}, Updated: {updated}'))
