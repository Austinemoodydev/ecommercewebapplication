from pathlib import Path
from datetime import datetime
import re
import shutil
import subprocess
import sys


ROOT = Path.cwd()

if not (ROOT / "manage.py").exists():
    raise SystemExit(
        "ERROR: Run this from the Django project root."
    )


stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

backup_dir = (
    ROOT
    / ".pricing_backups"
    / stamp
)

backup_dir.mkdir(
    parents=True,
    exist_ok=True,
)


def backup(path):
    if not path.exists():
        return

    destination = (
        backup_dir
        / path.relative_to(ROOT)
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        path,
        destination,
    )


def replace_once(
    path,
    old,
    new,
    description,
):
    text = path.read_text(
        encoding="utf-8-sig"
    )

    if new in text:
        print(
            f"[ALREADY] {description}"
        )
        return

    if old not in text:
        raise SystemExit(
            f"ERROR: Could not safely patch {description}"
        )

    backup(path)

    text = text.replace(
        old,
        new,
        1,
    )

    path.write_text(
        text,
        encoding="utf-8",
    )

    print(
        f"[PATCHED] {description}"
    )


# ============================================================
# 1. GLOBAL MONEY FORMATTER
# ============================================================

templatetag_dir = (
    ROOT
    / "core"
    / "templatetags"
)

templatetag_dir.mkdir(
    parents=True,
    exist_ok=True,
)

init_file = (
    templatetag_dir
    / "__init__.py"
)

init_file.touch(
    exist_ok=True
)

money_file = (
    templatetag_dir
    / "money.py"
)

backup(money_file)

money_file.write_text(
r'''from decimal import (
    Decimal,
    InvalidOperation,
    ROUND_HALF_UP,
)

from django import template


register = template.Library()


@register.filter(name="money")
def money(value):
    """
    Format a monetary value for display.

    Examples:

        75000.00
        -> 75,000

        74999.00
        -> 74,999

        74999.50
        -> 74,999.50

        1234567.89
        -> 1,234,567.89

    This filter changes presentation only.
    It does not change database values.
    """

    if value in (
        None,
        "",
    ):
        return "0"

    try:
        amount = Decimal(
            str(value)
        )
    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ):
        return value

    amount = amount.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    if (
        amount
        == amount.to_integral_value()
    ):
        return format(
            amount,
            ",.0f",
        )

    return format(
        amount,
        ",.2f",
    )
''',
    encoding="utf-8",
)

print(
    "[CREATED] Global money formatter"
)


# ============================================================
# 2. ENABLE MONEY FILTER GLOBALLY
# ============================================================

settings_file = (
    ROOT
    / "config"
    / "settings.py"
)

settings_text = (
    settings_file.read_text(
        encoding="utf-8-sig"
    )
)

builtin = (
    "'builtins': "
    "['core.templatetags.money'],"
)

if builtin not in settings_text:

    marker = "'OPTIONS': {"

    if marker not in settings_text:
        raise SystemExit(
            "ERROR: TEMPLATES OPTIONS not found."
        )

    backup(settings_file)

    settings_text = (
        settings_text.replace(
            marker,
            marker
            + "\n            "
            + builtin,
            1,
        )
    )

    settings_file.write_text(
        settings_text,
        encoding="utf-8",
    )

    print(
        "[PATCHED] Money filter enabled globally"
    )

else:
    print(
        "[ALREADY] Money filter globally enabled"
    )


# ============================================================
# 3. RETAIL PRICE NORMALIZATION
# ============================================================

forms_file = (
    ROOT
    / "dashboard"
    / "forms.py"
)

forms_text = (
    forms_file.read_text(
        encoding="utf-8-sig"
    )
)

backup(forms_file)


if (
    "from decimal import Decimal, ROUND_HALF_UP"
    not in forms_text
):

    forms_text = (
        "from decimal import Decimal, ROUND_HALF_UP\n"
        + forms_text
    )


helper = '''
RETAIL_PRICE_UNIT = Decimal("1")


def normalize_retail_price(value):
    """
    Store customer-facing retail prices
    using whole Kenyan shillings.

    DecimalField remains decimal_places=2,
    therefore 75000 is stored as 75000.00.
    """

    if value is None:
        return None

    return value.quantize(
        RETAIL_PRICE_UNIT,
        rounding=ROUND_HALF_UP,
    )


'''


