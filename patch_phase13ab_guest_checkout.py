from pathlib import Path
import shutil


ROOT = Path.cwd()

ORDER_MODELS = ROOT / "orders" / "models.py"
ORDER_VIEWS = ROOT / "orders" / "views.py"
ORDER_URLS = ROOT / "orders" / "urls.py"
CHECKOUT_TEMPLATE = (
    ROOT
    / "templates"
    / "orders"
    / "checkout.html"
)
CONFIRMATION_TEMPLATE = (
    ROOT
    / "templates"
    / "orders"
    / "order_confirmation.html"
)

GUEST_TEMPLATE = (
    ROOT
    / "templates"
    / "orders"
    / "guest_order_detail.html"
)

GUEST_ACCESS = (
    ROOT
    / "orders"
    / "guest_access.py"
)

TESTS = (
    ROOT
    / "orders"
    / "test_phase13ab.py"
)


required = [
    ORDER_MODELS,
    ORDER_VIEWS,
    ORDER_URLS,
    CHECKOUT_TEMPLATE,
    CONFIRMATION_TEMPLATE,
]


for path in required:

    if not path.exists():

        raise RuntimeError(
            f"Missing required file: {path}"
        )


for path in required:

    backup = Path(
        str(path)
        + ".phase13abbackup"
    )

    if not backup.exists():

        shutil.copy2(
            path,
            backup,
        )


# ============================================================
# 1. ORDER MODEL — OPTIONAL USER + GUEST SECURITY STATE
# ============================================================

text = ORDER_MODELS.read_text(
    encoding="utf-8-sig"
)


old = '''    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
    )
'''


new = '''    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
        null=True,
        blank=True,
    )

    guest_checkout = models.BooleanField(
        default=False,
        db_index=True,
    )

    guest_access_token_hash = models.CharField(
        max_length=64,
        blank=True,
        default="",
        db_index=True,
    )
'''


if old in text:

    text = text.replace(
        old,
        new,
        1,
    )

elif "guest_access_token_hash" not in text:

    raise RuntimeError(
        "Could not locate Order.user field."
    )


ORDER_MODELS.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# 2. SECURE GUEST TOKEN SERVICE
# ============================================================

GUEST_ACCESS.write_text(
r'''
import hashlib
import hmac
import secrets


TOKEN_BYTES = 32


def generate_guest_access_token():

    return secrets.token_urlsafe(
        TOKEN_BYTES
    )


def hash_guest_access_token(
    token,
):

    if not token:

        return ""

    return hashlib.sha256(
        token.encode(
            "utf-8"
        )
    ).hexdigest()


def verify_guest_access_token(
    order,
    token,
):

    if not order.guest_checkout:

        return False


    stored_hash = (
        order.guest_access_token_hash
        or ""
    )


    if not stored_hash:

        return False


    supplied_hash = (
        hash_guest_access_token(
            token
        )
    )


    return hmac.compare_digest(
        stored_hash,
        supplied_hash,
    )
'''.strip() + "\n",
encoding="utf-8",
)


# ============================================================
# 3. CHECKOUT IMPORTS
# ============================================================

text = ORDER_VIEWS.read_text(
    encoding="utf-8-sig"
)


if "from .guest_access import (" not in text:

    marker = '''from .inventory import release_order_inventory
'''


    addition = marker + '''

from .guest_access import (
    generate_guest_access_token,
    hash_guest_access_token,
    verify_guest_access_token,
)
'''


    if marker not in text:

        raise RuntimeError(
            "Could not locate inventory import."
        )


    text = text.replace(
        marker,
        addition,
        1,
    )


# ============================================================
# 4. REMOVE LOGIN REQUIREMENT FROM CHECKOUT ONLY
# ============================================================

old = '''@login_required
@ratelimit(key="user", rate="10/m", method="POST", block=True)
def checkout(request):
'''


new = '''@ratelimit(key="ip", rate="10/m", method="POST", block=True)
def checkout(request):
'''


if old in text:

    text = text.replace(
        old,
        new,
        1,
    )

elif '''@ratelimit(key="ip", rate="10/m", method="POST", block=True)
def checkout(request):
''' not in text:

    raise RuntimeError(
        "Could not locate checkout decorators."
    )


# ============================================================
# 5. GUEST-SAFE ADDRESSES
# ============================================================

old = '''    addresses = Address.objects.filter(user=request.user)

    default_address = addresses.filter(is_default=True).first()
'''


