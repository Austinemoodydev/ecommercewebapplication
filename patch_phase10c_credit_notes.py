from pathlib import Path
import shutil


ROOT = Path.cwd()

MODELS = ROOT / "orders" / "models.py"
SERVICE = ROOT / "orders" / "credit_note_service.py"
VIEWS = ROOT / "orders" / "credit_note_views.py"
URLS = ROOT / "dashboard" / "urls.py"

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

CREDIT_TEMPLATE = (
    DOC_DIR
    / "credit_note.html"
)

TESTS = (
    ROOT
    / "dashboard"
    / "test_phase10c.py"
)


# ============================================================
# BACKUPS
# ============================================================

for path in [
    MODELS,
    URLS,
    ADMIN_DETAIL,
]:

    if not path.exists():
        raise RuntimeError(
            f"Missing required file: {path}"
        )

    backup = Path(
        str(path)
        + ".phase10cbackup"
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
# 1. CREDIT NOTE MODEL
# ============================================================

text = MODELS.read_text(
    encoding="utf-8-sig"
)


if "class CreditNoteDocument(" not in text:

    text += r'''


class CreditNoteDocument(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name="credit_notes",
    )

    refund_request = models.OneToOneField(
        "payments.RefundRequest",
        on_delete=models.PROTECT,
        related_name="credit_note",
    )

    document_number = models.CharField(
        max_length=140,
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
        related_name="issued_credit_notes",
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


    def __str__(self):

        return (
            f"{self.document_number} "
            f"- {self.order.order_number}"
        )
'''


MODELS.write_text(
    text,
    encoding="utf-8",
)

print(
    "CreditNoteDocument model added."
)


# ============================================================
# 2. CREDIT NOTE SERVICE
# ============================================================

SERVICE.write_text(
r'''
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
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Credit note service created."
)


# ============================================================
# 3. CREDIT NOTE VIEWS
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

from orders.credit_note_service import (
    get_or_issue_credit_note,
)

from orders.models import (
    CreditNoteDocument,
)

from payments.models import (
    RefundRequest,
)


def _render_credit_note(
    request,
    document,
):

    return render(
        request,
        "orders/documents/credit_note.html",
        {
            "document":
                document,

            "snapshot":
                document.snapshot,

            "order":
                document.order,
        },
    )


def _customer_refund(
    request,
    refund_id,
):

    return get_object_or_404(
        RefundRequest.objects
        .select_related(
            "order",
            "processed_by",
        ),
        pk=refund_id,
        order__user=request.user,
        status="processed",
    )


def _admin_refund(
    refund_id,
):

    return get_object_or_404(
        RefundRequest.objects
        .select_related(
            "order",
            "processed_by",
        ),
        pk=refund_id,
        status="processed",
    )


@login_required
def customer_credit_note(
    request,
    refund_id,
):

    refund = _customer_refund(
        request,
        refund_id,
    )


    try:

        document = (
            get_or_issue_credit_note(
                refund=refund,
                issued_by=request.user,
            )
        )

    except ValueError:
        raise Http404


    return _render_credit_note(
        request,
        document,
    )


@staff_member_required
def admin_credit_note(
    request,
    refund_id,
):

    refund = _admin_refund(
        refund_id
    )


    try:

        document = (
            get_or_issue_credit_note(
                refund=refund,
                issued_by=request.user,
            )
        )

    except ValueError:
        raise Http404


    return _render_credit_note(
        request,
        document,
    )


def _credit_note_url(
    request,
    document,
):

    from django.urls import reverse


    route = (
        "admin_credit_note"
        if request.user.is_staff
        else "customer_credit_note"
    )


    return reverse(
        route,
        args=[
            document.refund_request_id
        ],
    )


def _send_credit_note_email(
    request,
    document,
):

    snapshot = document.snapshot

    recipient = (
        snapshot[
            "order"
        ]
        .get(
            "email",
            "",
        )
        .strip()
    )


    if not recipient:

        messages.error(
            request,
            "This order has no customer "
            "email address.",
        )

        return


    url = (
        request.build_absolute_uri(
            _credit_note_url(
                request,
                document,
            )
        )
    )


    subject = (
        f"Credit Note "
        f"{document.document_number}"
    )


    body = (
        f"Hello "
        f"{snapshot['order']['full_name']},\n\n"

        f"A refund credit note has been "
        f"issued for order "
        f"{snapshot['order']['order_number']}.\n\n"

        f"Credit note: "
        f"{document.document_number}\n"

        f"Refund amount: KES "
        f"{snapshot['refund']['amount']}\n"

        f"Refund reference: "
        f"{snapshot['refund']['external_reference']}\n\n"

        f"View credit note:\n"
        f"{url}\n"
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
        CreditNoteDocument.objects
        .filter(
            pk=document.pk
        )
        .update(
            email_count=(
                F("email_count")
                + 1
            ),

            last_emailed_at=(
                timezone.now()
            ),
        )
    )


    messages.success(
        request,
        "Credit note emailed successfully.",
    )


@login_required
@require_POST
def customer_credit_note_email(
    request,
    refund_id,
):

    refund = _customer_refund(
        request,
        refund_id,
    )


    try:

        document = (
            get_or_issue_credit_note(
                refund=refund,
                issued_by=request.user,
            )
        )

    except ValueError:
        raise Http404


    _send_credit_note_email(
        request,
        document,
    )


    return redirect(
        _credit_note_url(
            request,
            document,
        )
    )


@staff_member_required
@require_POST
def admin_credit_note_email(
    request,
    refund_id,
):

    refund = _admin_refund(
        refund_id
    )


    try:

        document = (
            get_or_issue_credit_note(
                refund=refund,
                issued_by=request.user,
            )
        )

    except ValueError:
        raise Http404


    _send_credit_note_email(
        request,
        document,
    )


    return redirect(
        _credit_note_url(
            request,
            document,
        )
    )
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Credit note views created."
)


# ============================================================
# 4. URLS
# ============================================================

text = URLS.read_text(
    encoding="utf-8-sig"
)


if (
    "from orders import credit_note_views"
    not in text
):

    marker = (
        "from orders import document_views\n"
    )

    if marker not in text:

        raise RuntimeError(
            "Could not locate document_views import."
        )

    text = text.replace(
        marker,
        marker
        + "from orders import credit_note_views\n",
        1,
    )


if 'name="customer_credit_note"' not in text:

    marker = '''    path(
        "orders/<str:order_number>/documents/<str:document_type>/email/",
        document_views.customer_document_email,
        name="customer_order_document_email",
    ),
'''

    addition = marker + '''
    path(
        "credit-notes/<int:refund_id>/",
        credit_note_views.customer_credit_note,
        name="customer_credit_note",
    ),

    path(
        "credit-notes/<int:refund_id>/email/",
        credit_note_views.customer_credit_note_email,
        name="customer_credit_note_email",
    ),
'''

    if marker not in text:

        raise RuntimeError(
            "Could not locate customer "
            "document email route."
        )

    text = text.replace(
        marker,
        addition,
        1,
    )


if 'name="admin_credit_note"' not in text:

    marker = '''    path(
        "admin/orders/<str:order_number>/documents/<str:document_type>/email/",
        document_views.admin_document_email,
        name="admin_order_document_email",
    ),
'''

    addition = marker + '''
    path(
        "admin/credit-notes/<int:refund_id>/",
        credit_note_views.admin_credit_note,
        name="admin_credit_note",
    ),

    path(
        "admin/credit-notes/<int:refund_id>/email/",
        credit_note_views.admin_credit_note_email,
        name="admin_credit_note_email",
    ),
'''

    if marker not in text:

        raise RuntimeError(
            "Could not locate admin "
            "document email route."
        )

    text = text.replace(
        marker,
        addition,
        1,
    )


URLS.write_text(
    text,
    encoding="utf-8",
)

print(
    "Credit note routes added."
)


# ============================================================
# 5. CREDIT NOTE TEMPLATE
# ============================================================

CREDIT_TEMPLATE.write_text(
r'''
{% extends "orders/documents/base.html" %}


{% block document_content %}

<header class="header">

    <div class="brand">

        <h1>
            {{ snapshot.store.name }}
        </h1>

        {% if snapshot.store.address %}
            <p>
                {{ snapshot.store.address }}
            </p>
        {% endif %}

        {% if snapshot.store.phone %}
            <p>
                {{ snapshot.store.phone }}
            </p>
        {% endif %}

        {% if snapshot.store.email %}
            <p>
                {{ snapshot.store.email }}
            </p>
        {% endif %}

    </div>


    <div class="document-meta">

        <h2>
            Credit Note
        </h2>

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
            Refund Processed
        </span>

    </div>

</header>


<section class="grid">

    <div class="info-block">

        <h3 class="section-title">
            Customer
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
            <p>
                {{ snapshot.order.email }}
            </p>
        {% endif %}

    </div>


    <div class="info-block">

        <h3 class="section-title">
            Refund Details
        </h3>

        <p>
            Reference:
            <strong>
                {{ snapshot.refund.external_reference }}
            </strong>
        </p>

        {% if snapshot.refund.reason %}

            <p>
                Reason:
                {{ snapshot.refund.reason }}
            </p>

        {% endif %}

        {% if snapshot.refund.processed_by %}

            <p>
                Processed by:
                {{ snapshot.refund.processed_by }}
            </p>

        {% endif %}

    </div>

</section>


<div class="payment-box">

    <h3>
        Financial Summary
    </h3>


    <div class="total-row">

        <span>
            Original Order Amount
        </span>

        <strong>
            KES
            {{ snapshot.order.total_amount }}
        </strong>

    </div>


    <div class="total-row refund-row">

        <span>
            This Refund
        </span>

        <strong>
            - KES
            {{ snapshot.refund.amount }}
        </strong>

    </div>


    <div class="total-row">

        <span>
            Total Refunds Processed
        </span>

        <strong>
            KES
            {{ snapshot.total_processed_refunds }}
        </strong>

    </div>


    <div class="total-row grand-total">

        <span>
            Net Amount Retained
        </span>

        <span>
            KES
            {{ snapshot.remaining_amount }}
        </span>

    </div>

</div>


{% if snapshot.items %}

<table>

    <thead>

        <tr>
            <th>Original Order Item</th>
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

                    {{ item.product_name }}

                    {% if item.variant_name %}

                        <div class="small">
                            {{ item.variant_name }}
                        </div>

                    {% endif %}

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

{% endif %}


<div class="payment-box">

    <p class="mb-0">

        This credit note records a processed
        refund against order
        <strong>
            {{ snapshot.order.order_number }}
        </strong>.

    </p>

</div>


<div class="footer">

    <p>
        Credit note
        {{ document.document_number }}
    </p>

    <p>
        {{ snapshot.store.name }}
    </p>

</div>

{% endblock %}
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Credit note template created."
)


# ============================================================
# 6. ADMIN DOCUMENT HISTORY
# ============================================================

text = ADMIN_DETAIL.read_text(
    encoding="utf-8-sig"
)


if "Financial Document History" not in text:

    marker = '''
<!-- STATUS -->
'''

    block = r'''
<!-- FINANCIAL DOCUMENT HISTORY -->

<div class="dashboard-card mb-4">

    <div
        class="
            d-flex
            justify-content-between
            align-items-center
            flex-wrap
            gap-2
            mb-3
        "
    >

        <div>

            <h2 class="h5 mb-1">
                Financial Document History
            </h2>

            <div class="text-muted small">
                Immutable invoices, receipts and refund documents
            </div>

        </div>

    </div>


    <div class="table-responsive">

        <table class="table align-middle mb-0">

            <thead>

                <tr>
                    <th>Document</th>
                    <th>Number</th>
                    <th>Issued</th>
                    <th>Email Count</th>
                    <th class="text-end">
                        Action
                    </th>
                </tr>

            </thead>


            <tbody>

                {% for document in order.documents.all %}

                    <tr>

                        <td>
                            {{ document.get_document_type_display }}
                        </td>

                        <td>
                            {{ document.document_number }}
                        </td>

                        <td>
                            {{ document.issued_at|date:"d M Y H:i" }}
                        </td>

                        <td>
                            {{ document.email_count }}
                        </td>

                        <td class="text-end">

                            {% if document.document_type == "invoice" %}

                                <a
                                    href="{% url 'admin_order_invoice' order.order_number %}"
                                    class="btn btn-sm btn-outline-primary"
                                    target="_blank"
                                >
                                    Open
                                </a>

                            {% else %}

                                <a
                                    href="{% url 'admin_order_receipt' order.order_number %}"
                                    class="btn btn-sm btn-outline-success"
                                    target="_blank"
                                >
                                    Open
                                </a>

                            {% endif %}

                        </td>

                    </tr>

                {% empty %}

                    <tr>

                        <td
                            colspan="5"
                            class="text-muted text-center py-4"
                        >
                            No invoice or receipt has been issued yet.
                        </td>

                    </tr>

                {% endfor %}


                {% for credit_note in order.credit_notes.all %}

                    <tr>

                        <td>
                            Credit Note
                        </td>

                        <td>
                            {{ credit_note.document_number }}
                        </td>

                        <td>
                            {{ credit_note.issued_at|date:"d M Y H:i" }}
                        </td>

                        <td>
                            {{ credit_note.email_count }}
                        </td>

                        <td class="text-end">

                            <a
                                href="{% url 'admin_credit_note' credit_note.refund_request_id %}"
                                class="btn btn-sm btn-outline-danger"
                                target="_blank"
                            >
                                Open
                            </a>

                        </td>

                    </tr>

                {% endfor %}

            </tbody>

        </table>

    </div>

</div>


'''

    if marker not in text:

        raise RuntimeError(
            "Could not locate STATUS marker "
            "in admin order detail."
        )

    text = text.replace(
        marker,
        block + marker,
        1,
    )


ADMIN_DETAIL.write_text(
    text,
    encoding="utf-8",
)

print(
    "Admin document history added."
)


# ============================================================
# 7. TESTS
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
    CreditNoteDocument,
    Order,
    OrderDocument,
    OrderItem,
)

