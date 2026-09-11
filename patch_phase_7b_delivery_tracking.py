from pathlib import Path
import re
import shutil

ROOT = Path.cwd()

DELIVERY = ROOT / "delivery"

MODELS = DELIVERY / "models.py"
FORMS = DELIVERY / "forms.py"
VIEWS = DELIVERY / "views.py"
URLS = DELIVERY / "urls.py"
ADMIN = DELIVERY / "admin.py"
SERVICES = DELIVERY / "services.py"

DASHBOARD_URLS = ROOT / "dashboard" / "urls.py"

ADMIN_ORDER_TEMPLATE = (
    ROOT
    / "templates"
    / "dashboard"
    / "admin"
    / "orders"
    / "detail.html"
)

CUSTOMER_ORDER_TEMPLATE = (
    ROOT
    / "templates"
    / "dashboard"
    / "order_detail.html"
)

DELIVERY_TEMPLATES = (
    DELIVERY
    / "templates"
)

ADMIN_DELIVERY_TEMPLATES = (
    DELIVERY_TEMPLATES
    / "dashboard"
    / "admin"
    / "delivery"
)

CUSTOMER_DELIVERY_TEMPLATES = (
    DELIVERY_TEMPLATES
    / "delivery"
)

ADMIN_DELIVERY_TEMPLATES.mkdir(
    parents=True,
    exist_ok=True,
)

CUSTOMER_DELIVERY_TEMPLATES.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# BACKUPS
# ============================================================

for path in [
    MODELS,
    FORMS,
    VIEWS,
    URLS,
    ADMIN,
    SERVICES,
    DASHBOARD_URLS,
    ADMIN_ORDER_TEMPLATE,
    CUSTOMER_ORDER_TEMPLATE,
]:

    if path.exists():

        backup = Path(
            str(path) + ".phase7bbackup"
        )

        if not backup.exists():

            shutil.copy2(
                path,
                backup,
            )


# ============================================================
# 1. DELIVERY ZONE MODEL
# ============================================================

models_text = MODELS.read_text(
    encoding="utf-8-sig"
)

if "class DeliveryZone(" not in models_text:

    marker = "class Delivery(models.Model):"

    if marker not in models_text:

        raise RuntimeError(
            "Could not locate Delivery model."
        )

    zone_model = r'''

class DeliveryZone(models.Model):

    PRICING_CHOICES = [
        ("fixed", "Fixed Delivery Fee"),
        ("confirm", "Fee Confirmed After Order"),
    ]

    METHOD_CHOICES = [
        ("local_door", "Local Door Delivery"),
        ("long_distance", "Long Distance Delivery"),
        ("station_pickup", "Station / Parcel Office Pickup"),
        ("store_pickup", "Store Pickup"),
        ("personal_rider", "Personal Rider / Bike"),
        ("other", "Other"),
    ]

    county = models.CharField(
        max_length=100,
        db_index=True,
    )

    town = models.CharField(
        max_length=150,
        blank=True,
        db_index=True,
    )

    method = models.CharField(
        max_length=30,
        choices=METHOD_CHOICES,
        default="local_door",
    )

    provider = models.ForeignKey(
        DeliveryProvider,
        on_delete=models.SET_NULL,
        related_name="zones",
        null=True,
        blank=True,
    )

    pickup_point = models.CharField(
        max_length=255,
        blank=True,
    )

    pricing_mode = models.CharField(
        max_length=20,
        choices=PRICING_CHOICES,
        default="fixed",
    )

    fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    estimated_time = models.CharField(
        max_length=120,
        blank=True,
        help_text=(
            "Example: Same day, 1-2 days, "
            "Next day."
        ),
    )

    instructions = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "county",
            "town",
            "method",
        ]

    def __str__(self):

        location = self.county

        if self.town:
            location += f" / {self.town}"

        return (
            f"{location} - "
            f"{self.get_method_display()}"
        )


'''

    models_text = models_text.replace(
        marker,
        zone_model + marker,
        1,
    )

    MODELS.write_text(
        models_text,
        encoding="utf-8",
    )

    print(
        "Added DeliveryZone model."
    )
else:

    print(
        "DeliveryZone model already exists."
    )


# ============================================================
# 2. DELIVERY ZONE FORM
# ============================================================

forms_text = FORMS.read_text(
    encoding="utf-8-sig"
)

forms_text = forms_text.replace(
    "DeliveryProvider,\n)",
    "DeliveryProvider,\n    DeliveryZone,\n)",
)

