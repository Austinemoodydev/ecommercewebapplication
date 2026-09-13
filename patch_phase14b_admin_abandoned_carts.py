from pathlib import Path
import shutil


ROOT = Path.cwd()

CART_MODEL = ROOT / "cart" / "models.py"
DASHBOARD_URLS = ROOT / "dashboard" / "urls.py"
ADMIN_BASE = (
    ROOT / "templates" / "dashboard"
    / "admin" / "base.html"
)

ABANDONED_VIEWS = (
    ROOT / "dashboard"
    / "abandoned_cart_views.py"
)

LIST_TEMPLATE = (
    ROOT / "templates" / "dashboard"
    / "admin" / "abandoned_carts"
    / "list.html"
)

DETAIL_TEMPLATE = (
    ROOT / "templates" / "dashboard"
    / "admin" / "abandoned_carts"
    / "detail.html"
)

TEST_FILE = (
    ROOT / "dashboard"
    / "test_phase14b.py"
)


# ============================================================
# VERIFY PHASE 14A
# ============================================================

if not CART_MODEL.exists():
    raise RuntimeError(
        "cart/models.py not found."
    )


cart_model_text = CART_MODEL.read_text(
    encoding="utf-8-sig"
)


required_fields = [
    "last_activity_at",
    "checkout_started_at",
    "converted_at",
]


missing = [
    field
    for field in required_fields
    if field not in cart_model_text
]


if missing:
    raise RuntimeError(
        "Phase 14A is not installed. "
        f"Missing Cart fields: {missing}"
    )


# ============================================================
# BACKUPS
# ============================================================

for path in [
    DASHBOARD_URLS,
    ADMIN_BASE,
]:

    if not path.exists():
        raise RuntimeError(
            f"Missing required file: {path}"
        )

    backup = Path(
        str(path) + ".phase14bbackup"
    )

    if not backup.exists():
        shutil.copy2(
            path,
            backup,
        )


# ============================================================
# ADMIN ABANDONED CART VIEWS
# ============================================================

