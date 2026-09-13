from pathlib import Path
import shutil


ROOT = Path.cwd()

MODELS = ROOT / "orders" / "models.py"
VIEWS = ROOT / "orders" / "views.py"
PRICING = ROOT / "orders" / "pricing.py"

DELIVERY_VIEWS = (
    ROOT
    / "delivery"
    / "views.py"
)

CHECKOUT_TEMPLATE = (
    ROOT
    / "templates"
    / "orders"
    / "checkout.html"
)

CONFIRMATION_TEMPLATE = (
    ROOT
    / "templates"
    / "orders"
    / "order_confirmation.html"
)

DOCUMENT_SERVICE = (
    ROOT
    / "orders"
    / "document_service.py"
)

INVOICE_TEMPLATE = (
    ROOT
    / "templates"
    / "orders"
    / "documents"
    / "invoice.html"
)

RECEIPT_TEMPLATE = (
    ROOT
    / "templates"
    / "orders"
    / "documents"
    / "receipt.html"
)

TESTS = (
    ROOT
    / "orders"
    / "test_phase12b.py"
)


required = [
    MODELS,
    VIEWS,
    DELIVERY_VIEWS,
    CHECKOUT_TEMPLATE,
    CONFIRMATION_TEMPLATE,
    DOCUMENT_SERVICE,
    INVOICE_TEMPLATE,
    RECEIPT_TEMPLATE,
]


for path in required:

    if not path.exists():

        raise RuntimeError(
            f"Missing required file: {path}"
        )


for path in required:

    backup = Path(
        str(path)
        + ".phase12bbackup"
    )

    if not backup.exists():

        shutil.copy2(
            path,
            backup,
        )


# ============================================================
# 1. CENTRAL ORDER PRICING SERVICE
# ============================================================

PRICING.write_text(
r'''
from decimal import (
    Decimal,
    ROUND_HALF_UP,
)


ZERO = Decimal("0.00")
HUNDRED = Decimal("100")
MONEY = Decimal("0.01")


def money(
    value,
):

    return Decimal(
        value or ZERO
    ).quantize(
        MONEY,
        rounding=ROUND_HALF_UP,
    )


def calculate_order_pricing(
    *,
    subtotal,
    shipping_cost=ZERO,
    discount=ZERO,
    tax_enabled=False,
    tax_rate=ZERO,
):

    subtotal = money(
        subtotal
    )

    shipping_cost = money(
        shipping_cost
    )

    discount = money(
        discount
    )

    tax_rate = Decimal(
        tax_rate or ZERO
    )


    # Never allow a discount to produce
    # a negative taxable merchandise value.
    taxable_amount = (
        subtotal
        - discount
    )


    if taxable_amount < ZERO:

        taxable_amount = ZERO


    tax_amount = ZERO


    if (
        tax_enabled
        and tax_rate > ZERO
    ):

        tax_amount = money(
            taxable_amount
            * tax_rate
            / HUNDRED
        )


    total_amount = money(
        taxable_amount
        + tax_amount
        + shipping_cost
    )


    return {

        "subtotal":
            subtotal,

        "discount":
            discount,

        "taxable_amount":
            taxable_amount,

        "tax_rate":
            tax_rate,

        "tax_amount":
            tax_amount,

        "shipping_cost":
            shipping_cost,

        "total_amount":
            total_amount,
    }


def minimum_order_satisfied(
    *,
    subtotal,
    minimum_order_amount,
):

    return (
        money(
            subtotal
        )
        >=
        money(
            minimum_order_amount
        )
    )


def total_from_order_snapshot(
    order,
    *,
    shipping_cost=None,
):

    """
    Recalculate total using historical order
    financial values.

    Important:
    Never read the current StoreSettings tax
    rate here. The order's tax_amount is already
    its historical tax snapshot.
    """

    if shipping_cost is None:

        shipping_cost = (
            order.shipping_cost
        )


    taxable_amount = (
        money(
            order.subtotal
        )
        -
        money(
            order.discount
        )
    )


    if taxable_amount < ZERO:

        taxable_amount = ZERO


    return money(
        taxable_amount
        + money(
            order.tax_amount
        )
        + money(
            shipping_cost
        )
    )
'''.strip() + "\n",
encoding="utf-8",
)

