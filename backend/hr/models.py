import uuid

from django.db import models
from django.utils import timezone

from clinical.models import Patient
from core.models import TimestampedModel, User


class Shift(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    staff = models.ForeignKey(User, on_delete=models.CASCADE, related_name="shifts")
    department_code = models.CharField(max_length=20)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "garde"
        ordering = ["start_at"]


class HospitalService(TimestampedModel):
    """Prestation hospitalière présentée aux patients et réservable en ligne."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    department_code = models.CharField(max_length=20, blank=True)
    icon = models.CharField(max_length=8, blank=True, default="🏥")
    duration_minutes = models.PositiveSmallIntegerField(default=30)
    price_hint = models.CharField(max_length=50, blank=True)
    opening_hours = models.CharField(max_length=120, blank=True)
    location_hint = models.CharField(max_length=200, blank=True)
    is_bookable_online = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "prestation hospitalière"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class DoctorAvailability(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="availabilities")
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    slot_duration_minutes = models.PositiveSmallIntegerField(default=30)
    is_bookable = models.BooleanField(default=True)

    class Meta:
        verbose_name = "disponibilité médecin"
        ordering = ["start_at"]


class DoctorProfile(TimestampedModel):
    """Fiche médecin : spécialité et service hospitalier."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="doctor_profile")
    specialty = models.CharField(max_length=120, default="Médecine générale")
    department_code = models.CharField(max_length=20, blank=True)
    department_name = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    is_accepting_appointments = models.BooleanField(default=True)

    class Meta:
        verbose_name = "profil médecin"

    def __str__(self):
        return f"{self.user} — {self.specialty}"


class Appointment(TimestampedModel):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"

    STATUS_CHOICES = [
        (PENDING, "En attente"),
        (CONFIRMED, "Confirmé"),
        (CANCELLED, "Annulé"),
        (COMPLETED, "Terminé"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="appointments")
    doctor = models.ForeignKey(User, on_delete=models.PROTECT, related_name="appointments")
    service = models.ForeignKey(
        HospitalService,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointments",
    )
    scheduled_at = models.DateTimeField()
    duration_minutes = models.PositiveSmallIntegerField(default=30)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    reason = models.TextField(blank=True)
    staff_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    confirmation_sent = models.BooleanField(default=False)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_appointments",
    )

    class Meta:
        verbose_name = "rendez-vous"
        ordering = ["scheduled_at"]


class ChatMessage(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="chat_messages")
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    content = models.TextField()
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "message chat"
        ordering = ["created_at"]


class MedicationReminder(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="medication_reminders")
    medicine_name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100)
    schedule_time = models.TimeField()
    is_active = models.BooleanField(default=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "rappel médicament"
        ordering = ["schedule_time"]
