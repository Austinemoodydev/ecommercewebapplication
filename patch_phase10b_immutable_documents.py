from pathlib import Path
import shutil


ROOT = Path.cwd()

MODELS = ROOT / "orders" / "models.py"
SERVICE = ROOT / "orders" / "document_service.py"
VIEWS = ROOT / "orders" / "document_views.py"

URLS = ROOT / "dashboard" / "urls.py"

BASE = (
    ROOT
    / "templates"
    / "orders"
    / "documents"
    / "base.html"
)

INVOICE = (
    ROOT
    / "templates"
    / "orders"
    / "documents"
    / "invoice.html"
)

RECEIPT = (
    ROOT
    / "templates"
    / "orders"
    / "documents"
    / "receipt.html"
)

TESTS = (
    ROOT
    / "dashboard"
    / "test_phase10b.py"
)


# ============================================================
# BACKUPS
# ============================================================

for path in [
    MODELS,
    VIEWS,
    URLS,
    BASE,
    INVOICE,
    RECEIPT,
]:

    if not path.exists():
        raise RuntimeError(
            f"Missing required file: {path}"
        )

    backup = Path(
        str(path)
        + ".phase10bbackup"
    )

    if not backup.exists():
        shutil.copy2(
            path,
            backup,
        )


# ============================================================
# 1. ORDER DOCUMENT MODEL
# ============================================================

text = MODELS.read_text(
    encoding="utf-8-sig"
)


if "class OrderDocument(" not in text:

    model = r'''


class OrderDocument(models.Model):

    INVOICE = "invoice"
    RECEIPT = "receipt"

    DOCUMENT_TYPE_CHOICES = [
        (
            INVOICE,
            "Invoice",
        ),
        (
            RECEIPT,
            "Receipt",
        ),
    ]


    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name="documents",
    )

    document_type = models.CharField(
        max_length=20,
        choices=DOCUMENT_TYPE_CHOICES,
    )

    document_number = models.CharField(
        max_length=120,
        unique=True,
        db_index=True,
    )

    snapshot = models.JSONField(
        default=dict,
    )

    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issued_order_documents",
    )

    issued_at = models.DateTimeField(
        auto_now_add=True,
    )

    last_emailed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    email_count = models.PositiveIntegerField(
        default=0,
    )


    class Meta:

        ordering = [
            "-issued_at",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "order",
                    "document_type",
                ],
                name=(
                    "unique_order_document_type"
                ),
            ),
        ]


    def __str__(self):

        return (
            f"{self.document_number} "
            f"- {self.order.order_number}"
        )
'''

    text += model


MODELS.write_text(
    text,
    encoding="utf-8",
)

print(
    "OrderDocument model added."
)


# ============================================================
# 2. IMMUTABLE DOCUMENT SNAPSHOT SERVICE
# ============================================================