print(
    "Central order pricing service created."
)


# ============================================================
# 2. ORDER HISTORICAL FINANCIAL SNAPSHOTS
# ============================================================

text = MODELS.read_text(
    encoding="utf-8-sig"
)


if (
    "tax_rate_at_checkout"
    not in text
):

    marker = '''    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
'''


    addition = marker + '''

    # ---------------------------------------------------------
    # HISTORICAL CHECKOUT FINANCIAL SNAPSHOT
    # ---------------------------------------------------------

    tax_enabled_at_checkout = models.BooleanField(
        default=False,
    )

    tax_rate_at_checkout = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    minimum_order_amount_at_checkout = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    currency_code_at_checkout = models.CharField(
        max_length=10,
        default="KES",
    )

    currency_symbol_at_checkout = models.CharField(
        max_length=10,
        default="KSh",
    )
'''


    if marker not in text:

        raise RuntimeError(
            "Could not locate Order.discount field."
        )


    text = text.replace(
        marker,
        addition,
        1,
    )


MODELS.write_text(
    text,
    encoding="utf-8",
)

print(
    "Historical order tax/currency fields added."
)


# ============================================================
# 3. CHECKOUT IMPORTS
# ============================================================

text = VIEWS.read_text(
    encoding="utf-8-sig"
)


if (
    "from core.models import StoreSettings"
    not in text
):

    marker = '''from delivery.models import Delivery, DeliveryZone
'''


    replacement = marker + '''

from core.models import StoreSettings

from core.store_settings import (
    get_store_settings,
)

from .pricing import (
    calculate_order_pricing,
    minimum_order_satisfied,
)
'''


    if marker not in text:

        raise RuntimeError(
            "Could not locate delivery imports "
            "inside orders/views.py."
        )


    text = text.replace(
        marker,
        replacement,
        1,
    )


# ============================================================
# 4. PRE-CHECKOUT STORE CONTROLS
# ============================================================

marker = '''    if not items.exists():
        return redirect("cart")

    addresses = Address.objects.filter(user=request.user)
'''


replacement = '''    if not items.exists():
        return redirect("cart")


    # ---------------------------------------------------------
    # STORE-WIDE CHECKOUT CONTROLS
    # ---------------------------------------------------------

    store_settings = (
        get_store_settings()
    )

    checkout_subtotal = (
        cart.total_price
    )


    if not store_settings.orders_enabled:

        messages.error(
            request,
            (
                "Online ordering is temporarily "
                "unavailable."
            ),
        )

        return redirect(
            "cart"
        )


    if not minimum_order_satisfied(
        subtotal=checkout_subtotal,
        minimum_order_amount=(
            store_settings
            .minimum_order_amount
        ),
    ):

        messages.error(
            request,
            (
                "The minimum order amount is "
                f"{store_settings.currency_symbol} "
                f"{store_settings.minimum_order_amount:.2f}."
            ),
        )

        return redirect(
            "cart"
        )


    addresses = Address.objects.filter(user=request.user)
'''


if marker not in text:

    raise RuntimeError(
        "Could not locate checkout cart validation."
    )


text = text.replace(
    marker,
    replacement,
    1,
)


# ============================================================
# 5. LOCK STORE SETTINGS DURING ORDER CREATION
# ============================================================

marker = '''            with transaction.atomic():

                delivery_zone = (
'''


