from celery import shared_task

from django.db import transaction
from django.utils import timezone

from .inventory import release_order_inventory
from .models import Order


@shared_task
def expire_unpaid_orders():

    now = timezone.now()

    candidate_ids = list(
        Order.objects.filter(
            status="pending",
            payment_status="pending",
            inventory_status="reserved",
            reservation_expires_at__isnull=False,
            reservation_expires_at__lte=now,
        ).values_list(
            "id",
            flat=True,
        )
    )

    expired_count = 0

    for order_id in candidate_ids:

        with transaction.atomic():

            order = (
                Order.objects
                .select_for_update()
                .filter(pk=order_id)
                .first()
            )

            if not order:
                continue

            # Re-check after obtaining lock.
            if order.payment_status != "pending":
                continue

            if order.status != "pending":
                continue

            if order.inventory_status != "reserved":
                continue

            if (
                not order.reservation_expires_at
                or order.reservation_expires_at > timezone.now()
            ):
                continue

            release_order_inventory(order)

            order.status = "cancelled"

            order.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

            expired_count += 1

    return {
        "expired_orders": expired_count,
    }