from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0002_alter_product_options_productimage_alt_text_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="reserved_stock",
            field=models.PositiveIntegerField(default=0),
        ),
    ]