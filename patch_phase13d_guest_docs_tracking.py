from pathlib import Path
import shutil


ROOT = Path.cwd()

ORDER_URLS = ROOT / "orders" / "urls.py"
DOCUMENT_VIEWS = ROOT / "orders" / "document_views.py"
DELIVERY_VIEWS = ROOT / "delivery" / "customer_views.py"

GUEST_ORDER_TEMPLATE = (
    ROOT / "templates" / "orders" / "guest_order_detail.html"
)

TRACKING_TEMPLATE = (
    ROOT / "delivery" / "templates" / "delivery" / "customer_tracking.html"
)

DOCUMENT_BASE = (
    ROOT / "templates" / "orders" / "documents" / "base.html"
)

TEST_FILE = (
    ROOT / "orders" / "test_phase13d.py"
)


required = [
    ORDER_URLS,
    DOCUMENT_VIEWS,
    DELIVERY_VIEWS,
    GUEST_ORDER_TEMPLATE,
    TRACKING_TEMPLATE,
    DOCUMENT_BASE,
]


for path in required:
    if not path.exists():
        raise RuntimeError(
            f"Missing required file: {path}"
        )


for path in required:
    backup = Path(
        str(path) + ".phase13dbackup"
    )

    if not backup.exists():
        shutil.copy2(
            path,
            backup,
        )


# ============================================================
# 1. DELIVERY — GUEST TRACKING VIEW
# ============================================================

text = DELIVERY_VIEWS.read_text(
    encoding="utf-8-sig"
)


marker = '''from orders.models import Order
'''

replacement = '''from orders.models import Order

from orders.guest_access import (
    verify_guest_access_token,
)
'''

if (
    marker in text
    and
    "verify_guest_access_token" not in text
):

    text = text.replace(
        marker,
        replacement,
        1,
    )


if "def guest_delivery_tracking(" not in text:

    guest_view = '''

def guest_delivery_tracking(
    request,
    order_number,
    token,
):

    order = get_object_or_404(
        Order.objects.select_related(
            "user"
        ),
        order_number=order_number,
        user__isnull=True,
        guest_checkout=True,
    )


    if not verify_guest_access_token(
        order,
        token,
    ):

        from django.http import Http404

        raise Http404(
            "Order not found."
        )


    delivery = get_object_or_404(
        Delivery.objects.select_related(
            "provider",
            "order",
        ),
        order=order,
    )


    events = (
        delivery.events
        .select_related(
            "created_by"
        )
        .order_by(
            "created_at"
        )
    )


    return render(
        request,
        "delivery/customer_tracking.html",
        {
            "order": order,
            "delivery": delivery,
            "events": events,
            "is_guest_tracking": True,
            "guest_access_token": token,
        },
    )


'''

    anchor = '''@login_required
def available_delivery_options(
'''

    if anchor not in text:
        raise RuntimeError(
            "Could not locate delivery view insertion point."
        )

    text = text.replace(
        anchor,
        guest_view + anchor,
        1,
    )


DELIVERY_VIEWS.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# 2. DOCUMENT VIEWS — GUEST OWNERSHIP
# ============================================================

text = DOCUMENT_VIEWS.read_text(
    encoding="utf-8-sig"
)


marker = '''from orders.models import (
    Order,
    OrderDocument,
)
'''

replacement = '''from orders.models import (
    Order,
    OrderDocument,
)

from orders.guest_access import (
    verify_guest_access_token,
)
'''

if (
    marker in text
    and
    "verify_guest_access_token" not in text
):

    text = text.replace(
        marker,
        replacement,
        1,
    )


# ------------------------------------------------------------
# Anonymous guest document issuance must use issued_by=None.
# ------------------------------------------------------------

old = '''            issued_by=request.user,
'''

new = '''            issued_by=(
                request.user
                if request.user.is_authenticated
                else None
            ),
'''

if old in text:
    text = text.replace(
        old,
        new,
        1,
    )


# ------------------------------------------------------------
# Guest document authorization helper.
# ------------------------------------------------------------

