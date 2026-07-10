from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_user_email_verified_emailotp"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="last_seen_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
