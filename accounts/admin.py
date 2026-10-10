from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, StaffSecurityEvent


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):

    fieldsets = UserAdmin.fieldsets + (
        ("Additional Information", {
            "fields": (
                "phone",
                "avatar",
                "role",
            )
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {
            "fields": (
                "phone",
                "avatar",
                "role",
            ),
        }),
    )


@admin.register(StaffSecurityEvent)
class StaffSecurityEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "target", "action", "ip_address")
    list_filter = ("action", "created_at")
    search_fields = ("actor__email", "target__email", "details")
    readonly_fields = ("actor", "target", "action", "details", "ip_address", "created_at")
