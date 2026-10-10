from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("core", "0003_alter_storesettings_credit_note_prefix_and_more"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="ErrorReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reference", models.CharField(db_index=True, max_length=12, unique=True)),
                ("path", models.CharField(max_length=500)),
                ("method", models.CharField(max_length=10)),
                ("status_code", models.PositiveSmallIntegerField(default=500)),
                ("exception_type", models.CharField(max_length=150)),
                ("message", models.TextField(blank=True)),
                ("traceback", models.TextField(blank=True)),
                ("resolved", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="error_reports", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-created_at",)},
        )
    ]
