from datetime import date, timedelta
from uuid import UUID

from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from ninja import Router, Schema
from ninja.errors import HttpError

from core.auth import jwt_auth
from core.permissions import require_any_permission, require_permission
from core.services.audit import log_audit
from pharmacy.models import Medicine, StockLot, StockMovement

router = Router(tags=["Pharmacie"])

_PHARMACY_READ = require_any_permission("pharmacy.manage_stock", "pharmacy.dispense")


class MedicineOut(Schema):
    id: UUID
    code: str
    name: str
    form: str
    unit: str
    unit_price: str
    reorder_threshold: int
    stock_total: int = 0
    stock_status: str = "OK"


class PharmacyOverviewOut(Schema):
    medicine_count: int
    stock_units: int
    alert_count: int
    lot_count: int
    expiring_soon: int


class StockLotOut(Schema):
    id: UUID
    medicine_id: UUID
    medicine_name: str
    lot_number: str
    expiry_date: date
    quantity: int
    location: str
    days_to_expiry: int


class StockLotIn(Schema):
    medicine_id: UUID
    lot_number: str
    expiry_date: date
    quantity: int
    location: str = ""


class StockMovementOut(Schema):
    id: UUID
    movement_type: str
    quantity: int
    reason: str
    medicine_name: str
    lot_number: str
    created_at: str


def _stock_total(medicine: Medicine) -> int:
    return medicine.lots.filter(quantity__gt=0, expiry_date__gte=timezone.now().date()).aggregate(
        total=Sum("quantity")
    )["total"] or 0


def _stock_status(medicine: Medicine, total: int) -> str:
    if total <= 0:
        return "OUT"
    if total <= medicine.reorder_threshold:
        return "LOW"
    return "OK"


def _medicine_out(medicine: Medicine) -> dict:
    total = _stock_total(medicine)
    return {
        "id": medicine.id,
        "code": medicine.code,
        "name": medicine.name,
        "form": medicine.form,
        "unit": medicine.unit,
        "unit_price": str(medicine.unit_price),
        "reorder_threshold": medicine.reorder_threshold,
        "stock_total": total,
        "stock_status": _stock_status(medicine, total),
    }


@router.get("/overview/", response=PharmacyOverviewOut, auth=jwt_auth)
@_PHARMACY_READ
def pharmacy_overview(request):
    today = timezone.now().date()
    soon = today + timedelta(days=90)
    medicines = Medicine.objects.filter(is_active=True).prefetch_related("lots")
    stock_units = 0
    alert_count = 0
    for med in medicines:
        total = _stock_total(med)
        stock_units += total
        if total <= med.reorder_threshold:
            alert_count += 1
    lots = StockLot.objects.filter(quantity__gt=0, expiry_date__gte=today)
    return {
        "medicine_count": medicines.count(),
        "stock_units": stock_units,
        "alert_count": alert_count,
        "lot_count": lots.count(),
        "expiring_soon": lots.filter(expiry_date__lte=soon).count(),
    }


@router.get("/medicines/", response=list[MedicineOut], auth=jwt_auth)
@_PHARMACY_READ
def list_medicines(request, search: str = ""):
    qs = Medicine.objects.filter(is_active=True).prefetch_related("lots")
    term = (search or "").strip()
    if term:
        qs = qs.filter(Q(name__icontains=term) | Q(code__icontains=term) | Q(form__icontains=term))
    return [_medicine_out(m) for m in qs]


@router.get("/stock/", response=list[StockLotOut], auth=jwt_auth)
@_PHARMACY_READ
def list_stock(request, search: str = ""):
    today = timezone.now().date()
    lots = StockLot.objects.select_related("medicine").filter(quantity__gt=0).order_by("expiry_date")
    term = (search or "").strip().lower()
    results = []
    for lot in lots:
        if term and term not in lot.medicine.name.lower() and term not in lot.lot_number.lower():
            continue
        results.append(
            {
                "id": lot.id,
                "medicine_id": lot.medicine_id,
                "medicine_name": lot.medicine.name,
                "lot_number": lot.lot_number,
                "expiry_date": lot.expiry_date,
                "quantity": lot.quantity,
                "location": lot.location or "—",
                "days_to_expiry": (lot.expiry_date - today).days,
            }
        )
    return results


