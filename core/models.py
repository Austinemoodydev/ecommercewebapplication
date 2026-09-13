from decimal import Decimal

from django.conf import settings
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models


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
        default="Online Shop",
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