if "class DeliveryZoneForm" not in forms_text:

    forms_text += r'''


class DeliveryZoneForm(forms.ModelForm):

    class Meta:

        model = DeliveryZone

        fields = [
            "county",
            "town",
            "method",
            "provider",
            "pickup_point",
            "pricing_mode",
            "fee",
            "estimated_time",
            "instructions",
            "is_active",
        ]

        widgets = {

            "county": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Nairobi",
                }
            ),

            "town": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "e.g. Kilimani, Kisii Town, Rongo"
                    ),
                }
            ),

            "method": forms.Select(
                attrs={
                    "class": "form-select"
                }
            ),

            "provider": forms.Select(
                attrs={
                    "class": "form-select"
                }
            ),

            "pickup_point": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Optional station / parcel office"
                    ),
                }
            ),

            "pricing_mode": forms.Select(
                attrs={
                    "class": "form-select"
                }
            ),

            "fee": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                }
            ),

            "estimated_time": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "e.g. Same day / 1-2 days"
                    ),
                }
            ),

            "instructions": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),

            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input"
                }
            ),
        }

    def __init__(
        self,
        *args,
        **kwargs,
    ):

        super().__init__(
            *args,
            **kwargs,
        )

        self.fields[
            "provider"
        ].queryset = (
            DeliveryProvider.objects
            .filter(is_active=True)
            .order_by("name")
        )

    def clean(self):

        cleaned = super().clean()

        pricing_mode = cleaned.get(
            "pricing_mode"
        )

        fee = cleaned.get(
            "fee"
        )

        if (
            pricing_mode == "fixed"
            and (
                fee is None
                or fee < 0
            )
        ):

            self.add_error(
                "fee",
                "Enter a valid delivery fee.",
            )

        return cleaned
'''

    FORMS.write_text(
        forms_text,
        encoding="utf-8",
    )

    print(
        "Added DeliveryZoneForm."
    )


# ============================================================
# 3. CUSTOMER TRACKING VIEW
# ============================================================

customer_views = DELIVERY / "customer_views.py"

customer_views.write_text(
r'''
from django.contrib.auth.decorators import login_required

from django.shortcuts import (
    get_object_or_404,
    render,
)

from orders.models import Order

from .models import (
    Delivery,
    DeliveryZone,
)


@login_required
def customer_delivery_tracking(
    request,
    order_number,
):

    order = get_object_or_404(
        Order.objects.select_related(
            "user"
        ),
        order_number=order_number,
        user=request.user,
    )

    delivery = get_object_or_404(
        Delivery.objects.select_related(
            "provider",
            "order",
        ),
        order=order,
    )

    events = (
        delivery.events
        .select_related(
            "created_by"
        )
        .order_by(
            "created_at"
        )
    )

    return render(
        request,
        "delivery/customer_tracking.html",
        {
            "order": order,
            "delivery": delivery,
            "events": events,
        },
    )


@login_required
def available_delivery_options(
    request,
):

    county = request.GET.get(
        "county",
        "",
    ).strip()

    town = request.GET.get(
        "town",
        "",
    ).strip()

    zones = (
        DeliveryZone.objects
        .filter(
            is_active=True
        )
        .select_related(
            "provider"
        )
    )

    if county:

        zones = zones.filter(
            county__iexact=county
        )

    if town:

        zones = zones.filter(
            town__iexact=town
        )

    return render(
        request,
        "delivery/customer_options.html",
        {
            "zones": zones,
            "county": county,
            "town": town,
        },
    )
'''.strip() + "\n",
encoding="utf-8"
)

print(
    "Created customer delivery views."
)


# ============================================================
# 4. ADD CUSTOMER URLS TO EXISTING DASHBOARD
# ============================================================

dashboard_urls_text = DASHBOARD_URLS.read_text(
    encoding="utf-8-sig"
)

if (
    "customer_delivery_tracking"
    not in dashboard_urls_text
):

    import_marker = "from . import views"

    dashboard_urls_text = (
        dashboard_urls_text.replace(
            import_marker,
            (
                import_marker
                + "\n"
                + "from delivery.customer_views import (\n"
                + "    customer_delivery_tracking,\n"
                + "    available_delivery_options,\n"
                + ")\n"
            ),
            1,
        )
    )

    marker = "urlpatterns = ["

    routes = r'''

    # =========================================================
    # CUSTOMER DELIVERY TRACKING
    # =========================================================

    path(
        "orders/<str:order_number>/track/",
        customer_delivery_tracking,
        name="customer_delivery_tracking",
    ),

    path(
        "delivery-options/",
        available_delivery_options,
        name="available_delivery_options",
    ),
'''

    dashboard_urls_text = (
        dashboard_urls_text.replace(
            marker,
            marker + routes,
            1,
        )
    )

    DASHBOARD_URLS.write_text(
        dashboard_urls_text,
        encoding="utf-8",
    )

    print(
        "Added customer delivery routes."
    )


# ============================================================
# 5. ADMIN DELIVERY ZONE VIEWS
# ============================================================

views_text = VIEWS.read_text(
    encoding="utf-8-sig"
)

views_text = views_text.replace(
    "DeliveryProviderForm,\n)",
    (
        "DeliveryProviderForm,\n"
        "    DeliveryZoneForm,\n"
        ")"
    ),
)

views_text = views_text.replace(
    "DeliveryProvider,\n)",
    (
        "DeliveryProvider,\n"
        "    DeliveryZone,\n"
        ")"
    ),
)

