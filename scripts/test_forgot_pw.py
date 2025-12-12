
import os
import sys
import django
from django.conf import settings

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import User, PasswordResetSession
from rest_framework.test import APIClient
from django.core import mail

def test_forgot_password_flow():
    print("Test: Forgot Password Flow")
    
    email = "testVal@example.com"
    phone = "9998887776"
    
    # Ensure user exists
    if not User.objects.filter(email=email).exists():
        User.objects.create_user(email=email, full_name="Test", phone=phone, password="oldpass")
        print("Created test user")
    
    client = APIClient()
    
    # 1. Request OTP
    print("\n1. Requesting OTP...")
    resp = client.post('/api/auth/forgot-password/request/', {'username': email})
    if resp.status_code == 200:
        print("PASS: Request Success")
    else:
        print(f"FAIL: Request Failed {resp.data}")
        return

    # Fetch OTP from DB (as we can't check email easily here without mock)
    session = PasswordResetSession.objects.filter(user__email=email).last()
    otp = session.otp_code
    print(f"   [Debug] Fetched OTP from DB: {otp}")
    
    # 2. Verify OTP
    print("\n2. Verifying OTP...")
    resp = client.post('/api/auth/forgot-password/verify/', {'username': email, 'otp': otp})
    reset_token = resp.data.get('reset_token')
    
    if resp.status_code == 200 and reset_token:
        print(f"PASS: Verify Success. Token: {reset_token}")
    else:
         print(f"FAIL: Verify Failed {resp.data}")
         return
         
    # 3. Confirm Reset
    print("\n3. Confirming Reset...")
    new_pass = "newSecurePass123"
    new_mpin = "5678"
    
    resp = client.post('/api/auth/forgot-password/confirm/', {
        'reset_token': reset_token,
        'new_password': new_pass,
        'mpin': new_mpin
    })
    
    if resp.status_code == 200:
        print("PASS: Confirm Success")
    else:
        print(f"FAIL: Confirm Failed {resp.data}")
        return
        
    # 4. Verify Login with New Creds
    print("\n4. Verifying Login with New Password...")
    resp = client.post('/api/auth/login/', {'username': email, 'password': new_pass})
    if resp.status_code == 200:
        print("PASS: Login Success")
    else:
        print(f"FAIL: Login Failed {resp.data}")

if __name__ == "__main__":
    test_forgot_password_flow()
