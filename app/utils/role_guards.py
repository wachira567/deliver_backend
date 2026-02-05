from functools import wraps
from flask_jwt_extended import (
    verify_jwt_in_request,
    get_jwt
)
from flask import jsonify

def role_required(*allowed_roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()

            claims = get_jwt()
            user_role = claims.get("role")

            if user_role not in allowed_roles:
                return jsonify({
                    "message": "You are not authorized to access this resource"
                }), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


admin_required = role_required("admin") #only admins can access
customer_required = role_required("customer")#only customers can access
courier_required = role_required("courier") #only courier can access
admin_courier_required = role_required("admin", "courier") #admins and couriers can access
admin_customer_required = role_required("admin", "customer") #admins and customers can access


#EXAMPLE USAGE:
"""
class AdminDashboard(Resource):
    @admin_required
    def get(self):
        return {"message": "Welcome admin"}, 200


class CourierOrders(Resource):
    @courier_required
    def get(self):
        return {"message": "Here are your orders"}, 200
"""