from flask import Flask
from flask_migrate import Migrate
from flask_mail import Mail
from flask_cors import CORS
from config import Config
from extensions import db, jwt
from dotenv import load_dotenv


load_dotenv()


migrate = Migrate()
mail = Mail()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Import models so Alembic can detect them
    from app import models
    jwt.init_app(app)
    mail.init_app(app)
    
    # Configure CORS with proper settings for preflight requests
    # Load CORS origins from environment variable for production flexibility
    cors_origins_str = os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173')
    cors_origins = [origin.strip() for origin in cors_origins_str.split(',')]
    
    CORS(app, 
         resources={
             r"/api/*": {
                 "origins": cors_origins,
                 "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
                 "allow_headers": ["Content-Type", "Authorization", "Access-Control-Allow-Credentials"],
                 "supports_credentials": True,
                 "preflight_max_age": 86400  # 24 hours
             }
         },
         supports_credentials=True,
         expose_headers=["Content-Type", "Authorization"],
         max_age=86400
    )

    # Create API Instance
    from flask_restful import Api
    api = Api(app)


    # Register Auth resources
    from app.routes.auth_routes import RegisterResource, LoginResource, MeResource, RefreshResource
    api.add_resource(RegisterResource, "/api/auth/register")
    api.add_resource(LoginResource, "/api/auth/login")
    api.add_resource(MeResource, "/api/auth/me")
    api.add_resource(RefreshResource, "/api/auth/refresh")

    # Register admin resources
    from app.routes.admin_routes import (
        AdminUsersResource,
        AdminOrdersResource, 
        AdminAssignCourierResource,
        AdminStatsResource, 
        AdminUpdateOrderStatusResource
    )

    api.add_resource(AdminUsersResource, "/api/admin/users")
    api.add_resource(AdminOrdersResource, "/api/admin/orders")
    api.add_resource(AdminAssignCourierResource, "/api/admin/orders/<int:order_id>/assign")
    api.add_resource(AdminStatsResource, "/api/admin/stats")
    api.add_resource(AdminUpdateOrderStatusResource, "/api/admin/orders/<int:order_id>/status")


    # Register courier routes
    from app.routes.courier_routes import (
        CourierOrdersResource,
        CourierOrderDetailResource,
        CourierUpdateStatusResource,
        CourierUpdateLocationResource,
        CourierStatsResource
    )

    api.add_resource(CourierOrdersResource, "/api/courier/orders")
    api.add_resource(CourierOrderDetailResource,  "/api/courier/orders/<int:order_id>")
    api.add_resource(CourierUpdateStatusResource, "/api/courier/orders/<int:order_id>/status")
    api.add_resource(CourierUpdateLocationResource, "/api/courier/orders/<int:order_id>/location")
    api.add_resource(CourierStatsResource, "/api/courier/stats")

    # Register Blueprint routes
    from app.routes.order_routes import orders_bp
    app.register_blueprint(orders_bp)

    from app.routes.payment_routes import payments_bp
    app.register_blueprint(payments_bp)

    return app

