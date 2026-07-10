from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="payment",
            name="method",
            field=models.CharField(
                choices=[
                    ("AIRTEL", "Airtel Money"),
                    ("MTN", "MTN Mobile Money"),
                ],
                max_length=20,
            ),
        ),
    ]
