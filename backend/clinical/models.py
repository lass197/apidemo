import uuid

from django.db import models
from django.utils import timezone

from core.models import OptimisticLockMixin, TimestampedModel, User


class Patient(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patient_profile",
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(
        max_length=1,
        choices=[("M", "Masculin"), ("F", "Féminin"), ("O", "Autre")],
    )
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True, null=True, unique=True)
    address = models.TextField(blank=True)
    social_security_number = models.CharField(max_length=50, blank=True)
    emergency_contact = models.CharField(max_length=150, blank=True)
    emergency_phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "patient"
        verbose_name_plural = "patients"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.last_name} {self.first_name}"


class Building(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "bâtiment"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Department(TimestampedModel):
    """Service hospitalier (ex: Cardiologie, Urgences)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name="departments")
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "service"
        unique_together = [("building", "code")]
        ordering = ["building", "name"]

    def __str__(self):
        return f"{self.building.code} — {self.name}"


class Room(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="rooms")
    number = models.CharField(max_length=20)
    floor = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "chambre"
        unique_together = [("department", "number")]

    def __str__(self):
        return f"Ch. {self.number} ({self.department.name})"


class Bed(TimestampedModel):
    AVAILABLE = "AVAILABLE"
    OCCUPIED = "OCCUPIED"
    MAINTENANCE = "MAINTENANCE"

    STATUS_CHOICES = [
        (AVAILABLE, "Disponible"),
        (OCCUPIED, "Occupé"),
        (MAINTENANCE, "Maintenance"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="beds")
    label = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=AVAILABLE)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "lit"
        unique_together = [("room", "label")]

    def __str__(self):
        return f"Lit {self.label} — {self.room}"


class Hospitalization(OptimisticLockMixin, TimestampedModel):
    ACTIVE = "ACTIVE"
    DISCHARGED = "DISCHARGED"
    TRANSFERRED = "TRANSFERRED"
    CANCELLED = "CANCELLED"

    STATUS_CHOICES = [
        (ACTIVE, "En cours"),
        (DISCHARGED, "Sortie"),
        (TRANSFERRED, "Transféré"),
        (CANCELLED, "Annulée"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="hospitalizations")
    bed = models.ForeignKey(Bed, on_delete=models.PROTECT, related_name="hospitalizations")
    referring_doctor = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="referring_hospitalizations",
    )
    admission_date = models.DateTimeField()
    expected_discharge_date = models.DateField()
    actual_discharge_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=ACTIVE)
    admission_reason = models.TextField()
    notes = models.TextField(blank=True)
    admitted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="admissions_created",
    )

    class Meta:
        verbose_name = "hospitalisation"
        ordering = ["-admission_date"]

    def __str__(self):
        return f"{self.patient} — {self.admission_date:%d/%m/%Y}"


class ICD10Code(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=10, unique=True)
    description = models.CharField(max_length=500)
    category = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "code CIM-10"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.description}"


class Consultation(OptimisticLockMixin, TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospitalization = models.ForeignKey(
        Hospitalization, on_delete=models.PROTECT, related_name="consultations"
    )
    doctor = models.ForeignKey(User, on_delete=models.PROTECT, related_name="consultations")
    consultation_date = models.DateTimeField(default=timezone.now)
    symptoms = models.TextField()
    clinical_notes = models.TextField(blank=True)
    icd10_codes = models.ManyToManyField(ICD10Code, blank=True, related_name="consultations")

    class Meta:
        verbose_name = "consultation"
        ordering = ["-consultation_date"]


class Prescription(OptimisticLockMixin, TimestampedModel):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"

    STATUS_CHOICES = [(DRAFT, "Brouillon"), (VALIDATED, "Validée")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    consultation = models.ForeignKey(
        Consultation, on_delete=models.PROTECT, related_name="prescriptions"
    )
    doctor = models.ForeignKey(User, on_delete=models.PROTECT, related_name="prescriptions")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=DRAFT)
    validated_at = models.DateTimeField(null=True, blank=True)
    instructions = models.TextField(blank=True)

    class Meta:
        verbose_name = "prescription"
        ordering = ["-created_at"]


class PrescriptionItem(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prescription = models.ForeignKey(
        Prescription, on_delete=models.CASCADE, related_name="items"
    )
    medicine_name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration_days = models.PositiveSmallIntegerField(default=7)
    route = models.CharField(max_length=50, default="oral")

    class Meta:
        verbose_name = "ligne prescription"


class CarePlan(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospitalization = models.ForeignKey(
        Hospitalization, on_delete=models.CASCADE, related_name="care_plans"
    )
    prescription = models.ForeignKey(
        Prescription, on_delete=models.SET_NULL, null=True, blank=True, related_name="care_plans"
    )
    title = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "plan de soins"


class CareTask(TimestampedModel):
    PENDING = "PENDING"
    DONE = "DONE"
    MISSED = "MISSED"

    STATUS_CHOICES = [
        (PENDING, "En attente"),
        (DONE, "Effectué"),
        (MISSED, "Omis"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    care_plan = models.ForeignKey(CarePlan, on_delete=models.CASCADE, related_name="tasks")
    description = models.CharField(max_length=300)
    scheduled_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    administered_at = models.DateTimeField(null=True, blank=True)
    nurse = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="care_tasks"
    )

    class Meta:
        verbose_name = "tâche de soin"
        ordering = ["scheduled_at"]


class VitalSign(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospitalization = models.ForeignKey(
        Hospitalization, on_delete=models.CASCADE, related_name="vital_signs"
    )
    nurse = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="vital_signs")
    recorded_at = models.DateTimeField(default=timezone.now)
    temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    blood_pressure_systolic = models.PositiveSmallIntegerField(null=True, blank=True)
    blood_pressure_diastolic = models.PositiveSmallIntegerField(null=True, blank=True)
    heart_rate = models.PositiveSmallIntegerField(null=True, blank=True)
    respiratory_rate = models.PositiveSmallIntegerField(null=True, blank=True)
    oxygen_saturation = models.PositiveSmallIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "constante vitale"
        ordering = ["-recorded_at"]


class TransferLog(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospitalization = models.ForeignKey(
        Hospitalization, on_delete=models.CASCADE, related_name="transfers"
    )
    from_bed = models.ForeignKey(
        Bed, on_delete=models.PROTECT, related_name="transfers_from"
    )
    to_bed = models.ForeignKey(Bed, on_delete=models.PROTECT, related_name="transfers_to")
    transferred_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    reason = models.TextField(blank=True)

    class Meta:
        verbose_name = "transfert"
        ordering = ["-created_at"]


class PartnerHospital(TimestampedModel):
    """Établissement partenaire pouvant recevoir des patients transférés."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    specialties = models.CharField(
        max_length=500,
        blank=True,
        help_text="Spécialités disponibles, séparées par des virgules",
    )
    available_beds = models.PositiveSmallIntegerField(default=0)
    total_beds = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    accepts_transfers = models.BooleanField(default=True)

    class Meta:
        verbose_name = "hôpital partenaire"
        verbose_name_plural = "hôpitaux partenaires"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.city})"

    @property
    def can_receive(self) -> bool:
        return self.is_active and self.accepts_transfers and self.available_beds > 0


