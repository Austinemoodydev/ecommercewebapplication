from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("socialaccount", "0006_alter_socialaccount_extra_data")]
    operations = [migrations.SeparateDatabaseAndState(
        database_operations=[migrations.AlterField(
            model_name="socialaccount",
            name="uid",
            field=models.CharField(max_length=40, verbose_name="uid"),
        )],
        state_operations=[migrations.AlterField(
            model_name="socialaccount",
            name="uid",
            field=models.CharField(max_length=191, verbose_name="uid"),
        )],
    )]
