from pathlib import Path
import shutil


ROOT = Path.cwd()

REPORTS = (
    ROOT
    / "dashboard"
    / "reports_views.py"
)

SALES_TEMPLATE = (
    ROOT
    / "templates"
    / "dashboard"
    / "admin"
    / "reports"
    / "sales.html"
)

DOCUMENT_VIEWS = (
    ROOT
    / "orders"
    / "document_views.py"
)

CREDIT_VIEWS = (
    ROOT
    / "orders"
    / "credit_note_views.py"
)

CREDIT_SERVICE = (
    ROOT
    / "orders"
    / "credit_note_service.py"
)

CORE_FORMS = (
    ROOT
    / "core"
    / "forms.py"
)

TESTS = (
    ROOT
    / "dashboard"
    / "test_phase12d.py"
)


FILES = [
    REPORTS,
    SALES_TEMPLATE,
    DOCUMENT_VIEWS,
    CREDIT_VIEWS,
    CREDIT_SERVICE,
    CORE_FORMS,
]


for path in FILES:

    if not path.exists():

        raise RuntimeError(
            f"Missing required file: {path}"
        )


for path in FILES:

    backup = Path(
        str(path)
        + ".phase12dbackup"
    )

    if not backup.exists():

        shutil.copy2(
            path,
            backup,
        )


# ============================================================
# 1. SALES REPORT — HISTORICAL FINANCIAL BREAKDOWN
# ============================================================

text = REPORTS.read_text(
    encoding="utf-8-sig"
)


if "tax_collected" not in text:

    marker = '''    gross_revenue = _money(
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


    processed_refund_qs = (
'''


    replacement = '''    gross_revenue = _money(
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
'''


    if marker not in text:

        raise RuntimeError(
            "Could not locate report revenue block."
        )


    text = text.replace(
        marker,
        replacement,
        1,
    )


# ============================================================
# 2. PROFIT SHOULD NOT TREAT TAX AS BUSINESS PROFIT
# ============================================================

old = '''    estimated_gross_profit = (
        net_revenue
        - estimated_cogs
        - actual_delivery_cost
    )
'''


new = '''    # Tax collected is separated from operating profit.
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
'''


if old in text:

    text = text.replace(
        old,
        new,
        1,
    )


# ============================================================
# 3. DAILY TAX TREND
# ============================================================

if "daily_tax" not in text:

    marker = '''    daily_sales = (
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
'''


    replacement = '''    daily_sales = (
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
'''


    if marker not in text:

        raise RuntimeError(
            "Could not locate daily sales block."
        )


    text = text.replace(
        marker,
        replacement,
        1,
    )


# ============================================================
# 4. REPORT CONTEXT
# ============================================================

if '"tax_collected": (' not in text:

    marker = '''        "gross_revenue": (
            gross_revenue
        ),

        "processed_refunds": (
'''


    addition = '''        "gross_revenue": (
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
'''


    if marker not in text:

        raise RuntimeError(
            "Could not locate report context revenue."
        )


    text = text.replace(
        marker,
        addition,
        1,
    )


if '"daily_tax": (' not in text:

    marker = '''        "daily_sales": (
            daily_sales
        ),

        "recent_orders": (
'''


    addition = '''        "daily_sales": (
            daily_sales
        ),

        "daily_tax": (
            daily_tax
        ),

        "financial_orders": (
            financial_orders
        ),

        "recent_orders": (
'''


    if marker not in text:

        raise RuntimeError(
            "Could not locate daily report context."
        )


    text = text.replace(
        marker,
        addition,
        1,
    )


# ============================================================
# 5. CSV SUMMARY TAX METRICS
# ============================================================

if '"Tax Collected"' not in text:

    marker = '''        (
            "Gross Revenue",
            context[
                "gross_revenue"
            ],
        ),

        (
            "Processed Refunds",
'''


    addition = '''        (
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
'''


    if marker not in text:

        raise RuntimeError(
            "Could not locate CSV metrics block."
        )


    text = text.replace(
        marker,
        addition,
        1,
    )


# ============================================================
# 6. CSV HISTORICAL ORDER FINANCIAL DETAIL
# ============================================================