replacement = '''            with transaction.atomic():

                # Store configuration can change while a
                # customer is on the checkout page.
                #
                # Re-read it under a database lock so the
                # order gets one internally consistent
                # financial snapshot.
                get_store_settings()

                store_settings = (
                    StoreSettings.objects
                    .select_for_update()
                    .get(
                        pk=StoreSettings.SINGLETON_PK
                    )
                )


                subtotal = (
                    cart.total_price
                )


                if not store_settings.orders_enabled:

                    messages.error(
                        request,
                        (
                            "Online ordering was disabled "
                            "before this order could be completed."
                        ),
                    )

                    return redirect(
                        "cart"
                    )


                if not minimum_order_satisfied(
                    subtotal=subtotal,
                    minimum_order_amount=(
                        store_settings
                        .minimum_order_amount
                    ),
                ):

                    messages.error(
                        request,
                        (
                            "Your cart no longer meets "
                            "the minimum order amount."
                        ),
                    )

                    return redirect(
                        "cart"
                    )


                delivery_zone = (
'''


if marker not in text:

    raise RuntimeError(
        "Could not locate checkout transaction."
    )


text = text.replace(
    marker,
    replacement,
    1,
)


# Remove the old duplicate subtotal assignment
text = text.replace(
    '''                subtotal = cart.total_price

                if (
                    delivery_zone.pricing_mode
''',
    '''                if (
                    delivery_zone.pricing_mode
''',
    1,
)


# ============================================================
# 6. REPLACE OLD TOTAL CALCULATION WITH TAX ENGINE
# ============================================================

old = '''                total_amount = subtotal + shipping_cost - discount

                order = Order.objects.create(
'''


new = '''                pricing = (
                    calculate_order_pricing(
                        subtotal=subtotal,
                        shipping_cost=shipping_cost,
                        discount=discount,
                        tax_enabled=(
                            store_settings.tax_enabled
                        ),
                        tax_rate=(
                            store_settings.tax_rate
                        ),
                    )
                )


                tax_amount = (
                    pricing[
                        "tax_amount"
                    ]
                )

                total_amount = (
                    pricing[
                        "total_amount"
                    ]
                )


                order = Order.objects.create(
'''


if old not in text:

    raise RuntimeError(
        "Could not locate old checkout total formula."
    )


text = text.replace(
    old,
    new,
    1,
)


# ============================================================
# 7. SAVE HISTORICAL SNAPSHOT ON ORDER
# ============================================================

marker = '''                    discount=discount,
                    coupon=coupon_obj,
                    total_amount=total_amount,

                    inventory_status="reserved",
'''


replacement = '''                    discount=discount,

                    tax_enabled_at_checkout=(
                        store_settings.tax_enabled
                    ),

                    tax_rate_at_checkout=(
                        store_settings.tax_rate
                        if store_settings.tax_enabled
                        else Decimal("0.00")
                    ),

                    tax_amount=tax_amount,

                    minimum_order_amount_at_checkout=(
                        store_settings
                        .minimum_order_amount
                    ),

                    currency_code_at_checkout=(
                        store_settings
                        .currency_code
                    ),

                    currency_symbol_at_checkout=(
                        store_settings
                        .currency_symbol
                    ),

                    coupon=coupon_obj,
                    total_amount=total_amount,

                    inventory_status="reserved",
'''


if marker not in text:

    raise RuntimeError(
        "Could not locate Order.objects.create "
        "financial fields."
    )


text = text.replace(
    marker,
    replacement,
    1,
)


# ============================================================
# 8. PASS SETTINGS TO CHECKOUT TEMPLATE
# ============================================================

text = text.replace(
    '''                            "stock_error": stock_error,
                        },
''',
    '''                            "stock_error": stock_error,
                            "store_settings": store_settings,
                        },
''',
    1,
)


marker = '''            "form": form,
            "stock_error": stock_error,
        },
'''


replacement = '''            "form": form,
            "stock_error": stock_error,
            "store_settings": store_settings,
        },
'''


if marker not in text:

    raise RuntimeError(
        "Could not locate final checkout template context."
    )


text = text.replace(
    marker,
    replacement,
    1,
)


VIEWS.write_text(
    text,
    encoding="utf-8",
)

