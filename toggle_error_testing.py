#!/usr/bin/env python
"""
Script to enable/disable API error testing mode.
Usage: python toggle_error_testing.py [on|off]
"""

import sys
import os

def toggle_error_testing(mode):
    """Enable or disable error testing middleware"""
    settings_path = os.path.join(os.path.dirname(__file__), 'backend', 'settings.py')
    
    if not os.path.exists(settings_path):
        print("❌ settings.py not found!")
        return False
    
    with open(settings_path, 'r') as f:
        content = f.read()
    
    middleware_line = "    'core.test_error_middleware.ForceAPIErrorsMiddleware',"
    
    if mode == 'on':
        if middleware_line in content:
            print("✅ Error testing is already ON")
            return True
        
        # Add the middleware
        if "'backend.middleware.RequestLoggingMiddleware'," in content:
            content = content.replace(
                "'backend.middleware.RequestLoggingMiddleware',",
                "'backend.middleware.RequestLoggingMiddleware',\n    \n    # TEMPORARY: Force API errors for testing (REMOVE AFTER TESTING)\n    'core.test_error_middleware.ForceAPIErrorsMiddleware',"
            )
            
            with open(settings_path, 'w') as f:
                f.write(content)
            
            print("✅ Error testing mode ENABLED")
            print("📝 All APIs (except login) will now return test errors")
            print("🔄 Restart your Django server to apply changes")
            return True
        else:
            print("❌ Could not find middleware section in settings.py")
            return False
    
    elif mode == 'off':
        if middleware_line not in content:
            print("✅ Error testing is already OFF")
            return True
        
        # Remove the middleware and its comment
        lines = content.split('\n')
        new_lines = []
        skip_next = False
        
        for line in lines:
            if "# TEMPORARY: Force API errors for testing" in line:
                skip_next = True
                continue
            if skip_next and middleware_line.strip() in line:
                skip_next = False
                continue
            new_lines.append(line)
        
        content = '\n'.join(new_lines)
        
        with open(settings_path, 'w') as f:
            f.write(content)
        
        print("✅ Error testing mode DISABLED")
        print("📝 APIs will now work normally")
        print("🔄 Restart your Django server to apply changes")
        return True
    
    else:
        print("❌ Invalid mode. Use 'on' or 'off'")
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python toggle_error_testing.py [on|off]")
        print("\nExamples:")
        print("  python toggle_error_testing.py on   # Enable error testing")
        print("  python toggle_error_testing.py off  # Disable error testing")
        sys.exit(1)
    
    mode = sys.argv[1].lower()
    success = toggle_error_testing(mode)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()