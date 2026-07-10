import uuid
from decimal import Decimal

from django.db import models
from django.utils import timezone

from core.models import TimestampedModel, User


class Medicine(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=200)
    form = models.CharField(max_length=50, default="comprimé")
    unit = models.CharField(max_length=20, default="unité")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    reorder_threshold = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "médicament"
        ordering = ["name"]

    def __str__(self):
        return self.name


class StockLot(TimestampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name="lots")
    lot_number = models.CharField(max_length=50)
    expiry_date = models.DateField()
    quantity = models.PositiveIntegerField(default=0)
    location = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "lot stock"
        unique_together = [("medicine", "lot_number")]
        ordering = ["expiry_date"]

    @property
    def is_expired(self):
        return self.expiry_date < timezone.now().date()


class StockMovement(TimestampedModel):
    IN = "IN"
    OUT = "OUT"
    ADJUSTMENT = "ADJUSTMENT"

    TYPE_CHOICES = [(IN, "Entrée"), (OUT, "Sortie"), (ADJUSTMENT, "Ajustement")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lot = models.ForeignKey(StockLot, on_delete=models.PROTECT, related_name="movements")
    movement_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    quantity = models.PositiveIntegerField()
    reason = models.CharField(max_length=200, blank=True)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    reference = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "mouvement stock"
        ordering = ["-created_at"]
