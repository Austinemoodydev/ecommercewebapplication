from pathlib import Path
import shutil


ROOT = Path.cwd()

PAYMENT_VIEWS = ROOT / "payments" / "views.py"
PAYMENT_URLS = ROOT / "payments" / "urls.py"
PAY_TEMPLATE = ROOT / "templates" / "payments" / "pay.html"
GUEST_TEMPLATE = ROOT / "templates" / "orders" / "guest_order_detail.html"
CONFIRMATION_TEMPLATE = ROOT / "templates" / "orders" / "order_confirmation.html"
TEST_FILE = ROOT / "payments" / "test_phase13c.py"


files = [
    PAYMENT_VIEWS,
    PAYMENT_URLS,
    PAY_TEMPLATE,
    GUEST_TEMPLATE,
    CONFIRMATION_TEMPLATE,
]


for path in files:
    if not path.exists():
        raise RuntimeError(f"Missing required file: {path}")


for path in files:
    backup = Path(str(path) + ".phase13cbackup")

    if not backup.exists():
        shutil.copy2(path, backup)


# ============================================================
# PAYMENTS/VIEWS.PY
# ============================================================

text = PAYMENT_VIEWS.read_text(
    encoding="utf-8-sig"
)


# ------------------------------------------------------------
# Imports
# ------------------------------------------------------------

old = '''from django.contrib.auth.decorators import login_required
'''

new = '''from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
'''

if old in text and "redirect_to_login" not in text:
    text = text.replace(
        old,
        new,
        1,
    )


old = '''from django.http import JsonResponse
'''

new = '''from django.http import JsonResponse, Http404
'''

if old in text and "JsonResponse, Http404" not in text:
    text = text.replace(
        old,
        new,
        1,
    )


marker = '''from orders.models import Order
'''

addition = '''from orders.models import Order
from orders.guest_access import verify_guest_access_token
'''

if marker in text and "verify_guest_access_token" not in text:
    text = text.replace(
        marker,
        addition,
        1,
    )


# ------------------------------------------------------------
# Shared payment ownership helper
# ------------------------------------------------------------

marker = '''def _payment_is_settled(order):
    return (
        order.payment_status
        in SETTLED_PAYMENT_STATUSES
    )


'''

helper = '''def _payment_is_settled(order):
    return (
        order.payment_status
        in SETTLED_PAYMENT_STATUSES
    )


def _get_authorized_payment_order(
    request,
    order_number,
    guest_token=None,
    lock=False,
):

    queryset = Order.objects

    if lock:
        queryset = queryset.select_for_update()


    if guest_token:

        order = get_object_or_404(
            queryset,
            order_number=order_number,
            guest_checkout=True,
            user__isnull=True,
        )

        if not verify_guest_access_token(
            order,
            guest_token,
        ):

            raise Http404(
                "Order not found."
            )

        return order


    if not request.user.is_authenticated:

        raise Http404(
            "Order not found."
        )


    return get_object_or_404(
        queryset,
        order_number=order_number,
        user=request.user,
        guest_checkout=False,
    )


'''

if marker in text and "_get_authorized_payment_order" not in text:
    text = text.replace(
        marker,
        helper,
        1,
    )


# ------------------------------------------------------------
# Change payment view decorator/signature
# ------------------------------------------------------------

old = '''@login_required
@ratelimit(
    key="user",
    rate="5/m",
    method="POST",
    block=True,
)
def initiate_payment(request, order_number):
'''

new = '''@ratelimit(
    key="ip",
    rate="5/m",
    method="POST",
    block=True,
)
def initiate_payment(
    request,
    order_number,
    token=None,
):
'''

if old in text:
    text = text.replace(
        old,
        new,
        1,
    )

elif "def initiate_payment(\n    request,\n    order_number,\n    token=None," not in text:
    raise RuntimeError(
        "Could not locate initiate_payment definition."
    )


# ------------------------------------------------------------
# Preserve normal login behavior
# ------------------------------------------------------------

old = '''def initiate_payment(
    request,
    order_number,
    token=None,
):

    if request.method != "POST":
'''

new = '''def initiate_payment(
    request,
    order_number,
    token=None,
):

    if (
        token is None
        and
        not request.user.is_authenticated
    ):

        return redirect_to_login(
            request.get_full_path()
        )


    if request.method != "POST":
'''

if old in text:
    text = text.replace(
        old,
        new,
        1,
    )