SERVICE.write_text(
r'''
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
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Immutable snapshot service created."
)


# ============================================================
# 3. REPLACE DOCUMENT VIEWS
# ============================================================

VIEWS.write_text(
r'''
from django.conf import settings
from django.contrib import messages

from django.contrib.admin.views.decorators import (
    staff_member_required,
)

from django.contrib.auth.decorators import (
    login_required,
)

from django.core.mail import send_mail

from django.db.models import F

from django.http import Http404

from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from django.utils import timezone

from django.views.decorators.http import (
    require_POST,
)

from orders.document_service import (
    get_or_issue_order_document,
)

from orders.models import (
    Order,
    OrderDocument,
)


SETTLED_PAYMENT_STATUSES = {
    "paid",
    "partially_refunded",
    "refunded",
}


def _document_queryset():

    return (
        Order.objects
        .select_related(
            "user",
            "coupon",
        )
        .prefetch_related(
            "items",
            "mpesa_transactions",
            "refund_requests",
        )
    )


def _issue(
    *,
    request,
    order,
    document_type,
):

    if (
        document_type == "receipt"
        and order.payment_status
        not in SETTLED_PAYMENT_STATUSES
    ):

        raise Http404(
            "Receipt is not available "
            "for an unpaid order."
        )


    return (
        get_or_issue_order_document(
            order=order,
            document_type=document_type,
            issued_by=request.user,
        )
    )


def _render(
    request,
    document,
):

    template = (
        "orders/documents/"
        f"{document.document_type}.html"
    )


    return render(
        request,
        template,
        {
            "document":
                document,

            "snapshot":
                document.snapshot,

            "order":
                document.order,

            "document_title":
                document.get_document_type_display(),

            "document_number":
                document.document_number,

            "email_url_name":
                (
                    "admin_order_document_email"
                    if request.user.is_staff
                    else
                    "customer_order_document_email"
                ),
        },
    )


# ============================================================
# CUSTOMER DOCUMENTS
# ============================================================

@login_required
def customer_invoice(
    request,
    order_number,
):

    order = get_object_or_404(
        _document_queryset(),
        order_number=order_number,
        user=request.user,
    )


    document = _issue(
        request=request,
        order=order,
        document_type="invoice",
    )


    return _render(
        request,
        document,
    )


@login_required
def customer_receipt(
    request,
    order_number,
):

    order = get_object_or_404(
        _document_queryset(),
        order_number=order_number,
        user=request.user,
    )


    document = _issue(
        request=request,
        order=order,
        document_type="receipt",
    )


    return _render(
        request,
        document,
    )


# ============================================================
# ADMIN DOCUMENTS
# ============================================================

@staff_member_required
def admin_invoice(
    request,
    order_number,
):

    order = get_object_or_404(
        _document_queryset(),
        order_number=order_number,
    )


    document = _issue(
        request=request,
        order=order,
        document_type="invoice",
    )


    return _render(
        request,
        document,
    )


@staff_member_required
def admin_receipt(
    request,
    order_number,
):

    order = get_object_or_404(
        _document_queryset(),
        order_number=order_number,
    )


    document = _issue(
        request=request,
        order=order,
        document_type="receipt",
    )


    return _render(
        request,
        document,
    )


# ============================================================
# EMAIL DELIVERY
# ============================================================

def _send_document_email(
    request,
    document,
):

    snapshot = document.snapshot

    order_snapshot = snapshot[
        "order"
    ]

    recipient = (
        order_snapshot.get(
            "email"
        )
        or ""
    ).strip()


    if not recipient:

        messages.error(
            request,
            "This order does not have "
            "a customer email address.",
        )

        return False


    absolute_url = (
        request.build_absolute_uri(
            document_view_url(
                request,
                document,
            )
        )
    )


    subject = (
        f"{document.get_document_type_display()} "
        f"{document.document_number}"
    )


    body = (
        f"Hello "
        f"{order_snapshot.get('full_name', 'Customer')},\n\n"
        f"Your "
        f"{document.get_document_type_display().lower()} "
        f"for order "
        f"{order_snapshot['order_number']} "
        f"is available.\n\n"
        f"Document number: "
        f"{document.document_number}\n"
        f"Order total: KES "
        f"{order_snapshot['total_amount']}\n\n"
        f"View document:\n"
        f"{absolute_url}\n\n"
        f"Thank you."
    )


    send_mail(
        subject=subject,
        message=body,
        from_email=getattr(
            settings,
            "DEFAULT_FROM_EMAIL",
            None,
        ),
        recipient_list=[
            recipient
        ],
        fail_silently=False,
    )


    (
        OrderDocument.objects
        .filter(
            pk=document.pk
        )
        .update(
            email_count=(
                F("email_count")
                + 1
            ),
            last_emailed_at=timezone.now(),
        )
    )


    document.refresh_from_db(
        fields=[
            "email_count",
            "last_emailed_at",
        ]
    )


    messages.success(
        request,
        f"{document.get_document_type_display()} "
        f"sent to {recipient}.",
    )


    return True


def document_view_url(
    request,
    document,
):

    from django.urls import reverse


    if request.user.is_staff:

        route = (
            "admin_order_invoice"
            if (
                document.document_type
                == "invoice"
            )
            else
            "admin_order_receipt"
        )

    else:

        route = (
            "customer_order_invoice"
            if (
                document.document_type
                == "invoice"
            )
            else
            "customer_order_receipt"
        )


    return reverse(
        route,
        args=[
            document.order.order_number
        ],
    )


@login_required
@require_POST
def customer_document_email(
    request,
    order_number,
    document_type,
):

    if document_type not in {
        "invoice",
        "receipt",
    }:

        raise Http404


    order = get_object_or_404(
        _document_queryset(),
        order_number=order_number,
        user=request.user,
    )


    document = _issue(
        request=request,
        order=order,
        document_type=document_type,
    )


    _send_document_email(
        request,
        document,
    )


    return redirect(
        document_view_url(
            request,
            document,
        )
    )


@staff_member_required
@require_POST
def admin_document_email(
    request,
    order_number,
    document_type,
):

    if document_type not in {
        "invoice",
        "receipt",
    }:

        raise Http404


    order = get_object_or_404(
        _document_queryset(),
        order_number=order_number,
    )


    document = _issue(
        request=request,
        order=order,
        document_type=document_type,
    )


    _send_document_email(
        request,
        document,
    )


    return redirect(
        document_view_url(
            request,
            document,
        )
    )
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Document views upgraded to immutable snapshots."
)


