
import os
import django
import sys
import traceback

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

try:
    django.setup()
    from core.models import User
    from django.db.models import Count

    print("Checking for duplicate phone numbers...")
    duplicates = User.objects.values('phone').annotate(count=Count('id')).filter(count__gt=1)
    
    if not duplicates:
        print("No duplicates found.")
    else:
        for dup in duplicates:
            phone = dup['phone']
            print(f"Fixing duplicates for phone: {phone}")
            users = User.objects.filter(phone=phone).order_by('date_joined')
            
            users_list = list(users)
            users_to_fix = users_list[:-1]
            
            for i, user in enumerate(users_to_fix):
                new_phone = f"{phone}_dup{i+1}"
                print(f"  - Renaming user {user.email} (ID: {user.id}) phone to {new_phone}")
                user.phone = new_phone
                user.save()

except Exception:
    with open('error.log', 'w') as f:
        f.write(traceback.format_exc())
    print("Error occurred, wrote to error.log")
