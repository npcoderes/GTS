# Production Deployment Guide

## 🚀 Required Services & Processes

Your backend requires **5 processes** to run in production:

1. **PostgreSQL** - Database
2. **Redis** - Message broker & cache
3. **Django/Gunicorn** - Web server
4. **Celery Worker** - Background tasks
5. **Celery Beat** - Scheduled tasks
6. **Daphne** (Optional) - WebSocket support

---

## 📋 Prerequisites

### Required Software
```bash
# PostgreSQL 12+
sudo apt install postgresql postgresql-contrib

# Redis 6+
sudo apt install redis-server

# Python 3.10+
sudo apt install python3.10 python3.10-venv python3-pip
```

---

## 🔧 Setup Steps

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
nano .env
```

**Required variables:**
```env
SECRET_KEY=your-production-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
POSTGRES_DB=gts_production
POSTGRES_USER=gts_user
POSTGRES_PASSWORD=strong-password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### 3. Database Setup
```bash
# Create database
sudo -u postgres psql
CREATE DATABASE gts_production;
CREATE USER gts_user WITH PASSWORD 'strong-password';
GRANT ALL PRIVILEGES ON DATABASE gts_production TO gts_user;
\q

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput
```

---

## 🏃 Running Processes

### Development (Single Command)
```bash
# Start all services manually in separate terminals

# Terminal 1: Django
python manage.py runserver

# Terminal 2: Celery Worker
celery -A backend worker -l info

# Terminal 3: Celery Beat
celery -A backend beat -l info
```

---

## 🎯 Production Commands

### 1. Start PostgreSQL
```bash
# Check status
sudo systemctl status postgresql

# Start
sudo systemctl start postgresql

# Enable on boot
sudo systemctl enable postgresql
```

### 2. Start Redis
```bash
# Check status
sudo systemctl status redis

# Start
sudo systemctl start redis

# Enable on boot
sudo systemctl enable redis

# Test connection
redis-cli ping
# Should return: PONG
```

### 3. Start Django with Gunicorn
```bash
# Production command
gunicorn backend.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --timeout 120 \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    --log-level info
```

### 4. Start Celery Worker
```bash
# Production command
celery -A backend worker \
    --loglevel=info \
    --logfile=logs/celery-worker.log \
    --concurrency=4
```

### 5. Start Celery Beat (Scheduler)
```bash
# Production command
celery -A backend beat \
    --loglevel=info \
    --logfile=logs/celery-beat.log \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### 6. Start Daphne (WebSocket - Optional)
```bash
# If using WebSockets
daphne -b 0.0.0.0 -p 8001 backend.asgi:application
```

---

## 🔄 Process Management with Systemd

### Create Service Files

#### 1. Gunicorn Service
```bash
sudo nano /etc/systemd/system/gts-gunicorn.service
```

```ini
[Unit]
Description=GTS Gunicorn Service
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/path/to/backend
Environment="PATH=/path/to/venv/bin"
EnvironmentFile=/path/to/backend/.env
ExecStart=/path/to/venv/bin/gunicorn backend.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --timeout 120 \
    --access-logfile /path/to/backend/logs/access.log \
    --error-logfile /path/to/backend/logs/error.log
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 2. Celery Worker Service
```bash
sudo nano /etc/systemd/system/gts-celery-worker.service
```

```ini
[Unit]
Description=GTS Celery Worker
After=network.target redis.service postgresql.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/path/to/backend
Environment="PATH=/path/to/venv/bin"
EnvironmentFile=/path/to/backend/.env
ExecStart=/path/to/venv/bin/celery -A backend worker \
    --loglevel=info \
    --logfile=/path/to/backend/logs/celery-worker.log \
    --concurrency=4 \
    --detach
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 3. Celery Beat Service
```bash
sudo nano /etc/systemd/system/gts-celery-beat.service
```

```ini
[Unit]
Description=GTS Celery Beat Scheduler
After=network.target redis.service postgresql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/path/to/backend
Environment="PATH=/path/to/venv/bin"
EnvironmentFile=/path/to/backend/.env
ExecStart=/path/to/venv/bin/celery -A backend beat \
    --loglevel=info \
    --logfile=/path/to/backend/logs/celery-beat.log
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Enable and Start Services
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable services (start on boot)
sudo systemctl enable gts-gunicorn
sudo systemctl enable gts-celery-worker
sudo systemctl enable gts-celery-beat

# Start services
sudo systemctl start gts-gunicorn
sudo systemctl start gts-celery-worker
sudo systemctl start gts-celery-beat

# Check status
sudo systemctl status gts-gunicorn
sudo systemctl status gts-celery-worker
sudo systemctl status gts-celery-beat
```

---

## 🐳 Docker Deployment (Alternative)

### docker-compose.yml
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:14
    environment:
      POSTGRES_DB: gts_production
      POSTGRES_USER: gts_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  web:
    build: .
    command: gunicorn backend.wsgi:application --bind 0.0.0.0:8000 --workers 4
    volumes:
      - .:/app
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - postgres
      - redis

  celery-worker:
    build: .
    command: celery -A backend worker -l info
    volumes:
      - .:/app
    env_file:
      - .env
    depends_on:
      - postgres
      - redis

  celery-beat:
    build: .
    command: celery -A backend beat -l info
    volumes:
      - .:/app
    env_file:
      - .env
    depends_on:
      - postgres
      - redis

volumes:
  postgres_data:
  static_volume:
  media_volume:
```

