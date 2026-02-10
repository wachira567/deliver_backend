# app/models/notification.py
"""
Notification Model
Stores in-app notifications for users about order updates
"""
from extensions import db
from datetime import datetime
from sqlalchemy_serializer import SerializerMixin


class Notification(db.Model, SerializerMixin):
    __tablename__ = 'notifications'

    # Primary Key
    id = db.Column(db.Integer, primary_key=True)

    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable = False)
    order_id = db.Column(db.Integer, db.ForeignKey('delivery_orders.id'), nullable=True)

    # Notis data
    type = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable= False)
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)

    # Timestamps
    created_at = db.Column(db.DateTime, default = datetime.utcnow)


    user = db.relationship('User', backref='notifications')


    serialize_rules = ('-user.notifications',)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'order_id': self.order_id,
            'type': self.type,
            'message': self.message,
            'is_read': self.is_read,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'created_at': self.created_at.isoformat()
        }
        
