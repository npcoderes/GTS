import subprocess
import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def run(cmd, cwd=None, title=None):
    full_cmd = f'start "{title or "Process"}" cmd /k {cmd}'
    subprocess.Popen(full_cmd, shell=True, cwd=cwd)

print("Starting services...")

# 1. Redis (Docker)
run(
    cmd="docker run -d -p 6379:6379 redis",
    title="Redis"
)
time.sleep(2)

# 2. Django Server
run(
    cmd="python manage.py runserver",
    cwd=BASE_DIR,
    title="Django Server"
)
time.sleep(2)

# 3. Celery Worker
run(
    cmd="celery -A backend worker -l info -P solo --concurrency=1",
    cwd=BASE_DIR,
    title="Celery Worker"
)
time.sleep(2)

# 4. Celery Beat
run(
    cmd="celery -A backend.celery beat -l info",
    cwd=BASE_DIR,
    title="Celery Beat"
)
time.sleep(2)

# 5. Ngrok
run(
    cmd="ngrok http 8000",
    title="Ngrok"
)
time.sleep(2)

# 6. Frontend
frontend_dir = os.path.join(BASE_DIR,"frontend-dashboard")
run(
    cmd="npm run start",
    cwd=frontend_dir,
    title="Frontend"
)

print("All services started successfully.")
