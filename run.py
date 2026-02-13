import os
from dotenv import load_dotenv
import logging

# Force load .env
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path, override=True)
    print(f"Loaded .env from {dotenv_path}")
else:
    print(f".env not found at {dotenv_path}")

print(f"DEBUG: DATABASE_URL={os.getenv('DATABASE_URL')}")

from app import create_app
from extensions import db  # Import your db instance

app = create_app()

# Create tables on startup (safe for production - won't recreate existing tables)
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run()
    