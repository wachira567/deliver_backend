"""
Payment Routes for Deliveroo
Handles M-Pesa STK Push initiation and callbacks

Place this file in: app/routes/payments.py
"""
from flask import Blueprint, request, jsonify
from app.services.payment_service import get_mpesa_service
from app.models.delivery import DeliveryOrder
from app.models.payment import Payment, PaymentMethod, PaymentStatus
from app import db
import logging

logger = logging.getLogger(__name__)

payments_bp = Blueprint('payments', __name__, url_prefix='/api/payments')


@payments_bp.route('/initiate', methods=['POST'])
def initiate_payment():
    """
    Initiate M-Pesa STK Push for an order
    
    Expected JSON:
    {
        "order_id": 123,
        "phone_number": "0712345678"
    }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    order_id = data.get('order_id')
    phone_number = data.get('phone_number')
    
    if not order_id:
        return jsonify({'error': 'Order ID is required'}), 400
    if not phone_number:
        return jsonify({'error': 'Phone number is required'}), 400
    
    # Get the order
    order = DeliveryOrder.query.get(order_id)
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
    # Check if payment already exists and is completed
    existing_payment = Payment.query.filter_by(order_id=order_id).first()
    if existing_payment and existing_payment.is_paid():
        return jsonify({'error': 'Order already paid'}), 400
    
    # Create or update payment record
    if existing_payment:
        payment = existing_payment
        payment.payment_status = PaymentStatus.PROCESSING
        payment.customer_phone = phone_number
    else:
        payment = Payment.create_for_order(
            order=order,
            payment_method='MPESA',
            customer_phone=phone_number
        )
        payment.payment_status = PaymentStatus.PROCESSING
        db.session.add(payment)
    
    # Save to get payment ID before STK push
    db.session.commit()
    payment_id = payment.id
    
    # Close session to prevent holding connection
    db.session.remove()
    
    try:
        # Get M-Pesa service instance
        mpesa_service = get_mpesa_service()
        
        # Initiate STK Push
        result = mpesa_service.initiate_stk_push(
            phone_number=phone_number,
            amount=int(order.total_price),
            order_id=order_id,
            description=f"Deliveroo Order {order.tracking_number}"
        )
    except Exception as e:
         result = {'success': False, 'error': str(e)}

    # Re-fetch payment in new transaction
    payment = Payment.query.get(payment_id)
    if not payment:
         return jsonify({'error': 'Payment record lost error'}), 500
    
    if result['success']:
        # Store M-Pesa request IDs
        payment.checkout_request_id = result['checkout_request_id']
        payment.merchant_request_id = result['merchant_request_id']
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': result['message'],
            'payment_id': payment.id,
            'transaction_reference': payment.transaction_reference,
            'checkout_request_id': result['checkout_request_id'],
            'amount': float(order.total_price),
            'currency': order.currency
        }), 200
    else:
        # Mark payment as failed
        payment.mark_as_failed(reason=result.get('error', 'STK push failed'))
        db.session.commit()
        
        return jsonify({
            'success': False,
            'error': result.get('error', 'Payment initiation failed')
        }), 400


@payments_bp.route('/callback', methods=['POST'])
def mpesa_callback():
    """
    M-Pesa callback endpoint
    
    This endpoint receives payment confirmation from Safaricom
    Must be publicly accessible (use ngrok for local testing)
    """
    callback_data = request.get_json()
    
    logger.info("=" * 50)
    logger.info("M-PESA CALLBACK RECEIVED")
    logger.info(callback_data)
    logger.info("=" * 50)
    
    # Get M-Pesa service instance
    mpesa_service = get_mpesa_service()
    
    # Parse the callback
    result = mpesa_service.parse_callback(callback_data)
    
    # Find payment by checkout_request_id
    checkout_id = result.get('checkout_request_id')
    payment = Payment.query.filter_by(checkout_request_id=checkout_id).first()
    
    if not payment:
        logger.warning(f"Payment not found for checkout_id: {checkout_id}")
        return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200
    
    if result['success']:
        # Payment successful
        payment.mark_as_paid(
            receipt_number=result.get('receipt_number'),
            payment_metadata={
                'mpesa_amount': result.get('amount'),
                'mpesa_phone': result.get('phone_number'),
                'mpesa_transaction_date': result.get('transaction_date')
            }
        )
        
        logger.info(f"✅ Payment #{payment.id} successful! Receipt: {result.get('receipt_number')}")
        logger.info(f"   Order #{payment.order_id} is now paid")
        
        # TODO: Trigger email notification to customer
        # email_service.send_payment_confirmation(payment)
        
    else:
        # Payment failed or cancelled
        payment.mark_as_failed(reason=result.get('result_description', 'Payment failed'))
        logger.warning(f"❌ Payment #{payment.id} failed: {result.get('result_description')}")
    
    db.session.commit()
    
    # Always respond with success to M-Pesa
    return jsonify({
        "ResultCode": 0,
        "ResultDesc": "Accepted"
    }), 200


@payments_bp.route('/status/<int:order_id>', methods=['GET'])
def get_payment_status(order_id):
    """
    Get payment status for an order
    
    GET /api/payments/status/<order_id>
    """
    payment = Payment.query.filter_by(order_id=order_id).first()
    
    if not payment:
        return jsonify({'error': 'Payment not found for this order'}), 404
    
    return jsonify({
        'success': True,
        'payment': payment.to_dict(include_sensitive=True)
    }), 200


@payments_bp.route('/query/<checkout_request_id>', methods=['GET'])
def query_mpesa_status(checkout_request_id):
    """
    Query M-Pesa for transaction status
    
    GET /api/payments/query/<checkout_request_id>
    
    Use this to check if user completed payment on their phone
    """
    # Check DB first
    payment = Payment.query.filter_by(checkout_request_id=checkout_request_id).first()
    
    if payment and payment.is_paid():
        return jsonify({
            'success': True,
            'status': 'completed',
            'payment': payment.to_dict()
        }), 200
    
    # Only need payment ID for update later
    if not payment:
        return jsonify({'error': 'Payment not found'}), 404
    payment_id = payment.id
        
    # Remove session
    db.session.remove()
    
    # Query M-Pesa directly
    try:
        mpesa_service = get_mpesa_service()
        result = mpesa_service.query_stk_status(checkout_request_id)
    except Exception as e:
        result = {'success': False, 'status': 'error', 'error': str(e)}
    
    # Re-fetch payment
    payment = Payment.query.get(payment_id)
    
    if result.get('status') == 'completed' and payment:
        # Update our records if M-Pesa says it's complete
        payment.payment_status = PaymentStatus.PAID
        payment.paid_at = db.func.now()
        db.session.commit()
    
    return jsonify({
        'success': True,
        'mpesa_status': result.get('status'),
        'result_description': result.get('result_description'),
        'payment': payment.to_dict() if payment else None
    }), 200


@payments_bp.route('/test', methods=['POST'])
def test_stk_push():
    """
    Test endpoint for STK Push (development only)
    
    POST /api/payments/test
    {
        "phone_number": "254712345678",
        "amount": 1
    }
    
    This bypasses order creation for quick testing
    """
    data = request.get_json()
    
    phone = data.get('phone_number')
    amount = data.get('amount', 1)
    
    if not phone:
        return jsonify({'error': 'Phone number required'}), 400
    
    # Get M-Pesa service instance
    mpesa_service = get_mpesa_service()
    
    result = mpesa_service.initiate_stk_push(
        phone_number=phone,
        amount=int(amount),
        order_id=0,
        description="Deliveroo Test Payment"
    )
    
    return jsonify(result), 200 if result['success'] else 400


@payments_bp.route('/orders/<int:order_id>/pay', methods=['POST'])
def pay_for_order(order_id):
    """
    Pay for an order via M-Pesa STK Push

    POST /api/payments/orders/<order_id>/pay
    {
        "phone_number": "254712345678"
    }
    """
    data = request.get_json() or {}
    phone_number = data.get('phone_number')

    if not phone_number:
        return jsonify({'error': 'Phone number is required'}), 400

    order = DeliveryOrder.query.get(order_id)
    if not order:
        return jsonify({'error': 'Order not found'}), 404

    existing_payment = Payment.query.filter_by(order_id=order_id).first()
    if existing_payment and existing_payment.is_paid():
        return jsonify({'error': 'Order already paid'}), 400

    if existing_payment:
        payment = existing_payment
        payment.payment_status = PaymentStatus.PROCESSING
        payment.customer_phone = phone_number
    else:
        payment = Payment.create_for_order(
            order=order,
            payment_method='MPESA',
            customer_phone=phone_number
        )
        payment.payment_status = PaymentStatus.PROCESSING
        db.session.add(payment)

    db.session.commit()
    
    # Close session to prevent holding connection during long external call
    db.session.remove()

    try:
        mpesa_service = get_mpesa_service()
        result = mpesa_service.initiate_stk_push(
            phone_number=phone_number,
            amount=int(order.total_price),
            order_id=order_id,
            description=f"Deliveroo Order {order.tracking_number}"
        )
    except Exception as e:
        # Fallback if the service call crashes completely
        result = {'success': False, 'error': str(e)}

    # Re-fetch payment in a new session/transaction
    payment = Payment.query.get(payment.id)
    if not payment:
         # Should not happen if committed above
         return jsonify({'error': 'Payment record lost'}), 500

    if result['success']:
        payment.checkout_request_id = result['checkout_request_id']
        payment.merchant_request_id = result['merchant_request_id']
        db.session.commit()

        return jsonify({
            'success': True,
            'message': result['message'],
            'payment_id': payment.id,
            'transaction_reference': payment.transaction_reference,
            'checkout_request_id': result['checkout_request_id'],
            'amount': float(order.total_price),
            'currency': order.currency
        }), 200
    else:
        payment.mark_as_failed(reason=result.get('error', 'STK push failed'))
        db.session.commit()

        return jsonify({
            'success': False,
            'error': result.get('error', 'Payment initiation failed')
        }), 400


@payments_bp.route('/simulate-callback', methods=['POST'])
def simulate_callback():
    """
    Simulate M-Pesa callback (Development Only)
    
    POST /api/payments/simulate-callback
    {
        "checkout_request_id": "ws_CO_...",
        "status": "success" | "failed",
        "amount": 100,
        "phone": "2547...",
        "receipt_number": "QWE..."
    }
    """
    data = request.get_json()
    checkout_id = data.get('checkout_request_id')
    status = data.get('status', 'success')
    
    if not checkout_id:
        return jsonify({'error': 'checkout_request_id is required'}), 400
        
    payment = Payment.query.filter_by(checkout_request_id=checkout_id).first()
    if not payment:
        return jsonify({'error': 'Payment not found'}), 404
        
    if status == 'success':
        payment.mark_as_paid(
            receipt_number=data.get('receipt_number', 'SIMULATED123'),
            payment_metadata={
                'mpesa_amount': data.get('amount', payment.amount),
                'mpesa_phone': data.get('phone', payment.customer_phone),
                'mpesa_transaction_date': str(db.func.now())
            }
        )
        logger.info(f"SIMULATED: Payment #{payment.id} marked as PAID")
    else:
        payment.mark_as_failed(reason="Simulated Failure")
        logger.info(f"SIMULATED: Payment #{payment.id} marked as FAILED")
        
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Payment {status} simulated',
        'payment': payment.to_dict()
    })