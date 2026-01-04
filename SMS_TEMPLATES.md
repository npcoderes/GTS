# SMS Templates for GTS System

## Overview
This document provides SMS templates for integration with your SMS API gateway. These templates correspond to the email notifications currently implemented in the system.

---

## 1. Welcome SMS (New User Creation)

**Trigger:** When a new user account is created by admin

**Template Name:** `USER_WELCOME`

**SMS Content:**
```
Welcome to Sabarmati Gas Limited!

Your account has been created.

Login Details:
Email: {email}
Phone: {phone}
Password: {password}

Please login and change your password immediately.

- SGL Team
```

**Variables:**
- `{email}` - User's email address
- `{phone}` - User's phone number
- `{password}` - Temporary password

**Character Count:** ~150 characters (1 SMS)

---

## 2. Password Reset OTP SMS

**Trigger:** When user requests password reset (Forgot Password)

**Template Name:** `PASSWORD_RESET_OTP`

**SMS Content:**
```
SGL Password Reset

Your OTP is: {otp}

Valid for 10 minutes.

If you didn't request this, please ignore.

- Sabarmati Gas Limited
```

**Variables:**
- `{otp}` - 6-digit OTP code

**Character Count:** ~100 characters (1 SMS)

---

## 3. Password Reset Success SMS

**Trigger:** After successful password reset

**Template Name:** `PASSWORD_RESET_SUCCESS`

**SMS Content:**
```
SGL Account Update

Your password and MPIN have been successfully reset.

You can now login with your new credentials.

- Sabarmati Gas Limited
```

**Variables:** None

**Character Count:** ~120 characters (1 SMS)

---

## 4. MPIN Setup Confirmation SMS (Optional)

**Trigger:** When user sets up MPIN

**Template Name:** `MPIN_SETUP_SUCCESS`

**SMS Content:**
```
SGL Security Update

Your 4-digit MPIN has been set successfully.

You can now use MPIN for quick login.

- Sabarmati Gas Limited
```

**Variables:** None

**Character Count:** ~110 characters (1 SMS)

---

## Implementation Guide

### API Integration Points

Update the following files to integrate SMS API:

#### 1. `backend/core/utils.py`

Add SMS sending functions:

```python
import requests
from django.conf import settings

def send_sms(phone_number, message):
    """
    Send SMS using client's SMS API gateway
    """
    try:
        # Replace with client's SMS API endpoint
        api_url = settings.SMS_API_URL
        api_key = settings.SMS_API_KEY
        
        payload = {
            'phone': phone_number,
            'message': message,
            'api_key': api_key
        }
        
        response = requests.post(api_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"SMS sent successfully to {phone_number}")
            return True
        else:
            logger.error(f"SMS failed: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"SMS error: {e}")
        return False


def send_welcome_sms(user, raw_password):
    """
    Send welcome SMS to new user
    """
    if not user.phone:
        return
    
    message = f"""Welcome to Sabarmati Gas Limited!

Your account has been created.

Login Details:
Email: {user.email}
Phone: {user.phone}
Password: {raw_password}

Please login and change your password immediately.

- SGL Team"""
    
    send_sms(user.phone, message)


def send_otp_sms(user, otp):
    """
    Send OTP SMS for password reset
    """
    if not user.phone:
        return
    
    message = f"""SGL Password Reset

Your OTP is: {otp}

Valid for 10 minutes.

If you didn't request this, please ignore.

- Sabarmati Gas Limited"""
    
    send_sms(user.phone, message)


def send_reset_success_sms(user):
    """
    Send password reset success SMS
    """
    if not user.phone:
        return
    
    message = """SGL Account Update

Your password and MPIN have been successfully reset.

You can now login with your new credentials.

- Sabarmati Gas Limited"""
    
    send_sms(user.phone, message)
```

#### 2. Update `backend/core/views.py`

Add SMS calls alongside email:

```python
# In UserViewSet.perform_create() - Line ~602
if raw_password:
    try:
        send_welcome_email(user, raw_password)
        send_welcome_sms(user, raw_password)  # ADD THIS LINE
    except Exception as e:
        logger.error(f"Failed to send welcome notifications: {e}")

# In request_password_reset() - Line ~XXX
if user.email:
    try:
        send_otp_email(user, otp)
        send_otp_sms(user, otp)  # ADD THIS LINE
    except Exception as e:
        logger.error(f"Failed to send OTP: {e}")

# In confirm_password_reset() - Line ~XXX
try:
    send_reset_success_email(user)
    send_reset_success_sms(user)  # ADD THIS LINE
except Exception as e:
    logger.error(f"Failed to send success notification: {e}")
```

#### 3. Add to `backend/backend/settings.py`

```python
# SMS Configuration
SMS_API_URL = env('SMS_API_URL', default='https://sms-api.example.com/send')
SMS_API_KEY = env('SMS_API_KEY', default='')
SMS_SENDER_ID = env('SMS_SENDER_ID', default='SGLGAS')
```

#### 4. Add to `.env` file

```env
# SMS API Configuration
SMS_API_URL=https://your-sms-gateway.com/api/send
SMS_API_KEY=your_api_key_here
SMS_SENDER_ID=SGLGAS
```

---

## SMS Template Registration (If Required by Provider)

Some SMS providers require pre-approved templates. Here are the templates in standard format:

### Template 1: Welcome SMS
```
Welcome to Sabarmati Gas Limited! Your account has been created. Login Details: Email: {#var#} Phone: {#var#} Password: {#var#} Please login and change your password immediately. - SGL Team
```

### Template 2: OTP SMS
```
SGL Password Reset. Your OTP is: {#var#}. Valid for 10 minutes. If you didn't request this, please ignore. - Sabarmati Gas Limited
```

### Template 3: Success SMS
```
SGL Account Update. Your password and MPIN have been successfully reset. You can now login with your new credentials. - Sabarmati Gas Limited
```

---

## Testing Checklist

- [ ] Test welcome SMS on user creation
- [ ] Test OTP SMS on forgot password
- [ ] Test success SMS after password reset
- [ ] Verify SMS delivery to all phone number formats
- [ ] Test with international numbers (if applicable)
- [ ] Verify character encoding (special characters)
- [ ] Test rate limiting and error handling
- [ ] Verify SMS logs and delivery reports

---

## Notes

1. **Phone Number Format:** Ensure phone numbers are in E.164 format (+919876543210)
2. **Character Limit:** Each SMS is 160 characters. Messages may be split into multiple SMS
3. **Delivery Reports:** Implement webhook to receive delivery status from SMS provider
4. **Fallback:** If SMS fails, email notification will still be sent
5. **Cost:** Monitor SMS usage for cost optimization
6. **Compliance:** Ensure SMS content complies with TRAI regulations (India)

---

## Support

For SMS API integration support, contact:
- Technical Team: tech@sabarmatigas.com
- SMS Provider Support: [Provider Contact]
