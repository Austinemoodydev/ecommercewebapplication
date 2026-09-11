from pathlib import Path
import re
import shutil

ROOT = Path.cwd()

DASHBOARD = ROOT / "dashboard"

URLS = DASHBOARD / "urls.py"

BASE = (
    ROOT
    / "templates"
    / "dashboard"
    / "admin"
    / "base.html"
)

TEMPLATES = (
    ROOT
    / "templates"
    / "dashboard"
    / "admin"
    / "reports"
)

TEMPLATES.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# BACKUPS
# ============================================================

for path in [
    URLS,
    BASE,
]:

    if path.exists():

        backup = Path(
            str(path) + ".phase9abackup"
        )

        if not backup.exists():

            shutil.copy2(
                path,
                backup,
            )


# ============================================================
# 1. REPORTS VIEW
# ============================================================

reports_views = (
    DASHBOARD
    / "reports_views.py"
)

reports_views.write_text(
r'''
import csv
from datetime import (
    datetime,
    time,
    timedelta,
)
from decimal import Decimal

from django.contrib.admin.views.decorators import (
    staff_member_required,
)

from django.db.models import (
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    Q,
    Sum,
)

from django.db.models.functions import (
    Coalesce,
    TruncDate,
)

from django.http import HttpResponse

from django.shortcuts import render

from django.utils import timezone

from orders.models import (
    Order,
    OrderItem,
)

from payments.models import (
    MpesaTransaction,
    RefundRequest,
)


ZERO = Decimal("0.00")


# ============================================================
# DATE HELPERS
# ============================================================

def _parse_date(value):

    if not value:
        return None

    try:

        return datetime.strptime(
            value,
            "%Y-%m-%d",
        ).date()

    except ValueError:
        return None


def _date_range(request):

    today = timezone.localdate()

    default_start = (
        today
        - timedelta(days=29)
    )

    start_date = (
        _parse_date(
            request.GET.get(
                "start"
            )
        )
        or default_start
    )

    end_date = (
        _parse_date(
            request.GET.get(
                "end"
            )
        )
        or today
    )


    if start_date > end_date:

        start_date, end_date = (
            end_date,
            start_date,
        )


    start_dt = timezone.make_aware(
        datetime.combine(
            start_date,
            time.min,
        ),
        timezone.get_current_timezone(),
    )

    end_dt = timezone.make_aware(
        datetime.combine(
            end_date,
            time.max,
        ),
        timezone.get_current_timezone(),
    )


    return (
        start_date,
        end_date,
        start_dt,
        end_dt,
    )


def _money(value):

    if value is None:
        return ZERO

    return Decimal(value)


# ============================================================
# REPORT DATA
# ============================================================

def build_sales_report(
    request,
):

    (
        start_date,
        end_date,
        start_dt,
        end_dt,
    ) = _date_range(
        request
    )


    orders = (
        Order.objects
        .filter(
            created_at__range=[
                start_dt,
                end_dt,
            ]
        )
        .select_related(
            "user"
        )
    )


    paid_orders = orders.filter(
        payment_status__in=[
            "paid",
            "partially_refunded",
            "refunded",
        ]
    )


    # --------------------------------------------------------
    # Revenue
    # --------------------------------------------------------

    gross_revenue = _money(
        paid_orders.aggregate(
            total=Coalesce(
                Sum(
                    "total_amount"
                ),
                ZERO,
                output_field=DecimalField(),
            )
        )["total"]
    )


    processed_refunds = _money(
        RefundRequest.objects
        .filter(
            order__created_at__range=[
                start_dt,
                end_dt,
            ],
            status="processed",
        )
        .aggregate(
            total=Coalesce(
                Sum(
                    "amount"
                ),
                ZERO,
                output_field=DecimalField(),
            )
        )["total"]
    )


    net_revenue = (
        gross_revenue
        - processed_refunds
    )


    # --------------------------------------------------------
    # Orders
    # --------------------------------------------------------

    total_orders = orders.count()

    paid_order_count = (
        paid_orders.count()
    )

    cancelled_orders = (
        orders.filter(
            status="cancelled"
        ).count()
    )


    average_order_value = (
        gross_revenue
        / paid_order_count
        if paid_order_count
        else ZERO
    )


    # --------------------------------------------------------
    # Delivery finances
    # --------------------------------------------------------

    delivery_income = _money(
        paid_orders.aggregate(
            total=Coalesce(
                Sum(
                    "shipping_cost"
                ),
                ZERO,
                output_field=DecimalField(),
            )
        )["total"]
    )


    try:

        from delivery.models import (
            Delivery,
        )

        actual_delivery_cost = _money(
            Delivery.objects
            .filter(
                order__created_at__range=[
                    start_dt,
                    end_dt,
                ],
                order__payment_status__in=[
                    "paid",
                    "partially_refunded",
                    "refunded",
                ],
            )
            .aggregate(
                total=Coalesce(
                    Sum(
                        "actual_delivery_cost"
                    ),
                    ZERO,
                    output_field=DecimalField(),
                )
            )["total"]
        )

    except Exception:

        actual_delivery_cost = ZERO


    delivery_margin = (
        delivery_income
        - actual_delivery_cost
    )


    # --------------------------------------------------------
    # Estimated cost of goods sold
    #
    # IMPORTANT:
    # cost_price currently comes from current Product /
    # ProductVariant data, not a historical OrderItem snapshot.
    # This is therefore an estimate.
    # --------------------------------------------------------

    paid_items = (
        OrderItem.objects
        .filter(
            order__in=paid_orders
        )
        .select_related(
            "product",
            "variant",
        )
    )


    estimated_cogs = ZERO


    for item in paid_items:

        unit_cost = ZERO

        if (
            item.variant_id
            and hasattr(
                item.variant,
                "cost_price",
            )
            and item.variant.cost_price
            is not None
        ):

            unit_cost = Decimal(
                item.variant.cost_price
            )

        elif (
            item.product_id
            and hasattr(
                item.product,
                "cost_price",
            )
            and item.product.cost_price
            is not None
        ):

            unit_cost = Decimal(
                item.product.cost_price
            )


        estimated_cogs += (
            unit_cost
            * item.quantity
        )


    estimated_gross_profit = (
        net_revenue
        - estimated_cogs
        - actual_delivery_cost
    )


    # --------------------------------------------------------
    # M-PESA collections
    # --------------------------------------------------------

    mpesa_collected = _money(
        MpesaTransaction.objects
        .filter(
            order__created_at__range=[
                start_dt,
                end_dt,
            ],
            status="success",
        )
        .aggregate(
            total=Coalesce(
                Sum(
                    "amount"
                ),
                ZERO,
                output_field=DecimalField(),
            )
        )["total"]
    )


    successful_mpesa_count = (
        MpesaTransaction.objects
        .filter(
            order__created_at__range=[
                start_dt,
                end_dt,
            ],
            status="success",
        )
        .count()
    )


    # --------------------------------------------------------
    # Top products
    # --------------------------------------------------------

    top_products = (
        OrderItem.objects
        .filter(
            order__in=paid_orders
        )
        .values(
            "product_name"
        )
        .annotate(
            quantity_sold=Sum(
                "quantity"
            ),
            revenue=Sum(
                "subtotal"
            ),
        )
        .order_by(
            "-quantity_sold",
            "-revenue",
        )[:10]
    )


    # --------------------------------------------------------
    # Top customers
    # --------------------------------------------------------

    top_customers = (
        paid_orders
        .values(
            "user_id",
            "full_name",
            "phone",
        )
        .annotate(
            order_count=Count(
                "id"
            ),
            total_spent=Sum(
                "total_amount"
            ),
        )
        .order_by(
            "-total_spent",
            "-order_count",
        )[:10]
    )


    # --------------------------------------------------------
    # Order status breakdown
    # --------------------------------------------------------

    order_statuses = (
        orders
        .values(
            "status"
        )
        .annotate(
            total=Count(
                "id"
            )
        )
        .order_by(
            "-total"
        )
    )


    payment_statuses = (
        orders
        .values(
            "payment_status"
        )
        .annotate(
            total=Count(
                "id"
            )
        )
        .order_by(
            "-total"
        )
    )


    # --------------------------------------------------------
    # Daily sales trend
    # --------------------------------------------------------

    daily_sales = (
        paid_orders
        .annotate(
            day=TruncDate(
                "created_at"
            )
        )
        .values(
            "day"
        )
        .annotate(
            orders=Count(
                "id"
            ),
            revenue=Sum(
                "total_amount"
            ),
        )
        .order_by(
            "day"
        )
    )


    # --------------------------------------------------------
    # Recent paid orders
    # --------------------------------------------------------

    recent_orders = (
        paid_orders
        .order_by(
            "-created_at"
        )[:20]
    )


    return {
        "start_date": start_date,
        "end_date": end_date,

        "gross_revenue": (
            gross_revenue
        ),

        "processed_refunds": (
            processed_refunds
        ),

        "net_revenue": (
            net_revenue
        ),

        "total_orders": (
            total_orders
        ),

        "paid_order_count": (
            paid_order_count
        ),

        "cancelled_orders": (
            cancelled_orders
        ),

        "average_order_value": (
            average_order_value
        ),

        "delivery_income": (
            delivery_income
        ),

        "actual_delivery_cost": (
            actual_delivery_cost
        ),

        "delivery_margin": (
            delivery_margin
        ),

        "estimated_cogs": (
            estimated_cogs
        ),

        "estimated_gross_profit": (
            estimated_gross_profit
        ),

        "mpesa_collected": (
            mpesa_collected
        ),

        "successful_mpesa_count": (
            successful_mpesa_count
        ),

        "top_products": (
            top_products
        ),

        "top_customers": (
            top_customers
        ),

        "order_statuses": (
            order_statuses
        ),

        "payment_statuses": (
            payment_statuses
        ),

        "daily_sales": (
            daily_sales
        ),

        "recent_orders": (
            recent_orders
        ),
    }


# ============================================================
# DASHBOARD
# ============================================================

@staff_member_required
def sales_reports(
    request,
):

    context = build_sales_report(
        request
    )

    return render(
        request,
        "dashboard/admin/reports/sales.html",
        context,
    )


# ============================================================
# CSV EXPORT
# ============================================================

@staff_member_required
def sales_reports_csv(
    request,
):

    context = build_sales_report(
        request
    )


    response = HttpResponse(
        content_type=(
            "text/csv; charset=utf-8"
        )
    )

    filename = (
        "sales-report-"
        f"{context['start_date']}-"
        f"{context['end_date']}.csv"
    )

    response[
        "Content-Disposition"
    ] = (
        f'attachment; filename="{filename}"'
    )


    writer = csv.writer(
        response
    )


    writer.writerow(
        [
            "Sales Report",
            (
                f"{context['start_date']} "
                f"to {context['end_date']}"
            ),
        ]
    )

    writer.writerow([])


    writer.writerow(
        [
            "Metric",
            "Value",
        ]
    )


    metrics = [

        (
            "Gross Revenue",
            context[
                "gross_revenue"
            ],
        ),

        (
            "Processed Refunds",
            context[
                "processed_refunds"
            ],
        ),

        (
            "Net Revenue",
            context[
                "net_revenue"
            ],
        ),

        (
            "Total Orders",
            context[
                "total_orders"
            ],
        ),

        (
            "Paid Orders",
            context[
                "paid_order_count"
            ],
        ),

        (
            "Cancelled Orders",
            context[
                "cancelled_orders"
            ],
        ),

        (
            "Average Order Value",
            context[
                "average_order_value"
            ],
        ),

        (
            "Delivery Income",
            context[
                "delivery_income"
            ],
        ),

        (
            "Actual Delivery Cost",
            context[
                "actual_delivery_cost"
            ],
        ),

        (
            "Delivery Margin",
            context[
                "delivery_margin"
            ],
        ),

        (
            "Estimated COGS",
            context[
                "estimated_cogs"
            ],
        ),

        (
            "Estimated Gross Profit",
            context[
                "estimated_gross_profit"
            ],
        ),

        (
            "M-PESA Collected",
            context[
                "mpesa_collected"
            ],
        ),
    ]


    for (
        name,
        value,
    ) in metrics:

        writer.writerow(
            [
                name,
                value,
            ]
        )


    writer.writerow([])
    writer.writerow(
        [
            "Top Products"
        ]
    )

    writer.writerow(
        [
            "Product",
            "Quantity Sold",
            "Revenue",
        ]
    )


    for row in context[
        "top_products"
    ]:

        writer.writerow(
            [
                row[
                    "product_name"
                ],
                row[
                    "quantity_sold"
                ],
                row[
                    "revenue"
                ],
            ]
        )


    writer.writerow([])
    writer.writerow(
        [
            "Top Customers"
        ]
    )

    writer.writerow(
        [
            "Customer",
            "Phone",
            "Orders",
            "Total Spent",
        ]
    )


    for row in context[
        "top_customers"
    ]:

        writer.writerow(
            [
                row[
                    "full_name"
                ],
                row[
                    "phone"
                ],
                row[
                    "order_count"
                ],
                row[
                    "total_spent"
                ],
            ]
        )


    return response
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Created Phase 9 sales reporting engine."
)


# ============================================================
# 2. DASHBOARD URLS
# ============================================================

urls = URLS.read_text(
    encoding="utf-8-sig"
)

if (
    "from . import reports_views"
    not in urls
):

    if "from . import views" in urls:

        urls = urls.replace(
            "from . import views",
            (
                "from . import views\n"
                "from . import reports_views"
            ),
            1,
        )

    else:

        urls = (
            "from . import reports_views\n"
            + urls
        )


routes = ""


if 'name="admin_sales_reports"' not in urls:

    routes += r'''
    path(
        "admin/reports/",
        reports_views.sales_reports,
        name="admin_sales_reports",
    ),
'''


if 'name="admin_sales_reports_csv"' not in urls:

    routes += r'''
    path(
        "admin/reports/export/",
        reports_views.sales_reports_csv,
        name="admin_sales_reports_csv",
    ),
'''


if routes:

    marker = "urlpatterns = ["

    if marker not in urls:

        raise RuntimeError(
            "Could not locate urlpatterns."
        )

    urls = urls.replace(
        marker,
        marker + routes,
        1,
    )


URLS.write_text(
    urls,
    encoding="utf-8",
)

print(
    "Reports URLs added."
)


# ============================================================
# 3. REPORT TEMPLATE
# ============================================================

(TEMPLATES / "sales.html").write_text(
r'''
{% extends "dashboard/admin/base.html" %}

{% block title %}
Sales Reports
{% endblock %}

{% block page_heading %}
Sales Reports
{% endblock %}

{% block admin_content %}

<div class="dashboard-heading">

    <div>

        <h1>
            Sales & Business Analytics
        </h1>

        <p>
            Revenue, orders, refunds, delivery costs,
            products and customer performance.
        </p>

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

            <label class="form-label">
                From
            </label>

            <input
                type="date"
                name="start"
                value="{{ start_date|date:'Y-m-d' }}"
                class="form-control"
            >

        </div>


        <div class="col-md-4">

            <label class="form-label">
                To
            </label>

            <input
                type="date"
                name="end"
                value="{{ end_date|date:'Y-m-d' }}"
                class="form-control"
            >

        </div>


        <div class="col-md-2">

            <button
                class="btn btn-primary w-100"
            >
                Apply
            </button>

        </div>


        <div class="col-md-2">

            <a
                href="{% url 'admin_sales_reports_csv' %}?start={{ start_date|date:'Y-m-d' }}&end={{ end_date|date:'Y-m-d' }}"
                class="btn btn-outline-success w-100"
            >
                Export CSV
            </a>

        </div>

    </form>

</div>


<!-- ===================================================== -->
<!-- REVENUE KPI -->
<!-- ===================================================== -->

<div class="row g-3 mb-4">

    <div class="col-md-6 col-xl-3">

        <div class="dashboard-card h-100">

            <small class="text-muted">
                Gross Revenue
            </small>

            <div class="fs-3 fw-bold">
                KES {{ gross_revenue|floatformat:2 }}
            </div>

        </div>

    </div>


    <div class="col-md-6 col-xl-3">

        <div class="dashboard-card h-100">

            <small class="text-muted">
                Refunds
            </small>

            <div class="fs-3 fw-bold">
                KES {{ processed_refunds|floatformat:2 }}
            </div>

        </div>

    </div>


    <div class="col-md-6 col-xl-3">

        <div class="dashboard-card h-100">

            <small class="text-muted">
                Net Revenue
            </small>

            <div class="fs-3 fw-bold">
                KES {{ net_revenue|floatformat:2 }}
            </div>

        </div>

    </div>


    <div class="col-md-6 col-xl-3">

        <div class="dashboard-card h-100">

            <small class="text-muted">
                Estimated Gross Profit
            </small>

            <div class="fs-3 fw-bold">
                KES {{ estimated_gross_profit|floatformat:2 }}
            </div>

            <small class="text-muted">
                Uses current product cost prices.
            </small>

        </div>

    </div>

</div>


<!-- ===================================================== -->
<!-- ORDER KPI -->
<!-- ===================================================== -->

<div class="row g-3 mb-4">

    <div class="col-md-6 col-xl-3">

        <div class="dashboard-card h-100">

            <small class="text-muted">
                Total Orders
            </small>

            <div class="fs-3 fw-bold">
                {{ total_orders }}
            </div>

        </div>

    </div>


    <div class="col-md-6 col-xl-3">

        <div class="dashboard-card h-100">

            <small class="text-muted">
                Paid Orders
            </small>

            <div class="fs-3 fw-bold">
                {{ paid_order_count }}
            </div>

        </div>

    </div>


    <div class="col-md-6 col-xl-3">

        <div class="dashboard-card h-100">

            <small class="text-muted">
                Cancelled
            </small>

            <div class="fs-3 fw-bold">
                {{ cancelled_orders }}
            </div>

        </div>

    </div>


    <div class="col-md-6 col-xl-3">

        <div class="dashboard-card h-100">

            <small class="text-muted">
                Average Order Value
            </small>

            <div class="fs-3 fw-bold">
                KES {{ average_order_value|floatformat:2 }}
            </div>

        </div>

    </div>

</div>


<!-- ===================================================== -->
<!-- DELIVERY / PAYMENT -->
<!-- ===================================================== -->

<div class="row g-4 mb-4">

    <div class="col-lg-6">

        <div class="dashboard-card h-100">

            <h2 class="h5 mb-4">
                Delivery Financials
            </h2>


            <div class="d-flex justify-content-between border-bottom py-2">

                <span>
                    Customer Delivery Charges
                </span>

                <strong>
                    KES {{ delivery_income|floatformat:2 }}
                </strong>

            </div>


            <div class="d-flex justify-content-between border-bottom py-2">

                <span>
                    Actual Delivery Cost
                </span>

                <strong>
                    KES {{ actual_delivery_cost|floatformat:2 }}
                </strong>

            </div>


            <div class="d-flex justify-content-between py-2">

                <span>
                    Delivery Margin
                </span>

                <strong>
                    KES {{ delivery_margin|floatformat:2 }}
                </strong>

            </div>

        </div>

    </div>


    <div class="col-lg-6">

        <div class="dashboard-card h-100">

            <h2 class="h5 mb-4">
                Payment Collection
            </h2>


            <div class="d-flex justify-content-between border-bottom py-2">

                <span>
                    Successful M-PESA
                </span>

                <strong>
                    {{ successful_mpesa_count }}
                </strong>

            </div>


            <div class="d-flex justify-content-between border-bottom py-2">

                <span>
                    M-PESA Collected
                </span>

                <strong>
                    KES {{ mpesa_collected|floatformat:2 }}
                </strong>

            </div>


            <div class="d-flex justify-content-between py-2">

                <span>
                    Estimated Product Cost
                </span>

                <strong>
                    KES {{ estimated_cogs|floatformat:2 }}
                </strong>

            </div>

        </div>

    </div>

</div>


<!-- ===================================================== -->
<!-- DAILY SALES -->
<!-- ===================================================== -->

<div class="dashboard-card mb-4">

    <h2 class="h5 mb-3">
        Daily Sales
    </h2>

    <div class="table-responsive">

        <table class="table align-middle">

            <thead>

                <tr>

                    <th>Date</th>
                    <th>Orders</th>
                    <th class="text-end">
                        Revenue
                    </th>

                </tr>

            </thead>


            <tbody>

                {% for row in daily_sales %}

                    <tr>

                        <td>
                            {{ row.day|date:"d M Y" }}
                        </td>

                        <td>
                            {{ row.orders }}
                        </td>

                        <td class="text-end">
                            KES {{ row.revenue|floatformat:2 }}
                        </td>

                    </tr>

                {% empty %}

                    <tr>

                        <td
                            colspan="3"
                            class="text-center text-muted py-4"
                        >
                            No paid sales in this period.
                        </td>

                    </tr>

                {% endfor %}

            </tbody>

        </table>

    </div>

</div>


<!-- ===================================================== -->
<!-- TOP PRODUCTS / CUSTOMERS -->
<!-- ===================================================== -->

<div class="row g-4 mb-4">

    <div class="col-lg-6">

        <div class="dashboard-card h-100">

            <h2 class="h5 mb-3">
                Top Products
            </h2>

            <div class="table-responsive">

                <table class="table align-middle">

                    <thead>

                        <tr>

                            <th>Product</th>

                            <th class="text-end">
                                Qty
                            </th>

                            <th class="text-end">
                                Revenue
                            </th>

                        </tr>

                    </thead>

                    <tbody>

                        {% for row in top_products %}

                            <tr>

                                <td>
                                    {{ row.product_name }}
                                </td>

                                <td class="text-end">
                                    {{ row.quantity_sold }}
                                </td>

                                <td class="text-end">
                                    KES {{ row.revenue|floatformat:2 }}
                                </td>

                            </tr>

                        {% empty %}

                            <tr>

                                <td
                                    colspan="3"
                                    class="text-muted text-center"
                                >
                                    No sales.
                                </td>

                            </tr>

                        {% endfor %}

                    </tbody>

                </table>

            </div>

        </div>

    </div>


    <div class="col-lg-6">

        <div class="dashboard-card h-100">

            <h2 class="h5 mb-3">
                Top Customers
            </h2>

            <div class="table-responsive">

                <table class="table align-middle">

                    <thead>

                        <tr>

                            <th>Customer</th>

                            <th class="text-end">
                                Orders
                            </th>

                            <th class="text-end">
                                Spent
                            </th>

                        </tr>

                    </thead>

                    <tbody>

                        {% for row in top_customers %}

                            <tr>

                                <td>

                                    {{ row.full_name }}

                                    <small class="d-block text-muted">
                                        {{ row.phone }}
                                    </small>

                                </td>

                                <td class="text-end">
                                    {{ row.order_count }}
                                </td>

                                <td class="text-end">
                                    KES {{ row.total_spent|floatformat:2 }}
                                </td>

                            </tr>

                        {% empty %}

                            <tr>

                                <td
                                    colspan="3"
                                    class="text-muted text-center"
                                >
                                    No customers.
                                </td>

                            </tr>

                        {% endfor %}

                    </tbody>

                </table>

            </div>

        </div>

    </div>

</div>


<!-- ===================================================== -->
<!-- STATUS BREAKDOWNS -->
<!-- ===================================================== -->

<div class="row g-4 mb-4">

    <div class="col-lg-6">

        <div class="dashboard-card h-100">

            <h2 class="h5">
                Order Status
            </h2>

            {% for row in order_statuses %}

                <div class="d-flex justify-content-between border-bottom py-2">

                    <span>
                        {{ row.status|title }}
                    </span>

                    <strong>
                        {{ row.total }}
                    </strong>

                </div>

            {% empty %}

                <p class="text-muted">
                    No orders.
                </p>

            {% endfor %}

        </div>

    </div>


    <div class="col-lg-6">

        <div class="dashboard-card h-100">

            <h2 class="h5">
                Payment Status
            </h2>

            {% for row in payment_statuses %}

                <div class="d-flex justify-content-between border-bottom py-2">

                    <span>
                        {{ row.payment_status|title }}
                    </span>

                    <strong>
                        {{ row.total }}
                    </strong>

                </div>

            {% empty %}

                <p class="text-muted">
                    No orders.
                </p>

            {% endfor %}

        </div>

    </div>

</div>


<!-- ===================================================== -->
<!-- RECENT PAID ORDERS -->
<!-- ===================================================== -->

<div class="dashboard-card">

    <h2 class="h5 mb-3">
        Recent Paid Orders
    </h2>

    <div class="table-responsive">

        <table class="table align-middle">

            <thead>

                <tr>

                    <th>Order</th>
                    <th>Customer</th>
                    <th>Status</th>
                    <th>Payment</th>
                    <th>Date</th>

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
                            >
                                {{ order.order_number }}
                            </a>

                        </td>

                        <td>
                            {{ order.full_name }}
                        </td>

                        <td>
                            {{ order.get_status_display }}
                        </td>

                        <td>
                            {{ order.get_payment_status_display }}
                        </td>

                        <td>
                            {{ order.created_at|date:"d M Y H:i" }}
                        </td>

                        <td class="text-end">
                            KES {{ order.total_amount|floatformat:2 }}
                        </td>

                    </tr>

                {% empty %}

                    <tr>

                        <td
                            colspan="6"
                            class="text-center text-muted py-4"
                        >
                            No paid orders.
                        </td>

                    </tr>

                {% endfor %}

            </tbody>

        </table>

    </div>

</div>

{% endblock %}
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Sales reports template created."
)


