from pathlib import Path
import re
import shutil

ROOT = Path.cwd()

DELIVERY_MODELS = ROOT / "delivery" / "models.py"
DELIVERY_FORMS = ROOT / "delivery" / "forms.py"
DELIVERY_VIEWS = ROOT / "delivery" / "views.py"
DELIVERY_TASKS = ROOT / "delivery" / "tasks.py"

ORDER_MODELS = ROOT / "orders" / "models.py"
ORDER_VIEWS = ROOT / "orders" / "views.py"

PAYMENT_VIEWS = ROOT / "payments" / "views.py"

CHECKOUT_TEMPLATE = (
    ROOT
    / "templates"
    / "orders"
    / "checkout.html"
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
    DELIVERY_MODELS,
    DELIVERY_FORMS,
    DELIVERY_VIEWS,
    DELIVERY_TASKS,
    ORDER_MODELS,
    ORDER_VIEWS,
    PAYMENT_VIEWS,
    CHECKOUT_TEMPLATE,
    PAY_TEMPLATE,
    DELIVERY_DETAIL,
]:

    if path.exists():

        backup = Path(
            str(path) + ".phase7dbackup"
        )

        if not backup.exists():

            shutil.copy2(
                path,
                backup,
            )


# ============================================================
# 1. HARDEN DELIVERY ZONE MODEL
# ============================================================

text = DELIVERY_MODELS.read_text(
    encoding="utf-8-sig"
)


# ------------------------------------------------------------
# Add free-delivery threshold
# ------------------------------------------------------------

if "free_delivery_threshold" not in text:

    marker = '''    estimated_time = models.CharField(
'''

    addition = '''    free_delivery_threshold = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=(
            "Orders at or above this subtotal receive "
            "free delivery for this zone."
        ),
    )

'''

    if marker not in text:

        raise RuntimeError(
            "Could not locate estimated_time "
            "in DeliveryZone."
        )

    text = text.replace(
        marker,
        addition + marker,
        1,
    )


# ------------------------------------------------------------
# Add model validation
# ------------------------------------------------------------

if "Duplicate delivery zone" not in text:

    marker = '''    def __str__(self):

        location = self.county
'''

    validation = '''    def clean(self):

        from django.core.exceptions import ValidationError

        super().clean()

        self.county = (
            self.county or ""
        ).strip()

        self.town = (
            self.town or ""
        ).strip()

        self.pickup_point = (
            self.pickup_point or ""
        ).strip()

        # Store pickup must never charge delivery.
        if self.method == "store_pickup":

            self.fee = Decimal("0.00")

            self.pricing_mode = "fixed"

        if (
            self.free_delivery_threshold
            is not None
            and self.free_delivery_threshold < 0
        ):

            raise ValidationError(
                {
                    "free_delivery_threshold":
                    (
                        "Free-delivery threshold "
                        "cannot be negative."
                    )
                }
            )

        duplicates = (
            DeliveryZone.objects
            .filter(
                county__iexact=self.county,
                town__iexact=self.town,
                method=self.method,
                provider=self.provider,
                pickup_point__iexact=(
                    self.pickup_point
                ),
            )
        )

        if self.pk:

            duplicates = duplicates.exclude(
                pk=self.pk
            )

        if duplicates.exists():

            raise ValidationError(
                (
                    "Duplicate delivery zone: "
                    "this county, town, method, "
                    "provider and pickup point "
                    "already exist."
                )
            )


    def save(
        self,
        *args,
        **kwargs,
    ):

        self.full_clean()

        return super().save(
            *args,
            **kwargs,
        )


'''

    if marker not in text:

        raise RuntimeError(
            "Could not locate DeliveryZone "
            "__str__ method."
        )

    text = text.replace(
        marker,
        validation + marker,
        1,
    )


DELIVERY_MODELS.write_text(
    text,
    encoding="utf-8",
)

print(
    "DeliveryZone validation hardened."
)


# ============================================================
# 2. FREE DELIVERY THRESHOLD FORM
# ============================================================

forms = DELIVERY_FORMS.read_text(
    encoding="utf-8-sig"
)

if (
    '"free_delivery_threshold"'
    not in forms
):

    forms = forms.replace(
        '''            "fee",
            "estimated_time",''',
        '''            "fee",
            "free_delivery_threshold",
            "estimated_time",''',
        1,
    )

    forms = forms.replace(
        '''            "estimated_time": forms.TextInput(''',
        '''            "free_delivery_threshold": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                    "placeholder": (
                        "Optional, e.g. 5000"
                    ),
                }
            ),

            "estimated_time": forms.TextInput(''',
        1,
    )


