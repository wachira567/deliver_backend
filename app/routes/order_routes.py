from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from decimal import Decimal

from app import db
from app.models.delivery import DeliveryOrder, OrderStatus
from app.models.order_tracking import OrderTracking
from app.models.payment import Payment
from app.models import User, Notification
from app.services.pricing_service import PricingService
from app.services.maps_service import MapsService
from app.validators.order_validators import OrderValidator

orders_bp = Blueprint('orders', __name__, url_prefix='/api/orders')

#  CREATE ORDER 
@orders_bp.route('/', methods=['POST'])
@jwt_required()
def create_order():
    """
    Create a new delivery order
    POST /api/orders
    """
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    # Validate input data
    is_valid, validated_data, errors = OrderValidator.validate_create_order(data)
    
    if not is_valid:
        return jsonify({'errors': errors}), 400
    
    try:
        # Get price breakdown and distance
        order_summary = PricingService.create_order_summary(validated_data)
        
        # Determine weight category
        weight_category = PricingService.determine_weight_category(validated_data['weight_kg'])
        
        # Calculate estimated delivery time
        estimated_minutes = order_summary['estimated_delivery']['minutes']
        estimated_delivery_time = datetime.utcnow() + timedelta(minutes=estimated_minutes)
        
        # Create order object
        order = DeliveryOrder(
            user_id=current_user_id,
            pickup_lat=validated_data['pickup_lat'],
            pickup_lng=validated_data['pickup_lng'],
            pickup_address=validated_data['pickup_address'],
            pickup_phone=validated_data.get('pickup_phone'),
            
            destination_lat=validated_data['destination_lat'],
            destination_lng=validated_data['destination_lng'],
            destination_address=validated_data['destination_address'],
            destination_phone=validated_data.get('destination_phone'),
            
            weight_kg=validated_data['weight_kg'],
            weight_category=weight_category,
            parcel_description=validated_data.get('parcel_description'),
            parcel_dimensions=validated_data.get('parcel_dimensions'),
            fragile=validated_data.get('fragile', False),
            insurance_required=validated_data.get('insurance_required', False),
            is_express=validated_data.get('is_express', False),
            is_weekend=validated_data.get('is_weekend', False),
            
            distance_km=order_summary['distance']['km'],
            base_price=Decimal(str(order_summary['price_breakdown']['base_price'])),
            distance_price=Decimal(str(order_summary['price_breakdown']['distance_price'])),
            weight_price=Decimal(str(order_summary['price_breakdown']['weight_price'])),
            extra_charges=Decimal(str(order_summary['price_breakdown']['extra_charges']['total'])),
            total_price=Decimal(str(order_summary['price_breakdown']['total_price'])),
            
            estimated_delivery_time=estimated_delivery_time,
            status=OrderStatus.PENDING
        )
        
        db.session.add(order)
        db.session.flush()  # Get order ID for tracking
        
        # Create initial tracking record
        tracking = OrderTracking(
            order_id=order.id,
            latitude=validated_data['pickup_lat'],
            longitude=validated_data['pickup_lng'],
            status=OrderStatus.PENDING,
            location_description="Order created",
            notes="Waiting for courier assignment"
        )
        db.session.add(tracking)
        
        # Create initial payment record
        payment = Payment(
            order_id=order.id,
            amount=order.total_price,
            payment_status='PENDING'
        )
        db.session.add(payment)
        
        # Create notification for user
        notification = Notification(
            user_id=current_user_id,
            order_id=order.id,
            type='STATUS_UPDATE',
            message=f'Your order #{order.tracking_number} has been created successfully. '
                   f'Estimated delivery: {estimated_delivery_time.strftime("%b %d, %H:%M")}'
        )
        db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Order created successfully',
            'order': order.to_dict(include_details=True),
            'summary': order_summary,
            'tracking_number': order.tracking_number
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create order: {str(e)}'}), 500

