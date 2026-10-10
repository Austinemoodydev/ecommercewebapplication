from decimal import Decimal

from django.conf import settings
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
    RegexValidator,
)
from django.db import models
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone


class ErrorReport(models.Model):
    reference = models.CharField(max_length=12, unique=True, db_index=True)
    path = models.CharField(max_length=500)
    method = models.CharField(max_length=10)
    status_code = models.PositiveSmallIntegerField(default=500)
    exception_type = models.CharField(max_length=150)
    message = models.TextField(blank=True)
    traceback = models.TextField(blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="error_reports",
    )
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.reference} — {self.exception_type}"


class StoreSettings(models.Model):

    """
    Singleton business configuration.

    The application always uses primary key 1.
    """

    SINGLETON_PK = 1


    # --------------------------------------------------------
    # BUSINESS IDENTITY
    # --------------------------------------------------------

    store_name = models.CharField(
        max_length=150,
        default="",
    )

    legal_name = models.CharField(
        max_length=200,
        blank=True,
    )


    business_registration_number = models.CharField(
        max_length=100,
        blank=True,
        help_text=(
            "Optional company or business "
            "registration number."
        ),
    )

    tax_pin = models.CharField(
        max_length=100,
        blank=True,
        help_text=(
            "Optional tax/KRA PIN shown on "
            "business documents."
        ),
    )


    # --------------------------------------------------------
    # CONTACT DETAILS
    # --------------------------------------------------------

    support_email = models.EmailField(
        blank=True,
    )

    support_phone = models.CharField(
        max_length=30,
        blank=True,
    )

    whatsapp_number = models.CharField(
        max_length=30,
        blank=True,
    )

    website_url = models.URLField(
        blank=True,
    )


    # --------------------------------------------------------
    # BUSINESS LOCATION
    # --------------------------------------------------------

    address = models.CharField(
        max_length=255,
        blank=True,
    )

    city = models.CharField(
        max_length=100,
        blank=True,
    )

    county = models.CharField(
        max_length=100,
        blank=True,
    )

    country = models.CharField(
        max_length=100,
        default="Kenya",
    )


    # --------------------------------------------------------
    # CURRENCY / FINANCE
    # --------------------------------------------------------

    currency_code = models.CharField(
        max_length=10,
        default="KES",
    )

    currency_symbol = models.CharField(
        max_length=10,
        default="KSh",
    )

    tax_enabled = models.BooleanField(
        default=False,
    )

    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(
                Decimal("0.00")
            ),
            MaxValueValidator(
                Decimal("100.00")
            ),
        ],
        help_text="Percentage from 0 to 100.",
    )


    # --------------------------------------------------------
    # ORDER SETTINGS
    # --------------------------------------------------------

    orders_enabled = models.BooleanField(
        default=True,
    )


    checkout_closed_message = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=(
            "Optional message shown when "
            "online ordering is disabled."
        ),
    )

    minimum_order_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(
                Decimal("0.00")
            ),
        ],
    )


    # --------------------------------------------------------
    # DOCUMENT SETTINGS
    # --------------------------------------------------------

    invoice_prefix = models.CharField(
        max_length=20,
        default="INV",
        blank=True,
    )

    receipt_prefix = models.CharField(
        max_length=20,
        default="RCP",
        blank=True,
    )

    credit_note_prefix = models.CharField(
        max_length=20,
        default="CN",
        blank=True,
    )


    document_footer = models.TextField(
        blank=True,
        default=(
            "Thank you for shopping with us."
        ),
    )


    # --------------------------------------------------------
    # AUDIT
    # --------------------------------------------------------

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=(
            "store_settings_updates"
        ),
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )


    class Meta:

        verbose_name = (
            "Store Settings"
        )

        verbose_name_plural = (
            "Store Settings"
        )


    def save(
        self,
        *args,
        **kwargs,
    ):

        # Enforce singleton storage.
        self.pk = self.SINGLETON_PK

        self.currency_code = (
            self.currency_code
            .strip()
            .upper()
        )

        super().save(
            *args,
            **kwargs,
        )


    def delete(
        self,
        *args,
        **kwargs,
    ):

        # Business configuration should never
        # disappear accidentally.
        return


    def __str__(self):

        return self.store_name


