from pathlib import Path
import shutil

ROOT = Path.cwd()

DOC_VIEWS = ROOT / "orders" / "document_views.py"

DASHBOARD_URLS = ROOT / "dashboard" / "urls.py"

CUSTOMER_DETAIL = (
    ROOT
    / "templates"
    / "dashboard"
    / "order_detail.html"
)

ADMIN_DETAIL = (
    ROOT
    / "templates"
    / "dashboard"
    / "admin"
    / "orders"
    / "detail.html"
)

DOC_DIR = (
    ROOT
    / "templates"
    / "orders"
    / "documents"
)

BASE_TEMPLATE = DOC_DIR / "base.html"
INVOICE_TEMPLATE = DOC_DIR / "invoice.html"
RECEIPT_TEMPLATE = DOC_DIR / "receipt.html"

TEST_FILE = (
    ROOT
    / "dashboard"
    / "test_phase10.py"
)


# ============================================================
# BACKUPS
# ============================================================

for path in [
    DASHBOARD_URLS,
    CUSTOMER_DETAIL,
    ADMIN_DETAIL,
]:

    if not path.exists():
        raise RuntimeError(
            f"Required file missing: {path}"
        )

    backup = Path(
        str(path)
        + ".phase10backup"
    )

    if not backup.exists():
        shutil.copy2(
            path,
            backup,
        )


DOC_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# 1. DOCUMENT VIEWS
# ============================================================

