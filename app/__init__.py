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

    # Create API Instance
    from flask_restful import Api
    api = Api(app)


    # Register Auth resources
    from app.routes.auth_routes import RegisterResource, LoginResource, MeResource, RefreshResource
    api.add_resource(RegisterResource, "/auth/register")
    api.add_resource(LoginResource, "/auth/login")
    api.add_resource(MeResource, "/auth/me")
    api.add_resource(RefreshResource, "/auth/refresh")

    # Register admin resources
    from app.routes.admin_routes import (
        AdminOrdersResource, 
        AdminAssignCourierResource,
        AdminStatsResource, 
        AdminUpdateOrderStatusResource
    )

    api.add_resource(AdminOrdersResource, "/admin/orders")
    api.add_resource(AdminAssignCourierResource, "/admin/orders/<int:order_id>/assign")
    api.add_resource(AdminStatsResource, "/admin/stats")
    api.add_resource(AdminUpdateOrderStatusResource, "/admin/orders/<int:order_id>/status")


    # Register courier routes
    from app.routes.courier_routes import (
        CourierOrdersResource,
        CourierOrderDetailResource,
        CourierUpdateStatusResource,
        CourierUpdateLocationResource,
        CourierStatsResource
    )

    api.add_resource(CourierOrdersResource, "/courier/orders")
    api.add_resource(CourierOrderDetailResource,  "/courier/orders/<int:order_id>")
    api.add_resource(CourierUpdateStatusResource, "/courier/orders/<int:order_id>/status")
    api.add_resource(CourierUpdateLocationResource, "/courier/orders/<int:order_id>/location")
    api.add_resource(CourierStatsResource, "/courier/stats")
    
    return app

