from pathlib import Path
import shutil


ROOT = Path.cwd()

VIEWS = ROOT / "payments" / "customer_returns.py"
URLS = ROOT / "payments" / "urls.py"

RETURN_TEMPLATE = (
    ROOT / "payments" / "templates" / "payments"
    / "return_request_v2.html"
)

RETURN_DETAIL = (
    ROOT / "payments" / "templates" / "payments"
    / "customer_return_detail.html"
)

REFUND_DETAIL = (
    ROOT / "payments" / "templates" / "payments"
    / "customer_refund_detail.html"
)

REFUND_FORM = (
    ROOT / "templates" / "payments"
    / "refund_request.html"
)

REFUND_SUBMITTED = (
    ROOT / "templates" / "payments"
    / "refund_submitted.html"
)

RETURN_SUBMITTED = (
    ROOT / "templates" / "payments"
    / "return_submitted.html"
)

GUEST_ORDER = (
    ROOT / "templates" / "orders"
    / "guest_order_detail.html"
)

TEST_FILE = (
    ROOT / "payments" / "test_phase13e.py"
)


required = [
    VIEWS,
    URLS,
    RETURN_TEMPLATE,
    RETURN_DETAIL,
    REFUND_DETAIL,
    REFUND_FORM,
    REFUND_SUBMITTED,
    RETURN_SUBMITTED,
    GUEST_ORDER,
]


for path in required:
    if not path.exists():
        raise RuntimeError(
            f"Required file missing: {path}"
        )


for path in required:
    backup = Path(
        str(path) + ".phase13ebackup"
    )

    if not backup.exists():
        shutil.copy2(
            path,
            backup,
        )


# ============================================================
# 1. CUSTOMER_RETURNS.PY
# ============================================================

text = VIEWS.read_text(
    encoding="utf-8-sig"
)


# ------------------------------------------------------------
# Imports
# ------------------------------------------------------------

old = '''from django.http import JsonResponse
'''

new = '''from django.http import JsonResponse, Http404
'''

if old in text:
    text = text.replace(
        old,
        new,
        1,
    )


old = '''from orders.models import Order
'''

new = '''from orders.models import Order

from orders.guest_access import (
    verify_guest_access_token,
)
'''

if (
    old in text
    and
    "verify_guest_access_token" not in text
):

    text = text.replace(
        old,
        new,
        1,
    )


# ------------------------------------------------------------
# Correct refund eligibility semantics.
# Fully refunded orders cannot start another refund.
# ------------------------------------------------------------

old = '''SETTLED_RETURN_PAYMENT_STATUSES = {
    "paid",
    "partially_refunded",
    "refunded",
}
'''

new = '''SETTLED_RETURN_PAYMENT_STATUSES = {
    "paid",
    "partially_refunded",
    "refunded",
}

REFUND_ELIGIBLE_PAYMENT_STATUSES = {
    "paid",
    "partially_refunded",
}
'''

if (
    old in text
    and
    "REFUND_ELIGIBLE_PAYMENT_STATUSES" not in text
):

    text = text.replace(
        old,
        new,
        1,
    )


# Existing customer refund should not accept fully-refunded.
text = text.replace(
    '''order.payment_status not in SETTLED_RETURN_PAYMENT_STATUSES
        or order.status != "delivered"''',
    '''order.payment_status not in REFUND_ELIGIBLE_PAYMENT_STATUSES
        or order.status != "delivered"''',
    1,
)


# ------------------------------------------------------------
# Guest authorization helper
# ------------------------------------------------------------

anchor = '''@login_required
@transaction.atomic
def request_refund(
'''

helper = '''def _get_guest_order(
    order_number,
    token,
    *,
    lock=False,
    prefetch_items=False,
):

    queryset = Order.objects


    if lock:
        queryset = (
            queryset.select_for_update()
        )


    if prefetch_items:
        queryset = (
            queryset.prefetch_related(
                "items"
            )
        )


    order = get_object_or_404(
        queryset,
        order_number=order_number,
        guest_checkout=True,
        user__isnull=True,
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
    "def _get_guest_order(" not in text
):

    text = text.replace(
        anchor,
        helper + anchor,
        1,
    )


# ============================================================
# Guest refund + return views
# ============================================================

guest_views = r'''