#  GET ALL ORDERS 
@orders_bp.route('/', methods=['GET'])
@jwt_required()
def get_orders():
    """
    Get orders for the current user
    GET /api/orders
    Query parameters:
    - status: filter by status
    - limit: number of orders per page
    - page: page number
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    # Get query parameters
    status_filter = request.args.get('status')
    limit = int(request.args.get('limit', 20))
    page = int(request.args.get('page', 1))
    
    # Base query based on user role
    if user.role == 'ADMIN':
        query = DeliveryOrder.query
    elif user.role == 'COURIER':
        query = DeliveryOrder.query.filter_by(courier_id=user.courier_profile.id)
    else:
        query = DeliveryOrder.query.filter_by(user_id=current_user_id)
    
    # Apply status filter if provided
    if status_filter and status_filter in [s.value for s in OrderStatus]:
        query = query.filter_by(status=OrderStatus(status_filter))
    
    # Pagination
    total = query.count()
    orders = query.order_by(DeliveryOrder.created_at.desc())\
                 .limit(limit)\
                 .offset((page - 1) * limit)\
                 .all()
    
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

#  GET SINGLE ORDER 
@orders_bp.route('/<int:order_id>', methods=['GET'])
@jwt_required()
def get_order(order_id):
    """
    Get specific order details
    GET /api/orders/:id
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    order = DeliveryOrder.query.get_or_404(order_id)
    
    # Check permissions
    if user.role == 'USER' and order.user_id != current_user_id:
        return jsonify({'error': 'Unauthorized access to this order'}), 403
    
    if user.role == 'COURIER':
        if not user.courier_profile or order.courier_id != user.courier_profile.id:
            return jsonify({'error': 'Unauthorized access to this order'}), 403
    
    # Get tracking history
    tracking_history = [track.to_dict() for track in order.tracking_updates]
    
    order_data = order.to_dict(include_details=True)
    order_data['tracking_history'] = tracking_history
    
    # Add payment info if exists
    if order.payment:
        order_data['payment'] = order.payment.to_dict()
    
    return jsonify({'order': order_data}), 200

#  UPDATE DESTINATION 
@orders_bp.route('/<int:order_id>/destination', methods=['PATCH'])
@jwt_required()
def update_destination(order_id):
    """
    Update order destination (before pickup only)
    PATCH /api/orders/:id/destination
    """
    current_user_id = get_jwt_identity()
    order = DeliveryOrder.query.get_or_404(order_id)
    
    # Check if user owns the order
    if order.user_id != current_user_id:
        return jsonify({'error': 'Unauthorized to update this order'}), 403
    
    data = request.get_json()
    
    # Validate if destination can be updated
    if not order.can_update_destination():
        return jsonify({'error': 'Destination can only be updated for pending orders'}), 400
    
    # Validate destination data
    is_valid, validated_data, errors = OrderValidator.validate_update_destination(data)
    
    if not is_valid:
        return jsonify({'errors': errors}), 400
    
    try:
        # Calculate new distance and price
        origin = (float(order.pickup_lat), float(order.pickup_lng))
        destination = (float(validated_data['destination_lat']), 
                      float(validated_data['destination_lng']))
        
        maps_service = MapsService()
        new_distance = maps_service.calculate_distance(origin, destination)
        
        # Recalculate price with new distance
        price_breakdown = PricingService.calculate_price_breakdown(
            distance_km=new_distance['distance_km'],
            weight_kg=float(order.weight_kg),
            is_fragile=order.fragile,
            needs_insurance=order.insurance_required,
            is_express=order.is_express,
            is_weekend=order.is_weekend
        )
        
        # Update order with new destination and price
        order.destination_lat = validated_data['destination_lat']
        order.destination_lng = validated_data['destination_lng']
        order.destination_address = validated_data['destination_address']
        order.destination_phone = validated_data.get('destination_phone', order.destination_phone)
        
        order.distance_km = Decimal(str(new_distance['distance_km']))
        order.distance_price = Decimal(str(price_breakdown['distance_price']))
        order.total_price = Decimal(str(price_breakdown['total_price']))
        
        # Recalculate estimated delivery time
        estimated_minutes = PricingService.calculate_estimated_delivery_time(
            new_distance['distance_km'], order.is_express
        )
        order.estimated_delivery_time = datetime.utcnow() + timedelta(minutes=estimated_minutes)
        
        # Update payment amount
        if order.payment:
            order.payment.amount = order.total_price
        
        # Create tracking update
        tracking = OrderTracking(
            order_id=order.id,
            latitude=order.destination_lat,
            longitude=order.destination_lng,
            status=OrderStatus.PENDING,
            location_description="Destination updated",
            notes=f"New destination: {validated_data['destination_address']}"
        )
        db.session.add(tracking)
        
        # Create notification
        notification = Notification(
            user_id=current_user_id,
            order_id=order.id,
            type='STATUS_UPDATE',
            message=f'Destination updated for order #{order.tracking_number}. '
                   f'New estimated delivery: {order.estimated_delivery_time.strftime("%b %d, %H:%M")}'
        )
        db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Destination updated successfully',
            'order': order.to_dict(include_details=True),
            'new_price': float(order.total_price),
            'new_distance_km': float(order.distance_km)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update destination: {str(e)}'}), 500