if "def delivery_zone_list(" not in views_text:

    views_text += r'''


# ============================================================
# DELIVERY ZONES
# ============================================================

@staff_member_required
def delivery_zone_list(request):

    zones = (
        DeliveryZone.objects
        .select_related(
            "provider"
        )
        .order_by(
            "county",
            "town",
            "method",
        )
    )

    q = request.GET.get(
        "q",
        "",
    ).strip()

    if q:

        zones = zones.filter(

            Q(
                county__icontains=q
            )

            | Q(
                town__icontains=q
            )

            | Q(
                provider__name__icontains=q
            )

            | Q(
                pickup_point__icontains=q
            )
        )

    return render(
        request,
        "dashboard/admin/delivery/zones.html",
        {
            "zones": zones,
            "query": q,
        },
    )


@staff_member_required
def delivery_zone_create(request):

    if request.method == "POST":

        form = DeliveryZoneForm(
            request.POST
        )

        if form.is_valid():

            zone = form.save()

            messages.success(
                request,
                (
                    f"Delivery zone for "
                    f"{zone.county} saved."
                ),
            )

            return redirect(
                "delivery_zone_list"
            )

    else:

        form = DeliveryZoneForm()

    return render(
        request,
        "dashboard/admin/delivery/zone_form.html",
        {
            "form": form,
            "title": "Add Delivery Zone",
        },
    )


@staff_member_required
def delivery_zone_edit(
    request,
    pk,
):

    zone = get_object_or_404(
        DeliveryZone,
        pk=pk,
    )

    if request.method == "POST":

        form = DeliveryZoneForm(
            request.POST,
            instance=zone,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Delivery zone updated.",
            )

            return redirect(
                "delivery_zone_list"
            )

    else:

        form = DeliveryZoneForm(
            instance=zone
        )

    return render(
        request,
        "dashboard/admin/delivery/zone_form.html",
        {
            "form": form,
            "title": "Edit Delivery Zone",
            "zone": zone,
        },
    )


@staff_member_required
def delivery_zone_toggle(
    request,
    pk,
):

    zone = get_object_or_404(
        DeliveryZone,
        pk=pk,
    )

    if request.method == "POST":

        zone.is_active = (
            not zone.is_active
        )

        zone.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

        messages.success(
            request,
            "Delivery zone status updated.",
        )

    return redirect(
        "delivery_zone_list"
    )
'''

    VIEWS.write_text(
        views_text,
        encoding="utf-8",
    )

    print(
        "Added delivery zone admin views."
    )


# ============================================================
# 6. ADMIN DELIVERY ZONE URLS
# ============================================================

urls_text = URLS.read_text(
    encoding="utf-8-sig"
)

if "delivery_zone_list" not in urls_text:

    marker = "urlpatterns = ["

    routes = r'''

    path(
        "zones/",
        views.delivery_zone_list,
        name="delivery_zone_list",
    ),

    path(
        "zones/add/",
        views.delivery_zone_create,
        name="delivery_zone_create",
    ),

    path(
        "zones/<int:pk>/edit/",
        views.delivery_zone_edit,
        name="delivery_zone_edit",
    ),

    path(
        "zones/<int:pk>/toggle/",
        views.delivery_zone_toggle,
        name="delivery_zone_toggle",
    ),
'''

    urls_text = urls_text.replace(
        marker,
        marker + routes,
        1,
    )

    URLS.write_text(
        urls_text,
        encoding="utf-8",
    )

    print(
        "Added delivery zone URLs."
    )


# ============================================================
# 7. DJANGO ADMIN
# ============================================================

admin_text = ADMIN.read_text(
    encoding="utf-8-sig"
)

admin_text = admin_text.replace(
    "DeliveryProvider,\n)",
    (
        "DeliveryProvider,\n"
        "    DeliveryZone,\n"
        ")"
    ),
)

if (
    "@admin.register(DeliveryZone)"
    not in admin_text
):

    admin_text += r'''


@admin.register(DeliveryZone)
class DeliveryZoneAdmin(admin.ModelAdmin):

    list_display = (
        "county",
        "town",
        "method",
        "provider",
        "pricing_mode",
        "fee",
        "is_active",
    )

    list_filter = (
        "method",
        "pricing_mode",
        "is_active",
    )

    search_fields = (
        "county",
        "town",
        "provider__name",
        "pickup_point",
    )
'''

    ADMIN.write_text(
        admin_text,
        encoding="utf-8",
    )


# ============================================================
# 8. DELIVERY NOTIFICATION TASK
# ============================================================

tasks_path = DELIVERY / "tasks.py"

