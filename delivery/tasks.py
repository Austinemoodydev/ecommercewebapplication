from celery import shared_task


NOTIFIABLE_STATUSES = {
    "dispatched",
    "in_transit",
    "arrived",
    "ready_for_collection",
    "out_for_delivery",
    "delivered",
    "collected",
    "failed",
    "returned",
}


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={
        "max_retries": 3
    },
)
def send_delivery_status_update(
    self,
    delivery_id,
):

    from notifications.tasks import (
        _send_order_notifications,
    )

    from .models import Delivery

    delivery = (
        Delivery.objects
        .select_related(
            "order",
            "order__user",
            "provider",
        )
        .get(
            pk=delivery_id
        )
    )

    if (
        delivery.status
        not in NOTIFIABLE_STATUSES
    ):
        return

    order = delivery.order

    provider_name = (
        delivery.provider.name
        if delivery.provider
        else "our delivery team"
    )

    status_label = (
        delivery.get_status_display()
    )

    details = []

    if delivery.transport_reference:

        details.append(
            "Reference: "
            + delivery.transport_reference
        )

    if delivery.pickup_point:

        details.append(
            "Pickup point: "
            + delivery.pickup_point
        )

    if delivery.destination:

        details.append(
            "Destination: "
            + delivery.destination
        )

    detail_text = ""

    if details:

        detail_text = (
            "\n"
            + "\n".join(details)
        )

    sms = (
        f"Order {order.order_number}: "
        f"{status_label}. "
        f"Provider: {provider_name}."
    )

    if delivery.transport_reference:

        sms += (
            " Ref: "
            + delivery.transport_reference
            + "."
        )

    if (
        delivery.status
        == "ready_for_collection"
        and delivery.pickup_point
    ):

        sms += (
            " Collect from "
            + delivery.pickup_point
            + "."
        )

    email_message = (
        f"Hi {order.full_name},\n\n"
        f"Your order {order.order_number} "
        f"delivery status is now: "
        f"{status_label}.\n\n"
        f"Provider: {provider_name}"
        f"{detail_text}\n\n"
        f"You can sign in to your account "
        f"to view the full delivery timeline."
    )

    _send_order_notifications(
        order,
        sms,
        f"Delivery update: {status_label}",
        email_message,
        event_key=(
            f"delivery:"
            f"{delivery.pk}:"
            f"{delivery.status}"
        ),
        category="delivery",
    )



@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={
        "max_retries": 3
    },
)
def send_delivery_quote_update(
    self,
    order_id,
):

    from notifications.tasks import (
        _send_order_notifications,
    )

    from orders.models import Order

    order = (
        Order.objects
        .select_related(
            "user",
            "delivery_zone",
        )
        .get(
            pk=order_id
        )
    )

    sms = (
        f"Order {order.order_number}: "
        f"delivery fee confirmed at "
        f"KES {order.shipping_cost:.2f}. "
        f"Total payable is "
        f"KES {order.total_amount:.2f}. "
        f"Please complete M-PESA payment."
    )

    email_message = (
        f"Hi {order.full_name},\n\n"
        f"Your delivery charge for order "
        f"{order.order_number} has been confirmed.\n\n"
        f"Delivery: KES "
        f"{order.shipping_cost:.2f}\n"
        f"Total payable: KES "
        f"{order.total_amount:.2f}\n\n"
        f"The quote is valid for 24 hours.\n\n"
        f"Please sign in to complete "
        f"your M-PESA payment."
    )

    _send_order_notifications(
        order,
        sms,
        "Your delivery quote is ready",
        email_message,
        event_key=(
            f"delivery-quote:"
            f"{order.pk}:"
            f"{order.shipping_cost}:"
            f"{order.total_amount}"
        ),
        category="delivery",
    )
