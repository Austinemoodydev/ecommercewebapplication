from django.conf import settings
from django.db import models


class CustomerNote(models.Model):

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="crm_notes",
    )

    note = models.TextField()

    is_pinned = models.BooleanField(
        default=False,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_customer_notes",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:

        ordering = [
            "-is_pinned",
            "-created_at",
        ]

        indexes = [
            models.Index(
                fields=[
                    "customer",
                    "created_at",
                ]
            ),
        ]

    def __str__(self):

        return (
            f"Note for "
            f"{self.customer}"
        )
