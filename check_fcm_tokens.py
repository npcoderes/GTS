"""
Diagnostic script to check FCM device token status and identify issues.

This script helps diagnose the notification errors you're seeing by:
1. Checking which users have invalid/missing tokens
2. Identifying the specific tokens causing errors
3. Providing recommendations for cleanup

Run from backend directory:
    python check_fcm_tokens.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.notification_models import DeviceToken
from core.models import User, UserRole
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count

def main():
    print("\n" + "=" * 70)
    print("FCM Device Token Diagnostic Report")
    print("=" * 70 + "\n")
    
    # Overall statistics
    total_tokens = DeviceToken.objects.count()
    active_tokens = DeviceToken.objects.filter(is_active=True).count()
    inactive_tokens = DeviceToken.objects.filter(is_active=False).count()
    
    print("📊 Overall Statistics:")
    print(f"  Total tokens: {total_tokens}")
    print(f"  Active tokens: {active_tokens}")
    print(f"  Inactive tokens: {inactive_tokens}")
    print()
    
    # Users without tokens
    users_with_tokens = DeviceToken.objects.filter(is_active=True).values_list('user_id', flat=True).distinct()
    all_users = User.objects.filter(is_active=True).count()
    users_without_tokens = User.objects.filter(is_active=True).exclude(id__in=users_with_tokens)
    
    print("👥 Users Without Active Tokens:")
    print(f"  Total active users: {all_users}")
    print(f"  Users with tokens: {len(set(users_with_tokens))}")
    print(f"  Users without tokens: {users_without_tokens.count()}")
    
    if users_without_tokens.exists():
        print("\n  Users missing tokens:")
        for user in users_without_tokens[:10]:
            roles = UserRole.objects.filter(user=user, active=True).values_list('role__code', flat=True)
            role_str = ", ".join(roles) if roles else "No role"
            print(f"    • ID {user.id}: {user.email} ({role_str})")
        
        if users_without_tokens.count() > 10:
            print(f"    ... and {users_without_tokens.count() - 10} more")
    print()
    
    # Check for old tokens
    cutoff_30_days = timezone.now() - timedelta(days=30)
    cutoff_90_days = timezone.now() - timedelta(days=90)
    
    old_30_days = DeviceToken.objects.filter(is_active=True, updated_at__lt=cutoff_30_days).count()
    old_90_days = DeviceToken.objects.filter(is_active=True, updated_at__lt=cutoff_90_days).count()
    
    print("📅 Token Age Analysis:")
    print(f"  Tokens not updated in 30+ days: {old_30_days}")
    print(f"  Tokens not updated in 90+ days: {old_90_days}")
    print()
    
    # Users with multiple devices
    users_with_multiple = DeviceToken.objects.filter(
        is_active=True
    ).values('user').annotate(
        count=Count('id')
    ).filter(count__gt=1).order_by('-count')
    
    print("📱 Users with Multiple Devices:")
    print(f"  Users with 2+ devices: {users_with_multiple.count()}")
    
    if users_with_multiple.exists():
        print("\n  Top users by device count:")
        for item in users_with_multiple[:10]:
            try:
                user = User.objects.get(id=item['user'])
                tokens = DeviceToken.objects.filter(user=user, is_active=True)
                platforms = ", ".join(tokens.values_list('platform', flat=True))
                print(f"    • {user.email}: {item['count']} devices ({platforms})")
            except User.DoesNotExist:
                pass
    print()
    
    # Check specific user from error log (User 39)
    print("🔍 Checking User 39 (from error log):")
    try:
        user_39 = User.objects.get(id=39)
        tokens_39 = DeviceToken.objects.filter(user=user_39)
        active_tokens_39 = tokens_39.filter(is_active=True)
        
        print(f"  Email: {user_39.email}")
        print(f"  Total tokens: {tokens_39.count()}")
        print(f"  Active tokens: {active_tokens_39.count()}")
        
        if tokens_39.exists():
            print("\n  Token details:")
            for token in tokens_39:
                status = "✅ Active" if token.is_active else "❌ Inactive"
                days_old = (timezone.now() - token.updated_at).days
                print(f"    • {status} | Platform: {token.platform} | "
                      f"Last updated: {days_old} days ago | "
                      f"Token: {token.token[:30]}...")
    except User.DoesNotExist:
        print("  ❌ User 39 not found")
    print()
    
    # Check dbs@gmail.com from error log
    print("🔍 Checking dbs@gmail.com (from error log):")
    try:
        dbs_user = User.objects.get(email='dbs@gmail.com')
        tokens_dbs = DeviceToken.objects.filter(user=dbs_user)
        active_tokens_dbs = tokens_dbs.filter(is_active=True)
        
        print(f"  User ID: {dbs_user.id}")
        print(f"  Total tokens: {tokens_dbs.count()}")
        print(f"  Active tokens: {active_tokens_dbs.count()}")
        
        if tokens_dbs.exists():
            print("\n  Token details:")
            for token in tokens_dbs:
                status = "✅ Active" if token.is_active else "❌ Inactive"
                days_old = (timezone.now() - token.updated_at).days
                print(f"    • {status} | Platform: {token.platform} | "
                      f"Last updated: {days_old} days ago | "
                      f"Token: {token.token[:30]}...")
    except User.DoesNotExist:
        print("  ❌ User dbs@gmail.com not found")
    print()
    
    # Recommendations
    print("💡 Recommendations:")
    if old_90_days > 0:
        print(f"  • Run cleanup command to deactivate {old_90_days} tokens older than 90 days:")
        print(f"    python manage.py cleanup_device_tokens --dry-run")
    
    if users_without_tokens.count() > 0:
        print(f"  • {users_without_tokens.count()} users have no device tokens")
        print(f"    They need to log in to the mobile app to register their devices")
    
    print(f"  • The enhanced notification service will now automatically deactivate")
    print(f"    invalid tokens when FCM returns 'not found' errors")
    
    print("\n" + "=" * 70 + "\n")

if __name__ == '__main__':
    main()
