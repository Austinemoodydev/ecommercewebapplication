from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import Sum

from orders.models import (
    Order,
    OrderDocument,
)


ZERO = Decimal("0.00")


def _money_string(
    value,
):

    if value is None:
        value = ZERO

    return format(
        Decimal(value),
        ".2f",
    )


def _store_snapshot():

    return {

        "name": getattr(
            settings,
            "STORE_NAME",
            "Online Shop",
        ),

        "email": getattr(
            settings,
            "STORE_EMAIL",
            "",
        ),

        "phone": getattr(
            settings,
            "STORE_PHONE",
            "",
        ),

        "address": getattr(
            settings,
            "STORE_ADDRESS",
            "",
        ),

        "website": getattr(
            settings,
            "STORE_WEBSITE",
            "",
        ),
    }


def _successful_payment(
    order,
):

    tx = (
        order.mpesa_transactions
        .filter(
            status="success",
        )
        .order_by(
            "-updated_at"
        )
        .first()
    )


    if not tx:
        return None


    return {

        "phone_number":
            tx.phone_number,

        "amount":
            _money_string(
                tx.amount
            ),

        "merchant_request_id":
            tx.merchant_request_id,

        "checkout_request_id":
            tx.checkout_request_id,

        "mpesa_receipt_number":
            tx.mpesa_receipt_number,

        "result_code":
            tx.result_code,

        "result_description":
            tx.result_description,

        "created_at":
            tx.created_at.isoformat()
            if tx.created_at
            else None,

        "updated_at":
            tx.updated_at.isoformat()
            if tx.updated_at
            else None,
    }


def _refund_snapshot(
    order,
):

    refunds = list(
        order.refund_requests
        .filter(
            status="processed",
        )
        .order_by(
            "processed_at",
            "created_at",
        )
    )


    total = (
        order.refund_requests
        .filter(
            status="processed",
        )
        .aggregate(
            total=Sum(
                "amount"
            )
        )[
            "total"
        ]
        or ZERO
    )


    rows = []


    for refund in refunds:

        rows.append(
            {

                "amount":
                    _money_string(
                        refund.amount
                    ),

                "reason":
                    refund.reason,

                "external_reference":
                    refund.external_reference,

                "processed_at":
                    (
                        refund.processed_at
                        .isoformat()
                        if refund.processed_at
                        else None
                    ),
            }
        )


    return (
        rows,
        Decimal(total),
    )


def build_order_document_snapshot(
    order,
):

    items = []


    for item in order.items.all():

        items.append(
            {

                "product_name":
                    item.product_name,

                "variant_name":
                    item.variant_name,

                "price":
                    _money_string(
                        item.price
                    ),

                "quantity":
                    item.quantity,

                "subtotal":
                    _money_string(
                        item.subtotal
                    ),

                "unit_cost_at_sale":
                    (
                        _money_string(
                            item.unit_cost_at_sale
                        )
                        if (
                            item.unit_cost_at_sale
                            is not None
                        )
                        else None
                    ),
            }
        )


    refund_rows, refund_total = (
        _refund_snapshot(
            order
        )
    )


    net_amount = (
        Decimal(
            order.total_amount
        )
        - refund_total
    )


    if net_amount < ZERO:
        net_amount = ZERO


    delivery = None


    try:

        delivery_obj = order.delivery

    except Exception:

        delivery_obj = None


    if delivery_obj:

        provider_name = ""

        if getattr(
            delivery_obj,
            "provider_id",
            None,
        ):

            provider_name = (
                delivery_obj.provider.name
            )


        delivery = {

            "method":
                delivery_obj.method,

            "method_display":
                delivery_obj.get_method_display(),

            "management_type":
                delivery_obj.management_type,

            "provider":
                provider_name,

            "status":
                delivery_obj.status,

            "status_display":
                delivery_obj.get_status_display(),

            "destination":
                delivery_obj.destination,

            "transport_reference":
                getattr(
                    delivery_obj,
                    "transport_reference",
                    "",
                ),

            "tracking_number":
                getattr(
                    delivery_obj,
                    "tracking_number",
                    "",
                ),
        }


    coupon_code = ""

    if order.coupon_id:
        coupon_code = order.coupon.code


    return {

        "schema_version": 1,

        "store":
            _store_snapshot(),

        "order": {

            "order_number":
                order.order_number,

            "created_at":
                (
                    order.created_at
                    .isoformat()
                ),

            "full_name":
                order.full_name,

            "phone":
                order.phone,

            "email":
                order.email,

            "county":
                order.county,

            "city":
                order.city,

            "estate":
                order.estate,

            "house_number":
                order.house_number,

            "landmark":
                order.landmark,

            "delivery_notes":
                order.delivery_notes,

            "subtotal":
                _money_string(
                    order.subtotal
                ),

            "shipping_cost":
                _money_string(
                    order.shipping_cost
                ),

            "discount":
                _money_string(
                    order.discount
                ),

            "total_amount":
                _money_string(
                    order.total_amount
                ),

            "payment_method":
                order.payment_method,

            "payment_status":
                order.payment_status,

            "payment_status_display":
                order.get_payment_status_display(),

            "order_status":
                order.status,

            "order_status_display":
                order.get_status_display(),

            "coupon_code":
                coupon_code,
        },

        "items":
            items,

        "payment":
            _successful_payment(
                order
            ),

        "refunds":
            refund_rows,

        "refund_total":
            _money_string(
                refund_total
            ),

        "net_amount":
            _money_string(
                net_amount
            ),

        "delivery":
            delivery,
    }


def _document_number(
    order,
    document_type,
):

    if document_type == "invoice":

        prefix = "INV"

    elif document_type == "receipt":

        prefix = "RCP"

    else:

        raise ValueError(
            "Unknown document type."
        )


    return (
        f"{prefix}-"
        f"{order.order_number}"
    )


@transaction.atomic
def get_or_issue_order_document(
    *,
    order,
    document_type,
    issued_by=None,
):

    # Lock the order so two simultaneous requests cannot
    # independently issue competing snapshots.

    locked_order = (
        Order.objects
        .select_for_update()
        .get(
            pk=order.pk
        )
    )


    existing = (
        OrderDocument.objects
        .filter(
            order=locked_order,
            document_type=document_type,
        )
        .first()
    )


    if existing:
        return existing


    # Reload required relations after acquiring lock.

    locked_order = (
        Order.objects
        .select_related(
            "coupon",
        )
        .prefetch_related(
            "items",
            "mpesa_transactions",
            "refund_requests",
        )
        .get(
            pk=locked_order.pk
        )
    )


    return (
        OrderDocument.objects
        .create(
            order=locked_order,

            document_type=(
                document_type
            ),

            document_number=(
                _document_number(
                    locked_order,
                    document_type,
                )
            ),

            snapshot=(
                build_order_document_snapshot(
                    locked_order
                )
            ),

            issued_by=issued_by,
        )
    )