if '"Order Financial Detail"' not in text:

    marker = '''    writer.writerow([])
    writer.writerow(
        [
            "Top Products"
        ]
    )
'''


    addition = '''    writer.writerow([])

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
'''


    if marker not in text:

        raise RuntimeError(
            "Could not locate CSV Top Products block."
        )


    text = text.replace(
        marker,
        addition,
        1,
    )


REPORTS.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# 7. REPORT UI
# ============================================================

text = SALES_TEMPLATE.read_text(
    encoding="utf-8-sig"
)


# Replace hard-coded KES labels on this report.
text = text.replace(
    "KES {{",
    "{{ report_currency_label }} {{",
)


if "Historical Financial Breakdown" not in text:

    marker = '''<!-- ===================================================== -->
<!-- ORDER KPI -->
<!-- ===================================================== -->
'''


    addition = '''<!-- ===================================================== -->
<!-- HISTORICAL FINANCIAL BREAKDOWN -->
<!-- ===================================================== -->

<div class="dashboard-card mb-4">

    <div
        class="
            d-flex
            justify-content-between
            align-items-start
            flex-wrap
            gap-3
            mb-3
        "
    >

        <div>

            <h2 class="h5 mb-1">
                Historical Financial Breakdown
            </h2>

            <p class="text-muted mb-0">
                Tax and currency values are taken from
                each order's checkout snapshot.
            </p>

        </div>

        <span class="badge bg-light text-dark border">

            Currency:
            {{ report_currency_label }}

        </span>

    </div>


    {% if has_mixed_currencies %}

        <div class="alert alert-warning">

            This period contains more than one currency.
            Totals are not foreign-exchange converted.
            Use the currency breakdown below for accurate
            currency-by-currency reporting.

        </div>

    {% endif %}


    <div class="row g-3">

        <div class="col-md-6 col-xl-3">

            <div class="border rounded p-3 h-100">

                <small class="text-muted">
                    Merchandise Subtotal
                </small>

                <div class="fs-5 fw-bold">

                    {{ report_currency_label }}
                    {{ merchandise_subtotal|floatformat:2 }}

                </div>

            </div>

        </div>


        <div class="col-md-6 col-xl-3">

            <div class="border rounded p-3 h-100">

                <small class="text-muted">
                    Discounts
                </small>

                <div class="fs-5 fw-bold">

                    {{ report_currency_label }}
                    {{ discounts_given|floatformat:2 }}

                </div>

            </div>

        </div>


        <div class="col-md-6 col-xl-3">

            <div class="border rounded p-3 h-100">

                <small class="text-muted">
                    Net Merchandise Before Tax
                </small>

                <div class="fs-5 fw-bold">

                    {{ report_currency_label }}
                    {{ net_merchandise_before_tax|floatformat:2 }}

                </div>

            </div>

        </div>


        <div class="col-md-6 col-xl-3">

            <div class="border rounded p-3 h-100">

                <small class="text-muted">
                    Tax Collected
                </small>

                <div class="fs-5 fw-bold">

                    {{ report_currency_label }}
                    {{ tax_collected|floatformat:2 }}

                </div>

            </div>

        </div>

    </div>


    <div class="row g-3 mt-1">

        <div class="col-md-6">

            <div class="border rounded p-3">

                <small class="text-muted">
                    Taxable Paid Orders
                </small>

                <div class="fs-4 fw-bold">
                    {{ taxable_order_count }}
                </div>

            </div>

        </div>


        <div class="col-md-6">

            <div class="border rounded p-3">

                <small class="text-muted">
                    Non-taxable Paid Orders
                </small>

                <div class="fs-4 fw-bold">
                    {{ non_taxable_order_count }}
                </div>

            </div>

        </div>

    </div>


    {% if currency_breakdown %}

        <div class="table-responsive mt-4">

            <table class="table align-middle">

                <thead>

                    <tr>
                        <th>Currency</th>
                        <th>Orders</th>
                        <th>Subtotal</th>
                        <th>Discount</th>
                        <th>Tax</th>
                        <th>Delivery</th>
                        <th>Total</th>
                    </tr>

                </thead>

                <tbody>

                    {% for row in currency_breakdown %}

                        <tr>

                            <td>
                                <strong>
                                    {{ row.currency_code_at_checkout }}
                                </strong>

                                {{ row.currency_symbol_at_checkout }}
                            </td>

                            <td>
                                {{ row.order_count }}
                            </td>

                            <td>
                                {{ row.subtotal|floatformat:2 }}
                            </td>

                            <td>
                                {{ row.discount|floatformat:2 }}
                            </td>

                            <td>
                                {{ row.tax|floatformat:2 }}
                            </td>

                            <td>
                                {{ row.delivery|floatformat:2 }}
                            </td>

                            <td>
                                {{ row.total|floatformat:2 }}
                            </td>

                        </tr>

                    {% endfor %}

                </tbody>

            </table>

        </div>

    {% endif %}

</div>


''' + marker


    if marker not in text:

        raise RuntimeError(
            "Could not locate report ORDER KPI section."
        )


    text = text.replace(
        marker,
        addition,
        1,
    )


