from datetime import datetime
from sqlalchemy import Enum
from app import db
from app.models.delivery import OrderStatus

class OrderTracking(db.Model):
    """Order tracking/location history model"""
    __tablename__ = 'order_tracking'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('delivery_orders.id'), nullable=False)
    
    # Location data
    latitude = db.Column(db.Numeric(10, 8))
    longitude = db.Column(db.Numeric(11, 8))
    location_description = db.Column(db.String(200))
    address = db.Column(db.Text)
    
    # Status and tracking info
    status = db.Column(Enum(OrderStatus), nullable=False)
    speed_kmh = db.Column(db.Numeric(5, 2))  # Courier speed if available
    battery_level = db.Column(db.Integer)    # Courier device battery
    accuracy_meters = db.Column(db.Numeric(5, 2))  # GPS accuracy
    
    # Additional info
    notes = db.Column(db.Text)
    photo_url = db.Column(db.String(500))  # Optional photo proof
    courier_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    courier = db.relationship('User', backref='tracking_updates', lazy=True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.updated_at:
            self.updated_at = datetime.utcnow()
    
    def get_google_maps_url(self):
        """Generate Google Maps URL for this location"""
        if self.latitude and self.longitude:
            return f"https://www.google.com/maps?q={self.latitude},{self.longitude}"
        return None
    
    def get_status_message(self):
        """Generate human-readable status message"""
        status_messages = {
            OrderStatus.PENDING: "Order created, waiting for courier",
            OrderStatus.PICKED_UP: "Parcel picked up by courier",
            OrderStatus.IN_TRANSIT: "Parcel is on the way",
            OrderStatus.DELIVERED: "Parcel delivered successfully",
            OrderStatus.CANCELLED: "Order cancelled"
        }
        return status_messages.get(self.status, "Status update")
    
    def to_dict(self):
        """Convert tracking record to dictionary"""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'location': {
                'latitude': float(self.latitude) if self.latitude else None,
                'longitude': float(self.longitude) if self.longitude else None,
                'description': self.location_description,
                'address': self.address,
                'google_maps_url': self.get_google_maps_url()
            },
            'status': self.status.value if self.status else None,
            'status_message': self.get_status_message(),
            'metadata': {
                'speed_kmh': float(self.speed_kmh) if self.speed_kmh else None,
                'battery_level': self.battery_level,
                'accuracy_meters': float(self.accuracy_meters) if self.accuracy_meters else None,
                'photo_url': self.photo_url,
                'courier_id': self.courier_id
            },
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'timestamp': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def create_from_status_change(cls, order, new_status, courier_id=None, notes=None):
        """Create tracking record from status change"""
        return cls(
            order_id=order.id,
            latitude=order.pickup_lat if new_status == OrderStatus.PENDING else None,
            longitude=order.pickup_lng if new_status == OrderStatus.PENDING else None,
            status=new_status,
            location_description=cls._get_location_description(new_status),
            courier_id=courier_id,
            notes=notes or f"Status changed to {new_status.value}"
        )
    
    @staticmethod
    def _get_location_description(status):
        """Get default location description for status"""
        descriptions = {
            OrderStatus.PENDING: "Pickup location",
            OrderStatus.PICKED_UP: "Picked up from customer",
            OrderStatus.IN_TRANSIT: "On the way to destination",
            OrderStatus.DELIVERED: "Delivered to destination",
            OrderStatus.CANCELLED: "Order cancelled location"
        }
        return descriptions.get(status, "Location update")