"""
Admin Routes - Flask-RESTful Resources
Handles administrative operations for order management and system statistics
"""
from flask_restful import Resource, reqparse
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta

from extensions import db
from app.models.user import User
from app.models.delivery import DeliveryOrder, OrderStatus
from app.models.order_tracking import OrderTracking
# from app.models.notification import Notification
from app.utils.role_guards import admin_required
from app.services.email_service import EmailService

# GET ALL USERS
class AdminUsersResource(Resource):
    @jwt_required()
    @admin_required
    def get(self):
        """
        Get all users in the system with optional filters
        GET /admin/users?role=courier&is_active=true&limit=20&page=1
        """
        parser = reqparse.RequestParser()
        parser.add_argument('role', type=str, required=False, choices=['courier', 'customer', 'admin'])
        parser.add_argument('is_active', type=str, required=False)
        parser.add_argument('limit', type=int, default=20, required=False)
        parser.add_argument('page', type=int, default=1, required=False)
        
        args = parser.parse_args()
        
        try:
            # Base query
            query = User.query
            
            # Apply filters
            if args['role']:
                query = query.filter_by(role=args['role'])
            
            if args['is_active'] is not None:
                is_active = args['is_active'].lower() == 'true'
                query = query.filter_by(is_active=is_active)
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            users = query.order_by(User.created_at.desc())\
                         .limit(args['limit'])\
                         .offset((args['page'] - 1) * args['limit'])\
                         .all()
            
            # Serialize users (excluding password_hash is handled by serialize_rules)
            users_data = [user.to_dict() for user in users]
            
            return {
                'users': users_data,
                'pagination': {
                    'total': total,
                    'page': args['page'],
                    'limit': args['limit'],
                    'pages': (total + args['limit'] - 1) // args['limit']
                }
            }, 200
        
        except Exception as e:
            return {'error': f'Failed to fetch users: {str(e)}'}, 500


