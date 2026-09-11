from pathlib import Path
import re
import shutil

ROOT = Path.cwd()

delivery = ROOT / "delivery"
templates = delivery / "templates" / "dashboard" / "admin" / "delivery"

delivery.mkdir(exist_ok=True)
templates.mkdir(parents=True, exist_ok=True)

(delivery / "migrations").mkdir(exist_ok=True)

(delivery / "__init__.py").touch()
(delivery / "migrations" / "__init__.py").touch()


# ============================================================
# APPS
# ============================================================

(delivery / "apps.py").write_text(
r'''
from django.apps import AppConfig


class DeliveryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "delivery"
'''.strip() + "\n",
encoding="utf-8"
)


# ============================================================
# MODELS
# ============================================================

(delivery / "models.py").write_text(
r'''
from decimal import Decimal

from django.conf import settings
from django.db import models


class DeliveryProvider(models.Model):

    TYPE_CHOICES = [
        ("ride_hailing", "Ride Hailing / App"),
        ("bus_coach", "Bus / Coach"),
        ("matatu_shuttle", "Matatu / Shuttle"),
        ("personal_rider", "Personal Rider"),
        ("shop_fleet", "Shop Rider / Fleet"),
        ("courier", "Courier Company"),
        ("other", "Other"),
    ]

    name = models.CharField(
        max_length=150,
        unique=True,
    )

    provider_type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        default="other",
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
    )

    email = models.EmailField(
        blank=True,
    )

    website = models.URLField(
        blank=True,
    )

    notes = models.TextField(
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
        ordering = ["name"]

    def __str__(self):
        return self.name


class Delivery(models.Model):

    MANAGEMENT_CHOICES = [
        ("internal", "Shop Managed"),
        ("external", "External Provider"),
    ]

    METHOD_CHOICES = [
        ("local_door", "Local Door Delivery"),
        ("long_distance", "Long Distance Delivery"),
        ("station_pickup", "Station / Parcel Office Pickup"),
        ("store_pickup", "Store Pickup"),
        ("personal_rider", "Personal Rider / Bike"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("assigned", "Assigned"),
        ("ready_for_dispatch", "Ready for Dispatch"),
        ("dispatched", "Dispatched"),
        ("in_transit", "In Transit"),
        ("arrived", "Arrived at Destination"),
        ("ready_for_collection", "Ready for Collection"),
        ("out_for_delivery", "Out for Delivery"),
        ("delivered", "Delivered"),
        ("collected", "Collected"),
        ("failed", "Delivery Attempt Failed"),
        ("returned", "Returned"),
        ("cancelled", "Delivery Cancelled"),
    ]

    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="delivery",
    )

    management_type = models.CharField(
        max_length=20,
        choices=MANAGEMENT_CHOICES,
        default="external",
        db_index=True,
    )

    method = models.CharField(
        max_length=30,
        choices=METHOD_CHOICES,
        default="local_door",
    )

    provider = models.ForeignKey(
        DeliveryProvider,
        on_delete=models.PROTECT,
        related_name="deliveries",
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="pending",
        db_index=True,
    )

    origin = models.CharField(
        max_length=200,
        blank=True,
    )

    destination = models.CharField(
        max_length=255,
    )

    pickup_point = models.CharField(
        max_length=255,
        blank=True,
    )

    transport_reference = models.CharField(
        max_length=120,
        blank=True,
        db_index=True,
    )

    driver_name = models.CharField(
        max_length=150,
        blank=True,
    )

    driver_phone = models.CharField(
        max_length=30,
        blank=True,
    )

    customer_delivery_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    actual_delivery_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    expected_arrival = models.DateTimeField(
        null=True,
        blank=True,
    )

    dispatched_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    arrived_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    collected_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deliveries_created",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.order.order_number} - {self.get_status_display()}"

    @property
    def delivery_margin(self):
        return (
            self.customer_delivery_fee
            - self.actual_delivery_cost
        )


class DeliveryEvent(models.Model):

    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.CASCADE,
        related_name="events",
    )

    status = models.CharField(
        max_length=30,
        choices=Delivery.STATUS_CHOICES,
    )

    message = models.TextField(
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delivery_events_created",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.delivery} - {self.get_status_display()}"


class DeliveryAttempt(models.Model):

    RESULT_CHOICES = [
        ("successful", "Successful"),
        ("customer_unavailable", "Customer Unavailable"),
        ("unreachable", "Customer Unreachable"),
        ("wrong_address", "Wrong Address"),
        ("transport_delay", "Transport Delay"),
        ("parcel_not_collected", "Parcel Not Collected"),
        ("other", "Other"),
    ]

    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.CASCADE,
        related_name="attempts",
    )

    result = models.CharField(
        max_length=40,
        choices=RESULT_CHOICES,
    )

    notes = models.TextField(
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delivery_attempts_created",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.delivery.order.order_number} - {self.get_result_display()}"
'''.strip() + "\n",
encoding="utf-8"
)


# ============================================================
# FORMS
# ============================================================

(delivery / "forms.py").write_text(
r'''
from django import forms

from .models import (
    Delivery,
    DeliveryAttempt,
    DeliveryProvider,
)


class DeliveryProviderForm(forms.ModelForm):

    class Meta:

        model = DeliveryProvider

        fields = [
            "name",
            "provider_type",
            "phone",
            "email",
            "website",
            "notes",
            "is_active",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "provider_type": forms.Select(
                attrs={"class": "form-select"}
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control"}
            ),
            "website": forms.URLInput(
                attrs={"class": "form-control"}
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }


class DeliveryAssignmentForm(forms.ModelForm):

    class Meta:

        model = Delivery

        fields = [
            "management_type",
            "method",
            "provider",
            "origin",
            "destination",
            "pickup_point",
            "transport_reference",
            "driver_name",
            "driver_phone",
            "customer_delivery_fee",
            "actual_delivery_cost",
            "expected_arrival",
            "notes",
        ]

        widgets = {
            "management_type": forms.Select(
                attrs={"class": "form-select"}
            ),

            "method": forms.Select(
                attrs={"class": "form-select"}
            ),

            "provider": forms.Select(
                attrs={"class": "form-select"}
            ),

            "origin": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Nairobi",
                }
            ),

            "destination": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Kisii Town",
                }
            ),

            "pickup_point": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Parcel office, stage, station "
                        "or collection point"
                    ),
                }
            ),

            "transport_reference": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Receipt, parcel number or "
                        "provider reference"
                    ),
                }
            ),

            "driver_name": forms.TextInput(
                attrs={"class": "form-control"}
            ),

            "driver_phone": forms.TextInput(
                attrs={"class": "form-control"}
            ),

            "customer_delivery_fee": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                }
            ),

            "actual_delivery_cost": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                }
            ),

            "expected_arrival": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                },
                format="%Y-%m-%dT%H:%M",
            ),

            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                }
            ),
        }

    def __init__(self, *args, **kwargs):

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

        self.fields[
            "expected_arrival"
        ].input_formats = [
            "%Y-%m-%dT%H:%M",
        ]

    def clean(self):

        cleaned = super().clean()

        management_type = cleaned.get(
            "management_type"
        )

        provider = cleaned.get(
            "provider"
        )

        method = cleaned.get(
            "method"
        )

        pickup_point = (
            cleaned.get(
                "pickup_point"
            )
            or ""
        ).strip()

        if (
            management_type == "external"
            and not provider
        ):

            self.add_error(
                "provider",
                (
                    "Choose the external transport "
                    "provider."
                ),
            )

        if (
            method == "station_pickup"
            and not pickup_point
        ):

            self.add_error(
                "pickup_point",
                (
                    "Enter the station, parcel office "
                    "or pickup point."
                ),
            )

        return cleaned


class DeliveryStatusForm(forms.Form):

    status = forms.ChoiceField(
        choices=Delivery.STATUS_CHOICES,
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )

    message = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": (
                    "Optional update visible in "
                    "the delivery timeline."
                ),
            }
        ),
    )


class DeliveryAttemptForm(forms.ModelForm):

    class Meta:

        model = DeliveryAttempt

        fields = [
            "result",
            "notes",
        ]

        widgets = {
            "result": forms.Select(
                attrs={"class": "form-select"}
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
        }
'''.strip() + "\n",
encoding="utf-8"
)


