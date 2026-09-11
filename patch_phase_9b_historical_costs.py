from pathlib import Path
import shutil


ROOT = Path.cwd()

ORDER_MODELS = (
    ROOT
    / "orders"
    / "models.py"
)

ORDER_VIEWS = (
    ROOT
    / "orders"
    / "views.py"
)

REPORT_VIEWS = (
    ROOT
    / "dashboard"
    / "reports_views.py"
)

REPORT_TEMPLATE = (
    ROOT
    / "templates"
    / "dashboard"
    / "admin"
    / "reports"
    / "sales.html"
)

TEST_FILE = (
    ROOT
    / "dashboard"
    / "test_phase9b.py"
)


# ============================================================
# BACKUPS
# ============================================================

for path in [
    ORDER_MODELS,
    ORDER_VIEWS,
    REPORT_VIEWS,
    REPORT_TEMPLATE,
]:

    if not path.exists():
        raise RuntimeError(
            f"Required file missing: {path}"
        )

    backup = Path(
        str(path)
        + ".phase9bbackup"
    )

    if not backup.exists():

        shutil.copy2(
            path,
            backup,
        )


# ============================================================
# 1. ORDER ITEM HISTORICAL COST FIELDS
# ============================================================

text = ORDER_MODELS.read_text(
    encoding="utf-8-sig"
)


if "unit_cost_at_sale" not in text:

    old = '''    price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
'''

    new = '''    price = models.DecimalField(max_digits=12, decimal_places=2)

    # Historical accounting snapshot.
    #
    # These values are captured when the order is created.
    # They must NOT change when Product.cost_price changes later.
    unit_cost_at_sale = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    cost_subtotal_at_sale = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    quantity = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
'''

    if old not in text:

        raise RuntimeError(
            "Could not locate OrderItem price/"
            "quantity/subtotal fields."
        )

    text = text.replace(
        old,
        new,
        1,
    )


ORDER_MODELS.write_text(
    text,
    encoding="utf-8",
)

print(
    "OrderItem historical cost fields added."
)


# ============================================================
# 2. CAPTURE COST DURING CHECKOUT
# ============================================================

text = ORDER_VIEWS.read_text(
    encoding="utf-8-sig"
)


if "unit_cost_at_sale=unit_cost_at_sale" not in text:

    old = '''                for item in items:
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        variant=item.variant,
                        product_name=item.product.name,
                        variant_name=item.variant.name if item.variant else "",
                        price=item.variant.current_price if item.variant else item.product.current_price,
                        quantity=item.quantity,
                        subtotal=item.subtotal,
                    )
'''

    new = '''                for item in items:

                    # -----------------------------------------
                    # HISTORICAL COST SNAPSHOT
                    # -----------------------------------------

                    if (
                        item.variant
                        and getattr(
                            item.variant,
                            "cost_price",
                            None,
                        )
                        is not None
                    ):

                        unit_cost_at_sale = (
                            item.variant.cost_price
                        )

                    else:

                        unit_cost_at_sale = (
                            getattr(
                                item.product,
                                "cost_price",
                                None,
                            )
                        )


                    cost_subtotal_at_sale = None

                    if (
                        unit_cost_at_sale
                        is not None
                    ):

                        cost_subtotal_at_sale = (
                            unit_cost_at_sale
                            * item.quantity
                        )


                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        variant=item.variant,
                        product_name=item.product.name,
                        variant_name=item.variant.name if item.variant else "",
                        price=item.variant.current_price if item.variant else item.product.current_price,

                        unit_cost_at_sale=(
                            unit_cost_at_sale
                        ),

                        cost_subtotal_at_sale=(
                            cost_subtotal_at_sale
                        ),

                        quantity=item.quantity,
                        subtotal=item.subtotal,
                    )
'''

    if old not in text:

        raise RuntimeError(
            "Could not locate checkout "
            "OrderItem.objects.create() block."
        )

    text = text.replace(
        old,
        new,
        1,
    )


ORDER_VIEWS.write_text(
    text,
    encoding="utf-8",
)

print(
    "Checkout now snapshots product cost."
)


# ============================================================
# 3. REPORTS USE SNAPSHOT FIRST
# ============================================================

text = REPORT_VIEWS.read_text(
    encoding="utf-8-sig"
)


old = '''    estimated_cogs = ZERO


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
'''


