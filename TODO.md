# ============================================
# Deliveroo Backend - Deployment Plan
# Target: Render.com
# ============================================

## Information Gathered:
- Flask REST API with SQLAlchemy ORM
- PostgreSQL database (needs production setup)
- JWT authentication
- M-Pesa payment integration
- Google Maps API integration
- Flask-Migrate for database migrations

## Plan:

### 1. Create Environment Template
- [x] Create `.env.example` with all required environment variables

### 2. Security Hardening
- [x] Remove hardcoded JWT secret from `app.py`
- [x] Remove hardcoded M-Pesa credentials from `payment_service.py`
- [x] Add production-safe configuration defaults

### 3. Dependencies Files
- [x] Create `requirements.txt` for pip installation (Render uses pip)
- [x] Keep `Pipfile` for development

### 4. Web Server Configuration
- [x] Create `Procfile` for Gunicorn/Procfile-based deployment
- [x] Create `gunicorn.conf.py` for production server settings
- [x] Update `app.py` for production WSGI handling

### 5. Database Configuration
- [x] Update `config.py` for Render PostgreSQL auto-detection
- [x] Add database connection pool settings for production

### 6. CORS Configuration
- [x] Make CORS origins configurable via environment
- [x] Add production frontend domain support

### 7. Static Files & root Route
- [x] Add root route handler for Render health checks

### 8. Documentation
- [x] Update README.md with deployment instructions

## Files Created:
1. [x] `.env.example` - Environment variables template
2. [x] `requirements.txt` - Python dependencies
3. [x] `Procfile` - Gunicorn start command
4. [x] `gunicorn.conf.py` - Production server configuration
5. [x] `render.yaml` - Infrastructure as code blueprint

## Files Modified:
1. [x] `app.py` - Removed hardcoded JWT secrets, configurable token expiry
2. [x] `app/__init__.py` - Made CORS configurable via environment
3. [x] `app/services/payment_service.py` - Removed hardcoded M-Pesa credentials, added lazy initialization
4. [x] `app/routes/payment_routes.py` - Updated to use lazy M-Pesa service initialization
5. [x] `README.md` - Added comprehensive deployment instructions

## Post-Deployment Checklist:
- [ ] Create PostgreSQL database on Render
- [ ] Set environment variables in Render dashboard:
  - [ ] `DATABASE_URL` (auto-provided)
  - [ ] `JWT_SECRET_KEY` (generate secure random)
  - [ ] `FLASK_ENV=production`
  - [ ] `MPESA_*` credentials
  - [ ] `GOOGLE_MAPS_API_KEY`
  - [ ] `CORS_ORIGINS`
- [ ] Run database migrations: `flask db upgrade`
- [ ] Seed initial data: `flask seed-db`
- [ ] Test health endpoint: `https://your-app.onrender.com/health`
- [ ] Verify M-Pesa integration works
- [ ] Update `.env` from `.env.example` and keep it safe

