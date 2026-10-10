from django.contrib import admin
from .models import CampaignAuditEvent, CampaignDelivery, ErrorReport, HomepageSlide, MarketingCampaign


@admin.register(ErrorReport)
class ErrorReportAdmin(admin.ModelAdmin):
    list_display = ("reference", "exception_type", "path", "status_code", "created_at", "resolved")
    list_filter = ("resolved", "status_code", "exception_type")
    search_fields = ("reference", "path", "message")
    readonly_fields = ("reference", "path", "method", "status_code", "exception_type", "message", "traceback", "user", "created_at")


@admin.register(MarketingCampaign)
class MarketingCampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "holiday_type", "starts_at", "ends_at", "is_enabled", "approved_at")
    list_filter = ("holiday_type", "is_enabled", "is_verified_holiday")
    search_fields = ("name", "headline", "message")
    filter_horizontal = ("products", "categories")


@admin.register(CampaignDelivery)
class CampaignDeliveryAdmin(admin.ModelAdmin):
    list_display = ("campaign", "user", "channel", "status", "sent_at")
    list_filter = ("channel", "status")
    readonly_fields = ("campaign", "user", "channel", "status", "error", "sent_at", "created_at")


@admin.register(CampaignAuditEvent)
class CampaignAuditEventAdmin(admin.ModelAdmin):
    list_display = ("campaign", "action", "actor", "created_at")
    readonly_fields = ("campaign", "action", "actor", "details", "created_at")


@admin.register(HomepageSlide)
class HomepageSlideAdmin(admin.ModelAdmin):
    list_display = ("internal_name", "heading", "display_order", "is_enabled", "starts_at", "ends_at")
    list_editable = ("display_order", "is_enabled")
    search_fields = ("internal_name", "heading", "description")
