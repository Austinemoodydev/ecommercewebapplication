from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("products", "0004_productvariant")]
    operations = [
        migrations.AddField(
            model_name="productvariant",
            name="reserved_stock",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