DOC_VIEWS.write_text(
r'''
from decimal import Decimal

from django.conf import settings
from django.contrib.admin.views.decorators import (
    staff_member_required,
)
from django.contrib.auth.decorators import (
    login_required,
)
from django.db.models import Sum
from django.http import Http404
from django.shortcuts import (
    get_object_or_404,
    render,
)

from orders.models import Order


ZERO = Decimal("0.00")


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
            "delivery",
            "delivery__provider",
            "delivery_zone",
        )
        .prefetch_related(
            "items__product",
            "items__variant",
            "mpesa_transactions",
            "refund_requests",
        )
    )


def _store_details():

    return {
        "store_name": getattr(
            settings,
            "STORE_NAME",
            "Online Shop",
        ),

        "store_email": getattr(
            settings,
            "STORE_EMAIL",
            "",
        ),

        "store_phone": getattr(
            settings,
            "STORE_PHONE",
            "",
        ),

        "store_address": getattr(
            settings,
            "STORE_ADDRESS",
            "",
        ),

        "store_website": getattr(
            settings,
            "STORE_WEBSITE",
            "",
        ),
    }


def _build_document_context(
    order,
    document_type,
):

    items = order.items.all()

    successful_payment = (
        order.mpesa_transactions
        .filter(
            status="success",
        )
        .order_by(
            "-updated_at"
        )
        .first()
    )


    processed_refunds = (
        order.refund_requests
        .filter(
            status="processed",
        )
        .order_by(
            "processed_at",
            "created_at",
        )
    )


    processed_refund_total = (
        processed_refunds
        .aggregate(
            total=Sum(
                "amount"
            )
        )[
            "total"
        ]
        or ZERO
    )


    net_amount = (
        order.total_amount
        - processed_refund_total
    )


    if net_amount < ZERO:
        net_amount = ZERO


    context = {
        "order": order,
        "items": items,
        "document_type": document_type,

        "successful_payment":
            successful_payment,

        "processed_refunds":
            processed_refunds,

        "processed_refund_total":
            processed_refund_total,

        "net_amount":
            net_amount,

        **_store_details(),
    }


    if document_type == "invoice":

        context[
            "document_number"
        ] = (
            f"INV-{order.order_number}"
        )

        context[
            "document_title"
        ] = "Invoice"


    elif document_type == "receipt":

        context[
            "document_number"
        ] = (
            f"RCP-{order.order_number}"
        )

        context[
            "document_title"
        ] = "Payment Receipt"


    return context


def _render_document(
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


    template = (
        "orders/documents/"
        f"{document_type}.html"
    )


    return render(
        request,
        template,
        _build_document_context(
            order,
            document_type,
        ),
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

    return _render_document(
        request,
        order,
        "invoice",
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

    return _render_document(
        request,
        order,
        "receipt",
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

    return _render_document(
        request,
        order,
        "invoice",
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

    return _render_document(
        request,
        order,
        "receipt",
    )
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Document views created."
)


# ============================================================
# 2. URLS
# ============================================================

text = DASHBOARD_URLS.read_text(
    encoding="utf-8-sig"
)


if (
    "from orders import document_views"
    not in text
):

    marker = (
        "from . import reports_views\n"
    )

    if marker not in text:
        raise RuntimeError(
            "Could not locate dashboard "
            "URL imports."
        )

    text = text.replace(
        marker,
        marker
        + "from orders import document_views\n",
        1,
    )


if 'name="customer_order_invoice"' not in text:

    marker = '''    path(
        "orders/<str:order_number>/",
        views.order_detail,
        name="order_detail",
    ),
'''

    addition = '''    path(
        "orders/<str:order_number>/",
        views.order_detail,
        name="order_detail",
    ),

    path(
        "orders/<str:order_number>/invoice/",
        document_views.customer_invoice,
        name="customer_order_invoice",
    ),

    path(
        "orders/<str:order_number>/receipt/",
        document_views.customer_receipt,
        name="customer_order_receipt",
    ),
'''

    if marker not in text:
        raise RuntimeError(
            "Could not locate customer "
            "order detail route."
        )

    text = text.replace(
        marker,
        addition,
        1,
    )


if 'name="admin_order_invoice"' not in text:

    marker = '''    path(
        "admin/orders/<str:order_number>/",
        views.admin_order_detail,
        name="admin_order_detail",
    ),
'''

    addition = '''    path(
        "admin/orders/<str:order_number>/",
        views.admin_order_detail,
        name="admin_order_detail",
    ),

    path(
        "admin/orders/<str:order_number>/invoice/",
        document_views.admin_invoice,
        name="admin_order_invoice",
    ),

    path(
        "admin/orders/<str:order_number>/receipt/",
        document_views.admin_receipt,
        name="admin_order_receipt",
    ),
'''

    if marker not in text:
        raise RuntimeError(
            "Could not locate admin "
            "order detail route."
        )

    text = text.replace(
        marker,
        addition,
        1,
    )


DASHBOARD_URLS.write_text(
    text,
    encoding="utf-8",
)

print(
    "Invoice and receipt URLs added."
)


# ============================================================
# 3. PRINT DOCUMENT BASE
# ============================================================

BASE_TEMPLATE.write_text(
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
            font-family:
                Arial,
                Helvetica,
                sans-serif;
            line-height: 1.5;
        }


        .document-toolbar {
            max-width: 950px;
            margin: 24px auto 0;
            display: flex;
            justify-content: flex-end;
            gap: 10px;
            padding: 0 16px;
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


        .document-toolbar button {
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
                rgba(0, 0, 0, 0.08);
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
            letter-spacing: .05em;
            color: #6b7280;
            border-bottom: 2px solid #e5e7eb;
            padding: 12px 8px;
        }


        td {
            border-bottom: 1px solid #e5e7eb;
            padding: 14px 8px;
            vertical-align: top;
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


        .payment-box h3 {
            margin-top: 0;
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


        @media (
            max-width: 700px
        ) {

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

            .grid > div {
                margin-bottom: 24px;
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


            a {
                color: inherit;
                text-decoration: none;
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


    <button
        type="button"
        onclick="window.print()"
    >
        Print / Save PDF
    </button>

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
# 4. INVOICE TEMPLATE
# ============================================================

INVOICE_TEMPLATE.write_text(
r'''
{% extends "orders/documents/base.html" %}


{% block document_content %}


<header class="header">

    <div class="brand">

        <h1>
            {{ store_name }}
        </h1>

        {% if store_address %}
            <p>{{ store_address }}</p>
        {% endif %}

        {% if store_phone %}
            <p>{{ store_phone }}</p>
        {% endif %}

        {% if store_email %}
            <p>{{ store_email }}</p>
        {% endif %}

        {% if store_website %}
            <p>{{ store_website }}</p>
        {% endif %}

    </div>


    <div class="document-meta">

        <h2>
            Invoice
        </h2>

        <p>
            <strong>
                {{ document_number }}
            </strong>
        </p>

        <p>
            Order:
            {{ order.order_number }}
        </p>

        <p>
            Date:
            {{ order.created_at|date:"d M Y H:i" }}
        </p>

        <span class="status">
            Payment:
            {{ order.get_payment_status_display }}
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
                {{ order.full_name }}
            </strong>
        </p>

        <p>
            {{ order.phone }}
        </p>

        {% if order.email %}
            <p>{{ order.email }}</p>
        {% endif %}

    </div>


    <div class="info-block">

        <h3 class="section-title">
            Delivery Address
        </h3>

        {% if order.house_number %}
            <p>{{ order.house_number }}</p>
        {% endif %}

        {% if order.estate %}
            <p>{{ order.estate }}</p>
        {% endif %}

        <p>
            {{ order.city }},
            {{ order.county }}
        </p>

        {% if order.landmark %}
            <p>
                Landmark:
                {{ order.landmark }}
            </p>
        {% endif %}

    </div>

</section>


<table>

    <thead>

        <tr>

            <th>
                Item
            </th>

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

        {% for item in items %}

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
                    KES {{ item.price|floatformat:2 }}
                </td>

                <td class="text-right">
                    {{ item.quantity }}
                </td>

                <td class="text-right">
                    KES {{ item.subtotal|floatformat:2 }}
                </td>

            </tr>

        {% endfor %}

    </tbody>

</table>


<div class="totals">

    <div class="total-row">

        <span>
            Subtotal
        </span>

        <strong>
            KES {{ order.subtotal|floatformat:2 }}
        </strong>

    </div>


    {% if order.discount %}

        <div class="total-row">

            <span>
                Discount
            </span>

            <strong>
                - KES {{ order.discount|floatformat:2 }}
            </strong>

        </div>

    {% endif %}


    <div class="total-row">

        <span>
            Delivery
        </span>

        <strong>
            KES {{ order.shipping_cost|floatformat:2 }}
        </strong>

    </div>


    <div class="total-row grand-total">

        <span>
            Total
        </span>

        <span>
            KES {{ order.total_amount|floatformat:2 }}
        </span>

    </div>

</div>


{% if order.coupon %}

    <div class="payment-box">

        <strong>
            Promotion:
        </strong>

        Coupon
        {{ order.coupon.code }}

    </div>

{% endif %}


{% if order.delivery %}

    <div class="payment-box">

        <h3>
            Delivery Information
        </h3>

        <p>
            Method:
            {{ order.delivery.get_method_display }}
        </p>

        {% if order.delivery.provider %}

            <p>
                Provider:
                {{ order.delivery.provider.name }}
            </p>

        {% endif %}

        {% if order.delivery.transport_reference %}

            <p>
                Reference:
                {{ order.delivery.transport_reference }}
            </p>

        {% endif %}

        <p>
            Status:
            {{ order.delivery.get_status_display }}
        </p>

    </div>

{% endif %}


<div class="footer">

    <p>
        Thank you for shopping with
        {{ store_name }}.
    </p>

    <p>
        This document is generated from order
        {{ order.order_number }}.
    </p>

</div>


{% endblock %}
'''.strip() + "\n",
encoding="utf-8",
)


# ============================================================
# 5. RECEIPT TEMPLATE
# ============================================================

RECEIPT_TEMPLATE.write_text(
r'''
{% extends "orders/documents/base.html" %}


{% block document_content %}


<header class="header">

    <div class="brand">

        <h1>
            {{ store_name }}
        </h1>

        {% if store_address %}
            <p>{{ store_address }}</p>
        {% endif %}

        {% if store_phone %}
            <p>{{ store_phone }}</p>
        {% endif %}

        {% if store_email %}
            <p>{{ store_email }}</p>
        {% endif %}

    </div>


    <div class="document-meta">

        <h2>
            Receipt
        </h2>

        <p>
            <strong>
                {{ document_number }}
            </strong>
        </p>

        <p>
            Order:
            {{ order.order_number }}
        </p>

        <p>
            Date:
            {{ order.created_at|date:"d M Y H:i" }}
        </p>

        <span class="status">
            {{ order.get_payment_status_display }}
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
                {{ order.full_name }}
            </strong>
        </p>

        <p>
            {{ order.phone }}
        </p>

        {% if order.email %}
            <p>{{ order.email }}</p>
        {% endif %}

    </div>


    <div class="info-block">

        <h3 class="section-title">
            Payment Details
        </h3>

        <p>
            Method:
            {{ order.payment_method|upper }}
        </p>

        {% if successful_payment %}

            {% if successful_payment.mpesa_receipt_number %}

                <p>
                    M-PESA Receipt:
                    <strong>
                        {{ successful_payment.mpesa_receipt_number }}
                    </strong>
                </p>

            {% endif %}


            <p>
                Payment Phone:
                {{ successful_payment.phone_number }}
            </p>


            <p>
                Payment Amount:
                KES
                {{ successful_payment.amount|floatformat:2 }}
            </p>

        {% endif %}

    </div>

</section>


<table>

    <thead>

        <tr>

            <th>
                Item
            </th>

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

        {% for item in items %}

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
                    KES {{ item.price|floatformat:2 }}
                </td>

                <td class="text-right">
                    {{ item.quantity }}
                </td>

                <td class="text-right">
                    KES {{ item.subtotal|floatformat:2 }}
                </td>

            </tr>

        {% endfor %}

    </tbody>

</table>


<div class="totals">

    <div class="total-row">

        <span>
            Order Total
        </span>

        <strong>
            KES {{ order.total_amount|floatformat:2 }}
        </strong>

    </div>


    {% if processed_refund_total %}

        <div class="total-row refund-row">

            <span>
                Refunded
            </span>

            <strong>
                - KES
                {{ processed_refund_total|floatformat:2 }}
            </strong>

        </div>


        <div class="total-row grand-total">

            <span>
                Net Amount
            </span>

            <span>
                KES {{ net_amount|floatformat:2 }}
            </span>

        </div>

    {% else %}

        <div class="total-row grand-total">

            <span>
                Amount Paid
            </span>

            <span>
                KES {{ order.total_amount|floatformat:2 }}
            </span>

        </div>

    {% endif %}

</div>


{% if processed_refunds %}

    <div class="payment-box">

        <h3>
            Refund History
        </h3>


        {% for refund in processed_refunds %}

            <p>

                KES
                {{ refund.amount|floatformat:2 }}

                {% if refund.processed_at %}

                    —
                    {{ refund.processed_at|date:"d M Y H:i" }}

                {% endif %}

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
        {{ order.order_number }}.
    </p>

    <p>
        Thank you for shopping with
        {{ store_name }}.
    </p>

</div>


{% endblock %}
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Invoice and receipt templates created."
)


