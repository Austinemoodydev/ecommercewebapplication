import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cart", "0002_cart_session_key_cartitem_created_at_alter_cart_user_and_more"),
        ("products", "0005_productvariant_reserved_stock"),
    ]

    operations = [
        migrations.AddField(
            model_name="cartitem",
            name="variant",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="cart_items",
                to="products.productvariant",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="cartitem",
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name="cartitem",
            constraint=models.UniqueConstraint(
                fields=("cart", "product", "variant"),
                name="cart_product_variant_unique",
            ),
        ),
    ]