print(
    "Checkout settings enforcement and tax "
    "calculation installed."
)


# ============================================================
# 9. DELIVERY QUOTE MUST PRESERVE TAX
# ============================================================

text = DELIVERY_VIEWS.read_text(
    encoding="utf-8-sig"
)


if (
    "total_from_order_snapshot"
    not in text
):

    # Put import near existing order/delivery imports.
    insert_at = text.find(
        "\n\n",
        text.find(
            "from orders"
        )
    )

    if insert_at == -1:

        # Fall back to beginning after decimal imports.
        marker = '''from decimal import Decimal
'''

        replacement = marker + '''

from orders.pricing import (
    total_from_order_snapshot,
)
'''

        if marker not in text:

            raise RuntimeError(
                "Could not place pricing import "
                "inside delivery/views.py."
            )

        text = text.replace(
            marker,
            replacement,
            1,
        )

    else:

        # Avoid disrupting multiline imports.
        marker = '''from decimal import Decimal
'''

        replacement = marker + '''

from orders.pricing import (
    total_from_order_snapshot,
)
'''

        if marker in text:

            text = text.replace(
                marker,
                replacement,
                1,
            )

        else:

            raise RuntimeError(
                "Could not place delivery pricing import."
            )


old = '''    order.total_amount = (
        order.subtotal
        + amount
        - order.discount
    )
'''


new = '''    # Preserve the tax captured when the order
    # was originally created.
    #
    # Never use the current StoreSettings tax rate here.
    order.total_amount = (
        total_from_order_snapshot(
            order,
            shipping_cost=amount,
        )
    )
'''


if old not in text:

    raise RuntimeError(
        "Could not locate delivery quote total formula."
    )


text = text.replace(
    old,
    new,
    1,
)


DELIVERY_VIEWS.write_text(
    text,
    encoding="utf-8",
)

print(
    "Delivery quote totals now preserve tax snapshots."
)


# ============================================================
# 10. DOCUMENT SNAPSHOT
# ============================================================

text = DOCUMENT_SERVICE.read_text(
    encoding="utf-8-sig"
)


marker = '''            "discount":
                _money_string(
                    order.discount
                ),

            "total_amount":
'''


replacement = '''            "discount":
                _money_string(
                    order.discount
                ),

            "tax_enabled":
                order.tax_enabled_at_checkout,

            "tax_rate":
                _money_string(
                    order.tax_rate_at_checkout
                ),

            "tax_amount":
                _money_string(
                    order.tax_amount
                ),

            "currency_code":
                order.currency_code_at_checkout,

            "currency_symbol":
                order.currency_symbol_at_checkout,

            "total_amount":
'''


if marker not in text:

    raise RuntimeError(
        "Could not locate order document "
        "discount snapshot."
    )


text = text.replace(
    marker,
    replacement,
    1,
)


DOCUMENT_SERVICE.write_text(
    text,
    encoding="utf-8",
)

print(
    "Invoice/receipt tax snapshots added."
)


# ============================================================
# 11. CHECKOUT TAX UI
# ============================================================

text = CHECKOUT_TEMPLATE.read_text(
    encoding="utf-8-sig"
)


# Add tax row before delivery.
if 'id="tax-row"' not in text:

    marker = '''                    <div class="d-flex justify-content-between mt-2">
                        <span>Delivery</span>
'''


    addition = '''                    {% if store_settings.tax_enabled %}

                    <div
                        class="d-flex justify-content-between mt-2"
                        id="tax-row"
                    >
                        <span>
                            Tax
                            ({{ store_settings.tax_rate }}%)
                        </span>

                        <strong>
                            {{ store_settings.currency_symbol }}
                            <span id="tax-amount">
                                0.00
                            </span>
                        </strong>
                    </div>

                    {% endif %}


                    <div class="d-flex justify-content-between mt-2">
                        <span>Delivery</span>
'''


    if marker not in text:

        raise RuntimeError(
            "Could not locate checkout delivery row."
        )


    text = text.replace(
        marker,
        addition,
        1,
    )


