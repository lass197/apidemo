import uuid

from django.db import models
from django.utils import timezone

from clinical.models import Hospitalization, Patient
from core.models import TimestampedModel, User


class LabTestType(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    sample_type = models.CharField(max_length=50, default="blood")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    turnaround_hours = models.PositiveSmallIntegerField(default=24)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "type d'examen"
        ordering = ["code"]

    def __str__(self):
        return self.name


class LabOrder(TimestampedModel):
    ORDERED = "ORDERED"
    COLLECTED = "COLLECTED"
    ASSIGNED = "ASSIGNED"
    RESULTS_ENTERED = "RESULTS_ENTERED"
    VALIDATED = "VALIDATED"
    PUBLISHED = "PUBLISHED"

    STATUS_CHOICES = [
        (ORDERED, "Commandé"),
        (COLLECTED, "Prélevé"),
        (ASSIGNED, "Affecté"),
        (RESULTS_ENTERED, "Résultats saisis"),
        (VALIDATED, "Validé"),
        (PUBLISHED, "Publié"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="lab_orders")
    hospitalization = models.ForeignKey(
        Hospitalization,
        on_delete=models.PROTECT,
        related_name="lab_orders",
        null=True,
        blank=True,
    )
    test_type = models.ForeignKey(LabTestType, on_delete=models.PROTECT, related_name="orders")
    ordered_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="lab_orders_ordered")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=ORDERED)
    priority = models.CharField(
        max_length=10,
        choices=[("NORMAL", "Normal"), ("URGENT", "Urgent")],
        default="NORMAL",
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lab_orders_assigned",
    )
    validated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lab_orders_validated",
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    clinical_notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "commande labo"
        ordering = ["-created_at"]


class LabSample(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lab_order = models.OneToOneField(LabOrder, on_delete=models.CASCADE, related_name="sample")
    barcode = models.CharField(max_length=50, unique=True)
    collected_at = models.DateTimeField(default=timezone.now)
    collected_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="samples_collected"
    )
    notes = models.TextField(blank=True)


class LabResult(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lab_order = models.OneToOneField(LabOrder, on_delete=models.CASCADE, related_name="result")
    entered_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="lab_results_entered"
    )
    result_data = models.JSONField(default=dict)
    interpretation = models.TextField(blank=True)
    is_abnormal = models.BooleanField(default=False)
    entered_at = models.DateTimeField(default=timezone.now)
    # Immuable après validation de la commande
    locked = models.BooleanField(default=False)

    class Meta:
        verbose_name = "résultat labo"