# Enforce store-pickup price in form too.
if "Store pickup is always free" not in forms:

    marker = '''        if (
            pricing_mode == "fixed"
            and (
                fee is None
                or fee < 0
            )
        ):
'''

    addition = '''        method = cleaned.get(
            "method"
        )

        if method == "store_pickup":

            cleaned["pricing_mode"] = "fixed"
            cleaned["fee"] = 0

            self.cleaned_data[
                "pricing_mode"
            ] = "fixed"

            self.cleaned_data[
                "fee"
            ] = 0

'''

    if marker in forms:

        forms = forms.replace(
            marker,
            addition + marker,
            1,
        )


DELIVERY_FORMS.write_text(
    forms,
    encoding="utf-8",
)

print(
    "DeliveryZoneForm hardened."
)


# ============================================================
# 3. ORDER QUOTE EXPIRY FIELD
# ============================================================

order_models = ORDER_MODELS.read_text(
    encoding="utf-8-sig"
)

if "delivery_quote_expires_at" not in order_models:

    marker = '''    delivery_pricing_status = models.CharField(
'''

    # Insert after entire pricing field.
    pricing_pattern = re.compile(
        r'''
        \s+delivery_pricing_status\s*=\s*
        models\.CharField\(
        .*?
        \)\n
        ''',
        re.S | re.X,
    )

    match = pricing_pattern.search(
        order_models
    )

    if not match:

        raise RuntimeError(
            "Could not locate "
            "delivery_pricing_status."
        )

    addition = '''

    delivery_quote_expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )
'''

    order_models = (
        order_models[:match.end()]
        + addition
        + order_models[match.end():]
    )


ORDER_MODELS.write_text(
    order_models,
    encoding="utf-8",
)

print(
    "Added delivery quote expiry."
)


# ============================================================
# 4. CHECKOUT: FREE DELIVERY THRESHOLD
# ============================================================

order_views = ORDER_VIEWS.read_text(
    encoding="utf-8-sig"
)


old_fixed = '''                if (
                    delivery_zone.pricing_mode
                    == "fixed"
                ):

                    shipping_cost = (
                        delivery_zone.fee
                    )

                    delivery_pricing_status = (
                        "fixed"
                    )
'''

new_fixed = '''                if (
                    delivery_zone.pricing_mode
                    == "fixed"
                ):

                    if (
                        delivery_zone.free_delivery_threshold
                        is not None
                        and subtotal
                        >= delivery_zone.free_delivery_threshold
                    ):

                        shipping_cost = (
                            Decimal("0.00")
                        )

                    else:

                        shipping_cost = (
                            delivery_zone.fee
                        )

                    delivery_pricing_status = (
                        "fixed"
                    )
'''

if old_fixed in order_views:

    order_views = order_views.replace(
        old_fixed,
        new_fixed,
        1,
    )


ORDER_VIEWS.write_text(
    order_views,
    encoding="utf-8",
)

print(
    "Checkout supports free-delivery thresholds."
)


# ============================================================
# 5. QUOTE EXPIRY + CUSTOMER NOTIFICATION
# ============================================================

delivery_views = DELIVERY_VIEWS.read_text(
    encoding="utf-8-sig"
)


if (
    "from datetime import timedelta"
    not in delivery_views
):

    delivery_views = (
        "from datetime import timedelta\n"
        + delivery_views
    )


if (
    "from django.utils import timezone"
    not in delivery_views
):

    marker = '''from django.shortcuts import (
'''

    delivery_views = delivery_views.replace(
        marker,
        '''from django.utils import timezone

''' + marker,
        1,
    )


# Save 24-hour quote expiry.
old_save = '''    order.delivery_pricing_status = (
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
'''

new_save = '''    order.delivery_pricing_status = (
        "quoted"
    )

    order.delivery_quote_expires_at = (
        timezone.now()
        + timedelta(hours=24)
    )

    order.save(
        update_fields=[
            "shipping_cost",
            "total_amount",
            "delivery_pricing_status",
            "delivery_quote_expires_at",
            "updated_at",
        ]
    )
'''

if old_save in delivery_views:

    delivery_views = delivery_views.replace(
        old_save,
        new_save,
        1,
    )