if (
    "def normalize_retail_price(value):"
    not in forms_text
):

    marker = (
        "from core.upload_security "
        "import validate_uploaded_image\n"
    )

    if marker not in forms_text:
        raise SystemExit(
            "ERROR: dashboard/forms.py import marker missing."
        )

    forms_text = (
        forms_text.replace(
            marker,
            marker
            + "\n"
            + helper,
            1,
        )
    )


# Retail price widgets:
# price + discount price + variant price
# become whole-shilling inputs.
forms_text = forms_text.replace(
'''            "price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                }
            ),''',
'''            "price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "1",
                }
            ),''',
    1,
)

forms_text = forms_text.replace(
'''            "discount_price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                    "placeholder": "Optional sale price",
                }
            ),''',
'''            "discount_price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "1",
                    "placeholder": "e.g. 75000",
                }
            ),''',
    1,
)


# Variant retail price only.
variant_start = forms_text.find(
    "class AdminProductVariantForm"
)

if variant_start == -1:
    raise SystemExit(
        "ERROR: AdminProductVariantForm not found."
    )

before_variant = (
    forms_text[:variant_start]
)

variant_section = (
    forms_text[variant_start:]
)

variant_section = (
    variant_section.replace(
        '"step": "0.01",',
        '"step": "1",',
        1,
    )
)

forms_text = (
    before_variant
    + variant_section
)


product_clean_methods = '''
    def clean_price(self):

        return normalize_retail_price(
            self.cleaned_data.get(
                "price"
            )
        )


    def clean_discount_price(self):

        return normalize_retail_price(
            self.cleaned_data.get(
                "discount_price"
            )
        )


'''


if (
    "def clean_discount_price(self):"
    not in forms_text
):

    marker = (
        "    def clean_image(self):\n"
    )

    if marker not in forms_text:
        raise SystemExit(
            "ERROR: Product clean_image marker missing."
        )

    forms_text = (
        forms_text.replace(
            marker,
            product_clean_methods
            + marker,
            1,
        )
    )


# Add variant clean_price only inside variant class.
variant_start = forms_text.find(
    "class AdminProductVariantForm"
)

variant_section = (
    forms_text[variant_start:]
)

if (
    "def clean_price(self):"
    not in variant_section
):

    insertion_marker = (
        "    def clean_sku(self):"
    )

    if insertion_marker not in variant_section:

        # Some snapshots may place clean methods differently.
        # Insert before the next class if possible.
        next_class = variant_section.find(
            "\nclass ",
            10,
        )

        method = '''
    def clean_price(self):

        return normalize_retail_price(
            self.cleaned_data.get(
                "price"
            )
        )


'''

        if next_class == -1:
            variant_section += method
        else:
            variant_section = (
                variant_section[:next_class]
                + method
                + variant_section[next_class:]
            )

    else:

        variant_section = (
            variant_section.replace(
                insertion_marker,
'''    def clean_price(self):

        return normalize_retail_price(
            self.cleaned_data.get(
                "price"
            )
        )


'''
                + insertion_marker,
                1,
            )
        )

    forms_text = (
        forms_text[:variant_start]
        + variant_section
    )


forms_file.write_text(
    forms_text,
    encoding="utf-8",
)

print(
    "[PATCHED] Retail prices normalize to whole KES"
)

print(
    "[UNCHANGED] Cost price may still use cents"
)


# ============================================================
# 4. CONVERT floatformat:2 MONEY OUTPUTS
# ============================================================

template_roots = [
    ROOT / "templates",
    ROOT / "delivery" / "templates",
    ROOT / "payments" / "templates",
]


for template_root in template_roots:

    if not template_root.exists():
        continue

    for path in template_root.rglob(
        "*.html"
    ):

        text = path.read_text(
            encoding="utf-8-sig"
        )

        original = text

        # Preserve percentages such as:
        # {{ refund_rate|floatformat:2 }}%
        pattern = re.compile(
            r"\|floatformat:2"
            r"(\s*}})"
            r"(\s*%)?"
        )

        def replace_float(match):

            closing = match.group(1)
            percent = match.group(2)

            if percent:
                return (
                    "|floatformat:2"
                    + closing
                    + percent
                )

            return (
                "|money"
                + closing
            )

        text = pattern.sub(
            replace_float,
            text,
        )

        if text != original:
            backup(path)

            path.write_text(
                text,
                encoding="utf-8",
            )