@transaction.atomic
def guest_request_refund(
    request,
    order_number,
    token,
):

    order = _get_guest_order(
        order_number,
        token,
        lock=True,
    )


    if (
        order.payment_status
        not in REFUND_ELIGIBLE_PAYMENT_STATUSES
        or
        order.status != "delivered"
    ):

        return JsonResponse(
            {
                "success": False,
                "error": (
                    "Refunds are available only "
                    "for paid delivered orders."
                ),
            },
            status=400,
        )


    refundable_amount = (
        remaining_refundable_amount(
            order,
            include_pending=True,
        )
    )


    if refundable_amount <= 0:

        return JsonResponse(
            {
                "success": False,
                "error": (
                    "This order has no remaining "
                    "refundable balance."
                ),
            },
            status=400,
        )


    if RefundRequest.objects.filter(
        order=order,
        status__in=[
            "requested",
            "approved",
        ],
    ).exists():

        return JsonResponse(
            {
                "success": False,
                "error": (
                    "An active refund request "
                    "already exists."
                ),
            },
            status=400,
        )


    if request.method != "POST":

        form = RefundRequestForm(
            order=order
        )

        form.fields[
            "amount"
        ].initial = (
            refundable_amount
        )


        return render(
            request,
            "payments/refund_request.html",
            {
                "order": order,
                "form": form,
                "refundable_amount":
                    refundable_amount,
                "is_guest_request": True,
                "guest_access_token": token,
            },
        )


    form = RefundRequestForm(
        request.POST,
        order=order,
    )


    if form.is_valid():

        amount = (
            form.cleaned_data[
                "amount"
            ]
        )


        if amount > refundable_amount:

            form.add_error(
                "amount",
                (
                    "Refund amount exceeds the "
                    "remaining refundable balance."
                ),
            )

        else:

            refund = form.save(
                commit=False
            )

            refund.order = order
            refund.save()


            ReturnRefundEvent.objects.create(
                refund=refund,
                status="requested",
                message=(
                    "Guest customer submitted "
                    "refund request."
                ),
                created_by=None,
            )


            return render(
                request,
                "payments/refund_submitted.html",
                {
                    "refund": refund,
                    "is_guest_request": True,
                    "guest_access_token": token,
                },
            )


    return render(
        request,
        "payments/refund_request.html",
        {
            "order": order,
            "form": form,
            "refundable_amount":
                refundable_amount,
            "is_guest_request": True,
            "guest_access_token": token,
        },
    )



