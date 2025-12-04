# Gas Transportation System (GTS) Backend

Django backend for the Gas Transportation System with PostgreSQL integration.

## Setup Instructions

### 1. Prerequisites
- Python 3.10+
- PostgreSQL 12+
- Virtual environment activated

### 2. Environment Configuration
Create a `.env` file in the backend directory with:
```env
POSTGRES_DB=gts
POSTGRES_USER=postgres
POSTGRES_PASSWORD=1234
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Database Setup
The PostgreSQL database is already configured. If you need to reset:
```bash
python reset_db.py
python manage.py migrate
```

### 5. Create Superuser
```bash
python manage.py createsuperuser
```
Enter your email, full name, and password when prompted.

### 6. Run Development Server
```bash
python manage.py runserver
```
Access the admin panel at: http://127.0.0.1:8000/admin/

## Models Overview

### User Management & RBAC

#### User Model
- Custom user model with **email-based authentication**
- Fields: email (unique), full_name, phone, role_in, role_out, is_active, is_staff
- Uses `AbstractBaseUser` and `PermissionsMixin`
- Custom `UserManager` for creating users and superusers

#### Role Model
- Represents different roles in the system (e.g., SUPER_ADMIN, MS_OPERATOR, DBS_OPERATOR, EIC, DRIVER)
- Fields: code (unique), name, description

#### UserRole Model
- Junction table for User ↔ Role relationship
- Supports station-specific assignments
- Fields: user, role, station (nullable for Super Admins), active

#### Station Model (Placeholder)
- Temporary model for foreign key constraints
- Will be fully implemented in a separate module

## Database Schema
All models follow the specifications in `Database Schema Documentation.md`.

## Next Steps
1. Create initial Roles (SUPER_ADMIN, MS_OPERATOR, DBS_OPERATOR, etc.)
2. Assign roles to users via Django Admin
3. Implement Stations, Partners, Vehicles, and other GTS entities
4. Build REST APIs for mobile/frontend integration
