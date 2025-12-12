
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import User
from rest_framework.test import APIClient
from django.urls import reverse

def verify_auth_features():
    print("Verifying Auth Features...")
    
    # 1. Create a User with Force Reset
    email = "testVal@example.com"
    phone = "9998887776"
    password = "password123"
    
    if User.objects.filter(email=email).exists():
        User.objects.filter(email=email).delete()
        
    user = User.objects.create_user(
        email=email,
        full_name="Test User",
        phone=phone,
        password=password,
        is_password_reset_required=True
    )
    print(f"Created user {user.email} with reset_required={user.is_password_reset_required}")
    
    client = APIClient()
    
    # 2. Login with Email
    print("\n[Test] Login with Email (Expect Reset flag + Token)")
    response = client.post('/api/auth/login/', {'username': email, 'password': password})
    if response.status_code == 200:
        if response.data.get('reset_required'):
            print("PASS: reset_required is True")
        else:
            print("FAIL: reset_required flag missing")
            
        if response.data.get('token'):
             print("PASS: Token returned even with reset_required")
             # Set token for subsequent requests
             client.credentials(HTTP_AUTHORIZATION='Token ' + response.data['token'])
        else:
             print("FAIL: Token NOT returned")
    else:
        print(f"FAIL: Login failed {response.data}")

    # 3. Login with Phone
    print("\n[Test] Login with Phone (Expect Success)")
    try:
        response = client.post('/api/auth/login/', {'username': phone, 'password': password})
        if response.status_code == 200:
            print("PASS: Phone login successful")
        else:
            print(f"FAIL: Phone login failed {response.data}")
    except Exception as e:
        print(f"FAIL: Phone login raised exception: {e}")
        
    # 4. Change Password with MPIN (New Requirement: No Old Password needed if Authenticated)
    print("\n[Test] Change Password + Set MPIN (Simplified Flow)")
    new_password = "newpassword456"
    mpin = "9999"
    # Authenticate via Token from Step 2 (already set in client credentials)
    # No old_password sent!
    
    response = client.post('/api/auth/change-password/', {
        'new_password': new_password,
        'mpin': mpin
    })
    
    if response.status_code == 200:
        print("PASS: Password changed and MPIN set")
        user.refresh_from_db()
        if not user.is_password_reset_required:
            print("PASS: reset_required flag cleared")
        else:
            print("FAIL: reset_required flag NOT cleared")
        
        if user.mpin:
            print("PASS: MPIN stored from change-password flow")
        else:
            print("FAIL: MPIN NOT stored from change-password flow")
    else:
        print(f"FAIL: Password change failed {response.data}")
        
    # 5. Set MPIN
    print("\n[Test] Set MPIN")
    mpin = "1234"
    response = client.post('/api/auth/mpin/set/', {'mpin': mpin, 'password': new_password})
    if response.status_code == 200:
        print("PASS: MPIN set")
        user.refresh_from_db()
        if user.mpin:
            print("PASS: MPIN stored")
        else:
            print("FAIL: MPIN not stored")
    else:
        print(f"FAIL: Set MPIN failed {response.data}")
        
    # 6. Login with MPIN
    print("\n[Test] Login with MPIN")
    client.logout()
    response = client.post('/api/auth/login/', {'username': email, 'mpin': mpin})
    if response.status_code == 200:
        print("PASS: MPIN Login successful")
    else:
        print(f"FAIL: MPIN Login failed {response.data}")

if __name__ == "__main__":
    verify_auth_features()