new = '''    if request.user.is_authenticated:

        addresses = (
            Address.objects
            .filter(
                user=request.user
            )
        )

        default_address = (
            addresses
            .filter(
                is_default=True
            )
            .first()
        )

    else:

        addresses = Address.objects.none()

        default_address = None
'''


if old in text:

    text = text.replace(
        old,
        new,
        1,
    )

elif "addresses = Address.objects.none()" not in text:

    raise RuntimeError(
        "Could not locate checkout address query."
    )


# ============================================================
# 6. REQUIRE EMAIL FOR GUEST CHECKOUT
# ============================================================

old = '''        if form.is_valid():

            for item in items:
'''


new = '''        form_valid = form.is_valid()


        if (
            form_valid
            and
            not request.user.is_authenticated
            and
            not (
                form.cleaned_data.get(
                    "email"
                )
                or ""
            ).strip()
        ):

            form.add_error(
                "email",
                (
                    "Email is required for guest checkout "
                    "so you can securely access your order."
                ),
            )

            form_valid = False


        if form_valid:

            for item in items:
'''


if old in text:

    text = text.replace(
        old,
        new,
        1,
    )

elif "Email is required for guest checkout" not in text:

    raise RuntimeError(
        "Could not locate checkout form-valid block."
    )


# Existing second form.is_valid() must use cached result.
old = '''        if form.is_valid() and not stock_error:
'''


new = '''        if form_valid and not stock_error:
'''


if old in text:

    text = text.replace(
        old,
        new,
        1,
    )


# ============================================================
# 7. CREATE GUEST TOKEN BEFORE ORDER
# ============================================================

marker = '''                order = Order.objects.create(
                    user=request.user,
'''


replacement = '''                guest_access_token = None
                guest_access_token_hash = ""


                if not request.user.is_authenticated:

                    guest_access_token = (
                        generate_guest_access_token()
                    )

                    guest_access_token_hash = (
                        hash_guest_access_token(
                            guest_access_token
                        )
                    )


                order = Order.objects.create(
                    user=(
                        request.user
                        if request.user.is_authenticated
                        else None
                    ),

                    guest_checkout=(
                        not request.user.is_authenticated
                    ),

                    guest_access_token_hash=(
                        guest_access_token_hash
                    ),
'''


if marker in text:

    text = text.replace(
        marker,
        replacement,
        1,
    )

elif "guest_access_token_hash=(" not in text:

    raise RuntimeError(
        "Could not locate Order.objects.create()."
    )


# ============================================================
# 8. GUEST REDIRECT AFTER CHECKOUT
# ============================================================

old = '''            return redirect("order_confirmation", order_number=order.order_number)
'''


new = '''            if order.guest_checkout:

                return redirect(
                    "guest_order_confirmation",
                    order_number=(
                        order.order_number
                    ),
                    token=guest_access_token,
                )


            return redirect(
                "order_confirmation",
                order_number=order.order_number,
            )
'''


if old in text:

    text = text.replace(
        old,
        new,
        1,
    )

elif '"guest_order_confirmation"' not in text:

    raise RuntimeError(
        "Could not locate checkout redirect."
    )


# ============================================================
# 9. SECURE GUEST VIEWS
# ============================================================

if "def guest_order_confirmation(" not in text:

    marker = '''@login_required
def order_confirmation(request, order_number):
'''


    guest_views = '''def _get_guest_order_or_404(
    order_number,
    token,
):

    order = get_object_or_404(
        Order.objects.prefetch_related(
            "items__product",
            "items__variant",
        ),
        order_number=order_number,
        guest_checkout=True,
        user__isnull=True,
    )


    if not verify_guest_access_token(
        order,
        token,
    ):

        from django.http import Http404

        raise Http404(
            "Order not found."
        )


    return order



def guest_order_confirmation(
    request,
    order_number,
    token,
):

    order = _get_guest_order_or_404(
        order_number,
        token,
    )


    return render(
        request,
        "orders/order_confirmation.html",
        {
            "order": order,
            "guest_access_token": token,
            "is_guest_order": True,
        },
    )



def guest_order_detail(
    request,
    order_number,
    token,
):

    order = _get_guest_order_or_404(
        order_number,
        token,
    )


    return render(
        request,
        "orders/guest_order_detail.html",
        {
            "order": order,
            "items": order.items.all(),
            "guest_access_token": token,
        },
    )



''' + marker


    if marker not in text:

        raise RuntimeError(
            "Could not locate order_confirmation()."
        )


    text = text.replace(
        marker,
        guest_views,
        1,
    )