# Queue customer notification.
if (
    "send_delivery_quote_update"
    not in delivery_views
):

    marker = '''    messages.success(
        request,
        (
            f"Delivery quote confirmed: "
'''

    notification = '''    try:

        from .tasks import (
            send_delivery_quote_update,
        )

        transaction.on_commit(
            lambda order_id=order.pk: (
                send_delivery_quote_update.delay(
                    order_id
                )
            ),
            robust=True,
        )

    except Exception:

        pass


'''

    if marker in delivery_views:

        delivery_views = delivery_views.replace(
            marker,
            notification + marker,
            1,
        )


DELIVERY_VIEWS.write_text(
    delivery_views,
    encoding="utf-8",
)

print(
    "Delivery quotes now expire after 24 hours."
)


# ============================================================
# 6. QUOTE NOTIFICATION TASK
# ============================================================

tasks = DELIVERY_TASKS.read_text(
    encoding="utf-8-sig"
)


if "def send_delivery_quote_update(" not in tasks:

    tasks += r'''


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={
        "max_retries": 3
    },
)
def send_delivery_quote_update(
    self,
    order_id,
):

    from notifications.tasks import (
        _send_order_notifications,
    )

    from orders.models import Order

    order = (
        Order.objects
        .select_related(
            "user",
            "delivery_zone",
        )
        .get(
            pk=order_id
        )
    )

    sms = (
        f"Order {order.order_number}: "
        f"delivery fee confirmed at "
        f"KES {order.shipping_cost:.2f}. "
        f"Total payable is "
        f"KES {order.total_amount:.2f}. "
        f"Please complete M-PESA payment."
    )

    email_message = (
        f"Hi {order.full_name},\n\n"
        f"Your delivery charge for order "
        f"{order.order_number} has been confirmed.\n\n"
        f"Delivery: KES "
        f"{order.shipping_cost:.2f}\n"
        f"Total payable: KES "
        f"{order.total_amount:.2f}\n\n"
        f"The quote is valid for 24 hours.\n\n"
        f"Please sign in to complete "
        f"your M-PESA payment."
    )

    _send_order_notifications(
        order,
        sms,
        "Your delivery quote is ready",
        email_message,
    )
'''

    DELIVERY_TASKS.write_text(
        tasks,
        encoding="utf-8",
    )

    print(
        "Added delivery quote notification."
    )


# ============================================================
# 7. PAYMENT: BLOCK EXPIRED QUOTES
# ============================================================

payment_views = PAYMENT_VIEWS.read_text(
    encoding="utf-8-sig"
)


if (
    "from django.utils import timezone"
    not in payment_views
):

    payment_views = (
        "from django.utils import timezone\n"
        + payment_views
    )


if "Delivery quote has expired" not in payment_views:

    marker = '''        if (
            order.delivery_pricing_status
            == "quote_pending"
        ):
'''

    expiry_guard = '''        if (
            order.delivery_pricing_status
            == "quoted"
            and order.delivery_quote_expires_at
            and order.delivery_quote_expires_at
            <= timezone.now()
        ):

            return JsonResponse(
                {
                    "success": False,
                    "error": (
                        "Delivery quote has expired. "
                        "Please wait for the shop "
                        "to confirm a new delivery price."
                    ),
                },
                status=409,
            )


'''

    if marker not in payment_views:

        raise RuntimeError(
            "Could not locate payment "
            "delivery quote guard."
        )

    payment_views = payment_views.replace(
        marker,
        expiry_guard + marker,
        1,
    )


# Add GET context for expiry.
payment_views = payment_views.replace(
    '''                "delivery_quote_pending": (
                    order.delivery_pricing_status
                    == "quote_pending"
                ),''',
    '''                "delivery_quote_pending": (
                    order.delivery_pricing_status
                    == "quote_pending"
                ),

                "delivery_quote_expired": (
                    order.delivery_pricing_status
                    == "quoted"
                    and
                    order.delivery_quote_expires_at
                    and
                    order.delivery_quote_expires_at
                    <= timezone.now()
                ),''',
    1,
)


PAYMENT_VIEWS.write_text(
    payment_views,
    encoding="utf-8",
)

print(
    "Expired delivery quotes cannot be paid."
)


# ============================================================
# 8. PAYMENT PAGE EXPIRED QUOTE UX
# ============================================================

pay = PAY_TEMPLATE.read_text(
    encoding="utf-8-sig"
)


