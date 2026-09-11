from pathlib import Path
import re
import shutil

ROOT = Path.cwd()

ORDER_MODELS = ROOT / "orders" / "models.py"
ORDER_FORMS = ROOT / "orders" / "forms.py"
ORDER_VIEWS = ROOT / "orders" / "views.py"

PAYMENT_VIEWS = ROOT / "payments" / "views.py"

DELIVERY_VIEWS = ROOT / "delivery" / "views.py"
DELIVERY_URLS = ROOT / "delivery" / "urls.py"

CHECKOUT_TEMPLATE = ROOT / "templates" / "orders" / "checkout.html"

CONFIRM_TEMPLATE = (
    ROOT
    / "templates"
    / "orders"
    / "order_confirmation.html"
)

PAY_TEMPLATE = (
    ROOT
    / "templates"
    / "payments"
    / "pay.html"
)

DELIVERY_DETAIL = (
    ROOT
    / "delivery"
    / "templates"
    / "dashboard"
    / "admin"
    / "delivery"
    / "detail.html"
)


# ============================================================
# BACKUPS
# ============================================================

for path in [
    ORDER_MODELS,
    ORDER_FORMS,
    ORDER_VIEWS,
    PAYMENT_VIEWS,
    DELIVERY_VIEWS,
    DELIVERY_URLS,
    CHECKOUT_TEMPLATE,
    CONFIRM_TEMPLATE,
    PAY_TEMPLATE,
    DELIVERY_DETAIL,
]:

    if path.exists():

        backup = Path(
            str(path) + ".phase7cbackup"
        )

        if not backup.exists():

            shutil.copy2(
                path,
                backup,
            )


# ============================================================
# 1. ORDER DELIVERY PRICING FIELDS
# ============================================================

text = ORDER_MODELS.read_text(
    encoding="utf-8-sig"
)

if "DELIVERY_PRICING_STATUS_CHOICES" not in text:

    marker = '''    INVENTORY_STATUS_CHOICES = [
'''

    addition = '''    DELIVERY_PRICING_STATUS_CHOICES = [
        ("fixed", "Fixed Delivery Price"),
        ("quote_pending", "Delivery Quote Pending"),
        ("quoted", "Delivery Quote Confirmed"),
    ]

'''

    if marker not in text:

        raise RuntimeError(
            "Could not locate Order choices."
        )

    text = text.replace(
        marker,
        addition + marker,
        1,
    )


if "delivery_pricing_status =" not in text:

    marker = '''    shipping_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
'''

    addition = '''    delivery_zone = models.ForeignKey(
        "delivery.DeliveryZone",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )

    delivery_pricing_status = models.CharField(
        max_length=30,
        choices=DELIVERY_PRICING_STATUS_CHOICES,
        default="fixed",
        db_index=True,
    )

'''

    if marker not in text:

        raise RuntimeError(
            "Could not locate shipping_cost."
        )

    text = text.replace(
        marker,
        addition + marker,
        1,
    )

ORDER_MODELS.write_text(
    text,
    encoding="utf-8",
)

print(
    "Added delivery pricing fields to Order."
)


# ============================================================
# 2. CHECKOUT FORM
# ============================================================

form_text = ORDER_FORMS.read_text(
    encoding="utf-8-sig"
)

if (
    "from delivery.models import DeliveryZone"
    not in form_text
):

    form_text = (
        "from delivery.models import DeliveryZone\n"
        + form_text
    )


# Remove old DeliveryArea ModelChoice field.
form_text = re.sub(
    r'''
    \n\s*delivery_area\s*=\s*forms\.ModelChoiceField\(
        .*?
    \)\n
    ''',
    "\n",
    form_text,
    count=1,
    flags=re.S | re.X,
)


# Add estate and delivery_zone before house_number.
if "delivery_zone = forms.ModelChoiceField" not in form_text:

    marker = '''    house_number = forms.CharField(max_length=100)
'''

    addition = '''    estate = forms.CharField(
        max_length=150,
    )

    delivery_zone = forms.ModelChoiceField(
        queryset=DeliveryZone.objects.filter(
            is_active=True
        ).select_related(
            "provider"
        ),
        required=True,
    )

'''

    if marker not in form_text:

        raise RuntimeError(
            "Could not locate house_number form field."
        )

    form_text = form_text.replace(
        marker,
        addition + marker,
        1,
    )