@transaction.atomic
def guest_request_return(
    request,
    order_number,
    token,
):

    order = _get_guest_order(
        order_number,
        token,
        lock=True,
        prefetch_items=True,
    )


    if (
        order.payment_status
        not in SETTLED_RETURN_PAYMENT_STATUSES
        or
        order.status != "delivered"
    ):

        return JsonResponse(
            {
                "success": False,
                "error": (
                    "Returns are available only "
                    "for paid delivered orders."
                ),
            },
            status=400,
        )


    if ReturnRequest.objects.filter(
        order=order,
        status__in=[
            "requested",
            "approved",
        ],
    ).exists():

        return JsonResponse(
            {
                "success": False,
                "error": (
                    "An active return request "
                    "already exists."
                ),
            },
            status=400,
        )


    if not return_window_open(
        order
    ):

        return JsonResponse(
            {
                "success": False,
                "error": (
                    "The return period for "
                    "this order has expired."
                ),
            },
            status=400,
        )


    items = list(
        order.items.select_related(
            "product",
            "variant",
        )
    )


    for item in items:

        item.returnable_quantity = (
            remaining_returnable_quantity(
                item
            )
        )


    context = {
        "order": order,
        "items": items,
        "is_guest_request": True,
        "guest_access_token": token,
    }


    if request.method == "POST":

        request_type = (
            request.POST.get(
                "request_type",
                ""
            )
        )


        reason = (
            request.POST.get(
                "reason",
                ""
            ).strip()
        )


        error = None


        if request_type not in {
            "return",
            "replacement",
        }:

            error = (
                "Select Return or Replacement."
            )


        elif not reason:

            error = (
                "Please explain why you are "
                "returning the item."
            )


        else:

            selected = []


            for item in items:

                raw_quantity = (
                    request.POST.get(
                        f"quantity_{item.pk}",
                        "0",
                    )
                )


                try:

                    quantity = int(
                        raw_quantity
                    )

                except (
                    TypeError,
                    ValueError,
                ):

                    quantity = 0


                if quantity < 0:

                    error = (
                        "Return quantity cannot "
                        "be negative."
                    )

                    break


                remaining_quantity = (
                    remaining_returnable_quantity(
                        item
                    )
                )


                if quantity > remaining_quantity:

                    error = (
                        f"Only {remaining_quantity} "
                        f"of {item.product_name} "
                        "remain eligible for return."
                    )

                    break


                if quantity:

                    selected.append(
                        (
                            item,
                            quantity,
                        )
                    )


            if (
                not error
                and
                not selected
                and
                items
            ):

                error = (
                    "Select at least one item "
                    "to return."
                )


        if not error:

            return_request = (
                ReturnRequest.objects.create(
                    order=order,
                    request_type=request_type,
                    reason=reason,
                )
            )


            for item, quantity in selected:

                ReturnRequestItem.objects.create(
                    return_request=
                        return_request,
                    order_item=item,
                    quantity=quantity,
                )


            ReturnRefundEvent.objects.create(
                return_request=
                    return_request,
                status="requested",
                message=(
                    "Guest customer submitted "
                    f"{return_request.get_request_type_display().lower()} "
                    "request."
                ),
                created_by=None,
            )


            return render(
                request,
                "payments/return_submitted.html",
                {
                    "return_request":
                        return_request,
                    "is_guest_request":
                        True,
                    "guest_access_token":
                        token,
                },
            )


        context.update(
            {
                "error": error,
                "request_type":
                    request_type,
                "reason": reason,
            }
        )


    return render(
        request,
        "payments/return_request_v2.html",
        context,
    )



def guest_return_detail(
    request,
    order_number,
    token,
    pk,
):

    order = _get_guest_order(
        order_number,
        token,
    )


    obj = get_object_or_404(
        ReturnRequest.objects
        .filter(
            order=order
        )
        .select_related(
            "order"
        )
        .prefetch_related(
            "items__order_item",
            "events__created_by",
        ),
        pk=pk,
    )


    return render(
        request,
        "payments/customer_return_detail.html",
        {
            "return_request": obj,
            "order": order,
            "return_deadline":
                get_return_deadline(
                    order
                ),
            "is_guest_request": True,
            "guest_access_token": token,
        },
    )



def guest_refund_detail(
    request,
    order_number,
    token,
    pk,
):

    order = _get_guest_order(
        order_number,
        token,
    )


    obj = get_object_or_404(
        RefundRequest.objects
        .filter(
            order=order
        )
        .select_related(
            "order"
        )
        .prefetch_related(
            "events__created_by"
        ),
        pk=pk,
    )


    return render(
        request,
        "payments/customer_refund_detail.html",
        {
            "refund": obj,
            "order": order,
            "is_guest_request": True,
            "guest_access_token": token,
        },
    )

