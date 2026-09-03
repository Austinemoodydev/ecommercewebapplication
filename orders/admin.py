from django.contrib import admin
from django.db import transaction
from .models import Order, OrderItem, DeliveryArea, Coupon
from products.models import Product


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "price", "quantity", "subtotal")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    list_display = ("order_number", "user", "total_amount", "status", "payment_status", "courier", "tracking_number", "created_at")
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
        previous_status = Order.objects.filter(pk=obj.pk).values_list("status", flat=True).first() if change else None
        super().save_model(request, obj, form, change)
        if change and previous_status != obj.status:
            from notifications.tasks import send_order_status_notification
            transaction.on_commit(lambda: send_order_status_notification.delay(obj.pk))

    @admin.action(description="Mark selected orders as Processing")
    def mark_processing(self, request, queryset):
        updated = 0
        for order in queryset:
            if order.status != "processing":
                order.status = "processing"
                self.save_model(request, order, form=None, change=True)
                updated += 1
        self.message_user(request, f"{updated} order(s) marked as Processing.")

    @admin.action(description="Mark selected orders as Shipped")
    def mark_shipped(self, request, queryset):
        updated = 0
        for order in queryset:
            if order.status != "shipped":
                order.status = "shipped"
                self.save_model(request, order, form=None, change=True)
                updated += 1
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
        updated = 0
        for order in queryset.select_for_update():
            if order.status != "pending" or order.payment_status != "pending":
                continue
            with transaction.atomic():
                for order_item in order.items.all():
                    inventory = order_item.variant.__class__.objects.select_for_update().get(id=order_item.variant_id) if order_item.variant_id else Product.objects.select_for_update().get(id=order_item.product_id)
                    inventory.reserved_stock = max(inventory.reserved_stock - order_item.quantity, 0)
                    inventory.save(update_fields=["reserved_stock"] + (["updated_at"] if not order_item.variant_id else []))
                order.status = "cancelled"
                self.save_model(request, order, form=None, change=True)
                updated += 1
        self.message_user(request, f"{updated} unpaid pending order(s) cancelled.")


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