print(
    "[PATCHED] Existing money float formatting"
)


# ============================================================
# 5. CUSTOMER-FACING RAW MONEY VALUES
# ============================================================

replacements = {


    "templates/core/home.html": [
        (
            "{{ product.discount_price }}",
            "{{ product.discount_price|money }}",
        ),
        (
            "{{ product.price }}",
            "{{ product.price|money }}",
        ),
    ],


    "templates/products/shop.html": [
        (
            "{{ product.discount_price }}",
            "{{ product.discount_price|money }}",
        ),
        (
            "{{ product.price }}",
            "{{ product.price|money }}",
        ),
    ],


    "templates/products/offers.html": [
        (
            "{{ product.discount_price }}",
            "{{ product.discount_price|money }}",
        ),
        (
            "{{ product.price }}",
            "{{ product.price|money }}",
        ),
    ],


    "templates/categories/category_detail.html": [
        (
            "{{ product.discount_price }}",
            "{{ product.discount_price|money }}",
        ),
        (
            "{{ product.price }}",
            "{{ product.price|money }}",
        ),
    ],


    "templates/products/product_detail.html": [
        (
            (
                '<h3 class="text-primary">'
                'KES {{ product.current_price }}'
                '</h3>'
            ),
            (
                '<h3 class="text-primary">'
                'KES {{ product.current_price|money }}'
                '</h3>'
            ),
        ),
        (
            (
                "{{ variant.name }} - "
                "KES {{ variant.current_price }}"
            ),
            (
                "{{ variant.name }} - "
                "KES {{ variant.current_price|money }}"
            ),
        ),
    ],


    "templates/cart/cart.html": [
        (
            "{{ item.variant.current_price }}",
            "{{ item.variant.current_price|money }}",
        ),
        (
            "{{ item.product.current_price }}",
            "{{ item.product.current_price|money }}",
        ),
        (
            "{{ item.subtotal }}",
            "{{ item.subtotal|money }}",
        ),
        (
            "{{ total }}",
            "{{ total|money }}",
        ),
    ],


    "templates/wishlist/wishlist.html": [
        (
            "{{ item.product.current_price }}",
            "{{ item.product.current_price|money }}",
        ),
    ],


    "templates/orders/checkout.html": [
        (
            "· KES {{ zone.fee }}",
            "· KES {{ zone.fee|money }}",
        ),
        (
            "<span>KES {{ item.subtotal }}</span>",
            "<span>KES {{ item.subtotal|money }}</span>",
        ),
        (
            "<strong>KES {{ cart.total_price }}</strong>",
            "<strong>KES {{ cart.total_price|money }}</strong>",
        ),
        (
            (
                '<span id="checkout-total">'
                '{{ cart.total_price }}'
                '</span>'
            ),
            (
                '<span id="checkout-total">'
                '{{ cart.total_price|money }}'
                '</span>'
            ),
        ),
    ],


    "templates/orders/order_confirmation.html": [
        (
            "{{ order.subtotal }}",
            "{{ order.subtotal|money }}",
        ),
        (
            "{{ order.tax_amount }}",
            "{{ order.tax_amount|money }}",
        ),
        (
            "{{ order.shipping_cost }}",
            "{{ order.shipping_cost|money }}",
        ),
        (
            "{{ order.total_amount }}",
            "{{ order.total_amount|money }}",
        ),
    ],


    "templates/orders/guest_order_detail.html": [
        (
            "{{ item.subtotal }}",
            "{{ item.subtotal|money }}",
        ),
        (
            "{{ order.subtotal }}",
            "{{ order.subtotal|money }}",
        ),
        (
            "{{ order.tax_amount }}",
            "{{ order.tax_amount|money }}",
        ),
        (
            "{{ order.total_amount }}",
            "{{ order.total_amount|money }}",
        ),
    ],


    "templates/dashboard/order_history.html": [
        (
            "{{ order.total_amount }}",
            "{{ order.total_amount|money }}",
        ),
    ],


    "templates/dashboard/dashboard.html": [
        (
            "{{ order.total_amount }}",
            "{{ order.total_amount|money }}",
        ),
    ],


    "templates/dashboard/order_detail.html": [
        (
            "{{ item.price }}",
            "{{ item.price|money }}",
        ),
        (
            "{{ item.subtotal }}",
            "{{ item.subtotal|money }}",
        ),
        (
            "{{ order.subtotal }}",
            "{{ order.subtotal|money }}",
        ),
        (
            "{{ order.shipping_cost }}",
            "{{ order.shipping_cost|money }}",
        ),
        (
            "{{ order.total_amount }}",
            "{{ order.total_amount|money }}",
        ),
    ],


    "templates/payments/pay.html": [
        (
            "{{ order.total_amount }}",
            "{{ order.total_amount|money }}",
        ),
    ],


    "templates/payments/refund_request.html": [
        (
            "{{ order.total_amount }}",
            "{{ order.total_amount|money }}",
        ),
    ],


    "templates/orders/documents/invoice.html": [
        (
            "{{ item.price }}",
            "{{ item.price|money }}",
        ),
        (
            "{{ item.subtotal }}",
            "{{ item.subtotal|money }}",
        ),
        (
            "{{ snapshot.order.subtotal }}",
            "{{ snapshot.order.subtotal|money }}",
        ),
        (
            "{{ snapshot.order.discount }}",
            "{{ snapshot.order.discount|money }}",
        ),
        (
            "{{ snapshot.order.tax_amount }}",
            "{{ snapshot.order.tax_amount|money }}",
        ),
        (
            "{{ snapshot.order.shipping_cost }}",
            "{{ snapshot.order.shipping_cost|money }}",
        ),
        (
            "{{ snapshot.order.total_amount }}",
            "{{ snapshot.order.total_amount|money }}",
        ),
    ],


    "templates/orders/documents/receipt.html": [
        (
            "{{ snapshot.payment.amount }}",
            "{{ snapshot.payment.amount|money }}",
        ),
        (
            "{{ item.price }}",
            "{{ item.price|money }}",
        ),
        (
            "{{ item.subtotal }}",
            "{{ item.subtotal|money }}",
        ),
        (
            "{{ snapshot.order.tax_amount }}",
            "{{ snapshot.order.tax_amount|money }}",
        ),
        (
            "{{ snapshot.order.total_amount }}",
            "{{ snapshot.order.total_amount|money }}",
        ),
        (
            "{{ snapshot.refund_total }}",
            "{{ snapshot.refund_total|money }}",
        ),
        (
            "{{ snapshot.net_amount }}",
            "{{ snapshot.net_amount|money }}",
        ),
        (
            "{{ refund.amount }}",
            "{{ refund.amount|money }}",
        ),
    ],


    "templates/orders/documents/credit_note.html": [
        (
            "{{ snapshot.order.total_amount }}",
            "{{ snapshot.order.total_amount|money }}",
        ),
        (
            "{{ item.subtotal }}",
            "{{ item.subtotal|money }}",
        ),
    ],
}


