from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Enum
from app import db
from decimal import Decimal

class PaymentMethod(PyEnum):
    MPESA = 'MPESA'
    CARD = 'CARD'
    CASH = 'CASH'
    WALLET = 'WALLET'

class PaymentStatus(PyEnum):
    PENDING = 'PENDING'
    PROCESSING = 'PROCESSING'
    PAID = 'PAID'
    FAILED = 'FAILED'
    REFUNDED = 'REFUNDED'
    CANCELLED = 'CANCELLED'

class Payment(db.Model):
    """Payment model linked to delivery orders"""
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('delivery_orders.id'), unique=True, nullable=False)
    
    # Payment details
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='KES')
    payment_method = db.Column(Enum(PaymentMethod))
    payment_status = db.Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    
    # Transaction references
    transaction_reference = db.Column(db.String(100), unique=True)
    merchant_request_id = db.Column(db.String(100))  # For M-Pesa
    checkout_request_id = db.Column(db.String(100))  # For M-Pesa
    mpesa_receipt_number = db.Column(db.String(100))
    
    # Card payment details (if applicable)
    card_last_four = db.Column(db.String(4))
    card_brand = db.Column(db.String(20))
    card_expiry_month = db.Column(db.Integer)
    card_expiry_year = db.Column(db.Integer)
    
    # Customer payment info
    customer_phone = db.Column(db.String(20))  # For M-Pesa
    customer_email = db.Column(db.String(120))
    
    # Timestamps
    initiated_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime)
    failed_at = db.Column(db.DateTime)
    refunded_at = db.Column(db.DateTime)
    
    # Additional info
    failure_reason = db.Column(db.Text)
    refund_reason = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    
    # Gateway metadata (avoid reserved name)
    gateway_metadata = db.Column(db.JSON)  # For additional payment gateway data
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.transaction_reference:
            self.transaction_reference = self.generate_transaction_reference()
    
    def generate_transaction_reference(self):
        """Generate unique transaction reference"""
        timestamp = datetime.utcnow().strftime('%y%m%d%H%M%S')
        import random
        random_part = f"{random.randint(1000, 9999)}"
        return f"PAY{timestamp}{random_part}"
    
    def is_paid(self):
        """Check if payment is completed"""
        return self.payment_status == PaymentStatus.PAID
    
    def can_refund(self):
        """Check if payment can be refunded"""
        return self.payment_status == PaymentStatus.PAID and self.paid_at
    
    def mark_as_paid(self, receipt_number=None, **kwargs):
        """Mark payment as paid"""
        self.payment_status = PaymentStatus.PAID
        self.paid_at = datetime.utcnow()
        
        if receipt_number:
            self.mpesa_receipt_number = receipt_number
        
        # Update any additional kwargs
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def mark_as_failed(self, reason=None):
        """Mark payment as failed"""
        self.payment_status = PaymentStatus.FAILED
        self.failed_at = datetime.utcnow()
        if reason:
            self.failure_reason = reason
    
    def initiate_refund(self, reason=None):
        """Initiate refund process"""
        if not self.can_refund():
            raise ValueError("Payment cannot be refunded")
        
        self.payment_status = PaymentStatus.REFUNDED
        self.refunded_at = datetime.utcnow()
        if reason:
            self.refund_reason = reason
    
    def get_payment_gateway_data(self):
        """Get data for payment gateway based on method"""
        if self.payment_method == PaymentMethod.MPESA:
            return {
                'BusinessShortCode': '174379',  # Sandbox code
                'Password': self._generate_mpesa_password(),
                'Timestamp': datetime.utcnow().strftime('%Y%m%d%H%M%S'),
                'TransactionType': 'CustomerPayBillOnline',
                'Amount': float(self.amount),
                'PartyA': self.customer_phone,
                'PartyB': '174379',
                'PhoneNumber': self.customer_phone,
                'CallBackURL': 'https://yourdomain.com/api/payments/mpesa-callback',
                'AccountReference': self.transaction_reference,
                'TransactionDesc': f'Delivery Order #{self.order_id}'
            }
        elif self.payment_method == PaymentMethod.CARD:
            return {
                'amount': float(self.amount),
                'currency': self.currency,
                'reference': self.transaction_reference,
                'email': self.customer_email,
                'metadata': {
                    'order_id': self.order_id
                }
            }
        return {}
    
    def _generate_mpesa_password(self):
        """Generate M-Pesa API password"""
        import base64
        from datetime import datetime
        
        business_short_code = "174379"  # Sandbox
        passkey = "your_mpesa_passkey"  # From M-Pesa dashboard
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        data_to_encode = business_short_code + passkey + timestamp
        encoded = base64.b64encode(data_to_encode.encode()).decode()
        return encoded
    
    def to_dict(self, include_sensitive=False):
        """Convert payment to dictionary"""
        data = {
            'id': self.id,
            'order_id': self.order_id,
            'amount': float(self.amount) if self.amount else None,
            'currency': self.currency,
            'payment_method': self.payment_method.value if self.payment_method else None,
            'payment_status': self.payment_status.value if self.payment_status else None,
            'transaction_reference': self.transaction_reference,
            'initiated_at': self.initiated_at.isoformat() if self.initiated_at else None,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
            'is_paid': self.is_paid(),
            'can_refund': self.can_refund()
        }
        
        if include_sensitive and self.payment_method == PaymentMethod.MPESA:
            data.update({
                'mpesa_receipt_number': self.mpesa_receipt_number,
                'customer_phone': self.customer_phone,
                'merchant_request_id': self.merchant_request_id,
                'checkout_request_id': self.checkout_request_id
            })
        
        return data
    
    @classmethod
    def create_for_order(cls, order, payment_method='MPESA', customer_phone=None, customer_email=None):
        """Create payment record for an order"""
        return cls(
            order_id=order.id,
            amount=order.total_price,
            currency=order.currency,
            payment_method=PaymentMethod(payment_method),
            customer_phone=customer_phone,
            customer_email=customer_email or order.customer.email,
            payment_status=PaymentStatus.PENDING
        )