anchor = '''# ============================================================
# CUSTOMER DOCUMENTS
# ============================================================
'''

guest_helper = '''def _get_guest_document_order(
    order_number,
    token,
):

    order = get_object_or_404(
        _document_queryset(),
        order_number=order_number,
        user__isnull=True,
        guest_checkout=True,
    )


    if not verify_guest_access_token(
        order,
        token,
    ):

        raise Http404(
            "Order not found."
        )


    return order



'''

if (
    anchor in text
    and
    "_get_guest_document_order" not in text
):

    text = text.replace(
        anchor,
        guest_helper + anchor,
        1,
    )


# ------------------------------------------------------------
# Add guest invoice/receipt views.
# ------------------------------------------------------------

anchor = '''# ============================================================
# ADMIN DOCUMENTS
# ============================================================
'''

guest_document_views = '''# ============================================================
# GUEST DOCUMENTS
# ============================================================

def guest_invoice(
    request,
    order_number,
    token,
):

    order = _get_guest_document_order(
        order_number,
        token,
    )


    document = _issue(
        request=request,
        order=order,
        document_type="invoice",
    )


    return _render(
        request,
        document,
        extra_context={
            "is_guest_document": True,
            "guest_access_token": token,
        },
    )



def guest_receipt(
    request,
    order_number,
    token,
):

    order = _get_guest_document_order(
        order_number,
        token,
    )


    document = _issue(
        request=request,
        order=order,
        document_type="receipt",
    )


    return _render(
        request,
        document,
        extra_context={
            "is_guest_document": True,
            "guest_access_token": token,
        },
    )



'''

if (
    anchor in text
    and
    "def guest_invoice(" not in text
):

    text = text.replace(
        anchor,
        guest_document_views + anchor,
        1,
    )


# ------------------------------------------------------------
# Upgrade _render to accept guest context.
# ------------------------------------------------------------

old = '''def _render(
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
'''

new = '''def _render(
    request,
    document,
    extra_context=None,
):

    template = (
        "orders/documents/"
        f"{document.document_type}.html"
    )


    context = {
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
                if (
                    request.user.is_authenticated
                    and
                    request.user.is_staff
                )
                else
                "customer_order_document_email"
            ),
    }


    if extra_context:
        context.update(
            extra_context
        )


    return render(
        request,
        template,
        context,
    )
'''

if old in text:
    text = text.replace(
        old,
        new,
        1,
    )

elif "extra_context=None" not in text:
    raise RuntimeError(
        "Could not update document renderer."
    )


DOCUMENT_VIEWS.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# 3. ORDER URLS — PRIVATE GUEST ROUTES
# ============================================================

text = ORDER_URLS.read_text(
    encoding="utf-8-sig"
)


if "from . import document_views" not in text:

    text = text.replace(
        '''from . import views
''',
        '''from . import views
from . import document_views

from delivery.customer_views import (
    guest_delivery_tracking,
)
''',
        1,
    )


marker = '''    path(
        "guest/<str:order_number>/<str:token>/",
        views.guest_order_detail,
        name="guest_order_detail",
    ),
'''

routes = marker + '''    path(
        "guest/<str:order_number>/<str:token>/track/",
        guest_delivery_tracking,
        name="guest_delivery_tracking",
    ),

    path(
        "guest/<str:order_number>/<str:token>/invoice/",
        document_views.guest_invoice,
        name="guest_order_invoice",
    ),

    path(
        "guest/<str:order_number>/<str:token>/receipt/",
        document_views.guest_receipt,
        name="guest_order_receipt",
    ),
'''

if (
    marker in text
    and
    'name="guest_order_invoice"' not in text
):

    text = text.replace(
        marker,
        routes,
        1,
    )


ORDER_URLS.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# 4. TRACKING TEMPLATE — GUEST-SAFE BACK BUTTON
# ============================================================

text = TRACKING_TEMPLATE.read_text(
    encoding="utf-8-sig"
)