# Add secure server-side location validation.
if "def clean(self):" not in form_text:

    class_end_marker = '''    longitude = forms.DecimalField(required=False, max_digits=9, decimal_places=6)
'''

    clean_method = r'''

    def clean(self):

        cleaned = super().clean()

        zone = cleaned.get(
            "delivery_zone"
        )

        county = (
            cleaned.get("county")
            or ""
        ).strip()

        city = (
            cleaned.get("city")
            or ""
        ).strip()

        if not zone:
            return cleaned

        if (
            zone.county.strip().casefold()
            != county.casefold()
        ):

            self.add_error(
                "delivery_zone",
                (
                    "The selected delivery option "
                    "does not match the selected county."
                ),
            )

        if (
            zone.town
            and zone.town.strip().casefold()
            != city.casefold()
        ):

            self.add_error(
                "delivery_zone",
                (
                    "The selected delivery option "
                    "does not match the selected town."
                ),
            )

        return cleaned
'''

    if class_end_marker not in form_text:

        raise RuntimeError(
            "Could not locate end of CheckoutForm."
        )

    form_text = form_text.replace(
        class_end_marker,
        class_end_marker + clean_method,
        1,
    )


ORDER_FORMS.write_text(
    form_text,
    encoding="utf-8",
)

print(
    "CheckoutForm now uses DeliveryZone."
)


# ============================================================
# 3. CHECKOUT VIEW IMPORTS
# ============================================================

view_text = ORDER_VIEWS.read_text(
    encoding="utf-8-sig"
)


if (
    "from delivery.models import Delivery, DeliveryZone"
    not in view_text
):

    import_marker = '''from products.models import Product
'''

    addition = '''from delivery.models import Delivery, DeliveryZone
'''

    if import_marker not in view_text:

        raise RuntimeError(
            "Could not locate Product import."
        )

    view_text = view_text.replace(
        import_marker,
        import_marker + addition,
        1,
    )


# ============================================================
# 4. DELIVERY ZONES IN CHECKOUT
# ============================================================

view_text = re.sub(
    r'''
    delivery_areas\s*=\s*
    DeliveryArea\.objects\.filter\(
        is_active=True
    \)
    ''',
    '''delivery_zones = (
        DeliveryZone.objects
        .filter(is_active=True)
        .select_related("provider")
        .order_by(
            "county",
            "town",
            "method",
        )
    )''',
    view_text,
    count=1,
    flags=re.S | re.X,
)


# ============================================================
# 5. SELECTED DELIVERY ZONE
# ============================================================

old = '''                delivery_area = form.cleaned_data["delivery_area"]

                subtotal = cart.total_price
                shipping_cost = delivery_area.fee
'''

new = '''                delivery_zone = (
                    DeliveryZone.objects
                    .select_for_update()
                    .select_related("provider")
                    .get(
                        pk=form.cleaned_data[
                            "delivery_zone"
                        ].pk,
                        is_active=True,
                    )
                )

                subtotal = cart.total_price

                if (
                    delivery_zone.pricing_mode
                    == "fixed"
                ):

                    shipping_cost = (
                        delivery_zone.fee
                    )

                    delivery_pricing_status = (
                        "fixed"
                    )

                else:

                    # The final transport cost will be
                    # entered by staff before payment.
                    shipping_cost = Decimal("0.00")

                    delivery_pricing_status = (
                        "quote_pending"
                    )
'''

if old not in view_text:

    raise RuntimeError(
        "Could not locate old DeliveryArea "
        "shipping calculation."
    )

view_text = view_text.replace(
    old,
    new,
    1,
)


# ============================================================
# 6. ORDER FIELDS
# ============================================================

view_text = view_text.replace(
    '''                    county=form.cleaned_data["county"],
                    city=form.cleaned_data["city"],
                    estate=delivery_area.name,
                    house_number=form.cleaned_data["house_number"],
''',
    '''                    county=form.cleaned_data["county"],
                    city=form.cleaned_data["city"],
                    estate=form.cleaned_data["estate"],
                    house_number=form.cleaned_data["house_number"],

                    delivery_zone=delivery_zone,
                    delivery_pricing_status=(
                        delivery_pricing_status
                    ),
''',
    1,
)