# ============================================================
# 4. EMAIL URLS
# ============================================================

text = URLS.read_text(
    encoding="utf-8-sig"
)


if 'name="customer_order_document_email"' not in text:

    marker = '''    path(
        "orders/<str:order_number>/receipt/",
        document_views.customer_receipt,
        name="customer_order_receipt",
    ),
'''

    replacement = marker + '''
    path(
        "orders/<str:order_number>/documents/<str:document_type>/email/",
        document_views.customer_document_email,
        name="customer_order_document_email",
    ),
'''

    if marker not in text:

        raise RuntimeError(
            "Could not locate customer "
            "receipt route."
        )

    text = text.replace(
        marker,
        replacement,
        1,
    )


if 'name="admin_order_document_email"' not in text:

    marker = '''    path(
        "admin/orders/<str:order_number>/receipt/",
        document_views.admin_receipt,
        name="admin_order_receipt",
    ),
'''

    replacement = marker + '''
    path(
        "admin/orders/<str:order_number>/documents/<str:document_type>/email/",
        document_views.admin_document_email,
        name="admin_order_document_email",
    ),
'''

    if marker not in text:

        raise RuntimeError(
            "Could not locate admin "
            "receipt route."
        )

    text = text.replace(
        marker,
        replacement,
        1,
    )


URLS.write_text(
    text,
    encoding="utf-8",
)

print(
    "Document email routes added."
)


# ============================================================
# 5. PRINT BASE TEMPLATE
# ============================================================