ORDER_VIEWS.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# 10. GUEST ROUTES
# ============================================================

text = ORDER_URLS.read_text(
    encoding="utf-8-sig"
)


if 'name="guest_order_confirmation"' not in text:

    marker = '''    path("", views.checkout, name="checkout"),
'''


    routes = marker + '''    path(
        "guest/<str:order_number>/<str:token>/confirmation/",
        views.guest_order_confirmation,
        name="guest_order_confirmation",
    ),
    path(
        "guest/<str:order_number>/<str:token>/",
        views.guest_order_detail,
        name="guest_order_detail",
    ),
'''


    if marker not in text:

        raise RuntimeError(
            "Could not locate checkout URL."
        )


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
# 11. CHECKOUT UI
# ============================================================

text = CHECKOUT_TEMPLATE.read_text(
    encoding="utf-8-sig"
)


if "Guest checkout" not in text:

    marker = '''                    <h4 class="mb-4">Delivery Information</h4>
'''


    addition = marker + '''

                    {% if not request.user.is_authenticated %}

                    <div class="alert alert-info">

                        <strong>
                            Guest checkout
                        </strong>

                        <div class="small mt-1">

                            No account is required.
                            Please provide a valid email address
                            so your order can be securely accessed.

                        </div>

                    </div>

                    {% endif %}
'''


    if marker not in text:

        raise RuntimeError(
            "Could not locate checkout heading."
        )


    text = text.replace(
        marker,
        addition,
        1,
    )


# Safer authenticated name default.
old = '''value="{{ request.user.get_full_name }}"'''
new = '''value="{% if request.user.is_authenticated %}{{ request.user.get_full_name }}{% endif %}"'''

text = text.replace(
    old,
    new,
)


old = '''value="{{ request.user.email }}">'''
new = '''value="{% if request.user.is_authenticated %}{{ request.user.email }}{% endif %}" {% if not request.user.is_authenticated %}required{% endif %}>'''

text = text.replace(
    old,
    new,
)


# Show email errors.
if "form.email.errors" not in text:

    marker = '''                        <div class="row">
'''


    # Add near email field instead of globally.
    email_marker = '''                        <div class="mb-3">
                            <label class="form-label">Email</label>
                            <input type="email" name="email" class="form-control" value="{% if request.user.is_authenticated %}{{ request.user.email }}{% endif %}" {% if not request.user.is_authenticated %}required{% endif %}>
                        </div>
'''


    email_replacement = '''                        <div class="mb-3">

                            <label class="form-label">
                                Email
                            </label>

                            <input
                                type="email"
                                name="email"
                                class="form-control"
                                value="{% if request.user.is_authenticated %}{{ request.user.email }}{% endif %}"
                                {% if not request.user.is_authenticated %}required{% endif %}
                            >

                            {% if form.email.errors %}

                                <div class="text-danger small mt-1">

                                    {% for error in form.email.errors %}
                                        {{ error }}
                                    {% endfor %}

                                </div>

                            {% endif %}

                        </div>
'''


    if email_marker in text:

        text = text.replace(
            email_marker,
            email_replacement,
            1,
        )


CHECKOUT_TEMPLATE.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# 12. CONFIRMATION TEMPLATE GUEST LINKS
# ============================================================

text = CONFIRMATION_TEMPLATE.read_text(
    encoding="utf-8-sig"
)


old = '''                    {% if order.delivery_pricing_status == "quote_pending" %}
'''


new = '''                    {% if is_guest_order %}

                    <div class="alert alert-info text-start">

                        <strong>
                            Save this page.
                        </strong>

                        <div class="mt-1">

                            Your guest order is protected by a
                            private access token.

                        </div>

                    </div>

                    <a
                        href="{% url 'guest_order_detail' order.order_number guest_access_token %}"
                        class="btn btn-outline-primary"
                    >
                        View Guest Order
                    </a>

                    {% elif order.delivery_pricing_status == "quote_pending" %}
'''


if old in text and "View Guest Order" not in text:

    text = text.replace(
        old,
        new,
        1,
    )


# Fix remaining hard-coded checkout currency labels.
text = text.replace(
    '''<span>KES {{ order.subtotal }}</span>''',
    '''<span>{{ order.currency_symbol_at_checkout }} {{ order.subtotal }}</span>''',
)

