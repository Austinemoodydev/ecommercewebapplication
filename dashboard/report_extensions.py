from decimal import Decimal

from django.db.models import (
    Count,
    Q,
    Sum,
)

from django.utils import timezone

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

    # ====================================================
    # MONTHLY SALES
    #
    # Do NOT use TruncMonth here.
    #
    # MySQL installations without populated timezone tables
    # can fail when Django asks the database to perform
    # timezone-aware datetime truncation.
    #
    # We already have the correct filtered QuerySet, so group
    # the relatively small report result in Python using
    # Django's active timezone.
    # ====================================================

    monthly_map = {}


    for order in (
        paid_orders
        .order_by(
            "created_at"
        )
    ):

        created_at = order.created_at


        if timezone.is_aware(
            created_at
        ):

            created_at = (
                timezone.localtime(
                    created_at
                )
            )


        month_key = (
            created_at.year,
            created_at.month,
        )


        if month_key not in monthly_map:

            month_start = (
                created_at.replace(
                    day=1,
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0,
                )
            )


            monthly_map[
                month_key
            ] = {
                "month": month_start,
                "order_count": 0,
                "revenue": ZERO,
            }


        monthly_map[
            month_key
        ][
            "order_count"
        ] += 1


        monthly_map[
            month_key
        ][
            "revenue"
        ] += _money(
            order.total_amount
        )


    monthly_sales = [
        monthly_map[key]
        for key
        in sorted(
            monthly_map
        )
    ]


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