# ============================================================
# 6. CUSTOMER ORDER BUTTONS
# ============================================================

text = CUSTOMER_DETAIL.read_text(
    encoding="utf-8-sig"
)


if "customer_order_invoice" not in text:

    marker = '''    <a href="{% url 'order_history' %}" class="btn btn-outline-secondary btn-sm mb-4">
        &larr; Back to My Orders
    </a>
'''

    replacement = '''    <div class="d-flex gap-2 flex-wrap mb-4">

        <a
            href="{% url 'order_history' %}"
            class="btn btn-outline-secondary btn-sm"
        >
            &larr; Back to My Orders
        </a>

        <a
            href="{% url 'customer_order_invoice' order.order_number %}"
            class="btn btn-outline-primary btn-sm"
        >
            <i class="bi bi-file-earmark-text"></i>
            Invoice
        </a>

        {% if order.payment_status == "paid" or order.payment_status == "partially_refunded" or order.payment_status == "refunded" %}

            <a
                href="{% url 'customer_order_receipt' order.order_number %}"
                class="btn btn-outline-success btn-sm"
            >
                <i class="bi bi-receipt"></i>
                Receipt
            </a>

        {% endif %}

    </div>
'''

    if marker not in text:
        raise RuntimeError(
            "Could not locate customer "
            "order back button."
        )

    text = text.replace(
        marker,
        replacement,
        1,
    )


