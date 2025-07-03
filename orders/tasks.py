from celery import shared_task
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse

from .models import Order, Cart
from core.utils import send_email, send_bulk_email

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': settings.EMAIL_TASK_MAX_RETRIES}
)
def send_order_confirmation_email(self, order_id):
    """Send order confirmation email to customer."""
    try:
        order = Order.objects.get(id=order_id)
        context = {
            'order': order,
            'order_number': order.order_number,
            'order_date': order.created_at.strftime('%B %d, %Y'),
            'order_total': str(order.total_amount),
            'shipping_address': order.shipping_address,
            'billing_address': order.billing_address,
            'items': [
                {
                    'name': item.product.name,
                    'quantity': item.quantity,
                    'price': str(item.price),
                    'total': str(item.get_total())
                }
                for item in order.items.all()
            ],
            'site_url': settings.SITE_URL,
            'logo_url': f"{settings.SITE_URL}/static/images/logo.jpg",
        }
        
        # Send customer confirmation
        send_email(
            subject=f'Order Confirmation - #{order.order_number}',
            template_name='orders/email/order_confirmation.html',
            to_email=order.user.email,
            to_name=f"{order.user.first_name} {order.user.last_name}",
            context=context
        )
        
        # Send admin notification
        send_email(
            subject=f'New Order - #{order.order_number}',
            template_name='orders/email/admin_order_notification.html',
            to_email=settings.SERVER_EMAIL,
            to_name='Admin',
            context=context
        )
        
    except Exception as e:
        self.retry(exc=e)

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': settings.EMAIL_TASK_MAX_RETRIES}
)
def send_shipping_update_email(self, order_id, status, tracking_number=None, tracking_url=None):
    """Send shipping status update email to customer."""
    try:
        order = Order.objects.get(id=order_id)
        context = {
            'order': order,
            'order_number': order.order_number,
            'status': status,
            'tracking_number': tracking_number or 'Not available',
            'tracking_url': tracking_url or '#',
            'estimated_delivery': (timezone.now() + timedelta(days=5)).strftime('%B %d, %Y'),
            'site_url': settings.SITE_URL,
            'logo_url': f"{settings.SITE_URL}/static/images/logo.jpg",
        }
        
        send_email(
            subject=f'Shipping Update - Order #{order.order_number}',
            template_name='orders/email/shipping_update.html',
            to_email=order.user.email,
            to_name=f"{order.user.first_name} {order.user.last_name}",
            context=context
        )
        
    except Exception as e:
        self.retry(exc=e)

@shared_task
def process_abandoned_carts():
    """Check for abandoned carts and send reminder emails."""
    cutoff_time = timezone.now() - timedelta(hours=settings.CART_ABANDONMENT_DELAY)
    abandoned_carts = Cart.objects.filter(
        modified_at__lt=cutoff_time,
        is_active=True,
        reminder_count__lt=settings.CART_ABANDONMENT_REMINDER_LIMIT
    ).select_related('user')
    
    for cart in abandoned_carts:
        send_cart_abandonment_email.delay(cart.id)
        cart.reminder_count += 1
        cart.save()

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': settings.EMAIL_TASK_MAX_RETRIES}
)
def send_cart_abandonment_email(self, cart_id):
    """Send abandoned cart reminder email."""
    try:
        cart = Cart.objects.get(id=cart_id)
        
        # Don't send if cart is empty or user has no email
        if not cart.items.exists() or not cart.user.email:
            return
            
        context = {
            'user': cart.user,
            'user_name': f"{cart.user.first_name} {cart.user.last_name}",
            'cart_items': [
                {
                    'name': item.product.name,
                    'quantity': item.quantity,
                    'price': str(item.price),
                    'total': str(item.get_total())
                }
                for item in cart.items.all()
            ],
            'cart_total': str(cart.get_total()),
            'cart_recovery_url': f"{settings.SITE_URL}{reverse('orders:cart')}",
            'site_url': settings.SITE_URL,
            'logo_url': f"{settings.SITE_URL}/static/images/logo.jpg",
            'special_offer': "Use code COMEBACK10 for 10% off your purchase!" if cart.reminder_count == 1 else None
        }
        
        send_email(
            subject='Complete Your Purchase at Rey Premium Vogue',
            template_name='orders/email/cart_abandonment.html',
            to_email=cart.user.email,
            to_name=f"{cart.user.first_name} {cart.user.last_name}",
            context=context
        )
        
    except Exception as e:
        self.retry(exc=e) 