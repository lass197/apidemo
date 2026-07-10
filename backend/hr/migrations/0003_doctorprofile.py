# Generated manually for DoctorProfile

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0002_hospitalservice_appointment_rejection_reason_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DoctorProfile",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("specialty", models.CharField(default="Médecine générale", max_length=120)),
                ("department_code", models.CharField(blank=True, max_length=20)),
                ("department_name", models.CharField(blank=True, max_length=100)),
                ("bio", models.TextField(blank=True)),
                ("is_accepting_appointments", models.BooleanField(default=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="doctor_profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "profil médecin",
            },
        ),
    ]
