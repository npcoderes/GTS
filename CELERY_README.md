# Celery & Redis Setup Guide

This document explains the Celery background task system implemented for the GTS backend.

## Overview

Celery is used for:
1. **Expired Driver Assignment Cleanup** - Automatically resets stock requests to `PENDING` when drivers don't accept within the timeout period
2. **EIC Notifications** - Sends push notifications to EIC users when assignments expire

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Django App    │────▶│     Redis       │◀────│  Celery Worker  │
│   (Producer)    │     │   (Broker)      │     │   (Consumer)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                ▲
                                │
                        ┌───────┴───────┐
                        │  Celery Beat  │
                        │  (Scheduler)  │
                        └───────────────┘
```

## Components

| Component | Purpose | Port |
|-----------|---------|------|
| **Redis** | Message broker & result backend | 6379 |
| **Celery Worker** | Processes background tasks | - |
| **Celery Beat** | Schedules periodic tasks | - |

## Configuration

### Settings (`backend/settings.py`)

```python
# Driver Assignment Timeout (configurable)
DRIVER_ASSIGNMENT_TIMEOUT_SECONDS = int(os.getenv('DRIVER_ASSIGNMENT_TIMEOUT_SECONDS', '300'))  # 5 minutes

# Celery Configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Kolkata'

# Periodic Task Schedule
CELERY_BEAT_SCHEDULE = {
    'check-expired-driver-assignments': {
        'task': 'logistics.check_expired_driver_assignments',
        'schedule': 60.0,  # Run every 60 seconds
    },
}
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DRIVER_ASSIGNMENT_TIMEOUT_SECONDS` | `300` | Time (seconds) driver has to accept a trip (5 min default) |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` | Redis for task results |

## Registered Tasks

### 1. `logistics.check_expired_driver_assignments`
- **Location**: `logistics/tasks.py`
- **Schedule**: Every 60 seconds (via Celery Beat)
- **Purpose**: Find expired driver assignments and reset them
- **Actions**:
  1. Finds `StockRequest` with `status='ASSIGNING'` and `assignment_started_at` > 5 min ago
  2. Resets status to `PENDING`
  3. Clears `target_driver`, `assignment_started_at`, `assignment_mode`
  4. Triggers notification task for each expired request

### 2. `logistics.notify_eic_assignment_expired`
- **Location**: `logistics/tasks.py`
- **Triggered by**: `check_expired_driver_assignments` task
- **Purpose**: Send FCM push notification to EIC users
- **Notification**:
  - Title: "Driver Assignment Expired"
  - Body: "{driver_name} did not accept the trip to {dbs_name}. Please reassign."

## Running Celery

### Prerequisites

1. **Install Redis** (choose one):
   ```bash
   # Docker (recommended)
   docker run -d -p 6379:6379 --name redis redis
   
   # Windows - Download from: https://github.com/microsoftarchive/redis/releases
   # macOS
   brew install redis && brew services start redis
   
   # Ubuntu/Debian
   sudo apt install redis-server && sudo systemctl start redis
   ```

2. **Install Python packages**:
   ```bash
   pip install celery redis
   ```

### Start Commands

You need **3 terminals** running:

#### Terminal 1: Django Server
```powershell
cd backend
python manage.py runserver
# or for production:
# daphne -b 0.0.0.0 -p 8000 backend.asgi:application
```

#### Terminal 2: Celery Worker
```powershell
cd backend
celery -A backend worker --loglevel=info --pool=solo
```
> Note: `--pool=solo` is required on Windows

#### Terminal 3: Celery Beat (Scheduler)
```powershell
cd backend
celery -A backend beat --loglevel=info
```

### Combined Command (Development)
For development, you can run worker and beat together:
```powershell
celery -A backend worker --beat --loglevel=info --pool=solo
```

## Changing the Timeout

### Option 1: Environment Variable (No code change)
```powershell
# Windows PowerShell
$env:DRIVER_ASSIGNMENT_TIMEOUT_SECONDS = "600"  # 10 minutes

# Linux/macOS
export DRIVER_ASSIGNMENT_TIMEOUT_SECONDS=600
```

### Option 2: In `.env` file
```
DRIVER_ASSIGNMENT_TIMEOUT_SECONDS=600
```

### Common Timeout Values
| Time | Seconds |
|------|---------|
| 3 min | 180 |
| 5 min | 300 (default) |
| 10 min | 600 |
| 15 min | 900 |
| 30 min | 1800 |

## Flow Diagram

```
EIC assigns driver to StockRequest
         │
         ▼
┌─────────────────────────────────┐
│ StockRequest.status = ASSIGNING │
│ assignment_started_at = now()   │
│ target_driver = selected driver │
└─────────────────────────────────┘
         │
         ▼
    Driver gets FCM notification
         │
    ┌────┴────┐
    ▼         ▼
 ACCEPTS   DOESN'T ACCEPT
    │         │
    ▼         ▼ (after 5 min)
 ASSIGNED  ┌──────────────────────┐
           │ Celery Beat triggers │
           │ check_expired task   │
           └──────────────────────┘
                    │
                    ▼
           ┌──────────────────────┐
           │ Reset to PENDING     │
           │ Notify EIC via FCM   │
           └──────────────────────┘
```

## Monitoring

### Check Worker Status
```powershell
celery -A backend inspect active
celery -A backend inspect scheduled
celery -A backend inspect stats
```

### View Registered Tasks
```powershell
celery -A backend inspect registered
```

### Trigger Task Manually (for testing)
```python
# In Django shell
from logistics.tasks import check_expired_driver_assignments
result = check_expired_driver_assignments.delay()
print(result.get())  # {'expired_count': 5}
```

## Troubleshooting

### Redis Connection Error
```
Error: Error connecting to redis://localhost:6379/0
```
**Solution**: Make sure Redis is running
```powershell
# Check if Redis is running
redis-cli ping  # Should return PONG

# Start Redis (Docker)
docker start redis
```

### Tasks Not Running
1. Check if **both** worker AND beat are running
2. Check worker terminal for errors
3. Verify Redis is accessible

### Worker Not Picking Up Tasks
```powershell
# Restart worker with verbose logging
celery -A backend worker --loglevel=debug --pool=solo
```

### Beat Not Scheduling
```powershell
# Delete old schedule file and restart
del celerybeat-schedule
celery -A backend beat --loglevel=info
```

## Production Deployment (Render)

Add to `render.yaml`:
```yaml
services:
  # ... existing web service ...
  
  - type: worker
    name: celery-worker
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: celery -A backend worker --loglevel=info
    envVars:
      - key: CELERY_BROKER_URL
        fromService:
          type: redis
          name: redis
          property: connectionString

  - type: worker
    name: celery-beat
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: celery -A backend beat --loglevel=info
    envVars:
      - key: CELERY_BROKER_URL
        fromService:
          type: redis
          name: redis
          property: connectionString

  - type: redis
    name: redis
    plan: free
```

## Files Modified/Created

| File | Purpose |
|------|---------|
| `backend/celery.py` | Celery app configuration |
| `backend/__init__.py` | Import Celery app on Django startup |
| `backend/settings.py` | Celery & timeout settings |
| `logistics/tasks.py` | Background task definitions |
| `requirements.txt` | Added celery, redis packages |

## Related Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/driver/pending-offers` | GET | Driver checks pending trip offers |
| `/api/driver-trips/accept/` | POST | Driver accepts trip (validates timeout) |
| `/api/driver-trips/reject/` | POST | Driver rejects trip |
| `/api/eic/stock-requests/{id}/status/` | PATCH | EIC assigns driver |

---

*Last Updated: December 2025*
