# Deliveroo Backend

A simple Flask backend for a parcel delivery system.

## Quick setup

1. Install dependencies:

   pipenv install

2. Configure environment variables in `.env` (see `.env.example` file in repo). At minimum set:
   - `DATABASE_URL` (example: `postgresql://postgres:password@localhost:5432/deliveroo`)
   - `JWT_SECRET_KEY`

## PostgreSQL setup (Ubuntu/Debian)

```bash
sudo apt update && sudo apt install -y postgresql postgresql-contrib
sudo systemctl start postgresql
# Create database (runs as postgres user)
sudo -u postgres createdb deliveroo
# (Optional) set postgres user password or create a dedicated user
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'password';"
```

Update your `.env` `DATABASE_URL` accordingly (including user and password). Example:

```
DATABASE_URL=postgresql://postgres:password@localhost:5432/deliveroo
```

## Create tables and seed data

Use the included Flask CLI commands (requires `FLASK_APP` set to `app.py` in your env):

```bash
flask create-db
flask seed-db
```

Or run the seeder directly:

```bash
python seed.py
```

The `seed` script will create an admin user (from `ADMIN_EMAIL`/`ADMIN_PASSWORD` env vars or defaults) and sample courier/customer users.

## Quick alternative (SQLite, dev only)

If you don't want to install Postgres, use a local SQLite DB for development/tests:

```bash
export DATABASE_URL="sqlite:///dev.db"
python seed.py
```

---

## Deployment to Render.com

This application is configured for easy deployment to Render.com.

### Prerequisites

1. A [Render.com](https://render.com) account
2. A [Safaricom Developer Portal](https://developer.safaricom.co.ke) account for M-Pesa
3. A [Google Cloud](https://console.cloud.google.com/) account for Maps API

### Step 1: Push to GitHub

Push your code to a GitHub repository:

```bash
git add .
git commit -m "Prepare for production deployment"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### Step 2: Create Render Web Service

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **New +** → **Web Service**
3. Connect your GitHub repository
4. Configure the service:
   - **Name**: `deliveroo-api` (or your preferred name)
   - **Environment**: `Python 3`
   - **Build Command**: `pipenv install`
   - **Start Command**: `pipenv run gunicorn --chdir /Users/andrewsigei/Development/phase_5/project/Deliveroo_backend app:app`
   - **Plan**: Select appropriate plan (Free tier available)

### Step 3: Create PostgreSQL Database

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **New +** → **PostgreSQL**
3. Configure:
   - **Name**: `deliveroo-db` (or your preferred name)
   - **Database Name**: `deliveroo`
   - **User**: `deliveroo`
4. Click **Create Database**

### Step 4: Configure Environment Variables

In your Web Service settings, add the following environment variables:

#### Required:
| Variable | Value |
|----------|-------|
| `DATABASE_URL` | (Auto-provided by Render - connect from PostgreSQL service) |
| `JWT_SECRET_KEY` | `python -c "import secrets; print(secrets.token_hex(32))"` (generate secure random) |
| `FLASK_ENV` | `production` |

#### M-Pesa (Required for payments):
| Variable | Value |
|----------|-------|
| `MPESA_ENVIRONMENT` | `sandbox` (change to `production` when ready) |
| `MPESA_CONSUMER_KEY` | From Safaricom Developer Portal |
| `MPESA_CONSUMER_SECRET` | From Safaricom Developer Portal |
| `MPESA_SHORTCODE` | Your Till Number or Paybill |
| `MPESA_PASSKEY` | From Safaricom Developer Portal |
| `MPESA_CALLBACK_URL` | `https://YOUR_SERVICE.onrender.com/api/payments/callback` |

#### Google Maps (Required for distance calculations):
| Variable | Value |
|----------|-------|
| `GOOGLE_MAPS_API_KEY` | From Google Cloud Console |

#### Optional (Customize):
| Variable | Value |
|----------|-------|
| `CORS_ORIGINS` | `http://localhost:5173,https://your-frontend.com` |
| `ADMIN_EMAIL` | `admin@your-domain.com` |
| `ADMIN_PASSWORD` | `secure-password-here` |

### Step 5: Run Database Migrations

1. In Render Dashboard, go to your Web Service
2. Click **Manual Deploy** → **Deploy latest commit**
3. Or use the **Shell** to run migrations:
   ```bash
   flask db upgrade
   ```

### Step 6: Seed Initial Data

```bash
flask seed-db
```

### Step 7: Verify Deployment

1. Visit `https://YOUR_SERVICE.onrender.com/health`
2. You should see: `{"status": "healthy", ...}`
3. Test the API endpoints with Postman or your frontend

### Troubleshooting

#### "ModuleNotFoundError" during build
- Ensure `requirements.txt` is up to date
- Check that all dependencies are listed

#### Database connection errors
- Verify `DATABASE_URL` is correctly set in environment variables
- Ensure PostgreSQL service is running
- Check that the database user has correct permissions

#### M-Pesa callback not working
- Ensure `MPESA_CALLBACK_URL` is publicly accessible
- For local testing, use [ngrok](https://ngrok.com/) to expose your local server
- Update `MPESA_CALLBACK_URL` when switching between sandbox and production

#### CORS errors
- Add your frontend domain to `CORS_ORIGINS` environment variable
- Format: `https://domain1.com,https://domain2.com`

---

## Testing M-Pesa in Sandbox

1. Use sandbox credentials from [Safaricom Developer Portal](https://developer.safaricom.co.ke)
2. Test phone numbers: Use `254700000000` format (Safaricom test numbers)
3. Use PIN `0812` when prompted on phone
4. Check [M-Pesa Test Tool](https://developer.safaricom.co.ke/test-tools) for more details

---

## Switching to Production M-Pesa

1. Get production credentials from Safaricom
2. Update environment variables:
   - `MPESA_ENVIRONMENT=production`
   - Update `MPESA_CONSUMER_KEY`, `MPESA_CONSUMER_SECRET`, `MPESA_PASSKEY`
   - Update `MPESA_CALLBACK_URL` to your production URL
3. Test with real transactions using small amounts

---

## Security Checklist for Production

- [ ] Change all default passwords
- [ ] Set strong `JWT_SECRET_KEY` (32+ random characters)
- [ ] Enable M-Pesa only in production mode
- [ ] Use HTTPS for all communications
- [ ] Restrict `CORS_ORIGINS` to your frontend domain
- [ ] Enable rate limiting (consider Flask-Limiter)
- [ ] Set up logging and monitoring
- [ ] Regular security updates for dependencies

---

If you'd like, I can also add a GitHub Actions workflow to run `pipenv run pytest` on each PR and ensure the test suite stays green.
