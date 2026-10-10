from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0008_productvariant_colour_colour_code_image"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductOption",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=50)),
                ("position", models.PositiveSmallIntegerField(default=0)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="options", to="products.product")),
            ],
            options={"ordering": ("position", "id")},
        ),
        migrations.CreateModel(
            name="ProductOptionValue",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("value", models.CharField(max_length=80)),
                ("colour_code", models.CharField(blank=True, max_length=7)),
                ("position", models.PositiveSmallIntegerField(default=0)),
                ("option", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="values", to="products.productoption")),
            ],
            options={"ordering": ("position", "id")},
        ),
        migrations.AddField(
            model_name="productvariant",
            name="option_values",
            field=models.ManyToManyField(blank=True, related_name="variants", to="products.productoptionvalue"),
        ),
        migrations.AddConstraint(
            model_name="productoption",
            constraint=models.UniqueConstraint(fields=("product", "name"), name="unique_product_option_name"),
        ),
        migrations.AddConstraint(
            model_name="productoptionvalue",
            constraint=models.UniqueConstraint(fields=("option", "value"), name="unique_product_option_value"),
        ),
    ]