# GET ALL ORDERS
class AdminOrdersResource(Resource):
    @jwt_required()
    @admin_required
    def get(self):
        """
        Get all orders in the system with optional filters
        GET /admin/orders?status=PENDING&limit=20&page=1
        """
        parser = reqparse.RequestParser()
        parser.add_argument('status', type=str, required=False)
        parser.add_argument('courier_id', type=int, required=False)
        parser.add_argument('date_from', type=str, required=False)
        parser.add_argument('date_to', type=str, required=False)
        parser.add_argument('limit', type=int, default=20, required=False)
        parser.add_argument('page', type=int, default=1, required=False)
        
        args = parser.parse_args()
        
        try:
            # Base query
            query = DeliveryOrder.query
            
            # Apply filters
            if args['status']:
                try:
                    status_enum = OrderStatus(args['status'])
                    query = query.filter_by(status=status_enum)
                except ValueError:
                    return {
                        'error': f'Invalid status. Valid options: {[s.value for s in OrderStatus]}'
                    }, 400
            
            if args['courier_id']:
                query = query.filter_by(courier_id=args['courier_id'])
            
            if args['date_from']:
                date_from_obj = datetime.strptime(args['date_from'], '%Y-%m-%d')
                query = query.filter(DeliveryOrder.created_at >= date_from_obj)
            
            if args['date_to']:
                date_to_obj = datetime.strptime(args['date_to'], '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(DeliveryOrder.created_at < date_to_obj)
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            orders = query.order_by(DeliveryOrder.created_at.desc())\
                         .limit(args['limit'])\
                         .offset((args['page'] - 1) * args['limit'])\
                         .all()
            
            # Serialize orders
            orders_data = [order.to_dict() for order in orders]
            
            return {
                'orders': orders_data,
                'pagination': {
                    'total': total,
                    'page': args['page'],
                    'limit': args['limit'],
                    'pages': (total + args['limit'] - 1) // args['limit']
                }
            }, 200
        
        except Exception as e:
            return {'error': f'Failed to fetch orders: {str(e)}'}, 500



# ASSIGN COURIER TO ORDER
assign_parser = reqparse.RequestParser()
assign_parser.add_argument('courier_id', type=int, required=True, help='courier_id is required')

class AdminAssignCourierResource(Resource):
    @jwt_required()
    @admin_required
    def patch(self, order_id):
        """
        Assign a courier to a delivery order
        PATCH /admin/orders/:id/assign
        """
        args = assign_parser.parse_args()
        courier_id = args['courier_id']
        
        try:
            # Get the order
            order = DeliveryOrder.query.get(order_id)
            if not order:
                return {'error': 'Order not found'}, 404
            
            # Check if order can be assigned
            if order.status not in [OrderStatus.PENDING, OrderStatus.ASSIGNED]:
                return {
                    'error': f'Cannot assign courier. Order status is {order.status.value}'
                }, 400
            
            # Get the courier
            courier = User.query.get(courier_id)
            if not courier:
                return {'error': 'Courier not found'}, 404
            
            # Verify user is actually a courier
            if courier.role != 'courier':
                return {
                    'error': f'User {courier.full_name} is not a courier. Role: {courier.role}'
                }, 400
            
            # Check if courier is active
            if not courier.is_active:
                return {
                    'error': f'Courier {courier.full_name} is not active'
                }, 400
            
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
            
            return {
                'message': 'Courier assigned successfully',
                'order': order.to_dict(),
                'courier': {
                    'id': courier.id,
                    'name': courier.full_name,
                    'phone': courier.phone
                }
            }, 200
        
        except Exception as e:
            db.session.rollback()
            return {'error': f'Failed to assign courier: {str(e)}'}, 500



# GET ADMIN DASHBOARD STATISTICS
class AdminStatsResource(Resource):
    @jwt_required()
    @admin_required
    def get(self):
        """
        Get dashboard statistics for admin
        GET /admin/stats?period=today
        """
        parser = reqparse.RequestParser()
        parser.add_argument('period', type=str, default='all', required=False)
        args = parser.parse_args()
        
        try:
            period = args['period']
            
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
            
            # Active couriers
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
            
            # Average delivery time
            avg_delivery_time = None
            if delivered_orders:
                delivery_times = []
                for order in delivered_orders:
                    if order.delivered_at and order.created_at:
                        delta = order.delivered_at - order.created_at
                        delivery_times.append(delta.total_seconds() / 60)
                
                if delivery_times:
                    avg_delivery_time = sum(delivery_times) / len(delivery_times)
            
            # Recent orders (last 5)
            recent_orders = DeliveryOrder.query\
                .order_by(DeliveryOrder.created_at.desc())\
                .limit(5)\
                .all()
            
            return {
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
            }, 200
        
        except Exception as e:
            return {'error': f'Failed to fetch statistics: {str(e)}'}, 500



# UPDATE ORDER STATUS (Admin Override)
status_parser = reqparse.RequestParser()
status_parser.add_argument('status', type=str, required=True, help='status is required')
status_parser.add_argument('notes', type=str, default='Status updated by admin', required=False)

class AdminUpdateOrderStatusResource(Resource):
    @jwt_required()
    @admin_required
    def patch(self, order_id):
        """
        Admin can manually update order status
        PATCH /admin/orders/:id/status
        """
        args = status_parser.parse_args()
        new_status = args['status']
        notes = args['notes']
        
        try:
            # Validate status
            try:
                status_enum = OrderStatus(new_status)
            except ValueError:
                return {
                    'error': f'Invalid status. Valid options: {[s.value for s in OrderStatus]}'
                }, 400
            
            # Get order
            order = DeliveryOrder.query.get(order_id)
            if not order:
                return {'error': 'Order not found'}, 404
            
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
            
            return {
                'message': 'Order status updated successfully',
                'order': order.to_dict()
            }, 200
        
        except Exception as e:
            db.session.rollback()
            return {'error': f'Failed to update status: {str(e)}'}, 500