# ============================================================
# 7. CREATE DELIVERY RECORD WITH ORDER
# ============================================================

if (
    "Delivery.objects.create("
    not in view_text
):

    marker = '''                for item in items:
                    inventory = item.variant.__class__.objects.select_for_update().get(id=item.variant_id) if item.variant else Product.objects.select_for_update().get(id=item.product_id)
'''

    delivery_creation = r'''
                # -------------------------------------------------
                # CREATE DELIVERY RECORD
                # -------------------------------------------------

                internal_provider_types = {
                    "personal_rider",
                    "shop_fleet",
                }

                if (
                    delivery_zone.method
                    == "store_pickup"
                ):

                    management_type = "internal"

                elif (
                    delivery_zone.provider
                    and
                    delivery_zone.provider.provider_type
                    in internal_provider_types
                ):

                    management_type = "internal"

                else:

                    management_type = "external"

                destination_parts = [
                    form.cleaned_data[
                        "house_number"
                    ],
                    form.cleaned_data[
                        "estate"
                    ],
                    form.cleaned_data[
                        "city"
                    ],
                    form.cleaned_data[
                        "county"
                    ],
                ]

                destination = ", ".join(
                    part.strip()
                    for part in destination_parts
                    if part
                )

                Delivery.objects.create(
                    order=order,

                    management_type=(
                        management_type
                    ),

                    method=(
                        delivery_zone.method
                    ),

                    provider=(
                        delivery_zone.provider
                    ),

                    status="pending",

                    destination=destination,

                    pickup_point=(
                        delivery_zone.pickup_point
                    ),

                    customer_delivery_fee=(
                        shipping_cost
                    ),

                    notes=(
                        delivery_zone.instructions
                    ),
                )


'''

    if marker not in view_text:

        raise RuntimeError(
            "Could not locate inventory reservation "
            "section."
        )

    view_text = view_text.replace(
        marker,
        delivery_creation + marker,
        1,
    )


# ============================================================
# 8. REPLACE DELIVERY CONTEXT
# ============================================================

view_text = view_text.replace(
    '"delivery_areas": delivery_areas,',
    '"delivery_zones": delivery_zones,',
)

ORDER_VIEWS.write_text(
    view_text,
    encoding="utf-8",
)

print(
    "Checkout now calculates delivery server-side."
)


# ============================================================
# 9. CUSTOMER CHECKOUT TEMPLATE
# ============================================================

checkout = CHECKOUT_TEMPLATE.read_text(
    encoding="utf-8-sig"
)


# ------------------------------------------------------------
# County selector -> flexible field
# ------------------------------------------------------------

county_pattern = re.compile(
    r'''
    <div\s+class="col-md-6\s+mb-3">
        \s*
        <label\s+class="form-label">
            County
        </label>
        \s*
        <select
            \s+name="county"
            .*?
        </select>
        \s*
    </div>
    ''',
    re.S | re.X,
)

county_replacement = r'''
                            <div class="col-md-6 mb-3">

                                <label class="form-label">
                                    County
                                </label>

                                <input
                                    type="text"
                                    name="county"
                                    id="checkout-county"
                                    class="form-control"
                                    value="{{ form.county.value|default:'' }}"
                                    placeholder="e.g. Nairobi"
                                    required
                                >

                            </div>
'''

checkout, count = county_pattern.subn(
    county_replacement,
    checkout,
    count=1,
)

if count == 0:

    print(
        "County block was not replaced "
        "(may already be updated)."
    )


# ------------------------------------------------------------
# Add ID to city
# ------------------------------------------------------------

checkout = checkout.replace(
    '''name="city" class="form-control"''',
    '''name="city" id="checkout-city" class="form-control"''',
    1,
)


# ------------------------------------------------------------
# Replace old Estate/Area delivery dropdown
# ------------------------------------------------------------

old_delivery_pattern = re.compile(
    r'''
    <div\s+class="mb-3">
        \s*
        <label\s+class="form-label">
            Estate\s*/\s*Area
        </label>
        .*?
    </div>
    ''',
    re.S | re.X,
)


