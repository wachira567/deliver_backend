import os
from typing import Optional
from app import create_app
from extensions import db
from  app.models.user import User


def seed_data(admin_email: Optional[str] = None, admin_password: Optional[str] = None):
    """Create initial users (admin + sample courier/customer).

    - Uses ADMIN_EMAIL and ADMIN_PASSWORD environment variables when available.
    - Idempotent: will not recreate users that already exist.
    - Ensures DB tables exist by calling db.create_all().
    """
    app = create_app()

    admin_email = admin_email or os.getenv("ADMIN_EMAIL", "admin@example.com")
    admin_password = admin_password or os.getenv("ADMIN_PASSWORD", "adminpass")

    with app.app_context():
        # Ensure tables exist
        db.create_all()

        # Create admin if missing
        admin = User.query.filter_by(email=admin_email).first()
        if admin:
            print(f"Admin user already exists: {admin_email}")
        else:
            admin = User(full_name="Admin User", email=admin_email, phone=None, role="admin", is_active=True)
            admin.set_password(admin_password)
            db.session.add(admin)
            db.session.commit()
            print(f"Created admin user: {admin_email}")

        # Sample users
        samples = [
            {"email": "courier@example.com", "role": "courier", "full_name": "Courier User"},
            {"email": "customer@example.com", "role": "customer", "full_name": "Customer User"},
        ]

        for s in samples:
            if not User.query.filter_by(email=s["email"]).first():
                u = User(full_name=s["full_name"], email=s["email"], phone=None, role=s["role"], is_active=True)
                u.set_password(os.getenv("SAMPLE_PASSWORD", "password"))
                db.session.add(u)
                print(f"Created {s['role']} user: {s['email']}")

        db.session.commit()


if __name__ == "__main__":
    seed_data()