# ============================================================
# SERVICES
# ============================================================

(delivery / "services.py").write_text(
r'''
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from orders.models import Order

from .models import (
    Delivery,
    DeliveryEvent,
)


DELIVERY_TRANSITIONS = {

    "pending": [
        "assigned",
        "cancelled",
    ],

    "assigned": [
        "ready_for_dispatch",
        "dispatched",
        "out_for_delivery",
        "cancelled",
    ],

    "ready_for_dispatch": [
        "dispatched",
        "out_for_delivery",
        "cancelled",
    ],

    "dispatched": [
        "in_transit",
        "arrived",
        "out_for_delivery",
        "failed",
    ],

    "in_transit": [
        "arrived",
        "out_for_delivery",
        "failed",
    ],

    "arrived": [
        "ready_for_collection",
        "out_for_delivery",
        "delivered",
        "failed",
    ],

    "ready_for_collection": [
        "collected",
        "failed",
    ],

    "out_for_delivery": [
        "delivered",
        "failed",
    ],

    "failed": [
        "assigned",
        "ready_for_dispatch",
        "dispatched",
        "out_for_delivery",
        "returned",
        "cancelled",
    ],

    "delivered": [],
    "collected": [],
    "returned": [],
    "cancelled": [],
}


def allowed_delivery_statuses(
    delivery
):

    return DELIVERY_TRANSITIONS.get(
        delivery.status,
        [],
    )


@transaction.atomic
def change_delivery_status(
    *,
    delivery,
    status,
    user,
    message="",
):

    delivery = (
        Delivery.objects
        .select_for_update()
        .select_related(
            "order",
            "provider",
        )
        .get(pk=delivery.pk)
    )

    allowed = allowed_delivery_statuses(
        delivery
    )

    if status not in allowed:

        raise ValidationError(
            (
                f"Delivery cannot move from "
                f"{delivery.get_status_display()} "
                f"to {dict(Delivery.STATUS_CHOICES).get(status, status)}."
            )
        )

    order = delivery.order

    # Money should be confirmed before the parcel leaves.
    if status in [
        "dispatched",
        "in_transit",
        "arrived",
        "ready_for_collection",
        "out_for_delivery",
        "delivered",
        "collected",
    ]:

        if order.payment_status != "paid":

            raise ValidationError(
                (
                    "This order has not been paid. "
                    "It cannot be dispatched or delivered."
                )
            )

    now = timezone.now()

    delivery.status = status

    update_fields = [
        "status",
        "updated_at",
    ]

    if (
        status == "dispatched"
        and not delivery.dispatched_at
    ):

        delivery.dispatched_at = now
        update_fields.append(
            "dispatched_at"
        )

    if (
        status == "arrived"
        and not delivery.arrived_at
    ):

        delivery.arrived_at = now
        update_fields.append(
            "arrived_at"
        )

    if (
        status == "delivered"
        and not delivery.delivered_at
    ):

        delivery.delivered_at = now
        update_fields.append(
            "delivered_at"
        )

    if (
        status == "collected"
        and not delivery.collected_at
    ):

        delivery.collected_at = now
        update_fields.append(
            "collected_at"
        )

    delivery.save(
        update_fields=update_fields
    )

    DeliveryEvent.objects.create(
        delivery=delivery,
        status=status,
        message=message.strip(),
        created_by=user,
    )

    # Keep the legacy Order status useful for the
    # existing order-management screens.
    if status in [
        "dispatched",
        "in_transit",
        "arrived",
        "ready_for_collection",
        "out_for_delivery",
    ]:

        if order.status in [
            "confirmed",
            "processing",
        ]:

            order.status = "shipped"

            order.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

    elif status in [
        "delivered",
        "collected",
    ]:

        order.status = "delivered"

        order.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

    return delivery
'''.strip() + "\n",
encoding="utf-8"
)


# ============================================================
# VIEWS
# ============================================================

