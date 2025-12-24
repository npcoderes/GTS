"""
Backend Cleanup Script
Safely removes duplicate and unnecessary files
"""
import os
import shutil
from pathlib import Path

# Get backend root directory
BACKEND_ROOT = Path(__file__).parent.parent

def cleanup():
    """Remove unnecessary files and folders"""
    
    print("🧹 Starting Backend Cleanup...\n")
    
    removed_count = 0
    saved_space = 0
    
    # Files to delete
    files_to_delete = [
        'gts-app-ce5ca-firebase-adminsdk-fbsvc-560c4032e5.json',
        'core/gts-app-ce5ca-firebase-adminsdk-fbsvc-560c4032e5.json',
        'db.sqlite3',
        'celerybeat-schedule',
        'celerybeat-schedule-shm',
        'celerybeat-schedule-wal',
        'error.log',
        'reuirements.txt',
        'create_cancelled_trip.txt',
        'to-do_app.txt',
    ]
    
    # Folders to delete
    folders_to_delete = [
        'dbs_decantings',
        'ms_fillings',
        'staticfiles',
    ]
    
    # Delete files
    print("📄 Removing duplicate/unnecessary files...")
    for file_path in files_to_delete:
        full_path = BACKEND_ROOT / file_path
        if full_path.exists():
            try:
                size = full_path.stat().st_size
                full_path.unlink()
                removed_count += 1
                saved_space += size
                print(f"  ✓ Deleted: {file_path} ({size / 1024:.1f} KB)")
            except Exception as e:
                print(f"  ✗ Failed to delete {file_path}: {e}")
        else:
            print(f"  ⊘ Not found: {file_path}")
    
    # Delete folders
    print("\n📁 Removing duplicate/unnecessary folders...")
    for folder_path in folders_to_delete:
        full_path = BACKEND_ROOT / folder_path
        if full_path.exists() and full_path.is_dir():
            try:
                # Calculate folder size
                folder_size = sum(f.stat().st_size for f in full_path.rglob('*') if f.is_file())
                shutil.rmtree(full_path)
                removed_count += 1
                saved_space += folder_size
                print(f"  ✓ Deleted: {folder_path}/ ({folder_size / 1024 / 1024:.1f} MB)")
            except Exception as e:
                print(f"  ✗ Failed to delete {folder_path}: {e}")
        else:
            print(f"  ⊘ Not found: {folder_path}/")
    
    # Clean Python cache
    print("\n🐍 Cleaning Python cache files...")
    cache_count = 0
    for pycache in BACKEND_ROOT.rglob('__pycache__'):
        try:
            shutil.rmtree(pycache)
            cache_count += 1
        except:
            pass
    
    for pyc in BACKEND_ROOT.rglob('*.pyc'):
        try:
            pyc.unlink()
            cache_count += 1
        except:
            pass
    
    if cache_count > 0:
        print(f"  ✓ Removed {cache_count} cache files/folders")
    
    # Summary
    print("\n" + "="*60)
    print("✅ CLEANUP COMPLETE!")
    print("="*60)
    print(f"📊 Files/Folders Removed: {removed_count}")
    print(f"💾 Space Saved: {saved_space / 1024 / 1024:.2f} MB")
    print("\n⚠️  Remember to:")
    print("  1. Test your application: python manage.py runserver")
    print("  2. Regenerate staticfiles: python manage.py collectstatic")
    print("  3. Commit changes to git")
    print("="*60)

if __name__ == '__main__':
    # Confirm before proceeding
    print("⚠️  This will delete duplicate and unnecessary files.")
    print("📋 See CLEANUP_GUIDE.md for details.\n")
    
    response = input("Continue? (yes/no): ").strip().lower()
    
    if response in ['yes', 'y']:
        cleanup()
    else:
        print("❌ Cleanup cancelled.")
