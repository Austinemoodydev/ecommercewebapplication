from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.CreateModel(
        name="Notification",
        fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("order_id", models.PositiveBigIntegerField(blank=True, null=True)),
            ("channel", models.CharField(default="email", max_length=20)),
            ("subject", models.CharField(max_length=200)),
            ("message", models.TextField()),
            ("status", models.CharField(choices=[("pending", "Pending"), ("sent", "Sent"), ("failed", "Failed")], default="pending", max_length=20)),
            ("attempts", models.PositiveIntegerField(default=0)),
            ("last_error", models.TextField(blank=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("sent_at", models.DateTimeField(blank=True, null=True)),
            ("updated_at", models.DateTimeField(auto_now=True)),
            ("user", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="notifications", to=settings.AUTH_USER_MODEL)),
        ],
        options={"ordering": ["-created_at"]},
    )]