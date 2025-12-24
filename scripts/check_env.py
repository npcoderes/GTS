"""
Environment Variables Validation Script
Checks if all required environment variables are properly configured.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_env():
    """Check if all required environment variables are set."""
    
    # Load .env file if exists
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
        print(f"✓ Loaded .env file from {env_file}")
    else:
        print(f"⚠ No .env file found at {env_file}")
        print("  Copy .env.example to .env and configure it")
        return False
    
    print("\n" + "="*60)
    print("ENVIRONMENT VARIABLES CHECK")
    print("="*60 + "\n")
    
    # Required variables
    required = {
        'SECRET_KEY': 'Django secret key',
        'POSTGRES_DB': 'Database name',
        'POSTGRES_USER': 'Database user',
        'POSTGRES_PASSWORD': 'Database password',
    }
    
    # Optional but recommended
    recommended = {
        'DEBUG': 'Debug mode (should be False in production)',
        'ALLOWED_HOSTS': 'Allowed hosts',
        'CORS_ALLOWED_ORIGINS': 'CORS allowed origins',
        'FIREBASE_CREDENTIALS_FILE': 'Firebase credentials file path',
    }
    
    # Security checks
    security_issues = []
    all_required_set = True
    
    # Check required variables
    print("REQUIRED VARIABLES:")
    print("-" * 60)
    for var, description in required.items():
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if 'PASSWORD' in var or 'SECRET' in var or 'KEY' in var:
                display_value = '*' * 8 + value[-4:] if len(value) > 4 else '*' * len(value)
            else:
                display_value = value[:30] + '...' if len(value) > 30 else value
            print(f"✓ {var:30} = {display_value}")
        else:
            print(f"✗ {var:30} = NOT SET")
            all_required_set = False
    
    print("\n" + "-" * 60)
    print("RECOMMENDED VARIABLES:")
    print("-" * 60)
    for var, description in recommended.items():
        value = os.getenv(var)
        if value:
            if 'PASSWORD' in var or 'SECRET' in var or 'KEY' in var:
                display_value = '*' * 8
            else:
                display_value = value[:50] + '...' if len(value) > 50 else value
            print(f"✓ {var:30} = {display_value}")
        else:
            print(f"⚠ {var:30} = NOT SET (optional)")
    
    # Security checks
    print("\n" + "="*60)
    print("SECURITY CHECKS")
    print("="*60 + "\n")
    
    # Check DEBUG mode
    debug = os.getenv('DEBUG', 'False')
    if debug == 'True':
        security_issues.append("⚠ DEBUG is True - should be False in production")
    else:
        print("✓ DEBUG is False")
    
    # Check SECRET_KEY
    secret_key = os.getenv('SECRET_KEY', '')
    if 'django-insecure' in secret_key.lower():
        security_issues.append("✗ SECRET_KEY contains 'django-insecure' - generate a new one!")
    elif len(secret_key) < 50:
        security_issues.append("⚠ SECRET_KEY is too short (should be 50+ characters)")
    else:
        print("✓ SECRET_KEY looks good")
    
    # Check ALLOWED_HOSTS
    allowed_hosts = os.getenv('ALLOWED_HOSTS', '')
    if '*' in allowed_hosts and debug == 'False':
        security_issues.append("✗ ALLOWED_HOSTS contains '*' - specify exact domains in production")
    else:
        print("✓ ALLOWED_HOSTS configured")
    
    # Check CORS
    cors_all = os.getenv('CORS_ALLOW_ALL_ORIGINS', 'False')
    if cors_all == 'True' and debug == 'False':
        security_issues.append("✗ CORS_ALLOW_ALL_ORIGINS is True - should be False in production")
    else:
        print("✓ CORS configuration looks safe")
    
    # Check database password
    db_password = os.getenv('POSTGRES_PASSWORD', '')
    weak_passwords = ['password', '1234', '12345', 'admin', 'postgres', 'root']
    if db_password.lower() in weak_passwords:
        security_issues.append("✗ Database password is weak - use a strong password!")
    elif len(db_password) < 8:
        security_issues.append("⚠ Database password is short - use 12+ characters")
    else:
        print("✓ Database password looks strong")
    
    # Check Firebase credentials
    firebase_file = os.getenv('FIREBASE_CREDENTIALS_FILE', 'firebase-credentials.json')
    firebase_path = Path(__file__).parent.parent / firebase_file
    if firebase_path.exists():
        print(f"✓ Firebase credentials file found at {firebase_file}")
    else:
        print(f"⚠ Firebase credentials file not found at {firebase_file}")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60 + "\n")
    
    if not all_required_set:
        print("✗ FAILED: Some required environment variables are not set")
        print("  Please configure them in your .env file")
        return False
    
    if security_issues:
        print("⚠ SECURITY ISSUES FOUND:\n")
        for issue in security_issues:
            print(f"  {issue}")
        print("\n  Please fix these issues before deploying to production!")
        return False
    
    print("✓ ALL CHECKS PASSED")
    print("  Your environment is properly configured!")
    return True

if __name__ == '__main__':
    success = check_env()
    sys.exit(0 if success else 1)