new_delivery_block = r'''
                        <div class="mb-3">

                            <label class="form-label">
                                Estate / Area
                            </label>

                            <input
                                type="text"
                                name="estate"
                                class="form-control"
                                value="{{ form.estate.value|default:'' }}"
                                placeholder="e.g. Kilimani, Westlands, Rongo Town"
                                required
                            >

                        </div>


                        <div class="mb-3">

                            <label class="form-label">
                                Delivery Option
                            </label>

                            <select
                                name="delivery_zone"
                                id="delivery-zone"
                                class="form-select"
                                required
                            >

                                <option value="">
                                    Select delivery option
                                </option>

                                {% for zone in delivery_zones %}

                                    <option
                                        value="{{ zone.id }}"
                                        data-county="{{ zone.county }}"
                                        data-town="{{ zone.town }}"
                                        data-fee="{{ zone.fee }}"
                                        data-pricing="{{ zone.pricing_mode }}"
                                        data-method="{{ zone.get_method_display }}"
                                        data-provider="{% if zone.provider %}{{ zone.provider.name }}{% endif %}"
                                        data-pickup="{{ zone.pickup_point }}"
                                    >

                                        {{ zone.county }}

                                        {% if zone.town %}
                                            - {{ zone.town }}
                                        {% endif %}

                                        · {{ zone.get_method_display }}

                                        {% if zone.provider %}
                                            · {{ zone.provider.name }}
                                        {% endif %}

                                        {% if zone.pricing_mode == "fixed" %}

                                            · KES {{ zone.fee }}

                                        {% else %}

                                            · Fee confirmed later

                                        {% endif %}

                                    </option>

                                {% endfor %}

                            </select>


                            <div
                                id="delivery-option-info"
                                class="
                                    alert
                                    alert-light
                                    border
                                    mt-3
                                    mb-0
                                    d-none
                                "
                            ></div>


                            {% if form.delivery_zone.errors %}

                                <div class="text-danger small mt-1">

                                    {% for error in form.delivery_zone.errors %}

                                        {{ error }}

                                    {% endfor %}

                                </div>

                            {% endif %}

                        </div>
'''


checkout, count = old_delivery_pattern.subn(
    new_delivery_block,
    checkout,
    count=1,
)

if count == 0 and 'id="delivery-zone"' not in checkout:

    raise RuntimeError(
        "Could not replace the old delivery area dropdown."
    )


# ------------------------------------------------------------
# Delivery fee display
# ------------------------------------------------------------

checkout = checkout.replace(
    '''<strong>KES <span id="delivery-fee">0</span></strong>''',
    '''<strong id="delivery-fee-wrap">
                            KES <span id="delivery-fee">0.00</span>
                        </strong>''',
    1,
)


# ------------------------------------------------------------
# JS delivery zone
# ------------------------------------------------------------

checkout = checkout.replace(
    '''const areaSelect = document.getElementById("delivery-area");''',
    '''const zoneSelect = document.getElementById("delivery-zone");
    const countyInput = document.getElementById("checkout-county");
    const cityInput = document.getElementById("checkout-city");
    const deliveryInfo = document.getElementById("delivery-option-info");
    const deliveryFeeWrap = document.getElementById("delivery-fee-wrap");''',
    1,
)


old_listener = re.compile(
    r'''
    if\s*\(areaSelect\)\s*\{
        .*?
    \}
    \s*
    const\s+applyCouponBtn
    ''',
    re.S | re.X,
)