### Start with Docker
```bash
docker-compose up -d
```

---

## 📊 Process Summary

| Process | Command | Port | Required | Purpose |
|---------|---------|------|----------|---------|
| **PostgreSQL** | `systemctl start postgresql` | 5432 | ✅ Yes | Database |
| **Redis** | `systemctl start redis` | 6379 | ✅ Yes | Message broker |
| **Gunicorn** | `gunicorn backend.wsgi:application` | 8000 | ✅ Yes | Web server |
| **Celery Worker** | `celery -A backend worker` | - | ✅ Yes | Background tasks |
| **Celery Beat** | `celery -A backend beat` | - | ✅ Yes | Scheduled tasks |
| **Daphne** | `daphne backend.asgi:application` | 8001 | ⚠️ Optional | WebSockets |

---

## 🔍 Monitoring & Logs

### Check Service Status
```bash
# All services
sudo systemctl status gts-*

# Individual services
sudo systemctl status gts-gunicorn
sudo systemctl status gts-celery-worker
sudo systemctl status gts-celery-beat
```

### View Logs
```bash
# Gunicorn logs
tail -f logs/access.log
tail -f logs/error.log

# Celery logs
tail -f logs/celery-worker.log
tail -f logs/celery-beat.log

# Application logs
tail -f logs/info.log
tail -f logs/error.log

# Systemd logs
sudo journalctl -u gts-gunicorn -f
sudo journalctl -u gts-celery-worker -f
```

### Check Redis
```bash
# Connect to Redis
redis-cli

# Check keys
KEYS *

# Monitor commands
MONITOR
```

### Check Celery Tasks
```bash
# Active tasks
celery -A backend inspect active

# Registered tasks
celery -A backend inspect registered

# Stats
celery -A backend inspect stats
```

---

## 🚨 Troubleshooting

### Service Won't Start
```bash
# Check logs
sudo journalctl -u gts-gunicorn -n 50
sudo journalctl -u gts-celery-worker -n 50

# Check permissions
ls -la /path/to/backend
sudo chown -R www-data:www-data /path/to/backend

# Check environment
sudo systemctl show gts-gunicorn | grep Environment
```

### Database Connection Issues
```bash
# Test connection
psql -h localhost -U gts_user -d gts_production

# Check PostgreSQL status
sudo systemctl status postgresql

# Check logs
sudo tail -f /var/log/postgresql/postgresql-14-main.log
```

### Redis Connection Issues
```bash
# Test connection
redis-cli ping

# Check status
sudo systemctl status redis

# Check logs
sudo tail -f /var/log/redis/redis-server.log
```

### Celery Not Processing Tasks
```bash
# Check worker status
celery -A backend inspect active

# Restart worker
sudo systemctl restart gts-celery-worker

# Check Redis connection
redis-cli
> KEYS celery*
```

---

## 🔐 Security Checklist

- [ ] `DEBUG=False` in production
- [ ] Strong `SECRET_KEY` generated
- [ ] `ALLOWED_HOSTS` configured
- [ ] Database password is strong
- [ ] Redis password set (if exposed)
- [ ] Firewall configured (only 80, 443 open)
- [ ] SSL/TLS certificate installed
- [ ] File permissions correct (www-data)
- [ ] `.env` file not in git
- [ ] Logs directory writable

---

## 📈 Performance Tuning

### Gunicorn Workers
```bash
# Formula: (2 x CPU cores) + 1
# For 4 CPU cores: 9 workers
gunicorn backend.wsgi:application --workers 9
```

### Celery Concurrency
```bash
# Match CPU cores
celery -A backend worker --concurrency=4
```

### Database Connection Pooling
Add to `settings.py`:
```python
DATABASES = {
    'default': {
        # ... existing config
        'CONN_MAX_AGE': 600,  # 10 minutes
    }
}
```

---

## 🎯 Quick Start Commands

### Development
```bash
# Start all in one terminal (for testing)
python manage.py runserver & \
celery -A backend worker -l info & \
celery -A backend beat -l info
```

### Production
```bash
# Start all services
sudo systemctl start postgresql redis
sudo systemctl start gts-gunicorn gts-celery-worker gts-celery-beat

# Check all services
sudo systemctl status gts-*

# Stop all services
sudo systemctl stop gts-gunicorn gts-celery-worker gts-celery-beat
```

---

## 📞 Support

**Check logs first:**
```bash
tail -f logs/error.log
sudo journalctl -u gts-* -f
```

**Restart services:**
```bash
sudo systemctl restart gts-gunicorn
sudo systemctl restart gts-celery-worker
sudo systemctl restart gts-celery-beat
```

---

**Last Updated**: 2024
**Required Processes**: 5 (PostgreSQL, Redis, Gunicorn, Celery Worker, Celery Beat)
