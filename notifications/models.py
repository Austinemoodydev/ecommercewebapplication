from django.conf import settings
from django.db import models


class Notification(models.Model):
	STATUS_CHOICES = [("pending", "Pending"), ("sent", "Sent"), ("failed", "Failed")]

	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
	order_id = models.PositiveBigIntegerField(null=True, blank=True)
	channel = models.CharField(max_length=20, default="email")
	subject = models.CharField(max_length=200)
	message = models.TextField()
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
	attempts = models.PositiveIntegerField(default=0)
	last_error = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	sent_at = models.DateTimeField(null=True, blank=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return f"{self.subject} - {self.status}"