#  CANCEL ORDER 
@orders_bp.route('/<int:order_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_order(order_id):
    """
    Cancel an order (before pickup only)
    POST /api/orders/:id/cancel
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    order = DeliveryOrder.query.get_or_404(order_id)
    
    # Check permissions
    if user.role == 'USER' and order.user_id != current_user_id:
        return jsonify({'error': 'Unauthorized to cancel this order'}), 403
    
    if user.role == 'COURIER':
        if not user.courier_profile or order.courier_id != user.courier_profile.id:
            return jsonify({'error': 'Unauthorized to cancel this order'}), 403
    
    # Check if order can be cancelled
    if not order.can_cancel():
        return jsonify({'error': 'Order cannot be cancelled at this stage'}), 400
    
    try:
        # Update order status
        order.update_status(OrderStatus.CANCELLED)
        
        # Update payment status
        if order.payment:
            order.payment.payment_status = 'CANCELLED'
        
        # Create tracking update
        tracking = OrderTracking(
            order_id=order.id,
            latitude=order.pickup_lat,
            longitude=order.pickup_lng,
            status=OrderStatus.CANCELLED,
            location_description="Order cancelled",
            notes=f"Cancelled by {user.role.lower()}"
        )
        db.session.add(tracking)
        
        # Create notification
        notification = Notification(
            user_id=order.user_id,
            order_id=order.id,
            type='STATUS_UPDATE',
            message=f'Order #{order.tracking_number} has been cancelled'
        )
        db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Order cancelled successfully',
            'order': order.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to cancel order: {str(e)}'}), 500

#  GET ORDER TRACKING 
@orders_bp.route('/<int:order_id>/tracking', methods=['GET'])
@jwt_required()
def get_order_tracking(order_id):
    """
    Get tracking history for an order
    GET /api/orders/:id/tracking
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    order = DeliveryOrder.query.get_or_404(order_id)
    
    # Check permissions
    if user.role == 'customer' and order.user_id != current_user_id:
        return jsonify({'error': 'Unauthorized access to tracking'}), 403
    
    if user.role == 'courier':
        if order.courier_id != current_user_id:
            return jsonify({'error': 'Unauthorized access to tracking'}), 403
    
    tracking_history = [track.to_dict() for track in order.tracking_updates]
    
    # Get current location (latest tracking point)
    current_location = None
    if tracking_history:
        current_location = tracking_history[0]
    
    return jsonify({
        'order_id': order.id,
        'tracking_number': order.tracking_number,
        'status': order.status.value,
        'current_location': current_location,
        'tracking_history': tracking_history
    }), 200

#  GET PRICE ESTIMATE 
@orders_bp.route('/estimate', methods=['POST'])
@jwt_required(optional=True)
def get_price_estimate():
    """
    Get price estimate for a delivery
    POST /api/orders/estimate
    """
    data = request.get_json()
    
    # Basic validation
    required_fields = ['pickup_lat', 'pickup_lng', 'destination_lat', 'destination_lng', 'weight_kg']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    try:
        # Calculate distance
        maps_service = MapsService()
        distance_result = maps_service.calculate_distance(
            origin=(data['pickup_lat'], data['pickup_lng']),
            destination=(data['destination_lat'], data['destination_lng'])
        )
        
        # Calculate price breakdown
        price_breakdown = PricingService.calculate_price_breakdown(
            distance_km=distance_result['distance_km'],
            weight_kg=data['weight_kg'],
            is_fragile=data.get('fragile', False),
            needs_insurance=data.get('insurance_required', False),
            is_express=data.get('is_express', False),
            is_weekend=data.get('is_weekend', False)
        )
        
        # Calculate estimated delivery time
        estimated_minutes = PricingService.calculate_estimated_delivery_time(
            distance_result['distance_km'], data.get('is_express', False)
        )
        
        return jsonify({
            'estimate': {
                'distance_km': distance_result['distance_km'],
                'duration_minutes': distance_result.get('duration_minutes', 0),
                'price_breakdown': price_breakdown,
                'estimated_delivery_minutes': estimated_minutes,
                'currency': 'KES'
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to calculate estimate: {str(e)}'}), 500