(delivery / "views.py").write_text(
r'''
from django.contrib import messages

from django.contrib.admin.views.decorators import (
    staff_member_required,
)

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator

from django.db.models import Q

from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from orders.models import Order

from .forms import (
    DeliveryAssignmentForm,
    DeliveryAttemptForm,
    DeliveryProviderForm,
)

from .models import (
    Delivery,
    DeliveryAttempt,
    DeliveryEvent,
    DeliveryProvider,
)

from .services import (
    allowed_delivery_statuses,
    change_delivery_status,
)


# ============================================================
# DELIVERY LIST
# ============================================================

@staff_member_required
def delivery_list(request):

    deliveries = (
        Delivery.objects
        .select_related(
            "order",
            "order__user",
            "provider",
        )
        .order_by("-created_at")
    )

    q = request.GET.get(
        "q",
        "",
    ).strip()

    status = request.GET.get(
        "status",
        "",
    )

    management = request.GET.get(
        "management",
        "",
    )

    if q:

        deliveries = deliveries.filter(

            Q(
                order__order_number__icontains=q
            )

            | Q(
                order__full_name__icontains=q
            )

            | Q(
                order__phone__icontains=q
            )

            | Q(
                destination__icontains=q
            )

            | Q(
                pickup_point__icontains=q
            )

            | Q(
                transport_reference__icontains=q
            )

            | Q(
                provider__name__icontains=q
            )
        )

    valid_statuses = dict(
        Delivery.STATUS_CHOICES
    )

    if status in valid_statuses:

        deliveries = deliveries.filter(
            status=status
        )

    if management in [
        "internal",
        "external",
    ]:

        deliveries = deliveries.filter(
            management_type=management
        )

    page_obj = Paginator(
        deliveries,
        25,
    ).get_page(
        request.GET.get("page")
    )

    stats = {

        "total": Delivery.objects.count(),

        "active": (
            Delivery.objects.exclude(
                status__in=[
                    "delivered",
                    "collected",
                    "returned",
                    "cancelled",
                ]
            ).count()
        ),

        "in_transit": (
            Delivery.objects.filter(
                status__in=[
                    "dispatched",
                    "in_transit",
                    "out_for_delivery",
                ]
            ).count()
        ),

        "ready_collection": (
            Delivery.objects.filter(
                status="ready_for_collection"
            ).count()
        ),

        "completed": (
            Delivery.objects.filter(
                status__in=[
                    "delivered",
                    "collected",
                ]
            ).count()
        ),
    }

    return render(
        request,
        "dashboard/admin/delivery/list.html",
        {
            "deliveries": (
                page_obj.object_list
            ),
            "page_obj": page_obj,
            "stats": stats,
            "query": q,
            "selected_status": status,
            "selected_management": management,
            "status_choices": Delivery.STATUS_CHOICES,
        },
    )


# ============================================================
# DELIVERY DETAIL
# ============================================================

@staff_member_required
def delivery_detail(
    request,
    pk,
):

    delivery = get_object_or_404(
        Delivery.objects
        .select_related(
            "order",
            "order__user",
            "provider",
            "created_by",
        )
        .prefetch_related(
            "events__created_by",
            "attempts__created_by",
        ),
        pk=pk,
    )

    allowed_values = (
        allowed_delivery_statuses(
            delivery
        )
    )

    status_labels = dict(
        Delivery.STATUS_CHOICES
    )

    allowed_statuses = [
        (
            value,
            status_labels[value],
        )
        for value in allowed_values
    ]

    return render(
        request,
        "dashboard/admin/delivery/detail.html",
        {
            "delivery": delivery,
            "order": delivery.order,
            "events": delivery.events.all(),
            "attempts": delivery.attempts.all(),
            "allowed_statuses": allowed_statuses,
            "attempt_form": DeliveryAttemptForm(),
        },
    )


# ============================================================
# ASSIGN / EDIT DELIVERY
# ============================================================

@staff_member_required
def delivery_assign(
    request,
    order_number,
):

    order = get_object_or_404(
        Order.objects.select_related(
            "user"
        ),
        order_number=order_number,
    )

    delivery = getattr(
        order,
        "delivery",
        None,
    )

    if order.status in [
        "delivered",
        "cancelled",
    ]:

        messages.error(
            request,
            (
                "Delivery cannot be assigned "
                "to a completed or cancelled order."
            ),
        )

        return redirect(
            "admin_order_detail",
            order_number=order.order_number,
        )

    if request.method == "POST":

        form = DeliveryAssignmentForm(
            request.POST,
            instance=delivery,
        )

        if form.is_valid():

            obj = form.save(
                commit=False
            )

            obj.order = order

            if not obj.created_by_id:
                obj.created_by = request.user

            is_new = obj.pk is None

            if (
                is_new
                and obj.status == "pending"
            ):
                obj.status = "assigned"

            obj.save()

            if is_new:

                DeliveryEvent.objects.create(
                    delivery=obj,
                    status=obj.status,
                    message=(
                        "Delivery assigned."
                    ),
                    created_by=request.user,
                )

            # Keep old Order shipping fields synchronized
            # for compatibility with existing screens.
            order_fields = []

            if obj.provider:

                if order.courier != obj.provider.name:

                    order.courier = (
                        obj.provider.name
                    )

                    order_fields.append(
                        "courier"
                    )

            if obj.transport_reference:

                if (
                    order.tracking_number
                    != obj.transport_reference
                ):

                    order.tracking_number = (
                        obj.transport_reference
                    )

                    order_fields.append(
                        "tracking_number"
                    )

            if order_fields:

                order_fields.append(
                    "updated_at"
                )

                order.save(
                    update_fields=order_fields
                )

            messages.success(
                request,
                (
                    "Delivery information saved."
                ),
            )

            return redirect(
                "delivery_detail",
                pk=obj.pk,
            )

    else:

        initial = {}

        if not delivery:

            address_parts = [
                order.estate,
                order.city,
                order.county,
            ]

            initial[
                "destination"
            ] = ", ".join(
                x
                for x in address_parts
                if x
            )

            initial[
                "customer_delivery_fee"
            ] = order.shipping_cost

        form = DeliveryAssignmentForm(
            instance=delivery,
            initial=initial,
        )

    return render(
        request,
        "dashboard/admin/delivery/assign.html",
        {
            "form": form,
            "order": order,
            "delivery": delivery,
        },
    )


# ============================================================
# STATUS UPDATE
# ============================================================

@staff_member_required
def delivery_update_status(
    request,
    pk,
):

    delivery = get_object_or_404(
        Delivery,
        pk=pk,
    )

    if request.method != "POST":

        return redirect(
            "delivery_detail",
            pk=delivery.pk,
        )

    status = request.POST.get(
        "status",
        "",
    ).strip()

    message = request.POST.get(
        "message",
        "",
    ).strip()

    try:

        change_delivery_status(
            delivery=delivery,
            status=status,
            user=request.user,
            message=message,
        )

        messages.success(
            request,
            "Delivery status updated.",
        )

    except ValidationError as exc:

        messages.error(
            request,
            " ".join(exc.messages),
        )

    return redirect(
        "delivery_detail",
        pk=delivery.pk,
    )


# ============================================================
# FAILED ATTEMPT
# ============================================================

@staff_member_required
def delivery_add_attempt(
    request,
    pk,
):

    delivery = get_object_or_404(
        Delivery,
        pk=pk,
    )

    if request.method != "POST":

        return redirect(
            "delivery_detail",
            pk=delivery.pk,
        )

    form = DeliveryAttemptForm(
        request.POST
    )

    if form.is_valid():

        attempt = form.save(
            commit=False
        )

        attempt.delivery = delivery
        attempt.created_by = request.user
        attempt.save()

        if (
            attempt.result
            != "successful"
            and delivery.status
            not in [
                "delivered",
                "collected",
                "returned",
                "cancelled",
            ]
        ):

            if (
                "failed"
                in allowed_delivery_statuses(
                    delivery
                )
            ):

                try:

                    change_delivery_status(
                        delivery=delivery,
                        status="failed",
                        user=request.user,
                        message=(
                            f"Delivery attempt failed: "
                            f"{attempt.get_result_display()}."
                        ),
                    )

                except ValidationError:
                    pass

        messages.success(
            request,
            "Delivery attempt recorded.",
        )

    else:

        messages.error(
            request,
            "Please correct the delivery attempt.",
        )

    return redirect(
        "delivery_detail",
        pk=delivery.pk,
    )


# ============================================================
# PROVIDERS
# ============================================================

@staff_member_required
def provider_list(request):

    providers = (
        DeliveryProvider.objects
        .order_by(
            "-is_active",
            "name",
        )
    )

    return render(
        request,
        "dashboard/admin/delivery/providers.html",
        {
            "providers": providers,
        },
    )


@staff_member_required
def provider_create(request):

    if request.method == "POST":

        form = DeliveryProviderForm(
            request.POST
        )

        if form.is_valid():

            provider = form.save()

            messages.success(
                request,
                (
                    f"{provider.name} "
                    f"has been added."
                ),
            )

            return redirect(
                "delivery_provider_list"
            )

    else:

        form = DeliveryProviderForm()

    return render(
        request,
        "dashboard/admin/delivery/provider_form.html",
        {
            "form": form,
            "title": "Add Delivery Provider",
        },
    )


@staff_member_required
def provider_edit(
    request,
    pk,
):

    provider = get_object_or_404(
        DeliveryProvider,
        pk=pk,
    )

    if request.method == "POST":

        form = DeliveryProviderForm(
            request.POST,
            instance=provider,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Delivery provider updated.",
            )

            return redirect(
                "delivery_provider_list"
            )

    else:

        form = DeliveryProviderForm(
            instance=provider
        )

    return render(
        request,
        "dashboard/admin/delivery/provider_form.html",
        {
            "form": form,
            "title": "Edit Delivery Provider",
            "provider": provider,
        },
    )


@staff_member_required
def provider_toggle(
    request,
    pk,
):

    provider = get_object_or_404(
        DeliveryProvider,
        pk=pk,
    )

    if request.method == "POST":

        provider.is_active = (
            not provider.is_active
        )

        provider.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

        messages.success(
            request,
            (
                f"{provider.name} is now "
                f"{'active' if provider.is_active else 'inactive'}."
            ),
        )

    return redirect(
        "delivery_provider_list"
    )
'''.strip() + "\n",
encoding="utf-8"
)


