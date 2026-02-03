"""
Authentication and Authorization Decorators

Role-based access control decorators for securing API endpoints.
Ensures only authorized users (admin, courier, customer) can access specific routes.

"""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app.models.user import User

def admin_required(fn):
    """
    Decorator to require admin role
    Usage: @admin_required
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        return fn(*args, **kwargs)
    return wrapper

def courier_required(fn):
    """
    Decorator to require courier role
    Usage: @courier_required
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if user.role != 'courier':
            return jsonify({'error': 'Courier access required'}), 403
        
        return fn(*args, **kwargs)
    return wrapper

def customer_required(fn):
    """
    Decorator to require customer role
    Usage: @customer_required
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if user.role != 'customer':
            return jsonify({'error': 'Customer access required'}), 403
        
        return fn(*args, **kwargs)
    return wrapper