tasks_path.write_text(
r'''
from celery import shared_task


NOTIFIABLE_STATUSES = {
    "dispatched",
    "in_transit",
    "arrived",
    "ready_for_collection",
    "out_for_delivery",
    "delivered",
    "collected",
    "failed",
    "returned",
}


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={
        "max_retries": 3
    },
)
def send_delivery_status_update(
    self,
    delivery_id,
):

    from notifications.tasks import (
        _send_order_notifications,
    )

    from .models import Delivery

    delivery = (
        Delivery.objects
        .select_related(
            "order",
            "order__user",
            "provider",
        )
        .get(
            pk=delivery_id
        )
    )

    if (
        delivery.status
        not in NOTIFIABLE_STATUSES
    ):
        return

    order = delivery.order

    provider_name = (
        delivery.provider.name
        if delivery.provider
        else "our delivery team"
    )

    status_label = (
        delivery.get_status_display()
    )

    details = []

    if delivery.transport_reference:

        details.append(
            "Reference: "
            + delivery.transport_reference
        )

    if delivery.pickup_point:

        details.append(
            "Pickup point: "
            + delivery.pickup_point
        )

    if delivery.destination:

        details.append(
            "Destination: "
            + delivery.destination
        )

    detail_text = ""

    if details:

        detail_text = (
            "\n"
            + "\n".join(details)
        )

    sms = (
        f"Order {order.order_number}: "
        f"{status_label}. "
        f"Provider: {provider_name}."
    )

    if delivery.transport_reference:

        sms += (
            " Ref: "
            + delivery.transport_reference
            + "."
        )

    if (
        delivery.status
        == "ready_for_collection"
        and delivery.pickup_point
    ):

        sms += (
            " Collect from "
            + delivery.pickup_point
            + "."
        )

    email_message = (
        f"Hi {order.full_name},\n\n"
        f"Your order {order.order_number} "
        f"delivery status is now: "
        f"{status_label}.\n\n"
        f"Provider: {provider_name}"
        f"{detail_text}\n\n"
        f"You can sign in to your account "
        f"to view the full delivery timeline."
    )

    _send_order_notifications(
        order,
        sms,
        f"Delivery update: {status_label}",
        email_message,
    )
'''.strip() + "\n",
encoding="utf-8"
)

print(
    "Created delivery notification task."
)


# ============================================================
# 9. QUEUE NOTIFICATIONS FROM STATUS SERVICE
# ============================================================

services_text = SERVICES.read_text(
    encoding="utf-8-sig"
)

if (
    "_queue_delivery_notification"
    not in services_text
):

    insert_after = (
        "from .models import (\n"
        "    Delivery,\n"
        "    DeliveryEvent,\n"
        ")\n"
    )

    helper = r'''


def _queue_delivery_notification(
    delivery_id,
):

    try:

        from .tasks import (
            send_delivery_status_update,
        )

        send_delivery_status_update.delay(
            delivery_id
        )

    except Exception:

        # Delivery state must never be rolled back
        # because the message broker is temporarily
        # unavailable.
        pass
'''

    if insert_after not in services_text:

        raise RuntimeError(
            "Could not locate delivery service imports."
        )

    services_text = services_text.replace(
        insert_after,
        insert_after + helper,
        1,
    )

    event_marker = r'''    DeliveryEvent.objects.create(
        delivery=delivery,
        status=status,
        message=message.strip(),
        created_by=user,
    )
'''

    event_replacement = event_marker + r'''

    transaction.on_commit(
        lambda delivery_id=delivery.pk: (
            _queue_delivery_notification(
                delivery_id
            )
        ),
        robust=True,
    )
'''

    if event_marker not in services_text:

        raise RuntimeError(
            "Could not locate DeliveryEvent creation."
        )

    services_text = services_text.replace(
        event_marker,
        event_replacement,
        1,
    )

    SERVICES.write_text(
        services_text,
        encoding="utf-8",
    )

    print(
        "Connected delivery notifications."
    )


# ============================================================
# 10. CUSTOMER TRACKING TEMPLATE
# ============================================================