ABANDONED_VIEWS.write_text(
r'''
from decimal import Decimal

from django.contrib.admin.views.decorators import (
    staff_member_required,
)

from django.core.paginator import Paginator

from django.db.models import (
    Prefetch,
    Q,
)

from django.shortcuts import (
    get_object_or_404,
    render,
)

from django.utils import timezone


from cart.models import (
    Cart,
    CartItem,
)

from cart.selectors.abandoned_cart_selector import (
    AbandonedCartSelector,
)


def _cart_items_queryset():

    return (
        CartItem.objects
        .select_related(
            "product",
            "variant",
        )
        .order_by(
            "created_at",
            "id",
        )
    )



def _decorate_cart(
    cart,
    *,
    now=None,
):

    if now is None:
        now = timezone.now()


    items = list(
        cart.items.all()
    )


    cart.admin_items = items

    cart.admin_item_count = sum(
        item.quantity
        for item in items
    )


    cart.admin_value = sum(
        (
            item.subtotal
            for item in items
        ),
        Decimal("0.00"),
    )


    if cart.last_activity_at:

        age = (
            now
            - cart.last_activity_at
        )

        total_seconds = max(
            int(age.total_seconds()),
            0,
        )

        cart.admin_age_hours = (
            total_seconds // 3600
        )

        cart.admin_age_days = (
            cart.admin_age_hours // 24
        )

    else:

        cart.admin_age_hours = 0
        cart.admin_age_days = 0


    cart.admin_customer_type = (
        "Customer"
        if cart.user_id
        else
        "Guest"
    )


    if cart.user_id:

        cart.admin_identity = (
            cart.user.get_full_name()
            or
            cart.user.email
            or
            cart.user.username
        )

    else:

        cart.admin_identity = (
            "Guest session"
        )


    return cart



def _base_abandoned_queryset():

    return (
        AbandonedCartSelector
        .abandoned()
        .select_related(
            "user"
        )
        .prefetch_related(
            Prefetch(
                "items",
                queryset=(
                    _cart_items_queryset()
                ),
            )
        )
    )



@staff_member_required
def admin_abandoned_cart_list(
    request,
):

    queryset = (
        _base_abandoned_queryset()
    )


    customer_type = (
        request.GET.get(
            "type",
            "",
        ).strip()
    )


    checkout_state = (
        request.GET.get(
            "checkout",
            "",
        ).strip()
    )


    search = (
        request.GET.get(
            "q",
            "",
        ).strip()
    )


    if customer_type == "customer":

        queryset = queryset.filter(
            user__isnull=False
        )


    elif customer_type == "guest":

        queryset = queryset.filter(
            user__isnull=True
        )


    if checkout_state == "started":

        queryset = queryset.filter(
            checkout_started_at__isnull=False
        )


    elif checkout_state == "not_started":

        queryset = queryset.filter(
            checkout_started_at__isnull=True
        )


    if search:

        queryset = queryset.filter(
            Q(
                user__username__icontains=
                    search
            )
            |
            Q(
                user__email__icontains=
                    search
            )
            |
            Q(
                user__first_name__icontains=
                    search
            )
            |
            Q(
                user__last_name__icontains=
                    search
            )
            |
            Q(
                session_key__icontains=
                    search
            )
            |
            Q(
                items__product__name__icontains=
                    search
            )
            |
            Q(
                items__product__sku__icontains=
                    search
            )
        ).distinct()


    queryset = queryset.order_by(
        "last_activity_at",
        "pk",
    )


    all_abandoned = list(
        _base_abandoned_queryset()
    )


    now = timezone.now()


    total_value = Decimal(
        "0.00"
    )

    registered_count = 0
    guest_count = 0
    checkout_started_count = 0


    for cart in all_abandoned:

        _decorate_cart(
            cart,
            now=now,
        )


        total_value += (
            cart.admin_value
        )


        if cart.user_id:

            registered_count += 1

        else:

            guest_count += 1


        if cart.checkout_started_at:

            checkout_started_count += 1


    paginator = Paginator(
        queryset,
        25,
    )


    page = paginator.get_page(
        request.GET.get("page")
    )


    for cart in page.object_list:

        _decorate_cart(
            cart,
            now=now,
        )


    context = {
        "page_obj":
            page,

        "carts":
            page.object_list,

        "total_abandoned":
            len(all_abandoned),

        "total_value":
            total_value,

        "registered_count":
            registered_count,

        "guest_count":
            guest_count,

        "checkout_started_count":
            checkout_started_count,

        "selected_type":
            customer_type,

        "selected_checkout":
            checkout_state,

        "search":
            search,
    }


    return render(
        request,
        (
            "dashboard/admin/"
            "abandoned_carts/list.html"
        ),
        context,
    )



@staff_member_required
def admin_abandoned_cart_detail(
    request,
    pk,
):

    abandoned_ids = (
        AbandonedCartSelector
        .abandoned()
        .values_list(
            "pk",
            flat=True,
        )
    )


    cart = get_object_or_404(
        Cart.objects
        .select_related(
            "user"
        )
        .prefetch_related(
            Prefetch(
                "items",
                queryset=(
                    _cart_items_queryset()
                ),
            )
        ),
        pk=pk,
        pk__in=abandoned_ids,
    )


    _decorate_cart(
        cart
    )


    return render(
        request,
        (
            "dashboard/admin/"
            "abandoned_carts/detail.html"
        ),
        {
            "cart": cart,
        },
    )
'''.strip() + "\n",
encoding="utf-8",
)


# ============================================================
# DASHBOARD URLS
# ============================================================

text = DASHBOARD_URLS.read_text(
    encoding="utf-8-sig"
)


if (
    "abandoned_cart_views"
    not in text
):

    text = text.replace(
        '''from . import reports_views
''',
        '''from . import reports_views
from . import abandoned_cart_views
''',
        1,
    )


anchor = '''    # =========================================================
    # ORDER MANAGEMENT
    # =========================================================
'''


routes = '''    # =========================================================
    # ABANDONED CARTS
    # =========================================================

    path(
        "admin/abandoned-carts/",
        abandoned_cart_views.admin_abandoned_cart_list,
        name="admin_abandoned_cart_list",
    ),

    path(
        "admin/abandoned-carts/<int:pk>/",
        abandoned_cart_views.admin_abandoned_cart_detail,
        name="admin_abandoned_cart_detail",
    ),


''' + anchor


if (
    anchor in text
    and
    'name="admin_abandoned_cart_list"'
    not in text
):

    text = text.replace(
        anchor,
        routes,
        1,
    )


DASHBOARD_URLS.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# ADMIN SIDEBAR
# ============================================================

text = ADMIN_BASE.read_text(
    encoding="utf-8-sig"
)


