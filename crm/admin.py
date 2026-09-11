from django.contrib import admin

from .models import CustomerNote


@admin.register(CustomerNote)
class CustomerNoteAdmin(
    admin.ModelAdmin
):

    list_display = [
        "customer",
        "created_by",
        "is_pinned",
        "created_at",
    ]

    list_filter = [
        "is_pinned",
        "created_at",
    ]

    search_fields = [
        "customer__username",
        "customer__email",
        "customer__phone",
        "note",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
    ]