class InterHospitalTransfer(TimestampedModel):
    """Demande de transfert vers un établissement partenaire."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

    STATUS_CHOICES = [
        (PENDING, "En attente"),
        (APPROVED, "Validé"),
        (REJECTED, "Refusé"),
        (CANCELLED, "Annulé"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospitalization = models.ForeignKey(
        Hospitalization, on_delete=models.PROTECT, related_name="inter_hospital_transfers"
    )
    partner_hospital = models.ForeignKey(
        PartnerHospital, on_delete=models.PROTECT, related_name="incoming_transfers"
    )
    reason = models.TextField()
    clinical_summary = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    requested_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="inter_transfers_requested"
    )
    validated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inter_transfers_validated",
    )
    validated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "transfert inter-établissement"
        ordering = ["-created_at"]


class PatientMovementHistory(TimestampedModel):
    """Historique immuable des admissions, sorties et transferts."""

    ADMISSION = "ADMISSION"
    ADMISSION_CORRECTION = "ADMISSION_CORRECTION"
    ADMISSION_CANCEL = "ADMISSION_CANCEL"
    DISCHARGE = "DISCHARGE"
    INTERNAL_TRANSFER = "INTERNAL_TRANSFER"
    INTER_TRANSFER = "INTER_TRANSFER"

    EVENT_TYPES = [
        (ADMISSION, "Admission"),
        (ADMISSION_CORRECTION, "Correction date d'admission"),
        (ADMISSION_CANCEL, "Annulation d'admission"),
        (DISCHARGE, "Sortie"),
        (INTERNAL_TRANSFER, "Transfert interne"),
        (INTER_TRANSFER, "Transfert inter-établissement"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="movement_history")
    hospitalization = models.ForeignKey(
        Hospitalization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movement_history",
    )
    event_at = models.DateTimeField()
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="patient_movements",
    )
    details = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movement_events",
    )

    class Meta:
        verbose_name = "historique mouvement patient"
        verbose_name_plural = "historiques mouvements patients"
        ordering = ["-event_at", "-created_at"]

    def __str__(self):
        return f"{self.get_event_type_display()} — {self.patient} ({self.event_at:%d/%m/%Y %H:%M})"

