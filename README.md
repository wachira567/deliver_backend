# Deliveroo Backend

A simple Flask backend for a parcel delivery system.

## Quick setup

1. Install dependencies:

   pipenv install

2. Configure environment variables in `.env` (see `.env` file in repo). At minimum set:
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

If you'd like, I can also add a GitHub Actions workflow to run `pipenv run pytest` on each PR and ensure the test suite stays green.