new_listener = r'''
    function updateDeliveryOption() {

        if (!zoneSelect) {
            return;
        }

        const selected = (
            zoneSelect.options[
                zoneSelect.selectedIndex
            ]
        );

        if (
            !selected
            || !selected.value
        ) {

            currentFee = 0;

            feeEl.textContent = "0.00";

            if (deliveryInfo) {
                deliveryInfo.classList.add(
                    "d-none"
                );
            }

            recalcTotal();

            return;
        }


        const pricing = (
            selected.dataset.pricing
            || "fixed"
        );

        const county = (
            selected.dataset.county
            || ""
        );

        const town = (
            selected.dataset.town
            || ""
        );

        const provider = (
            selected.dataset.provider
            || "Shop Delivery"
        );

        const method = (
            selected.dataset.method
            || ""
        );

        const pickup = (
            selected.dataset.pickup
            || ""
        );


        /*
         * Keep checkout location synchronized
         * with the selected delivery zone.
         */
        if (
            countyInput
            && county
        ) {
            countyInput.value = county;
        }

        if (
            cityInput
            && town
        ) {
            cityInput.value = town;
        }


        let info = (
            "<strong>"
            + method
            + "</strong>"
        );

        if (provider) {

            info += (
                "<br>Provider: "
                + provider
            );
        }

        if (pickup) {

            info += (
                "<br>Pickup point: "
                + pickup
            );
        }


        if (pricing === "fixed") {

            currentFee = parseFloat(
                selected.dataset.fee || 0
            );

            feeEl.textContent = (
                currentFee.toFixed(2)
            );

            deliveryFeeWrap.classList.remove(
                "text-warning"
            );

            info += (
                "<br>Delivery fee: "
                + "KES "
                + currentFee.toFixed(2)
            );

        } else {

            currentFee = 0;

            feeEl.textContent = (
                "Pending quote"
            );

            deliveryFeeWrap.classList.add(
                "text-warning"
            );

            info += (
                "<br><strong>"
                + "Delivery fee will be confirmed "
                + "by the shop before M-Pesa payment."
                + "</strong>"
            );
        }


        if (deliveryInfo) {

            deliveryInfo.innerHTML = info;

            deliveryInfo.classList.remove(
                "d-none"
            );
        }

        recalcTotal();
    }


    if (zoneSelect) {

        zoneSelect.addEventListener(
            "change",
            updateDeliveryOption
        );

        updateDeliveryOption();
    }


    const applyCouponBtn
'''


checkout, count = old_listener.subn(
    new_listener,
    checkout,
    count=1,
)

if count == 0:

    raise RuntimeError(
        "Could not replace old delivery JavaScript."
    )


CHECKOUT_TEMPLATE.write_text(
    checkout,
    encoding="utf-8",
)

print(
    "Checkout UI now uses Delivery Zones."
)


# ============================================================
# 10. ORDER CONFIRMATION QUOTE-PENDING UX
# ============================================================

confirm = CONFIRM_TEMPLATE.read_text(
    encoding="utf-8-sig"
)


confirm = confirm.replace(
    '''                        <div class="d-flex justify-content-between mb-2">
                            <span>Delivery Fee</span>
                            <span>KES {{ order.shipping_cost }}</span>
                        </div>''',
    '''                        <div class="d-flex justify-content-between mb-2">

                            <span>
                                Delivery Fee
                            </span>

                            <span>

                                {% if order.delivery_pricing_status == "quote_pending" %}

                                    <strong class="text-warning">
                                        Awaiting Quote
                                    </strong>

                                {% else %}

                                    KES {{ order.shipping_cost }}

                                {% endif %}

                            </span>

                        </div>''',
    1,
)


confirm = confirm.replace(
    '''                    {% if order.payment_status == "pending" %}
                    <a href="{% url 'initiate_payment' order.order_number %}" class="btn btn-success">
                        Pay with M-PESA
                    </a>
                    {% else %}''',
    '''                    {% if order.delivery_pricing_status == "quote_pending" %}

                    <div class="alert alert-warning text-start">

                        <strong>
                            Delivery quotation pending.
                        </strong>

                        <div class="mt-1">

                            The shop will confirm the final
                            delivery charge before you pay.

                        </div>

                    </div>

                    <a
                        href="{% url 'order_detail' order.order_number %}"
                        class="btn btn-outline-primary"
                    >
                        View Order
                    </a>

                    {% elif order.payment_status == "pending" %}

                    <a
                        href="{% url 'initiate_payment' order.order_number %}"
                        class="btn btn-success"
                    >
                        Pay with M-PESA
                    </a>

                    {% else %}''',
    1,
)


CONFIRM_TEMPLATE.write_text(
    confirm,
    encoding="utf-8",
)

print(
    "Order confirmation handles pending quotes."
)


# ============================================================
# 11. BLOCK M-PESA UNTIL DELIVERY QUOTE EXISTS
# ============================================================

payment_text = PAYMENT_VIEWS.read_text(
    encoding="utf-8-sig"
)