text = text.replace(
    '''KES {{ order.shipping_cost }}''',
    '''{{ order.currency_symbol_at_checkout }} {{ order.shipping_cost }}''',
)


CONFIRMATION_TEMPLATE.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# 13. GUEST ORDER DETAIL TEMPLATE
# ============================================================

GUEST_TEMPLATE.write_text(
r'''
{% extends "base.html" %}

{% block content %}

<div class="container py-5">

    <div class="row justify-content-center">

        <div class="col-xl-9">

            <div class="d-flex justify-content-between align-items-start flex-wrap gap-3 mb-4">

                <div>

                    <h2 class="mb-1">
                        Guest Order
                    </h2>

                    <div class="text-muted">
                        {{ order.order_number }}
                    </div>

                </div>


                <div class="text-end">

                    <div>
                        <span class="badge bg-secondary text-capitalize">
                            {{ order.status }}
                        </span>
                    </div>

                    <div class="mt-2">
                        Payment:
                        <strong class="text-capitalize">
                            {{ order.payment_status }}
                        </strong>
                    </div>

                </div>

            </div>


            <div class="alert alert-warning">

                This page contains a private guest-order token.
                Do not share this URL publicly.

            </div>


            <div class="card shadow-sm mb-4">

                <div class="card-body">

                    <h5 class="mb-3">
                        Customer & Delivery
                    </h5>


                    <div class="row g-3">

                        <div class="col-md-6">

                            <div class="text-muted small">
                                Customer
                            </div>

                            <strong>
                                {{ order.full_name }}
                            </strong>

                        </div>


                        <div class="col-md-6">

                            <div class="text-muted small">
                                Email
                            </div>

                            <strong>
                                {{ order.email }}
                            </strong>

                        </div>


                        <div class="col-md-6">

                            <div class="text-muted small">
                                Phone
                            </div>

                            <strong>
                                {{ order.phone }}
                            </strong>

                        </div>


                        <div class="col-md-6">

                            <div class="text-muted small">
                                Delivery Address
                            </div>

                            <strong>
                                {{ order.house_number }},
                                {{ order.estate }},
                                {{ order.city }},
                                {{ order.county }}
                            </strong>

                        </div>

                    </div>

                </div>

            </div>


            <div class="card shadow-sm mb-4">

                <div class="card-body">

                    <h5 class="mb-3">
                        Items
                    </h5>


                    <div class="table-responsive">

                        <table class="table align-middle">

                            <thead>

                                <tr>
                                    <th>Item</th>
                                    <th>Qty</th>
                                    <th>Price</th>
                                    <th class="text-end">
                                        Total
                                    </th>
                                </tr>

                            </thead>

                            <tbody>

                                {% for item in items %}

                                <tr>

                                    <td>

                                        {{ item.product_name }}

                                        {% if item.variant_name %}

                                            <div class="small text-muted">
                                                {{ item.variant_name }}
                                            </div>

                                        {% endif %}

                                    </td>

                                    <td>
                                        {{ item.quantity }}
                                    </td>

                                    <td>
                                        {{ order.currency_symbol_at_checkout }}
                                        {{ item.price }}
                                    </td>

                                    <td class="text-end">

                                        {{ order.currency_symbol_at_checkout }}
                                        {{ item.subtotal }}

                                    </td>

                                </tr>

                                {% endfor %}

                            </tbody>

                        </table>

                    </div>

                </div>

            </div>


            <div class="card shadow-sm">

                <div class="card-body">

                    <div class="d-flex justify-content-between mb-2">

                        <span>
                            Merchandise
                        </span>

                        <span>
                            {{ order.currency_symbol_at_checkout }}
                            {{ order.subtotal }}
                        </span>

                    </div>


                    {% if order.discount %}

                    <div class="d-flex justify-content-between mb-2">

                        <span>
                            Discount
                        </span>

                        <span>
                            -
                            {{ order.currency_symbol_at_checkout }}
                            {{ order.discount }}
                        </span>

                    </div>

                    {% endif %}


                    {% if order.tax_amount %}

                    <div class="d-flex justify-content-between mb-2">

                        <span>
                            Tax
                            ({{ order.tax_rate_at_checkout }}%)
                        </span>

                        <span>
                            {{ order.currency_symbol_at_checkout }}
                            {{ order.tax_amount }}
                        </span>

                    </div>

                    {% endif %}


                    <div class="d-flex justify-content-between mb-2">

                        <span>
                            Delivery
                        </span>

                        <span>

                            {% if order.delivery_pricing_status == "quote_pending" %}

                                Awaiting quote

                            {% else %}

                                {{ order.currency_symbol_at_checkout }}
                                {{ order.shipping_cost }}

                            {% endif %}

                        </span>

                    </div>


                    <hr>


                    <div class="d-flex justify-content-between fs-5 fw-bold">

                        <span>
                            Total
                        </span>

                        <span>
                            {{ order.currency_symbol_at_checkout }}
                            {{ order.total_amount }}
                        </span>

                    </div>


                    {% if order.payment_status == "pending" %}

                    <div class="alert alert-info mt-4 mb-0">

                        Guest M-PESA payment access will use this
                        same secure order token.

                    </div>

                    {% endif %}

                </div>

            </div>

        </div>

    </div>

</div>

{% endblock %}
'''.strip() + "\n",
encoding="utf-8",
)