(
    CUSTOMER_DELIVERY_TEMPLATES
    / "customer_tracking.html"
).write_text(
r'''
{% extends "base.html" %}

{% block content %}

<div class="container py-5">

    <div
        class="
            d-flex
            justify-content-between
            align-items-start
            flex-wrap
            gap-3
            mb-4
        "
    >

        <div>

            <a
                href="{% url 'order_detail' order.order_number %}"
                class="btn btn-sm btn-outline-secondary mb-3"
            >
                &larr; Back to Order
            </a>

            <h2 class="mb-1">
                Track Delivery
            </h2>

            <div class="text-muted">
                Order {{ order.order_number }}
            </div>

        </div>

        <span
            class="
                badge
                bg-primary
                fs-6
            "
        >
            {{ delivery.get_status_display }}
        </span>

    </div>


    {% if delivery.status == "ready_for_collection" %}

        <div class="alert alert-success">

            <strong>
                Your parcel is ready for collection.
            </strong>

            {% if delivery.pickup_point %}

                <div class="mt-2">

                    Pickup Point:
                    <strong>
                        {{ delivery.pickup_point }}
                    </strong>

                </div>

            {% endif %}

        </div>

    {% endif %}


    <div class="row g-4">

        <div class="col-lg-5">

            <div class="card shadow-sm mb-4">

                <div class="card-body p-4">

                    <h5 class="mb-4">
                        Delivery Information
                    </h5>

                    <div class="mb-3">

                        <small class="text-muted">
                            Delivery Type
                        </small>

                        <div class="fw-semibold">
                            {{ delivery.get_method_display }}
                        </div>

                    </div>


                    <div class="mb-3">

                        <small class="text-muted">
                            Managed By
                        </small>

                        <div class="fw-semibold">
                            {{ delivery.get_management_type_display }}
                        </div>

                    </div>


                    <div class="mb-3">

                        <small class="text-muted">
                            Provider
                        </small>

                        <div class="fw-semibold">

                            {% if delivery.provider %}

                                {{ delivery.provider.name }}

                            {% else %}

                                Shop Delivery Team

                            {% endif %}

                        </div>

                    </div>


                    {% if delivery.transport_reference %}

                        <div class="mb-3">

                            <small class="text-muted">
                                Parcel / Transport Reference
                            </small>

                            <div>
                                <code class="fs-6">
                                    {{ delivery.transport_reference }}
                                </code>
                            </div>

                        </div>

                    {% endif %}


                    <div class="mb-3">

                        <small class="text-muted">
                            Destination
                        </small>

                        <div class="fw-semibold">
                            {{ delivery.destination }}
                        </div>

                    </div>


                    {% if delivery.pickup_point %}

                        <div class="mb-3">

                            <small class="text-muted">
                                Pickup Point
                            </small>

                            <div class="fw-semibold">
                                {{ delivery.pickup_point }}
                            </div>

                        </div>

                    {% endif %}


                    {% if delivery.expected_arrival %}

                        <div class="mb-3">

                            <small class="text-muted">
                                Expected Arrival
                            </small>

                            <div class="fw-semibold">
                                {{ delivery.expected_arrival|date:"d M Y H:i" }}
                            </div>

                        </div>

                    {% endif %}


                    {% if delivery.provider.phone %}

                        <div class="mt-4">

                            <a
                                href="tel:{{ delivery.provider.phone }}"
                                class="btn btn-outline-primary"
                            >
                                <i class="bi bi-telephone"></i>
                                Contact Provider
                            </a>

                        </div>

                    {% endif %}

                </div>

            </div>

        </div>


        <div class="col-lg-7">

            <div class="card shadow-sm">

                <div class="card-body p-4">

                    <h5 class="mb-4">
                        Delivery Progress
                    </h5>


                    {% for event in events %}

                        <div
                            class="
                                d-flex
                                gap-3
                                pb-4
                            "
                        >

                            <div>

                                <div
                                    class="
                                        rounded-circle
                                        bg-success
                                        text-white
                                        d-flex
                                        align-items-center
                                        justify-content-center
                                    "
                                    style="
                                        width:38px;
                                        height:38px;
                                    "
                                >
                                    <i class="bi bi-check-lg"></i>
                                </div>

                            </div>


                            <div class="flex-grow-1">

                                <div class="fw-semibold">
                                    {{ event.get_status_display }}
                                </div>

                                <small class="text-muted">
                                    {{ event.created_at|date:"d M Y H:i" }}
                                </small>

                                {% if event.message %}

                                    <p class="mb-0 mt-2">
                                        {{ event.message }}
                                    </p>

                                {% endif %}

                            </div>

                        </div>

                    {% empty %}

                        <div class="text-muted">
                            Delivery tracking information
                            will appear here once your parcel
                            is assigned.
                        </div>

                    {% endfor %}

                </div>

            </div>

        </div>

    </div>

</div>

{% endblock %}
'''.strip() + "\n",
encoding="utf-8"
)


# ============================================================
# 11. CUSTOMER AVAILABLE OPTIONS TEMPLATE
# ============================================================

(
    CUSTOMER_DELIVERY_TEMPLATES
    / "customer_options.html"
).write_text(
r'''
{% extends "base.html" %}

{% block content %}

<div class="container py-5">

    <h2>
        Delivery Options
    </h2>

    <p class="text-muted">
        Available delivery methods for your area.
    </p>


    <form
        method="GET"
        class="card card-body shadow-sm mb-4"
    >

        <div class="row g-3">

            <div class="col-md-5">

                <label class="form-label">
                    County
                </label>

                <input
                    type="text"
                    name="county"
                    value="{{ county }}"
                    class="form-control"
                    placeholder="e.g. Kisii"
                >

            </div>

            <div class="col-md-5">

                <label class="form-label">
                    Town
                </label>

                <input
                    type="text"
                    name="town"
                    value="{{ town }}"
                    class="form-control"
                    placeholder="e.g. Kisii Town"
                >

            </div>

            <div class="col-md-2 d-flex align-items-end">

                <button
                    class="btn btn-primary w-100"
                >
                    Check
                </button>

            </div>

        </div>

    </form>


    <div class="row g-3">

        {% for zone in zones %}

            <div class="col-md-6 col-xl-4">

                <div class="card shadow-sm h-100">

                    <div class="card-body">

                        <h5>
                            {{ zone.get_method_display }}
                        </h5>

                        <div class="text-muted mb-3">

                            {{ zone.county }}

                            {% if zone.town %}
                                · {{ zone.town }}
                            {% endif %}

                        </div>


                        {% if zone.provider %}

                            <div class="mb-2">

                                Provider:
                                <strong>
                                    {{ zone.provider.name }}
                                </strong>

                            </div>

                        {% endif %}


                        {% if zone.pickup_point %}

                            <div class="mb-2">

                                Pickup:
                                <strong>
                                    {{ zone.pickup_point }}
                                </strong>

                            </div>

                        {% endif %}


                        {% if zone.pricing_mode == "fixed" %}

                            <div class="fs-5 fw-bold">

                                KES
                                {{ zone.fee|floatformat:2 }}

                            </div>

                        {% else %}

                            <div class="fw-semibold text-primary">
                                Delivery fee confirmed after order
                            </div>

                        {% endif %}


                        {% if zone.estimated_time %}

                            <div class="mt-2">

                                Estimated:
                                {{ zone.estimated_time }}

                            </div>

                        {% endif %}


                        {% if zone.instructions %}

                            <p class="small text-muted mt-3 mb-0">
                                {{ zone.instructions }}
                            </p>

                        {% endif %}

                    </div>

                </div>

            </div>

        {% empty %}

            <div class="col-12">

                <div class="alert alert-light border">

                    No configured delivery options
                    match this location yet.

                </div>

            </div>

        {% endfor %}

    </div>

</div>

{% endblock %}
'''.strip() + "\n",
encoding="utf-8"
)