# GET guard
get_marker = '''        return render(
            request,
            "payments/pay.html",
            {
                "order": order,
            },
        )
'''

get_replacement = '''        return render(
            request,
            "payments/pay.html",
            {
                "order": order,
                "delivery_quote_pending": (
                    order.delivery_pricing_status
                    == "quote_pending"
                ),
            },
        )
'''

if get_marker in payment_text:

    payment_text = payment_text.replace(
        get_marker,
        get_replacement,
        1,
    )


# POST guard
if (
    "Delivery price has not been confirmed yet."
    not in payment_text
):

    marker = '''        if order.payment_status == "paid":
'''

    guard = '''        if (
            order.delivery_pricing_status
            == "quote_pending"
        ):

            return JsonResponse(
                {
                    "success": False,
                    "error": (
                        "Delivery price has not been "
                        "confirmed yet. Please wait for "
                        "the shop to provide the final "
                        "delivery quote."
                    ),
                },
                status=409,
            )

'''

    if marker not in payment_text:

        raise RuntimeError(
            "Could not locate payment status guard."
        )

    payment_text = payment_text.replace(
        marker,
        guard + marker,
        1,
    )


PAYMENT_VIEWS.write_text(
    payment_text,
    encoding="utf-8",
)

print(
    "M-Pesa now blocks quote-pending orders."
)


# ============================================================
# 12. PAYMENT TEMPLATE UX
# ============================================================

pay = PAY_TEMPLATE.read_text(
    encoding="utf-8-sig"
)

if (
    "delivery_quote_pending"
    not in pay
):

    old = '''                    <button id="pay-btn" class="btn btn-success w-100">
                        Pay Now
                    </button>'''

    new = '''                    {% if delivery_quote_pending %}

                    <div class="alert alert-warning text-start">

                        <strong>
                            Delivery quote pending.
                        </strong>

                        <div class="mt-1">

                            M-PESA payment will become
                            available after the shop confirms
                            your final delivery cost.

                        </div>

                    </div>

                    <a
                        href="{% url 'order_detail' order.order_number %}"
                        class="btn btn-outline-primary w-100"
                    >
                        Back to Order
                    </a>

                    {% else %}

                    <button
                        id="pay-btn"
                        class="btn btn-success w-100"
                    >
                        Pay Now
                    </button>

                    {% endif %}'''

    if old not in pay:

        raise RuntimeError(
            "Could not locate Pay Now button."
        )

    pay = pay.replace(
        old,
        new,
        1,
    )


    # Prevent JavaScript error when Pay button doesn't exist.
    pay = pay.replace(
        '''    payBtn.addEventListener("click", function () {''',
        '''    if (payBtn) {

    payBtn.addEventListener("click", function () {''',
        1,
    )

    pay = pay.replace(
        '''    function pollStatus() {''',
        '''    }

    function pollStatus() {''',
        1,
    )


PAY_TEMPLATE.write_text(
    pay,
    encoding="utf-8",
)

print(
    "Payment page handles delivery quotes."
)


# ============================================================
# 13. ADMIN QUOTE ENDPOINT
# ============================================================

delivery_views = DELIVERY_VIEWS.read_text(
    encoding="utf-8-sig"
)


if (
    "from decimal import Decimal, InvalidOperation"
    not in delivery_views
):

    delivery_views = (
        "from decimal import Decimal, InvalidOperation\n"
        + delivery_views
    )


if (
    "from django.db import transaction"
    not in delivery_views
):

    import_marker = '''from django.db.models import Q
'''

    delivery_views = delivery_views.replace(
        import_marker,
        '''from django.db import transaction
from django.db.models import Q
''',
        1,
    )


