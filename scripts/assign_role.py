import os
import django
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import User, Role, UserRole

def assign():
    try:
        user = User.objects.get(username='vendor_admin')
        role = Role.objects.get(code='SGL_TRANSPORT_VENDOR')
        
        if not UserRole.objects.filter(user=user, role=role).exists():
            UserRole.objects.create(user=user, role=role, station=None)
            print(f"Assigned {role.name} to {user.username}")
        else:
            print(f"Role {role.name} already assigned to {user.username}")
            
    except Exception:
        traceback.print_exc()

if __name__ == '__main__':
    assign()
