import hashlib
import uuid

from django.db import models

from clinical.models import Hospitalization, Patient
from core.models import TimestampedModel, User
from laboratory.models import LabOrder


class Document(TimestampedModel):
    CONSULTATION = "CONSULTATION"
    PRESCRIPTION = "PRESCRIPTION"
    LAB_REPORT = "LAB_REPORT"
    INVOICE = "INVOICE"
    IMAGING = "IMAGING"
    ADMISSION = "ADMISSION"
    DISCHARGE = "DISCHARGE"
    TRANSFER = "TRANSFER"
    OTHER = "OTHER"

    TYPE_CHOICES = [
        (CONSULTATION, "Consultation"),
        (PRESCRIPTION, "Ordonnance"),
        (LAB_REPORT, "Compte-rendu labo"),
        (INVOICE, "Facture"),
        (IMAGING, "Imagerie"),
        (ADMISSION, "Attestation d'admission"),
        (DISCHARGE, "Attestation de sortie"),
        (TRANSFER, "Attestation de transfert"),
        (OTHER, "Autre"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="documents")
    hospitalization = models.ForeignKey(
        Hospitalization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )
    lab_order = models.ForeignKey(
        LabOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )
    document_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    file_path = models.CharField(max_length=500)
    mime_type = models.CharField(max_length=100)
    file_size = models.PositiveIntegerField()
    file_hash = models.CharField(max_length=64)
    is_encrypted = models.BooleanField(default=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    signed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="signed_documents",
    )
    signature_hash = models.CharField(max_length=64, blank=True)

    class Meta:
        verbose_name = "document"
        ordering = ["-created_at"]

    @staticmethod
    def compute_hash(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()


class DocumentAccessLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="access_logs")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    accessed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    action = models.CharField(max_length=20, default="VIEW")

    class Meta:
        verbose_name = "accès document"
        ordering = ["-accessed_at"]
