
import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import User
from django.db.models import Count

def fix_duplicates():
    print("Checking for duplicate phone numbers...")
    duplicates = User.objects.values('phone').annotate(count=Count('id')).filter(count__gt=1)
    
    if not duplicates:
        print("No duplicates found.")
        return

    for dup in duplicates:
        phone = dup['phone']
        print(f"Fixing duplicates for phone: {phone}")
        users = User.objects.filter(phone=phone).order_by('date_joined')
        
        # Keep the latest one as is? Or the first one?
        # Usually valid user is the one using it. 
        # Let's keep the last one (most recent) as the valid one, and rename others.
        # Actually safer to rename ALL except one.
        
        # Strategy: Keep the one with most recent login? or most recent creation?
        # Let's keep the last one active.
        
        users_list = list(users)
        # Keep the last one
        user_to_keep = users_list[-1]
        users_to_fix = users_list[:-1]
        
        for i, user in enumerate(users_to_fix):
            new_phone = f"{phone}_dup{i+1}"
            print(f"  - Renaming user {user.email} (ID: {user.id}) phone to {new_phone}")
            user.phone = new_phone
            try:
                user.save()
            except Exception as e:
                print(f"Error saving user {user.id}: {e}")
            
    print("Duplicate resolution complete.")

if __name__ == "__main__":
    fix_duplicates()
