from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0003_doctorprofile"),
    ]

    operations = [
        migrations.AddField(
            model_name="hospitalservice",
            name="location_hint",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="hospitalservice",
            name="opening_hours",
            field=models.CharField(blank=True, max_length=120),
        ),
    ]