# Add minimum order information.
if "Minimum order:" not in text:

    marker = '''                    <h4 class="mb-4">Order Summary</h4>
'''


    addition = marker + '''

                    {% if store_settings.minimum_order_amount > 0 %}

                    <div class="alert alert-light border small">

                        Minimum order:
                        <strong>
                            {{ store_settings.currency_symbol }}
                            {{ store_settings.minimum_order_amount }}
                        </strong>

                    </div>

                    {% endif %}
'''


    text = text.replace(
        marker,
        addition,
        1,
    )


# JS: add tax variables.
marker = '''    const subtotal = {{ cart.total_price|default:0 }};

    let currentFee = 0;
'''


replacement = '''    const subtotal = {{ cart.total_price|default:0 }};

    const taxEnabled = (
        "{{ store_settings.tax_enabled|yesno:'true,false' }}"
        === "true"
    );

    const taxRate = parseFloat(
        "{{ store_settings.tax_rate|default:'0' }}"
    ) || 0;

    const taxAmountEl = (
        document.getElementById(
            "tax-amount"
        )
    );

    let currentFee = 0;
'''


if marker not in text:

    raise RuntimeError(
        "Could not locate checkout JS subtotal."
    )


text = text.replace(
    marker,
    replacement,
    1,
)


old = '''    function recalcTotal() {
        const total = subtotal + currentFee - currentDiscount;
        totalEl.textContent = total.toFixed(2);
    }
'''


new = '''    function recalcTotal() {

        const taxableAmount = Math.max(
            subtotal - currentDiscount,
            0
        );

        const taxAmount = (
            taxEnabled
            ? (
                taxableAmount
                * taxRate
                / 100
            )
            : 0
        );

        if (taxAmountEl) {

            taxAmountEl.textContent = (
                taxAmount.toFixed(2)
            );
        }

        const total = (
            taxableAmount
            + taxAmount
            + currentFee
        );

        totalEl.textContent = (
            total.toFixed(2)
        );
    }
'''


if old not in text:

    raise RuntimeError(
        "Could not locate checkout recalcTotal()."
    )


text = text.replace(
    old,
    new,
    1,
)


# Run initial tax calculation when page opens.
marker = '''    const detectBtn = document.getElementById("detect-location-btn");
'''


replacement = '''    recalcTotal();


    const detectBtn = document.getElementById("detect-location-btn");
'''


if marker not in text:

    raise RuntimeError(
        "Could not locate checkout geolocation JS."
    )


text = text.replace(
    marker,
    replacement,
    1,
)


CHECKOUT_TEMPLATE.write_text(
    text,
    encoding="utf-8",
)

print(
    "Checkout tax/minimum-order UI added."
)


# ============================================================
# 12. ORDER CONFIRMATION TAX DISPLAY
# ============================================================

text = CONFIRMATION_TEMPLATE.read_text(
    encoding="utf-8-sig"
)


if "order.tax_amount" not in text:

    marker = '''                        <div class="d-flex justify-content-between mb-2">

                            <span>
                                Delivery Fee
                            </span>
'''


    addition = '''                        {% if order.tax_amount %}

                        <div class="d-flex justify-content-between mb-2">

                            <span>
                                Tax
                                ({{ order.tax_rate_at_checkout }}%)
                            </span>

                            <span>
                                {{ order.currency_symbol_at_checkout }}
                                {{ order.tax_amount }}
                            </span>

                        </div>

                        {% endif %}


                        <div class="d-flex justify-content-between mb-2">

                            <span>
                                Delivery Fee
                            </span>
'''


    if marker not in text:

        raise RuntimeError(
            "Could not locate confirmation delivery row."
        )


    text = text.replace(
        marker,
        addition,
        1,
    )


# Replace confirmation total currency.
text = text.replace(
    '''<span>KES {{ order.total_amount }}</span>''',
    '''<span>{{ order.currency_symbol_at_checkout }} {{ order.total_amount }}</span>''',
)