anchor = '''            <!-- PRODUCTS -->

            <a
                href="{% url 'admin_product_list' %}"
'''


sidebar = '''            <!-- ABANDONED CARTS -->

            <a
                href="{% url 'admin_abandoned_cart_list' %}"
                class="
                    sidebar-link
                    {% if 'admin_abandoned_cart' in request.resolver_match.url_name %}
                        active
                    {% endif %}
                "
            >

                <i class="bi bi-cart-x"></i>

                <span>
                    Abandoned Carts
                </span>

            </a>


            <!-- PRODUCTS -->

            <a
                href="{% url 'admin_product_list' %}"
'''


if (
    anchor in text
    and
    "admin_abandoned_cart_list"
    not in text
):

    text = text.replace(
        anchor,
        sidebar,
        1,
    )


ADMIN_BASE.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# LIST TEMPLATE
# ============================================================

LIST_TEMPLATE.parent.mkdir(
    parents=True,
    exist_ok=True,
)


LIST_TEMPLATE.write_text(
r'''
{% extends "dashboard/admin/base.html" %}

{% block title %}
Abandoned Carts
{% endblock %}


{% block content %}

<div class="container-fluid">

    <div
        class="d-flex flex-column flex-lg-row
        justify-content-between
        align-items-lg-center
        gap-3 mb-4"
    >

        <div>

            <h2 class="mb-1">
                Abandoned Carts
            </h2>

            <p class="text-muted mb-0">

                Carts that still contain products,
                have not converted to an order,
                and have passed the abandonment
                threshold.

            </p>

        </div>

    </div>


    <!-- METRICS -->

    <div class="row g-3 mb-4">

        <div class="col-md-6 col-xl-3">

            <div class="card shadow-sm h-100">

                <div class="card-body">

                    <div
                        class="text-muted small
                        text-uppercase"
                    >
                        Abandoned Carts
                    </div>

                    <div class="fs-3 fw-bold">
                        {{ total_abandoned }}
                    </div>

                </div>

            </div>

        </div>


        <div class="col-md-6 col-xl-3">

            <div class="card shadow-sm h-100">

                <div class="card-body">

                    <div
                        class="text-muted small
                        text-uppercase"
                    >
                        Cart Value
                    </div>

                    <div class="fs-3 fw-bold">
                        {{ store_settings.currency_symbol }}
                        {{ total_value|floatformat:2 }}
                    </div>

                </div>

            </div>

        </div>


        <div class="col-md-6 col-xl-3">

            <div class="card shadow-sm h-100">

                <div class="card-body">

                    <div
                        class="text-muted small
                        text-uppercase"
                    >
                        Customers / Guests
                    </div>

                    <div class="fs-4 fw-bold">
                        {{ registered_count }}
                        /
                        {{ guest_count }}
                    </div>

                </div>

            </div>

        </div>


        <div class="col-md-6 col-xl-3">

            <div class="card shadow-sm h-100">

                <div class="card-body">

                    <div
                        class="text-muted small
                        text-uppercase"
                    >
                        Reached Checkout
                    </div>

                    <div class="fs-3 fw-bold">
                        {{ checkout_started_count }}
                    </div>

                </div>

            </div>

        </div>

    </div>


    <!-- FILTERS -->

    <div class="card shadow-sm mb-4">

        <div class="card-body">

            <form
                method="get"
                class="row g-3 align-items-end"
            >

                <div class="col-lg-5">

                    <label
                        class="form-label"
                    >
                        Search
                    </label>

                    <input
                        type="search"
                        name="q"
                        value="{{ search }}"
                        class="form-control"
                        placeholder="Customer, email, product, SKU or session"
                    >

                </div>


                <div class="col-md-3">

                    <label
                        class="form-label"
                    >
                        Cart Type
                    </label>

                    <select
                        name="type"
                        class="form-select"
                    >

                        <option value="">
                            All
                        </option>

                        <option
                            value="customer"
                            {% if selected_type == "customer" %}
                                selected
                            {% endif %}
                        >
                            Registered Customers
                        </option>

                        <option
                            value="guest"
                            {% if selected_type == "guest" %}
                                selected
                            {% endif %}
                        >
                            Guests
                        </option>

                    </select>

                </div>


                <div class="col-md-3">

                    <label
                        class="form-label"
                    >
                        Checkout
                    </label>

                    <select
                        name="checkout"
                        class="form-select"
                    >

                        <option value="">
                            All
                        </option>

                        <option
                            value="started"
                            {% if selected_checkout == "started" %}
                                selected
                            {% endif %}
                        >
                            Checkout Started
                        </option>

                        <option
                            value="not_started"
                            {% if selected_checkout == "not_started" %}
                                selected
                            {% endif %}
                        >
                            Checkout Not Started
                        </option>

                    </select>

                </div>


                <div class="col-lg-1">

                    <button
                        type="submit"
                        class="btn btn-primary w-100"
                    >
                        Filter
                    </button>

                </div>

            </form>

        </div>

    </div>


    <!-- TABLE -->

    <div class="card shadow-sm">

        <div class="card-body p-0">

            <div class="table-responsive">

                <table
                    class="table table-hover
                    align-middle mb-0"
                >

                    <thead>

                        <tr>

                            <th>
                                Cart
                            </th>

                            <th>
                                Customer
                            </th>

                            <th>
                                Items
                            </th>

                            <th>
                                Value
                            </th>

                            <th>
                                Checkout
                            </th>

                            <th>
                                Last Activity
                            </th>

                            <th>
                                Age
                            </th>

                            <th></th>

                        </tr>

                    </thead>


                    <tbody>

                        {% for cart in carts %}

                        <tr>

                            <td>

                                <strong>
                                    #{{ cart.pk }}
                                </strong>

                                <div
                                    class="small text-muted"
                                >
                                    {{ cart.admin_customer_type }}
                                </div>

                            </td>


                            <td>

                                {% if cart.user %}

                                    <div class="fw-semibold">
                                        {{ cart.admin_identity }}
                                    </div>

                                    <div
                                        class="small text-muted"
                                    >
                                        {{ cart.user.email|default:"No email" }}
                                    </div>

                                {% else %}

                                    <span
                                        class="badge text-bg-secondary"
                                    >
                                        Guest
                                    </span>

                                    <div
                                        class="small text-muted mt-1"
                                    >
                                        Session:
                                        {{ cart.session_key|default:"-"|truncatechars:18 }}
                                    </div>

                                {% endif %}

                            </td>


                            <td>
                                {{ cart.admin_item_count }}
                            </td>


                            <td>

                                {{ store_settings.currency_symbol }}
                                {{ cart.admin_value|floatformat:2 }}

                            </td>


                            <td>

                                {% if cart.checkout_started_at %}

                                    <span
                                        class="badge text-bg-warning"
                                    >
                                        Started
                                    </span>

                                {% else %}

                                    <span
                                        class="badge text-bg-light"
                                    >
                                        Not started
                                    </span>

                                {% endif %}

                            </td>


                            <td>

                                {{ cart.last_activity_at|date:"M d, Y H:i" }}

                            </td>


                            <td>

                                {% if cart.admin_age_days %}

                                    {{ cart.admin_age_days }}
                                    day{{ cart.admin_age_days|pluralize }}

                                {% else %}

                                    {{ cart.admin_age_hours }}
                                    hour{{ cart.admin_age_hours|pluralize }}

                                {% endif %}

                            </td>


                            <td class="text-end">

                                <a
                                    href="{% url 'admin_abandoned_cart_detail' cart.pk %}"
                                    class="btn btn-sm btn-outline-primary"
                                >
                                    View
                                </a>

                            </td>

                        </tr>


                        {% empty %}

                        <tr>

                            <td
                                colspan="8"
                                class="text-center
                                py-5 text-muted"
                            >
                                No abandoned carts
                                match these filters.
                            </td>

                        </tr>

                        {% endfor %}

                    </tbody>

                </table>

            </div>

        </div>

    </div>


    {% if page_obj.paginator.num_pages > 1 %}

    <nav class="mt-4">

        <ul class="pagination">

            {% if page_obj.has_previous %}

            <li class="page-item">

                <a
                    class="page-link"
                    href="?page={{ page_obj.previous_page_number }}&q={{ search|urlencode }}&type={{ selected_type|urlencode }}&checkout={{ selected_checkout|urlencode }}"
                >
                    Previous
                </a>

            </li>

            {% endif %}


            <li
                class="page-item active"
            >

                <span class="page-link">

                    {{ page_obj.number }}
                    /
                    {{ page_obj.paginator.num_pages }}

                </span>

            </li>


            {% if page_obj.has_next %}

            <li class="page-item">

                <a
                    class="page-link"
                    href="?page={{ page_obj.next_page_number }}&q={{ search|urlencode }}&type={{ selected_type|urlencode }}&checkout={{ selected_checkout|urlencode }}"
                >
                    Next
                </a>

            </li>

            {% endif %}

        </ul>

    </nav>

    {% endif %}

</div>

{% endblock %}
'''.strip() + "\n",
encoding="utf-8",
)


