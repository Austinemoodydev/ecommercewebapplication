from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("payments", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="RefundRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("reason", models.TextField()),
                ("status", models.CharField(choices=[("requested", "Requested"), ("approved", "Approved"), ("processed", "Processed"), ("rejected", "Rejected")], default="requested", max_length=20)),
                ("external_reference", models.CharField(blank=True, max_length=100)),
                ("staff_note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="refund_requests", to="orders.order")),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]