"""
Courier Routes
Handles courier operations for viewing and updating assigned deliveries
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

from app import db
from app.models.user import User
from app.models.delivery import DeliveryOrder, OrderStatus
from app.models.order_tracking import OrderTracking
from app.models.notification import Notification
from app.auth.decorators import courier_required
from app.services.email_service import EmailService

courier_bp = Blueprint('courier', __name__, url_prefix='/api/courier')


# ============================================================================
# GET ASSIGNED ORDERS
# ============================================================================
@courier_bp.route('/orders', methods=['GET'])
@jwt_required()
@courier_required
def get_assigned_orders():
    """
    Get all orders assigned to the current courier
    
    GET /api/courier/orders
    Query Parameters:
    - status: Filter by order status (ASSIGNED, PICKED_UP, IN_TRANSIT, DELIVERED)
    - limit: Number of orders per page (default: 20)
    - page: Page number (default: 1)
    """
    try:
        current_user_id = get_jwt_identity()
        courier = User.query.get(current_user_id)
        
        # Get query parameters
        status_filter = request.args.get('status')
        limit = int(request.args.get('limit', 20))
        page = int(request.args.get('page', 1))
        
        # Base query - only orders assigned to this courier
        query = DeliveryOrder.query.filter_by(courier_id=current_user_id)
        
        # Apply status filter if provided
        if status_filter:
            try:
                status_enum = OrderStatus(status_filter)
                query = query.filter_by(status=status_enum)
            except ValueError:
                return jsonify({
                    'error': f'Invalid status. Valid options: {[s.value for s in OrderStatus]}'
                }), 400
        
        # Get total count
        total = query.count()
        
        # Apply pagination and sorting (most recent first)
        orders = query.order_by(DeliveryOrder.created_at.desc())\
                     .limit(limit)\
                     .offset((page - 1) * limit)\
                     .all()
        
        # Serialize orders with details
        orders_data = [order.to_dict(include_details=True) for order in orders]
        
        return jsonify({
            'orders': orders_data,
            'courier': {
                'id': courier.id,
                'name': courier.full_name,
                'phone': courier.phone
            },
            'pagination': {
                'total': total,
                'page': page,
                'limit': limit,
                'pages': (total + limit - 1) // limit
            }
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to fetch orders: {str(e)}'}), 500


# ============================================================================
# UPDATE ORDER STATUS
# ============================================================================
@courier_bp.route('/orders/<int:order_id>/status', methods=['PATCH'])
@jwt_required()
@courier_required
def update_order_status(order_id):
    """
    Update the status of an assigned order
    Courier can update: ASSIGNED → PICKED_UP → IN_TRANSIT → DELIVERED
    
    PATCH /api/courier/orders/:id/status
    Body:
    {
        "status": "PICKED_UP",
        "notes": "Optional notes about the status update"
    }
    """
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate input
        if not data or 'status' not in data:
            return jsonify({'error': 'status is required'}), 400
        
        new_status = data['status']
        notes = data.get('notes', '')
        
        # Validate status
        valid_courier_statuses = [
            OrderStatus.PICKED_UP.value,
            OrderStatus.IN_TRANSIT.value,
            OrderStatus.DELIVERED.value
        ]
        
        if new_status not in valid_courier_statuses:
            return jsonify({
                'error': f'Invalid status. Couriers can only set: {valid_courier_statuses}'
            }), 400
        
        try:
            status_enum = OrderStatus(new_status)
        except ValueError:
            return jsonify({'error': 'Invalid status value'}), 400
        
        # Get the order
        order = DeliveryOrder.query.get_or_404(order_id)
        
        # Verify courier owns this order
        if order.courier_id != current_user_id:
            return jsonify({
                'error': 'You are not assigned to this order'
            }), 403
        
        # Validate status transition
        current_status = order.status
        
        # Define valid transitions
        valid_transitions = {
            OrderStatus.ASSIGNED: [OrderStatus.PICKED_UP],
            OrderStatus.PICKED_UP: [OrderStatus.IN_TRANSIT],
            OrderStatus.IN_TRANSIT: [OrderStatus.DELIVERED],
        }
        
        if current_status not in valid_transitions:
            return jsonify({
                'error': f'Cannot update status from {current_status.value}'
            }), 400
        
        if status_enum not in valid_transitions[current_status]:
            return jsonify({
                'error': f'Invalid transition from {current_status.value} to {new_status}. '
                        f'Valid next status: {[s.value for s in valid_transitions[current_status]]}'
            }), 400
        
        # Update order status
        old_status = order.status
        order.update_status(status_enum)
        
        # If delivered, set delivered timestamp
        if status_enum == OrderStatus.DELIVERED:
            order.delivered_at = datetime.utcnow()
        
        # Create tracking update
        tracking = OrderTracking(
            order_id=order.id,
            latitude=order.current_latitude or order.pickup_lat,
            longitude=order.current_longitude or order.pickup_lng,
            status=status_enum,
            location_description=f"Status updated to {new_status}",
            notes=notes or f"Status changed from {old_status.value} to {new_status}"
        )
        db.session.add(tracking)
        
        # Create notification for customer
        notification = Notification(
            user_id=order.user_id,
            order_id=order.id,
            type='STATUS_UPDATE',
            message=f'Your order #{order.tracking_number} is now {new_status}'
        )
        db.session.add(notification)
        
        db.session.commit()
        
        # Send email notification to customer
        customer = User.query.get(order.user_id)
        if customer and customer.email:
            if status_enum == OrderStatus.DELIVERED:
                EmailService.send_delivery_complete(
                    user_email=customer.email,
                    order_id=order.id
                )
            else:
                EmailService.send_status_update(
                    user_email=customer.email,
                    order_id=order.id,
                    status=new_status
                )
        
        return jsonify({
            'message': f'Order status updated to {new_status}',
            'order': order.to_dict(include_details=True)
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update status: {str(e)}'}), 500


# ============================================================================
# UPDATE CURRENT LOCATION
# ============================================================================
@courier_bp.route('/orders/<int:order_id>/location', methods=['PATCH'])
@jwt_required()
@courier_required
def update_location(order_id):
    """
    Update the courier's current location for an order
    Used for real-time tracking
    
    PATCH /api/courier/orders/:id/location
    Body:
    {
        "latitude": -1.286389,
        "longitude": 36.817223,
        "location_description": "Optional description (e.g., 'Near City Hall')"
    }
    """
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate input
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        if 'latitude' not in data or 'longitude' not in data:
            return jsonify({'error': 'latitude and longitude are required'}), 400
        
        latitude = data['latitude']
        longitude = data['longitude']
        location_description = data.get('location_description', 'Location updated')
        
        # Validate coordinates
        try:
            latitude = float(latitude)
            longitude = float(longitude)
            
            if not (-90 <= latitude <= 90):
                return jsonify({'error': 'Invalid latitude. Must be between -90 and 90'}), 400
            if not (-180 <= longitude <= 180):
                return jsonify({'error': 'Invalid longitude. Must be between -180 and 180'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'latitude and longitude must be numbers'}), 400
        
        # Get the order
        order = DeliveryOrder.query.get_or_404(order_id)
        
        # Verify courier owns this order
        if order.courier_id != current_user_id:
            return jsonify({
                'error': 'You are not assigned to this order'
            }), 403
        
        # Only allow location updates for active deliveries
        if order.status not in [OrderStatus.PICKED_UP, OrderStatus.IN_TRANSIT]:
            return jsonify({
                'error': f'Cannot update location for order with status {order.status.value}'
            }), 400
        
        # Update order's current location
        order.current_latitude = latitude
        order.current_longitude = longitude
        
        # Create tracking point
        tracking = OrderTracking(
            order_id=order.id,
            latitude=latitude,
            longitude=longitude,
            status=order.status,
            location_description=location_description,
            notes='Courier location updated'
        )
        db.session.add(tracking)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Location updated successfully',
            'current_location': {
                'latitude': float(order.current_latitude),
                'longitude': float(order.current_longitude),
                'updated_at': tracking.created_at.isoformat()
            }
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update location: {str(e)}'}), 500


# ============================================================================
# GET SINGLE ORDER DETAILS
# ============================================================================
@courier_bp.route('/orders/<int:order_id>', methods=['GET'])
@jwt_required()
@courier_required
def get_order_details(order_id):
    """
    Get detailed information about a specific assigned order
    
    GET /api/courier/orders/:id
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Get the order
        order = DeliveryOrder.query.get_or_404(order_id)
        
        # Verify courier owns this order
        if order.courier_id != current_user_id:
            return jsonify({
                'error': 'You are not assigned to this order'
            }), 403
        
        # Get tracking history
        tracking_history = [track.to_dict() for track in order.tracking_updates]
        
        # Serialize order with full details
        order_data = order.to_dict(include_details=True)
        order_data['tracking_history'] = tracking_history
        
        # Add customer contact info
        customer = User.query.get(order.user_id)
        if customer:
            order_data['customer'] = {
                'name': customer.full_name,
                'phone': customer.phone,
                'email': customer.email
            }
        
        return jsonify({
            'order': order_data
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to fetch order: {str(e)}'}), 500


# ============================================================================
# GET COURIER STATISTICS
# ============================================================================
@courier_bp.route('/stats', methods=['GET'])
@jwt_required()
@courier_required
def get_courier_stats():
    """
    Get statistics for the current courier
    
    GET /api/courier/stats
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Total deliveries
        total_deliveries = DeliveryOrder.query.filter_by(
            courier_id=current_user_id
        ).count()
        
        # Completed deliveries
        completed_deliveries = DeliveryOrder.query.filter_by(
            courier_id=current_user_id,
            status=OrderStatus.DELIVERED
        ).count()
        
        # Active deliveries (currently in progress)
        active_deliveries = DeliveryOrder.query.filter(
            DeliveryOrder.courier_id == current_user_id,
            DeliveryOrder.status.in_([
                OrderStatus.ASSIGNED,
                OrderStatus.PICKED_UP,
                OrderStatus.IN_TRANSIT
            ])
        ).count()
        
        # Today's deliveries
        from datetime import datetime, timedelta
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        todays_deliveries = DeliveryOrder.query.filter(
            DeliveryOrder.courier_id == current_user_id,
            DeliveryOrder.created_at >= today_start
        ).count()
        
        # Calculate success rate
        success_rate = 0
        if total_deliveries > 0:
            success_rate = (completed_deliveries / total_deliveries) * 100
        
        return jsonify({
            'summary': {
                'total_deliveries': total_deliveries,
                'completed_deliveries': completed_deliveries,
                'active_deliveries': active_deliveries,
                'todays_deliveries': todays_deliveries,
                'success_rate': round(success_rate, 2)
            }
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to fetch statistics: {str(e)}'}), 500