BASE.write_text(
r'''
<!DOCTYPE html>

<html lang="en">

<head>

    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1"
    >

    <title>
        {{ document_title }}
        {{ document_number }}
    </title>


    <style>

        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            background: #f4f5f7;
            color: #1f2937;
            font-family: Arial, Helvetica, sans-serif;
            line-height: 1.5;
        }

        .document-toolbar {
            max-width: 950px;
            margin: 24px auto 0;
            padding: 0 16px;
            display: flex;
            flex-wrap: wrap;
            justify-content: flex-end;
            gap: 10px;
        }

        .document-toolbar a,
        .document-toolbar button {
            border: 1px solid #d1d5db;
            background: white;
            color: #111827;
            padding: 10px 16px;
            border-radius: 7px;
            text-decoration: none;
            cursor: pointer;
            font-weight: 600;
        }

        .document-toolbar .primary {
            background: #111827;
            color: white;
            border-color: #111827;
        }

        .document-sheet {
            width: calc(100% - 32px);
            max-width: 950px;
            min-height: 1120px;
            margin: 16px auto 40px;
            background: white;
            padding: 52px;
            box-shadow:
                0 10px 35px
                rgba(0, 0, 0, .08);
        }

        .header {
            display: flex;
            justify-content: space-between;
            gap: 40px;
            padding-bottom: 30px;
            border-bottom: 2px solid #111827;
        }

        .brand h1 {
            margin: 0 0 8px;
            font-size: 28px;
        }

        .brand p,
        .document-meta p {
            margin: 3px 0;
            color: #6b7280;
        }

        .document-meta {
            text-align: right;
        }

        .document-meta h2 {
            font-size: 30px;
            margin: 0 0 10px;
            text-transform: uppercase;
        }

        .status {
            display: inline-block;
            margin-top: 8px;
            padding: 5px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            background: #eef2ff;
        }

        .grid {
            display: grid;
            grid-template-columns:
                repeat(2, minmax(0, 1fr));
            gap: 30px;
            margin: 32px 0;
        }

        .section-title {
            margin: 0 0 12px;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: .08em;
            color: #6b7280;
        }

        .info-block p {
            margin: 4px 0;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 24px;
        }

        th {
            text-align: left;
            font-size: 12px;
            text-transform: uppercase;
            color: #6b7280;
            border-bottom: 2px solid #e5e7eb;
            padding: 12px 8px;
        }

        td {
            border-bottom: 1px solid #e5e7eb;
            padding: 14px 8px;
        }

        .text-right {
            text-align: right;
        }

        .totals {
            margin-left: auto;
            margin-top: 25px;
            width: min(390px, 100%);
        }

        .total-row {
            display: flex;
            justify-content: space-between;
            padding: 7px 0;
            gap: 20px;
        }

        .grand-total {
            border-top: 2px solid #111827;
            margin-top: 8px;
            padding-top: 14px;
            font-size: 20px;
            font-weight: 700;
        }

        .refund-row {
            color: #b91c1c;
        }

        .payment-box {
            margin-top: 30px;
            padding: 20px;
            border: 1px solid #e5e7eb;
            background: #f9fafb;
            border-radius: 8px;
        }

        .footer {
            margin-top: 55px;
            border-top: 1px solid #e5e7eb;
            padding-top: 20px;
            color: #6b7280;
            font-size: 13px;
            text-align: center;
        }

        .small {
            font-size: 13px;
            color: #6b7280;
        }

        .immutable-note {
            max-width: 950px;
            margin: 10px auto;
            padding: 0 16px;
            font-size: 12px;
            color: #6b7280;
            text-align: right;
        }

        @media(max-width: 700px) {

            .document-sheet {
                padding: 25px;
                min-height: auto;
            }

            .header,
            .grid {
                display: block;
            }

            .document-meta {
                text-align: left;
                margin-top: 25px;
            }

        }

        @media print {

            @page {
                size: A4;
                margin: 14mm;
            }

            body {
                background: white;
            }

            .no-print {
                display: none !important;
            }

            .document-sheet {
                width: 100%;
                max-width: none;
                min-height: auto;
                margin: 0;
                padding: 0;
                box-shadow: none;
            }

            tr,
            td,
            th {
                page-break-inside: avoid;
            }

        }

    </style>

</head>


<body>


<div class="document-toolbar no-print">

    {% if request.user.is_staff %}

        <a
            href="{% url 'admin_order_detail' order.order_number %}"
        >
            Back to Order
        </a>

    {% else %}

        <a
            href="{% url 'order_detail' order.order_number %}"
        >
            Back to Order
        </a>

    {% endif %}


    {% if snapshot.order.email %}

        <form
            method="post"
            action="{% url email_url_name order.order_number document.document_type %}"
        >

            {% csrf_token %}

            <button type="submit">
                Email Customer
            </button>

        </form>

    {% endif %}


    <button
        type="button"
        class="primary"
        onclick="window.print()"
    >
        Print / Save PDF
    </button>

</div>


<div class="immutable-note no-print">

    Issued:
    {{ document.issued_at|date:"d M Y H:i" }}

    · Email count:
    {{ document.email_count }}

</div>


<main class="document-sheet">

    {% block document_content %}
    {% endblock %}

</main>


</body>

</html>
'''.strip() + "\n",
encoding="utf-8",
)


# ============================================================
# 6. SNAPSHOT-BASED INVOICE
# ============================================================

