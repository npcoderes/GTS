import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import User
from django.db.models import Count

def check_duplicate_phones():
    duplicates = User.objects.values('phone').annotate(count=Count('id')).filter(count__gt=1)
    
    if duplicates:
        print("Found duplicate phone numbers:")
        for dup in duplicates:
            print(f"Phone: {dup['phone']}, Count: {dup['count']}")
            users = User.objects.filter(phone=dup['phone'])
            for user in users:
                print(f"  - User: {user.email} (ID: {user.id})")
    else:
        print("No duplicate phone numbers found.")

if __name__ == "__main__":
    check_duplicate_phones()
