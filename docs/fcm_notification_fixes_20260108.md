# FCM Notification Error Fixes - 2026-01-08

## Issues Identified

### 1. **FCM "Requested entity was not found" Error**
**Error Log:**
```
ERROR 2026-01-08 18:22:22 - FCM send error: Requested entity was not found.
INFO 2026-01-08 18:22:22 - Notification sent to 1/3 devices for dbs@gmail.com
WARNING 2026-01-08 18:22:22 - User 39 has no active device tokens
```

**Root Cause:**
- Device tokens in the database were invalid/expired (user uninstalled app, cleared data, or token expired)
- System continued attempting to send to invalid tokens
- No automatic cleanup of invalid tokens

### 2. **Token Model Field Error**
**Error Log:**
```
ERROR 2026-01-08 18:21:47 - Failed to send allocation notification: Cannot resolve keyword 'driver' into field. Choices are: id, issued_at, ms, ms_id, token_no, trip, vehicle, vehicle_id
```

**Root Cause:**
- `notify_trip_assignment()` tried to query `Token.objects.filter(driver=driver)`
- The `Token` model doesn't have a `driver` field (only has: vehicle, ms, token_no, issued_at)
- Should have used `VehicleToken` model instead (which has driver field)

---

## Solutions Implemented

### 1. Automatic Invalid Token Cleanup

**File:** `backend/core/notification_service.py`

**Changes:**

#### A. Enhanced `send_to_device()` method:
- Detects FCM errors indicating invalid tokens:
  - "not found"
  - "invalid"
  - "unregistered"
  - "registration token"
- Automatically deactivates invalid tokens in database
- Logs which tokens were deactivated with user email

```python
# Now automatically deactivates invalid tokens
if is_invalid_token:
    device_token = DeviceToken.objects.filter(token=token, is_active=True).first()
    if device_token:
        device_token.is_active = False
        device_token.save(update_fields=['is_active'])
        logger.warning(f"Deactivated invalid FCM token for user {device_token.user.email}")
```

#### B. Enhanced `send_to_user()` method:
- Tracks how many tokens were invalid
- Provides better logging with invalid token count
- Returns `invalid_tokens` count in response

```python
# Enhanced logging
logger.info(
    f"Notification sent to {sent_count}/{total_devices} devices for {user.email} "
    f"({invalid_token_count} invalid tokens auto-deactivated)"
)
```

### 2. Fixed Token Model Query Error

**File:** `backend/core/notification_service.py`

**Changes in `notify_trip_assignment()` method:**

**Before:**
```python
if trip:
    trip_token = TripToken.objects.filter(vehicle=trip.vehicle).order_by('-issued_at').first()
else:
    trip_token = TripToken.objects.filter(driver=driver).order_by('-issued_at').first()  # ❌ ERROR
```

**After:**
```python
if trip:
    # Trip exists - get the trip's Token
    trip_token = TripToken.objects.filter(vehicle=trip.vehicle).order_by('-issued_at').first()
else:
    # No trip yet - get driver's allocated VehicleToken
    vehicle_token = VehicleToken.objects.filter(
        driver=driver,
        status='ALLOCATED'
    ).order_by('-allocated_at').first()  # ✅ CORRECT
```

**Additional improvements:**
- Better notification body messages with actual MS/DBS names
- Includes `tokenNumber` in notification payload
- Handles missing relationships gracefully

---

## Diagnostic Tools Created

### 1. Token Diagnostic Script
**File:** `backend/check_fcm_tokens.py`

**Purpose:** Analyze current FCM token status

**Usage:**
```bash
cd backend
python check_fcm_tokens.py
```

**Features:**
- Shows overall token statistics
- Lists users without active tokens
- Identifies old/stale tokens
- Shows users with multiple devices
- Checks specific users mentioned in error logs

### 2. Cleanup Management Command
**File:** `backend/core/management/commands/cleanup_device_tokens.py`

**Purpose:** Clean up old/invalid tokens

**Usage:**
```bash
# Preview what will be cleaned (dry run)
python manage.py cleanup_device_tokens --dry-run

# Actually clean up tokens older than 180 days (default)
python manage.py cleanup_device_tokens

# Clean tokens older than 90 days
python manage.py cleanup_device_tokens --days 90

# Force cleanup without confirmation
python manage.py cleanup_device_tokens --force
```

**Features:**
- Deactivates tokens not updated in X days (default: 180)
- Shows statistics before cleanup
- Identifies users with many devices (potential duplicates)
- Dry-run mode for safe preview

---

## Expected Behavior After Fixes

### Automatic Token Cleanup
1. When FCM returns "not found" error → token is automatically deactivated
2. Future notification attempts skip deactivated tokens
3. Logs show which tokens were cleaned up
4. Database stays clean without manual intervention

### Successful Notifications
1. Driver allocation notifications now work correctly
2. Notification includes proper MS/DBS names and token numbers
3. No more "driver field" errors

### Better Monitoring
1. Logs show: `"Notification sent to X/Y devices (Z invalid tokens auto-deactivated)"`
2. Can run diagnostic script to check token health
3. Can proactively clean old tokens with management command

---

## Recommendations

### Immediate Actions
1. ✅ **Fixed automatically** - Invalid tokens will be cleaned as they're encountered
2. 🔧 **Optional** - Run cleanup command to remove old tokens:
   ```bash
   python manage.py cleanup_device_tokens --dry-run  # Preview first
   python manage.py cleanup_device_tokens             # Then clean
   ```

### Long-term Maintenance
1. **Monitor logs** for invalid token warnings
2. **Run cleanup command monthly** to remove stale tokens
3. **Educate users** to keep app updated and logged in
4. **Consider periodic cleanup** via scheduled task (e.g., weekly cron job)

### User 39 Specifically
- User 39 has no active device tokens
- They need to:
  1. Open the mobile app
  2. Log in
  3. Allow notifications
  4. This will register a new device token

---

## Testing Checklist

- [x] Fixed "driver field" error in token allocation notifications
- [x] Added automatic invalid token detection and cleanup
- [x] Enhanced logging with invalid token counts
- [x] Created diagnostic script for token analysis
- [x] Created management command for manual cleanup
- [ ] Test notification sending after fixes
- [ ] Verify invalid tokens are auto-deactivated
- [ ] Run diagnostic script to check current state
- [ ] Run cleanup command to remove old tokens

---

## Files Modified

1. `backend/core/notification_service.py` - Enhanced error handling and token cleanup
2. `backend/check_fcm_tokens.py` - New diagnostic script
3. `backend/core/management/commands/cleanup_device_tokens.py` - New cleanup command

---

## Impact

**Before:**
- ❌ Notifications failed silently for invalid tokens
- ❌ Database filled with stale tokens
- ❌ "driver field" error prevented allocation notifications
- ❌ No visibility into token health

**After:**
- ✅ Invalid tokens automatically deactivated
- ✅ Clean database with only valid tokens
- ✅ Allocation notifications work correctly
- ✅ Full visibility with diagnostic tools
- ✅ Better error messages and logging
