"""
Django management command to seed initial GTS permissions and role-permission mappings.
Usage: python manage.py seed_permissions
"""
from django.core.management.base import BaseCommand
from core.permission_models import Permission, RolePermission, DEFAULT_PERMISSIONS, DEFAULT_ROLE_PERMISSIONS
from core.models import Role


class Command(BaseCommand):
    help = 'Seeds initial permissions and role-permission mappings for the Gas Transportation System'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('Seeding GTS Permissions...'))
        
        # Step 1: Seed Permissions
        perm_created_count = 0
        perm_updated_count = 0
        
        for perm_data in DEFAULT_PERMISSIONS:
            permission, created = Permission.objects.update_or_create(
                code=perm_data['code'],
                defaults={
                    'name': perm_data['name'],
                    'description': perm_data['description'],
                    'category': perm_data['category']
                }
            )
            
            if created:
                perm_created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Created permission: {permission.name} ({permission.code})')
                )
            else:
                perm_updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'  ↻ Updated permission: {permission.name} ({permission.code})')
                )
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Successfully seeded {perm_created_count} new permissions and updated {perm_updated_count} existing permissions.'
        ))
        
        # Step 2: Seed Role-Permission Mappings
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('Seeding Role-Permission Mappings...'))
        
        role_perm_created_count = 0
        role_perm_updated_count = 0
        
        for role_code, perm_codes in DEFAULT_ROLE_PERMISSIONS.items():
            # Get the role
            try:
                role = Role.objects.get(code=role_code)
            except Role.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Role not found: {role_code} (skipping)')
                )
                continue
            
            # For each permission code, create or update the RolePermission
            for perm_code in perm_codes:
                try:
                    permission = Permission.objects.get(code=perm_code)
                except Permission.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ Permission not found: {perm_code} (skipping)')
                    )
                    continue
                
                role_perm, created = RolePermission.objects.update_or_create(
                    role=role,
                    permission=permission,
                    defaults={'granted': True}
                )
                
                if created:
                    role_perm_created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ Created: {role.code} → {permission.code}')
                    )
                else:
                    role_perm_updated_count += 1
                    # Only show updated if you want detailed logs
                    # self.stdout.write(
                    #     self.style.WARNING(f'  ↻ Updated: {role.code} → {permission.code}')
                    # )
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Successfully seeded {role_perm_created_count} new role-permission mappings and updated {role_perm_updated_count} existing mappings.'
        ))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✅ Permission seeding completed successfully!'))