old = '''            <a
                href="{% url 'order_detail' order.order_number %}"
                class="btn btn-sm btn-outline-secondary mb-3"
            >
                &larr; Back to Order
            </a>
'''

new = '''            {% if is_guest_tracking %}

            <a
                href="{% url 'guest_order_detail' order.order_number guest_access_token %}"
                class="btn btn-sm btn-outline-secondary mb-3"
            >
                &larr; Back to Order
            </a>

            {% else %}

            <a
                href="{% url 'order_detail' order.order_number %}"
                class="btn btn-sm btn-outline-secondary mb-3"
            >
                &larr; Back to Order
            </a>

            {% endif %}
'''

if old in text:
    text = text.replace(
        old,
        new,
        1,
    )


TRACKING_TEMPLATE.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# 5. DOCUMENT BASE — GUEST-SAFE TOOLBAR
# ============================================================

text = DOCUMENT_BASE.read_text(
    encoding="utf-8-sig"
)


old = '''    {% if request.user.is_staff %}

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
'''

new = '''    {% if is_guest_document %}

        <a
            href="{% url 'guest_order_detail' order.order_number guest_access_token %}"
        >
            Back to Order
        </a>

    {% elif request.user.is_staff %}

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
'''

if old in text:
    text = text.replace(
        old,
        new,
        1,
    )


# ------------------------------------------------------------
# Do not expose logged-in customer email POST route to guest.
# ------------------------------------------------------------

old = '''    {% if snapshot.order.email %}

        {% if is_credit_note %}
'''

new = '''    {% if snapshot.order.email and not is_guest_document %}

        {% if is_credit_note %}
'''

if old in text:
    text = text.replace(
        old,
        new,
        1,
    )


DOCUMENT_BASE.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# 6. GUEST ORDER DETAIL — TRACKING + DOCUMENT BUTTONS
# ============================================================

text = GUEST_ORDER_TEMPLATE.read_text(
    encoding="utf-8-sig"
)


marker = '''            <div class="card shadow-sm">

                <div class="card-body">
'''

buttons = '''            <div class="card shadow-sm mb-4">

                <div class="card-body">

                    <h5 class="mb-3">
                        Order Documents & Tracking
                    </h5>

                    <div class="d-flex flex-wrap gap-2">

                        <a
                            href="{% url 'guest_order_invoice' order.order_number guest_access_token %}"
                            class="btn btn-outline-dark"
                        >
                            View Invoice
                        </a>


                        {% if order.payment_status == "paid" or order.payment_status == "partially_refunded" or order.payment_status == "refunded" %}

                        <a
                            href="{% url 'guest_order_receipt' order.order_number guest_access_token %}"
                            class="btn btn-outline-success"
                        >
                            View Receipt
                        </a>

                        {% endif %}


                        {% if order.delivery %}

                        <a
                            href="{% url 'guest_delivery_tracking' order.order_number guest_access_token %}"
                            class="btn btn-outline-primary"
                        >
                            Track Delivery
                        </a>

                        {% endif %}

                    </div>

                </div>

            </div>


''' + marker


if (
    marker in text
    and
    "guest_order_invoice" not in text
):

    text = text.replace(
        marker,
        buttons,
        1,
    )


GUEST_ORDER_TEMPLATE.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# 7. TESTS
# ============================================================

