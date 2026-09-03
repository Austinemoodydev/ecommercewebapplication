from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_remove_customuser_created_at_and_more")]
    operations = [
        migrations.AddField(model_name="customuser", name="email_notifications", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="customuser", name="sms_notifications", field=models.BooleanField(default=True)),
    ]