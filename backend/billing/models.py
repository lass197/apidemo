import uuid
from decimal import Decimal

from django.db import models
from django.utils import timezone

from clinical.models import Hospitalization, Patient
from core.models import TimestampedModel, User
from laboratory.models import LabOrder
from pharmacy.models import Medicine


class InsuranceProvider(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=30, unique=True)
    contact_email = models.EmailField(blank=True)
    coverage_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("80.00"))
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "assurance"
        ordering = ["name"]


class PatientInsurance(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="insurances")
    provider = models.ForeignKey(
        InsuranceProvider, on_delete=models.PROTECT, related_name="patient_insurances"
    )
    policy_number = models.CharField(max_length=50)
    valid_from = models.DateField()
    valid_until = models.DateField(null=True, blank=True)
    is_primary = models.BooleanField(default=True)

    class Meta:
        verbose_name = "couverture patient"


class ServicePrice(TimestampedModel):
    ACT = "ACT"
    NIGHT = "NIGHT"
    EXAM = "EXAM"
    MEDICINE = "MEDICINE"
    CONSUMABLE = "CONSUMABLE"

    TYPE_CHOICES = [
        (ACT, "Acte médical"),
        (NIGHT, "Nuitée"),
        (EXAM, "Examen"),
        (MEDICINE, "Médicament"),
        (CONSUMABLE, "Consommable"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=30, unique=True)
    label = models.CharField(max_length=200)
    service_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "tarif"
        ordering = ["code"]


class Invoice(TimestampedModel):
    DRAFT = "DRAFT"
    ISSUED = "ISSUED"
    PARTIAL = "PARTIAL"
    PAID = "PAID"
    CANCELLED = "CANCELLED"

    STATUS_CHOICES = [
        (DRAFT, "Brouillon"),
        (ISSUED, "Émise"),
        (PARTIAL, "Partiellement payée"),
        (PAID, "Payée"),
        (CANCELLED, "Annulée"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice_number = models.CharField(max_length=30, unique=True)
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="invoices")
    hospitalization = models.ForeignKey(
        Hospitalization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
    )
    insurance = models.ForeignKey(
        PatientInsurance,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=DRAFT)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    insurance_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    patient_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    issued_at = models.DateTimeField(null=True, blank=True)
    issued_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="invoices_issued")

    class Meta:
        verbose_name = "facture"
        ordering = ["-created_at"]

    @property
    def balance_due(self):
        due = self.patient_amount - self.paid_amount
        return due if due > 0 else Decimal("0")


class InvoiceLine(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")
    description = models.CharField(max_length=300)
    service_type = models.CharField(max_length=20)
    quantity = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("1"))
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    reference_id = models.CharField(max_length=64, blank=True)

    class Meta:
        verbose_name = "ligne facture"


class Payment(TimestampedModel):
    AIRTEL = "AIRTEL"
    MTN = "MTN"

    METHOD_CHOICES = [
        (AIRTEL, "Airtel Money"),
        (MTN, "MTN Mobile Money"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    paid_at = models.DateTimeField(default=timezone.now)
    received_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    reference = models.CharField(max_length=100, blank=True)
    is_installment = models.BooleanField(default=False)
    installment_number = models.PositiveSmallIntegerField(null=True, blank=True)
    declared_by_patient = models.BooleanField(default=False)

    class Meta:
        verbose_name = "paiement"
        ordering = ["-paid_at"]


class InvoicePatientDeclaration(TimestampedModel):
    """Déclaration de paiement mobile money par le patient (Airtel / MTN)."""

    PAID = "PAID"
    UNPAID = "UNPAID"

    STATUS_CHOICES = [
        (PAID, "Payée"),
        (UNPAID, "Impayée"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="patient_declarations")
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="invoice_declarations")
    phone_number = models.CharField(max_length=20)
    method = models.CharField(max_length=20, choices=Payment.METHOD_CHOICES)
    transaction_reference = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    amount_claimed = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    declared_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="invoice_declarations"
    )

    class Meta:
        verbose_name = "déclaration paiement patient"
        ordering = ["-created_at"]


class AccountingEntry(models.Model):
    """Journal comptable immuable — append-only."""

    DEBIT = "DEBIT"
    CREDIT = "CREDIT"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entry_date = models.DateTimeField(default=timezone.now, db_index=True)
    account_code = models.CharField(max_length=20)
    label = models.CharField(max_length=300)
    entry_type = models.CharField(max_length=10, choices=[(DEBIT, "Débit"), (CREDIT, "Crédit")])
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    invoice = models.ForeignKey(
        Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name="accounting_entries"
    )
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    is_adjustment = models.BooleanField(default=False)
    adjusts_entry = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="adjustments"
    )

    class Meta:
        verbose_name = "écriture comptable"
        ordering = ["-entry_date"]

    def save(self, *args, **kwargs):
        if self.pk and AccountingEntry.objects.filter(pk=self.pk).exists():
            raise ValueError("Les écritures comptables sont immuables.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Les écritures comptables ne peuvent pas être supprimées.")