if (
    "delivery_quote_expired"
    not in pay
):

    marker = '''                    {% if delivery_quote_pending %}'''

    replacement = '''                    {% if delivery_quote_expired %}

                    <div class="alert alert-danger text-start">

                        <strong>
                            Delivery quote expired.
                        </strong>

                        <div class="mt-1">

                            The delivery price must be
                            reconfirmed before M-PESA payment.

                        </div>

                    </div>

                    <a
                        href="{% url 'order_detail' order.order_number %}"
                        class="btn btn-outline-primary w-100"
                    >
                        Back to Order
                    </a>

                    {% elif delivery_quote_pending %}'''

    if marker not in pay:

        raise RuntimeError(
            "Could not locate payment quote block."
        )

    pay = pay.replace(
        marker,
        replacement,
        1,
    )


PAY_TEMPLATE.write_text(
    pay,
    encoding="utf-8",
)


# ============================================================
# 9. DELIVERY ZONE FORM TEMPLATE
# ============================================================

zone_form = (
    ROOT
    / "delivery"
    / "templates"
    / "dashboard"
    / "admin"
    / "delivery"
    / "zone_form.html"
)

zone_html = zone_form.read_text(
    encoding="utf-8-sig"
)


if "Free Delivery Threshold" not in zone_html:

    marker = '''            <div class="col-md-6">

                <label class="form-label">
                    Estimated Time
                </label>

                {{ form.estimated_time }}

            </div>'''

    addition = '''            <div class="col-md-6">

                <label class="form-label">
                    Free Delivery Threshold
                </label>

                {{ form.free_delivery_threshold }}

                <div class="form-text">

                    Optional. Example: enter 5000
                    to make delivery free when the
                    order subtotal reaches KES 5,000.

                </div>

            </div>


'''

    if marker not in zone_html:

        raise RuntimeError(
            "Could not locate Estimated Time "
            "field."
        )

    zone_html = zone_html.replace(
        marker,
        addition + marker,
        1,
    )


zone_form.write_text(
    zone_html,
    encoding="utf-8",
)


# ============================================================
# 10. CHECKOUT DELIVERY FILTERING
# ============================================================

checkout = CHECKOUT_TEMPLATE.read_text(
    encoding="utf-8-sig"
)


# Add free threshold metadata.
checkout = checkout.replace(
    '''data-fee="{{ zone.fee }}"
                                        data-pricing="{{ zone.pricing_mode }}"''',
    '''data-fee="{{ zone.fee }}"
                                        data-free-threshold="{% if zone.free_delivery_threshold %}{{ zone.free_delivery_threshold }}{% endif %}"
                                        data-pricing="{{ zone.pricing_mode }}"''',
    1,
)


# Add subtotal to JS.
if "checkoutSubtotal" not in checkout:

    checkout = checkout.replace(
        '''let currentFee = 0;''',
        '''let currentFee = 0;

    const checkoutSubtotal = parseFloat(
        "{{ subtotal|default:'0' }}"
    ) || 0;''',
        1,
    )


# Replace fixed fee calculation.
old = '''            currentFee = parseFloat(
                selected.dataset.fee || 0
            );

            feeEl.textContent = (
                currentFee.toFixed(2)
            );'''

new = '''            const normalFee = parseFloat(
                selected.dataset.fee || 0
            );

            const threshold = parseFloat(
                selected.dataset.freeThreshold || 0
            );

            if (
                threshold > 0
                && checkoutSubtotal >= threshold
            ) {

                currentFee = 0;

                feeEl.textContent = "0.00";

                info += (
                    "<br><strong>"
                    + "Free delivery applied."
                    + "</strong>"
                );

            } else {

                currentFee = normalFee;

                feeEl.textContent = (
                    currentFee.toFixed(2)
                );
            }'''

if old in checkout:

    checkout = checkout.replace(
        old,
        new,
        1,
    )


# Add county/town option filtering.
if "filterDeliveryZones" not in checkout:

    insertion = r'''

    function filterDeliveryZones() {

        if (
            !zoneSelect
            || !countyInput
        ) {
            return;
        }

        const selectedCounty = (
            countyInput.value || ""
        ).trim().toLowerCase();

        const selectedTown = (
            cityInput
            ? (
                cityInput.value || ""
            ).trim().toLowerCase()
            : ""
        );


        Array.from(
            zoneSelect.options
        ).forEach(
            function(option) {

                if (!option.value) {
                    return;
                }

                const county = (
                    option.dataset.county
                    || ""
                ).trim().toLowerCase();

                const town = (
                    option.dataset.town
                    || ""
                ).trim().toLowerCase();


                const countyMatch = (
                    !selectedCounty
                    || county === selectedCounty
                );

                const townMatch = (
                    !selectedTown
                    || !town
                    || town === selectedTown
                );


                option.hidden = !(
                    countyMatch
                    && townMatch
                );
            }
        );


        const selected = (
            zoneSelect.options[
                zoneSelect.selectedIndex
            ]
        );

        if (
            selected
            && selected.value
            && selected.hidden
        ) {

            zoneSelect.value = "";

            updateDeliveryOption();
        }
    }


    if (countyInput) {

        countyInput.addEventListener(
            "input",
            filterDeliveryZones
        );
    }


    if (cityInput) {

        cityInput.addEventListener(
            "input",
            filterDeliveryZones
        );
    }


'''

    marker = '''    function updateDeliveryOption() {'''

    if marker not in checkout:

        raise RuntimeError(
            "Could not locate delivery JS."
        )

    checkout = checkout.replace(
        marker,
        insertion + marker,
        1,
    )