if "def delivery_set_quote(" not in delivery_views:

    delivery_views += r'''


# ============================================================
# DELIVERY QUOTE
# ============================================================

@staff_member_required
@transaction.atomic
def delivery_set_quote(
    request,
    pk,
):

    delivery = get_object_or_404(
        Delivery.objects
        .select_for_update()
        .select_related(
            "order",
            "provider",
        ),
        pk=pk,
    )

    if request.method != "POST":

        return redirect(
            "delivery_detail",
            pk=delivery.pk,
        )


    order = (
        Order.objects
        .select_for_update()
        .get(
            pk=delivery.order_id
        )
    )


    if (
        order.payment_status
        == "paid"
    ):

        messages.error(
            request,
            (
                "Delivery price cannot be changed "
                "after payment."
            ),
        )

        return redirect(
            "delivery_detail",
            pk=delivery.pk,
        )


    if (
        order.delivery_pricing_status
        != "quote_pending"
    ):

        messages.error(
            request,
            (
                "This order is not waiting "
                "for a delivery quote."
            ),
        )

        return redirect(
            "delivery_detail",
            pk=delivery.pk,
        )


    raw_amount = request.POST.get(
        "delivery_fee",
        "",
    ).strip()


    try:

        amount = Decimal(
            raw_amount
        ).quantize(
            Decimal("0.01")
        )

    except (
        InvalidOperation,
        ValueError,
    ):

        messages.error(
            request,
            "Enter a valid delivery fee.",
        )

        return redirect(
            "delivery_detail",
            pk=delivery.pk,
        )


    if amount < 0:

        messages.error(
            request,
            (
                "Delivery fee cannot be negative."
            ),
        )

        return redirect(
            "delivery_detail",
            pk=delivery.pk,
        )


    order.shipping_cost = amount

    order.total_amount = (
        order.subtotal
        + amount
        - order.discount
    )

    order.delivery_pricing_status = (
        "quoted"
    )

    order.save(
        update_fields=[
            "shipping_cost",
            "total_amount",
            "delivery_pricing_status",
            "updated_at",
        ]
    )


    delivery.customer_delivery_fee = (
        amount
    )

    delivery.save(
        update_fields=[
            "customer_delivery_fee",
            "updated_at",
        ]
    )


    DeliveryEvent.objects.create(
        delivery=delivery,
        status=delivery.status,
        message=(
            f"Delivery fee confirmed at "
            f"KES {amount:.2f}."
        ),
        created_by=request.user,
    )


    messages.success(
        request,
        (
            f"Delivery quote confirmed: "
            f"KES {amount:.2f}. "
            f"The customer can now pay."
        ),
    )


    return redirect(
        "delivery_detail",
        pk=delivery.pk,
    )
'''


DELIVERY_VIEWS.write_text(
    delivery_views,
    encoding="utf-8",
)

print(
    "Added admin delivery quote workflow."
)


# ============================================================
# 14. DELIVERY QUOTE URL
# ============================================================

urls = DELIVERY_URLS.read_text(
    encoding="utf-8-sig"
)

if "delivery_set_quote" not in urls:

    marker = '''urlpatterns = [
'''

    route = '''

    path(
        "<int:pk>/quote/",
        views.delivery_set_quote,
        name="delivery_set_quote",
    ),
'''

    urls = urls.replace(
        marker,
        marker + route,
        1,
    )


DELIVERY_URLS.write_text(
    urls,
    encoding="utf-8",
)


# ============================================================
# 15. ADMIN DELIVERY DETAIL QUOTE CARD
# ============================================================

detail = DELIVERY_DETAIL.read_text(
    encoding="utf-8-sig"
)

if (
    "delivery_set_quote"
    not in detail
):

    marker = '''<div class="row g-3 mb-4">'''

    quote_card = r'''
{% if order.delivery_pricing_status == "quote_pending" %}

<div class="alert alert-warning">

    <div
        class="
            d-flex
            justify-content-between
            align-items-start
            flex-wrap
            gap-3
        "
    >

        <div>

            <strong>
                Delivery Quote Required
            </strong>

            <div class="mt-1">

                The customer cannot make the M-PESA
                payment until the final delivery
                charge is confirmed.

            </div>

        </div>


        <form
            method="POST"
            action="{% url 'delivery_set_quote' delivery.pk %}"
            class="
                d-flex
                gap-2
                align-items-center
                flex-wrap
            "
        >

            {% csrf_token %}

            <div class="input-group">

                <span class="input-group-text">
                    KES
                </span>

                <input
                    type="number"
                    name="delivery_fee"
                    min="0"
                    step="0.01"
                    class="form-control"
                    placeholder="e.g. 550"
                    required
                >

                <button
                    type="submit"
                    class="btn btn-warning"
                >
                    Confirm Quote
                </button>

            </div>

        </form>

    </div>

</div>

{% endif %}


'''

    if marker not in detail:

        raise RuntimeError(
            "Could not locate Delivery detail metrics."
        )

    detail = detail.replace(
        marker,
        quote_card + marker,
        1,
    )