# ============================================================
# URLS
# ============================================================

(delivery / "urls.py").write_text(
r'''
from django.urls import path

from . import views


urlpatterns = [

    path(
        "",
        views.delivery_list,
        name="delivery_list",
    ),

    path(
        "providers/",
        views.provider_list,
        name="delivery_provider_list",
    ),

    path(
        "providers/add/",
        views.provider_create,
        name="delivery_provider_create",
    ),

    path(
        "providers/<int:pk>/edit/",
        views.provider_edit,
        name="delivery_provider_edit",
    ),

    path(
        "providers/<int:pk>/toggle/",
        views.provider_toggle,
        name="delivery_provider_toggle",
    ),

    path(
        "order/<str:order_number>/assign/",
        views.delivery_assign,
        name="delivery_assign",
    ),

    path(
        "<int:pk>/",
        views.delivery_detail,
        name="delivery_detail",
    ),

    path(
        "<int:pk>/status/",
        views.delivery_update_status,
        name="delivery_update_status",
    ),

    path(
        "<int:pk>/attempt/",
        views.delivery_add_attempt,
        name="delivery_add_attempt",
    ),
]
'''.strip() + "\n",
encoding="utf-8"
)


# ============================================================
# ADMIN
# ============================================================

(delivery / "admin.py").write_text(
r'''
from django.contrib import admin

from .models import (
    Delivery,
    DeliveryAttempt,
    DeliveryEvent,
    DeliveryProvider,
)


@admin.register(DeliveryProvider)
class DeliveryProviderAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "provider_type",
        "phone",
        "is_active",
    )

    list_filter = (
        "provider_type",
        "is_active",
    )

    search_fields = (
        "name",
        "phone",
    )


class DeliveryEventInline(
    admin.TabularInline
):

    model = DeliveryEvent
    extra = 0
    readonly_fields = (
        "status",
        "message",
        "created_by",
        "created_at",
    )

    can_delete = False


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):

    list_display = (
        "order",
        "management_type",
        "provider",
        "status",
        "destination",
        "transport_reference",
        "created_at",
    )

    list_filter = (
        "management_type",
        "status",
        "provider",
    )

    search_fields = (
        "order__order_number",
        "destination",
        "transport_reference",
        "driver_phone",
    )

    inlines = [
        DeliveryEventInline
    ]


@admin.register(DeliveryEvent)
class DeliveryEventAdmin(admin.ModelAdmin):

    list_display = (
        "delivery",
        "status",
        "created_by",
        "created_at",
    )

    readonly_fields = (
        "delivery",
        "status",
        "message",
        "created_by",
        "created_at",
    )


@admin.register(DeliveryAttempt)
class DeliveryAttemptAdmin(admin.ModelAdmin):

    list_display = (
        "delivery",
        "result",
        "created_by",
        "created_at",
    )
'''.strip() + "\n",
encoding="utf-8"
)


# ============================================================
# DELIVERY LIST TEMPLATE
# ============================================================