# ------------------------------------------------------------
# GET ownership check
# ------------------------------------------------------------

old = '''        order = get_object_or_404(
            Order,
            order_number=order_number,
            user=request.user,
        )
'''

new = '''        order = _get_authorized_payment_order(
            request,
            order_number,
            guest_token=token,
        )
'''

if old in text:
    text = text.replace(
        old,
        new,
        1,
    )

else:
    raise RuntimeError(
        "Could not locate payment GET ownership lookup."
    )


# Add guest context to payment template.
old = '''                "delivery_quote_expired": (
                    order.delivery_pricing_status
                    == "quoted"
                    and
                    order.delivery_quote_expires_at
                    and
                    order.delivery_quote_expires_at
                    <= timezone.now()
                ),
            },
'''

new = '''                "delivery_quote_expired": (
                    order.delivery_pricing_status
                    == "quoted"
                    and
                    order.delivery_quote_expires_at
                    and
                    order.delivery_quote_expires_at
                    <= timezone.now()
                ),

                "guest_access_token": token,

                "is_guest_payment": bool(
                    token
                ),
            },
'''

if old in text:
    text = text.replace(
        old,
        new,
        1,
    )


# ------------------------------------------------------------
# POST locked ownership check
# ------------------------------------------------------------

old = '''        order = get_object_or_404(
            Order.objects.select_for_update(),
            order_number=order_number,
            user=request.user,
        )
'''

new = '''        order = _get_authorized_payment_order(
            request,
            order_number,
            guest_token=token,
            lock=True,
        )
'''

if old in text:
    text = text.replace(
        old,
        new,
        1,
    )

else:
    raise RuntimeError(
        "Could not locate locked payment ownership lookup."
    )


# ------------------------------------------------------------
# Payment status endpoint
# ------------------------------------------------------------

old = '''@login_required
def check_payment_status(
    request,
    order_number,
):

    order = get_object_or_404(
        Order,
        order_number=order_number,
        user=request.user,
    )
'''

new = '''def check_payment_status(
    request,
    order_number,
    token=None,
):

    if (
        token is None
        and
        not request.user.is_authenticated
    ):

        return redirect_to_login(
            request.get_full_path()
        )


    order = _get_authorized_payment_order(
        request,
        order_number,
        guest_token=token,
    )
'''

if old in text:
    text = text.replace(
        old,
        new,
        1,
    )

elif "guest_token=token" not in text:
    raise RuntimeError(
        "Could not locate check_payment_status."
    )


PAYMENT_VIEWS.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# PAYMENTS/URLS.PY
# ============================================================

text = PAYMENT_URLS.read_text(
    encoding="utf-8-sig"
)


marker = '''    path("pay/<str:order_number>/", views.initiate_payment, name="initiate_payment"),
'''

routes = '''    path(
        "guest/pay/<str:order_number>/<str:token>/",
        views.initiate_payment,
        name="guest_initiate_payment",
    ),

    path(
        "guest/status/<str:order_number>/<str:token>/",
        views.check_payment_status,
        name="guest_check_payment_status",
    ),

    path("pay/<str:order_number>/", views.initiate_payment, name="initiate_payment"),
'''

if (
    marker in text
    and
    'name="guest_initiate_payment"' not in text
):

    text = text.replace(
        marker,
        routes,
        1,
    )


PAYMENT_URLS.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# PAYMENTS/PAY.HTML
# ============================================================

text = PAY_TEMPLATE.read_text(
    encoding="utf-8-sig"
)


# Historical currency snapshot.
text = text.replace(
    '''Amount: <strong>KES {{ order.total_amount }}</strong>''',
    '''Amount:
                        <strong>
                            {{ order.currency_symbol_at_checkout }}
                            {{ order.total_amount }}
                        </strong>''',
)


# Guest-safe back buttons.
old = '''href="{% url 'order_detail' order.order_number %}"'''

new = '''href="{% if is_guest_payment %}{% url 'guest_order_detail' order.order_number guest_access_token %}{% else %}{% url 'order_detail' order.order_number %}{% endif %}"'''

text = text.replace(
    old,
    new,
)


# Guest-safe polling.
old = '''fetch("{% url 'check_payment_status' order.order_number %}")'''

new = '''fetch("{% if is_guest_payment %}{% url 'guest_check_payment_status' order.order_number guest_access_token %}{% else %}{% url 'check_payment_status' order.order_number %}{% endif %}")'''