'''

if "def guest_request_refund(" not in text:

    text += guest_views


VIEWS.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# 2. URLS
# ============================================================

text = URLS.read_text(
    encoding="utf-8-sig"
)


marker = '''urlpatterns = [
'''

routes = '''urlpatterns = [
    path(
        "guest/refund/<str:order_number>/<str:token>/",
        customer_returns.guest_request_refund,
        name="guest_request_refund",
    ),

    path(
        "guest/return/<str:order_number>/<str:token>/",
        customer_returns.guest_request_return,
        name="guest_request_return",
    ),

    path(
        "guest/return/<str:order_number>/<str:token>/<int:pk>/",
        customer_returns.guest_return_detail,
        name="guest_return_detail",
    ),

    path(
        "guest/refund/<str:order_number>/<str:token>/<int:pk>/",
        customer_returns.guest_refund_detail,
        name="guest_refund_detail",
    ),

'''

if (
    marker in text
    and
    'name="guest_request_refund"' not in text
):

    text = text.replace(
        marker,
        routes,
        1,
    )


URLS.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# 3. RETURN FORM — guest-safe back link
# ============================================================

text = RETURN_TEMPLATE.read_text(
    encoding="utf-8-sig"
)


old = '''            <a
                href="{% url 'order_detail' order.order_number %}"
                class="btn btn-outline-secondary btn-sm mb-4"
            >
                &larr; Back to Order
            </a>
'''

new = '''            {% if is_guest_request %}

            <a
                href="{% url 'guest_order_detail' order.order_number guest_access_token %}"
                class="btn btn-outline-secondary btn-sm mb-4"
            >
                &larr; Back to Order
            </a>

            {% else %}

            <a
                href="{% url 'order_detail' order.order_number %}"
                class="btn btn-outline-secondary btn-sm mb-4"
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


RETURN_TEMPLATE.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# 4. REFUND FORM
# ============================================================

text = REFUND_FORM.read_text(
    encoding="utf-8-sig"
)


text = text.replace(
    '''<p>Order {{ order.order_number }} · KES {{ order.total_amount }}</p>''',
    '''<p>
        Order {{ order.order_number }} ·
        {{ order.currency_symbol_at_checkout }}
        {{ order.total_amount }}
    </p>

    {% if is_guest_request %}

    <a
        href="{% url 'guest_order_detail' order.order_number guest_access_token %}"
        class="btn btn-outline-secondary btn-sm mb-3"
    >
        &larr; Back to Order
    </a>

    {% endif %}
''',
)


REFUND_FORM.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# 5. SUBMITTED PAGES
# ============================================================

text = REFUND_SUBMITTED.read_text(
    encoding="utf-8-sig"
)


text = text.replace(
    '''We received your request for KES {{ refund.amount }}''',
    '''We received your request for
    {{ refund.order.currency_symbol_at_checkout }}
    {{ refund.amount }}''',
)


old = '''<a href="{% url 'order_detail' refund.order.order_number %}" class="btn btn-outline-secondary">Back to order</a>'''

new = '''{% if is_guest_request %}

<a
    href="{% url 'guest_refund_detail' refund.order.order_number guest_access_token refund.pk %}"
    class="btn btn-primary"
>
    View Refund Status
</a>

<a
    href="{% url 'guest_order_detail' refund.order.order_number guest_access_token %}"
    class="btn btn-outline-secondary"
>
    Back to Order
</a>

{% else %}

<a
    href="{% url 'order_detail' refund.order.order_number %}"
    class="btn btn-outline-secondary"
>
    Back to order
</a>

{% endif %}'''

if old in text:

    text = text.replace(
        old,
        new,
        1,
    )


REFUND_SUBMITTED.write_text(
    text,
    encoding="utf-8",
)


text = RETURN_SUBMITTED.read_text(
    encoding="utf-8-sig"
)


old = '''</p></div>{% endblock %}'''

new = '''</p>

{% if is_guest_request %}

<a
    href="{% url 'guest_return_detail' return_request.order.order_number guest_access_token return_request.pk %}"
    class="btn btn-primary"
>
    View Request Status
</a>

<a
    href="{% url 'guest_order_detail' return_request.order.order_number guest_access_token %}"
    class="btn btn-outline-secondary"
>
    Back to Order
</a>

{% endif %}

</div>
{% endblock %}
'''

if old in text:

    text = text.replace(
        old,
        new,
        1,
    )


RETURN_SUBMITTED.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# 6. DETAIL PAGES — guest-safe navigation
# ============================================================

for path in [
    RETURN_DETAIL,
    REFUND_DETAIL,
]:

    text = path.read_text(
        encoding="utf-8-sig"
    )


    old = '''    <a
        href="{% url 'customer_returns_refunds' %}"
        class="btn btn-outline-secondary btn-sm mb-4"
    >
        &larr; Returns & Refunds
    </a>
'''

    new = '''    {% if is_guest_request %}

    <a
        href="{% url 'guest_order_detail' order.order_number guest_access_token %}"
        class="btn btn-outline-secondary btn-sm mb-4"
    >
        &larr; Back to Order
    </a>

    {% else %}

    <a
        href="{% url 'customer_returns_refunds' %}"
        class="btn btn-outline-secondary btn-sm mb-4"
    >
        &larr; Returns & Refunds
    </a>

    {% endif %}
'''

    if old in text:

        text = text.replace(
            old,
            new,
            1,
        )


    # Historical currency, not hard-coded KES.
    text = text.replace(
        '''KES {{ refund.amount|floatformat:2 }}''',
        '''{{ order.currency_symbol_at_checkout }}
                                {{ refund.amount|floatformat:2 }}''',
    )


    path.write_text(
        text,
        encoding="utf-8",
    )


# ============================================================
# 7. GUEST ORDER PAGE
# ============================================================

text = GUEST_ORDER.read_text(
    encoding="utf-8-sig"
)


anchor = '''            <div class="card shadow-sm">

                <div class="card-body">
'''

block = '''            {% if order.status == "delivered" %}

            <div class="card shadow-sm mb-4">

                <div class="card-body">

                    <h5 class="mb-3">
                        Returns & Refunds
                    </h5>

                    <p class="text-muted">
                        Need help with a delivered order?
                        You can securely submit a return,
                        replacement, or eligible refund request.
                    </p>


                    <div class="d-flex flex-wrap gap-2">

                        {% if order.payment_status == "paid" or order.payment_status == "partially_refunded" or order.payment_status == "refunded" %}

                        <a
                            href="{% url 'guest_request_return' order.order_number guest_access_token %}"
                            class="btn btn-outline-primary"
                        >
                            Return / Replace Items
                        </a>

                        {% endif %}


                        {% if order.payment_status == "paid" or order.payment_status == "partially_refunded" %}

                        <a
                            href="{% url 'guest_request_refund' order.order_number guest_access_token %}"
                            class="btn btn-outline-warning"
                        >
                            Request Refund
                        </a>

                        {% endif %}

                    </div>

                </div>

            </div>

            {% endif %}


''' + anchor


if (
    anchor in text
    and
    "guest_request_refund" not in text
):

    text = text.replace(
        anchor,
        block,
        1,
    )


GUEST_ORDER.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# 8. TESTS
# ============================================================

TEST_FILE.write_text(
r'''
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from categories.models import Category

from products.models import Product

from orders.guest_access import (
    generate_guest_access_token,
    hash_guest_access_token,
)

from orders.models import (
    Order,
    OrderItem,
)

from payments.models import (
    RefundRequest,
    ReturnRequest,
    ReturnRequestItem,
)


class Phase13EGuestReturnsTests(
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
            order_number="GUEST-RET-001",
            full_name="Guest Customer",
            phone="0712345678",
            email="guest@example.com",
            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="1",
            subtotal=Decimal("1000.00"),
            shipping_cost=Decimal("0.00"),
            total_amount=Decimal("1000.00"),
            payment_status="paid",
            status="delivered",
            inventory_status="consumed",
            delivery_pricing_status="fixed",
            currency_code_at_checkout="KES",
            currency_symbol_at_checkout="KSh",
        )


        category = Category.objects.create(
            name="Phase 13E",
            slug="phase-13e",
        )


        product = Product.objects.create(
            category=category,
            name="Guest Return Product",
            slug="guest-return-product",
            sku="GUEST-RET-PROD",
            description="Test",
            price=Decimal("500.00"),
            stock=10,
        )


        self.item = OrderItem.objects.create(
            order=self.order,
            product=product,
            product_name=product.name,
            price=Decimal("500.00"),
            quantity=2,
            subtotal=Decimal("1000.00"),
        )


    def test_guest_can_open_refund_form(
        self,
    ):

        response = self.client.get(
            reverse(
                "guest_request_refund",
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


    def test_wrong_token_cannot_open_refund(
        self,
    ):

        response = self.client.get(
            reverse(
                "guest_request_refund",
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


    def test_guest_can_submit_refund(
        self,
    ):

        response = self.client.post(
            reverse(
                "guest_request_refund",
                args=[
                    self.order.order_number,
                    self.token,
                ],
            ),
            {
                "amount": "300.00",
                "reason":
                    "Item did not meet expectations.",
            },
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        refund = RefundRequest.objects.get(
            order=self.order
        )


        self.assertEqual(
            refund.amount,
            Decimal("300.00"),
        )


        event = refund.events.get()


        self.assertIsNone(
            event.created_by
        )


    def test_fully_refunded_order_cannot_request_another_refund(
        self,
    ):

        self.order.payment_status = "refunded"

        self.order.save(
            update_fields=[
                "payment_status"
            ]
        )


        response = self.client.get(
            reverse(
                "guest_request_refund",
                args=[
                    self.order.order_number,
                    self.token,
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            400,
        )


    def test_guest_can_open_return_form(
        self,
    ):

        response = self.client.get(
            reverse(
                "guest_request_return",
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


    def test_guest_can_submit_item_return(
        self,
    ):

        response = self.client.post(
            reverse(
                "guest_request_return",
                args=[
                    self.order.order_number,
                    self.token,
                ],
            ),
            {
                "request_type": "return",
                "reason": "Wrong size.",
                f"quantity_{self.item.pk}":
                    "1",
            },
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        request_obj = (
            ReturnRequest.objects.get(
                order=self.order
            )
        )


        line = (
            ReturnRequestItem.objects.get(
                return_request=request_obj
            )
        )


        self.assertEqual(
            line.order_item,
            self.item,
        )


        self.assertEqual(
            line.quantity,
            1,
        )


        self.assertIsNone(
            request_obj.events.get().created_by
        )


    def test_wrong_token_cannot_submit_return(
        self,
    ):

        response = self.client.post(
            reverse(
                "guest_request_return",
                args=[
                    self.order.order_number,
                    "wrong-token",
                ],
            ),
            {
                "request_type": "return",
                "reason": "Wrong size.",
                f"quantity_{self.item.pk}":
                    "1",
            },
        )


        self.assertEqual(
            response.status_code,
            404,
        )


        self.assertFalse(
            ReturnRequest.objects.filter(
                order=self.order
            ).exists()
        )


    def test_guest_cannot_return_more_than_purchased(
        self,
    ):

        response = self.client.post(
            reverse(
                "guest_request_return",
                args=[
                    self.order.order_number,
                    self.token,
                ],
            ),
            {
                "request_type": "return",
                "reason": "Test.",
                f"quantity_{self.item.pk}":
                    "3",
            },
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertContains(
            response,
            "remain eligible for return",
        )


        self.assertFalse(
            ReturnRequest.objects.filter(
                order=self.order
            ).exists()
        )


    def test_guest_can_view_own_refund_status(
        self,
    ):

        refund = RefundRequest.objects.create(
            order=self.order,
            amount=Decimal("100.00"),
            reason="Test",
        )


        response = self.client.get(
            reverse(
                "guest_refund_detail",
                args=[
                    self.order.order_number,
                    self.token,
                    refund.pk,
                ],
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


    def test_token_for_one_order_cannot_view_another_orders_refund(
        self,
    ):

        other_token = (
            generate_guest_access_token()
        )


        other = Order.objects.create(
            user=None,
            guest_checkout=True,
            guest_access_token_hash=(
                hash_guest_access_token(
                    other_token
                )
            ),
            order_number="GUEST-RET-002",
            full_name="Other Guest",
            phone="0700000000",
            email="other@example.com",
            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="2",
            subtotal=Decimal("100.00"),
            total_amount=Decimal("100.00"),
            payment_status="paid",
            status="delivered",
        )


        refund = RefundRequest.objects.create(
            order=other,
            amount=Decimal("50.00"),
            reason="Other",
        )


        response = self.client.get(
            reverse(
                "guest_refund_detail",
                args=[
                    other.order_number,
                    self.token,
                    refund.pk,
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
print("PHASE 13E INSTALLED")
print("=" * 72)
print()
print("Added:")
print("  Guest refund requests")
print("  Guest item return/replacement requests")
print("  Secure guest refund status")
print("  Secure guest return status")
print("  Cross-order token protection")
print("  Existing return-window protection preserved")
print("  Existing item quantity protection preserved")
print("  Existing admin processing preserved")
print("  Fully refunded orders cannot request another refund")
print()
print("No migration required.")