(templates / "list.html").write_text(
r'''
{% extends "dashboard/admin/base.html" %}

{% block title %}
Delivery Management
{% endblock %}

{% block page_heading %}
Delivery
{% endblock %}

{% block admin_content %}

<div class="dashboard-heading">

    <div class="d-flex justify-content-between align-items-start flex-wrap gap-3">

        <div>

            <h1>
                Delivery Management
            </h1>

            <p>
                Manage shop riders, external transport providers,
                parcel references and delivery progress.
            </p>

        </div>

        <a
            href="{% url 'delivery_provider_list' %}"
            class="btn btn-outline-primary"
        >
            <i class="bi bi-truck"></i>
            Delivery Providers
        </a>

    </div>

</div>


<div class="row g-3 mb-4">

    <div class="col-md-6 col-xl">

        <div class="dashboard-card mini-stat">
            <span>Total Deliveries</span>
            <strong>{{ stats.total }}</strong>
        </div>

    </div>

    <div class="col-md-6 col-xl">

        <div class="dashboard-card mini-stat">
            <span>Active</span>
            <strong>{{ stats.active }}</strong>
        </div>

    </div>

    <div class="col-md-6 col-xl">

        <div class="dashboard-card mini-stat">
            <span>In Transit</span>
            <strong>{{ stats.in_transit }}</strong>
        </div>

    </div>

    <div class="col-md-6 col-xl">

        <div class="dashboard-card mini-stat">
            <span>Ready Collection</span>
            <strong>{{ stats.ready_collection }}</strong>
        </div>

    </div>

    <div class="col-md-6 col-xl">

        <div class="dashboard-card mini-stat">
            <span>Completed</span>
            <strong>{{ stats.completed }}</strong>
        </div>

    </div>

</div>


<div class="dashboard-card mb-4">

    <div class="card-header-custom">

        <div>
            <h2>Find Deliveries</h2>
            <p>Search order, customer, provider, destination or parcel reference.</p>
        </div>

    </div>

    <form method="GET">

        <div class="row g-3">

            <div class="col-lg-6">

                <label class="form-label">
                    Search
                </label>

                <input
                    name="q"
                    value="{{ query }}"
                    class="form-control"
                    placeholder="Order, phone, provider, destination, parcel reference..."
                >

            </div>

            <div class="col-lg-3">

                <label class="form-label">
                    Management
                </label>

                <select
                    name="management"
                    class="form-select"
                >

                    <option value="">All</option>

                    <option
                        value="internal"
                        {% if selected_management == "internal" %}selected{% endif %}
                    >
                        Shop Managed
                    </option>

                    <option
                        value="external"
                        {% if selected_management == "external" %}selected{% endif %}
                    >
                        External Provider
                    </option>

                </select>

            </div>

            <div class="col-lg-3">

                <label class="form-label">
                    Status
                </label>

                <select
                    name="status"
                    class="form-select"
                >

                    <option value="">All Statuses</option>

                    {% for value, label in status_choices %}

                        <option
                            value="{{ value }}"
                            {% if selected_status == value %}selected{% endif %}
                        >
                            {{ label }}
                        </option>

                    {% endfor %}

                </select>

            </div>

        </div>

        <div class="mt-3">

            <button
                type="submit"
                class="btn btn-primary"
            >
                <i class="bi bi-funnel"></i>
                Apply Filters
            </button>

            <a
                href="{% url 'delivery_list' %}"
                class="btn btn-outline-secondary"
            >
                Reset
            </a>

        </div>

    </form>

</div>


<div class="dashboard-card">

    <div class="card-header-custom">

        <div>
            <h2>Deliveries</h2>
            <p>Current parcel and rider activity.</p>
        </div>

    </div>

    <div class="table-responsive">

        <table class="table dashboard-table align-middle">

            <thead>

                <tr>
                    <th>Order</th>
                    <th>Customer</th>
                    <th>Type</th>
                    <th>Provider</th>
                    <th>Destination</th>
                    <th>Reference</th>
                    <th>Status</th>
                    <th class="text-end">Action</th>
                </tr>

            </thead>

            <tbody>

                {% for delivery in deliveries %}

                <tr>

                    <td>
                        <strong>
                            {{ delivery.order.order_number }}
                        </strong>
                    </td>

                    <td>

                        {{ delivery.order.full_name }}

                        <small class="d-block text-muted">
                            {{ delivery.order.phone }}
                        </small>

                    </td>

                    <td>
                        {{ delivery.get_management_type_display }}
                    </td>

                    <td>
                        {{ delivery.provider.name|default:"Shop / Internal" }}
                    </td>

                    <td>
                        {{ delivery.destination }}
                    </td>

                    <td>

                        {% if delivery.transport_reference %}

                            <code>
                                {{ delivery.transport_reference }}
                            </code>

                        {% else %}
                            —
                        {% endif %}

                    </td>

                    <td>

                        {% if delivery.status == "delivered" or delivery.status == "collected" %}

                            <span class="badge text-bg-success">
                                {{ delivery.get_status_display }}
                            </span>

                        {% elif delivery.status == "failed" %}

                            <span class="badge text-bg-danger">
                                {{ delivery.get_status_display }}
                            </span>

                        {% elif delivery.status == "ready_for_collection" %}

                            <span class="badge text-bg-info">
                                Ready for Collection
                            </span>

                        {% else %}

                            <span class="badge text-bg-primary">
                                {{ delivery.get_status_display }}
                            </span>

                        {% endif %}

                    </td>

                    <td class="text-end">

                        <a
                            href="{% url 'delivery_detail' delivery.pk %}"
                            class="btn btn-sm btn-outline-primary"
                        >
                            View
                        </a>

                    </td>

                </tr>

                {% empty %}

                <tr>

                    <td
                        colspan="8"
                        class="text-center py-5"
                    >

                        <i class="bi bi-truck fs-1 text-muted"></i>

                        <h5 class="mt-3">
                            No deliveries yet
                        </h5>

                        <p class="text-muted mb-0">
                            Assign delivery from an order.
                        </p>

                    </td>

                </tr>

                {% endfor %}

            </tbody>

        </table>

    </div>


    {% if page_obj.paginator.num_pages > 1 %}

        <div class="d-flex justify-content-between align-items-center flex-wrap gap-3 pt-3 border-top">

            <small class="text-muted">
                Page {{ page_obj.number }}
                of {{ page_obj.paginator.num_pages }}
            </small>

            <div class="d-flex gap-2">

                {% if page_obj.has_previous %}

                    <a
                        class="btn btn-sm btn-outline-secondary"
                        href="?page={{ page_obj.previous_page_number }}&q={{ query|urlencode }}&status={{ selected_status|urlencode }}&management={{ selected_management|urlencode }}"
                    >
                        Previous
                    </a>

                {% endif %}

                {% if page_obj.has_next %}

                    <a
                        class="btn btn-sm btn-outline-secondary"
                        href="?page={{ page_obj.next_page_number }}&q={{ query|urlencode }}&status={{ selected_status|urlencode }}&management={{ selected_management|urlencode }}"
                    >
                        Next
                    </a>

                {% endif %}

            </div>

        </div>

    {% endif %}

</div>

{% endblock %}
'''.strip() + "\n",
encoding="utf-8"
)


# ============================================================
# ASSIGN TEMPLATE
# ============================================================

