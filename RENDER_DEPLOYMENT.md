# Deploy to Render - Quick Guide

## Option 1: Automatic Deployment (Recommended)

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Ready for Render deployment"
   git push origin main
   ```

2. **Connect to Render**
   - Go to [render.com](https://render.com) and sign up/login
   - Click "New +" → "Blueprint"
   - Connect your GitHub repository
   - Render will auto-detect `render.yaml` and create:
     - PostgreSQL database
     - Web service with environment variables

3. **Done!** Your app will be live at: `https://gts-backend.onrender.com`

## Option 2: Manual Setup

### Step 1: Create PostgreSQL Database
1. Go to Render Dashboard → "New +" → "PostgreSQL"
2. Name: `gts-db`
3. Database: `gts`
4. User: `gts_user`
5. Click "Create Database"
6. **Save the connection details** (Internal Database URL)

### Step 2: Create Web Service
1. Click "New +" → "Web Service"
2. Connect your GitHub repo
3. Configure:
   - **Name**: `gts-backend`
   - **Environment**: `Python 3`
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn backend.wsgi:application`

### Step 3: Add Environment Variables
Go to "Environment" tab and add:

```
SECRET_KEY=<generate-random-50-char-string>
DEBUG=False
ALLOWED_HOSTS=.onrender.com
POSTGRES_DB=<from-database>
POSTGRES_USER=<from-database>
POSTGRES_PASSWORD=<from-database>
POSTGRES_HOST=<from-database-internal-host>
POSTGRES_PORT=5432
FCM_MOCK_MODE=True
```

### Step 4: Deploy
Click "Create Web Service" - Render will build and deploy automatically.

## Post-Deployment

### Create Superuser
```bash
# In Render Dashboard → Shell
python manage.py createsuperuser
```

### Access Admin Panel
`https://your-app.onrender.com/admin/`

## Important Notes

- **Free tier**: Database and web service sleep after 15 min inactivity
- **Logs**: Available in Render Dashboard → Logs tab
- **Database backups**: Automatic on paid plans
- **Custom domain**: Add in Settings → Custom Domain

## Troubleshooting

**Build fails?**
- Check `build.sh` has execute permissions
- Verify `requirements.txt` is complete

**Database connection error?**
- Verify all POSTGRES_* env vars are set correctly
- Use Internal Database URL from Render

**Static files not loading?**
- Run: `python manage.py collectstatic --no-input`
- Check STATIC_ROOT in settings.py
