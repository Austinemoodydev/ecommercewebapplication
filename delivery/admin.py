from django.contrib import admin

from .models import (
    Delivery,
    DeliveryAttempt,
    DeliveryEvent,
    DeliveryProvider,
    DeliveryZone,
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
