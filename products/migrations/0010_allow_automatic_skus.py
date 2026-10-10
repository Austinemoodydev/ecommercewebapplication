from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("products", "0009_productoption_productoptionvalue_and_variant_options")]
    operations = [
        migrations.AlterField(
            model_name="product",
            name="sku",
            field=models.CharField(blank=True, max_length=50, unique=True),
        ),
        migrations.AlterField(
            model_name="productvariant",
            name="sku",
            field=models.CharField(blank=True, max_length=50, unique=True),
        ),
    ]