(templates / "assign.html").write_text(
r'''
{% extends "dashboard/admin/base.html" %}

{% block title %}
Delivery | {{ order.order_number }}
{% endblock %}

{% block page_heading %}
Assign Delivery
{% endblock %}

{% block admin_content %}

<div class="dashboard-heading">

    <div class="d-flex justify-content-between align-items-start flex-wrap gap-3">

        <div>

            <h1>
                {% if delivery %}
                    Edit Delivery
                {% else %}
                    Assign Delivery
                {% endif %}
            </h1>

            <p>
                Order {{ order.order_number }}
                · {{ order.full_name }}
            </p>

        </div>

        <a
            href="{% url 'admin_order_detail' order.order_number %}"
            class="btn btn-outline-secondary"
        >
            <i class="bi bi-arrow-left"></i>
            Back to Order
        </a>

    </div>

</div>


<div class="row g-3">

    <div class="col-xl-8">

        <div class="dashboard-card">

            <div class="card-header-custom">

                <div>
                    <h2>Delivery Assignment</h2>
                    <p>
                        Choose whether this delivery is controlled
                        by the shop or an external provider.
                    </p>
                </div>

            </div>

            <form method="POST">

                {% csrf_token %}

                <div class="row g-3">

                    <div class="col-md-6">

                        <label class="form-label">
                            Managed By
                        </label>

                        {{ form.management_type }}

                        {% for error in form.management_type.errors %}
                            <div class="text-danger small">{{ error }}</div>
                        {% endfor %}

                    </div>

                    <div class="col-md-6">

                        <label class="form-label">
                            Delivery Method
                        </label>

                        {{ form.method }}

                    </div>

                    <div class="col-md-6">

                        <label class="form-label">
                            Transport Provider
                        </label>

                        {{ form.provider }}

                        <div class="form-text">
                            Required for external delivery.
                        </div>

                        {% for error in form.provider.errors %}
                            <div class="text-danger small">{{ error }}</div>
                        {% endfor %}

                    </div>

                    <div class="col-md-6">

                        <label class="form-label">
                            Provider / Parcel Reference
                        </label>

                        {{ form.transport_reference }}

                    </div>

                    <div class="col-md-6">

                        <label class="form-label">
                            Origin
                        </label>

                        {{ form.origin }}

                    </div>

                    <div class="col-md-6">

                        <label class="form-label">
                            Destination
                        </label>

                        {{ form.destination }}

                    </div>

                    <div class="col-12">

                        <label class="form-label">
                            Pickup Point / Parcel Office
                        </label>

                        {{ form.pickup_point }}

                        {% for error in form.pickup_point.errors %}
                            <div class="text-danger small">{{ error }}</div>
                        {% endfor %}

                    </div>

                    <div class="col-md-6">

                        <label class="form-label">
                            Rider / Driver Name
                        </label>

                        {{ form.driver_name }}

                    </div>

                    <div class="col-md-6">

                        <label class="form-label">
                            Rider / Driver Phone
                        </label>

                        {{ form.driver_phone }}

                    </div>

                    <div class="col-md-6">

                        <label class="form-label">
                            Customer Delivery Fee
                        </label>

                        {{ form.customer_delivery_fee }}

                    </div>

                    <div class="col-md-6">

                        <label class="form-label">
                            Actual Delivery Cost
                        </label>

                        {{ form.actual_delivery_cost }}

                    </div>

                    <div class="col-md-6">

                        <label class="form-label">
                            Expected Arrival
                        </label>

                        {{ form.expected_arrival }}

                    </div>

                    <div class="col-12">

                        <label class="form-label">
                            Delivery Notes
                        </label>

                        {{ form.notes }}

                    </div>

                </div>

                {% if form.non_field_errors %}

                    <div class="alert alert-danger mt-3">
                        {{ form.non_field_errors }}
                    </div>

                {% endif %}

                <div class="mt-4">

                    <button
                        type="submit"
                        class="btn btn-primary"
                    >
                        <i class="bi bi-check-lg"></i>

                        {% if delivery %}
                            Save Delivery
                        {% else %}
                            Assign Delivery
                        {% endif %}
                    </button>

                </div>

            </form>

        </div>

    </div>


    <div class="col-xl-4">

        <div class="dashboard-card">

            <div class="card-header-custom">

                <div>
                    <h2>Customer Destination</h2>
                </div>

            </div>

            <strong>
                {{ order.full_name }}
            </strong>

            <div class="mt-2">
                {{ order.phone }}
            </div>

            <hr>

            <div>
                {{ order.house_number }}
            </div>

            <div>
                {{ order.estate }}
            </div>

            <div>
                {{ order.city }}
            </div>

            <div>
                {{ order.county }}
            </div>

            {% if order.landmark %}

                <div class="mt-2 text-muted">
                    Landmark:
                    {{ order.landmark }}
                </div>

            {% endif %}

            <hr>

            <div class="small text-muted">

                External providers do not use
                the shop's delivery PIN.

                Their parcel/reference number
                and pickup information are recorded instead.

            </div>

        </div>

    </div>

</div>

{% endblock %}
'''.strip() + "\n",
encoding="utf-8"
)


# ============================================================
# DETAIL TEMPLATE
# ============================================================

(templates / "detail.html").write_text(
r'''
{% extends "dashboard/admin/base.html" %}

{% block title %}
Delivery | {{ order.order_number }}
{% endblock %}

{% block page_heading %}
Delivery Details
{% endblock %}

{% block admin_content %}

<div class="dashboard-heading">

    <div class="d-flex justify-content-between align-items-start flex-wrap gap-3">

        <div>

            <h1>
                {{ order.order_number }}
            </h1>

            <p>
                {{ delivery.get_management_type_display }}
                · {{ delivery.get_method_display }}
            </p>

        </div>

        <div class="d-flex gap-2 flex-wrap">

            <a
                href="{% url 'delivery_assign' order.order_number %}"
                class="btn btn-outline-primary"
            >
                <i class="bi bi-pencil"></i>
                Edit Delivery
            </a>

            <a
                href="{% url 'admin_order_detail' order.order_number %}"
                class="btn btn-outline-secondary"
            >
                View Order
            </a>

        </div>

    </div>

</div>


<div class="row g-3 mb-4">

    <div class="col-md-6 col-xl-3">

        <div class="dashboard-card mini-stat">
            <span>Status</span>
            <strong class="fs-6">
                {{ delivery.get_status_display }}
            </strong>
        </div>

    </div>

    <div class="col-md-6 col-xl-3">

        <div class="dashboard-card mini-stat">
            <span>Provider</span>
            <strong class="fs-6">
                {{ delivery.provider.name|default:"Shop / Internal" }}
            </strong>
        </div>

    </div>

    <div class="col-md-6 col-xl-3">

        <div class="dashboard-card mini-stat">
            <span>Charged</span>
            <strong>
                KES {{ delivery.customer_delivery_fee|floatformat:2 }}
            </strong>
        </div>

    </div>

    <div class="col-md-6 col-xl-3">

        <div class="dashboard-card mini-stat">
            <span>Delivery Margin</span>
            <strong>
                KES {{ delivery.delivery_margin|floatformat:2 }}
            </strong>
        </div>

    </div>

</div>


<div class="row g-3 mb-4">

    <div class="col-xl-7">

        <div class="dashboard-card h-100">

            <div class="card-header-custom">

                <div>
                    <h2>Delivery Information</h2>
                    <p>Transport and customer destination details.</p>
                </div>

            </div>

            <div class="table-responsive">

                <table class="table dashboard-table mb-0">

                    <tbody>

                        <tr>
                            <th>Managed By</th>
                            <td>{{ delivery.get_management_type_display }}</td>
                        </tr>

                        <tr>
                            <th>Method</th>
                            <td>{{ delivery.get_method_display }}</td>
                        </tr>

                        <tr>
                            <th>Provider</th>
                            <td>{{ delivery.provider.name|default:"Shop / Internal" }}</td>
                        </tr>

                        <tr>
                            <th>Parcel Reference</th>
                            <td>
                                {% if delivery.transport_reference %}
                                    <code>{{ delivery.transport_reference }}</code>
                                {% else %}
                                    —
                                {% endif %}
                            </td>
                        </tr>

                        <tr>
                            <th>Origin</th>
                            <td>{{ delivery.origin|default:"—" }}</td>
                        </tr>

                        <tr>
                            <th>Destination</th>
                            <td>{{ delivery.destination }}</td>
                        </tr>

                        <tr>
                            <th>Pickup Point</th>
                            <td>{{ delivery.pickup_point|default:"—" }}</td>
                        </tr>

                        <tr>
                            <th>Driver / Rider</th>
                            <td>{{ delivery.driver_name|default:"—" }}</td>
                        </tr>

                        <tr>
                            <th>Driver Phone</th>
                            <td>{{ delivery.driver_phone|default:"—" }}</td>
                        </tr>

                        <tr>
                            <th>Expected Arrival</th>
                            <td>
                                {% if delivery.expected_arrival %}
                                    {{ delivery.expected_arrival|date:"d M Y H:i" }}
                                {% else %}
                                    —
                                {% endif %}
                            </td>
                        </tr>

                    </tbody>

                </table>

            </div>

        </div>

    </div>


    <div class="col-xl-5">

        <div class="dashboard-card h-100">

            <div class="card-header-custom">

                <div>
                    <h2>Update Status</h2>
                    <p>Record the real delivery progress.</p>
                </div>

            </div>

            {% if allowed_statuses %}

                <form
                    method="POST"
                    action="{% url 'delivery_update_status' delivery.pk %}"
                >

                    {% csrf_token %}

                    <label class="form-label">
                        Next Status
                    </label>

                    <select
                        name="status"
                        class="form-select"
                        required
                    >

                        <option value="">
                            Choose...
                        </option>

                        {% for value, label in allowed_statuses %}

                            <option value="{{ value }}">
                                {{ label }}
                            </option>

                        {% endfor %}

                    </select>

                    <label class="form-label mt-3">
                        Timeline Message
                    </label>

                    <textarea
                        name="message"
                        class="form-control"
                        rows="3"
                        placeholder="e.g. Parcel loaded in Nairobi for Kisii."
                    ></textarea>

                    <button
                        type="submit"
                        class="btn btn-primary mt-3"
                    >
                        Update Delivery
                    </button>

                </form>

            {% else %}

                <div class="alert alert-light border mb-0">

                    This delivery is currently in
                    a final state:

                    <strong>
                        {{ delivery.get_status_display }}
                    </strong>

                </div>

            {% endif %}

        </div>

    </div>

</div>


<div class="row g-3">

    <div class="col-xl-7">

        <div class="dashboard-card">

            <div class="card-header-custom">

                <div>
                    <h2>Delivery Timeline</h2>
                    <p>Chronological delivery activity.</p>
                </div>

            </div>

            {% for event in events %}

                <div class="border-start border-3 ps-3 pb-4">

                    <strong>
                        {{ event.get_status_display }}
                    </strong>

                    <small class="d-block text-muted">
                        {{ event.created_at|date:"d M Y H:i" }}

                        {% if event.created_by %}
                            · {{ event.created_by.username }}
                        {% endif %}
                    </small>

                    {% if event.message %}

                        <div class="mt-2">
                            {{ event.message }}
                        </div>

                    {% endif %}

                </div>

            {% empty %}

                <p class="text-muted">
                    No delivery events yet.
                </p>

            {% endfor %}

        </div>

    </div>


    <div class="col-xl-5">

        <div class="dashboard-card">

            <div class="card-header-custom">

                <div>
                    <h2>Delivery Attempt</h2>
                    <p>Record failed or successful delivery attempts.</p>
                </div>

            </div>

            <form
                method="POST"
                action="{% url 'delivery_add_attempt' delivery.pk %}"
            >

                {% csrf_token %}

                <label class="form-label">
                    Result
                </label>

                {{ attempt_form.result }}

                <label class="form-label mt-3">
                    Notes
                </label>

                {{ attempt_form.notes }}

                <button
                    type="submit"
                    class="btn btn-outline-primary mt-3"
                >
                    Record Attempt
                </button>

            </form>


            {% if attempts %}

                <hr>

                {% for attempt in attempts %}

                    <div class="mb-3">

                        <strong>
                            {{ attempt.get_result_display }}
                        </strong>

                        <small class="d-block text-muted">
                            {{ attempt.created_at|date:"d M Y H:i" }}
                        </small>

                        {% if attempt.notes %}
                            <div class="small mt-1">
                                {{ attempt.notes }}
                            </div>
                        {% endif %}

                    </div>

                {% endfor %}

            {% endif %}

        </div>

    </div>

</div>

{% endblock %}
'''.strip() + "\n",
encoding="utf-8"
)


