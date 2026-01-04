
import os
import django
import sys

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import User
from core.notification_models import DeviceToken

def reactivate_token(user_id):
    try:
        user = User.objects.get(id=user_id)
        tokens = DeviceToken.objects.filter(user=user)
        if tokens.exists():
            updated = tokens.update(is_active=True)
            print(f"Reactivated {updated} tokens for user {user.email}.")
        else:
            print("No tokens found to reactivate.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    reactivate_token(37)