CUSTOMER_DETAIL.write_text(
    text,
    encoding="utf-8",
)

print(
    "Customer document buttons added."
)


# ============================================================
# 7. ADMIN ORDER BUTTONS
# ============================================================

text = ADMIN_DETAIL.read_text(
    encoding="utf-8-sig"
)


if "admin_order_invoice" not in text:

    marker = '''    <a
        href="{% url 'admin_order_list' %}"
        class="btn btn-outline-secondary"
    >
        <i class="bi bi-arrow-left"></i>
        Orders
    </a>
'''

    replacement = '''    <div class="d-flex gap-2 flex-wrap">

        <a
            href="{% url 'admin_order_invoice' order.order_number %}"
            class="btn btn-outline-primary"
            target="_blank"
        >
            <i class="bi bi-file-earmark-text"></i>
            Invoice
        </a>

        {% if order.payment_status == "paid" or order.payment_status == "partially_refunded" or order.payment_status == "refunded" %}

            <a
                href="{% url 'admin_order_receipt' order.order_number %}"
                class="btn btn-outline-success"
                target="_blank"
            >
                <i class="bi bi-receipt"></i>
                Receipt
            </a>

        {% endif %}

        <a
            href="{% url 'admin_order_list' %}"
            class="btn btn-outline-secondary"
        >
            <i class="bi bi-arrow-left"></i>
            Orders
        </a>

    </div>
'''

    if marker not in text:
        raise RuntimeError(
            "Could not locate admin "
            "order back button."
        )

    text = text.replace(
        marker,
        replacement,
        1,
    )