if old in text:
    text = text.replace(
        old,
        new,
        1,
    )

elif "guest_check_payment_status" not in text:
    raise RuntimeError(
        "Could not locate payment polling URL."
    )


PAY_TEMPLATE.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# GUEST ORDER DETAIL — PAYMENT BUTTON
# ============================================================

text = GUEST_TEMPLATE.read_text(
    encoding="utf-8-sig"
)


old = '''                    {% if order.payment_status == "pending" %}

                    <div class="alert alert-info mt-4 mb-0">

                        Guest M-PESA payment access will use this
                        same secure order token.

                    </div>

                    {% endif %}
'''

new = '''                    {% if order.payment_status == "pending" %}

                        {% if order.delivery_pricing_status == "quote_pending" %}

                        <div class="alert alert-warning mt-4 mb-0">

                            Delivery price is awaiting confirmation.
                            M-PESA payment will become available after
                            the shop confirms the delivery charge.

                        </div>

                        {% else %}

                        <a
                            href="{% url 'guest_initiate_payment' order.order_number guest_access_token %}"
                            class="btn btn-success w-100 mt-4"
                        >
                            Pay with M-PESA
                        </a>

                        {% endif %}

                    {% elif order.payment_status == "paid" %}

                    <div class="alert alert-success mt-4 mb-0">

                        Payment received.

                    </div>

                    {% endif %}
'''

if old in text:
    text = text.replace(
        old,
        new,
        1,
    )

elif "guest_initiate_payment" not in text:
    raise RuntimeError(
        "Could not locate guest payment placeholder."
    )


GUEST_TEMPLATE.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# GUEST CONFIRMATION — DIRECT M-PESA BUTTON
# ============================================================

text = CONFIRMATION_TEMPLATE.read_text(
    encoding="utf-8-sig"
)


marker = '''                    <a
                        href="{% url 'guest_order_detail' order.order_number guest_access_token %}"
                        class="btn btn-outline-primary"
                    >
                        View Guest Order
                    </a>
'''

addition = '''                    <a
                        href="{% url 'guest_order_detail' order.order_number guest_access_token %}"
                        class="btn btn-outline-primary"
                    >
                        View Guest Order
                    </a>

                    {% if order.payment_status == "pending" and order.delivery_pricing_status != "quote_pending" %}

                    <a
                        href="{% url 'guest_initiate_payment' order.order_number guest_access_token %}"
                        class="btn btn-success ms-2"
                    >
                        Pay with M-PESA
                    </a>

                    {% endif %}
'''

if (
    marker in text
    and
    "guest_initiate_payment" not in text
):

    text = text.replace(
        marker,
        addition,
        1,
    )


CONFIRMATION_TEMPLATE.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# PHASE 13C TESTS
# ============================================================

