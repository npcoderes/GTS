import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import Role

def create_roles():
    roles = [
        {'code': 'SUPER_ADMIN', 'name': 'Super Admin', 'description': 'Full access to all modules'},
        {'code': 'DBS_OPERATOR', 'name': 'DBS Operator', 'description': 'Manage DBS operations'},
        {'code': 'MS_OPERATOR', 'name': 'MS Operator', 'description': 'Manage MS operations'},
        {'code': 'EIC', 'name': 'Engineer In-Charge (EIC)', 'description': 'Oversee operations'},
        {'code': 'SGL_CUSTOMER', 'name': 'SGL Customer', 'description': 'Customer access'},
        {'code': 'DRIVER', 'name': 'Driver', 'description': 'Vehicle driver'},
        {'code': 'SGL_TRANSPORT_VENDOR', 'name': 'SGL Transport Vendor', 'description': 'Transport vendor management'},
    ]

    print("Creating roles...")
    for role_data in roles:
        role, created = Role.objects.get_or_create(
            code=role_data['code'],
            defaults={
                'name': role_data['name'],
                'description': role_data['description']
            }
        )
        if created:
            print(f"Created role: {role.name}")
        else:
            print(f"Role already exists: {role.name}")

if __name__ == "__main__":
    create_roles()
