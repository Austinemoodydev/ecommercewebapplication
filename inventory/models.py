from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from products.models import Product, ProductVariant


class InventoryMovement(models.Model):

    MOVEMENT_TYPES = [
        ("restock", "Restock"),
        ("sale", "Sale"),
        ("adjustment_in", "Adjustment In"),
        ("adjustment_out", "Adjustment Out"),
        ("damaged", "Damaged / Lost"),
        ("return", "Customer Return"),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="inventory_movements",
        null=True,
        blank=True,
    )

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.PROTECT,
        related_name="inventory_movements",
        null=True,
        blank=True,
    )

    movement_type = models.CharField(
        max_length=30,
        choices=MOVEMENT_TYPES,
        db_index=True,
    )

    quantity = models.PositiveIntegerField()

    stock_before = models.PositiveIntegerField()

    stock_after = models.PositiveIntegerField()

    reference = models.CharField(
        max_length=150,
        blank=True,
        db_index=True,
    )

    notes = models.TextField(
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_movements",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at", "-id"]

        indexes = [
            models.Index(
                fields=[
                    "movement_type",
                    "created_at",
                ]
            ),
        ]

    def clean(self):

        if self.product_id and self.variant_id:
            raise ValidationError(
                "A movement cannot target both "
                "a product and a variant."
            )

        if not self.product_id and not self.variant_id:
            raise ValidationError(
                "A movement must target either "
                "a product or a variant."
            )

        if self.quantity <= 0:
            raise ValidationError(
                "Movement quantity must be greater than zero."
            )

    @property
    def item_name(self):

        if self.variant_id:
            return (
                f"{self.variant.product.name} "
                f"— {self.variant.name}"
            )

        return self.product.name

    @property
    def direction(self):

        if self.movement_type in {
            "restock",
            "adjustment_in",
            "return",
        }:
            return "in"

        return "out"

    def __str__(self):
        return (
            f"{self.get_movement_type_display()} "
            f"{self.item_name} "
            f"({self.quantity})"
        )
