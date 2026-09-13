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

from .report_extensions import build_advanced_report

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


    # --------------------------------------------------------
    # Historical financial snapshots
    #
    # IMPORTANT:
    # These values come from each Order snapshot.
    # We NEVER recalculate old orders using today's tax
    # or currency configuration.
    # --------------------------------------------------------

    merchandise_subtotal = _money(
        paid_orders.aggregate(
            total=Coalesce(
                Sum(
                    "subtotal"
                ),
                ZERO,
                output_field=DecimalField(),
            )
        )["total"]
    )


    discounts_given = _money(
        paid_orders.aggregate(
            total=Coalesce(
                Sum(
                    "discount"
                ),
                ZERO,
                output_field=DecimalField(),
            )
        )["total"]
    )


    net_merchandise_before_tax = (
        merchandise_subtotal
        - discounts_given
    )


    tax_collected = _money(
        paid_orders.aggregate(
            total=Coalesce(
                Sum(
                    "tax_amount"
                ),
                ZERO,
                output_field=DecimalField(),
            )
        )["total"]
    )


    taxable_order_count = (
        paid_orders
        .filter(
            tax_amount__gt=ZERO
        )
        .count()
    )


    non_taxable_order_count = (
        paid_orders.count()
        - taxable_order_count
    )


    currency_breakdown = list(
        paid_orders
        .values(
            "currency_code_at_checkout",
            "currency_symbol_at_checkout",
        )
        .annotate(
            order_count=Count(
                "id"
            ),

            subtotal=Coalesce(
                Sum(
                    "subtotal"
                ),
                ZERO,
                output_field=DecimalField(),
            ),

            discount=Coalesce(
                Sum(
                    "discount"
                ),
                ZERO,
                output_field=DecimalField(),
            ),

            tax=Coalesce(
                Sum(
                    "tax_amount"
                ),
                ZERO,
                output_field=DecimalField(),
            ),

            delivery=Coalesce(
                Sum(
                    "shipping_cost"
                ),
                ZERO,
                output_field=DecimalField(),
            ),

            total=Coalesce(
                Sum(
                    "total_amount"
                ),
                ZERO,
                output_field=DecimalField(),
            ),
        )
        .order_by(
            "currency_code_at_checkout",
            "currency_symbol_at_checkout",
        )
    )


    currency_pairs = {
        (
            row[
                "currency_code_at_checkout"
            ],
            row[
                "currency_symbol_at_checkout"
            ],
        )
        for row in currency_breakdown
    }


    has_mixed_currencies = (
        len(currency_pairs) > 1
    )


    if len(currency_pairs) == 1:

        (
            report_currency_code,
            report_currency_symbol,
        ) = next(
            iter(
                currency_pairs
            )
        )

        report_currency_label = (
            report_currency_code
            or report_currency_symbol
            or "KES"
        )

    elif has_mixed_currencies:

        report_currency_code = "MIXED"
        report_currency_symbol = ""
        report_currency_label = "MIXED"

    else:

        report_currency_code = "KES"
        report_currency_symbol = "KSh"
        report_currency_label = "KES"


    processed_refund_qs = (
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


    historical_cogs = ZERO

    legacy_estimated_cogs = ZERO

    historical_cost_items = 0

    legacy_cost_items = 0


    for item in paid_items:

        # ----------------------------------------------------
        # New orders:
        # use immutable sale-time cost snapshot.
        # ----------------------------------------------------

        if (
            item.cost_subtotal_at_sale
            is not None
        ):

            historical_cogs += Decimal(
                item.cost_subtotal_at_sale
            )

            historical_cost_items += 1

            continue


        # ----------------------------------------------------
        # Legacy orders:
        # no historical snapshot exists.
        #
        # Fall back to CURRENT product cost, but keep it
        # separate so reports do not pretend it is historical.
        # ----------------------------------------------------

        unit_cost = ZERO

        if (
            item.variant_id
            and getattr(
                item.variant,
                "cost_price",
                None,
            )
            is not None
        ):

            unit_cost = Decimal(
                item.variant.cost_price
            )

        elif (
            item.product_id
            and getattr(
                item.product,
                "cost_price",
                None,
            )
            is not None
        ):

            unit_cost = Decimal(
                item.product.cost_price
            )


        legacy_estimated_cogs += (
            unit_cost
            * item.quantity
        )

        legacy_cost_items += 1


    estimated_cogs = (
        historical_cogs
        + legacy_estimated_cogs
    )


    # Tax collected is separated from operating profit.
    #
    # Refunds are already deducted through net_revenue.
    # Item-level tax allocation on refunds can be added later
    # if tax-refund accounting requires it.
    estimated_gross_profit = (
        net_revenue
        - tax_collected
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
            tax=Sum(
                "tax_amount"
            ),
        )
        .order_by(
            "day"
        )
    )


    daily_tax = (
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
            tax=Coalesce(
                Sum(
                    "tax_amount"
                ),
                ZERO,
                output_field=DecimalField(),
            )
        )
        .order_by(
            "day"
        )
    )


    financial_orders = (
        paid_orders
        .order_by(
            "created_at",
            "id",
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


    advanced_report = (
        build_advanced_report(
            orders=orders,
            paid_orders=paid_orders,
            start_dt=start_dt,
            end_dt=end_dt,
            gross_revenue=gross_revenue,
        )
    )


    return {
        "start_date": start_date,
        "end_date": end_date,

        "gross_revenue": (
            gross_revenue
        ),

        "merchandise_subtotal": (
            merchandise_subtotal
        ),

        "discounts_given": (
            discounts_given
        ),

        "net_merchandise_before_tax": (
            net_merchandise_before_tax
        ),

        "tax_collected": (
            tax_collected
        ),

        "taxable_order_count": (
            taxable_order_count
        ),

        "non_taxable_order_count": (
            non_taxable_order_count
        ),

        "currency_breakdown": (
            currency_breakdown
        ),

        "has_mixed_currencies": (
            has_mixed_currencies
        ),

        "report_currency_code": (
            report_currency_code
        ),

        "report_currency_symbol": (
            report_currency_symbol
        ),

        "report_currency_label": (
            report_currency_label
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

        "historical_cogs": (
            historical_cogs
        ),

        "legacy_estimated_cogs": (
            legacy_estimated_cogs
        ),

        "historical_cost_items": (
            historical_cost_items
        ),

        "legacy_cost_items": (
            legacy_cost_items
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

        "daily_tax": (
            daily_tax
        ),

        "financial_orders": (
            financial_orders
        ),

        "recent_orders": (
            recent_orders
        ),

        **advanced_report,
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
            "Merchandise Subtotal",
            context[
                "merchandise_subtotal"
            ],
        ),

        (
            "Discounts Given",
            context[
                "discounts_given"
            ],
        ),

        (
            "Net Merchandise Before Tax",
            context[
                "net_merchandise_before_tax"
            ],
        ),

        (
            "Tax Collected",
            context[
                "tax_collected"
            ],
        ),

        (
            "Taxable Orders",
            context[
                "taxable_order_count"
            ],
        ),

        (
            "Non-taxable Orders",
            context[
                "non_taxable_order_count"
            ],
        ),

        (
            "Report Currency",
            context[
                "report_currency_label"
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
            "Order Financial Detail"
        ]
    )

    writer.writerow(
        [
            "Order Number",
            "Created",
            "Subtotal",
            "Discount",
            "Tax Rate %",
            "Tax Amount",
            "Delivery",
            "Total",
            "Currency Code",
            "Currency Symbol",
            "Payment Status",
        ]
    )


    for order in context[
        "financial_orders"
    ]:

        writer.writerow(
            [
                order.order_number,
                order.created_at,
                order.subtotal,
                order.discount,
                order.tax_rate_at_checkout,
                order.tax_amount,
                order.shipping_cost,
                order.total_amount,
                order.currency_code_at_checkout,
                order.currency_symbol_at_checkout,
                order.payment_status,
            ]
        )


    writer.writerow([])
    writer.writerow(
        [
            "Currency Breakdown"
        ]
    )

    writer.writerow(
        [
            "Currency",
            "Symbol",
            "Orders",
            "Subtotal",
            "Discount",
            "Tax",
            "Delivery",
            "Total",
        ]
    )


    for row in context[
        "currency_breakdown"
    ]:

        writer.writerow(
            [
                row[
                    "currency_code_at_checkout"
                ],
                row[
                    "currency_symbol_at_checkout"
                ],
                row[
                    "order_count"
                ],
                row[
                    "subtotal"
                ],
                row[
                    "discount"
                ],
                row[
                    "tax"
                ],
                row[
                    "delivery"
                ],
                row[
                    "total"
                ],
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


    return response
