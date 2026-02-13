from flask_restful import Resource
import phonenumbers
from flask import request
from app.models.user import User
from sqlalchemy.exc import IntegrityError
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity
)
from extensions import db

#POST /auth/register → show messages auto-login.
class RegisterResource(Resource):
    def post(self):
        try:
            data = request.get_json()
            print(f"DEBUG REGISTER: Received data: {data}")
            
            if not data:
                return {"message": "Request body is required"}, 400
            
            # Validate required fields
            required_fields = ["full_name", "email", "password", "phone"]
            for field in required_fields:
                if field not in data:
                    return {"message": f"{field} is required"}, 400
            
            role = data.get("role", "customer")
            
            # Validate role
            if role not in ("customer", "courier", "admin"):
                return {"message": "Invalid role"}, 400

            # Normalize and validate courier-specific fields
            vehicle = (data.get("vehicle_type") or "").strip()
            plate = (data.get("plate_number") or "").strip().upper()

            if role == "courier":
                if not vehicle or not plate:
                    return {"message": "Vehicle type and plate number are required for couriers"}, 422
                import re
                if not re.match(r'^[A-Z0-9-]{3,20}$', plate):
                    return {"message": "Invalid plate number format"}, 422
                data["vehicle_type"] = vehicle
                data["plate_number"] = plate
            else:
                # Non-couriers should not submit courier-only fields
                if vehicle or plate:
                    return {"message": "Vehicle info only allowed for couriers"}, 422
            email = User.query.filter_by(email=data['email']).first()
            if email:
                return {"message": "Email already taken"}, 422
            # Format phone number validation
            raw_phone = data.get("phone", "")
            if raw_phone.startswith("0"):
                data["phone"] = "+254" + raw_phone[1:]
            elif raw_phone.startswith("254"):
                data["phone"] = "+" + raw_phone
            
            # Check for existing phone AFTER formatting
            existing_phone = User.query.filter_by(phone=data['phone']).first()
            if existing_phone:
                return {"message": "Phone number already taken"}, 422
            
            password = data.pop("password")
            user = User(**data)
            user.set_password(password)

            db.session.add(user)
            db.session.commit()

            access_token = create_access_token(identity=str(user.id))
            refresh_token = create_refresh_token(identity=str(user.id))


            return {
                "message": "User registered successfully",
                "user": user.to_dict(),
                "access_token": access_token,
                "refresh_token": refresh_token,
            }, 201
        
        except phonenumbers.NumberParseException as e:
            print(f"DEBUG REGISTER ERROR: NumberParseException: {e}")
            return {"message": str(e), "error": "ValidationError"}, 422
        except ValueError as e:
            print(f"DEBUG REGISTER ERROR: ValueError: {e}")
            return {"message": str(e), "error": "ValueError"}, 422
        except IntegrityError as e:
            print(f"DEBUG REGISTER ERROR: IntegrityError: {e}")
            return {"message": "Missing Values", "error": "IntegrityError"}, 422
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"DEBUG REGISTER ERROR: Unexpected: {e}")
            return {"message": str(e), "error": "UnexpectedError"}, 400

#POST /auth/login → store access_token, user.role.

class LoginResource(Resource):
    def post(self):
        try:
            data = request.get_json()
            
            if not data:
                return {"error": "Request body is required"}, 400
            
            email = data.get("email")
            password = data.get("password")

            if not all([email, password]):
                return {"error": "Email and password are required"}, 400
            
            user = User.query.filter_by(email=email).first()
            if not user:
                return {"error": "Invalid email or password"}, 401
            if not user.is_active:
                return {"error": "Account is inactive. Please contact support."}, 403
            
            if not user.check_password(password):
                return {"error": "Invalid email or password"}, 401

            access_token = create_access_token(identity=str(user.id))
            refresh_token = create_refresh_token(identity=str(user.id))

            return {
                "message": "Login successful",
                "user": user.to_dict(),
                "access_token": access_token,
                "refresh_token": refresh_token,
            }, 200
        except Exception as e:
            return {"error": str(e)}, 400
    

class MeResource(Resource):
    @jwt_required()
    def get(self):
        user_id = int(get_jwt_identity())

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
    def post(self): 
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)

        if not user:
            return {"message": "User not found"}, 404

        access_token = create_access_token(identity=str(user.id))

        return {
            "access_token": access_token
        }, 200