# ============================================================
# 12. DELIVERY ZONES ADMIN TEMPLATE
# ============================================================

(
    ADMIN_DELIVERY_TEMPLATES
    / "zones.html"
).write_text(
r'''
{% extends "dashboard/admin/base.html" %}

{% block title %}
Delivery Zones
{% endblock %}

{% block page_heading %}
Delivery Zones
{% endblock %}

{% block admin_content %}

<div class="dashboard-heading">

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

            <h1>
                Delivery Zones & Pricing
            </h1>

            <p>
                Configure counties, towns, pickup points,
                delivery methods and customer charges.
            </p>

        </div>


        <div class="d-flex gap-2 flex-wrap">

            <a
                href="{% url 'delivery_list' %}"
                class="btn btn-outline-secondary"
            >
                Deliveries
            </a>

            <a
                href="{% url 'delivery_provider_list' %}"
                class="btn btn-outline-primary"
            >
                Providers
            </a>

            <a
                href="{% url 'delivery_zone_create' %}"
                class="btn btn-primary"
            >
                <i class="bi bi-plus-lg"></i>
                Add Zone
            </a>

        </div>

    </div>

</div>


<div class="dashboard-card mb-4">

    <form method="GET">

        <div class="input-group">

            <input
                type="text"
                name="q"
                value="{{ query }}"
                class="form-control"
                placeholder="Search county, town, provider or pickup point..."
            >

            <button
                class="btn btn-primary"
            >
                Search
            </button>

        </div>

    </form>

</div>


<div class="dashboard-card">

    <div class="table-responsive">

        <table
            class="
                table
                dashboard-table
                align-middle
            "
        >

            <thead>

                <tr>
                    <th>County / Town</th>
                    <th>Method</th>
                    <th>Provider</th>
                    <th>Pickup Point</th>
                    <th>Price</th>
                    <th>Estimated</th>
                    <th>Status</th>
                    <th class="text-end">Action</th>
                </tr>

            </thead>


            <tbody>

                {% for zone in zones %}

                    <tr>

                        <td>

                            <strong>
                                {{ zone.county }}
                            </strong>

                            {% if zone.town %}

                                <small class="d-block text-muted">
                                    {{ zone.town }}
                                </small>

                            {% endif %}

                        </td>


                        <td>
                            {{ zone.get_method_display }}
                        </td>


                        <td>

                            {% if zone.provider %}
                                {{ zone.provider.name }}
                            {% else %}
                                —
                            {% endif %}

                        </td>


                        <td>
                            {{ zone.pickup_point|default:"—" }}
                        </td>


                        <td>

                            {% if zone.pricing_mode == "fixed" %}

                                KES {{ zone.fee|floatformat:2 }}

                            {% else %}

                                <span class="text-primary">
                                    Confirm Later
                                </span>

                            {% endif %}

                        </td>


                        <td>
                            {{ zone.estimated_time|default:"—" }}
                        </td>


                        <td>

                            {% if zone.is_active %}

                                <span class="badge text-bg-success">
                                    Active
                                </span>

                            {% else %}

                                <span class="badge text-bg-secondary">
                                    Disabled
                                </span>

                            {% endif %}

                        </td>


                        <td class="text-end">

                            <a
                                href="{% url 'delivery_zone_edit' zone.pk %}"
                                class="btn btn-sm btn-outline-primary"
                            >
                                Edit
                            </a>

                            <form
                                method="POST"
                                action="{% url 'delivery_zone_toggle' zone.pk %}"
                                class="d-inline"
                            >

                                {% csrf_token %}

                                <button
                                    class="btn btn-sm btn-outline-secondary"
                                >
                                    {% if zone.is_active %}
                                        Disable
                                    {% else %}
                                        Enable
                                    {% endif %}
                                </button>

                            </form>

                        </td>

                    </tr>

                {% empty %}

                    <tr>

                        <td
                            colspan="8"
                            class="text-center py-5"
                        >

                            No delivery zones configured yet.

                        </td>

                    </tr>

                {% endfor %}

            </tbody>

        </table>

    </div>

</div>

{% endblock %}
'''.strip() + "\n",
encoding="utf-8"
)


# ============================================================
# 13. DELIVERY ZONE FORM TEMPLATE
# ============================================================