@router.get("/stock/alerts/", response=list[MedicineOut], auth=jwt_auth)
@_PHARMACY_READ
def stock_alerts(request):
    alerts = []
    for med in Medicine.objects.filter(is_active=True).prefetch_related("lots"):
        total = _stock_total(med)
        if total <= med.reorder_threshold:
            alerts.append(_medicine_out(med))
    return alerts


@router.post("/stock/lots/", response=StockLotOut, auth=jwt_auth)
@require_permission("pharmacy.manage_stock")
def add_stock_lot(request, payload: StockLotIn):
    try:
        medicine = Medicine.objects.get(pk=payload.medicine_id, is_active=True)
    except Medicine.DoesNotExist as exc:
        raise HttpError(404, "Médicament introuvable.") from exc

    lot, created = StockLot.objects.get_or_create(
        medicine=medicine,
        lot_number=payload.lot_number,
        defaults={
            "expiry_date": payload.expiry_date,
            "quantity": payload.quantity,
            "location": payload.location,
        },
    )
    if not created:
        lot.quantity += payload.quantity
        lot.save(update_fields=["quantity", "updated_at"])

    StockMovement.objects.create(
        lot=lot,
        movement_type=StockMovement.IN,
        quantity=payload.quantity,
        reason="Réception stock",
        performed_by=request.auth,
    )
    log_audit(
        user=request.auth,
        action_type="CREATE",
        resource_type="StockLot",
        resource_id=str(lot.id),
    )
    return {
        "id": lot.id,
        "medicine_id": medicine.id,
        "medicine_name": medicine.name,
        "lot_number": lot.lot_number,
        "expiry_date": lot.expiry_date,
        "quantity": lot.quantity,
        "location": lot.location or "—",
        "days_to_expiry": (lot.expiry_date - timezone.now().date()).days,
    }


@router.get("/stock/movements/", response=list[StockMovementOut], auth=jwt_auth)
@_PHARMACY_READ
def list_movements(request, limit: int = 50):
    moves = StockMovement.objects.select_related("lot__medicine").order_by("-created_at")[:limit]
    return [
        {
            "id": m.id,
            "movement_type": m.movement_type,
            "quantity": m.quantity,
            "reason": m.reason,
            "medicine_name": m.lot.medicine.name,
            "lot_number": m.lot.lot_number,
            "created_at": m.created_at.isoformat(),
        }
        for m in moves
    ]


@router.post("/dispense/{medicine_id}/", auth=jwt_auth)
@require_permission("pharmacy.dispense")
def dispense_medicine(request, medicine_id: UUID, quantity: int = 1):
    if not Medicine.objects.filter(pk=medicine_id, is_active=True).exists():
        raise HttpError(404, "Médicament introuvable.")

    with transaction.atomic():
        lot = (
            StockLot.objects.select_for_update()
            .filter(
                medicine_id=medicine_id,
                quantity__gte=quantity,
                expiry_date__gte=timezone.now().date(),
            )
            .order_by("expiry_date")
            .first()
        )
        if not lot:
            raise HttpError(409, "Stock insuffisant ou lot expiré.")

        lot.quantity -= quantity
        lot.save(update_fields=["quantity", "updated_at"])
        StockMovement.objects.create(
            lot=lot,
            movement_type=StockMovement.OUT,
            quantity=quantity,
            reason="Dispensation prescription",
            performed_by=request.auth,
        )

    log_audit(
        user=request.auth,
        action_type="UPDATE",
        resource_type="StockLot",
        resource_id=str(lot.id),
        new_value={"dispensed": quantity},
    )
    return {"detail": f"{quantity} unité(s) dispensée(s).", "remaining": lot.quantity}
