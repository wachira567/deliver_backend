from flask import Flask
from flask_migrate import Migrate
from flask_mail import Mail
from flask_cors import CORS
from config import Config
from extensions import db, jwt

migrate = Migrate()
mail = Mail()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    mail.init_app(app)
    CORS(app)
    
    # Register API resources
    from flask_restful import Api
    from app.routes.auth_routes import RegisterResource, LoginResource, MeResource, RefreshResource
    
    api = Api(app)
    api.add_resource(RegisterResource, "/auth/register")
    api.add_resource(LoginResource, "/auth/login")
    api.add_resource(MeResource, "/auth/me")
    api.add_resource(RefreshResource, "/auth/refresh")

    @app.cli.command("add-courier-constraint")
    def add_courier_constraint():
        """Add DB check constraint to ensure couriers include vehicle info.

        Usage: flask add-courier-constraint
        """
        with app.app_context():
            conn = db.engine.connect()
            # Check if constraint exists
            exists = conn.execute(
                "SELECT constraint_name FROM information_schema.table_constraints WHERE table_name='users' AND constraint_type='CHECK' AND constraint_name='ck_courier_vehicle_required'"
            ).fetchone()

            if exists:
                print("Constraint 'ck_courier_vehicle_required' already exists.")
                return

            conn.execute(
                "ALTER TABLE users ADD CONSTRAINT ck_courier_vehicle_required CHECK ((role != 'courier') OR (vehicle_type IS NOT NULL AND plate_number IS NOT NULL));"
            )
            print("Constraint 'ck_courier_vehicle_required' added successfully.")

    return app