(
    ADMIN_DELIVERY_TEMPLATES
    / "zone_form.html"
).write_text(
r'''
{% extends "dashboard/admin/base.html" %}

{% block title %}
{{ title }}
{% endblock %}

{% block page_heading %}
Delivery Zone
{% endblock %}

{% block admin_content %}

<div class="dashboard-heading">

    <div>

        <h1>
            {{ title }}
        </h1>

        <p>
            Configure location-based delivery options
            without requiring a transport API.
        </p>

    </div>

</div>


<div class="dashboard-card">

    <form method="POST">

        {% csrf_token %}

        <div class="row g-3">

            <div class="col-md-6">

                <label class="form-label">
                    County
                </label>

                {{ form.county }}

                {{ form.county.errors }}

            </div>


            <div class="col-md-6">

                <label class="form-label">
                    Town / Area
                </label>

                {{ form.town }}

            </div>


            <div class="col-md-6">

                <label class="form-label">
                    Delivery Method
                </label>

                {{ form.method }}

            </div>


            <div class="col-md-6">

                <label class="form-label">
                    Preferred Provider
                </label>

                {{ form.provider }}

            </div>


            <div class="col-12">

                <label class="form-label">
                    Pickup Point / Parcel Office
                </label>

                {{ form.pickup_point }}

            </div>


            <div class="col-md-6">

                <label class="form-label">
                    Pricing
                </label>

                {{ form.pricing_mode }}

            </div>


            <div class="col-md-6">

                <label class="form-label">
                    Delivery Fee
                </label>

                {{ form.fee }}

                {{ form.fee.errors }}

            </div>


            <div class="col-md-6">

                <label class="form-label">
                    Estimated Time
                </label>

                {{ form.estimated_time }}

            </div>


            <div class="col-12">

                <label class="form-label">
                    Customer Instructions
                </label>

                {{ form.instructions }}

            </div>


            <div class="col-12">

                <div class="form-check">

                    {{ form.is_active }}

                    <label class="form-check-label">
                        Active
                    </label>

                </div>

            </div>

        </div>


        <div class="mt-4">

            <button
                class="btn btn-primary"
            >
                Save Delivery Zone
            </button>

            <a
                href="{% url 'delivery_zone_list' %}"
                class="btn btn-outline-secondary"
            >
                Cancel
            </a>

        </div>

    </form>

</div>

{% endblock %}
'''.strip() + "\n",
encoding="utf-8"
)


# ============================================================
# 14. ADD ZONES BUTTON TO DELIVERY PAGE
# ============================================================

delivery_list_template = (
    ADMIN_DELIVERY_TEMPLATES
    / "list.html"
)

delivery_list_text = (
    delivery_list_template.read_text(
        encoding="utf-8-sig"
    )
)

if (
    "delivery_zone_list"
    not in delivery_list_text
):

    old = r'''        <a
            href="{% url 'delivery_provider_list' %}"
            class="btn btn-outline-primary"
        >
            <i class="bi bi-truck"></i>
            Delivery Providers
        </a>'''

    new = r'''        <div class="d-flex gap-2 flex-wrap">

            <a
                href="{% url 'delivery_zone_list' %}"
                class="btn btn-outline-secondary"
            >
                <i class="bi bi-geo-alt"></i>
                Zones & Pricing
            </a>

            <a
                href="{% url 'delivery_provider_list' %}"
                class="btn btn-outline-primary"
            >
                <i class="bi bi-truck"></i>
                Delivery Providers
            </a>

        </div>'''

    if old in delivery_list_text:

        delivery_list_text = (
            delivery_list_text.replace(
                old,
                new,
                1,
            )
        )

        delivery_list_template.write_text(
            delivery_list_text,
            encoding="utf-8",
        )

        print(
            "Added Zones button to Delivery page."
        )


# ============================================================
# 15. ADD ASSIGN/MANAGE DELIVERY TO ADMIN ORDER
# ============================================================

admin_order_text = (
    ADMIN_ORDER_TEMPLATE.read_text(
        encoding="utf-8-sig"
    )
)

if (
    "delivery_assign"
    not in admin_order_text
):

    marker = r'''        <div class="d-flex gap-2 flex-wrap">'''

    addition = r'''        <div class="d-flex gap-2 flex-wrap">

            {% if order.status != "cancelled" %}

                <a
                    href="{% url 'delivery_assign' order.order_number %}"
                    class="btn btn-outline-primary"
                >
                    <i class="bi bi-truck"></i>

                    {% if order.delivery %}
                        Manage Delivery
                    {% else %}
                        Assign Delivery
                    {% endif %}
                </a>

            {% endif %}
'''

    if marker not in admin_order_text:

        raise RuntimeError(
            "Could not locate admin order action area."
        )

    admin_order_text = (
        admin_order_text.replace(
            marker,
            addition,
            1,
        )
    )

    ADMIN_ORDER_TEMPLATE.write_text(
        admin_order_text,
        encoding="utf-8",
    )

    print(
        "Added delivery action to admin order."
    )


# ============================================================
# 16. ADD TRACK BUTTON TO CUSTOMER ORDER
# ============================================================

