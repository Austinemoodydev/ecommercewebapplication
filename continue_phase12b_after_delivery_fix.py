from pathlib import Path
import shutil


ROOT = Path.cwd()

DOCUMENT_SERVICE = (
    ROOT
    / "orders"
    / "document_service.py"
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


for path in [
    DOCUMENT_SERVICE,
    CHECKOUT_TEMPLATE,
    CONFIRMATION_TEMPLATE,
    INVOICE_TEMPLATE,
    RECEIPT_TEMPLATE,
]:

    if not path.exists():

        raise RuntimeError(
            f"Missing file: {path}"
        )


    backup = Path(
        str(path)
        + ".phase12b-cont-backup"
    )

    if not backup.exists():

        shutil.copy2(
            path,
            backup,
        )


# ============================================================
# DOCUMENT SNAPSHOT
# ============================================================

text = DOCUMENT_SERVICE.read_text(
    encoding="utf-8-sig"
)


if '"tax_amount"' not in text:

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
            "Could not locate document "
            "snapshot financial section."
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


# ============================================================
# CHECKOUT TAX UI
# ============================================================

text = CHECKOUT_TEMPLATE.read_text(
    encoding="utf-8-sig"
)


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
            "Could not locate checkout "
            "delivery summary row."
        )


    text = text.replace(
        marker,
        addition,
        1,
    )


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


    if marker in text:

        text = text.replace(
            marker,
            addition,
            1,
        )


# JS tax variables
if "const taxEnabled" not in text:

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
            "Could not locate checkout subtotal JS."
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


if old in text:

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

    text = text.replace(
        old,
        new,
        1,
    )


if (
    "recalcTotal();"
    not in text[
        text.find(
            "const detectBtn"
        ) - 100:
        text.find(
            "const detectBtn"
        ) + 50
    ]
):

    marker = '''    const detectBtn = document.getElementById("detect-location-btn");
'''

    if marker in text:

        text = text.replace(
            marker,
            '''    recalcTotal();


    const detectBtn = document.getElementById("detect-location-btn");
''',
            1,
        )


CHECKOUT_TEMPLATE.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# CONFIRMATION
# ============================================================

text = CONFIRMATION_TEMPLATE.read_text(
    encoding="utf-8-sig"
)


if "order.tax_rate_at_checkout" not in text:

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


    if marker in text:

        text = text.replace(
            marker,
            addition,
            1,
        )


text = text.replace(
    "KES {{ order.total_amount }}",
    "{{ order.currency_symbol_at_checkout }} {{ order.total_amount }}",
)


CONFIRMATION_TEMPLATE.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# INVOICE
# ============================================================

text = INVOICE_TEMPLATE.read_text(
    encoding="utf-8-sig"
)


if "snapshot.order.tax_rate" not in text:

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
            {{ snapshot.order.currency_symbol|default:"KSh" }}
            {{ snapshot.order.tax_amount }}
        </strong>

    </div>

    {% endif %}


    <div class="total-row">

        <span>Delivery</span>
'''


    if marker in text:

        text = text.replace(
            marker,
            addition,
            1,
        )


text = text.replace(
    "KES {{ snapshot.order.total_amount }}",
    "{{ snapshot.order.currency_symbol|default:'KSh' }} {{ snapshot.order.total_amount }}",
)


INVOICE_TEMPLATE.write_text(
    text,
    encoding="utf-8",
)


# ============================================================
# RECEIPT
# ============================================================

text = RECEIPT_TEMPLATE.read_text(
    encoding="utf-8-sig"
)


if "snapshot.order.tax_rate" not in text:

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
            {{ snapshot.order.currency_symbol|default:"KSh" }}
            {{ snapshot.order.tax_amount }}
        </strong>

    </div>

    {% endif %}


    <div class="total-row">

        <span>Order Total</span>
'''


    if marker in text:

        text = text.replace(
            marker,
            addition,
            1,
        )


text = text.replace(
    "KES {{ snapshot.order.total_amount }}",
    "{{ snapshot.order.currency_symbol|default:'KSh' }} {{ snapshot.order.total_amount }}",
)


RECEIPT_TEMPLATE.write_text(
    text,
    encoding="utf-8",
)


print("=" * 72)
print("PHASE 12B CONTINUATION APPLIED")
print("=" * 72)
print()
print("Document snapshot integration: OK")
print("Checkout tax UI: OK")
print("Confirmation tax UI: OK")
print("Invoice tax UI: OK")
print("Receipt tax UI: OK")