hex_colour = RegexValidator(
    regex=r"^#[0-9A-Fa-f]{6}$",
    message="Enter a six-digit colour such as #B91C1C.",
)


class MarketingCampaign(models.Model):
    HOLIDAY_TYPES = [
        ("public_holiday", "Kenyan Public Holiday"),
        ("christmas", "Christmas"),
        ("new_year", "New Year"),
        ("religious", "Religious Holiday"),
        ("festive", "Festive Season"),
        ("promotion", "Store Promotion"),
        ("other", "Other"),
    ]
    AUDIENCE_CHOICES = [
        ("all", "All customers"),
        ("registered", "Registered customers"),
        ("previous_buyers", "Previous buyers"),
    ]

    name = models.CharField(max_length=150)
    holiday_type = models.CharField(max_length=30, choices=HOLIDAY_TYPES)
    headline = models.CharField(max_length=180)
    message = models.TextField()
    chatbot_message = models.TextField(blank=True)
    delivery_notice = models.CharField(max_length=255, blank=True)
    store_hours_notice = models.CharField(max_length=255, blank=True)
    starts_at = models.DateTimeField(db_index=True)
    ends_at = models.DateTimeField(db_index=True)
    priority = models.PositiveSmallIntegerField(default=10)
    is_enabled = models.BooleanField(default=True, db_index=True)
    is_verified_holiday = models.BooleanField(default=False)
    official_source_url = models.URLField(blank=True)

    banner_image = models.ImageField(upload_to="campaigns/", blank=True, null=True)
    primary_colour = models.CharField(max_length=7, default="#B91C1C", validators=[hex_colour])
    secondary_colour = models.CharField(max_length=7, default="#15803D", validators=[hex_colour])
    text_colour = models.CharField(max_length=7, default="#FFFFFF", validators=[hex_colour])

    coupon = models.ForeignKey(
        "orders.Coupon",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaigns",
    )
    products = models.ManyToManyField("products.Product", blank=True, related_name="campaigns")
    categories = models.ManyToManyField("categories.Category", blank=True, related_name="campaigns")
    audience = models.CharField(max_length=30, choices=AUDIENCE_CHOICES, default="all")
    show_on_website = models.BooleanField(default=True)
    send_in_app = models.BooleanField(default=False)
    send_email = models.BooleanField(default=False)
    send_sms = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaigns_approved",
    )
    dispatched_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaigns_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaigns_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-starts_at", "-priority"]
        permissions = [
            ("publish_marketingcampaign", "Can approve and publish marketing campaigns"),
            ("send_marketingcampaign", "Can send campaign communications"),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        super().clean()
        if self.ends_at and self.starts_at and self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "The campaign must end after it starts."})
        if self.is_verified_holiday and not self.official_source_url:
            raise ValidationError(
                {"official_source_url": "Add the official source used to verify this holiday."}
            )
        if self.send_sms and len(self.message.strip()) > 1000:
            raise ValidationError({"message": "Keep campaign messages concise for SMS delivery."})
        if self.show_on_website and self.starts_at and self.ends_at:
            overlaps = type(self).objects.filter(
                show_on_website=True,
                is_enabled=True,
                priority=self.priority,
                starts_at__lt=self.ends_at,
                ends_at__gt=self.starts_at,
            )
            if self.pk:
                overlaps = overlaps.exclude(pk=self.pk)
            if overlaps.exists():
                raise ValidationError(
                    "Another site-wide campaign overlaps this schedule at the same priority. "
                    "Change the schedule or assign an explicit higher/lower priority."
                )

    @property
    def is_active_now(self):
        now = timezone.now()
        return bool(
            self.is_enabled
            and self.approved_at
            and self.starts_at <= now < self.ends_at
        )

    def __str__(self):
        return self.name


