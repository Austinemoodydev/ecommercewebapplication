from django.contrib import admin
from .models import Notification
from .tasks import retry_notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
	list_display = ("subject", "user", "channel", "status", "attempts", "created_at", "sent_at")
	list_filter = ("status", "channel", "created_at")
	search_fields = ("subject", "user__username", "last_error")
	readonly_fields = ("user", "order_id", "channel", "subject", "message", "attempts", "last_error", "created_at", "sent_at", "updated_at")
	actions = ("retry_failed",)

	@admin.action(description="Retry failed notifications")
	def retry_failed(self, request, queryset):
		count = 0
		for notification in queryset.filter(status="failed"):
			notification.status = "pending"
			notification.save(update_fields=["status", "updated_at"])
			retry_notification.delay(notification.id)
			count += 1
		self.message_user(request, f"{count} notification(s) queued for retry.")
