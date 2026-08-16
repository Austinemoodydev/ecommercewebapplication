from django.db import migrations


AREAS = [
    ("Westlands", 250),
    ("Kilimani", 200),
    ("Kileleshwa", 200),
    ("Karen", 400),
    ("Lang'ata", 300),
    ("South B", 150),
    ("South C", 150),
    ("Embakasi", 300),
    ("Kasarani", 350),
    ("Roysambu", 300),
]


def seed_areas(apps, schema_editor):

    DeliveryArea = apps.get_model("orders", "DeliveryArea")

    for name, fee in AREAS:
        DeliveryArea.objects.get_or_create(
            county="Nairobi",
            name=name,
            defaults={"fee": fee},
        )


def remove_areas(apps, schema_editor):

    DeliveryArea = apps.get_model("orders", "DeliveryArea")

    DeliveryArea.objects.filter(
        county="Nairobi",
        name__in=[name for name, _ in AREAS],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0002_deliveryarea"),
    ]

    operations = [
        migrations.RunPython(seed_areas, remove_areas),
    ]
