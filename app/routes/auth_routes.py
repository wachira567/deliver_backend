from flask_restful import Resource, reqparse
import phonenumbers
from flask import jsonify
from app.models.user import User
from sqlalchemy.exc import IntegrityError
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity
)
from extensions import db

register_parser = reqparse.RequestParser()
register_parser.add_argument("full_name", type=str,required=True, help="Full name is required")
register_parser.add_argument("email", type=str,required=True, help="Email is required")
register_parser.add_argument("password",type=str ,required=True, help="Password is required")
register_parser.add_argument("phone", type=str,required=False)

#POST /auth/register → show messages auto-login.
class RegisterResource(Resource):
    def post(self):
        try:
            data = register_parser.parse_args()
            email = User.query.filter_by(email=data['email']).first()
            if email:
                return {"message": "Email already  taken"}, 422
            phone = User.query.filter_by(phone=data.get('phone')).first()
            if phone:
                return {"message": "Phone number already taken"}, 422
            password = data.pop("password")
            user = User(**data)
            user.set_password(password)

            db.session.add(user)
            db.session.commit()

            access_token = create_access_token(identity=user.id)
            refresh_token = create_refresh_token(identity=user.id)


            return (
            jsonify(
                {
                    "message": "User registered successfully",
                    "user": user.to_dict(),
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                }
            ),
            201,
        )
        except phonenumbers.NumberParseException as e:
            return {"message": str(e), "error": "ValidationError"}, 422
        except ValueError as e:
            return {"message": str(e), "error": "ValueError"}, 422
        except IntegrityError as e:
            print(str(e))
            return {"message": "Missing Values", "error": "IntegrityError"}, 422

#POST /auth/login → store access_token, user.role.

login_parser = reqparse.RequestParser()
login_parser.add_argument("email", type=str, required=True, help="Email is required")
login_parser.add_argument("password", type=str, required=True, help="Password is required")
class LoginResource(Resource):
    def post(self):
        data = login_parser.parse_args()

        email = data.get("email")
        password = data.get("password")

        if not all([email, password]):
            return jsonify({"error": "email and password are required"}), 400
        
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({"error": "Invalid email or password"}), 401
        if not user.is_active:
            return jsonify({"error": "Account is disabled"}), 403
                # In auth_routes.py, validate phone before DB check if provided:
        if data.get('phone'):
            phone = User.query.filter_by(phone=data['phone']).first()
            if phone:
                return {"message": "Phone number already taken"}, 422


        if not user.check_password(password):
            return jsonify({"error": "Invalid email or password"}), 401

        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)

        return jsonify(
            {
                "message": "Login successful",
                "user": user.to_dict(),
                "access_token": access_token,
                "refresh_token": refresh_token,
            }
        ),200
    

class MeResource(Resource):
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()

        user = User.query.get(user_id)

        if not user:
            return {"message": "User not found"}, 404

        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat()
        }, 200

#refresh token endpoint
class RefreshResource(Resource):
    @jwt_required(refresh=True)
    def refresh(self):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return {"message": "User not found"}, 404

        access_token = create_access_token(identity=user.id)

        return {
            "access_token": access_token
        }, 200