# ============================================================
# 14. TESTS
# ============================================================

TESTS.write_text(
r'''
from decimal import Decimal

from django.contrib.auth import (
    get_user_model,
)

from django.test import TestCase
from django.urls import reverse

from cart.models import Cart, CartItem

from categories.models import Category

from delivery.models import DeliveryZone

from orders.guest_access import (
    generate_guest_access_token,
    hash_guest_access_token,
    verify_guest_access_token,
)

from orders.models import Order

from products.models import Product


User = get_user_model()


class Phase13ABGuestAccessTests(
    TestCase
):

    def setUp(self):

        self.category = (
            Category.objects.create(
                name="Guest Category",
                slug="guest-category",
            )
        )


        self.product = (
            Product.objects.create(
                category=self.category,
                name="Guest Product",
                slug="guest-product",
                description="Guest checkout item",
                sku="GUEST-001",
                price=Decimal("1000.00"),
                stock=20,
                reserved_stock=0,
                is_active=True,
            )
        )


        self.zone = (
            DeliveryZone.objects.create(
                county="Nairobi",
                town="Nairobi",
                method="local_delivery",
                pricing_mode="fixed",
                fee=Decimal("200.00"),
                is_active=True,
            )
        )


    def _create_guest_cart(self):

        session = self.client.session

        session[
            "phase13ab"
        ] = True

        session.save()


        cart = Cart.objects.create(
            session_key=session.session_key
        )


        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=1,
        )


        return cart


    def test_token_hash_verification(
        self,
    ):

        token = (
            generate_guest_access_token()
        )


        order = Order(
            guest_checkout=True,
            guest_access_token_hash=(
                hash_guest_access_token(
                    token
                )
            ),
        )


        self.assertTrue(
            verify_guest_access_token(
                order,
                token,
            )
        )


        self.assertFalse(
            verify_guest_access_token(
                order,
                "wrong-token",
            )
        )


    def test_normal_order_rejects_guest_token(
        self,
    ):

        token = (
            generate_guest_access_token()
        )


        order = Order(
            guest_checkout=False,
            guest_access_token_hash=(
                hash_guest_access_token(
                    token
                )
            ),
        )


        self.assertFalse(
            verify_guest_access_token(
                order,
                token,
            )
        )


    def test_guest_checkout_requires_email(
        self,
    ):

        self._create_guest_cart()


        response = self.client.post(
            reverse(
                "checkout"
            ),
            {
                "full_name":
                    "Guest Customer",

                "phone":
                    "0712345678",

                "email":
                    "",

                "county":
                    "Nairobi",

                "city":
                    "Nairobi",

                "estate":
                    "CBD",

                "house_number":
                    "1",

                "delivery_zone":
                    str(
                        self.zone.pk
                    ),
            },
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertEqual(
            Order.objects.count(),
            0,
        )


        self.assertContains(
            response,
            "Email is required for guest checkout",
        )


    def test_guest_checkout_creates_order_without_user(
        self,
    ):

        self._create_guest_cart()


        response = self.client.post(
            reverse(
                "checkout"
            ),
            {
                "full_name":
                    "Guest Customer",

                "phone":
                    "0712345678",

                "email":
                    "guest@example.com",

                "county":
                    "Nairobi",

                "city":
                    "Nairobi",

                "estate":
                    "CBD",

                "house_number":
                    "1",

                "delivery_zone":
                    str(
                        self.zone.pk
                    ),
            },
        )


        self.assertEqual(
            response.status_code,
            302,
        )


        order = (
            Order.objects.get()
        )


        self.assertIsNone(
            order.user
        )

        self.assertTrue(
            order.guest_checkout
        )

        self.assertEqual(
            order.email,
            "guest@example.com",
        )

        self.assertEqual(
            len(
                order.guest_access_token_hash
            ),
            64,
        )


        self.assertIn(
            order.order_number,
            response.url,
        )


        # Raw token must not be stored in the DB.
        self.assertNotIn(
            order.guest_access_token_hash,
            response.url,
        )


    def test_wrong_guest_token_returns_404(
        self,
    ):

        token = (
            generate_guest_access_token()
        )


        order = Order.objects.create(
            user=None,
            guest_checkout=True,
            guest_access_token_hash=(
                hash_guest_access_token(
                    token
                )
            ),
            order_number="GUEST-SEC-001",
            full_name="Guest",
            phone="0712345678",
            email="guest@example.com",
            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="1",
            subtotal=Decimal("1000.00"),
            total_amount=Decimal("1000.00"),
        )


        response = self.client.get(
            reverse(
                "guest_order_detail",
                args=[
                    order.order_number,
                    "definitely-wrong",
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            404,
        )


    def test_correct_guest_token_can_view_order(
        self,
    ):

        token = (
            generate_guest_access_token()
        )


        order = Order.objects.create(
            user=None,
            guest_checkout=True,
            guest_access_token_hash=(
                hash_guest_access_token(
                    token
                )
            ),
            order_number="GUEST-SEC-002",
            full_name="Guest",
            phone="0712345678",
            email="guest@example.com",
            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="1",
            subtotal=Decimal("1000.00"),
            total_amount=Decimal("1000.00"),
        )


        response = self.client.get(
            reverse(
                "guest_order_detail",
                args=[
                    order.order_number,
                    token,
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertContains(
            response,
            "GUEST-SEC-002",
        )


    def test_order_number_alone_does_not_expose_guest_order(
        self,
    ):

        token = (
            generate_guest_access_token()
        )


        order = Order.objects.create(
            user=None,
            guest_checkout=True,
            guest_access_token_hash=(
                hash_guest_access_token(
                    token
                )
            ),
            order_number="GUEST-SEC-003",
            full_name="Guest",
            phone="0712345678",
            email="guest@example.com",
            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="1",
            subtotal=Decimal("1000.00"),
            total_amount=Decimal("1000.00"),
        )


        response = self.client.get(
            reverse(
                "order_confirmation",
                args=[
                    order.order_number
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            302,
        )


        self.assertIn(
            "/accounts/",
            response.url,
        )


    def test_authenticated_checkout_still_uses_user_order(
        self,
    ):

        user = (
            User.objects.create_user(
                username="phase13-user",
                password="pass12345",
                email="member@example.com",
            )
        )


        self.client.force_login(
            user
        )


        cart = Cart.objects.create(
            user=user
        )


        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=1,
        )


        response = self.client.post(
            reverse(
                "checkout"
            ),
            {
                "full_name":
                    "Member Customer",

                "phone":
                    "0712345678",

                "email":
                    "member@example.com",

                "county":
                    "Nairobi",

                "city":
                    "Nairobi",

                "estate":
                    "CBD",

                "house_number":
                    "1",

                "delivery_zone":
                    str(
                        self.zone.pk
                    ),
            },
        )


        self.assertEqual(
            response.status_code,
            302,
        )


        order = (
            Order.objects.get()
        )


        self.assertEqual(
            order.user,
            user,
        )

        self.assertFalse(
            order.guest_checkout
        )

        self.assertEqual(
            order.guest_access_token_hash,
            "",
        )
'''.strip() + "\n",
encoding="utf-8",
)


print()
print("=" * 72)
print("PHASE 13A + 13B INSTALLED")
print("=" * 72)
print()
print("Added:")
print("  Anonymous checkout")
print("  Existing session-cart reuse")
print("  Optional Order.user for guests")
print("  Guest order marker")
print("  Cryptographically random guest access token")
print("  SHA-256 token storage instead of raw token storage")
print("  Constant-time token comparison")
print("  Guest email requirement")
print("  Secure guest confirmation URL")
print("  Secure guest order-detail URL")
print("  Wrong-token 404 protection")
print("  Authenticated checkout preserved")
print()
print("Migration required.")