DELIVERY_DETAIL.write_text(
    detail,
    encoding="utf-8",
)


# ============================================================
# 16. TESTS
# ============================================================

tests = ROOT / "delivery" / "test_phase7c.py"

tests.write_text(
r'''
from decimal import Decimal

from django.contrib.auth import (
    get_user_model,
)

from django.test import TestCase

from django.urls import reverse

from orders.models import Order

from delivery.models import (
    Delivery,
    DeliveryProvider,
    DeliveryZone,
)


User = get_user_model()


class DeliveryCheckoutIntegrationTests(
    TestCase
):

    def setUp(self):

        self.customer = (
            User.objects.create_user(
                username="phase7ccustomer",
                password="pass12345",
                role=User.CUSTOMER,
            )
        )

        self.staff = (
            User.objects.create_user(
                username="phase7cstaff",
                password="pass12345",
                role=User.ADMIN,
                is_staff=True,
            )
        )

        self.provider = (
            DeliveryProvider.objects.create(
                name="Phase 7C Coach",
                provider_type="bus_coach",
            )
        )

        self.zone = (
            DeliveryZone.objects.create(
                county="Kisii",
                town="Kisii",
                method="station_pickup",
                provider=self.provider,
                pickup_point="Kisii Parcel Office",
                pricing_mode="confirm",
                fee=Decimal("0.00"),
                estimated_time="1 day",
            )
        )

        self.order = Order.objects.create(
            user=self.customer,
            order_number="QUOTE-001",
            full_name="Quote Customer",
            phone="0712345678",
            email="quote@example.com",
            county="Kisii",
            city="Kisii",
            estate="Town",
            house_number="1",
            subtotal=Decimal("3000.00"),
            shipping_cost=Decimal("0.00"),
            discount=Decimal("200.00"),
            total_amount=Decimal("2800.00"),
            delivery_zone=self.zone,
            delivery_pricing_status="quote_pending",
            payment_status="pending",
            inventory_status="reserved",
        )

        self.delivery = (
            Delivery.objects.create(
                order=self.order,
                management_type="external",
                method="station_pickup",
                provider=self.provider,
                status="pending",
                destination="Kisii",
                pickup_point="Kisii Parcel Office",
                customer_delivery_fee=Decimal("0.00"),
            )
        )


    def test_staff_can_confirm_delivery_quote(
        self
    ):

        self.client.login(
            username="phase7cstaff",
            password="pass12345",
        )

        response = self.client.post(
            reverse(
                "delivery_set_quote",
                kwargs={
                    "pk": self.delivery.pk
                },
            ),
            {
                "delivery_fee": "500.00",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.order.refresh_from_db()

        self.delivery.refresh_from_db()

        self.assertEqual(
            self.order.shipping_cost,
            Decimal("500.00"),
        )

        self.assertEqual(
            self.order.total_amount,
            Decimal("3300.00"),
        )

        self.assertEqual(
            self.order.delivery_pricing_status,
            "quoted",
        )

        self.assertEqual(
            self.delivery.customer_delivery_fee,
            Decimal("500.00"),
        )


    def test_customer_cannot_set_delivery_quote(
        self
    ):

        self.client.login(
            username="phase7ccustomer",
            password="pass12345",
        )

        response = self.client.post(
            reverse(
                "delivery_set_quote",
                kwargs={
                    "pk": self.delivery.pk
                },
            ),
            {
                "delivery_fee": "1.00",
            },
        )

        self.assertNotEqual(
            response.status_code,
            200,
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.delivery_pricing_status,
            "quote_pending",
        )
'''.strip() + "\n",
encoding="utf-8"
)


print()
print("=" * 72)
print("PHASE 7C CHECKOUT DELIVERY INTEGRATION COMPLETE")
print("=" * 72)
print()
print("Next commands:")
print("python manage.py makemigrations orders")
print("python manage.py migrate")
print("python manage.py check")