new = '''    historical_cogs = ZERO

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


    estimated_gross_profit = (
        net_revenue
        - estimated_cogs
        - actual_delivery_cost
    )
'''


if old not in text:

    if "historical_cogs = ZERO" not in text:

        raise RuntimeError(
            "Could not locate Phase 9A "
            "COGS calculation."
        )

else:

    text = text.replace(
        old,
        new,
        1,
    )


# ------------------------------------------------------------
# Add values to context
# ------------------------------------------------------------

if '"historical_cogs":' not in text:

    marker = '''        "estimated_cogs": (
            estimated_cogs
        ),
'''

    replacement = '''        "estimated_cogs": (
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
'''

    if marker not in text:

        raise RuntimeError(
            "Could not locate estimated_cogs "
            "context entry."
        )

    text = text.replace(
        marker,
        replacement,
        1,
    )


REPORT_VIEWS.write_text(
    text,
    encoding="utf-8",
)

print(
    "Reports now prefer historical cost snapshots."
)


# ============================================================
# 4. REPORT UI ACCOUNTING QUALITY
# ============================================================

text = REPORT_TEMPLATE.read_text(
    encoding="utf-8-sig"
)


old = '''            <small class="text-muted">
                Uses current product cost prices.
            </small>
'''


new = '''            <small class="text-muted">

                {% if legacy_cost_items %}

                    Includes
                    {{ legacy_cost_items }}
                    legacy item{{ legacy_cost_items|pluralize }}
                    using estimated historical cost.

                {% else %}

                    Uses sale-time cost snapshots.

                {% endif %}

            </small>
'''


if old in text:

    text = text.replace(
        old,
        new,
        1,
    )


# Add accounting quality section before daily sales.

if "Accounting Data Quality" not in text:

    marker = '''<!-- ===================================================== -->
<!-- DAILY SALES -->
<!-- ===================================================== -->
'''

    block = '''
<!-- ===================================================== -->
<!-- ACCOUNTING DATA QUALITY -->
<!-- ===================================================== -->

<div class="dashboard-card mb-4">

    <div class="d-flex justify-content-between align-items-start flex-wrap gap-3">

        <div>

            <h2 class="h5 mb-1">
                Accounting Data Quality
            </h2>

            <p class="text-muted mb-0">
                Historical cost coverage for orders
                in the selected period.
            </p>

        </div>

    </div>


    <div class="row g-3 mt-2">


        <div class="col-md-3">

            <div class="border rounded p-3 h-100">

                <small class="text-muted">
                    Snapshot Items
                </small>

                <div class="fs-4 fw-bold">
                    {{ historical_cost_items }}
                </div>

            </div>

        </div>


        <div class="col-md-3">

            <div class="border rounded p-3 h-100">

                <small class="text-muted">
                    Legacy Items
                </small>

                <div class="fs-4 fw-bold">
                    {{ legacy_cost_items }}
                </div>

            </div>

        </div>


        <div class="col-md-3">

            <div class="border rounded p-3 h-100">

                <small class="text-muted">
                    Historical COGS
                </small>

                <div class="fs-5 fw-bold">
                    KES {{ historical_cogs|floatformat:2 }}
                </div>

            </div>

        </div>


        <div class="col-md-3">

            <div class="border rounded p-3 h-100">

                <small class="text-muted">
                    Legacy Estimated COGS
                </small>

                <div class="fs-5 fw-bold">
                    KES {{ legacy_estimated_cogs|floatformat:2 }}
                </div>

            </div>

        </div>


    </div>


    {% if legacy_cost_items %}

        <div
            class="
                alert
                alert-warning
                mt-3
                mb-0
            "
        >

            <strong>
                Legacy accounting data:
            </strong>

            Some older order items were created before
            historical cost snapshots existed.

            Their cost is estimated using the current
            product cost and may not equal the original
            purchase cost.

        </div>

    {% else %}

        <div
            class="
                alert
                alert-success
                mt-3
                mb-0
            "
        >

            All items in this report contain
            sale-time cost snapshots.

        </div>

    {% endif %}

</div>


'''

    if marker not in text:

        raise RuntimeError(
            "Could not locate Daily Sales section."
        )

    text = text.replace(
        marker,
        block + marker,
        1,
    )


REPORT_TEMPLATE.write_text(
    text,
    encoding="utf-8",
)

print(
    "Accounting data-quality UI added."
)


# ============================================================
# 5. PHASE 9B TESTS
# ============================================================

