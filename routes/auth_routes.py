from flask_restful import Resource, reqparse
import phonenumbers
from flask_bycrypt import generate_password_hash
from flask import jsonify
from models.user import User
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
            pw_hash = generate_password_hash(data["password"]).decode("utf-8")

            del data["password"]

            user = User(**data, password_hash=pw_hash)
            db.session.add(user)
            db.session.commit()

            access_token = create_access_token(identity=user)
            refresh_token = create_refresh_token(identity=user)


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

