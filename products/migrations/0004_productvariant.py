import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("products", "0003_product_reserved_stock")]
    operations = [migrations.CreateModel(
        name="ProductVariant",
        fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(max_length=100)),
            ("sku", models.CharField(max_length=50, unique=True)),
            ("price", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
            ("stock", models.PositiveIntegerField(default=0)),
            ("is_active", models.BooleanField(default=True)),
            ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="variants", to="products.product")),
        ],
    )]