INVOICE.write_text(
r'''
{% extends "orders/documents/base.html" %}


{% block document_content %}

<header class="header">

    <div class="brand">

        <h1>
            {{ snapshot.store.name }}
        </h1>

        {% if snapshot.store.address %}
            <p>{{ snapshot.store.address }}</p>
        {% endif %}

        {% if snapshot.store.phone %}
            <p>{{ snapshot.store.phone }}</p>
        {% endif %}

        {% if snapshot.store.email %}
            <p>{{ snapshot.store.email }}</p>
        {% endif %}

        {% if snapshot.store.website %}
            <p>{{ snapshot.store.website }}</p>
        {% endif %}

    </div>


    <div class="document-meta">

        <h2>Invoice</h2>

        <p>
            <strong>
                {{ document.document_number }}
            </strong>
        </p>

        <p>
            Order:
            {{ snapshot.order.order_number }}
        </p>

        <p>
            Issued:
            {{ document.issued_at|date:"d M Y H:i" }}
        </p>

        <span class="status">
            Payment:
            {{ snapshot.order.payment_status_display }}
        </span>

    </div>

</header>


<section class="grid">

    <div class="info-block">

        <h3 class="section-title">
            Bill To
        </h3>

        <p>
            <strong>
                {{ snapshot.order.full_name }}
            </strong>
        </p>

        <p>
            {{ snapshot.order.phone }}
        </p>

        {% if snapshot.order.email %}
            <p>{{ snapshot.order.email }}</p>
        {% endif %}

    </div>


    <div class="info-block">

        <h3 class="section-title">
            Delivery Address
        </h3>

        {% if snapshot.order.house_number %}
            <p>{{ snapshot.order.house_number }}</p>
        {% endif %}

        {% if snapshot.order.estate %}
            <p>{{ snapshot.order.estate }}</p>
        {% endif %}

        <p>
            {{ snapshot.order.city }},
            {{ snapshot.order.county }}
        </p>

        {% if snapshot.order.landmark %}

            <p>
                Landmark:
                {{ snapshot.order.landmark }}
            </p>

        {% endif %}

    </div>

</section>


<table>

    <thead>

        <tr>

            <th>Item</th>

            <th class="text-right">
                Unit Price
            </th>

            <th class="text-right">
                Qty
            </th>

            <th class="text-right">
                Amount
            </th>

        </tr>

    </thead>


    <tbody>

        {% for item in snapshot.items %}

            <tr>

                <td>

                    <strong>
                        {{ item.product_name }}
                    </strong>

                    {% if item.variant_name %}

                        <div class="small">
                            {{ item.variant_name }}
                        </div>

                    {% endif %}

                </td>

                <td class="text-right">
                    KES {{ item.price }}
                </td>

                <td class="text-right">
                    {{ item.quantity }}
                </td>

                <td class="text-right">
                    KES {{ item.subtotal }}
                </td>

            </tr>

        {% endfor %}

    </tbody>

</table>


<div class="totals">

    <div class="total-row">

        <span>Subtotal</span>

        <strong>
            KES {{ snapshot.order.subtotal }}
        </strong>

    </div>


    {% if snapshot.order.discount != "0.00" %}

        <div class="total-row">

            <span>Discount</span>

            <strong>
                - KES {{ snapshot.order.discount }}
            </strong>

        </div>

    {% endif %}


    <div class="total-row">

        <span>Delivery</span>

        <strong>
            KES {{ snapshot.order.shipping_cost }}
        </strong>

    </div>


    <div class="total-row grand-total">

        <span>Total</span>

        <span>
            KES {{ snapshot.order.total_amount }}
        </span>

    </div>

</div>


{% if snapshot.order.coupon_code %}

    <div class="payment-box">

        <strong>Promotion:</strong>

        Coupon
        {{ snapshot.order.coupon_code }}

    </div>

{% endif %}


{% if snapshot.delivery %}

    <div class="payment-box">

        <h3>
            Delivery Information
        </h3>

        <p>
            Method:
            {{ snapshot.delivery.method_display }}
        </p>

        {% if snapshot.delivery.provider %}

            <p>
                Provider:
                {{ snapshot.delivery.provider }}
            </p>

        {% endif %}

        {% if snapshot.delivery.transport_reference %}

            <p>
                Reference:
                {{ snapshot.delivery.transport_reference }}
            </p>

        {% endif %}

        <p>
            Status:
            {{ snapshot.delivery.status_display }}
        </p>

    </div>

{% endif %}


<div class="footer">

    <p>
        Thank you for shopping with
        {{ snapshot.store.name }}.
    </p>

    <p>
        Document snapshot:
        {{ document.document_number }}
    </p>

</div>

{% endblock %}
'''.strip() + "\n",
encoding="utf-8",
)