TEST_FILE.write_text(
r'''
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from delivery.models import (
    Delivery,
    DeliveryEvent,
)

from orders.guest_access import (
    generate_guest_access_token,
    hash_guest_access_token,
)

from orders.models import (
    Order,
    OrderDocument,
)


class Phase13DGuestDocumentsTrackingTests(
    TestCase
):

    def setUp(self):

        self.token = (
            generate_guest_access_token()
        )


        self.order = Order.objects.create(
            user=None,
            guest_checkout=True,
            guest_access_token_hash=(
                hash_guest_access_token(
                    self.token
                )
            ),
            order_number="GUEST-DOC-001",
            full_name="Guest Customer",
            phone="0712345678",
            email="guest@example.com",
            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="1",
            subtotal=Decimal("1000.00"),
            shipping_cost=Decimal("200.00"),
            total_amount=Decimal("1200.00"),
            payment_status="pending",
            status="confirmed",
            inventory_status="reserved",
            delivery_pricing_status="fixed",
            currency_code_at_checkout="KES",
            currency_symbol_at_checkout="KSh",
        )


    def test_guest_can_view_invoice_with_valid_token(
        self,
    ):

        response = self.client.get(
            reverse(
                "guest_order_invoice",
                args=[
                    self.order.order_number,
                    self.token,
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertEqual(
            OrderDocument.objects.filter(
                order=self.order,
                document_type="invoice",
            ).count(),
            1,
        )


    def test_wrong_token_cannot_view_invoice(
        self,
    ):

        response = self.client.get(
            reverse(
                "guest_order_invoice",
                args=[
                    self.order.order_number,
                    "wrong-token",
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            404,
        )


    def test_unpaid_guest_cannot_view_receipt(
        self,
    ):

        response = self.client.get(
            reverse(
                "guest_order_receipt",
                args=[
                    self.order.order_number,
                    self.token,
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            404,
        )


    def test_paid_guest_can_view_receipt(
        self,
    ):

        self.order.payment_status = "paid"

        self.order.save(
            update_fields=[
                "payment_status"
            ]
        )


        response = self.client.get(
            reverse(
                "guest_order_receipt",
                args=[
                    self.order.order_number,
                    self.token,
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertEqual(
            OrderDocument.objects.filter(
                order=self.order,
                document_type="receipt",
            ).count(),
            1,
        )


    def test_guest_document_does_not_require_user_account(
        self,
    ):

        response = self.client.get(
            reverse(
                "guest_order_invoice",
                args=[
                    self.order.order_number,
                    self.token,
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


        self.assertIsNone(
            document.issued_by
        )


    def test_guest_can_track_delivery_with_valid_token(
        self,
    ):

        delivery = Delivery.objects.create(
            order=self.order,
            management_type="external",
            method="local_door",
            status="in_transit",
            destination="Nairobi CBD",
            customer_delivery_fee=Decimal(
                "200.00"
            ),
        )


        DeliveryEvent.objects.create(
            delivery=delivery,
            status="in_transit",
            message="Parcel is on the way.",
        )


        response = self.client.get(
            reverse(
                "guest_delivery_tracking",
                args=[
                    self.order.order_number,
                    self.token,
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertContains(
            response,
            "Parcel is on the way.",
        )


    def test_wrong_token_cannot_track_delivery(
        self,
    ):

        Delivery.objects.create(
            order=self.order,
            management_type="external",
            method="local_door",
            status="pending",
            destination="Nairobi CBD",
        )


        response = self.client.get(
            reverse(
                "guest_delivery_tracking",
                args=[
                    self.order.order_number,
                    "wrong-token",
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            404,
        )


    def test_order_number_without_token_does_not_open_guest_tracking(
        self,
    ):

        response = self.client.get(
            reverse(
                "customer_delivery_tracking",
                args=[
                    self.order.order_number
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            302,
        )


    def test_guest_order_page_exposes_secure_invoice_link(
        self,
    ):

        response = self.client.get(
            reverse(
                "guest_order_detail",
                args=[
                    self.order.order_number,
                    self.token,
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        expected = reverse(
            "guest_order_invoice",
            args=[
                self.order.order_number,
                self.token,
            ],
        )


        self.assertContains(
            response,
            expected,
        )
'''.strip() + "\n",
encoding="utf-8",
)


print()
print("=" * 72)
print("PHASE 13D INSTALLED")
print("=" * 72)
print()
print("Added:")
print("  Secure guest delivery tracking")
print("  Secure guest invoice access")
print("  Secure guest receipt access")
print("  Receipt remains unavailable before payment")
print("  Guest documents support issued_by=None")
print("  Guest-safe document toolbar")
print("  Guest-safe tracking back button")
print("  Existing customer/admin document routes preserved")
print()
print("No migration required.")