for relative, changes in replacements.items():

    path = ROOT / relative

    if not path.exists():
        continue

    text = path.read_text(
        encoding="utf-8-sig"
    )

    original = text

    for old, new in changes:

        if new in text:
            continue

        text = text.replace(
            old,
            new,
        )

    if text != original:

        backup(path)

        path.write_text(
            text,
            encoding="utf-8",
        )


print(
    "[PATCHED] Customer-facing money presentation"
)


# ============================================================
# 6. CART JAVASCRIPT MONEY FORMATTING
# ============================================================

cart_js = (
    ROOT
    / "static"
    / "js"
    / "cart.js"
)

if cart_js.exists():

    backup(cart_js)

    text = cart_js.read_text(
        encoding="utf-8-sig"
    )


    helper = '''function formatKesAmount(value) {
    const amount = Number(value);

    if (!Number.isFinite(amount)) {
        return value;
    }

    const hasCents = (
        Math.round(amount * 100) % 100
        !== 0
    );

    return amount.toLocaleString(
        "en-KE",
        {
            minimumFractionDigits:
                hasCents ? 2 : 0,
            maximumFractionDigits: 2
        }
    );
}

'''


    if (
        "function formatKesAmount"
        not in text
    ):
        text = helper + text


    text = text.replace(
        "totalEl.textContent = data.total;",
        (
            "totalEl.textContent = "
            "formatKesAmount(data.total);"
        ),
    )

    text = text.replace(
        "subEl.textContent = data.subtotal;",
        (
            "subEl.textContent = "
            "formatKesAmount(data.subtotal);"
        ),
    )

    text = text.replace(
        "KES ${item.subtotal}",
        (
            "KES "
            "${formatKesAmount(item.subtotal)}"
        ),
    )


    cart_js.write_text(
        text,
        encoding="utf-8",
    )