SALES_TEMPLATE.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# 8. INVOICE / RECEIPT EMAIL MUST ALWAYS USE CUSTOMER URL
# ============================================================

text = DOCUMENT_VIEWS.read_text(
    encoding="utf-8-sig"
)


if "def customer_document_view_url(" not in text:

    marker = '''def document_view_url(
    request,
    document,
):
'''


    helper = '''def customer_document_view_url(
    document,
):

    from django.urls import reverse


    route = (
        "customer_order_invoice"
        if (
            document.document_type
            == "invoice"
        )
        else
        "customer_order_receipt"
    )


    return reverse(
        route,
        args=[
            document.order.order_number
        ],
    )



''' + marker


    if marker not in text:

        raise RuntimeError(
            "Could not locate document_view_url()."
        )


    text = text.replace(
        marker,
        helper,
        1,
    )


old = '''            document_view_url(
                request,
                document,
            )
'''


new = '''            customer_document_view_url(
                document,
            )
'''


# Replace ONLY first occurrence — this is inside email generation.
if old in text:

    text = text.replace(
        old,
        new,
        1,
    )


# Historical document currency in email.
old = '''        f"Order total: KES "
        f"{order_snapshot['total_amount']}\\n\\n"
'''


new = '''        f"Order total: "
        f"{order_snapshot.get('currency_symbol', 'KSh')} "
        f"{order_snapshot['total_amount']}\\n\\n"
'''


if old in text:

    text = text.replace(
        old,
        new,
        1,
    )


DOCUMENT_VIEWS.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# 9. CREDIT NOTE SNAPSHOT — HISTORICAL ORDER CURRENCY
# ============================================================

text = CREDIT_SERVICE.read_text(
    encoding="utf-8-sig"
)


if '"currency_code":' not in text[
    text.find('"order": {'):
    text.find('"refund": {')
]:

    marker = '''            "total_amount":
                _money(
                    order.total_amount
                ),

            "payment_method":
'''


    addition = '''            "total_amount":
                _money(
                    order.total_amount
                ),

            "currency_code":
                order.currency_code_at_checkout,

            "currency_symbol":
                order.currency_symbol_at_checkout,

            "tax_amount":
                _money(
                    order.tax_amount
                ),

            "tax_rate":
                _money(
                    order.tax_rate_at_checkout
                ),

            "payment_method":
'''


    if marker not in text:

        raise RuntimeError(
            "Could not locate credit note "
            "order snapshot total."
        )


    text = text.replace(
        marker,
        addition,
        1,
    )


CREDIT_SERVICE.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# 10. CREDIT NOTE EMAIL MUST ALWAYS USE CUSTOMER URL
# ============================================================

text = CREDIT_VIEWS.read_text(
    encoding="utf-8-sig"
)


if "def _customer_credit_note_url(" not in text:

    marker = '''def _credit_note_url(
    request,
    document,
):
'''


    helper = '''def _customer_credit_note_url(
    document,
):

    from django.urls import reverse


    return reverse(
        "customer_credit_note",
        args=[
            document.refund_request_id
        ],
    )



''' + marker


    if marker not in text:

        raise RuntimeError(
            "Could not locate _credit_note_url()."
        )


    text = text.replace(
        marker,
        helper,
        1,
    )


