"""
Seed All Roles with Default Permissions

This command creates RolePermission entries for all roles based on
DEFAULT_ROLE_PERMISSIONS defined in permission_models.py

Usage:
    python manage.py seed_all_role_permissions
    python manage.py seed_all_role_permissions --role EIC
"""

from django.core.management.base import BaseCommand
from core.models import Role
from core.permission_models import Permission, RolePermission, DEFAULT_ROLE_PERMISSIONS


class Command(BaseCommand):
    help = 'Seed all roles with their default permissions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--role',
            type=str,
            help='Seed only a specific role code (e.g., EIC, DRIVER)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating',
        )
        parser.add_argument(
            '--include-super-admin',
            action='store_true',
            help='Include SUPER_ADMIN (grants all permissions)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        role_filter = options['role']
        include_super_admin = options['include_super_admin']
        
        # Get all permissions for Super Admin seeding
        all_permissions = list(Permission.objects.all())
        
        if not all_permissions:
            self.stderr.write(self.style.ERROR('No permissions found. Run seed_permissions first.'))
            return
        
        self.stdout.write(f"Found {len(all_permissions)} permissions in database")
        
        total_created = 0
        total_updated = 0
        
        # Determine which roles to seed
        if role_filter:
            roles_to_seed = {role_filter: DEFAULT_ROLE_PERMISSIONS.get(role_filter, [])}
        else:
            roles_to_seed = DEFAULT_ROLE_PERMISSIONS.copy()
        
        for role_code, perm_codes in roles_to_seed.items():
            # Skip SUPER_ADMIN unless explicitly included
            if role_code == 'SUPER_ADMIN' and not include_super_admin:
                continue
                
            try:
                role = Role.objects.get(code=role_code)
            except Role.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"Role {role_code} not found, skipping"))
                continue
            
            self.stdout.write(f"\n--- Seeding role: {role.name} ({role_code}) ---")
            
            # For Super Admin, grant ALL permissions
            if role_code == 'SUPER_ADMIN':
                perms_to_grant = all_permissions
            else:
                # Get permissions by code
                perms_to_grant = Permission.objects.filter(code__in=perm_codes)
            
            created = 0
            updated = 0
            
            for perm in perms_to_grant:
                if dry_run:
                    self.stdout.write(f"  [DRY-RUN] Would grant: {perm.code}")
                else:
                    obj, was_created = RolePermission.objects.update_or_create(
                        role=role,
                        permission=perm,
                        defaults={'granted': True}
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1
            
            if not dry_run:
                self.stdout.write(f"  Created: {created}, Updated: {updated}")
            
            total_created += created
            total_updated += updated
        
        self.stdout.write('')
        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run complete.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Complete! Total Created: {total_created}, Updated: {total_updated}'))