# ============================================================
# PROVIDERS TEMPLATE
# ============================================================

(templates / "providers.html").write_text(
r'''
{% extends "dashboard/admin/base.html" %}

{% block title %}
Delivery Providers
{% endblock %}

{% block page_heading %}
Delivery Providers
{% endblock %}

{% block admin_content %}

<div class="dashboard-heading">

    <div class="d-flex justify-content-between align-items-start flex-wrap gap-3">

        <div>

            <h1>
                Delivery Providers
            </h1>

            <p>
                Manage transport companies, riders,
                coaches, shuttles and courier services.
            </p>

        </div>

        <div class="d-flex gap-2">

            <a
                href="{% url 'delivery_list' %}"
                class="btn btn-outline-secondary"
            >
                Delivery
            </a>

            <a
                href="{% url 'delivery_provider_create' %}"
                class="btn btn-primary"
            >
                <i class="bi bi-plus-lg"></i>
                Add Provider
            </a>

        </div>

    </div>

</div>


<div class="dashboard-card">

    <div class="table-responsive">

        <table class="table dashboard-table align-middle">

            <thead>

                <tr>
                    <th>Provider</th>
                    <th>Type</th>
                    <th>Phone</th>
                    <th>Status</th>
                    <th class="text-end">Actions</th>
                </tr>

            </thead>

            <tbody>

                {% for provider in providers %}

                <tr>

                    <td>
                        <strong>
                            {{ provider.name }}
                        </strong>
                    </td>

                    <td>
                        {{ provider.get_provider_type_display }}
                    </td>

                    <td>
                        {{ provider.phone|default:"—" }}
                    </td>

                    <td>

                        {% if provider.is_active %}

                            <span class="badge text-bg-success">
                                Active
                            </span>

                        {% else %}

                            <span class="badge text-bg-secondary">
                                Inactive
                            </span>

                        {% endif %}

                    </td>

                    <td class="text-end">

                        <a
                            href="{% url 'delivery_provider_edit' provider.pk %}"
                            class="btn btn-sm btn-outline-primary"
                        >
                            Edit
                        </a>

                        <form
                            method="POST"
                            action="{% url 'delivery_provider_toggle' provider.pk %}"
                            class="d-inline"
                        >

                            {% csrf_token %}

                            <button
                                type="submit"
                                class="btn btn-sm btn-outline-secondary"
                            >
                                {% if provider.is_active %}
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
                        colspan="5"
                        class="text-center py-5"
                    >
                        No delivery providers added yet.
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
# PROVIDER FORM
# ============================================================

(templates / "provider_form.html").write_text(
r'''
{% extends "dashboard/admin/base.html" %}

{% block title %}
{{ title }}
{% endblock %}

{% block page_heading %}
Delivery Provider
{% endblock %}

{% block admin_content %}

<div class="dashboard-heading">

    <div>

        <h1>
            {{ title }}
        </h1>

        <p>
            Add providers without requiring an API integration.
        </p>

    </div>

</div>


<div class="dashboard-card">

    <form method="POST">

        {% csrf_token %}

        <div class="row g-3">

            <div class="col-md-6">

                <label class="form-label">
                    Provider Name
                </label>

                {{ form.name }}

                {{ form.name.errors }}

            </div>

            <div class="col-md-6">

                <label class="form-label">
                    Provider Type
                </label>

                {{ form.provider_type }}

            </div>

            <div class="col-md-6">

                <label class="form-label">
                    Phone
                </label>

                {{ form.phone }}

            </div>

            <div class="col-md-6">

                <label class="form-label">
                    Email
                </label>

                {{ form.email }}

            </div>

            <div class="col-12">

                <label class="form-label">
                    Website
                </label>

                {{ form.website }}

            </div>

            <div class="col-12">

                <label class="form-label">
                    Notes
                </label>

                {{ form.notes }}

            </div>

            <div class="col-12">

                <div class="form-check">

                    {{ form.is_active }}

                    <label class="form-check-label">
                        Active Provider
                    </label>

                </div>

            </div>

        </div>

        <div class="mt-4">

            <button
                type="submit"
                class="btn btn-primary"
            >
                Save Provider
            </button>

            <a
                href="{% url 'delivery_provider_list' %}"
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
# SETTINGS
# ============================================================

settings_path = ROOT / "config" / "settings.py"

settings_text = settings_path.read_text(
    encoding="utf-8-sig"
)

if "'delivery'," not in settings_text:

    marker = "'payments',"

    if marker not in settings_text:
        marker = '"payments",'

    if marker not in settings_text:
        raise RuntimeError(
            "Could not locate payments in INSTALLED_APPS."
        )

    settings_text = settings_text.replace(
        marker,
        marker + "\n    'delivery',",
        1,
    )

    settings_path.write_text(
        settings_text,
        encoding="utf-8",
    )

    print("Added delivery to INSTALLED_APPS.")


# ============================================================
# ROOT URLS
# ============================================================

urls_path = ROOT / "config" / "urls.py"

urls_text = urls_path.read_text(
    encoding="utf-8-sig"
)

urls_text = re.sub(
    r"from django\.urls import[^\n]+",
    "from django.urls import include, path",
    urls_text,
    count=1,
)

if 'include("delivery.urls")' not in urls_text:

    marker = "urlpatterns = ["

    route = '''
    path(
        "dashboard/admin/delivery/",
        include("delivery.urls"),
    ),
'''

    if marker not in urls_text:
        raise RuntimeError(
            "Could not locate urlpatterns."
        )

    urls_text = urls_text.replace(
        marker,
        marker + route,
        1,
    )

urls_path.write_text(
    urls_text,
    encoding="utf-8",
)

print("Connected delivery URLs.")


# ============================================================
# RESPONSIVE SIDEBAR
# ============================================================

base_path = (
    ROOT
    / "templates"
    / "dashboard"
    / "admin"
    / "base.html"
)

base_text = base_path.read_text(
    encoding="utf-8-sig"
)

if "delivery_list" not in base_text:

    match = re.search(
        r'<a\b[^>]*>.*?<span>\s*Delivery\s*</span>.*?</a>',
        base_text,
        flags=re.S,
    )

    replacement = r'''<a
                href="{% url 'delivery_list' %}"
                class="
                    sidebar-link
                    {% if 'delivery_' in request.resolver_match.url_name %}
                        active
                    {% endif %}
                "
            >

                <i class="bi bi-truck"></i>

                <span>
                    Delivery
                </span>

            </a>'''

    if match:

        base_text = (
            base_text[:match.start()]
            + replacement
            + base_text[match.end():]
        )

    else:

        delivery_span = base_text.find(
            "<span>Delivery</span>"
        )

        if delivery_span == -1:

            delivery_span = base_text.find(
                "Delivery"
            )

        if delivery_span == -1:
            raise RuntimeError(
                "Could not locate Delivery sidebar item."
            )

        start = base_text.rfind(
            "<a",
            0,
            delivery_span,
        )

        end = base_text.find(
            "</a>",
            delivery_span,
        )

        if start == -1 or end == -1:
            raise RuntimeError(
                "Could not identify Delivery link boundaries."
            )

        end += 4

        base_text = (
            base_text[:start]
            + replacement
            + base_text[end:]
        )

    base_path.write_text(
        base_text,
        encoding="utf-8",
    )

    print("Activated Delivery sidebar.")
else:
    print("Delivery sidebar already active.")


# ============================================================
# TESTS
# ============================================================

(delivery / "tests.py").write_text(
r'''
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from orders.models import Order

from .models import (
    Delivery,
    DeliveryProvider,
)


User = get_user_model()


class DeliveryManagementTests(TestCase):

    def setUp(self):

        self.staff = User.objects.create_user(
            username="deliverystaff",
            password="testpass123",
            role=User.ADMIN,
            is_staff=True,
        )

        self.customer = User.objects.create_user(
            username="deliverycustomer",
            password="testpass123",
            role=User.CUSTOMER,
        )

        self.order = Order.objects.create(
            user=self.customer,
            order_number="DELIVERY-TEST-001",
            full_name="Delivery Customer",
            phone="0712345678",
            email="customer@example.com",
            county="Kisii",
            city="Kisii",
            estate="Town",
            house_number="1",
            subtotal=Decimal("3000.00"),
            shipping_cost=Decimal("500.00"),
            discount=Decimal("0.00"),
            total_amount=Decimal("3500.00"),
            status="processing",
            payment_status="paid",
            inventory_status="consumed",
        )

        self.provider = (
            DeliveryProvider.objects.create(
                name="Test Coach",
                provider_type="bus_coach",
                is_active=True,
            )
        )

    def test_staff_can_open_delivery_list(self):

        self.client.login(
            username="deliverystaff",
            password="testpass123",
        )

        response = self.client.get(
            reverse("delivery_list")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_external_delivery_can_be_assigned(self):

        self.client.login(
            username="deliverystaff",
            password="testpass123",
        )

        response = self.client.post(
            reverse(
                "delivery_assign",
                kwargs={
                    "order_number": (
                        self.order.order_number
                    )
                },
            ),
            {
                "management_type": "external",
                "method": "station_pickup",
                "provider": self.provider.pk,
                "origin": "Nairobi",
                "destination": "Kisii",
                "pickup_point": "Kisii Parcel Office",
                "transport_reference": "PARCEL-001",
                "driver_name": "",
                "driver_phone": "",
                "customer_delivery_fee": "500.00",
                "actual_delivery_cost": "450.00",
                "expected_arrival": "",
                "notes": "",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        delivery = Delivery.objects.get(
            order=self.order
        )

        self.assertEqual(
            delivery.provider,
            self.provider,
        )

        self.assertEqual(
            delivery.status,
            "assigned",
        )

        self.assertEqual(
            delivery.transport_reference,
            "PARCEL-001",
        )
'''.strip() + "\n",
encoding="utf-8"
)


print()
print("=" * 70)
print("PHASE 7A DELIVERY SYSTEM CREATED")
print("=" * 70)
print()
print("Next:")
print("python manage.py makemigrations delivery")
print("python manage.py migrate")
print("python manage.py check")
