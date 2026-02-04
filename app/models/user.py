from extensions import  db, bcrypt
from sqlalchemy.orm import validates
from sqlalchemy import CheckConstraint
from sqlalchemy_serializer import SerializerMixin
import phonenumbers



class User(db.Model, SerializerMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=True)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(
        db.Enum("courier", "customer", "admin", name="user_roles"),
        default="customer",
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "(role != 'courier') OR (vehicle_type IS NOT NULL AND plate_number IS NOT NULL)",
            name="ck_courier_vehicle_required",
        ),
    )

    vehicle_type = db.Column(db.String(50), nullable=True)
    plate_number = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    @validates("plate_number")
    def validate_plate_number(self, key, number):
        # Ensure courier has a plate, normalize and validate format
        if number is None or number.strip() == "":
            if self.role == "courier":
                raise ValueError("Plate number is required for couriers")
            return number
        plate = number.strip().upper()
        if len(plate) < 7:
            raise ValueError("Plate number must be at least 7 characters")
        return plate

    serialize_rules = ("-password_hash",)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)
    
    @validates("email")
    def validate_email(self, key, address):
        if "@" not in address:
            raise ValueError("Invalid email address")
        return address
    
    @validates("phone")
    def validate_phone(self, key, number):
        # Skip validation if phone is None or empty
        if number is None or number == "":
            return number
        
        parsed = phonenumbers.parse(number, None)
        is_valid = phonenumbers.is_valid_number(parsed)

        if not is_valid:
            raise ValueError("Enter a valid phone number")
        elif "+" not in number:
            raise ValueError("Phone number must include country code")
        return number

    @validates("vehicle_type")
    def validate_vehicle_type(self, key, vehicle):
        vehicle = (vehicle or "").strip()
        if self.role == "courier":
            if not vehicle:
                raise ValueError("Vehicle type is required for couriers")
        return vehicle