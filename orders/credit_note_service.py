from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import Sum

from orders.models import (
    CreditNoteDocument,
    Order,
)

from payments.models import (
    RefundRequest,
)


ZERO = Decimal("0.00")


def _money(
    value,
):

    return format(
        Decimal(
            value or ZERO
        ),
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


def build_credit_note_snapshot(
    refund,
):

    order = refund.order


    total_processed_refunds = (
        RefundRequest.objects
        .filter(
            order=order,
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


    remaining_amount = (
        Decimal(
            order.total_amount
        )
        - Decimal(
            total_processed_refunds
        )
    )


    if remaining_amount < ZERO:
        remaining_amount = ZERO


    items = []


    for item in order.items.all():

        items.append(
            {

                "product_name":
                    item.product_name,

                "variant_name":
                    item.variant_name,

                "quantity":
                    item.quantity,

                "price":
                    _money(
                        item.price
                    ),

                "subtotal":
                    _money(
                        item.subtotal
                    ),
            }
        )


    return {

        "schema_version": 1,

        "store":
            _store_snapshot(),

        "order": {

            "order_number":
                order.order_number,

            "full_name":
                order.full_name,

            "phone":
                order.phone,

            "email":
                order.email,

            "total_amount":
                _money(
                    order.total_amount
                ),

            "payment_method":
                order.payment_method,

            "payment_status":
                order.payment_status,
        },

        "refund": {

            "id":
                refund.pk,

            "amount":
                _money(
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

            "processed_by":
                (
                    refund.processed_by
                    .get_username()
                    if refund.processed_by
                    else ""
                ),
        },

        "items":
            items,

        "total_processed_refunds":
            _money(
                total_processed_refunds
            ),

        "remaining_amount":
            _money(
                remaining_amount
            ),
    }


def _credit_note_number(
    refund,
):

    # Refund ID provides stable uniqueness.
    return (
        f"CN-"
        f"{refund.order.order_number}-"
        f"{refund.pk:02d}"
    )


@transaction.atomic
def get_or_issue_credit_note(
    *,
    refund,
    issued_by=None,
):

    locked_refund = (
        RefundRequest.objects
        .select_for_update()
        .select_related(
            "order",
            "processed_by",
        )
        .get(
            pk=refund.pk
        )
    )


    if locked_refund.status != "processed":

        raise ValueError(
            "Credit notes can only be issued "
            "for processed refunds."
        )


    if not locked_refund.external_reference:

        raise ValueError(
            "Processed refund must have an "
            "external reference before a "
            "credit note is issued."
        )


    existing = (
        CreditNoteDocument.objects
        .filter(
            refund_request=locked_refund
        )
        .first()
    )


    if existing:
        return existing


    locked_refund = (
        RefundRequest.objects
        .select_related(
            "order",
            "processed_by",
        )
        .prefetch_related(
            "order__items",
        )
        .get(
            pk=locked_refund.pk
        )
    )


    return (
        CreditNoteDocument.objects
        .create(
            order=locked_refund.order,

            refund_request=locked_refund,

            document_number=(
                _credit_note_number(
                    locked_refund
                )
            ),

            snapshot=(
                build_credit_note_snapshot(
                    locked_refund
                )
            ),

            issued_by=issued_by,
        )
    )
