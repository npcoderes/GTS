
import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings') # Assuming backend.settings
django.setup()

from core.models import User
from core.notification_models import DeviceToken

def check_user_tokens(user_id):
    try:
        user = User.objects.get(id=user_id)
        print(f"User found: {user.email} (ID: {user.id})")
        
        tokens = DeviceToken.objects.filter(user=user)
        if tokens.exists():
            print(f"Found {tokens.count()} tokens:")
            for t in tokens:
                print(f"  - ID: {t.id}, Platform: {t.platform}, Active: {t.is_active}, Updated: {t.updated_at}")
                print(f"    Token: {t.token[:50]}...")
        else:
            print("No DeviceToken records found for this user.")
            
        # Check simple User.fcm_token field too
        if user.fcm_token:
            print(f"User.fcm_token field is set: {user.fcm_token[:50]}...")
        else:
            print("User.fcm_token field is empty.")

    except User.DoesNotExist:
        print(f"User with ID {user_id} does not exist.")

if __name__ == "__main__":
    check_user_tokens(37)
