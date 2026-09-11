from pathlib import Path
import shutil

ROOT = Path.cwd()

CUSTOMER_BASE = ROOT / "templates" / "base.html"

ADMIN_BASE = (
    ROOT
    / "templates"
    / "dashboard"
    / "admin"
    / "base.html"
)

ANALYTICS = (
    ROOT
    / "templates"
    / "dashboard"
    / "admin_analytics.html"
)

TESTS = (
    ROOT
    / "dashboard"
    / "test_layout_isolation.py"
)


# ============================================================
# BACKUPS
# ============================================================

for path in [
    CUSTOMER_BASE,
    ADMIN_BASE,
    ANALYTICS,
]:

    if path.exists():

        backup = Path(
            str(path)
            + ".layoutisolationbackup"
        )

        if not backup.exists():

            shutil.copy2(
                path,
                backup,
            )


# ============================================================
# 1. EXPLICIT CUSTOMER BODY
# ============================================================

customer = CUSTOMER_BASE.read_text(
    encoding="utf-8-sig"
)

if '<body class="storefront-body">' not in customer:

    customer = customer.replace(
        "<body>",
        '<body class="storefront-body">',
        1,
    )

CUSTOMER_BASE.write_text(
    customer,
    encoding="utf-8",
)

print(
    "Customer shell marked as storefront-body."
)


# ============================================================
# 2. EXPLICIT ADMIN BODY
# ============================================================

admin = ADMIN_BASE.read_text(
    encoding="utf-8-sig"
)

if '<body class="admin-body">' not in admin:

    admin = admin.replace(
        "<body>",
        '<body class="admin-body">',
        1,
    )

ADMIN_BASE.write_text(
    admin,
    encoding="utf-8",
)

print(
    "Admin shell marked as admin-body."
)


# ============================================================
# 3. REBUILD ANALYTICS USING ADMIN SHELL
# ============================================================

