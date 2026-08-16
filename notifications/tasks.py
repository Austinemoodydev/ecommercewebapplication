from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail


def _get_sms_client():
    """Initialise Africa's Talking inside the worker, not the web process."""
    if not settings.AFRICASTALKING_USERNAME or not settings.AFRICASTALKING_API_KEY:
        raise RuntimeError("Africa's Talking SMS credentials are not configured")
    import africastalking
    africastalking.initialize(settings.AFRICASTALKING_USERNAME, settings.AFRICASTALKING_API_KEY)
    return africastalking.SMS


def _normalise_phone(phone_number):
    phone_number = phone_number.strip().replace(" ", "")
    if phone_number.startswith("0"):
        return f"+254{phone_number[1:]}"
    if phone_number.startswith("254"):
        return f"+{phone_number}"
    return phone_number


def _send_order_notifications(order, sms_message, subject, email_message):
    """Run provider calls in the worker so web requests and callbacks stay fast."""
    if order.phone:
        _get_sms_client().send(sms_message, [_normalise_phone(order.phone)])
    if order.email:
        send_mail(
            subject=f"{subject} — {order.order_number}", message=email_message,
            from_email=settings.DEFAULT_FROM_EMAIL, recipient_list=[order.email],
            fail_silently=False,
        )


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True,
             retry_jitter=True, retry_kwargs={"max_retries": 3})
def send_payment_confirmation(self, order_id):
    from orders.models import Order
    order = Order.objects.get(id=order_id)
    _send_order_notifications(
        order,
        f"Order {order.order_number}: payment received (KES {order.total_amount}). Awaiting shipment.",
        "Payment received",
        f"Hi {order.full_name},\n\nPayment received for order {order.order_number} "
        f"(KES {order.total_amount}). Your order is awaiting shipment.",
    )


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True,
             retry_jitter=True, retry_kwargs={"max_retries": 3})
def send_delivery_notification(self, order_id):
    from orders.models import Order
    order = Order.objects.get(id=order_id)
    _send_order_notifications(
        order,
        f"Order {order.order_number} has been delivered. Thank you for shopping with us.",
        "Order delivered",
        f"Hi {order.full_name},\n\nOrder {order.order_number} has been delivered. Thank you for shopping with us.",
    )