TEST_FILE.write_text(
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

from products.models import Product


User = get_user_model()


class Phase9BHistoricalCostTests(
    TestCase
):

    def setUp(self):

        self.staff = (
            User.objects.create_user(
                username="phase9bstaff",
                password="pass12345",
                role=User.ADMIN,
                is_staff=True,
            )
        )

        self.customer = (
            User.objects.create_user(
                username="phase9bcustomer",
                password="pass12345",
                role=User.CUSTOMER,
            )
        )

        self.category = (
            Category.objects.create(
                name="Phase 9B",
                slug="phase-9b",
            )
        )

        self.product = (
            Product.objects.create(
                category=self.category,
                name="Accounting Laptop",
                slug="accounting-laptop",
                sku="P9B-001",
                price=Decimal("35000.00"),
                cost_price=Decimal("27000.00"),
                stock=20,
                reserved_stock=0,
                is_active=True,
            )
        )

        self.order = (
            Order.objects.create(
                user=self.customer,
                order_number="PHASE9B-001",
                full_name="Accounting Customer",
                phone="0712345678",
                email="phase9b@example.com",
                county="Nairobi",
                city="Nairobi",
                estate="CBD",
                house_number="1",
                subtotal=Decimal("35000.00"),
                shipping_cost=Decimal("0.00"),
                discount=Decimal("0.00"),
                total_amount=Decimal("35000.00"),
                status="delivered",
                payment_status="paid",
                inventory_status="consumed",
            )
        )


    def test_historical_cost_does_not_change_with_product(
        self
    ):

        item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=self.product.name,
            price=Decimal("35000.00"),
            unit_cost_at_sale=Decimal("27000.00"),
            cost_subtotal_at_sale=Decimal("27000.00"),
            quantity=1,
            subtotal=Decimal("35000.00"),
        )


        self.product.cost_price = Decimal(
            "31000.00"
        )

        self.product.save(
            update_fields=[
                "cost_price",
            ]
        )


        item.refresh_from_db()


        self.assertEqual(
            item.unit_cost_at_sale,
            Decimal("27000.00"),
        )

        self.assertEqual(
            item.cost_subtotal_at_sale,
            Decimal("27000.00"),
        )


    def test_reports_use_snapshot_not_current_cost(
        self
    ):

        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=self.product.name,
            price=Decimal("35000.00"),
            unit_cost_at_sale=Decimal("27000.00"),
            cost_subtotal_at_sale=Decimal("27000.00"),
            quantity=1,
            subtotal=Decimal("35000.00"),
        )


        self.product.cost_price = Decimal(
            "33000.00"
        )

        self.product.save(
            update_fields=[
                "cost_price",
            ]
        )


        self.client.login(
            username="phase9bstaff",
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
                "historical_cogs"
            ],
            Decimal("27000.00"),
        )


        self.assertEqual(
            response.context[
                "legacy_estimated_cogs"
            ],
            Decimal("0.00"),
        )


    def test_legacy_order_is_identified_as_estimate(
        self
    ):

        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=self.product.name,
            price=Decimal("35000.00"),
            quantity=1,
            subtotal=Decimal("35000.00"),
        )


        self.client.login(
            username="phase9bstaff",
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
                "legacy_cost_items"
            ],
            1,
        )


        self.assertEqual(
            response.context[
                "historical_cost_items"
            ],
            0,
        )


        self.assertEqual(
            response.context[
                "legacy_estimated_cogs"
            ],
            Decimal("27000.00"),
        )


    def test_snapshot_handles_multiple_quantity(
        self
    ):

        item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=self.product.name,
            price=Decimal("35000.00"),
            unit_cost_at_sale=Decimal("27000.00"),
            cost_subtotal_at_sale=Decimal("54000.00"),
            quantity=2,
            subtotal=Decimal("70000.00"),
        )


        self.assertEqual(
            item.cost_subtotal_at_sale,
            Decimal("54000.00"),
        )
'''.strip() + "\n",
encoding="utf-8",
)


print(
    "Phase 9B regression tests created."
)


print()
print("=" * 72)
print("PHASE 9B HISTORICAL COST SNAPSHOTS INSTALLED")
print("=" * 72)
print()
print("New sales:")
print("  Selling price snapshot")
print("  Unit cost snapshot")
print("  Total cost snapshot")
print()
print("Old sales:")
print("  Remain legacy")
print("  Reports clearly mark their cost as estimated")
