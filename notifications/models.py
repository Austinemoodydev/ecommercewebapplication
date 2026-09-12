from django.conf import settings
from django.db import models


class Notification(models.Model):

    CATEGORY_CHOICES = [
        ("general", "General"),
        ("orders", "Order Updates"),
        ("payments", "Payment Updates"),
        ("delivery", "Delivery Updates"),
        ("returns", "Returns & Refunds"),
        ("marketing", "Marketing"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("failed", "Failed"),
        ("partial", "Partially Delivered"),
    ]

    CHANNEL_STATUS_CHOICES = [
        ("not_requested", "Not Requested"),
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("failed", "Failed"),
        ("skipped", "Skipped"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    order_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )

    channel = models.CharField(
        max_length=20,
        default="email",
    )

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="general",
        db_index=True,
    )

    event_key = models.CharField(
        max_length=190,
        null=True,
        blank=True,
        unique=True,
        db_index=True,
    )

    subject = models.CharField(
        max_length=200,
    )

    message = models.TextField()

    sms_message = models.TextField(
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )


    email_status = models.CharField(
        max_length=20,
        choices=CHANNEL_STATUS_CHOICES,
        default="not_requested",
        db_index=True,
    )

    sms_status = models.CharField(
        max_length=20,
        choices=CHANNEL_STATUS_CHOICES,
        default="not_requested",
        db_index=True,
    )

    email_attempts = models.PositiveIntegerField(
        default=0,
    )

    sms_attempts = models.PositiveIntegerField(
        default=0,
    )

    email_sent_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    sms_sent_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    email_error = models.TextField(
        blank=True,
    )

    sms_error = models.TextField(
        blank=True,
    )

    attempts = models.PositiveIntegerField(
        default=0,
    )

    last_error = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    sent_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    read_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-created_at",
        ]

    @property
    def is_read(self):
        return self.read_at is not None

    def __str__(self):
        return (
            f"{self.subject} - "
            f"{self.status}"
        )


class NotificationPreference(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )

    # Master delivery channels
    email_enabled = models.BooleanField(
        default=True,
    )

    sms_enabled = models.BooleanField(
        default=True,
    )

    # Transactional categories
    order_updates = models.BooleanField(
        default=True,
    )

    payment_updates = models.BooleanField(
        default=True,
    )

    delivery_updates = models.BooleanField(
        default=True,
    )

    return_refund_updates = models.BooleanField(
        default=True,
    )

    # Optional marketing communication
    marketing_email = models.BooleanField(
        default=False,
    )

    marketing_sms = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return (
            "Notification preferences - "
            f"{self.user}"
        )
