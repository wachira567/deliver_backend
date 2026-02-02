"""
Email Notification Service
Sends emails for order status updates and notifications
"""
from flask_mail import Message, Mail

mail = Mail()

class EmailService:
    
    @staticmethod
    def send_status_update(user_email, order_id, status):
        """
        Send email when order status changes
        
        Args:
            user_email (str): Customer's email
            order_id (int): Order ID
            status (str): New order status
        """
        try:
            msg = Message(
                subject=f'Deliveroo - Order #{order_id} Update',
                recipients=[user_email]
            )
            
            msg.body = f"""
Hello,

Your delivery order #{order_id} has been updated.

New Status: {status}

Track your order at: https://deliveroo.com/track/{order_id}

Thank you for using Deliveroo!

Best regards,
Deliveroo Team
            """
            
            mail.send(msg)
            return {'status': 'success', 'message': 'Email sent'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    @staticmethod
    def send_courier_assigned(user_email, order_id, courier_name, courier_phone):
        """
        Send email when courier is assigned
        
        Args:
            user_email (str): Customer's email
            order_id (int): Order ID
            courier_name (str): Courier's name
            courier_phone (str): Courier's phone number
        """
        try:
            msg = Message(
                subject=f'Deliveroo - Courier Assigned to Order #{order_id}',
                recipients=[user_email]
            )
            
            msg.body = f"""
Hello,

Great news! A courier has been assigned to your order #{order_id}.

Courier Details:
Name: {courier_name}
Phone: {courier_phone}

You will receive updates as your parcel moves through the delivery process.

Track your order at: https://deliveroo.com/track/{order_id}

Thank you for using Deliveroo!

Best regards,
Deliveroo Team
            """
            
            mail.send(msg)
            return {'status': 'success', 'message': 'Email sent'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    @staticmethod
    def send_delivery_complete(user_email, order_id):
        """
        Send email when delivery is completed
        
        Args:
            user_email (str): Customer's email
            order_id (int): Order ID
        """
        try:
            msg = Message(
                subject=f'Deliveroo - Order #{order_id} Delivered!',
                recipients=[user_email]
            )
            
            msg.body = f"""
Hello,

Your order #{order_id} has been successfully delivered!

We hope you're satisfied with our service.

Please rate your delivery experience: https://deliveroo.com/rate/{order_id}

Thank you for using Deliveroo!

Best regards,
Deliveroo Team
            """
            
            mail.send(msg)
            return {'status': 'success', 'message': 'Email sent'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}