# ============================================================
# DETAIL TEMPLATE
# ============================================================

DETAIL_TEMPLATE.write_text(
r'''
{% extends "dashboard/admin/base.html" %}

{% block title %}
Abandoned Cart #{{ cart.pk }}
{% endblock %}


{% block content %}

<div class="container-fluid">

    <div
        class="d-flex flex-column flex-md-row
        justify-content-between
        align-items-md-center
        gap-3 mb-4"
    >

        <div>

            <a
                href="{% url 'admin_abandoned_cart_list' %}"
                class="btn btn-sm
                btn-outline-secondary mb-3"
            >
                &larr; Abandoned Carts
            </a>

            <h2 class="mb-1">
                Abandoned Cart #{{ cart.pk }}
            </h2>

            <div class="text-muted">

                Last activity:
                {{ cart.last_activity_at|date:"M d, Y H:i" }}

            </div>

        </div>

    </div>


    <div class="row g-4">

        <div class="col-xl-8">

            <div class="card shadow-sm">

                <div class="card-header">

                    <strong>
                        Cart Items
                    </strong>

                </div>


                <div class="card-body p-0">

                    <div class="table-responsive">

                        <table
                            class="table
                            align-middle mb-0"
                        >

                            <thead>

                                <tr>

                                    <th>
                                        Product
                                    </th>

                                    <th>
                                        Variant
                                    </th>

                                    <th>
                                        Qty
                                    </th>

                                    <th>
                                        Unit Price
                                    </th>

                                    <th>
                                        Subtotal
                                    </th>

                                </tr>

                            </thead>


                            <tbody>

                                {% for item in cart.admin_items %}

                                <tr>

                                    <td>

                                        <div class="fw-semibold">
                                            {{ item.product.name }}
                                        </div>

                                        <div
                                            class="small text-muted"
                                        >
                                            {{ item.product.sku }}
                                        </div>

                                    </td>


                                    <td>

                                        {% if item.variant %}

                                            {{ item.variant.name }}

                                        {% else %}

                                            —

                                        {% endif %}

                                    </td>


                                    <td>
                                        {{ item.quantity }}
                                    </td>


                                    <td>

                                        {{ store_settings.currency_symbol }}

                                        {% if item.variant %}
                                            {{ item.variant.current_price|floatformat:2 }}
                                        {% else %}
                                            {{ item.product.current_price|floatformat:2 }}
                                        {% endif %}

                                    </td>


                                    <td>

                                        {{ store_settings.currency_symbol }}
                                        {{ item.subtotal|floatformat:2 }}

                                    </td>

                                </tr>

                                {% endfor %}

                            </tbody>


                            <tfoot>

                                <tr>

                                    <th colspan="4">
                                        Cart Total
                                    </th>

                                    <th>
                                        {{ store_settings.currency_symbol }}
                                        {{ cart.admin_value|floatformat:2 }}
                                    </th>

                                </tr>

                            </tfoot>

                        </table>

                    </div>

                </div>

            </div>

        </div>


        <div class="col-xl-4">

            <div class="card shadow-sm mb-4">

                <div class="card-header">

                    <strong>
                        Customer
                    </strong>

                </div>


                <div class="card-body">

                    {% if cart.user %}

                        <div class="mb-2">

                            <strong>
                                {{ cart.admin_identity }}
                            </strong>

                        </div>


                        <div class="text-muted">
                            {{ cart.user.email|default:"No email" }}
                        </div>


                        {% if cart.user.phone %}

                        <div class="text-muted">
                            {{ cart.user.phone }}
                        </div>

                        {% endif %}


                        <div class="mt-3">

                            <span
                                class="badge text-bg-primary"
                            >
                                Registered Customer
                            </span>

                        </div>

                    {% else %}

                        <span
                            class="badge text-bg-secondary"
                        >
                            Guest Cart
                        </span>


                        <div class="mt-3">

                            <div class="small text-muted">
                                Session Key
                            </div>

                            <code>
                                {{ cart.session_key|default:"-" }}
                            </code>

                        </div>

                    {% endif %}

                </div>

            </div>


            <div class="card shadow-sm">

                <div class="card-header">

                    <strong>
                        Cart Activity
                    </strong>

                </div>


                <div class="card-body">

                    <dl class="row mb-0">

                        <dt class="col-6">
                            Items
                        </dt>

                        <dd class="col-6 text-end">
                            {{ cart.admin_item_count }}
                        </dd>


                        <dt class="col-6">
                            Value
                        </dt>

                        <dd class="col-6 text-end">

                            {{ store_settings.currency_symbol }}
                            {{ cart.admin_value|floatformat:2 }}

                        </dd>


                        <dt class="col-6">
                            Checkout
                        </dt>

                        <dd class="col-6 text-end">

                            {% if cart.checkout_started_at %}

                                Started

                            {% else %}

                                Not started

                            {% endif %}

                        </dd>


                        <dt class="col-6">
                            Created
                        </dt>

                        <dd class="col-6 text-end">
                            {{ cart.created_at|date:"M d, Y H:i" }}
                        </dd>


                        <dt class="col-6">
                            Last Activity
                        </dt>

                        <dd class="col-6 text-end">
                            {{ cart.last_activity_at|date:"M d, Y H:i" }}
                        </dd>


                        <dt class="col-6">
                            Inactive
                        </dt>

                        <dd class="col-6 text-end">

                            {% if cart.admin_age_days %}

                                {{ cart.admin_age_days }}
                                day{{ cart.admin_age_days|pluralize }}

                            {% else %}

                                {{ cart.admin_age_hours }}
                                hour{{ cart.admin_age_hours|pluralize }}

                            {% endif %}

                        </dd>

                    </dl>

                </div>

            </div>

        </div>

    </div>


    <div class="alert alert-info mt-4 mb-0">

        Recovery messaging is intentionally disabled
        in Phase 14B. This screen is read-only.

    </div>

</div>

{% endblock %}
'''.strip() + "\n",
encoding="utf-8",
)


