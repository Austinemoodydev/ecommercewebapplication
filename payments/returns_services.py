from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

from .models import (
    RefundRequest,
    ReturnRequestItem,
)


ACTIVE_RETURN_STATUSES = [
    "requested",
    "approved",
    "completed",
]


def get_order_delivered_at(order):

    """
    Prefer the actual Delivery delivered timestamp.

    Older orders may not have a Delivery object, so
    fall back to the Order updated timestamp.
    """

    try:

        delivery = order.delivery

    except Exception:

        delivery = None


    if (
        delivery
        and delivery.delivered_at
    ):

        return delivery.delivered_at


    return order.updated_at


def get_return_deadline(order):

    delivered_at = get_order_delivered_at(
        order
    )

    if not delivered_at:
        return None


    days = getattr(
        settings,
        "RETURN_WINDOW_DAYS",
        14,
    )

    return (
        delivered_at
        + timedelta(days=days)
    )


def return_window_open(order):

    deadline = get_return_deadline(
        order
    )

    if deadline is None:
        return True

    return timezone.now() <= deadline


def already_returned_quantity(
    order_item,
):

    total = (
        ReturnRequestItem.objects
        .filter(
            order_item=order_item,
            return_request__status__in=(
                ACTIVE_RETURN_STATUSES
            ),
        )
        .aggregate(
            total=Sum("quantity")
        )["total"]
        or 0
    )

    return int(total)


def remaining_returnable_quantity(
    order_item,
):

    used = already_returned_quantity(
        order_item
    )

    return max(
        int(order_item.quantity)
        - used,
        0,
    )


def processed_refund_total(order):

    return (
        RefundRequest.objects
        .filter(
            order=order,
            status="processed",
        )
        .aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )


def pending_refund_total(order):

    return (
        RefundRequest.objects
        .filter(
            order=order,
            status__in=[
                "requested",
                "approved",
            ],
        )
        .aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )


def remaining_refundable_amount(
    order,
    include_pending=True,
):

    used = processed_refund_total(
        order
    )

    if include_pending:

        used += pending_refund_total(
            order
        )

    remaining = (
        order.total_amount
        - used
    )

    return max(
        remaining,
        Decimal("0.00"),
    )
