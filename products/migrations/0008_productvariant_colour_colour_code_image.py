from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0007_product_cost_price_product_low_stock_threshold_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="productvariant",
            name="colour",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="productvariant",
            name="colour_code",
            field=models.CharField(blank=True, max_length=7),
        ),
        migrations.AddField(
            model_name="productvariant",
            name="image",
            field=models.ImageField(blank=True, null=True, upload_to="products/variants/"),
        ),
    ]
