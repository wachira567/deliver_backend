"""
Admin Routes
Handles administrative operations for order management and system statistics
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta

from app import db
from app.models.user import User
from app.models.delivery import DeliveryOrder, OrderStatus
from app.models.order_tracking import OrderTracking
from app.models.notification import Notification
from app.auth.decorators import admin_required
from app.services.email_service import EmailService

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


# ============================================================================
# GET ALL ORDERS
# ============================================================================
@admin_bp.route('/orders', methods=['GET'])
@jwt_required()
@admin_required
def get_all_orders():
    """
    Get all orders in the system with optional filters
    
    GET /api/admin/orders
    Query Parameters:
    - status: Filter by order status (PENDING, ASSIGNED, PICKED_UP, etc.)
    - courier_id: Filter by courier
    - date_from: Filter orders from this date (YYYY-MM-DD)
    - date_to: Filter orders until this date (YYYY-MM-DD)
    - limit: Number of orders per page (default: 20)
    - page: Page number (default: 1)
    """
    try:
        # Get query parameters
        status_filter = request.args.get('status')
        courier_id = request.args.get('courier_id')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        limit = int(request.args.get('limit', 20))
        page = int(request.args.get('page', 1))
        
        # Base query
        query = DeliveryOrder.query
        
        # Apply filters
        if status_filter:
            # Check if valid status
            try:
                status_enum = OrderStatus(status_filter)
                query = query.filter_by(status=status_enum)
            except ValueError:
                return jsonify({
                    'error': f'Invalid status. Valid options: {[s.value for s in OrderStatus]}'
                }), 400
        
        if courier_id:
            query = query.filter_by(courier_id=courier_id)
        
        if date_from:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(DeliveryOrder.created_at >= date_from_obj)
        
        if date_to:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(DeliveryOrder.created_at < date_to_obj)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        orders = query.order_by(DeliveryOrder.created_at.desc())\
                     .limit(limit)\
                     .offset((page - 1) * limit)\
                     .all()
        
        # Serialize orders
        orders_data = [order.to_dict() for order in orders]
        
        return jsonify({
            'orders': orders_data,
            'pagination': {
                'total': total,
                'page': page,
                'limit': limit,
                'pages': (total + limit - 1) // limit
            }
        }), 200
    
    except ValueError as e:
        return jsonify({'error': f'Invalid parameter: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to fetch orders: {str(e)}'}), 500


# ============================================================================
# ASSIGN COURIER TO ORDER
# ============================================================================
@admin_bp.route('/orders/<int:order_id>/assign', methods=['PATCH'])
@jwt_required()
@admin_required
def assign_courier(order_id):
    """
    Assign a courier to a delivery order
    
    PATCH /api/admin/orders/:id/assign
    Body:
    {
        "courier_id": 123
    }
    """
    try:
        data = request.get_json()
        
        # Validate input
        if not data or 'courier_id' not in data:
            return jsonify({'error': 'courier_id is required'}), 400
        
        courier_id = data['courier_id']
        
        # Get the order
        order = DeliveryOrder.query.get_or_404(order_id)
        
        # Check if order can be assigned
        if order.status not in [OrderStatus.PENDING, OrderStatus.ASSIGNED]:
            return jsonify({
                'error': f'Cannot assign courier. Order status is {order.status.value}'
            }), 400
        
        # Get the courier
        courier = User.query.get_or_404(courier_id)
        
        # Verify user is actually a courier
        if courier.role != 'courier':
            return jsonify({
                'error': f'User {courier.full_name} is not a courier. Role: {courier.role}'
            }), 400
        
        # Check if courier is active
        if not courier.is_active:
            return jsonify({
                'error': f'Courier {courier.full_name} is not active'
            }), 400
        
        # Assign the courier
        order.courier_id = courier_id
        order.status = OrderStatus.ASSIGNED
        
        # Create tracking update
        tracking = OrderTracking(
            order_id=order.id,
            latitude=order.pickup_lat,
            longitude=order.pickup_lng,
            status=OrderStatus.ASSIGNED,
            location_description="Courier assigned",
            notes=f"Assigned to {courier.full_name}"
        )
        db.session.add(tracking)
        
        # Create notification for customer
        customer_notification = Notification(
            user_id=order.user_id,
            order_id=order.id,
            type='COURIER_ASSIGNED',
            message=f'Courier {courier.full_name} has been assigned to your order #{order.tracking_number}'
        )
        db.session.add(customer_notification)
        
        # Create notification for courier
        courier_notification = Notification(
            user_id=courier_id,
            order_id=order.id,
            type='NEW_ASSIGNMENT',
            message=f'You have been assigned to order #{order.tracking_number}'
        )
        db.session.add(courier_notification)
        
        db.session.commit()
        
        # Send email notification to customer
        customer = User.query.get(order.user_id)
        if customer and customer.email:
            EmailService.send_courier_assigned(
                user_email=customer.email,
                order_id=order.id,
                courier_name=courier.full_name,
                courier_phone=courier.phone or 'N/A'
            )
        
        return jsonify({
            'message': 'Courier assigned successfully',
            'order': order.to_dict(),
            'courier': {
                'id': courier.id,
                'name': courier.full_name,
                'phone': courier.phone
            }
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to assign courier: {str(e)}'}), 500


# ============================================================================
# GET ADMIN DASHBOARD STATISTICS
# ============================================================================
@admin_bp.route('/stats', methods=['GET'])
@jwt_required()
@admin_required
def get_dashboard_stats():
    """
    Get dashboard statistics for admin
    
    GET /api/admin/stats
    Query Parameters:
    - period: 'today', 'week', 'month', 'all' (default: 'all')
    """
    try:
        period = request.args.get('period', 'all')
        
        # Determine date filter
        now = datetime.utcnow()
        if period == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            start_date = now - timedelta(days=7)
        elif period == 'month':
            start_date = now - timedelta(days=30)
        else:
            start_date = None
        
        # Base query
        query = DeliveryOrder.query
        if start_date:
            query = query.filter(DeliveryOrder.created_at >= start_date)
        
        # Total orders
        total_orders = query.count()
        
        # Orders by status
        orders_by_status = {
            'pending': query.filter_by(status=OrderStatus.PENDING).count(),
            'assigned': query.filter_by(status=OrderStatus.ASSIGNED).count(),
            'picked_up': query.filter_by(status=OrderStatus.PICKED_UP).count(),
            'in_transit': query.filter_by(status=OrderStatus.IN_TRANSIT).count(),
            'delivered': query.filter_by(status=OrderStatus.DELIVERED).count(),
            'cancelled': query.filter_by(status=OrderStatus.CANCELLED).count(),
        }
        
        # Revenue (only from delivered orders)
        delivered_orders = query.filter_by(status=OrderStatus.DELIVERED).all()
        total_revenue = sum(float(order.total_price) for order in delivered_orders)
        
        # Active couriers (couriers with at least one assigned order)
        active_couriers = User.query.filter_by(role='courier', is_active=True).count()
        
        # Couriers with active deliveries
        couriers_with_active_deliveries = db.session.query(DeliveryOrder.courier_id)\
            .filter(DeliveryOrder.status.in_([
                OrderStatus.ASSIGNED, 
                OrderStatus.PICKED_UP, 
                OrderStatus.IN_TRANSIT
            ]))\
            .distinct()\
            .count()
        
        # Average delivery time (for delivered orders)
        avg_delivery_time = None
        if delivered_orders:
            delivery_times = []
            for order in delivered_orders:
                if order.delivered_at and order.created_at:
                    delta = order.delivered_at - order.created_at
                    delivery_times.append(delta.total_seconds() / 60)  # minutes
            
            if delivery_times:
                avg_delivery_time = sum(delivery_times) / len(delivery_times)
        
        # Recent orders (last 5)
        recent_orders = DeliveryOrder.query\
            .order_by(DeliveryOrder.created_at.desc())\
            .limit(5)\
            .all()
        
        return jsonify({
            'period': period,
            'summary': {
                'total_orders': total_orders,
                'total_revenue': round(total_revenue, 2),
                'active_couriers': active_couriers,
                'couriers_on_delivery': couriers_with_active_deliveries,
                'average_delivery_time_minutes': round(avg_delivery_time, 2) if avg_delivery_time else None
            },
            'orders_by_status': orders_by_status,
            'recent_orders': [order.to_dict() for order in recent_orders]
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to fetch statistics: {str(e)}'}), 500


# ============================================================================
# UPDATE ORDER STATUS (Admin Override)
# ============================================================================
@admin_bp.route('/orders/<int:order_id>/status', methods=['PATCH'])
@jwt_required()
@admin_required
def update_order_status(order_id):
    """
    Admin can manually update order status
    
    PATCH /api/admin/orders/:id/status
    Body:
    {
        "status": "DELIVERED",
        "notes": "Optional notes"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'status' not in data:
            return jsonify({'error': 'status is required'}), 400
        
        new_status = data['status']
        notes = data.get('notes', 'Status updated by admin')
        
        # Validate status
        try:
            status_enum = OrderStatus(new_status)
        except ValueError:
            return jsonify({
                'error': f'Invalid status. Valid options: {[s.value for s in OrderStatus]}'
            }), 400
        
        # Get order
        order = DeliveryOrder.query.get_or_404(order_id)
        
        # Update status
        old_status = order.status
        order.update_status(status_enum)
        
        # Create tracking update
        tracking = OrderTracking(
            order_id=order.id,
            latitude=order.pickup_lat,
            longitude=order.pickup_lng,
            status=status_enum,
            location_description="Status updated by admin",
            notes=notes
        )
        db.session.add(tracking)
        
        # Create notification
        notification = Notification(
            user_id=order.user_id,
            order_id=order.id,
            type='STATUS_UPDATE',
            message=f'Order #{order.tracking_number} status changed from {old_status.value} to {new_status}'
        )
        db.session.add(notification)
        
        db.session.commit()
        
        # Send email notification
        customer = User.query.get(order.user_id)
        if customer and customer.email:
            EmailService.send_status_update(
                user_email=customer.email,
                order_id=order.id,
                status=new_status
            )
        
        return jsonify({
            'message': 'Order status updated successfully',
            'order': order.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update status: {str(e)}'}), 500