# ============================================================
# 7. SNAPSHOT-BASED RECEIPT
# ============================================================

RECEIPT.write_text(
r'''
{% extends "orders/documents/base.html" %}


{% block document_content %}

<header class="header">

    <div class="brand">

        <h1>
            {{ snapshot.store.name }}
        </h1>

        {% if snapshot.store.address %}
            <p>{{ snapshot.store.address }}</p>
        {% endif %}

        {% if snapshot.store.phone %}
            <p>{{ snapshot.store.phone }}</p>
        {% endif %}

        {% if snapshot.store.email %}
            <p>{{ snapshot.store.email }}</p>
        {% endif %}

    </div>


    <div class="document-meta">

        <h2>Receipt</h2>

        <p>
            <strong>
                {{ document.document_number }}
            </strong>
        </p>

        <p>
            Order:
            {{ snapshot.order.order_number }}
        </p>

        <p>
            Issued:
            {{ document.issued_at|date:"d M Y H:i" }}
        </p>

        <span class="status">
            {{ snapshot.order.payment_status_display }}
        </span>

    </div>

</header>


<section class="grid">

    <div class="info-block">

        <h3 class="section-title">
            Received From
        </h3>

        <p>
            <strong>
                {{ snapshot.order.full_name }}
            </strong>
        </p>

        <p>
            {{ snapshot.order.phone }}
        </p>

        {% if snapshot.order.email %}
            <p>{{ snapshot.order.email }}</p>
        {% endif %}

    </div>


    <div class="info-block">

        <h3 class="section-title">
            Payment Details
        </h3>

        <p>
            Method:
            {{ snapshot.order.payment_method|upper }}
        </p>


        {% if snapshot.payment %}

            {% if snapshot.payment.mpesa_receipt_number %}

                <p>

                    M-PESA Receipt:

                    <strong>
                        {{ snapshot.payment.mpesa_receipt_number }}
                    </strong>

                </p>

            {% endif %}


            <p>
                Payment Phone:
                {{ snapshot.payment.phone_number }}
            </p>

            <p>
                Payment Amount:
                KES {{ snapshot.payment.amount }}
            </p>

        {% endif %}

    </div>

</section>


<table>

    <thead>

        <tr>

            <th>Item</th>

            <th class="text-right">
                Price
            </th>

            <th class="text-right">
                Qty
            </th>

            <th class="text-right">
                Amount
            </th>

        </tr>

    </thead>


    <tbody>

        {% for item in snapshot.items %}

            <tr>

                <td>

                    <strong>
                        {{ item.product_name }}
                    </strong>

                    {% if item.variant_name %}

                        <div class="small">
                            {{ item.variant_name }}
                        </div>

                    {% endif %}

                </td>

                <td class="text-right">
                    KES {{ item.price }}
                </td>

                <td class="text-right">
                    {{ item.quantity }}
                </td>

                <td class="text-right">
                    KES {{ item.subtotal }}
                </td>

            </tr>

        {% endfor %}

    </tbody>

</table>


<div class="totals">

    <div class="total-row">

        <span>Order Total</span>

        <strong>
            KES {{ snapshot.order.total_amount }}
        </strong>

    </div>


    {% if snapshot.refund_total != "0.00" %}

        <div class="total-row refund-row">

            <span>Refunded</span>

            <strong>
                - KES {{ snapshot.refund_total }}
            </strong>

        </div>


        <div class="total-row grand-total">

            <span>Net Amount</span>

            <span>
                KES {{ snapshot.net_amount }}
            </span>

        </div>

    {% else %}

        <div class="total-row grand-total">

            <span>Amount Paid</span>

            <span>
                KES {{ snapshot.order.total_amount }}
            </span>

        </div>

    {% endif %}

</div>


{% if snapshot.refunds %}

    <div class="payment-box">

        <h3>
            Refund History
        </h3>


        {% for refund in snapshot.refunds %}

            <p>

                KES {{ refund.amount }}

                {% if refund.external_reference %}

                    —
                    Ref:
                    {{ refund.external_reference }}

                {% endif %}

            </p>

        {% endfor %}

    </div>

{% endif %}


<div class="footer">

    <p>
        Payment receipt for order
        {{ snapshot.order.order_number }}.
    </p>

    <p>
        Thank you for shopping with
        {{ snapshot.store.name }}.
    </p>

</div>

{% endblock %}
'''.strip() + "\n",
encoding="utf-8",
)