ANALYTICS.write_text(
r'''
{% extends "dashboard/admin/base.html" %}

{% block title %}
Store Analytics
{% endblock %}

{% block page_heading %}
Store Analytics
{% endblock %}


{% block admin_content %}


<!-- ===================================================== -->
<!-- PAGE HEADING -->
<!-- ===================================================== -->

<div class="dashboard-heading">

    <div>

        <h1>
            Store Analytics
        </h1>

        <p>
            Monitor sales, orders, customers,
            products and stock performance.
        </p>

    </div>


    <div class="d-flex gap-2">

        <a
            href="{% url 'admin_sales_reports' %}"
            class="btn btn-primary"
        >
            <i class="bi bi-bar-chart-line me-1"></i>
            Full Reports
        </a>

    </div>

</div>


<!-- ===================================================== -->
<!-- FILTERS -->
<!-- ===================================================== -->

<div class="dashboard-card mb-4">

    <form
        method="GET"
        class="row g-3 align-items-end"
    >

        <div class="col-md-4">

            <label
                for="start"
                class="form-label"
            >
                From
            </label>

            <input
                id="start"
                type="date"
                name="start"
                value="{{ start_date|date:'Y-m-d' }}"
                class="form-control"
            >

        </div>


        <div class="col-md-4">

            <label
                for="end"
                class="form-label"
            >
                To
            </label>

            <input
                id="end"
                type="date"
                name="end"
                value="{{ end_date|date:'Y-m-d' }}"
                class="form-control"
            >

        </div>


        <div class="col-md-2">

            <button
                type="submit"
                class="btn btn-primary w-100"
            >
                Apply
            </button>

        </div>


        <div class="col-md-2">

            <a
                href="{% url 'admin_sales_export' %}?start={{ start_date|date:'Y-m-d' }}&end={{ end_date|date:'Y-m-d' }}"
                class="
                    btn
                    btn-outline-success
                    w-100
                "
            >
                Export CSV
            </a>

        </div>

    </form>

</div>


<!-- ===================================================== -->
<!-- KPIs -->
<!-- ===================================================== -->

<div class="row g-3 mb-4">


    <div class="col-sm-6 col-xl-3">

        <div class="dashboard-card stat-card h-100">

            <div>

                <span class="stat-label">
                    Orders in Range
                </span>

                <h3>
                    {{ report_orders }}
                </h3>

            </div>

            <div class="stat-icon">

                <i class="bi bi-bag-check"></i>

            </div>

        </div>

    </div>


    <div class="col-sm-6 col-xl-3">

        <div class="dashboard-card stat-card h-100">

            <div>

                <span class="stat-label">
                    Revenue
                </span>

                <h3>
                    KES {{ today_revenue|floatformat:2 }}
                </h3>

            </div>

            <div class="stat-icon">

                <i class="bi bi-cash-stack"></i>

            </div>

        </div>

    </div>


    <div class="col-sm-6 col-xl-3">

        <div class="dashboard-card stat-card h-100">

            <div>

                <span class="stat-label">
                    Customers
                </span>

                <h3>
                    {{ report_customers }}
                </h3>

            </div>

            <div class="stat-icon">

                <i class="bi bi-people"></i>

            </div>

        </div>

    </div>


    <div class="col-sm-6 col-xl-3">

        <div class="dashboard-card stat-card h-100">

            <div>

                <span class="stat-label">
                    Open Orders
                </span>

                <h3>
                    {{ pending_orders }}
                </h3>

            </div>

            <div class="stat-icon">

                <i class="bi bi-hourglass-split"></i>

            </div>

        </div>

    </div>


</div>


<!-- ===================================================== -->
<!-- SECONDARY KPI -->
<!-- ===================================================== -->

<div class="row g-3 mb-4">


    <div class="col-md-6">

        <div class="dashboard-card mini-stat h-100">

            <span>
                Orders Today
            </span>

            <strong>
                {{ today_orders }}
            </strong>

        </div>

    </div>


    <div class="col-md-6">

        <div class="dashboard-card mini-stat h-100">

            <span>
                Revenue in Selected Range
            </span>

            <strong>
                KES {{ week_revenue|floatformat:2 }}
            </strong>

        </div>

    </div>


</div>


<!-- ===================================================== -->
<!-- RECENT ORDERS -->
<!-- ===================================================== -->

<div class="row g-4">


    <div class="col-xl-8">

        <div class="dashboard-card h-100">

            <div class="card-header-custom">

                <div>

                    <h2>
                        Recent Orders
                    </h2>

                    <p>
                        Latest orders received by the store.
                    </p>

                </div>


                <a
                    href="{% url 'admin_order_list' %}"
                    class="
                        btn
                        btn-sm
                        btn-outline-primary
                    "
                >
                    View All
                </a>

            </div>


            <div class="table-responsive">

                <table
                    class="
                        table
                        dashboard-table
                        align-middle
                    "
                >

                    <thead>

                        <tr>

                            <th>
                                Order
                            </th>

                            <th>
                                Customer
                            </th>

                            <th>
                                Status
                            </th>

                            <th class="text-end">
                                Total
                            </th>

                        </tr>

                    </thead>


                    <tbody>

                        {% for order in recent_orders %}

                            <tr>

                                <td>

                                    <a
                                        href="{% url 'admin_order_detail' order.order_number %}"
                                        class="fw-semibold text-decoration-none"
                                    >
                                        {{ order.order_number }}
                                    </a>

                                </td>


                                <td>

                                    {{ order.full_name }}

                                    {% if order.phone %}

                                        <small class="d-block text-muted">

                                            {{ order.phone }}

                                        </small>

                                    {% endif %}

                                </td>


                                <td>

                                    <span
                                        class="
                                            status-badge
                                            status-{{ order.status }}
                                        "
                                    >
                                        {{ order.get_status_display }}
                                    </span>

                                </td>


                                <td class="text-end fw-semibold">

                                    KES {{ order.total_amount|floatformat:2 }}

                                </td>

                            </tr>


                        {% empty %}

                            <tr>

                                <td
                                    colspan="4"
                                    class="
                                        text-center
                                        text-muted
                                        py-5
                                    "
                                >
                                    No orders yet.
                                </td>

                            </tr>

                        {% endfor %}

                    </tbody>

                </table>

            </div>

        </div>

    </div>


    <!-- ================================================= -->
    <!-- RIGHT COLUMN -->
    <!-- ================================================= -->

    <div class="col-xl-4">


        <!-- TOP PRODUCTS -->

        <div class="dashboard-card mb-4">

            <div class="card-header-custom">

                <div>

                    <h2>
                        Top Products
                    </h2>

                    <p>
                        Best-selling products in this period.
                    </p>

                </div>

            </div>


            {% for product in top_products %}

                <div class="list-row">

                    <div>

                        <strong>
                            {{ product.product_name }}
                        </strong>

                        <small>
                            KES {{ product.revenue|floatformat:2 }}
                        </small>

                    </div>


                    <span class="stock-count">

                        {{ product.units }} sold

                    </span>

                </div>


            {% empty %}

                <p class="text-muted mb-0">
                    No paid sales in this period.
                </p>

            {% endfor %}

        </div>


        <!-- ORDER STATUS -->

        <div class="dashboard-card mb-4">

            <div class="card-header-custom">

                <div>

                    <h2>
                        Order Status
                    </h2>

                    <p>
                        Current order pipeline.
                    </p>

                </div>

            </div>


            {% for item in status_counts %}

                <div class="list-row">

                    <span>
                        {{ item.status|title }}
                    </span>

                    <strong>
                        {{ item.total }}
                    </strong>

                </div>


            {% empty %}

                <p class="text-muted mb-0">
                    No orders yet.
                </p>

            {% endfor %}

        </div>


        <!-- LOW STOCK -->

        <div class="dashboard-card">

            <div class="card-header-custom">

                <div>

                    <h2>
                        Low Stock
                    </h2>

                    <p>
                        Products requiring attention.
                    </p>

                </div>


                <a
                    href="{% url 'inventory_dashboard' %}"
                    class="
                        btn
                        btn-sm
                        btn-outline-primary
                    "
                >
                    Inventory
                </a>

            </div>


            {% for product in low_stock %}

                <div class="stock-item">

                    <div>

                        <strong>
                            {{ product.name }}
                        </strong>

                        <small>
                            {{ product.sku }}
                        </small>

                    </div>


                    <span class="stock-count">

                        {{ product.available_stock }}

                    </span>

                </div>


            {% empty %}

                <p class="text-muted mb-0">

                    Stock levels look good.

                </p>

            {% endfor %}

        </div>


    </div>

</div>


{% endblock %}
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Analytics moved completely into admin shell."
)


# ============================================================
# 4. REGRESSION TESTS
# ============================================================

TESTS.write_text(
r'''
from pathlib import Path

from django.contrib.auth import (
    get_user_model,
)

from django.test import (
    TestCase,
)

from django.urls import reverse


User = get_user_model()


class LayoutIsolationTests(
    TestCase
):

    def setUp(self):

        self.staff = (
            User.objects.create_user(
                username="layoutstaff",
                password="pass12345",
                role=User.ADMIN,
                is_staff=True,
            )
        )


    def test_admin_analytics_uses_admin_shell(
        self
    ):

        self.client.login(
            username="layoutstaff",
            password="pass12345",
        )

        response = self.client.get(
            reverse(
                "admin_analytics"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        content = response.content.decode(
            "utf-8"
        )

        self.assertIn(
            "admin-layout",
            content,
        )

        self.assertIn(
            "admin-dashboard.css",
            content,
        )

        self.assertNotIn(
            "storefront-nav",
            content,
        )

        self.assertNotIn(
            "whatsapp-float",
            content,
        )

        self.assertNotIn(
            'css/styles.css',
            content,
        )


    def test_admin_analytics_template_uses_admin_base(
        self
    ):

        root = Path(
            __file__
        ).resolve().parent.parent

        path = (
            root
            / "templates"
            / "dashboard"
            / "admin_analytics.html"
        )

        source = path.read_text(
            encoding="utf-8-sig"
        )

        self.assertIn(
            '{% extends "dashboard/admin/base.html" %}',
            source,
        )

        self.assertNotIn(
            '{% extends "base.html" %}',
            source,
        )


    def test_admin_base_does_not_load_storefront_css(
        self
    ):

        root = Path(
            __file__
        ).resolve().parent.parent

        path = (
            root
            / "templates"
            / "dashboard"
            / "admin"
            / "base.html"
        )

        source = path.read_text(
            encoding="utf-8-sig"
        )

        self.assertIn(
            "admin-dashboard.css",
            source,
        )

        self.assertNotIn(
            "css/styles.css",
            source,
        )


    def test_storefront_base_does_not_load_admin_css(
        self
    ):

        root = Path(
            __file__
        ).resolve().parent.parent

        path = (
            root
            / "templates"
            / "base.html"
        )

        source = path.read_text(
            encoding="utf-8-sig"
        )

        self.assertIn(
            "css/styles.css",
            source,
        )

        self.assertNotIn(
            "admin-dashboard.css",
            source,
        )
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Layout-isolation regression tests created."
)


print()
print("=" * 72)
print("ADMIN / STOREFRONT LAYOUT ISOLATION REPAIR COMPLETE")
print("=" * 72)
print()
print("Customer:")
print("  base.html -> styles.css")
print()
print("Store owner:")
print("  dashboard/admin/base.html -> admin-dashboard.css")
print()
print("Analytics:")
print("  now uses dashboard/admin/base.html")
print()
print("No migration required.")
