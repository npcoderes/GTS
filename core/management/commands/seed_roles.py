"""
Django management command to seed initial GTS roles.
Usage: python manage.py seed_roles
"""
from django.core.management.base import BaseCommand
from core.models import Role


class Command(BaseCommand):
    help = 'Seeds initial roles for the Gas Transportation System'
    
    ROLES = [
        {
            'code': 'SUPER_ADMIN',
            'name': 'Super Administrator',
            'description': 'Full system access with administrative privileges across all modules'
        },
        {
            'code': 'MS_OPERATOR',
            'name': 'MS Operator',
            'description': 'Mother Station operator responsible for vehicle filling and dispatch'
        },
        {
            'code': 'DBS_OPERATOR',
            'name': 'DBS Operator',
            'description': 'Daughter Booster Station operator handling stock requests and decanting'
        },
        {
            'code': 'EIC',
            'name': 'Engineer in Charge',
            'description': 'Engineering oversight, control tower, and system monitoring'
        },
        {
            'code': 'DRIVER',
            'name': 'Driver',
            'description': 'Vehicle driver responsible for transportation between MS and DBS'
        },
        {
            'code': 'FDODO_CUSTOMER',
            'name': 'FDODO Customer',
            'description': 'FDODO customer with access to request management and tracking'
        },
        {
            'code': 'SGL_CUSTOMER',
            'name': 'SGL Customer',
            'description': 'SGL customer with access to transport tracking and stock monitoring'
        },
    ]
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('Seeding GTS Roles...'))
        
        created_count = 0
        updated_count = 0
        
        for role_data in self.ROLES:
            role, created = Role.objects.update_or_create(
                code=role_data['code'],
                defaults={
                    'name': role_data['name'],
                    'description': role_data['description']
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Created: {role.name} ({role.code})')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'  ↻ Updated: {role.name} ({role.code})')
                )
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Successfully seeded {created_count} new roles and updated {updated_count} existing roles.'
        ))