# ============================================================
# TESTS
# ============================================================

TEST_FILE.write_text(
r'''
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model

from django.test import TestCase

from django.urls import reverse

from django.utils import timezone


from categories.models import Category

from products.models import Product

from cart.models import (
    Cart,
    CartItem,
)


User = get_user_model()


class Phase14BAdminAbandonedCartTests(
    TestCase
):

    def setUp(self):

        self.staff = (
            User.objects.create_user(
                username="phase14b-admin",
                email="admin@example.com",
                password="pass12345",
                is_staff=True,
            )
        )


        self.customer = (
            User.objects.create_user(
                username="phase14b-customer",
                email="buyer@example.com",
                password="pass12345",
            )
        )


        category = Category.objects.create(
            name="Phase 14B",
            slug="phase-14b",
        )


        self.product = Product.objects.create(
            category=category,
            name="Abandoned Product",
            slug="abandoned-product",
            sku="ABANDONED-001",
            description="Test product",
            price=Decimal("250.00"),
            stock=20,
        )


    def create_abandoned_cart(
        self,
        *,
        user=None,
        session_key=None,
        quantity=2,
        checkout_started=False,
    ):

        cart = Cart.objects.create(
            user=user,
            session_key=session_key,
        )


        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=quantity,
        )


        old_time = (
            timezone.now()
            - timedelta(hours=30)
        )


        values = {
            "last_activity_at":
                old_time,
        }


        if checkout_started:

            values[
                "checkout_started_at"
            ] = (
                old_time
                + timedelta(hours=1)
            )


        Cart.objects.filter(
            pk=cart.pk
        ).update(
            **values
        )


        cart.refresh_from_db()


        return cart


    def test_non_staff_cannot_access_list(
        self,
    ):

        self.client.force_login(
            self.customer
        )


        response = self.client.get(
            reverse(
                "admin_abandoned_cart_list"
            )
        )


        self.assertEqual(
            response.status_code,
            302,
        )


    def test_staff_can_view_abandoned_cart_list(
        self,
    ):

        cart = self.create_abandoned_cart(
            user=self.customer,
        )


        self.client.force_login(
            self.staff
        )


        response = self.client.get(
            reverse(
                "admin_abandoned_cart_list"
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertContains(
            response,
            f"#{cart.pk}",
        )


        self.assertContains(
            response,
            "buyer@example.com",
        )


    def test_cart_value_is_calculated(
        self,
    ):

        self.create_abandoned_cart(
            user=self.customer,
            quantity=2,
        )


        self.client.force_login(
            self.staff
        )


        response = self.client.get(
            reverse(
                "admin_abandoned_cart_list"
            )
        )


        self.assertEqual(
            response.context[
                "total_value"
            ],
            Decimal("500.00"),
        )


    def test_guest_cart_is_displayed(
        self,
    ):

        self.create_abandoned_cart(
            session_key=
                "phase14b-guest-session",
        )


        self.client.force_login(
            self.staff
        )


        response = self.client.get(
            reverse(
                "admin_abandoned_cart_list"
            )
        )


        self.assertEqual(
            response.context[
                "guest_count"
            ],
            1,
        )


        self.assertContains(
            response,
            "Guest",
        )


    def test_customer_filter(
        self,
    ):

        customer_cart = (
            self.create_abandoned_cart(
                user=self.customer,
            )
        )


        guest_cart = (
            self.create_abandoned_cart(
                session_key="guest-filter",
            )
        )


        self.client.force_login(
            self.staff
        )


        response = self.client.get(
            reverse(
                "admin_abandoned_cart_list"
            ),
            {
                "type": "customer",
            },
        )


        carts = list(
            response.context[
                "carts"
            ]
        )


        self.assertIn(
            customer_cart,
            carts,
        )


        self.assertNotIn(
            guest_cart,
            carts,
        )


    def test_checkout_started_filter(
        self,
    ):

        started = (
            self.create_abandoned_cart(
                user=self.customer,
                checkout_started=True,
            )
        )


        not_started = (
            self.create_abandoned_cart(
                session_key=
                    "checkout-filter-guest",
                checkout_started=False,
            )
        )


        self.client.force_login(
            self.staff
        )


        response = self.client.get(
            reverse(
                "admin_abandoned_cart_list"
            ),
            {
                "checkout":
                    "started",
            },
        )


        carts = list(
            response.context[
                "carts"
            ]
        )


        self.assertIn(
            started,
            carts,
        )


        self.assertNotIn(
            not_started,
            carts,
        )


    def test_search_by_product(
        self,
    ):

        cart = self.create_abandoned_cart(
            user=self.customer
        )


        self.client.force_login(
            self.staff
        )


        response = self.client.get(
            reverse(
                "admin_abandoned_cart_list"
            ),
            {
                "q":
                    "Abandoned Product",
            },
        )


        self.assertIn(
            cart,
            list(
                response.context[
                    "carts"
                ]
            ),
        )


    def test_staff_can_view_abandoned_cart_detail(
        self,
    ):

        cart = self.create_abandoned_cart(
            user=self.customer,
            quantity=2,
        )


        self.client.force_login(
            self.staff
        )


        response = self.client.get(
            reverse(
                "admin_abandoned_cart_detail",
                args=[cart.pk],
            )
        )


        self.assertEqual(
            response.status_code,
            200,
        )


        self.assertContains(
            response,
            "Abandoned Product",
        )


        self.assertContains(
            response,
            "500.00",
        )


    def test_recent_cart_cannot_be_opened_as_abandoned(
        self,
    ):

        cart = Cart.objects.create(
            user=self.customer,
        )


        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=1,
        )


        self.client.force_login(
            self.staff
        )


        response = self.client.get(
            reverse(
                "admin_abandoned_cart_detail",
                args=[cart.pk],
            )
        )


        self.assertEqual(
            response.status_code,
            404,
        )


    def test_converted_cart_cannot_be_opened_as_abandoned(
        self,
    ):

        cart = self.create_abandoned_cart(
            user=self.customer
        )


        Cart.objects.filter(
            pk=cart.pk
        ).update(
            converted_at=timezone.now()
        )


        self.client.force_login(
            self.staff
        )


        response = self.client.get(
            reverse(
                "admin_abandoned_cart_detail",
                args=[cart.pk],
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
print("PHASE 14B INSTALLED")
print("=" * 72)
print()
print("Added:")
print("  Admin abandoned-cart list")
print("  Admin abandoned-cart detail")
print("  Customer/guest filtering")
print("  Checkout-start filtering")
print("  Search by customer/session/product/SKU")
print("  Cart item count")
print("  Current cart value")
print("  Abandonment age")
print("  Read-only admin inspection")
print("  Sidebar navigation")
print()
print("No database migration required.")
print("No email or SMS is sent.")
