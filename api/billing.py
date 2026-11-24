"""Razorpay billing: create subscriptions and increment usage quantity."""
import os
import razorpay
from dotenv import load_dotenv

load_dotenv()

client = razorpay.Client(auth=(
    os.getenv('RAZORPAY_KEY_ID'),
    os.getenv('RAZORPAY_KEY_SECRET')
))

PLAN_ID = os.getenv('RAZORPAY_PLAN_ID')

def create_subscription(customer_id: str) -> dict:
    """Create a Razorpay subscription for a new customer.
    Returns the subscription object (contains 'id' and 'short_url').
    """
    try:
        subscription = client.subscription.create({
            'plan_id': PLAN_ID,
            'customer_notify': 1,
            'quantity': 1,
            'total_count': 2,  # 12 billing cycles = 1 year
            'notes': {'customer_id': customer_id}
        })
        return {'success': True, 'subscription': subscription}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def increment_usage(subscription_id: str, current_quantity: int) -> dict:
    """Increase subscription quantity by 1 (one more ticket resolved).
    Razorpay charges plan_amount * quantity at the next billing cycle.
    """
    try:
        updated = client.subscription.update(subscription_id, {
            'quantity': current_quantity + 1
        })
        return {'success': True, 'subscription': updated}
    except Exception as e:
        return {'success': False, 'error': str(e)}
