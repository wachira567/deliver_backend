"""
Courier Routes - Flask-RESTful Resources
Handles courier operations for viewing and updating assigned deliveries
"""
from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

from extensions import db
from app.models.user import User
from app.models.delivery import DeliveryOrder, OrderStatus
from app.models.order_tracking import OrderTracking
from app.models.notification import Notification
from app.utils.role_guards import courier_required
from app.services.email_service import EmailService


# GET ASSIGNED ORDERS
class CourierOrdersResource(Resource):
    @jwt_required()
    @courier_required
    def get(self):
        """
        Get all orders assigned to the current courier
        GET /courier/orders?status=ASSIGNED&limit=20&page=1
        """
        current_user_id = get_jwt_identity()
        
        parser = reqparse.RequestParser()
        parser.add_argument('status', type=str, required=False)
        parser.add_argument('limit', type=int, default=20, required=False)
        parser.add_argument('page', type=int, default=1, required=False)
        args = parser.parse_args()
        
        try:
            courier = User.query.get(current_user_id)
            
            # Base query - only orders assigned to this courier
            query = DeliveryOrder.query.filter_by(courier_id=current_user_id)
            
            # Apply status filter
            if args['status']:
                try:
                    status_enum = OrderStatus(args['status'])
                    query = query.filter_by(status=status_enum)
                except ValueError:
                    return {
                        'error': f'Invalid status. Valid options: {[s.value for s in OrderStatus]}'
                    }, 400
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            orders = query.order_by(DeliveryOrder.created_at.desc())\
                         .limit(args['limit'])\
                         .offset((args['page'] - 1) * args['limit'])\
                         .all()
            
            # Serialize orders
            orders_data = [order.to_dict(include_details=True) for order in orders]
            
            return {
                'orders': orders_data,
                'courier': {
                    'id': courier.id,
                    'name': courier.full_name,
                    'phone': courier.phone
                },
                'pagination': {
                    'total': total,
                    'page': args['page'],
                    'limit': args['limit'],
                    'pages': (total + args['limit'] - 1) // args['limit']
                }
            }, 200
        
        except Exception as e:
            return {'error': f'Failed to fetch orders: {str(e)}'}, 500


# GET SINGLE ORDER DETAILS
class CourierOrderDetailResource(Resource):
    @jwt_required()
    @courier_required
    def get(self, order_id):
        """
        Get detailed information about a specific assigned order
        GET /courier/orders/:id
        """
        current_user_id = get_jwt_identity()
        
        try:
            # Get the order
            order = DeliveryOrder.query.get(order_id)
            if not order:
                return {'error': 'Order not found'}, 404
            
            # Verify courier owns this order
            if order.courier_id != current_user_id:
                return {'error': 'You are not assigned to this order'}, 403
            
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
            
            return {'order': order_data}, 200
        
        except Exception as e:
            return {'error': f'Failed to fetch order: {str(e)}'}, 500



# UPDATE ORDER STATUS
update_status_parser = reqparse.RequestParser()
update_status_parser.add_argument('status', type=str, required=True, help='status is required')
update_status_parser.add_argument('notes', type=str, default='', required=False)

class CourierUpdateStatusResource(Resource):
    @jwt_required()
    @courier_required
    def patch(self, order_id):
        """
        Update the status of an assigned order
        PATCH /courier/orders/:id/status
        """
        current_user_id = get_jwt_identity()
        args = update_status_parser.parse_args()
        
        new_status = args['status']
        notes = args['notes']
        
        try:
            # Validate status
            valid_courier_statuses = [
                OrderStatus.PICKED_UP.value,
                OrderStatus.IN_TRANSIT.value,
                OrderStatus.DELIVERED.value
            ]
            
            if new_status not in valid_courier_statuses:
                return {
                    'error': f'Invalid status. Couriers can only set: {valid_courier_statuses}'
                }, 400
            
            try:
                status_enum = OrderStatus(new_status)
            except ValueError:
                return {'error': 'Invalid status value'}, 400
            
            # Get the order
            order = DeliveryOrder.query.get(order_id)
            if not order:
                return {'error': 'Order not found'}, 404
            
            # Verify courier owns this order
            if order.courier_id != current_user_id:
                return {'error': 'You are not assigned to this order'}, 403
            
            # Validate status transition
            current_status = order.status
            
            valid_transitions = {
                OrderStatus.ASSIGNED: [OrderStatus.PICKED_UP],
                OrderStatus.PICKED_UP: [OrderStatus.IN_TRANSIT],
                OrderStatus.IN_TRANSIT: [OrderStatus.DELIVERED],
            }
            
            if current_status not in valid_transitions:
                return {
                    'error': f'Cannot update status from {current_status.value}'
                }, 400
            
            if status_enum not in valid_transitions[current_status]:
                return {
                    'error': f'Invalid transition from {current_status.value} to {new_status}. '
                            f'Valid next status: {[s.value for s in valid_transitions[current_status]]}'
                }, 400
            
            # Update order status
            old_status = order.status
            order.update_status(status_enum)
            
            # If delivered, set timestamp
            if status_enum == OrderStatus.DELIVERED:
                order.actual_delivery_time = datetime.utcnow()
            
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
            
            # Create notification
            notification = Notification(
                user_id=order.user_id,
                order_id=order.id,
                type='STATUS_UPDATE',
                message=f'Your order #{order.tracking_number} is now {new_status}'
            )
            db.session.add(notification)
            
            db.session.commit()
            
            # Send email notification
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
            
            return {
                'message': f'Order status updated to {new_status}',
                'order': order.to_dict(include_details=True)
            }, 200
        
        except Exception as e:
            db.session.rollback()
            return {'error': f'Failed to update status: {str(e)}'}, 500



