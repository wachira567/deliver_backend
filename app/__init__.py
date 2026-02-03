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

    from app.routes.admin_routes import admin_bp
    app.register_blueprint(admin_bp)
    
    # Register API resources
    from flask_restful import Api
    from app.routes.auth_routes import RegisterResource, LoginResource, MeResource, RefreshResource
    
    api = Api(app)
    api.add_resource(RegisterResource, "/auth/register")
    api.add_resource(LoginResource, "/auth/login")
    api.add_resource(MeResource, "/auth/me")
    api.add_resource(RefreshResource, "/auth/refresh")
    
    return app