TEST_FILE.write_text(
r'''
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from orders.guest_access import (
    generate_guest_access_token,
    hash_guest_access_token,
)

from orders.models import Order

from payments.models import MpesaTransaction


User = get_user_model()


@override_settings(
    MPESA_STK_ACTIVE_SECONDS=120,
    MPESA_PAYMENT_GRACE_MINUTES=10,
    ORDER_RESERVATION_MINUTES=15,
)
class Phase13CGuestPaymentTests(
    TestCase
):

    def setUp(self):

        self.token = (
            generate_guest_access_token()
        )


        self.guest_order = (
            Order.objects.create(
                user=None,
                guest_checkout=True,
                guest_access_token_hash=(
                    hash_guest_access_token(
                        self.token
                    )
                ),
                order_number="GUEST-PAY-001",
                full_name="Guest Buyer",
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
                status="pending",
                inventory_status="reserved",
                delivery_pricing_status="fixed",
                currency_code_at_checkout="KES",
                currency_symbol_at_checkout="KSh",
            )
        )


    def test_guest_can_open_payment_page_with_correct_token(
        self,
    ):

        response = self.client.get(
            reverse(
                "guest_initiate_payment",
                args=[
                    self.guest_order.order_number,
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
            "Pay with M-PESA",
        )


        self.assertContains(
            response,
            "KSh",
        )


    def test_guest_payment_page_rejects_wrong_token(
        self,
    ):

        response = self.client.get(
            reverse(
                "guest_initiate_payment",
                args=[
                    self.guest_order.order_number,
                    "wrong-private-token",
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            404,
        )


    def test_normal_payment_route_still_requires_login(
        self,
    ):

        response = self.client.get(
            reverse(
                "initiate_payment",
                args=[
                    self.guest_order.order_number
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


    @patch(
        "payments.views.stk_push"
    )
    def test_guest_can_start_stk_push(
        self,
        mocked_stk_push,
    ):

        mocked_stk_push.return_value = {
            "ResponseCode": "0",
            "MerchantRequestID":
                "MERCHANT-GUEST-001",
            "CheckoutRequestID":
                "CHECKOUT-GUEST-001",
        }


        response = self.client.post(
            reverse(
                "guest_initiate_payment",
                args=[
                    self.guest_order.order_number,
                    self.token,
                ],
            ),
            {
                "phone_number":
                    "0712345678",
            },
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        payload = response.json()


        self.assertTrue(
            payload["success"]
        )


        transaction = (
            MpesaTransaction.objects.get(
                order=self.guest_order
            )
        )


        self.assertEqual(
            transaction.checkout_request_id,
            "CHECKOUT-GUEST-001",
        )


        self.assertEqual(
            transaction.amount,
            Decimal("1200.00"),
        )


        mocked_stk_push.assert_called_once()


    @patch(
        "payments.views.stk_push"
    )
    def test_wrong_guest_token_cannot_start_stk(
        self,
        mocked_stk_push,
    ):

        response = self.client.post(
            reverse(
                "guest_initiate_payment",
                args=[
                    self.guest_order.order_number,
                    "wrong-token",
                ],
            ),
            {
                "phone_number":
                    "0712345678",
            },
        )


        self.assertEqual(
            response.status_code,
            404,
        )


        mocked_stk_push.assert_not_called()


        self.assertFalse(
            MpesaTransaction.objects.filter(
                order=self.guest_order
            ).exists()
        )


    def test_guest_can_check_own_payment_status(
        self,
    ):

        MpesaTransaction.objects.create(
            order=self.guest_order,
            phone_number="254712345678",
            amount=Decimal("1200.00"),
            checkout_request_id=(
                "CHECKOUT-STATUS-001"
            ),
            status="success",
            mpesa_receipt_number=(
                "ABC123XYZ"
            ),
        )


        response = self.client.get(
            reverse(
                "guest_check_payment_status",
                args=[
                    self.guest_order.order_number,
                    self.token,
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        payload = response.json()


        self.assertEqual(
            payload["status"],
            "success",
        )


        self.assertEqual(
            payload["receipt"],
            "ABC123XYZ",
        )


    def test_wrong_token_cannot_check_payment_status(
        self,
    ):

        response = self.client.get(
            reverse(
                "guest_check_payment_status",
                args=[
                    self.guest_order.order_number,
                    "wrong-token",
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            404,
        )


    def test_authenticated_payment_route_still_works(
        self,
    ):

        user = User.objects.create_user(
            username="phase13c-member",
            password="pass12345",
            email="member@example.com",
        )


        order = Order.objects.create(
            user=user,
            guest_checkout=False,
            order_number="MEMBER-PAY-001",
            full_name="Member Buyer",
            phone="0712345678",
            email="member@example.com",
            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="1",
            subtotal=Decimal("500.00"),
            total_amount=Decimal("500.00"),
            payment_status="pending",
            inventory_status="reserved",
            delivery_pricing_status="fixed",
        )


        self.client.force_login(
            user
        )


        response = self.client.get(
            reverse(
                "initiate_payment",
                args=[
                    order.order_number
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


    def test_logged_in_customer_cannot_use_normal_route_for_guest_order(
        self,
    ):

        user = User.objects.create_user(
            username="random-member",
            password="pass12345",
        )


        self.client.force_login(
            user
        )


        response = self.client.get(
            reverse(
                "initiate_payment",
                args=[
                    self.guest_order.order_number
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            404,
        )
'''.strip() + "\n",
encoding="utf-8",
)


print()
print("=" * 72)
print("PHASE 13C INSTALLED")
print("=" * 72)
print()
print("Added:")
print("  Secure token-authorized guest M-PESA payment")
print("  Guest STK initiation")
print("  Guest payment-status polling")
print("  Wrong-token protection")
print("  Existing authenticated ownership preserved")
print("  Existing callback flow preserved")
print("  Existing duplicate-STK protection preserved")
print("  Existing inventory reservation logic preserved")
print()
print("No migration required.")