customer_order_text = (
    CUSTOMER_ORDER_TEMPLATE.read_text(
        encoding="utf-8-sig"
    )
)

if (
    "customer_delivery_tracking"
    not in customer_order_text
):

    marker = r'''                    {% if order.courier or order.tracking_number %}'''

    tracking_block = r'''                    {% if order.delivery %}

                    <hr>

                    <div
                        class="
                            d-flex
                            justify-content-between
                            align-items-center
                            gap-3
                        "
                    >

                        <div>

                            <strong>
                                Delivery Tracking
                            </strong>

                            <div class="small text-muted">
                                {{ order.delivery.get_status_display }}
                            </div>

                        </div>

                        <a
                            href="{% url 'customer_delivery_tracking' order.order_number %}"
                            class="btn btn-primary btn-sm"
                        >
                            Track Delivery
                        </a>

                    </div>

                    {% endif %}


'''

    if marker in customer_order_text:

        customer_order_text = (
            customer_order_text.replace(
                marker,
                tracking_block + marker,
                1,
            )
        )

    else:

        raise RuntimeError(
            "Could not locate customer delivery tracking section."
        )

    CUSTOMER_ORDER_TEMPLATE.write_text(
        customer_order_text,
        encoding="utf-8",
    )

    print(
        "Added customer Track Delivery button."
    )


# ============================================================
# 17. TESTS
# ============================================================

tests_path = (
    DELIVERY
    / "test_phase7b.py"
)

tests_path.write_text(
r'''
from decimal import Decimal

from django.contrib.auth import get_user_model

from django.test import TestCase

from django.urls import reverse

from orders.models import Order

from .models import (
    Delivery,
    DeliveryEvent,
    DeliveryProvider,
    DeliveryZone,
)


User = get_user_model()


class DeliveryPhase7BTests(TestCase):

    def setUp(self):

        self.customer = (
            User.objects.create_user(
                username="trackingcustomer",
                password="pass12345",
                role=User.CUSTOMER,
            )
        )

        self.other_customer = (
            User.objects.create_user(
                username="othercustomer",
                password="pass12345",
                role=User.CUSTOMER,
            )
        )

        self.staff = (
            User.objects.create_user(
                username="deliverystaff7b",
                password="pass12345",
                role=User.ADMIN,
                is_staff=True,
            )
        )

        self.order = Order.objects.create(
            user=self.customer,
            order_number="TRACK-001",
            full_name="Tracking Customer",
            phone="0712345678",
            email="track@example.com",
            county="Kisii",
            city="Kisii",
            estate="Town",
            house_number="1",
            subtotal=Decimal("2500.00"),
            shipping_cost=Decimal("500.00"),
            discount=Decimal("0.00"),
            total_amount=Decimal("3000.00"),
            status="shipped",
            payment_status="paid",
            inventory_status="consumed",
        )

        self.provider = (
            DeliveryProvider.objects.create(
                name="Sample Coach",
                provider_type="bus_coach",
            )
        )

        self.delivery = (
            Delivery.objects.create(
                order=self.order,
                management_type="external",
                method="station_pickup",
                provider=self.provider,
                status="in_transit",
                origin="Nairobi",
                destination="Kisii",
                pickup_point=(
                    "Kisii Parcel Office"
                ),
                transport_reference=(
                    "PARCEL-777"
                ),
                customer_delivery_fee=(
                    Decimal("500.00")
                ),
                actual_delivery_cost=(
                    Decimal("450.00")
                ),
            )
        )

        DeliveryEvent.objects.create(
            delivery=self.delivery,
            status="dispatched",
            message=(
                "Parcel left Nairobi."
            ),
            created_by=self.staff,
        )

    def test_owner_can_view_tracking(self):

        self.client.login(
            username="trackingcustomer",
            password="pass12345",
        )

        response = self.client.get(
            reverse(
                "customer_delivery_tracking",
                kwargs={
                    "order_number": (
                        self.order.order_number
                    )
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "PARCEL-777",
        )

        self.assertContains(
            response,
            "Kisii Parcel Office",
        )

    def test_other_customer_cannot_view_tracking(self):

        self.client.login(
            username="othercustomer",
            password="pass12345",
        )

        response = self.client.get(
            reverse(
                "customer_delivery_tracking",
                kwargs={
                    "order_number": (
                        self.order.order_number
                    )
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_delivery_zone_can_be_created(self):

        zone = DeliveryZone.objects.create(
            county="Kisii",
            town="Kisii Town",
            method="station_pickup",
            provider=self.provider,
            pickup_point=(
                "Kisii Parcel Office"
            ),
            pricing_mode="fixed",
            fee=Decimal("500.00"),
            estimated_time="1 day",
        )

        self.assertEqual(
            zone.fee,
            Decimal("500.00"),
        )
'''.strip() + "\n",
encoding="utf-8"
)


print()
print("=" * 72)
print("PHASE 7B PATCH COMPLETE")
print("=" * 72)
print()
print("Next:")
print("python manage.py makemigrations delivery")
print("python manage.py migrate")
print("python manage.py check")
