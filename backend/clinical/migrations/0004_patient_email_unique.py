# Generated migration — email patient unique (nullable)

from django.db import migrations, models


def empty_email_to_null(apps, schema_editor):
    Patient = apps.get_model("clinical", "Patient")
    Patient.objects.filter(email="").update(email=None)


class Migration(migrations.Migration):

    dependencies = [
        ("clinical", "0003_icd10code_careplan_caretask_consultation_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="patient",
            name="email",
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
        migrations.RunPython(empty_email_to_null, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="patient",
            name="email",
            field=models.EmailField(blank=True, max_length=254, null=True, unique=True),
        ),
    ]
