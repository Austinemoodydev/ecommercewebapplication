import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("payments", "0002_refundrequest")]
    operations = [migrations.CreateModel(
        name="ReturnRequest",
        fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("request_type", models.CharField(choices=[("return", "Return"), ("replacement", "Replacement")], max_length=20)),
            ("reason", models.TextField()),
            ("status", models.CharField(choices=[("requested", "Requested"), ("approved", "Approved"), ("completed", "Completed"), ("rejected", "Rejected")], default="requested", max_length=20)),
            ("staff_note", models.TextField(blank=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("updated_at", models.DateTimeField(auto_now=True)),
            ("order", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="return_requests", to="orders.order")),
        ],
    )]