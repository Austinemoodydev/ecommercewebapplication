from pathlib import Path
import shutil


ROOT = Path.cwd()

ACCOUNTS_VIEWS = ROOT / "accounts" / "views.py"
ACCOUNTS_URLS = ROOT / "accounts" / "urls.py"
GUEST_ORDER = (
    ROOT / "templates" / "orders"
    / "guest_order_detail.html"
)

CLAIM_TEMPLATE = (
    ROOT / "templates" / "accounts"
    / "claim_guest_order.html"
)

TEST_FILE = (
    ROOT / "accounts" / "test_phase13f.py"
)


for path in [
    ACCOUNTS_VIEWS,
    ACCOUNTS_URLS,
    GUEST_ORDER,
]:

    if not path.exists():

        raise RuntimeError(
            f"Missing required file: {path}"
        )


for path in [
    ACCOUNTS_VIEWS,
    ACCOUNTS_URLS,
    GUEST_ORDER,
]:

    backup = Path(
        str(path) + ".phase13fbackup"
    )

    if not backup.exists():

        shutil.copy2(
            path,
            backup,
        )


# ============================================================
# 1. ACCOUNTS/VIEWS.PY IMPORTS
# ============================================================

text = ACCOUNTS_VIEWS.read_text(
    encoding="utf-8-sig"
)


old = '''from django.shortcuts import get_object_or_404, redirect, render
'''

new = '''from django.shortcuts import get_object_or_404, redirect, render
from django.http import Http404
from django.db import transaction
from django.contrib import messages
'''

if old in text:

    text = text.replace(
        old,
        new,
        1,
    )


marker = '''from .models import Address
'''

replacement = '''from .models import Address

from orders.models import Order

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


# ============================================================
# 2. SECURE CLAIM HELPERS
# ============================================================

anchor = '''def register(request):
'''

helpers = '''PENDING_GUEST_ORDER_KEY = (
    "pending_guest_order_claim"
)