print(
    "[PATCHED] Cart JavaScript money formatting"
)


# ============================================================
# 7. CHECKOUT JAVASCRIPT MONEY FORMATTING
# ============================================================

checkout_file = (
    ROOT
    / "templates"
    / "orders"
    / "checkout.html"
)

if checkout_file.exists():

    backup(checkout_file)

    text = checkout_file.read_text(
        encoding="utf-8-sig"
    )


    marker = (
        'document.addEventListener('
        '"DOMContentLoaded", function () {\n'
    )


    helper = '''document.addEventListener("DOMContentLoaded", function () {

    function formatKesAmount(value) {

        const amount = Number(value);

        if (!Number.isFinite(amount)) {
            return value;
        }

        const hasCents = (
            Math.round(amount * 100) % 100
            !== 0
        );

        return amount.toLocaleString(
            "en-KE",
            {
                minimumFractionDigits:
                    hasCents ? 2 : 0,
                maximumFractionDigits: 2
            }
        );
    }
'''


    if (
        "function formatKesAmount(value)"
        not in text
    ):

        if marker not in text:
            raise SystemExit(
                "ERROR: Checkout JavaScript marker missing."
            )

        text = text.replace(
            marker,
            helper,
            1,
        )


    text = text.replace(
        "taxAmount.toFixed(2)",
        "formatKesAmount(taxAmount)",
    )

    text = text.replace(
        "total.toFixed(2)",
        "formatKesAmount(total)",
    )

    text = text.replace(
        'feeEl.textContent = "0.00";',
        'feeEl.textContent = "0";',
    )

    text = text.replace(
        "currentFee.toFixed(2)",
        "formatKesAmount(currentFee)",
    )


    checkout_file.write_text(
        text,
        encoding="utf-8",
    )


print(
    "[PATCHED] Checkout JavaScript money formatting"
)


# ============================================================
# 8. TESTS
# ============================================================

test_file = (
    ROOT
    / "core"
    / "test_money_formatting.py"
)

backup(test_file)

test_file.write_text(
r'''from decimal import Decimal

from django.template import (
    Context,
    Template,
)
from django.test import SimpleTestCase

from core.templatetags.money import money
from dashboard.forms import (
    AdminProductForm,
    AdminProductVariantForm,
    normalize_retail_price,
)


class MoneyFormattingTests(
    SimpleTestCase
):

    def test_whole_shillings_hide_decimal_places(
        self
    ):

        self.assertEqual(
            money(
                Decimal("75000.00")
            ),
            "75,000",
        )


    def test_fractional_money_keeps_two_decimals(
        self
    ):

        self.assertEqual(
            money(
                Decimal("74999.50")
            ),
            "74,999.50",
        )


    def test_large_money_has_grouping(
        self
    ):

        self.assertEqual(
            money(
                Decimal("1250000.00")
            ),
            "1,250,000",
        )


    def test_template_filter_is_available_globally(
        self
    ):

        output = Template(
            "{{ amount|money }}"
        ).render(
            Context(
                {
                    "amount": (
                        Decimal(
                            "75000.00"
                        )
                    )
                }
            )
        )

        self.assertEqual(
            output,
            "75,000",
        )


class RetailPriceNormalizationTests(
    SimpleTestCase
):

    def test_retail_price_rounds_to_nearest_shilling(
        self
    ):

        self.assertEqual(
            normalize_retail_price(
                Decimal(
                    "74999.98"
                )
            ),
            Decimal(
                "75000"
            ),
        )


    def test_retail_price_rounds_down_when_appropriate(
        self
    ):

        self.assertEqual(
            normalize_retail_price(
                Decimal(
                    "74999.20"
                )
            ),
            Decimal(
                "74999"
            ),
        )


    def test_product_price_input_uses_whole_shillings(
        self
    ):

        self.assertEqual(
            AdminProductForm
            .base_fields[
                "price"
            ]
            .widget
            .attrs[
                "step"
            ],
            "1",
        )


    def test_sale_price_input_uses_whole_shillings(
        self
    ):

        self.assertEqual(
            AdminProductForm
            .base_fields[
                "discount_price"
            ]
            .widget
            .attrs[
                "step"
            ],
            "1",
        )


    def test_variant_price_input_uses_whole_shillings(
        self
    ):

        self.assertEqual(
            AdminProductVariantForm
            .base_fields[
                "price"
            ]
            .widget
            .attrs[
                "step"
            ],
            "1",
        )
''',
    encoding="utf-8",
)