# Run filter on initial load.
checkout = checkout.replace(
    '''        updateDeliveryOption();
    }''',
    '''        filterDeliveryZones();
        updateDeliveryOption();
    }''',
    1,
)


CHECKOUT_TEMPLATE.write_text(
    checkout,
    encoding="utf-8",
)

print(
    "Checkout zone filtering hardened."
)


# ============================================================
# 11. ADMIN DELIVERY DETAIL: QUOTE EXPIRY
# ============================================================

detail = DELIVERY_DETAIL.read_text(
    encoding="utf-8-sig"
)


if "Quote valid until" not in detail:

    marker = '''{% if order.delivery_pricing_status == "quote_pending" %}'''

    quote_status = r'''
{% if order.delivery_pricing_status == "quoted" and order.delivery_quote_expires_at %}

<div class="alert alert-info">

    <strong>
        Delivery quote confirmed.
    </strong>

    <div class="mt-1">

        Delivery fee:
        <strong>
            KES {{ order.shipping_cost|floatformat:2 }}
        </strong>

        <br>

        Quote valid until:
        <strong>
            {{ order.delivery_quote_expires_at|date:"d M Y H:i" }}
        </strong>

    </div>

</div>

{% endif %}


'''

    detail = detail.replace(
        marker,
        quote_status + marker,
        1,
    )


DELIVERY_DETAIL.write_text(
    detail,
    encoding="utf-8",
)


# ============================================================
# 12. TESTS
# ============================================================

tests = (
    ROOT
    / "delivery"
    / "test_phase7d.py"
)


tests.write_text(
r'''
from decimal import Decimal

from django.core.exceptions import (
    ValidationError,
)

from django.test import TestCase

from delivery.models import (
    DeliveryProvider,
    DeliveryZone,
)


class DeliveryZoneHardeningTests(
    TestCase
):

    def setUp(self):

        self.provider = (
            DeliveryProvider.objects.create(
                name="Phase7D Provider",
                provider_type="bus_coach",
            )
        )


    def test_store_pickup_is_free(self):

        zone = DeliveryZone.objects.create(
            county="Nairobi",
            town="Nairobi",
            method="store_pickup",
            pricing_mode="confirm",
            fee=Decimal("500.00"),
        )

        self.assertEqual(
            zone.fee,
            Decimal("0.00"),
        )

        self.assertEqual(
            zone.pricing_mode,
            "fixed",
        )


    def test_duplicate_zone_rejected(self):

        DeliveryZone.objects.create(
            county="Kisii",
            town="Kisii",
            method="station_pickup",
            provider=self.provider,
            pickup_point="Main Office",
            pricing_mode="fixed",
            fee=Decimal("500.00"),
        )

        duplicate = DeliveryZone(
            county="kisii",
            town="kisii",
            method="station_pickup",
            provider=self.provider,
            pickup_point="main office",
            pricing_mode="fixed",
            fee=Decimal("550.00"),
        )

        with self.assertRaises(
            ValidationError
        ):

            duplicate.save()


    def test_negative_free_threshold_rejected(
        self
    ):

        zone = DeliveryZone(
            county="Migori",
            town="Rongo",
            method="local_door",
            pricing_mode="fixed",
            fee=Decimal("300.00"),
            free_delivery_threshold=(
                Decimal("-1.00")
            ),
        )

        with self.assertRaises(
            ValidationError
        ):

            zone.save()
'''.strip() + "\n",
encoding="utf-8"
)


print()
print("=" * 72)
print("PHASE 7D DELIVERY HARDENING COMPLETE")
print("=" * 72)
print()
print("Next:")
print("python manage.py makemigrations delivery orders")
print("python manage.py migrate")
print("python manage.py check")