def _get_guest_order_for_claim(
    order_number,
    token,
    *,
    lock=False,
):

    queryset = Order.objects


    if lock:

        queryset = (
            queryset.select_for_update()
        )


    order = get_object_or_404(
        queryset,
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



def _store_pending_guest_claim(
    request,
    order_number,
    token,
):

    # Validate BEFORE storing anything
    # in the session.

    _get_guest_order_for_claim(
        order_number,
        token,
    )


    request.session[
        PENDING_GUEST_ORDER_KEY
    ] = {
        "order_number": order_number,
        "token": token,
    }


    request.session.modified = True



@transaction.atomic
def _claim_guest_order(
    user,
    order_number,
    token,
):

    order = _get_guest_order_for_claim(
        order_number,
        token,
        lock=True,
    )


    # Account must be active and email
    # verified before ownership transfer.

    if (
        not user.is_active
        or
        not user.email_verified
    ):

        raise PermissionError(
            "Verify your email before "
            "linking this order."
        )


    order.user = user

    order.guest_checkout = False

    # Destroy the guest credential.
    # The old private URL stops working
    # immediately after this commit.

    order.guest_access_token_hash = ""


    order.save(
        update_fields=[
            "user",
            "guest_checkout",
            "guest_access_token_hash",
            "updated_at",
        ]
    )


    return order



def _claim_pending_order_if_possible(
    request,
    user,
):

    pending = request.session.get(
        PENDING_GUEST_ORDER_KEY
    )


    if not pending:

        return None


    order_number = pending.get(
        "order_number"
    )

    token = pending.get(
        "token"
    )


    if not order_number or not token:

        request.session.pop(
            PENDING_GUEST_ORDER_KEY,
            None,
        )

        return None


    try:

        order = _claim_guest_order(
            user,
            order_number,
            token,
        )

    except (
        Http404,
        PermissionError,
    ):

        return None


    request.session.pop(
        PENDING_GUEST_ORDER_KEY,
        None,
    )


    return order



'''

if (
    anchor in text
    and
    "_claim_guest_order(" not in text
):

    text = text.replace(
        anchor,
        helpers + anchor,
        1,
    )


# ============================================================
# 3. REGISTRATION — ACCEPT PENDING CLAIM
# ============================================================

old = '''def register(request):
    form = RegisterForm(request.POST or None)
'''

new = '''def register(request):

    claim_order = request.GET.get(
        "claim_order"
    )

    claim_token = request.GET.get(
        "claim_token"
    )


    if claim_order and claim_token:

        _store_pending_guest_claim(
            request,
            claim_order,
            claim_token,
        )


    form = RegisterForm(
        request.POST or None
    )
'''

if old in text:

    text = text.replace(
        old,
        new,
        1,
    )

elif "claim_order = request.GET.get" not in text:

    raise RuntimeError(
        "Could not update register view."
    )


# ============================================================
# 4. EMAIL VERIFICATION — CLAIM AFTER VERIFICATION
# ============================================================

old = '''    user.is_active = True
    user.email_verified = True
    user.save(update_fields=["is_active", "email_verified"])
    return render(request, "accounts/verify_email.html", {"verified": True})
'''

new = '''    user.is_active = True
    user.email_verified = True

    user.save(
        update_fields=[
            "is_active",
            "email_verified",
        ]
    )


    claimed_order = (
        _claim_pending_order_if_possible(
            request,
            user,
        )
    )


    return render(
        request,
        "accounts/verify_email.html",
        {
            "verified": True,
            "claimed_order":
                claimed_order,
        },
    )
'''

if old in text:

    text = text.replace(
        old,
        new,
        1,
    )

elif "claimed_order" not in text:

    raise RuntimeError(
        "Could not update verify_email."
    )


# ============================================================
# 5. CLAIM VIEW
# ============================================================

claim_view = '''

@ratelimit(
    key="ip",
    rate="10/m",
    method="POST",
    block=True,
)
def claim_guest_order(
    request,
    order_number,
    token,
):

    order = _get_guest_order_for_claim(
        order_number,
        token,
    )


    if not request.user.is_authenticated:

        _store_pending_guest_claim(
            request,
            order_number,
            token,
        )


        if request.method == "POST":

            return redirect(
                (
                    f"{reverse('login')}"
                    f"?next="
                    f"{reverse('claim_guest_order', args=[order_number, token])}"
                )
            )


        return render(
            request,
            "accounts/claim_guest_order.html",
            {
                "order": order,
                "guest_access_token":
                    token,
            },
        )


    if not request.user.email_verified:

        messages.error(
            request,
            (
                "Verify your account email "
                "before linking this order."
            ),
        )


        return render(
            request,
            "accounts/claim_guest_order.html",
            {
                "order": order,
                "guest_access_token":
                    token,
                "requires_verification":
                    True,
            },
            status=403,
        )


    if request.method != "POST":

        return render(
            request,
            "accounts/claim_guest_order.html",
            {
                "order": order,
                "guest_access_token":
                    token,
            },
        )


    try:

        claimed_order = (
            _claim_guest_order(
                request.user,
                order_number,
                token,
            )
        )

    except PermissionError:

        return render(
            request,
            "accounts/claim_guest_order.html",
            {
                "order": order,
                "guest_access_token":
                    token,
                "requires_verification":
                    True,
            },
            status=403,
        )


    request.session.pop(
        PENDING_GUEST_ORDER_KEY,
        None,
    )


    messages.success(
        request,
        (
            f"Order "
            f"{claimed_order.order_number} "
            "has been linked to your account."
        ),
    )


    return redirect(
        "order_detail",
        order_number=(
            claimed_order.order_number
        ),
    )

'''

if "def claim_guest_order(" not in text:

    text += claim_view


ACCOUNTS_VIEWS.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# 6. ACCOUNTS URL
# ============================================================

text = ACCOUNTS_URLS.read_text(
    encoding="utf-8-sig"
)


marker = '''urlpatterns = [
'''

replacement = '''urlpatterns = [
    path(
        "claim-order/<str:order_number>/<str:token>/",
        views.claim_guest_order,
        name="claim_guest_order",
    ),
'''

if (
    marker in text
    and
    'name="claim_guest_order"' not in text
):

    text = text.replace(
        marker,
        replacement,
        1,
    )


ACCOUNTS_URLS.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# 7. CLAIM TEMPLATE
# ============================================================

CLAIM_TEMPLATE.parent.mkdir(
    parents=True,
    exist_ok=True,
)


CLAIM_TEMPLATE.write_text(
r'''
{% extends "base.html" %}

{% block title %}
Link Order to Account
{% endblock %}


{% block content %}

<div class="container py-5">

    <div class="row justify-content-center">

        <div class="col-lg-7">

            <div class="card shadow-sm">

                <div class="card-body p-4">

                    <h3 class="mb-3">
                        Link Order to Your Account
                    </h3>


                    <p class="text-muted">

                        Order

                        <strong>
                            {{ order.order_number }}
                        </strong>

                        can be moved from guest checkout
                        into your customer account.

                    </p>


                    <div class="alert alert-info">

                        Once linked, this private guest
                        link will stop working. You will
                        access the order from My Orders.

                    </div>


                    {% if requires_verification %}

                    <div class="alert alert-warning">

                        Your account email must be
                        verified before this order can
                        be linked.

                    </div>

                    {% endif %}


                    {% if request.user.is_authenticated %}

                        {% if request.user.email_verified %}

                        <form method="post">

                            {% csrf_token %}

                            <button
                                type="submit"
                                class="btn btn-primary"
                            >
                                Link Order to My Account
                            </button>


                            <a
                                href="{% url 'guest_order_detail' order.order_number guest_access_token %}"
                                class="btn btn-outline-secondary"
                            >
                                Cancel
                            </a>

                        </form>

                        {% else %}

                        <a
                            href="{% url 'guest_order_detail' order.order_number guest_access_token %}"
                            class="btn btn-outline-secondary"
                        >
                            Back to Order
                        </a>

                        {% endif %}


                    {% else %}

                    <div class="d-grid gap-2">

                        <form method="post">

                            {% csrf_token %}

                            <button
                                type="submit"
                                class="btn btn-primary w-100"
                            >
                                I Already Have an Account
                            </button>

                        </form>


                        <a
                            href="{% url 'register' %}?claim_order={{ order.order_number|urlencode }}&claim_token={{ guest_access_token|urlencode }}"
                            class="btn btn-success"
                        >
                            Create Account
                        </a>


                        <a
                            href="{% url 'guest_order_detail' order.order_number guest_access_token %}"
                            class="btn btn-outline-secondary"
                        >
                            Back to Guest Order
                        </a>

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
# 8. GUEST ORDER BUTTON
# ============================================================

text = GUEST_ORDER.read_text(
    encoding="utf-8-sig"
)


# Insert immediately before the financial totals card.
anchor = '''            <div class="card shadow-sm">

                <div class="card-body">
'''

account_block = '''            <div class="card shadow-sm mb-4">

                <div class="card-body">

                    <div
                        class="d-flex flex-column flex-md-row
                        justify-content-between
                        align-items-md-center gap-3"
                    >

                        <div>

                            <h5 class="mb-1">
                                Want easier order access?
                            </h5>

                            <div class="text-muted">

                                Create an account or sign in
                                and securely add this guest
                                order to My Orders.

                            </div>

                        </div>


                        <a
                            href="{% url 'claim_guest_order' order.order_number guest_access_token %}"
                            class="btn btn-primary"
                        >
                            Link to My Account
                        </a>

                    </div>

                </div>

            </div>


''' + anchor


if (
    anchor in text
    and
    "claim_guest_order" not in text
):

    text = text.replace(
        anchor,
        account_block,
        1,
    )


GUEST_ORDER.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# 9. TESTS
# ============================================================

TEST_FILE.write_text(
r'''
from decimal import Decimal

from django.contrib.auth import (
    get_user_model,
)

from django.test import TestCase
from django.urls import reverse

from orders.guest_access import (
    generate_guest_access_token,
    hash_guest_access_token,
)

from orders.models import Order


User = get_user_model()


class Phase13FGuestOrderClaimTests(
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
            order_number="GUEST-CLAIM-001",
            full_name="Guest Buyer",
            phone="0712345678",
            email="guest@example.com",
            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="1",
            subtotal=Decimal("500.00"),
            total_amount=Decimal("500.00"),
            payment_status="paid",
            status="confirmed",
            inventory_status="consumed",
            delivery_pricing_status="fixed",
        )


        self.user = (
            User.objects.create_user(
                username="verified-customer",
                email="different@example.com",
                password="pass12345",
                is_active=True,
                email_verified=True,
            )
        )


    def claim_url(
        self,
        token=None,
    ):

        return reverse(
            "claim_guest_order",
            args=[
                self.order.order_number,
                token or self.token,
            ],
        )


    def test_guest_order_page_has_link_account_button(
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


        self.assertContains(
            response,
            self.claim_url(),
        )


    def test_wrong_token_cannot_open_claim_page(
        self,
    ):

        response = self.client.get(
            self.claim_url(
                "wrong-token"
            )
        )


        self.assertEqual(
            response.status_code,
            404,
        )


    def test_anonymous_user_can_open_claim_choice(
        self,
    ):

        response = self.client.get(
            self.claim_url()
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertContains(
            response,
            "Create Account",
        )


    def test_authenticated_verified_user_can_claim_order(
        self,
    ):

        self.client.force_login(
            self.user
        )


        response = self.client.post(
            self.claim_url()
        )


        self.assertEqual(
            response.status_code,
            302,
        )


        self.order.refresh_from_db()


        self.assertEqual(
            self.order.user,
            self.user,
        )


        self.assertFalse(
            self.order.guest_checkout
        )


        self.assertEqual(
            self.order.guest_access_token_hash,
            "",
        )


    def test_email_does_not_need_to_match_order(
        self,
    ):

        # Ownership is proven by possession
        # of the high-entropy guest token,
        # not by email equality.

        self.assertNotEqual(
            self.user.email,
            self.order.email,
        )


        self.client.force_login(
            self.user
        )


        response = self.client.post(
            self.claim_url()
        )


        self.assertEqual(
            response.status_code,
            302,
        )


        self.order.refresh_from_db()


        self.assertEqual(
            self.order.user,
            self.user,
        )


    def test_unverified_account_cannot_claim(
        self,
    ):

        user = User.objects.create_user(
            username="unverified",
            email="guest@example.com",
            password="pass12345",
            is_active=True,
            email_verified=False,
        )


        self.client.force_login(
            user
        )


        response = self.client.post(
            self.claim_url()
        )


        self.assertEqual(
            response.status_code,
            403,
        )


        self.order.refresh_from_db()


        self.assertIsNone(
            self.order.user
        )


        self.assertTrue(
            self.order.guest_checkout
        )


    def test_old_guest_url_stops_working_after_claim(
        self,
    ):

        guest_url = reverse(
            "guest_order_detail",
            args=[
                self.order.order_number,
                self.token,
            ],
        )


        self.client.force_login(
            self.user
        )


        self.client.post(
            self.claim_url()
        )


        self.client.logout()


        response = self.client.get(
            guest_url
        )


        self.assertEqual(
            response.status_code,
            404,
        )


    def test_claim_cannot_be_repeated(
        self,
    ):

        self.client.force_login(
            self.user
        )


        self.client.post(
            self.claim_url()
        )


        response = self.client.post(
            self.claim_url()
        )


        self.assertEqual(
            response.status_code,
            404,
        )


    def test_second_account_cannot_take_claimed_order(
        self,
    ):

        second = User.objects.create_user(
            username="second-customer",
            email="second@example.com",
            password="pass12345",
            is_active=True,
            email_verified=True,
        )


        self.client.force_login(
            self.user
        )


        self.client.post(
            self.claim_url()
        )


        self.client.force_login(
            second
        )


        response = self.client.post(
            self.claim_url()
        )


        self.assertEqual(
            response.status_code,
            404,
        )


        self.order.refresh_from_db()


        self.assertEqual(
            self.order.user,
            self.user,
        )


    def test_claimed_order_is_available_through_customer_order_detail(
        self,
    ):

        self.client.force_login(
            self.user
        )


        self.client.post(
            self.claim_url()
        )


        response = self.client.get(
            reverse(
                "order_detail",
                args=[
                    self.order.order_number
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


    def test_register_claim_parameters_are_validated_before_session_storage(
        self,
    ):

        response = self.client.get(
            reverse("register")
            + (
                "?claim_order="
                + self.order.order_number
                + "&claim_token=wrong-token"
            )
        )


        self.assertEqual(
            response.status_code,
            404,
        )


        self.assertNotIn(
            "pending_guest_order_claim",
            self.client.session,
        )


    def test_valid_register_claim_is_saved_in_session(
        self,
    ):

        response = self.client.get(
            reverse("register")
            + (
                "?claim_order="
                + self.order.order_number
                + "&claim_token="
                + self.token
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        pending = (
            self.client.session.get(
                "pending_guest_order_claim"
            )
        )


        self.assertIsNotNone(
            pending
        )


        self.assertEqual(
            pending["order_number"],
            self.order.order_number,
        )
'''.strip() + "\n",
encoding="utf-8",
)


print()
print("=" * 72)
print("PHASE 13F INSTALLED")
print("=" * 72)
print()
print("Added:")
print("  Optional guest-order account linking")
print("  Existing-account login path")
print("  New-account registration path")
print("  Email verification required before ownership transfer")
print("  Database row locking during claim")
print("  Guest token revalidated during claim")
print("  Guest token destroyed after successful claim")
print("  Old guest URL invalid after claim")
print("  Second-account takeover prevented")
print("  No email-only automatic linking")
print()
print("No migration required.")