print(
    "[CREATED] Money regression tests"
)


# ============================================================
# 9. GITIGNORE
# ============================================================

gitignore = ROOT / ".gitignore"

if gitignore.exists():

    text = gitignore.read_text(
        encoding="utf-8-sig"
    )

    entry = (
        ".pricing_backups/"
    )

    if entry not in text:

        if not text.endswith("\n"):
            text += "\n"

        text += (
            "\n"
            "# Local pricing patch backups\n"
            + entry
            + "\n"
        )

        gitignore.write_text(
            text,
            encoding="utf-8",
        )


# ============================================================
# 10. VALIDATE CODE FIRST
# ============================================================

commands = [

    [
        sys.executable,
        "manage.py",
        "check",
    ],

    [
        sys.executable,
        "manage.py",
        "makemigrations",
        "--check",
        "--dry-run",
    ],

    [
        sys.executable,
        "manage.py",
        "test",
        "core.test_money_formatting",
        "-v",
        "2",
    ],

    [
        sys.executable,
        "manage.py",
        "test",
        "products",
        "cart",
        "orders",
        "dashboard",
        "-v",
        "1",
    ],
]


for command in commands:

    print()
    print("=" * 72)

    print(
        ">",
        " ".join(
            command
        )
    )

    print("=" * 72)

    result = subprocess.run(
        command,
        cwd=ROOT,
    )

    if result.returncode != 0:

        print()
        print("=" * 72)
        print(
            "PRICING VALIDATION FAILED"
        )
        print("=" * 72)

        print()
        print(
            "Do not continue to code cleanup."
        )

        print(
            "Send me the exact failing output."
        )

        print()
        print(
            "Backup directory:"
        )

        print(
            backup_dir
        )

        raise SystemExit(
            result.returncode
        )


# ============================================================
# 11. CORRECT CURRENT GAMING LAPTOP CATALOG PRICE
# ============================================================

update_code = r'''
from decimal import Decimal
from products.models import Product

product = Product.objects.filter(
    slug="gaming-laptop"
).first()

if product is None:
    print(
        "[INFO] Gaming Laptop not found. "
        "No catalog row changed."
    )
else:
    print(
        "[BEFORE] Gaming Laptop:"
    )

    print(
        "Regular price:",
        product.price
    )

    print(
        "Sale price:",
        product.discount_price
    )

    product.discount_price = Decimal(
        "75000.00"
    )

    product.save(
        update_fields=[
            "discount_price",
            "updated_at",
        ]
    )

    product.refresh_from_db()

    print(
        "[AFTER] Gaming Laptop:"
    )

    print(
        "Regular price:",
        product.price
    )

    print(
        "Sale price:",
        product.discount_price
    )

    print(
        "[SAFE] Historical orders/payments "
        "were NOT changed."
    )
'''


result = subprocess.run(
    [
        sys.executable,
        "manage.py",
        "shell",
        "-c",
        update_code,
    ],
    cwd=ROOT,
)

if result.returncode != 0:

    raise SystemExit(
        result.returncode
    )


print()
print("=" * 72)

print(
    "KENYAN RETAIL PRICING PHASE PASSED"
)

print("=" * 72)

print()
print(
    "Retail behavior:"
)

print(
    "  74999.98 entered -> stored as 75000.00"
)

print(
    "  75000.00 displayed -> KES 75,000"
)

print(
    "  74999.00 displayed -> KES 74,999"
)

print(
    "  genuine 74999.50 accounting value "
    "-> KES 74,999.50"
)

print()
print(
    "Preserved:"
)

print(
    "  - Decimal database fields"
)

print(
    "  - Tax calculations"
)

print(
    "  - Refund calculations"
)

print(
    "  - Payment calculations"
)

print(
    "  - Historical order totals"
)

print(
    "  - Historical payment amounts"
)

print(
    "  - Cost price decimal precision"
)

print()
print(
    "Backup directory:"
)

print(
    backup_dir
)

print()
print(
    "FULL REGRESSION GATE:"
)

print(
    "python manage.py test -v 1"
)

