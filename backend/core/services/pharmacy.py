from django.db import transaction
from django.utils import timezone

from pharmacy.models import Medicine, StockLot, StockMovement


def deduct_for_prescription(prescription, performed_by) -> list[str]:
    """Décrémente le stock à la validation d'une ordonnance. Retourne les alertes."""
    alerts = []
    for item in prescription.items.all():
        medicine = (
            Medicine.objects.filter(is_active=True, name__icontains=item.medicine_name.split()[0])
            .first()
        )
        if not medicine:
            medicine = Medicine.objects.filter(name__icontains=item.medicine_name[:10]).first()
        if not medicine:
            alerts.append(f"Stock non déduit — médicament inconnu : {item.medicine_name}")
            continue

        qty = max(1, item.duration_days // 7 or 1)
        with transaction.atomic():
            lot = (
                StockLot.objects.select_for_update()
                .filter(
                    medicine=medicine,
                    quantity__gte=qty,
                    expiry_date__gte=timezone.now().date(),
                )
                .order_by("expiry_date")
                .first()
            )
            if not lot:
                alerts.append(f"Stock insuffisant pour {medicine.name}")
                continue
            lot.quantity -= qty
            lot.save(update_fields=["quantity", "updated_at"])
            StockMovement.objects.create(
                lot=lot,
                movement_type=StockMovement.OUT,
                quantity=qty,
                reason=f"Ordonnance validée #{prescription.id}",
                performed_by=performed_by,
            )
    return alerts