old = '''            _credit_note_url(
                request,
                document,
            )
'''


new = '''            _customer_credit_note_url(
                document,
            )
'''


# First occurrence is the URL embedded in email.
if old in text:

    text = text.replace(
        old,
        new,
        1,
    )


old = '''        f"Refund amount: KES "
        f"{snapshot['refund']['amount']}\\n"
'''


new = '''        f"Refund amount: "
        f"{snapshot['order'].get('currency_symbol', 'KSh')} "
        f"{snapshot['refund']['amount']}\\n"
'''


if old in text:

    text = text.replace(
        old,
        new,
        1,
    )


CREDIT_VIEWS.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# 11. CURRENCY CHANGE PROTECTION
# ============================================================

text = CORE_FORMS.read_text(
    encoding="utf-8-sig"
)


if "active_unpaid_orders" not in text:

    marker = '''    def clean_minimum_order_amount(
        self,
    ):
'''


    method = '''    def clean(
        self,
    ):

        cleaned_data = super().clean()


        if not getattr(
            self.instance,
            "pk",
            None,
        ):

            return cleaned_data


        new_code = (
            cleaned_data.get(
                "currency_code"
            )
            or self.instance.currency_code
        )

        new_symbol = (
            cleaned_data.get(
                "currency_symbol"
            )
            or self.instance.currency_symbol
        )


        old_code = (
            self.instance.currency_code
            or ""
        )

        old_symbol = (
            self.instance.currency_symbol
            or ""
        )


        currency_changed = (
            new_code != old_code
            or
            new_symbol != old_symbol
        )


        if currency_changed:

            from orders.models import Order


            active_unpaid_orders = (
                Order.objects
                .filter(
                    status__in=[
                        "pending",
                        "confirmed",
                        "processing",
                        "shipped",
                    ],
                    payment_status__in=[
                        "pending",
                        "failed",
                    ],
                )
                .exists()
            )


            if active_unpaid_orders:

                raise forms.ValidationError(
                    (
                        "Currency cannot be changed while "
                        "active unpaid orders exist. "
                        "Complete, cancel, or resolve those "
                        "orders first."
                    )
                )


        return cleaned_data



''' + marker


    if marker not in text:

        raise RuntimeError(
            "Could not locate StoreSettingsForm "
            "minimum order cleaner."
        )


    text = text.replace(
        marker,
        method,
        1,
    )


CORE_FORMS.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# 12. PHASE 12D TESTS
# ============================================================

