from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        (
            "cart",
            "0003_cartitem_variant",
        ),
    ]


    operations = [

        migrations.AddField(
            model_name="cart",
            name="last_activity_at",
            field=models.DateTimeField(
                db_index=True,
                default=django.utils.timezone.now,
            ),
        ),

        migrations.AddField(
            model_name="cart",
            name="checkout_started_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
            ),
        ),

        migrations.AddField(
            model_name="cart",
            name="converted_at",
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                null=True,
            ),
        ),
    ]
