from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("orders", "0007_order_courier_order_tracking_number")]
    operations = [migrations.AddField(
        model_name="order", name="tracking_url", field=models.URLField(blank=True),
    )]