CONFIRMATION_TEMPLATE.write_text(
    text,
    encoding="utf-8",
)

print(
    "Order confirmation tax display added."
)


# ============================================================
# 13. INVOICE TAX DISPLAY
# ============================================================

text = INVOICE_TEMPLATE.read_text(
    encoding="utf-8-sig"
)


if "snapshot.order.tax_amount" not in text:

    marker = '''    <div class="total-row">

        <span>Delivery</span>
'''


    addition = '''    {% if snapshot.order.tax_amount and snapshot.order.tax_amount != "0.00" %}

    <div class="total-row">

        <span>
            Tax
            ({{ snapshot.order.tax_rate }}%)
        </span>

        <strong>
            {{ snapshot.order.currency_symbol|default:"KES" }}
            {{ snapshot.order.tax_amount }}
        </strong>

    </div>

    {% endif %}


    <div class="total-row">

        <span>Delivery</span>
'''


    if marker not in text:

        raise RuntimeError(
            "Could not locate invoice delivery row."
        )


    text = text.replace(
        marker,
        addition,
        1,
    )


# New document snapshots use historical currency.
text = text.replace(
    '''KES {{ snapshot.order.total_amount }}''',
    '''{{ snapshot.order.currency_symbol|default:"KES" }} {{ snapshot.order.total_amount }}''',
)


INVOICE_TEMPLATE.write_text(
    text,
    encoding="utf-8",
)

print(
    "Invoice tax display added."
)


# ============================================================
# 14. RECEIPT TAX DISPLAY
# ============================================================

text = RECEIPT_TEMPLATE.read_text(
    encoding="utf-8-sig"
)


if "snapshot.order.tax_amount" not in text:

    marker = '''<div class="totals">

    <div class="total-row">

        <span>Order Total</span>
'''


    addition = '''<div class="totals">

    {% if snapshot.order.tax_amount and snapshot.order.tax_amount != "0.00" %}

    <div class="total-row">

        <span>
            Tax included
            ({{ snapshot.order.tax_rate }}%)
        </span>

        <strong>
            {{ snapshot.order.currency_symbol|default:"KES" }}
            {{ snapshot.order.tax_amount }}
        </strong>

    </div>

    {% endif %}


    <div class="total-row">

        <span>Order Total</span>
'''


    if marker not in text:

        raise RuntimeError(
            "Could not locate receipt totals."
        )


    text = text.replace(
        marker,
        addition,
        1,
    )


text = text.replace(
    '''KES {{ snapshot.order.total_amount }}''',
    '''{{ snapshot.order.currency_symbol|default:"KES" }} {{ snapshot.order.total_amount }}''',
)


RECEIPT_TEMPLATE.write_text(
    text,
    encoding="utf-8",
)

print(
    "Receipt tax display added."
)


# ============================================================
# 15. PHASE 12B TESTS
# ============================================================