class CampaignDelivery(models.Model):
    STATUS_CHOICES = [("pending", "Pending"), ("sent", "Sent"), ("failed", "Failed"), ("skipped", "Skipped")]
    campaign = models.ForeignKey(MarketingCampaign, on_delete=models.CASCADE, related_name="deliveries")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="campaign_deliveries")
    channel = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    error = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["campaign", "user", "channel"], name="unique_campaign_user_channel")
        ]


class CampaignAuditEvent(models.Model):
    campaign = models.ForeignKey(MarketingCampaign, on_delete=models.CASCADE, related_name="audit_events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class HomepageSlide(models.Model):
    """An owner-managed, responsive promotion shown on the storefront home page."""

    internal_name = models.CharField(max_length=100, unique=True)
    eyebrow = models.CharField(max_length=80, blank=True)
    heading = models.CharField(max_length=120)
    description = models.CharField(max_length=240, blank=True)
    button_label = models.CharField(max_length=40, default="Shop now")
    image_alt = models.CharField(
        max_length=160,
        help_text="Briefly describe the products pictured for screen-reader users.",
    )
    desktop_image = models.ImageField(upload_to="homepage_slides/desktop/", blank=True)
    mobile_image = models.ImageField(upload_to="homepage_slides/mobile/", blank=True)
    desktop_static_path = models.CharField(max_length=255, blank=True, editable=False)
    mobile_static_path = models.CharField(max_length=255, blank=True, editable=False)
    category = models.ForeignKey(
        "categories.Category", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="homepage_slides",
    )
    product = models.ForeignKey(
        "products.Product", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="homepage_slides",
    )
    destination_url = models.CharField(
        max_length=500,
        blank=True,
        help_text="Optional relative path such as /shop/ or a full https:// address.",
    )
    starts_at = models.DateTimeField(null=True, blank=True, db_index=True)
    ends_at = models.DateTimeField(null=True, blank=True, db_index=True)
    display_order = models.PositiveSmallIntegerField(default=10)
    is_enabled = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "pk"]

    def clean(self):
        from django.core.exceptions import ValidationError

        super().clean()
        errors = {}
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            errors["ends_at"] = "The end time must be later than the start time."
        if not self.desktop_image and not self.desktop_static_path:
            errors["desktop_image"] = "Upload a desktop banner image."
        if self.destination_url:
            value = self.destination_url.strip()
            if not (value.startswith("/") or value.startswith("https://")):
                errors["destination_url"] = "Use a site path beginning with / or a secure https:// URL."
        destinations = sum(bool(value) for value in (self.category_id, self.product_id, self.destination_url.strip()))
        if destinations > 1:
            errors["destination_url"] = "Choose only one destination: category, product, or custom URL."
        if errors:
            raise ValidationError(errors)

    @property
    def desktop_url(self):
        return self.desktop_image.url if self.desktop_image else static(self.desktop_static_path)

    @property
    def mobile_url(self):
        if self.mobile_image:
            return self.mobile_image.url
        if self.mobile_static_path:
            return static(self.mobile_static_path)
        return self.desktop_url

    @property
    def resolved_url(self):
        if self.product_id:
            return reverse("product_detail", kwargs={"slug": self.product.slug})
        if self.category_id:
            return reverse("category_detail", kwargs={"slug": self.category.slug})
        return self.destination_url.strip() or reverse("shop")

    @property
    def is_active_now(self):
        now = timezone.now()
        return bool(
            self.is_enabled
            and (not self.starts_at or self.starts_at <= now)
            and (not self.ends_at or now < self.ends_at)
        )

    def __str__(self):
        return self.internal_name
