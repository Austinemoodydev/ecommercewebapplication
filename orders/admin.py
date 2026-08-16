from django.contrib import admin
from django.db import transaction
from .models import Order, OrderItem, DeliveryArea, Coupon


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "price", "quantity", "subtotal")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    list_display = ("order_number", "user", "total_amount", "status", "payment_status", "created_at")
    list_filter = ("status", "payment_status", "created_at")
    search_fields = ("order_number", "user__username", "phone")
    list_editable = ("status",)

    readonly_fields = (
        "order_number", "user", "subtotal", "shipping_cost",
        "discount", "total_amount", "payment_status", "payment_method",
        "created_at", "updated_at",
    )

    inlines = [OrderItemInline]

    actions = ["mark_processing", "mark_shipped", "mark_delivered", "mark_cancelled"]

    def save_model(self, request, obj, form, change):
        was_delivered = change and Order.objects.filter(pk=obj.pk, status="delivered").exists()
        super().save_model(request, obj, form, change)
        if obj.status == "delivered" and not was_delivered:
            from notifications.tasks import send_delivery_notification
            transaction.on_commit(lambda: send_delivery_notification.delay(obj.pk))

    @admin.action(description="Mark selected orders as Processing")
    def mark_processing(self, request, queryset):
        updated = queryset.update(status="processing")
        self.message_user(request, f"{updated} order(s) marked as Processing.")

    @admin.action(description="Mark selected orders as Shipped")
    def mark_shipped(self, request, queryset):
        updated = queryset.update(status="shipped")
        self.message_user(request, f"{updated} order(s) marked as Shipped.")

    @admin.action(description="Mark selected orders as Delivered")
    def mark_delivered(self, request, queryset):

        count = 0

        for order in queryset:
            if order.status != "delivered":
                order.status = "delivered"
                self.save_model(request, order, form=None, change=True)
                count += 1

        self.message_user(request, f"{count} order(s) marked as Delivered.")

    @admin.action(description="Cancel selected orders")
    def mark_cancelled(self, request, queryset):
        updated = queryset.update(status="cancelled")
        self.message_user(request, f"{updated} order(s) cancelled.")


@admin.register(DeliveryArea)
class DeliveryAreaAdmin(admin.ModelAdmin):

    list_display = ("name", "county", "fee", "is_active")
    list_filter = ("county", "is_active")
    search_fields = ("name",)


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):

    list_display = ("code", "discount_type", "discount_value", "is_active", "times_used", "usage_limit", "valid_until")
    list_filter = ("discount_type", "is_active")
    search_fields = ("code",)