ADMIN_DETAIL.write_text(
    text,
    encoding="utf-8",
)

print(
    "Admin document buttons added."
)


# ============================================================
# 8. PHASE 10 TESTS
# ============================================================

TEST_FILE.write_text(
r'''
from decimal import Decimal

from django.contrib.auth import (
    get_user_model,
)

from django.test import TestCase

from django.urls import reverse

from categories.models import Category

from orders.models import (
    Order,
    OrderItem,
)

from payments.models import (
    MpesaTransaction,
    RefundRequest,
)

from products.models import Product


User = get_user_model()


class Phase10DocumentTests(
    TestCase
):

    def setUp(self):

        self.customer = (
            User.objects.create_user(
                username="phase10customer",
                password="pass12345",
                role=User.CUSTOMER,
            )
        )


        self.other_customer = (
            User.objects.create_user(
                username="phase10other",
                password="pass12345",
                role=User.CUSTOMER,
            )
        )


        self.staff = (
            User.objects.create_user(
                username="phase10staff",
                password="pass12345",
                role=User.ADMIN,
                is_staff=True,
            )
        )


        self.category = (
            Category.objects.create(
                name="Phase 10",
                slug="phase-10",
            )
        )


        self.product = (
            Product.objects.create(
                category=self.category,
                name="Receipt Laptop",
                slug="receipt-laptop",
                sku="P10-001",
                price=Decimal(
                    "50000.00"
                ),
                cost_price=Decimal(
                    "40000.00"
                ),
                stock=10,
                reserved_stock=0,
                is_active=True,
            )
        )


        self.order = (
            Order.objects.create(
                user=self.customer,
                order_number="PHASE10-001",
                full_name="Phase Ten Customer",
                phone="0712345678",
                email="phase10@example.com",
                county="Nairobi",
                city="Nairobi",
                estate="CBD",
                house_number="10",
                subtotal=Decimal(
                    "50000.00"
                ),
                shipping_cost=Decimal(
                    "500.00"
                ),
                discount=Decimal(
                    "0.00"
                ),
                total_amount=Decimal(
                    "50500.00"
                ),
                status="delivered",
                payment_status="paid",
                inventory_status="consumed",
                payment_method="mpesa",
            )
        )


        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=self.product.name,
            price=Decimal(
                "50000.00"
            ),
            unit_cost_at_sale=Decimal(
                "40000.00"
            ),
            cost_subtotal_at_sale=Decimal(
                "40000.00"
            ),
            quantity=1,
            subtotal=Decimal(
                "50000.00"
            ),
        )


        MpesaTransaction.objects.create(
            order=self.order,
            phone_number="254712345678",
            amount=Decimal(
                "50500.00"
            ),
            mpesa_receipt_number="TESTP10MPESA",
            status="success",
        )


    def test_customer_can_view_own_invoice(
        self
    ):

        self.client.login(
            username="phase10customer",
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

        self.assertContains(
            response,
            "INV-PHASE10-001",
        )

        self.assertContains(
            response,
            "Receipt Laptop",
        )


    def test_customer_cannot_view_another_customer_invoice(
        self
    ):

        self.client.login(
            username="phase10other",
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


    def test_customer_receipt_contains_mpesa_reference(
        self
    ):

        self.client.login(
            username="phase10customer",
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


        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "TESTP10MPESA",
        )


    def test_unpaid_order_has_no_receipt(
        self
    ):

        self.order.payment_status = (
            "pending"
        )

        self.order.save(
            update_fields=[
                "payment_status",
                "updated_at",
            ]
        )


        self.client.login(
            username="phase10customer",
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


        self.assertEqual(
            response.status_code,
            404,
        )


    def test_staff_can_view_admin_invoice(
        self
    ):

        self.client.login(
            username="phase10staff",
            password="pass12345",
        )


        response = self.client.get(
            reverse(
                "admin_order_invoice",
                args=[
                    self.order.order_number
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


    def test_receipt_shows_processed_refund(
        self
    ):

        RefundRequest.objects.create(
            order=self.order,
            amount=Decimal(
                "5000.00"
            ),
            reason="Test refund",
            status="processed",
            external_reference="REF-P10-001",
            processed_by=self.staff,
        )


        self.order.payment_status = (
            "partially_refunded"
        )

        self.order.save(
            update_fields=[
                "payment_status",
                "updated_at",
            ]
        )


        self.client.login(
            username="phase10customer",
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


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertContains(
            response,
            "REF-P10-001",
        )

        self.assertContains(
            response,
            "45500.00",
        )
'''.strip() + "\n",
encoding="utf-8",
)


print(
    "Phase 10 tests created."
)


print()
print("=" * 72)
print("PHASE 10A INVOICES & RECEIPTS INSTALLED")
print("=" * 72)
print()
print("Added:")
print("  Customer invoice")
print("  Customer payment receipt")
print("  Admin invoice")
print("  Admin payment receipt")
print("  A4 print layout")
print("  M-PESA receipt reference")
print("  Refund history")
print("  Net amount after refunds")
print("  Ownership protection")
print()
print("No migration required.")
