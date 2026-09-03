from django.contrib import admin
from .models import MpesaTransaction, RefundRequest, ReturnRequest


@admin.register(MpesaTransaction)
class MpesaTransactionAdmin(admin.ModelAdmin):

    list_display = ("order", "phone_number", "amount", "status", "mpesa_receipt_number", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("order__order_number", "phone_number", "checkout_request_id", "mpesa_receipt_number")
    readonly_fields = (
        "order", "phone_number", "amount", "merchant_request_id",
        "checkout_request_id", "mpesa_receipt_number", "result_code",
        "result_description", "created_at", "updated_at",
    )


@admin.register(RefundRequest)
class RefundRequestAdmin(admin.ModelAdmin):
    list_display = ("order", "amount", "status", "external_reference", "created_at", "updated_at")
    list_filter = ("status", "created_at")
    search_fields = ("order__order_number", "external_reference")
    readonly_fields = ("order", "amount", "reason", "created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.status == "processed" and obj.order.payment_status != "refunded":
            obj.order.payment_status = "refunded"
            obj.order.save(update_fields=["payment_status", "updated_at"])


@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display = ("order", "request_type", "status", "created_at", "updated_at")
    list_filter = ("request_type", "status", "created_at")
    search_fields = ("order__order_number",)
    readonly_fields = ("order", "request_type", "reason", "created_at", "updated_at")
