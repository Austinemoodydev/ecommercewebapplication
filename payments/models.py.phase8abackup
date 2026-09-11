from django.db import models

from orders.models import Order


class MpesaTransaction(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="mpesa_transactions",
    )

    phone_number = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    merchant_request_id = models.CharField(max_length=100, blank=True)
    checkout_request_id = models.CharField(max_length=100, blank=True, db_index=True)

    mpesa_receipt_number = models.CharField(max_length=50, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    result_code = models.CharField(max_length=10, blank=True)
    result_description = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.order.order_number} - {self.status}"


class RefundRequest(models.Model):
    STATUS_CHOICES = [
        ("requested", "Requested"),
        ("approved", "Approved"),
        ("processed", "Processed"),
        ("rejected", "Rejected"),
    ]

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="refund_requests")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="requested")
    external_reference = models.CharField(max_length=100, blank=True)
    staff_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Refund {self.order.order_number} - {self.status}"

    def clean(self):
        from django.core.exceptions import ValidationError
        from django.db.models import Sum
        if not self.order_id:
            return
        previous = RefundRequest.objects.filter(order=self.order).exclude(pk=self.pk).aggregate(total=Sum("amount"))["total"] or 0
        if previous + self.amount > self.order.total_amount:
            raise ValidationError("Total refunds cannot exceed the order total.")


class ReturnRequest(models.Model):
    TYPE_CHOICES = [("return", "Return"), ("replacement", "Replacement")]
    STATUS_CHOICES = [("requested", "Requested"), ("approved", "Approved"), ("completed", "Completed"), ("rejected", "Rejected")]
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="return_requests")
    request_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="requested")
    staff_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.request_type.title()} {self.order.order_number} - {self.status}"