# ============================================================
# 4. ACTIVATE REPORTS SIDEBAR
# ============================================================

base = BASE.read_text(
    encoding="utf-8-sig"
)


if (
    "{% url 'admin_sales_reports' %}"
    not in base
):

    pattern = re.compile(
        r'''
        <a\b
        (?:
            (?!</a>).
        )*?
        <span>
        \s*
        Reports
        \s*
        </span>
        (?:
            (?!</a>).
        )*?
        </a>
        ''',
        re.S | re.X,
    )

    matches = list(
        pattern.finditer(
            base
        )
    )


    if len(matches) != 1:

        raise RuntimeError(
            "Expected exactly one Reports "
            f"sidebar item, found {len(matches)}."
        )


    replacement = r'''
            <a
                href="{% url 'admin_sales_reports' %}"
                class="
                    sidebar-link
                    {% if request.resolver_match.url_name == 'admin_sales_reports' or request.resolver_match.url_name == 'admin_sales_reports_csv' %}
                        active
                    {% endif %}
                "
            >

                <i class="bi bi-bar-chart-line"></i>

                <span>
                    Reports
                </span>

            </a>
'''

    match = matches[0]

    base = (
        base[:match.start()]
        + replacement
        + base[match.end():]
    )


BASE.write_text(
    base,
    encoding="utf-8",
)