# UPDATE CURRENT LOCATION
location_parser = reqparse.RequestParser()
location_parser.add_argument('latitude', type=float, required=True, help='latitude is required')
location_parser.add_argument('longitude', type=float, required=True, help='longitude is required')
location_parser.add_argument('location_description', type=str, default='Location updated', required=False)

class CourierUpdateLocationResource(Resource):
    @jwt_required()
    @courier_required
    def patch(self, order_id):
        """
        Update the courier's current location for an order
        PATCH /courier/orders/:id/location
        """
        current_user_id = get_jwt_identity()
        args = location_parser.parse_args()
        
        latitude = args['latitude']
        longitude = args['longitude']
        location_description = args['location_description']
        
        try:
            # Validate coordinates
            if not (-90 <= latitude <= 90):
                return {'error': 'Invalid latitude. Must be between -90 and 90'}, 400
            if not (-180 <= longitude <= 180):
                return {'error': 'Invalid longitude. Must be between -180 and 180'}, 400
            
            # Get the order
            order = DeliveryOrder.query.get(order_id)
            if not order:
                return {'error': 'Order not found'}, 404
            
            # Verify courier owns this order
            if order.courier_id != current_user_id:
                return {'error': 'You are not assigned to this order'}, 403
            
            # Only allow location updates for active deliveries
            if order.status not in [OrderStatus.PICKED_UP, OrderStatus.IN_TRANSIT]:
                return {
                    'error': f'Cannot update location for order with status {order.status.value}'
                }, 400
            
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
            
            return {
                'message': 'Location updated successfully',
                'current_location': {
                    'latitude': float(order.current_latitude),
                    'longitude': float(order.current_longitude),
                    'updated_at': tracking.created_at.isoformat()
                }
            }, 200
        
        except Exception as e:
            db.session.rollback()
            return {'error': f'Failed to update location: {str(e)}'}, 500


# GET COURIER STATISTICS
class CourierStatsResource(Resource):
    @jwt_required()
    @courier_required
    def get(self):
        """
        Get statistics for the current courier
        GET /courier/stats
        """
        current_user_id = get_jwt_identity()
        
        try:
            # Total deliveries
            total_deliveries = DeliveryOrder.query.filter_by(
                courier_id=current_user_id
            ).count()
            
            # Completed deliveries
            completed_deliveries = DeliveryOrder.query.filter_by(
                courier_id=current_user_id,
                status=OrderStatus.DELIVERED
            ).count()
            
            # Active deliveries
            active_deliveries = DeliveryOrder.query.filter(
                DeliveryOrder.courier_id == current_user_id,
                DeliveryOrder.status.in_([
                    OrderStatus.ASSIGNED,
                    OrderStatus.PICKED_UP,
                    OrderStatus.IN_TRANSIT
                ])
            ).count()
            
            # Today's deliveries
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            todays_deliveries = DeliveryOrder.query.filter(
                DeliveryOrder.courier_id == current_user_id,
                DeliveryOrder.created_at >= today_start
            ).count()
            
            # Success rate
            success_rate = 0
            if total_deliveries > 0:
                success_rate = (completed_deliveries / total_deliveries) * 100
            
            return {
                'summary': {
                    'total_deliveries': total_deliveries,
                    'completed_deliveries': completed_deliveries,
                    'active_deliveries': active_deliveries,
                    'todays_deliveries': todays_deliveries,
                    'success_rate': round(success_rate, 2)
                }
            }, 200
        
        except Exception as e:
            return {'error': f'Failed to fetch statistics: {str(e)}'}, 500