TESTS.write_text(
r'''
from decimal import Decimal

from django.contrib.auth import (
    get_user_model,
)

from django.test import TestCase

from django.urls import reverse

from cart.models import (
    Cart,
    CartItem,
)

from categories.models import Category

from core.store_settings import (
    get_store_settings,
)

from delivery.models import (
    DeliveryZone,
)

from orders.models import Order

from orders.pricing import (
    calculate_order_pricing,
    minimum_order_satisfied,
    total_from_order_snapshot,
)

from products.models import Product


User = get_user_model()


class Phase12BPricingTests(
    TestCase
):

    def test_tax_is_calculated_after_discount(
        self,
    ):

        result = calculate_order_pricing(
            subtotal=Decimal("1000.00"),
            discount=Decimal("100.00"),
            shipping_cost=Decimal("200.00"),
            tax_enabled=True,
            tax_rate=Decimal("16.00"),
        )


        self.assertEqual(
            result["taxable_amount"],
            Decimal("900.00"),
        )


        self.assertEqual(
            result["tax_amount"],
            Decimal("144.00"),
        )


        self.assertEqual(
            result["total_amount"],
            Decimal("1244.00"),
        )


    def test_tax_disabled_is_zero(
        self,
    ):

        result = calculate_order_pricing(
            subtotal=Decimal("1000.00"),
            discount=Decimal("100.00"),
            shipping_cost=Decimal("200.00"),
            tax_enabled=False,
            tax_rate=Decimal("16.00"),
        )


        self.assertEqual(
            result["tax_amount"],
            Decimal("0.00"),
        )


        self.assertEqual(
            result["total_amount"],
            Decimal("1100.00"),
        )


    def test_minimum_order_validation(
        self,
    ):

        self.assertTrue(
            minimum_order_satisfied(
                subtotal=Decimal("500.00"),
                minimum_order_amount=Decimal("500.00"),
            )
        )


        self.assertFalse(
            minimum_order_satisfied(
                subtotal=Decimal("499.99"),
                minimum_order_amount=Decimal("500.00"),
            )
        )


    def test_delivery_quote_total_uses_saved_tax(
        self,
    ):

        user = User.objects.create_user(
            username="phase12bquote",
            password="pass12345",
        )


        order = Order.objects.create(
            user=user,
            order_number="P12B-Q-001",
            full_name="Phase 12B",
            phone="0712345678",
            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="1",
            subtotal=Decimal("1000.00"),
            discount=Decimal("100.00"),
            tax_enabled_at_checkout=True,
            tax_rate_at_checkout=Decimal("16.00"),
            tax_amount=Decimal("144.00"),
            shipping_cost=Decimal("0.00"),
            total_amount=Decimal("1044.00"),
        )


        self.assertEqual(
            total_from_order_snapshot(
                order,
                shipping_cost=Decimal("300.00"),
            ),
            Decimal("1344.00"),
        )


class Phase12BCheckoutTests(
    TestCase
):

    def setUp(self):

        self.user = (
            User.objects.create_user(
                username="phase12bcustomer",
                password="pass12345",
                email="phase12b@example.com",
                phone="0712345678",
                role=User.CUSTOMER,
            )
        )


        self.category = (
            Category.objects.create(
                name="Phase 12B",
                slug="phase-12b",
            )
        )


        self.product = (
            Product.objects.create(
                category=self.category,
                name="Phase 12B Product",
                slug="phase-12b-product",
                sku="P12B-001",
                price=Decimal("1000.00"),
                stock=20,
                reserved_stock=0,
                is_active=True,
            )
        )


        self.zone = (
            DeliveryZone.objects.create(
                county="Nairobi",
                town="Nairobi",
                method="local_door",
                pricing_mode="fixed",
                fee=Decimal("200.00"),
                is_active=True,
            )
        )


        self.cart = (
            Cart.objects.create(
                user=self.user
            )
        )


        CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2,
        )


        self.store = (
            get_store_settings()
        )


        self.client.login(
            username="phase12bcustomer",
            password="pass12345",
        )


    def test_disabled_orders_block_checkout(
        self,
    ):

        self.store.orders_enabled = False

        self.store.save()


        response = self.client.get(
            reverse(
                "checkout"
            )
        )


        self.assertEqual(
            response.status_code,
            302,
        )


        self.assertEqual(
            Order.objects.count(),
            0,
        )


    def test_minimum_order_blocks_checkout(
        self,
    ):

        self.store.orders_enabled = True

        self.store.minimum_order_amount = (
            Decimal("5000.00")
        )

        self.store.save()


        response = self.client.get(
            reverse(
                "checkout"
            )
        )


        self.assertEqual(
            response.status_code,
            302,
        )


        self.assertEqual(
            Order.objects.count(),
            0,
        )


    def test_checkout_captures_tax_and_currency_snapshot(
        self,
    ):

        self.store.orders_enabled = True

        self.store.minimum_order_amount = (
            Decimal("500.00")
        )

        self.store.tax_enabled = True

        self.store.tax_rate = (
            Decimal("16.00")
        )

        self.store.currency_code = "KES"

        self.store.currency_symbol = "KSh"

        self.store.save()


        response = self.client.post(
            reverse(
                "checkout"
            ),
            {
                "full_name":
                    "Phase 12B Customer",

                "phone":
                    "0712345678",

                "email":
                    "phase12b@example.com",

                "county":
                    "Nairobi",

                "city":
                    "Nairobi",

                "estate":
                    "CBD",

                "delivery_zone":
                    str(
                        self.zone.pk
                    ),

                "house_number":
                    "10",

                "landmark":
                    "",

                "delivery_notes":
                    "",
            },
        )


        self.assertEqual(
            response.status_code,
            302,
        )


        order = (
            Order.objects.get()
        )


        # Merchandise:
        # 2 x 1000 = 2000
        #
        # Tax:
        # 2000 x 16% = 320
        #
        # Delivery:
        # 200
        #
        # Total:
        # 2520

        self.assertEqual(
            order.subtotal,
            Decimal("2000.00"),
        )


        self.assertTrue(
            order.tax_enabled_at_checkout
        )


        self.assertEqual(
            order.tax_rate_at_checkout,
            Decimal("16.00"),
        )


        self.assertEqual(
            order.tax_amount,
            Decimal("320.00"),
        )


        self.assertEqual(
            order.shipping_cost,
            Decimal("200.00"),
        )


        self.assertEqual(
            order.total_amount,
            Decimal("2520.00"),
        )


        self.assertEqual(
            order.currency_code_at_checkout,
            "KES",
        )


        self.assertEqual(
            order.currency_symbol_at_checkout,
            "KSh",
        )


        self.assertEqual(
            order.minimum_order_amount_at_checkout,
            Decimal("500.00"),
        )


    def test_old_order_tax_snapshot_does_not_change_with_store_settings(
        self,
    ):

        order = Order.objects.create(
            user=self.user,
            order_number="P12B-HIST-001",
            full_name="Historical Customer",
            phone="0712345678",
            county="Nairobi",
            city="Nairobi",
            estate="CBD",
            house_number="1",
            subtotal=Decimal("1000.00"),
            discount=Decimal("0.00"),
            tax_enabled_at_checkout=True,
            tax_rate_at_checkout=Decimal("16.00"),
            tax_amount=Decimal("160.00"),
            shipping_cost=Decimal("100.00"),
            total_amount=Decimal("1260.00"),
            currency_code_at_checkout="KES",
            currency_symbol_at_checkout="KSh",
        )


        self.store.tax_rate = (
            Decimal("20.00")
        )

        self.store.currency_code = "USD"

        self.store.currency_symbol = "$"

        self.store.save()


        order.refresh_from_db()


        self.assertEqual(
            order.tax_rate_at_checkout,
            Decimal("16.00"),
        )


        self.assertEqual(
            order.tax_amount,
            Decimal("160.00"),
        )


        self.assertEqual(
            order.currency_code_at_checkout,
            "KES",
        )


        self.assertEqual(
            order.currency_symbol_at_checkout,
            "KSh",
        )
'''.strip() + "\n",
encoding="utf-8",
)


print(
    "Phase 12B tests created."
)


print()
print("=" * 72)
print("PHASE 12B INSTALLED")
print("=" * 72)
print()
print("Added:")
print("  Server-side checkout enable/disable")
print("  Server-side minimum order enforcement")
print("  Central pricing engine")
print("  Tax after coupon discount")
print("  Historical tax rate snapshot")
print("  Historical tax amount snapshot")
print("  Historical currency snapshot")
print("  Historical minimum-order snapshot")
print("  Tax-aware checkout total")
print("  Tax-aware order confirmation")
print("  Tax-aware invoices and receipts")
print("  Delivery quote totals preserve historical tax")
print()
print("Migration required.")
