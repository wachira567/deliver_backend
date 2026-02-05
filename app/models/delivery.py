from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Enum
from app import db
from decimal import Decimal

class OrderStatus(PyEnum):
    PENDING = 'PENDING'
    PICKED_UP = 'PICKED_UP'
    IN_TRANSIT = 'IN_TRANSIT'
    DELIVERED = 'DELIVERED'
    CANCELLED = 'CANCELLED'

class WeightCategory(PyEnum):
    SMALL = 'SMALL'      # < 5kg
    MEDIUM = 'MEDIUM'    # 5-20kg
    LARGE = 'LARGE'      # 20-50kg
    XLARGE = 'XLARGE'    # > 50kg

class DeliveryOrder(db.Model):
    """Main delivery order model"""
    __tablename__ = 'delivery_orders'
    
    id = db.Column(db.Integer, primary_key=True)
    tracking_number = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    courier_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Location data
    pickup_lat = db.Column(db.Numeric(10, 8), nullable=False)
    pickup_lng = db.Column(db.Numeric(11, 8), nullable=False)
    pickup_address = db.Column(db.Text, nullable=False)
    pickup_phone = db.Column(db.String(20))
    
    destination_lat = db.Column(db.Numeric(10, 8), nullable=False)
    destination_lng = db.Column(db.Numeric(11, 8), nullable=False)
    destination_address = db.Column(db.Text, nullable=False)
    destination_phone = db.Column(db.String(20))
    
    # Parcel details
    weight_kg = db.Column(db.Numeric(6, 2), nullable=False)
    weight_category = db.Column(Enum(WeightCategory), nullable=False)
    parcel_description = db.Column(db.Text)
    parcel_dimensions = db.Column(db.String(50))  # "LxWxH in cm"
    fragile = db.Column(db.Boolean, default=False)
    insurance_required = db.Column(db.Boolean, default=False)
    is_express = db.Column(db.Boolean, default=False)
    is_weekend = db.Column(db.Boolean, default=False)
    
    # Pricing breakdown
    distance_km = db.Column(db.Numeric(8, 2))
    base_price = db.Column(db.Numeric(10, 2))
    distance_price = db.Column(db.Numeric(10, 2))
    weight_price = db.Column(db.Numeric(10, 2))
    extra_charges = db.Column(db.Numeric(10, 2), default=0)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='KES')
    
    # Status and timestamps
    status = db.Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    estimated_delivery_time = db.Column(db.DateTime)
    actual_delivery_time = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tracking_updates = db.relationship('OrderTracking', backref='order', lazy=True, 
                                      order_by='desc(OrderTracking.updated_at)')
    payment = db.relationship('Payment', backref='order', uselist=False, lazy=True)
    notifications = db.relationship('Notification', backref='order', lazy=True)
    customer = db.relationship('User', foreign_keys=[user_id], backref='orders')
    # Couriers are represented by users with role='courier'
    courier = db.relationship('User', foreign_keys=[courier_id], backref='assigned_orders')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.tracking_number:
            self.tracking_number = self.generate_tracking_number()
    
    def generate_tracking_number(self):
        """Generate unique tracking number"""
        timestamp = datetime.utcnow().strftime('%y%m%d%H%M')
        import random
        random_part = f"{random.randint(1000, 9999)}"
        return f"DLV{timestamp}{random_part}"
    
    def can_update_destination(self):
        """Check if destination can be updated (only before pickup)"""
        return self.status in [OrderStatus.PENDING]
    
    def can_cancel(self):
        """Check if order can be cancelled"""
        return self.status in [OrderStatus.PENDING, OrderStatus.PICKED_UP]
    
    def update_status(self, new_status, courier_id=None):
        """Update order status with validation"""
        status_flow = {
            OrderStatus.PENDING: [OrderStatus.PICKED_UP, OrderStatus.CANCELLED],
            OrderStatus.PICKED_UP: [OrderStatus.IN_TRANSIT, OrderStatus.CANCELLED],
            OrderStatus.IN_TRANSIT: [OrderStatus.DELIVERED],
            OrderStatus.DELIVERED: [],
            OrderStatus.CANCELLED: []
        }
        
        if new_status not in status_flow.get(self.status, []):
            raise ValueError(f"Cannot change status from {self.status.value} to {new_status.value}")
        
        self.status = new_status
        self.updated_at = datetime.utcnow()
        
        if new_status == OrderStatus.DELIVERED:
            self.actual_delivery_time = datetime.utcnow()
        elif new_status == OrderStatus.PICKED_UP and courier_id:
            self.courier_id = courier_id
    
    def get_price_breakdown(self):
        """Return price breakdown as dictionary"""
        return {
            'base_price': float(self.base_price) if self.base_price else 0,
            'distance_price': float(self.distance_price) if self.distance_price else 0,
            'weight_price': float(self.weight_price) if self.weight_price else 0,
            'extra_charges': float(self.extra_charges) if self.extra_charges else 0,
            'total': float(self.total_price) if self.total_price else 0,
            'currency': self.currency
        }
    
    def to_dict(self, include_details=False):
        """Convert order to dictionary"""
        data = {
            'id': self.id,
            'tracking_number': self.tracking_number,
            'status': self.status.value if self.status else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'pickup_address': self.pickup_address,
            'destination_address': self.destination_address,
            'weight_kg': float(self.weight_kg) if self.weight_kg else None,
            'weight_category': self.weight_category.value if self.weight_category else None,
            'distance_km': float(self.distance_km) if self.distance_km else None,
            'total_price': float(self.total_price) if self.total_price else None,
            'estimated_delivery_time': self.estimated_delivery_time.isoformat() if self.estimated_delivery_time else None,
            'actual_delivery_time': self.actual_delivery_time.isoformat() if self.actual_delivery_time else None,
            'customer_id': self.user_id,
            'courier_id': self.courier_id
        }
        
        if include_details:
            data.update({
                'price_breakdown': self.get_price_breakdown(),
                'parcel_details': {
                    'description': self.parcel_description,
                    'dimensions': self.parcel_dimensions,
                    'fragile': self.fragile,
                    'insurance_required': self.insurance_required,
                    'is_express': self.is_express,
                    'is_weekend': self.is_weekend
                },
                'contact_info': {
                    'pickup_phone': self.pickup_phone,
                    'destination_phone': self.destination_phone
                },
                'coordinates': {
                    'pickup': {'lat': float(self.pickup_lat), 'lng': float(self.pickup_lng)},
                    'destination': {'lat': float(self.destination_lat), 'lng': float(self.destination_lng)}
                }
            })
        
        return data