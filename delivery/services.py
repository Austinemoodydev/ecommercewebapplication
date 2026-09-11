from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from orders.models import Order

from .models import (
    Delivery,
    DeliveryEvent,
)





SETTLED_DELIVERY_PAYMENT_STATUSES = {
    "paid",
    "partially_refunded",
    "refunded",
}


def _queue_delivery_notification(
    delivery_id,
):

    try:

        from .tasks import (
            send_delivery_status_update,
        )

        send_delivery_status_update.delay(
            delivery_id
        )

    except Exception:

        # Delivery state must never be rolled back
        # because the message broker is temporarily
        # unavailable.
        pass


DELIVERY_TRANSITIONS = {

    "pending": [
        "assigned",
        "cancelled",
    ],

    "assigned": [
        "ready_for_dispatch",
        "dispatched",
        "out_for_delivery",
        "cancelled",
    ],

    "ready_for_dispatch": [
        "dispatched",
        "out_for_delivery",
        "cancelled",
    ],

    "dispatched": [
        "in_transit",
        "arrived",
        "out_for_delivery",
        "failed",
    ],

    "in_transit": [
        "arrived",
        "out_for_delivery",
        "failed",
    ],

    "arrived": [
        "ready_for_collection",
        "out_for_delivery",
        "delivered",
        "failed",
    ],

    "ready_for_collection": [
        "collected",
        "failed",
    ],

    "out_for_delivery": [
        "delivered",
        "failed",
    ],

    "failed": [
        "assigned",
        "ready_for_dispatch",
        "dispatched",
        "out_for_delivery",
        "returned",
        "cancelled",
    ],

    "delivered": [],
    "collected": [],
    "returned": [],
    "cancelled": [],
}


def allowed_delivery_statuses(
    delivery
):

    return DELIVERY_TRANSITIONS.get(
        delivery.status,
        [],
    )


@transaction.atomic
def change_delivery_status(
    *,
    delivery,
    status,
    user,
    message="",
):

    delivery = (
        Delivery.objects
        .select_for_update()
        .select_related(
            "order",
            "provider",
        )
        .get(pk=delivery.pk)
    )

    allowed = allowed_delivery_statuses(
        delivery
    )

    if status not in allowed:

        raise ValidationError(
            (
                f"Delivery cannot move from "
                f"{delivery.get_status_display()} "
                f"to {dict(Delivery.STATUS_CHOICES).get(status, status)}."
            )
        )

    order = delivery.order

    # Money should be confirmed before the parcel leaves.
    if status in [
        "dispatched",
        "in_transit",
        "arrived",
        "ready_for_collection",
        "out_for_delivery",
        "delivered",
        "collected",
    ]:

        if order.payment_status not in SETTLED_DELIVERY_PAYMENT_STATUSES:

            raise ValidationError(
                (
                    "This order has not been paid. "
                    "It cannot be dispatched or delivered."
                )
            )

    now = timezone.now()

    delivery.status = status

    update_fields = [
        "status",
        "updated_at",
    ]

    if (
        status == "dispatched"
        and not delivery.dispatched_at
    ):

        delivery.dispatched_at = now
        update_fields.append(
            "dispatched_at"
        )

    if (
        status == "arrived"
        and not delivery.arrived_at
    ):

        delivery.arrived_at = now
        update_fields.append(
            "arrived_at"
        )

    if (
        status == "delivered"
        and not delivery.delivered_at
    ):

        delivery.delivered_at = now
        update_fields.append(
            "delivered_at"
        )

    if (
        status == "collected"
        and not delivery.collected_at
    ):

        delivery.collected_at = now
        update_fields.append(
            "collected_at"
        )

    delivery.save(
        update_fields=update_fields
    )

    DeliveryEvent.objects.create(
        delivery=delivery,
        status=status,
        message=message.strip(),
        created_by=user,
    )


    transaction.on_commit(
        lambda delivery_id=delivery.pk: (
            _queue_delivery_notification(
                delivery_id
            )
        ),
        robust=True,
    )

    # Keep the legacy Order status useful for the
    # existing order-management screens.
    if status in [
        "dispatched",
        "in_transit",
        "arrived",
        "ready_for_collection",
        "out_for_delivery",
    ]:

        if order.status in [
            "confirmed",
            "processing",
        ]:

            order.status = "shipped"

            order.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

    elif status in [
        "delivered",
        "collected",
    ]:

        order.status = "delivered"

        order.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

    return delivery
