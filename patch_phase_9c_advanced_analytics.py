from pathlib import Path
import shutil

ROOT = Path.cwd()

REPORTS = (
    ROOT
    / "dashboard"
    / "reports_views.py"
)

EXTENSIONS = (
    ROOT
    / "dashboard"
    / "report_extensions.py"
)

TEMPLATE = (
    ROOT
    / "templates"
    / "dashboard"
    / "admin"
    / "reports"
    / "sales.html"
)

TESTS = (
    ROOT
    / "dashboard"
    / "test_phase9c.py"
)


# ============================================================
# BACKUPS
# ============================================================

for path in [
    REPORTS,
    TEMPLATE,
]:

    if not path.exists():
        raise RuntimeError(
            f"Missing required file: {path}"
        )

    backup = Path(
        str(path) + ".phase9cbackup"
    )

    if not backup.exists():
        shutil.copy2(
            path,
            backup,
        )


# ============================================================
# 1. ADVANCED REPORTING SERVICE
# ============================================================

EXTENSIONS.write_text(
r'''
from decimal import Decimal

from django.db.models import (
    Count,
    Q,
    Sum,
)

from django.db.models.functions import (
    TruncMonth,
)

from delivery.models import Delivery

from orders.models import OrderItem

from payments.models import RefundRequest


ZERO = Decimal("0.00")


def _money(value):

    if value is None:
        return ZERO

    return Decimal(value)


def _add_share(
    rows,
    value_key,
    total,
):

    rows = list(rows)

    total = _money(total)

    for row in rows:

        value = _money(
            row.get(
                value_key
            )
        )

        row[value_key] = value

        if total > 0:

            row[
                "share_percent"
            ] = round(
                float(
                    (
                        value
                        / total
                    )
                    * Decimal("100")
                ),
                2,
            )

        else:

            row[
                "share_percent"
            ] = 0

    return rows


def _processed_refunds(
    start_dt,
    end_dt,
):

    """
    Refund accounting should use the date the refund was
    processed, not merely the date the original order was
    created.

    Legacy rows without processed_at fall back to order date.
    """

    return (
        RefundRequest.objects
        .filter(
            status="processed",
        )
        .filter(
            Q(
                processed_at__range=[
                    start_dt,
                    end_dt,
                ]
            )
            |
            Q(
                processed_at__isnull=True,
                order__created_at__range=[
                    start_dt,
                    end_dt,
                ],
            )
        )
    )


def build_advanced_report(
    *,
    orders,
    paid_orders,
    start_dt,
    end_dt,
    gross_revenue,
):

    # ========================================================
    # CATEGORY PERFORMANCE
    # ========================================================

    category_rows = (
        OrderItem.objects
        .filter(
            order__in=paid_orders
        )
        .values(
            "product__category__name"
        )
        .annotate(
            quantity_sold=Sum(
                "quantity"
            ),
            revenue=Sum(
                "subtotal"
            ),
            order_count=Count(
                "order",
                distinct=True,
            ),
        )
        .order_by(
            "-revenue"
        )[:15]
    )


    category_performance = (
        _add_share(
            category_rows,
            "revenue",
            gross_revenue,
        )
    )


    for row in category_performance:

        if not row[
            "product__category__name"
        ]:

            row[
                "product__category__name"
            ] = "Uncategorised"


    # ========================================================
    # BRAND PERFORMANCE
    # ========================================================

    brand_rows = (
        OrderItem.objects
        .filter(
            order__in=paid_orders
        )
        .values(
            "product__brand__name"
        )
        .annotate(
            quantity_sold=Sum(
                "quantity"
            ),
            revenue=Sum(
                "subtotal"
            ),
            order_count=Count(
                "order",
                distinct=True,
            ),
        )
        .order_by(
            "-revenue"
        )[:15]
    )


    brand_performance = (
        _add_share(
            brand_rows,
            "revenue",
            gross_revenue,
        )
    )


    for row in brand_performance:

        if not row[
            "product__brand__name"
        ]:

            row[
                "product__brand__name"
            ] = "Unbranded"


    # ========================================================
    # COUNTY PERFORMANCE
    # ========================================================

    county_rows = (
        paid_orders
        .values(
            "county"
        )
        .annotate(
            order_count=Count(
                "id"
            ),
            customer_count=Count(
                "user_id",
                distinct=True,
            ),
            revenue=Sum(
                "total_amount"
            ),
        )
        .order_by(
            "-revenue"
        )[:15]
    )


    county_performance = (
        _add_share(
            county_rows,
            "revenue",
            gross_revenue,
        )
    )


    # ========================================================
    # TOWN / CITY PERFORMANCE
    # ========================================================

    town_rows = (
        paid_orders
        .values(
            "county",
            "city",
        )
        .annotate(
            order_count=Count(
                "id"
            ),
            customer_count=Count(
                "user_id",
                distinct=True,
            ),
            revenue=Sum(
                "total_amount"
            ),
        )
        .order_by(
            "-revenue"
        )[:20]
    )


    town_performance = (
        _add_share(
            town_rows,
            "revenue",
            gross_revenue,
        )
    )


    # ========================================================
    # CUSTOMER LOYALTY
    # ========================================================

    customer_rollup = list(
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
            "-total_spent"
        )
    )


    repeat_customers = [
        row
        for row
        in customer_rollup
        if row[
            "order_count"
        ] > 1
    ]


    one_time_customers = [
        row
        for row
        in customer_rollup
        if row[
            "order_count"
        ] == 1
    ]


    repeat_customer_revenue = sum(
        (
            _money(
                row[
                    "total_spent"
                ]
            )
            for row
            in repeat_customers
        ),
        ZERO,
    )


    repeat_customer_count = len(
        repeat_customers
    )

    one_time_customer_count = len(
        one_time_customers
    )

    unique_customer_count = len(
        customer_rollup
    )


    if unique_customer_count:

        repeat_customer_rate = round(
            (
                repeat_customer_count
                / unique_customer_count
            )
            * 100,
            2,
        )

    else:

        repeat_customer_rate = 0


    top_repeat_customers = (
        repeat_customers[:10]
    )


    # ========================================================
    # MONTHLY SALES TREND
    # ========================================================

    monthly_sales = list(
        paid_orders
        .annotate(
            month=TruncMonth(
                "created_at"
            )
        )
        .values(
            "month"
        )
        .annotate(
            order_count=Count(
                "id"
            ),
            revenue=Sum(
                "total_amount"
            ),
        )
        .order_by(
            "month"
        )
    )


    for row in monthly_sales:

        row[
            "revenue"
        ] = _money(
            row[
                "revenue"
            ]
        )


    # ========================================================
    # DELIVERY PROVIDER PROFITABILITY
    # ========================================================

    delivery_rows = list(
        Delivery.objects
        .filter(
            order__in=paid_orders
        )
        .values(
            "provider__name",
            "management_type",
        )
        .annotate(
            delivery_count=Count(
                "id"
            ),
            customer_charge=Sum(
                "customer_delivery_fee"
            ),
            actual_cost=Sum(
                "actual_delivery_cost"
            ),
        )
        .order_by(
            "-customer_charge"
        )
    )


    delivery_provider_performance = []


    for row in delivery_rows:

        charge = _money(
            row[
                "customer_charge"
            ]
        )

        actual_cost = _money(
            row[
                "actual_cost"
            ]
        )

        count = (
            row[
                "delivery_count"
            ]
            or 0
        )


        if count:

            average_cost = (
                actual_cost
                / count
            )

        else:

            average_cost = ZERO


        delivery_provider_performance.append(
            {
                "provider": (
                    row[
                        "provider__name"
                    ]
                    or (
                        "Shop / "
                        "Unassigned"
                    )
                ),

                "management_type": (
                    row[
                        "management_type"
                    ]
                ),

                "delivery_count": (
                    count
                ),

                "customer_charge": (
                    charge
                ),

                "actual_cost": (
                    actual_cost
                ),

                "margin": (
                    charge
                    - actual_cost
                ),

                "average_cost": (
                    average_cost
                ),
            }
        )


    # ========================================================
    # REFUND PERFORMANCE
    # ========================================================

    refunds = _processed_refunds(
        start_dt,
        end_dt,
    )


    advanced_refund_amount = _money(
        refunds.aggregate(
            total=Sum(
                "amount"
            )
        )[
            "total"
        ]
    )


    advanced_refund_count = (
        refunds.count()
    )


    if gross_revenue > 0:

        refund_rate = round(
            float(
                (
                    advanced_refund_amount
                    / gross_revenue
                )
                * Decimal(
                    "100"
                )
            ),
            2,
        )

    else:

        refund_rate = 0


    # ========================================================
    # ORDER PIPELINE
    # ========================================================

    total_orders = orders.count()


    if total_orders:

        paid_conversion_rate = round(
            (
                paid_orders.count()
                / total_orders
            )
            * 100,
            2,
        )

    else:

        paid_conversion_rate = 0


    return {

        "category_performance":
            category_performance,

        "brand_performance":
            brand_performance,

        "county_performance":
            county_performance,

        "town_performance":
            town_performance,

        "repeat_customer_count":
            repeat_customer_count,

        "one_time_customer_count":
            one_time_customer_count,

        "unique_customer_count":
            unique_customer_count,

        "repeat_customer_rate":
            repeat_customer_rate,

        "repeat_customer_revenue":
            repeat_customer_revenue,

        "top_repeat_customers":
            top_repeat_customers,

        "monthly_sales":
            monthly_sales,

        "delivery_provider_performance":
            delivery_provider_performance,

        "advanced_refund_amount":
            advanced_refund_amount,

        "advanced_refund_count":
            advanced_refund_count,

        "refund_rate":
            refund_rate,

        "paid_conversion_rate":
            paid_conversion_rate,
    }
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Advanced analytics service created."
)


# ============================================================
# 2. CONNECT ADVANCED REPORT TO REPORT ENGINE
# ============================================================

text = REPORTS.read_text(
    encoding="utf-8-sig"
)


if (
    "from .report_extensions import "
    "build_advanced_report"
    not in text
):

    import_marker = (
        "from orders.models import ("
    )

    if import_marker not in text:

        raise RuntimeError(
            "Could not locate reports imports."
        )

    text = text.replace(
        import_marker,
        (
            "from .report_extensions import "
            "build_advanced_report\n\n"
            + import_marker
        ),
        1,
    )


# ============================================================
# 3. CORRECT REFUND PERIOD ACCOUNTING
# ============================================================

old_refund = '''    processed_refunds = _money(
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
'''


new_refund = '''    processed_refund_qs = (
        RefundRequest.objects
        .filter(
            status="processed",
        )
        .filter(
            Q(
                processed_at__range=[
                    start_dt,
                    end_dt,
                ]
            )
            |
            Q(
                processed_at__isnull=True,
                order__created_at__range=[
                    start_dt,
                    end_dt,
                ],
            )
        )
    )


    processed_refunds = _money(
        processed_refund_qs
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
'''


if old_refund in text:

    text = text.replace(
        old_refund,
        new_refund,
        1,
    )


# Q import required

if "    Q,\n" not in text:

    marker = '''    F,
    Sum,
'''

    if marker in text:

        text = text.replace(
            marker,
            '''    F,
    Q,
    Sum,
''',
            1,
        )


# ============================================================
# 4. ADD ADVANCED CONTEXT
# ============================================================

if "advanced_report = (" not in text:

    marker = '''    return {
        "start_date": start_date,
'''

    if marker not in text:

        raise RuntimeError(
            "Could not locate report context return."
        )


    advanced = '''    advanced_report = (
        build_advanced_report(
            orders=orders,
            paid_orders=paid_orders,
            start_dt=start_dt,
            end_dt=end_dt,
            gross_revenue=gross_revenue,
        )
    )


'''

    text = text.replace(
        marker,
        advanced + marker,
        1,
    )


# Spread advanced dictionary into context.

if '"advanced_refund_amount"' not in text:

    marker = '''        "recent_orders": (
            recent_orders
        ),
'''

    replacement = '''        "recent_orders": (
            recent_orders
        ),

        **advanced_report,
'''

    if marker not in text:

        raise RuntimeError(
            "Could not locate recent_orders "
            "context block."
        )

    text = text.replace(
        marker,
        replacement,
        1,
    )


# ============================================================
# 5. EXTEND CSV EXPORT
# ============================================================

if '"Category Performance"' not in text:

    marker = '''    return response
'''

    csv_block = r'''
    # ========================================================
    # ADVANCED BUSINESS ANALYTICS
    # ========================================================

    writer.writerow([])
    writer.writerow(
        [
            "Category Performance"
        ]
    )

    writer.writerow(
        [
            "Category",
            "Units Sold",
            "Orders",
            "Revenue",
            "Revenue Share %",
        ]
    )


    for row in context[
        "category_performance"
    ]:

        writer.writerow(
            [
                row[
                    "product__category__name"
                ],
                row[
                    "quantity_sold"
                ],
                row[
                    "order_count"
                ],
                row[
                    "revenue"
                ],
                row[
                    "share_percent"
                ],
            ]
        )


    writer.writerow([])
    writer.writerow(
        [
            "County Performance"
        ]
    )

    writer.writerow(
        [
            "County",
            "Orders",
            "Customers",
            "Revenue",
            "Revenue Share %",
        ]
    )


    for row in context[
        "county_performance"
    ]:

        writer.writerow(
            [
                row[
                    "county"
                ],
                row[
                    "order_count"
                ],
                row[
                    "customer_count"
                ],
                row[
                    "revenue"
                ],
                row[
                    "share_percent"
                ],
            ]
        )


    writer.writerow([])
    writer.writerow(
        [
            "Delivery Provider Profitability"
        ]
    )

    writer.writerow(
        [
            "Provider",
            "Management",
            "Deliveries",
            "Customer Charges",
            "Actual Cost",
            "Margin",
        ]
    )


    for row in context[
        "delivery_provider_performance"
    ]:

        writer.writerow(
            [
                row[
                    "provider"
                ],
                row[
                    "management_type"
                ],
                row[
                    "delivery_count"
                ],
                row[
                    "customer_charge"
                ],
                row[
                    "actual_cost"
                ],
                row[
                    "margin"
                ],
            ]
        )


    writer.writerow([])
    writer.writerow(
        [
            "Customer Loyalty"
        ]
    )

    writer.writerow(
        [
            "Unique Customers",
            context[
                "unique_customer_count"
            ],
        ]
    )

    writer.writerow(
        [
            "Repeat Customers",
            context[
                "repeat_customer_count"
            ],
        ]
    )

    writer.writerow(
        [
            "Repeat Customer Rate %",
            context[
                "repeat_customer_rate"
            ],
        ]
    )

    writer.writerow(
        [
            "Repeat Customer Revenue",
            context[
                "repeat_customer_revenue"
            ],
        ]
    )


'''

    # Replace LAST return response.
    index = text.rfind(
        marker
    )

    if index == -1:

        raise RuntimeError(
            "Could not locate CSV return response."
        )

    text = (
        text[:index]
        + csv_block
        + text[index:]
    )


REPORTS.write_text(
    text,
    encoding="utf-8",
)

print(
    "Advanced analytics connected to reports."
)


# ============================================================
# 6. REPORT TEMPLATE
# ============================================================

template = TEMPLATE.read_text(
    encoding="utf-8-sig"
)


if "Advanced Business Analytics" not in template:

    marker = '''<!-- ===================================================== -->
<!-- RECENT PAID ORDERS -->
<!-- ===================================================== -->
'''

    if marker not in template:

        raise RuntimeError(
            "Could not locate Recent Paid Orders section."
        )


    advanced_html = r'''
<!-- ===================================================== -->
<!-- ADVANCED BUSINESS ANALYTICS -->
<!-- ===================================================== -->

<div class="dashboard-card mb-4">

    <div class="card-header-custom">

        <div>

            <h2>
                Advanced Business Analytics
            </h2>

            <p>
                Customer loyalty, refunds and
                paid-order performance.
            </p>

        </div>

    </div>


    <div class="row g-3">


        <div class="col-md-6 col-xl-3">

            <div class="border rounded p-3 h-100">

                <small class="text-muted">
                    Unique Customers
                </small>

                <div class="fs-3 fw-bold">
                    {{ unique_customer_count }}
                </div>

            </div>

        </div>


        <div class="col-md-6 col-xl-3">

            <div class="border rounded p-3 h-100">

                <small class="text-muted">
                    Repeat Customers
                </small>

                <div class="fs-3 fw-bold">
                    {{ repeat_customer_count }}
                </div>

                <small class="text-muted">
                    {{ repeat_customer_rate|floatformat:2 }}%
                    of customers
                </small>

            </div>

        </div>


        <div class="col-md-6 col-xl-3">

            <div class="border rounded p-3 h-100">

                <small class="text-muted">
                    Refund Rate
                </small>

                <div class="fs-3 fw-bold">
                    {{ refund_rate|floatformat:2 }}%
                </div>

                <small class="text-muted">
                    {{ advanced_refund_count }}
                    processed refund{{ advanced_refund_count|pluralize }}
                </small>

            </div>

        </div>


        <div class="col-md-6 col-xl-3">

            <div class="border rounded p-3 h-100">

                <small class="text-muted">
                    Paid Order Rate
                </small>

                <div class="fs-3 fw-bold">
                    {{ paid_conversion_rate|floatformat:2 }}%
                </div>

                <small class="text-muted">
                    Paid orders / orders created
                </small>

            </div>

        </div>

    </div>

</div>


<!-- ===================================================== -->
<!-- CATEGORY / BRAND -->
<!-- ===================================================== -->

<div class="row g-4 mb-4">


    <div class="col-xl-6">

        <div class="dashboard-card h-100">

            <h2 class="h5 mb-3">
                Category Performance
            </h2>

            <div class="table-responsive">

                <table class="table align-middle">

                    <thead>

                        <tr>

                            <th>
                                Category
                            </th>

                            <th class="text-end">
                                Units
                            </th>

                            <th class="text-end">
                                Revenue
                            </th>

                            <th class="text-end">
                                Share
                            </th>

                        </tr>

                    </thead>

                    <tbody>

                        {% for row in category_performance %}

                            <tr>

                                <td>
                                    {{ row.product__category__name }}
                                </td>

                                <td class="text-end">
                                    {{ row.quantity_sold }}
                                </td>

                                <td class="text-end">
                                    KES {{ row.revenue|floatformat:2 }}
                                </td>

                                <td class="text-end">
                                    {{ row.share_percent|floatformat:1 }}%
                                </td>

                            </tr>

                        {% empty %}

                            <tr>

                                <td
                                    colspan="4"
                                    class="text-center text-muted"
                                >
                                    No category sales.
                                </td>

                            </tr>

                        {% endfor %}

                    </tbody>

                </table>

            </div>

        </div>

    </div>


    <div class="col-xl-6">

        <div class="dashboard-card h-100">

            <h2 class="h5 mb-3">
                Brand Performance
            </h2>

            <div class="table-responsive">

                <table class="table align-middle">

                    <thead>

                        <tr>

                            <th>
                                Brand
                            </th>

                            <th class="text-end">
                                Units
                            </th>

                            <th class="text-end">
                                Revenue
                            </th>

                            <th class="text-end">
                                Share
                            </th>

                        </tr>

                    </thead>

                    <tbody>

                        {% for row in brand_performance %}

                            <tr>

                                <td>
                                    {{ row.product__brand__name }}
                                </td>

                                <td class="text-end">
                                    {{ row.quantity_sold }}
                                </td>

                                <td class="text-end">
                                    KES {{ row.revenue|floatformat:2 }}
                                </td>

                                <td class="text-end">
                                    {{ row.share_percent|floatformat:1 }}%
                                </td>

                            </tr>

                        {% empty %}

                            <tr>

                                <td
                                    colspan="4"
                                    class="text-center text-muted"
                                >
                                    No brand sales.
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
<!-- GEOGRAPHY -->
<!-- ===================================================== -->

<div class="row g-4 mb-4">


    <div class="col-xl-6">

        <div class="dashboard-card h-100">

            <h2 class="h5 mb-3">
                Sales by County
            </h2>

            <div class="table-responsive">

                <table class="table align-middle">

                    <thead>

                        <tr>

                            <th>
                                County
                            </th>

                            <th class="text-end">
                                Orders
                            </th>

                            <th class="text-end">
                                Customers
                            </th>

                            <th class="text-end">
                                Revenue
                            </th>

                        </tr>

                    </thead>

                    <tbody>

                        {% for row in county_performance %}

                            <tr>

                                <td>
                                    {{ row.county }}
                                </td>

                                <td class="text-end">
                                    {{ row.order_count }}
                                </td>

                                <td class="text-end">
                                    {{ row.customer_count }}
                                </td>

                                <td class="text-end">
                                    KES {{ row.revenue|floatformat:2 }}
                                </td>

                            </tr>

                        {% empty %}

                            <tr>

                                <td
                                    colspan="4"
                                    class="text-center text-muted"
                                >
                                    No county sales.
                                </td>

                            </tr>

                        {% endfor %}

                    </tbody>

                </table>

            </div>

        </div>

    </div>


    <div class="col-xl-6">

        <div class="dashboard-card h-100">

            <h2 class="h5 mb-3">
                Sales by Town / City
            </h2>

            <div class="table-responsive">

                <table class="table align-middle">

                    <thead>

                        <tr>

                            <th>
                                Location
                            </th>

                            <th class="text-end">
                                Orders
                            </th>

                            <th class="text-end">
                                Revenue
                            </th>

                        </tr>

                    </thead>

                    <tbody>

                        {% for row in town_performance %}

                            <tr>

                                <td>

                                    {{ row.city }}

                                    <small class="d-block text-muted">
                                        {{ row.county }}
                                    </small>

                                </td>

                                <td class="text-end">
                                    {{ row.order_count }}
                                </td>

                                <td class="text-end">
                                    KES {{ row.revenue|floatformat:2 }}
                                </td>

                            </tr>

                        {% empty %}

                            <tr>

                                <td
                                    colspan="3"
                                    class="text-center text-muted"
                                >
                                    No town sales.
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
<!-- DELIVERY PROVIDER PROFITABILITY -->
<!-- ===================================================== -->

<div class="dashboard-card mb-4">

    <h2 class="h5 mb-3">
        Delivery Provider Profitability
    </h2>

    <div class="table-responsive">

        <table class="table align-middle">

            <thead>

                <tr>

                    <th>
                        Provider
                    </th>

                    <th>
                        Type
                    </th>

                    <th class="text-end">
                        Deliveries
                    </th>

                    <th class="text-end">
                        Charged
                    </th>

                    <th class="text-end">
                        Actual Cost
                    </th>

                    <th class="text-end">
                        Margin
                    </th>

                </tr>

            </thead>


            <tbody>

                {% for row in delivery_provider_performance %}

                    <tr>

                        <td class="fw-semibold">
                            {{ row.provider }}
                        </td>

                        <td>
                            {{ row.management_type|title }}
                        </td>

                        <td class="text-end">
                            {{ row.delivery_count }}
                        </td>

                        <td class="text-end">
                            KES {{ row.customer_charge|floatformat:2 }}
                        </td>

                        <td class="text-end">
                            KES {{ row.actual_cost|floatformat:2 }}
                        </td>

                        <td class="text-end">

                            {% if row.margin < 0 %}

                                <span class="text-danger fw-bold">
                                    KES {{ row.margin|floatformat:2 }}
                                </span>

                            {% else %}

                                <span class="text-success fw-bold">
                                    KES {{ row.margin|floatformat:2 }}
                                </span>

                            {% endif %}

                        </td>

                    </tr>

                {% empty %}

                    <tr>

                        <td
                            colspan="6"
                            class="text-center text-muted py-4"
                        >
                            No delivery financial data.
                        </td>

                    </tr>

                {% endfor %}

            </tbody>

        </table>

    </div>

</div>


<!-- ===================================================== -->
<!-- MONTHLY TREND / REPEAT CUSTOMERS -->
<!-- ===================================================== -->

<div class="row g-4 mb-4">


    <div class="col-xl-6">

        <div class="dashboard-card h-100">

            <h2 class="h5 mb-3">
                Monthly Sales Trend
            </h2>

            <div class="table-responsive">

                <table class="table align-middle">

                    <thead>

                        <tr>

                            <th>
                                Month
                            </th>

                            <th class="text-end">
                                Orders
                            </th>

                            <th class="text-end">
                                Revenue
                            </th>

                        </tr>

                    </thead>

                    <tbody>

                        {% for row in monthly_sales %}

                            <tr>

                                <td>
                                    {{ row.month|date:"M Y" }}
                                </td>

                                <td class="text-end">
                                    {{ row.order_count }}
                                </td>

                                <td class="text-end">
                                    KES {{ row.revenue|floatformat:2 }}
                                </td>

                            </tr>

                        {% empty %}

                            <tr>

                                <td
                                    colspan="3"
                                    class="text-center text-muted"
                                >
                                    No monthly sales.
                                </td>

                            </tr>

                        {% endfor %}

                    </tbody>

                </table>

            </div>

        </div>

    </div>


    <div class="col-xl-6">

        <div class="dashboard-card h-100">

            <h2 class="h5 mb-3">
                Repeat Customers
            </h2>

            <div class="mb-3">

                <small class="text-muted">
                    Revenue from repeat customers
                </small>

                <div class="fs-4 fw-bold">

                    KES {{ repeat_customer_revenue|floatformat:2 }}

                </div>

            </div>


            <div class="table-responsive">

                <table class="table align-middle">

                    <thead>

                        <tr>

                            <th>
                                Customer
                            </th>

                            <th class="text-end">
                                Orders
                            </th>

                            <th class="text-end">
                                Spent
                            </th>

                        </tr>

                    </thead>

                    <tbody>

                        {% for row in top_repeat_customers %}

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
                                    class="text-center text-muted"
                                >
                                    No repeat customers
                                    in this period yet.
                                </td>

                            </tr>

                        {% endfor %}

                    </tbody>

                </table>

            </div>

        </div>

    </div>

</div>


<div
    class="
        alert
        alert-info
        mb-4
    "
>

    <strong>
        Refund allocation note:
    </strong>

    Product, brand and category figures show
    gross paid sales.

    Your current refund model records refunds at
    order level rather than allocating the refunded
    amount to individual order items, so the system
    does not fabricate product-level net sales.

</div>


'''

    template = template.replace(
        marker,
        advanced_html + marker,
        1,
    )


TEMPLATE.write_text(
    template,
    encoding="utf-8",
)

print(
    "Advanced business analytics UI added."
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

from django.test import TestCase

from django.urls import reverse

from categories.models import Category

from delivery.models import (
    Delivery,
    DeliveryProvider,
)

from orders.models import (
    Order,
    OrderItem,
)

from products.models import Product


User = get_user_model()


class Phase9CAdvancedAnalyticsTests(
    TestCase
):

    def setUp(self):

        self.staff = (
            User.objects.create_user(
                username="phase9cstaff",
                password="pass12345",
                role=User.ADMIN,
                is_staff=True,
            )
        )

        self.customer = (
            User.objects.create_user(
                username="phase9ccustomer",
                password="pass12345",
                role=User.CUSTOMER,
            )
        )


        self.category = (
            Category.objects.create(
                name="Computers",
                slug="computers-phase9c",
            )
        )


        self.product = (
            Product.objects.create(
                category=self.category,
                name="Phase 9C Laptop",
                slug="phase-9c-laptop",
                sku="P9C-001",
                price=Decimal(
                    "40000.00"
                ),
                cost_price=Decimal(
                    "30000.00"
                ),
                stock=20,
                reserved_stock=0,
                is_active=True,
            )
        )


        self.order1 = (
            self._make_order(
                "P9C-001",
                Decimal(
                    "40000.00"
                ),
            )
        )


        self.order2 = (
            self._make_order(
                "P9C-002",
                Decimal(
                    "40000.00"
                ),
            )
        )


        self.provider = (
            DeliveryProvider.objects.create(
                name="Phase 9C Courier",
                provider_type="courier",
            )
        )


        Delivery.objects.create(
            order=self.order1,
            management_type="external",
            method="local_door",
            provider=self.provider,
            destination="Nairobi CBD",
            customer_delivery_fee=Decimal(
                "500.00"
            ),
            actual_delivery_cost=Decimal(
                "350.00"
            ),
            status="delivered",
        )


    def _make_order(
        self,
        number,
        amount,
    ):

        order = Order.objects.create(
            user=self.customer,
            order_number=number,
            full_name="Phase 9C Customer",
            phone="0712345678",
            email="phase9c@example.com",
            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="1",
            subtotal=amount,
            shipping_cost=Decimal(
                "0.00"
            ),
            discount=Decimal(
                "0.00"
            ),
            total_amount=amount,
            status="delivered",
            payment_status="paid",
            inventory_status="consumed",
        )


        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            price=amount,
            unit_cost_at_sale=Decimal(
                "30000.00"
            ),
            cost_subtotal_at_sale=Decimal(
                "30000.00"
            ),
            quantity=1,
            subtotal=amount,
        )


        return order


    def test_category_performance(
        self
    ):

        self.client.login(
            username="phase9cstaff",
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


        rows = response.context[
            "category_performance"
        ]


        self.assertEqual(
            rows[0][
                "product__category__name"
            ],
            "Computers",
        )


        self.assertEqual(
            rows[0][
                "quantity_sold"
            ],
            2,
        )


    def test_repeat_customer_detected(
        self
    ):

        self.client.login(
            username="phase9cstaff",
            password="pass12345",
        )


        response = self.client.get(
            reverse(
                "admin_sales_reports"
            )
        )


        self.assertEqual(
            response.context[
                "repeat_customer_count"
            ],
            1,
        )


        self.assertEqual(
            response.context[
                "unique_customer_count"
            ],
            1,
        )


        self.assertEqual(
            response.context[
                "repeat_customer_rate"
            ],
            100.0,
        )


    def test_delivery_provider_margin(
        self
    ):

        self.client.login(
            username="phase9cstaff",
            password="pass12345",
        )


        response = self.client.get(
            reverse(
                "admin_sales_reports"
            )
        )


        rows = response.context[
            "delivery_provider_performance"
        ]


        self.assertEqual(
            len(rows),
            1,
        )


        self.assertEqual(
            rows[0][
                "provider"
            ],
            "Phase 9C Courier",
        )


        self.assertEqual(
            rows[0][
                "margin"
            ],
            Decimal(
                "150.00"
            ),
        )


    def test_county_performance(
        self
    ):

        self.client.login(
            username="phase9cstaff",
            password="pass12345",
        )


        response = self.client.get(
            reverse(
                "admin_sales_reports"
            )
        )


        rows = response.context[
            "county_performance"
        ]


        self.assertEqual(
            rows[0][
                "county"
            ],
            "Nairobi",
        )


        self.assertEqual(
            rows[0][
                "order_count"
            ],
            2,
        )
'''.strip() + "\n",
encoding="utf-8",
)


print(
    "Phase 9C tests created."
)


print()
print("=" * 72)
print("PHASE 9C ADVANCED BUSINESS ANALYTICS INSTALLED")
print("=" * 72)
print()
print("Added:")
print("  Category performance")
print("  Brand performance")
print("  County performance")
print("  Town / city performance")
print("  Repeat customer metrics")
print("  Monthly trends")
print("  Delivery provider profitability")
print("  Refund-rate analysis")
print("  Extended CSV export")
print()
print("No migration required.")