print(
    "Reports sidebar activated."
)


# ============================================================
# 5. TESTS
# ============================================================

tests = (
    DASHBOARD
    / "test_phase9a.py"
)

tests.write_text(
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
    RefundRequest,
)

from products.models import Product


User = get_user_model()


class Phase9AReportsTests(
    TestCase
):

    def setUp(self):

        self.staff = (
            User.objects.create_user(
                username="reportstaff",
                password="pass12345",
                role=User.ADMIN,
                is_staff=True,
            )
        )

        self.customer = (
            User.objects.create_user(
                username="reportcustomer",
                password="pass12345",
                role=User.CUSTOMER,
            )
        )

        self.category = (
            Category.objects.create(
                name="Reports Category",
                slug="reports-category",
            )
        )

        self.product = (
            Product.objects.create(
                category=self.category,
                name="Reports Product",
                slug="reports-product",
                sku="RPT-001",
                price=Decimal("2000.00"),
                cost_price=Decimal("1000.00"),
                stock=10,
                reserved_stock=0,
                is_active=True,
            )
        )

        self.order = (
            Order.objects.create(
                user=self.customer,
                order_number="REPORT-001",
                full_name="Report Customer",
                phone="0712345678",
                email="report@example.com",
                county="Nairobi",
                city="Nairobi",
                estate="CBD",
                house_number="1",
                subtotal=Decimal("4000.00"),
                shipping_cost=Decimal("300.00"),
                discount=Decimal("0.00"),
                total_amount=Decimal("4300.00"),
                status="delivered",
                payment_status="paid",
                inventory_status="consumed",
            )
        )

        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=self.product.name,
            price=Decimal("2000.00"),
            quantity=2,
            subtotal=Decimal("4000.00"),
        )


    def test_staff_can_view_report(
        self
    ):

        self.client.login(
            username="reportstaff",
            password="pass12345",
        )

        response = self.client.get(
            reverse(
                "admin_sales_reports"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Sales & Business Analytics",
        )

        self.assertContains(
            response,
            "4300.00",
        )


    def test_non_staff_cannot_view_report(
        self
    ):

        self.client.login(
            username="reportcustomer",
            password="pass12345",
        )

        response = self.client.get(
            reverse(
                "admin_sales_reports"
            )
        )

        self.assertNotEqual(
            response.status_code,
            200,
        )


    def test_processed_refund_reduces_net_revenue(
        self
    ):

        RefundRequest.objects.create(
            order=self.order,
            amount=Decimal("500.00"),
            reason="Report test refund",
            status="processed",
        )

        self.client.login(
            username="reportstaff",
            password="pass12345",
        )

        response = self.client.get(
            reverse(
                "admin_sales_reports"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.context[
                "gross_revenue"
            ],
            Decimal("4300.00"),
        )

        self.assertEqual(
            response.context[
                "processed_refunds"
            ],
            Decimal("500.00"),
        )

        self.assertEqual(
            response.context[
                "net_revenue"
            ],
            Decimal("3800.00"),
        )


    def test_csv_export(
        self
    ):

        self.client.login(
            username="reportstaff",
            password="pass12345",
        )

        response = self.client.get(
            reverse(
                "admin_sales_reports_csv"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response[
                "Content-Type"
            ],
            "text/csv; charset=utf-8",
        )

        self.assertIn(
            "Sales Report",
            response.content.decode(
                "utf-8"
            ),
        )
'''.strip() + "\n",
encoding="utf-8",
)


print()
print("=" * 72)
print("PHASE 9A SALES REPORTS COMPLETE")
print("=" * 72)
print()
print("No database migration should be required.")
print()
print("Next:")
print("python manage.py check")
print("python manage.py test dashboard.test_phase9a -v 2")