TESTS.write_text(
r'''
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import (
    get_user_model,
)

from django.forms.models import (
    model_to_dict,
)

from django.test import (
    RequestFactory,
    TestCase,
)

from django.urls import reverse

from core.forms import (
    StoreSettingsForm,
)

from core.store_settings import (
    get_store_settings,
)

from dashboard.reports_views import (
    build_sales_report,
)

from orders.credit_note_views import (
    _customer_credit_note_url,
)

from orders.document_views import (
    customer_document_view_url,
)

from orders.models import (
    CreditNoteDocument,
    Order,
    OrderDocument,
)

from payments.models import (
    RefundRequest,
)


User = get_user_model()


class Phase12DFinancialReportTests(
    TestCase
):

    def setUp(self):

        self.user = (
            User.objects.create_user(
                username="phase12d-customer",
                password="pass12345",
                email="customer@example.com",
            )
        )


        self.staff = (
            User.objects.create_user(
                username="phase12d-admin",
                password="pass12345",
                email="admin@example.com",
                is_staff=True,
            )
        )


        self.factory = (
            RequestFactory()
        )


    def create_paid_order(
        self,
        *,
        number,
        subtotal,
        discount,
        tax,
        delivery,
        total,
        code="KES",
        symbol="KSh",
        tax_rate="16.00",
    ):

        return Order.objects.create(
            user=self.user,
            order_number=number,
            full_name="Phase 12D Customer",
            phone="0712345678",
            email="customer@example.com",
            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="1",
            subtotal=Decimal(
                subtotal
            ),
            discount=Decimal(
                discount
            ),
            tax_enabled_at_checkout=(
                Decimal(tax) > 0
            ),
            tax_rate_at_checkout=Decimal(
                tax_rate
            ),
            tax_amount=Decimal(
                tax
            ),
            shipping_cost=Decimal(
                delivery
            ),
            total_amount=Decimal(
                total
            ),
            currency_code_at_checkout=code,
            currency_symbol_at_checkout=symbol,
            payment_status="paid",
            status="confirmed",
        )


    def test_report_uses_historical_tax_snapshot(
        self,
    ):

        self.create_paid_order(
            number="P12D-001",
            subtotal="1000.00",
            discount="100.00",
            tax="144.00",
            delivery="200.00",
            total="1244.00",
        )


        request = (
            self.factory.get(
                "/dashboard/admin/reports/"
            )
        )


        report = build_sales_report(
            request
        )


        self.assertEqual(
            report[
                "merchandise_subtotal"
            ],
            Decimal("1000.00"),
        )


        self.assertEqual(
            report[
                "discounts_given"
            ],
            Decimal("100.00"),
        )


        self.assertEqual(
            report[
                "net_merchandise_before_tax"
            ],
            Decimal("900.00"),
        )


        self.assertEqual(
            report[
                "tax_collected"
            ],
            Decimal("144.00"),
        )


        self.assertEqual(
            report[
                "gross_revenue"
            ],
            Decimal("1244.00"),
        )


        self.assertEqual(
            report[
                "taxable_order_count"
            ],
            1,
        )


    def test_zero_tax_legacy_style_order_remains_valid(
        self,
    ):

        self.create_paid_order(
            number="P12D-002",
            subtotal="500.00",
            discount="0.00",
            tax="0.00",
            tax_rate="0.00",
            delivery="100.00",
            total="600.00",
        )


        request = (
            self.factory.get(
                "/dashboard/admin/reports/"
            )
        )


        report = build_sales_report(
            request
        )


        self.assertEqual(
            report[
                "tax_collected"
            ],
            Decimal("0.00"),
        )


        self.assertEqual(
            report[
                "non_taxable_order_count"
            ],
            1,
        )


    def test_mixed_currencies_are_detected(
        self,
    ):

        self.create_paid_order(
            number="P12D-KES",
            subtotal="1000.00",
            discount="0.00",
            tax="0.00",
            delivery="0.00",
            total="1000.00",
            code="KES",
            symbol="KSh",
            tax_rate="0.00",
        )


        self.create_paid_order(
            number="P12D-USD",
            subtotal="10.00",
            discount="0.00",
            tax="0.00",
            delivery="0.00",
            total="10.00",
            code="USD",
            symbol="$",
            tax_rate="0.00",
        )


        request = (
            self.factory.get(
                "/dashboard/admin/reports/"
            )
        )


        report = build_sales_report(
            request
        )


        self.assertTrue(
            report[
                "has_mixed_currencies"
            ]
        )


        self.assertEqual(
            report[
                "report_currency_label"
            ],
            "MIXED",
        )


        self.assertEqual(
            len(
                report[
                    "currency_breakdown"
                ]
            ),
            2,
        )


    def test_csv_contains_historical_tax_fields(
        self,
    ):

        self.create_paid_order(
            number="P12D-CSV",
            subtotal="2000.00",
            discount="100.00",
            tax="304.00",
            delivery="200.00",
            total="2404.00",
            code="KES",
            symbol="KSh",
        )


        self.client.force_login(
            self.staff
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


        content = (
            response.content.decode(
                "utf-8"
            )
        )


        self.assertIn(
            "Order Financial Detail",
            content,
        )

        self.assertIn(
            "Tax Rate %",
            content,
        )

        self.assertIn(
            "Tax Amount",
            content,
        )

        self.assertIn(
            "P12D-CSV",
            content,
        )

        self.assertIn(
            "304.00",
            content,
        )


class Phase12DDocumentURLTests(
    TestCase
):

    def setUp(self):

        self.user = (
            User.objects.create_user(
                username="phase12d-doc",
                password="pass12345",
            )
        )


        self.order = (
            Order.objects.create(
                user=self.user,
                order_number="P12D-DOC",
                full_name="Document Customer",
                phone="0712345678",
                email="customer@example.com",
                county="Nairobi",
                city="Nairobi",
                estate="CBD",
                house_number="1",
                subtotal=Decimal("1000.00"),
                total_amount=Decimal("1000.00"),
            )
        )


    def test_invoice_email_helper_is_customer_route(
        self,
    ):

        document = OrderDocument(
            order=self.order,
            document_type="invoice",
        )


        self.assertEqual(
            customer_document_view_url(
                document
            ),
            reverse(
                "customer_order_invoice",
                args=[
                    self.order.order_number
                ],
            ),
        )


    def test_receipt_email_helper_is_customer_route(
        self,
    ):

        document = OrderDocument(
            order=self.order,
            document_type="receipt",
        )


        self.assertEqual(
            customer_document_view_url(
                document
            ),
            reverse(
                "customer_order_receipt",
                args=[
                    self.order.order_number
                ],
            ),
        )


    def test_credit_note_email_helper_is_customer_route(
        self,
    ):

        refund = (
            RefundRequest.objects.create(
                order=self.order,
                amount=Decimal("100.00"),
                reason="Phase 12D",
            )
        )


        document = CreditNoteDocument(
            order=self.order,
            refund_request=refund,
        )


        self.assertEqual(
            _customer_credit_note_url(
                document
            ),
            reverse(
                "customer_credit_note",
                args=[
                    refund.pk
                ],
            ),
        )


class Phase12DCurrencySafetyTests(
    TestCase
):

    def setUp(self):

        self.user = (
            User.objects.create_user(
                username="phase12d-money",
                password="pass12345",
            )
        )


        self.store = (
            get_store_settings()
        )


    def _form_data(self):

        data = model_to_dict(
            self.store,
            fields=(
                StoreSettingsForm
                .Meta
                .fields
            ),
        )


        # ModelForm accepts normal Python values,
        # but ensure optional fields do not become None.
        for field_name in (
            "legal_name",
            "business_registration_number",
            "tax_pin",
            "support_email",
            "support_phone",
            "whatsapp_number",
            "website_url",
            "address",
            "city",
            "county",
            "checkout_closed_message",
            "document_footer",
        ):

            if data.get(
                field_name
            ) is None:

                data[
                    field_name
                ] = ""


        return data


    def test_currency_change_blocked_with_active_unpaid_order(
        self,
    ):

        Order.objects.create(
            user=self.user,
            order_number="P12D-UNPAID",
            full_name="Pending Customer",
            phone="0712345678",
            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="1",
            subtotal=Decimal("500.00"),
            total_amount=Decimal("500.00"),
            status="pending",
            payment_status="pending",
        )


        data = self._form_data()

        data[
            "currency_code"
        ] = "USD"

        data[
            "currency_symbol"
        ] = "$"


        form = StoreSettingsForm(
            data=data,
            instance=self.store,
        )


        self.assertFalse(
            form.is_valid()
        )


        self.assertIn(
            "Currency cannot be changed",
            str(
                form.non_field_errors()
            ),
        )


    def test_currency_change_allowed_without_active_unpaid_orders(
        self,
    ):

        data = self._form_data()

        data[
            "currency_code"
        ] = "USD"

        data[
            "currency_symbol"
        ] = "$"


        form = StoreSettingsForm(
            data=data,
            instance=self.store,
        )


        self.assertTrue(
            form.is_valid(),
            form.errors,
        )
'''.strip() + "\n",
encoding="utf-8",
)


print()
print("=" * 72)
print("PHASE 12D INSTALLED")
print("=" * 72)
print()
print("Added:")
print("  Historical merchandise subtotal reporting")
print("  Historical discount reporting")
print("  Historical tax collected reporting")
print("  Taxable/non-taxable paid-order counts")
print("  Daily tax reporting")
print("  Currency-by-currency financial reporting")
print("  Mixed-currency warning")
print("  Detailed financial CSV export")
print("  Profit calculation excludes collected tax")
print("  Active-unpaid-order currency change protection")
print("  Invoice email customer URL hardening")
print("  Receipt email customer URL hardening")
print("  Credit-note email customer URL hardening")
print("  Historical credit-note currency snapshot")
print()
print("No migration required.")