print(
    "Invoice and receipt templates now "
    "render immutable snapshots."
)


# ============================================================
# 8. TESTS
# ============================================================

TESTS.write_text(
r'''
from decimal import Decimal

from django.contrib.auth import (
    get_user_model,
)

from django.core import mail

from django.test import TestCase

from django.urls import reverse

from categories.models import Category

from orders.models import (
    Order,
    OrderDocument,
    OrderItem,
)

from payments.models import (
    MpesaTransaction,
)

from products.models import Product


User = get_user_model()


class Phase10BImmutableDocumentTests(
    TestCase
):

    def setUp(self):

        self.customer = (
            User.objects.create_user(
                username="phase10bcustomer",
                password="pass12345",
                email="phase10b@example.com",
                role=User.CUSTOMER,
            )
        )

        self.other = (
            User.objects.create_user(
                username="phase10bother",
                password="pass12345",
                role=User.CUSTOMER,
            )
        )

        self.staff = (
            User.objects.create_user(
                username="phase10bstaff",
                password="pass12345",
                role=User.ADMIN,
                is_staff=True,
            )
        )

        self.category = (
            Category.objects.create(
                name="Phase 10B",
                slug="phase-10b",
            )
        )

        self.product = (
            Product.objects.create(
                category=self.category,
                name="Original Laptop Name",
                slug="phase-10b-laptop",
                sku="P10B-001",
                price=Decimal(
                    "60000.00"
                ),
                cost_price=Decimal(
                    "45000.00"
                ),
                stock=10,
                reserved_stock=0,
                is_active=True,
            )
        )

        self.order = (
            Order.objects.create(
                user=self.customer,
                order_number="PHASE10B-001",
                full_name="Original Customer",
                phone="0712345678",
                email="customer@example.com",
                county="Nairobi",
                city="Nairobi",
                estate="CBD",
                house_number="10",
                subtotal=Decimal(
                    "60000.00"
                ),
                shipping_cost=Decimal(
                    "500.00"
                ),
                discount=Decimal(
                    "0.00"
                ),
                total_amount=Decimal(
                    "60500.00"
                ),
                status="delivered",
                payment_status="paid",
                inventory_status="consumed",
                payment_method="mpesa",
            )
        )

        self.item = (
            OrderItem.objects.create(
                order=self.order,
                product=self.product,
                product_name=(
                    "Original Laptop Name"
                ),
                price=Decimal(
                    "60000.00"
                ),
                unit_cost_at_sale=Decimal(
                    "45000.00"
                ),
                cost_subtotal_at_sale=Decimal(
                    "45000.00"
                ),
                quantity=1,
                subtotal=Decimal(
                    "60000.00"
                ),
            )
        )

        MpesaTransaction.objects.create(
            order=self.order,
            phone_number="254712345678",
            amount=Decimal(
                "60500.00"
            ),
            mpesa_receipt_number=(
                "P10B-MPESA"
            ),
            status="success",
        )


    def test_invoice_creates_persistent_document(
        self
    ):

        self.client.login(
            username="phase10bcustomer",
            password="pass12345",
        )

        response = self.client.get(
            reverse(
                "customer_order_invoice",
                args=[
                    self.order.order_number
                ],
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        document = (
            OrderDocument.objects.get(
                order=self.order,
                document_type="invoice",
            )
        )

        self.assertEqual(
            document.document_number,
            "INV-PHASE10B-001",
        )


    def test_second_view_reuses_same_document(
        self
    ):

        self.client.login(
            username="phase10bcustomer",
            password="pass12345",
        )

        url = reverse(
            "customer_order_invoice",
            args=[
                self.order.order_number
            ],
        )

        self.client.get(url)
        self.client.get(url)

        self.assertEqual(
            OrderDocument.objects
            .filter(
                order=self.order,
                document_type="invoice",
            )
            .count(),
            1,
        )


    def test_snapshot_does_not_change_after_order_edit(
        self
    ):

        self.client.login(
            username="phase10bcustomer",
            password="pass12345",
        )

        url = reverse(
            "customer_order_invoice",
            args=[
                self.order.order_number
            ],
        )

        self.client.get(url)

        self.order.full_name = (
            "Changed Customer"
        )

        self.order.total_amount = Decimal(
            "99999.00"
        )

        self.order.save()

        self.item.product_name = (
            "Changed Product Name"
        )

        self.item.save(
            update_fields=[
                "product_name",
            ]
        )

        response = self.client.get(
            url
        )

        self.assertContains(
            response,
            "Original Customer",
        )

        self.assertContains(
            response,
            "Original Laptop Name",
        )

        self.assertContains(
            response,
            "60500.00",
        )

        self.assertNotContains(
            response,
            "Changed Customer",
        )

        self.assertNotContains(
            response,
            "Changed Product Name",
        )


    def test_receipt_snapshot_contains_mpesa_reference(
        self
    ):

        self.client.login(
            username="phase10bcustomer",
            password="pass12345",
        )

        response = self.client.get(
            reverse(
                "customer_order_receipt",
                args=[
                    self.order.order_number
                ],
            )
        )

        self.assertContains(
            response,
            "P10B-MPESA",
        )

        document = (
            OrderDocument.objects.get(
                order=self.order,
                document_type="receipt",
            )
        )

        self.assertEqual(
            document.snapshot[
                "payment"
            ][
                "mpesa_receipt_number"
            ],
            "P10B-MPESA",
        )


    def test_customer_cannot_access_other_document(
        self
    ):

        self.client.login(
            username="phase10bother",
            password="pass12345",
        )

        response = self.client.get(
            reverse(
                "customer_order_invoice",
                args=[
                    self.order.order_number
                ],
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )


    def test_customer_can_email_own_invoice(
        self
    ):

        self.client.login(
            username="phase10bcustomer",
            password="pass12345",
        )

        # Issue document first.
        self.client.get(
            reverse(
                "customer_order_invoice",
                args=[
                    self.order.order_number
                ],
            )
        )

        response = self.client.post(
            reverse(
                "customer_order_document_email",
                args=[
                    self.order.order_number,
                    "invoice",
                ],
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            len(
                mail.outbox
            ),
            1,
        )

        self.assertEqual(
            mail.outbox[0].to,
            [
                "customer@example.com"
            ],
        )

        document = (
            OrderDocument.objects.get(
                order=self.order,
                document_type="invoice",
            )
        )

        self.assertEqual(
            document.email_count,
            1,
        )

        self.assertIsNotNone(
            document.last_emailed_at,
        )
'''.strip() + "\n",
encoding="utf-8",
)


print(
    "Phase 10B tests created."
)


print()
print("=" * 72)
print(
    "PHASE 10B IMMUTABLE DOCUMENTS INSTALLED"
)
print("=" * 72)
print()
print("Added:")
print("  Persistent invoice record")
print("  Persistent receipt record")
print("  Immutable JSON snapshots")
print("  Frozen customer details")
print("  Frozen item details")
print("  Frozen payment reference")
print("  Frozen refund state")
print("  Document issuance audit")
print("  Email delivery audit")
print("  Customer email delivery")
print("  Admin email delivery")
print()
print("Migration required.")