from payments.models import (
    RefundRequest,
)

from products.models import Product


User = get_user_model()


class Phase10CCreditNoteTests(
    TestCase
):

    def setUp(self):

        self.customer = (
            User.objects.create_user(
                username="phase10ccustomer",
                password="pass12345",
                role=User.CUSTOMER,
            )
        )


        self.other = (
            User.objects.create_user(
                username="phase10cother",
                password="pass12345",
                role=User.CUSTOMER,
            )
        )


        self.staff = (
            User.objects.create_user(
                username="phase10cstaff",
                password="pass12345",
                role=User.ADMIN,
                is_staff=True,
            )
        )


        self.category = (
            Category.objects.create(
                name="Phase 10C",
                slug="phase-10c",
            )
        )


        self.product = (
            Product.objects.create(
                category=self.category,
                name="Refund Laptop",
                slug="refund-laptop",
                sku="P10C-001",
                price=Decimal(
                    "50000.00"
                ),
                cost_price=Decimal(
                    "40000.00"
                ),
                stock=5,
                reserved_stock=0,
                is_active=True,
            )
        )


        self.order = (
            Order.objects.create(
                user=self.customer,
                order_number="PHASE10C-001",
                full_name="Refund Customer",
                phone="0712345678",
                email="refund@example.com",
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
                payment_status=(
                    "partially_refunded"
                ),
                inventory_status="consumed",
                payment_method="mpesa",
            )
        )


        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name="Refund Laptop",
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


        self.refund = (
            RefundRequest.objects.create(
                order=self.order,
                amount=Decimal(
                    "5000.00"
                ),
                reason="Partial return",
                status="processed",
                external_reference=(
                    "REFUND-P10C-001"
                ),
                processed_by=self.staff,
            )
        )


    def test_processed_refund_can_issue_credit_note(
        self
    ):

        self.client.login(
            username="phase10ccustomer",
            password="pass12345",
        )


        response = self.client.get(
            reverse(
                "customer_credit_note",
                args=[
                    self.refund.pk
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        document = (
            CreditNoteDocument.objects.get(
                refund_request=self.refund
            )
        )


        self.assertEqual(
            document.snapshot[
                "refund"
            ][
                "amount"
            ],
            "5000.00",
        )


    def test_credit_note_is_idempotent(
        self
    ):

        self.client.login(
            username="phase10ccustomer",
            password="pass12345",
        )


        url = reverse(
            "customer_credit_note",
            args=[
                self.refund.pk
            ],
        )


        self.client.get(url)
        self.client.get(url)


        self.assertEqual(
            CreditNoteDocument.objects
            .filter(
                refund_request=self.refund
            )
            .count(),
            1,
        )


    def test_other_customer_cannot_view_credit_note(
        self
    ):

        self.client.login(
            username="phase10cother",
            password="pass12345",
        )


        response = self.client.get(
            reverse(
                "customer_credit_note",
                args=[
                    self.refund.pk
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            404,
        )


    def test_unprocessed_refund_has_no_credit_note(
        self
    ):

        pending = (
            RefundRequest.objects.create(
                order=self.order,
                amount=Decimal(
                    "1000.00"
                ),
                reason="Pending refund",
                status="requested",
            )
        )


        self.client.login(
            username="phase10ccustomer",
            password="pass12345",
        )


        response = self.client.get(
            reverse(
                "customer_credit_note",
                args=[
                    pending.pk
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            404,
        )


    def test_credit_note_email(
        self
    ):

        self.client.login(
            username="phase10ccustomer",
            password="pass12345",
        )


        response = self.client.post(
            reverse(
                "customer_credit_note_email",
                args=[
                    self.refund.pk
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


        document = (
            CreditNoteDocument.objects.get(
                refund_request=self.refund
            )
        )


        document.refresh_from_db()


        self.assertEqual(
            document.email_count,
            1,
        )


    def test_existing_receipt_snapshot_is_not_rewritten(
        self
    ):

        receipt = (
            OrderDocument.objects.create(
                order=self.order,
                document_type="receipt",
                document_number=(
                    "RCP-PHASE10C-001"
                ),
                snapshot={
                    "refund_total": "0.00",
                    "net_amount": "50500.00",
                },
                issued_by=self.customer,
            )
        )


        self.client.login(
            username="phase10ccustomer",
            password="pass12345",
        )


        self.client.get(
            reverse(
                "customer_credit_note",
                args=[
                    self.refund.pk
                ],
            )
        )


        receipt.refresh_from_db()


        self.assertEqual(
            receipt.snapshot[
                "refund_total"
            ],
            "0.00",
        )

        self.assertEqual(
            receipt.snapshot[
                "net_amount"
            ],
            "50500.00",
        )
'''.strip() + "\n",
encoding="utf-8",
)


print(
    "Phase 10C tests created."
)


print()
print("=" * 72)
print("PHASE 10C CREDIT NOTES INSTALLED")
print("=" * 72)
print()
print("Added:")
print("  One credit note per processed refund")
print("  Immutable refund snapshots")
print("  Refund document numbering")
print("  Customer ownership protection")
print("  Staff access")
print("  Credit note email delivery")
print("  Email audit count")
print("  Admin financial document history")
print("  Original receipt remains immutable")
print()
print("Migration required.")
