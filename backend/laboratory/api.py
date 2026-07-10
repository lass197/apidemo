from datetime import datetime
from uuid import UUID

from django.utils import timezone
from ninja import Router, Schema
from ninja.errors import HttpError

from clinical.models import Hospitalization, Patient
from core.auth import jwt_auth
from core.permissions import require_any_permission, require_permission
from core.services.audit import log_audit
from core.services.dashboard import invalidate_dashboard_cache
from core.services.pdf import generate_lab_report_pdf
from core.services.storage import store_encrypted_file
from documents.models import Document
from laboratory.models import LabOrder, LabResult, LabSample, LabTestType

router = Router(tags=["Laboratoire"])


class LabTestOut(Schema):
    id: UUID
    code: str
    name: str
    price: str
    sample_type: str


class LabOrderIn(Schema):
    patient_id: UUID
    test_type_id: UUID
    hospitalization_id: UUID | None = None
    priority: str = "NORMAL"
    clinical_notes: str = ""


class LabOrderOut(Schema):
    id: UUID
    patient_id: UUID
    patient_name: str = ""
    test_name: str
    test_code: str = ""
    status: str
    priority: str
    clinical_notes: str = ""
    created_at: datetime


class LabOverviewOut(Schema):
    test_count: int
    orders_pending: int
    orders_urgent: int
    orders_validated_today: int
    orders_published: int


_LAB_READ = require_any_permission(
    "lab.order", "lab.enter_results", "lab.validate_results", "lab.publish_results"
)


class LabResultIn(Schema):
    result_data: dict
    interpretation: str = ""
    is_abnormal: bool = False


class LabResultOut(Schema):
    id: UUID
    lab_order_id: UUID
    result_data: dict
    interpretation: str
    locked: bool


VALID_TRANSITIONS = {
    LabOrder.ORDERED: [LabOrder.COLLECTED],
    LabOrder.COLLECTED: [LabOrder.ASSIGNED],
    LabOrder.ASSIGNED: [LabOrder.RESULTS_ENTERED],
    LabOrder.RESULTS_ENTERED: [LabOrder.VALIDATED],
    LabOrder.VALIDATED: [LabOrder.PUBLISHED],
}


def _order_out(order: LabOrder) -> dict:
    return {
        "id": order.id,
        "patient_id": order.patient_id,
        "patient_name": str(order.patient) if getattr(order, "patient", None) else "",
        "test_name": order.test_type.name,
        "test_code": order.test_type.code,
        "status": order.status,
        "priority": order.priority,
        "clinical_notes": order.clinical_notes or "",
        "created_at": order.created_at,
    }


def _transition(order: LabOrder, new_status: str, user, **extra):
    allowed = VALID_TRANSITIONS.get(order.status, [])
    if new_status not in allowed:
        raise HttpError(409, f"Transition {order.status} → {new_status} non autorisée.")
    order.status = new_status
    for k, v in extra.items():
        setattr(order, k, v)
    order.save()
    log_audit(
        user=user,
        action_type="UPDATE" if new_status != LabOrder.VALIDATED else "VALIDATE",
        resource_type="LabOrder",
        resource_id=str(order.id),
        new_value={"status": new_status},
    )


@router.get("/overview/", response=LabOverviewOut, auth=jwt_auth)
@_LAB_READ
def lab_overview(request):
    today = timezone.now().date()
    qs = LabOrder.objects.all()
    return {
        "test_count": LabTestType.objects.filter(is_active=True).count(),
        "orders_pending": qs.exclude(status__in=[LabOrder.VALIDATED, LabOrder.PUBLISHED]).count(),
        "orders_urgent": qs.filter(priority="URGENT").exclude(status=LabOrder.PUBLISHED).count(),
        "orders_validated_today": qs.filter(validated_at__date=today).count(),
        "orders_published": qs.filter(status=LabOrder.PUBLISHED).count(),
    }


@router.get("/tests/", response=list[LabTestOut], auth=jwt_auth)
@_LAB_READ
def list_tests(request, search: str = ""):
    from django.db.models import Q

    qs = LabTestType.objects.filter(is_active=True)
    term = (search or "").strip()
    if term:
        qs = qs.filter(Q(name__icontains=term) | Q(code__icontains=term) | Q(sample_type__icontains=term))
    return [
        {
            "id": t.id,
            "code": t.code,
            "name": t.name,
            "price": str(t.price),
            "sample_type": t.sample_type,
        }
        for t in qs
    ]


@router.post("/orders/", response=LabOrderOut, auth=jwt_auth)
@require_permission("lab.order")
def create_order(request, payload: LabOrderIn):
    try:
        patient = Patient.objects.get(pk=payload.patient_id, is_active=True)
        test = LabTestType.objects.get(pk=payload.test_type_id, is_active=True)
    except (Patient.DoesNotExist, LabTestType.DoesNotExist) as exc:
        raise HttpError(404, "Patient ou examen introuvable.") from exc

    hosp = None
    if payload.hospitalization_id:
        try:
            hosp = Hospitalization.objects.get(
                pk=payload.hospitalization_id, status=Hospitalization.ACTIVE
            )
        except Hospitalization.DoesNotExist as exc:
            raise HttpError(404, "Hospitalisation active requise.") from exc

    order = LabOrder.objects.create(
        patient=patient,
        hospitalization=hosp,
        test_type=test,
        ordered_by=request.auth,
        priority=payload.priority,
        clinical_notes=payload.clinical_notes,
    )
    invalidate_dashboard_cache()
    log_audit(
        user=request.auth,
        action_type="CREATE",
        resource_type="LabOrder",
        resource_id=str(order.id),
    )
    return _order_out(order)


@router.get("/orders/", response=list[LabOrderOut], auth=jwt_auth)
@_LAB_READ
def list_orders(request, status: str | None = None, search: str = "", page: int = 1, page_size: int = 50):
    qs = LabOrder.objects.select_related("test_type", "patient").order_by("-created_at")
    if status:
        qs = qs.filter(status=status)
    term = (search or "").strip()
    if term:
        from django.db.models import Q

        qs = qs.filter(
            Q(patient__first_name__icontains=term)
            | Q(patient__last_name__icontains=term)
            | Q(test_type__name__icontains=term)
            | Q(test_type__code__icontains=term)
        )
    offset = (page - 1) * page_size
    return [_order_out(o) for o in qs[offset : offset + page_size]]


@router.post("/orders/{order_id}/collect/", response=LabOrderOut, auth=jwt_auth)
@require_permission("lab.enter_results")
def collect_sample(request, order_id: UUID):
    import uuid as uuid_mod

    try:
        order = LabOrder.objects.select_related("test_type", "patient").get(pk=order_id)
    except LabOrder.DoesNotExist as exc:
        raise HttpError(404, "Commande introuvable.") from exc

    _transition(order, LabOrder.COLLECTED, request.auth)
    LabSample.objects.get_or_create(
        lab_order=order,
        defaults={
            "barcode": f"SGHL-{uuid_mod.uuid4().hex[:12].upper()}",
            "collected_by": request.auth,
        },
    )
    return _order_out(order)


@router.post("/orders/{order_id}/assign/", response=LabOrderOut, auth=jwt_auth)
@require_permission("lab.enter_results")
def assign_order(request, order_id: UUID):
    try:
        order = LabOrder.objects.select_related("test_type", "patient").get(pk=order_id)
    except LabOrder.DoesNotExist as exc:
        raise HttpError(404, "Commande introuvable.") from exc
    _transition(order, LabOrder.ASSIGNED, request.auth, assigned_to=request.auth)
    return _order_out(order)


@router.post("/orders/{order_id}/results/", response=LabResultOut, auth=jwt_auth)
@require_permission("lab.enter_results")
def enter_results(request, order_id: UUID, payload: LabResultIn):
    try:
        order = LabOrder.objects.get(pk=order_id)
    except LabOrder.DoesNotExist as exc:
        raise HttpError(404, "Commande introuvable.") from exc

    if order.status in (LabOrder.VALIDATED, LabOrder.PUBLISHED):
        raise HttpError(409, "Résultat verrouillé après validation.")

    result, _ = LabResult.objects.get_or_create(
        lab_order=order,
        defaults={"entered_by": request.auth},
    )
    if result.locked:
        raise HttpError(409, "Résultat immuable.")

    old_data = result.result_data
    result.result_data = payload.result_data
    result.interpretation = payload.interpretation
    result.is_abnormal = payload.is_abnormal
    result.entered_by = request.auth
    result.entered_at = timezone.now()
    result.save()

    log_audit(
        user=request.auth,
        action_type="UPDATE",
        resource_type="LabResult",
        resource_id=str(result.id),
        old_value=old_data,
        new_value=payload.result_data,
    )

    if order.status == LabOrder.ASSIGNED:
        _transition(order, LabOrder.RESULTS_ENTERED, request.auth)

    return {
        "id": result.id,
        "lab_order_id": order.id,
        "result_data": result.result_data,
        "interpretation": result.interpretation,
        "locked": result.locked,
    }


@router.post("/orders/{order_id}/validate/", response=LabOrderOut, auth=jwt_auth)
@require_permission("lab.validate_results")
def validate_results(request, order_id: UUID):
    try:
        order = LabOrder.objects.select_related("test_type", "patient", "result").get(pk=order_id)
    except LabOrder.DoesNotExist as exc:
        raise HttpError(404, "Commande introuvable.") from exc

    if not hasattr(order, "result"):
        raise HttpError(400, "Résultats non saisis.")

    _transition(
        order,
        LabOrder.VALIDATED,
        request.auth,
        validated_by=request.auth,
        validated_at=timezone.now(),
    )
    order.result.locked = True
    order.result.save(update_fields=["locked", "updated_at"])
    return _order_out(order)


@router.post("/orders/{order_id}/publish/", response=LabOrderOut, auth=jwt_auth)
@require_permission("lab.publish_results")
def publish_results(request, order_id: UUID):
    try:
        order = LabOrder.objects.select_related("test_type", "patient", "result", "validated_by").get(
            pk=order_id
        )
    except LabOrder.DoesNotExist as exc:
        raise HttpError(404, "Commande introuvable.") from exc

    _transition(order, LabOrder.PUBLISHED, request.auth, published_at=timezone.now())

    pdf_bytes = generate_lab_report_pdf(
        patient_name=str(order.patient),
        test_name=order.test_type.name,
        result_data=order.result.result_data,
        validated_by=str(order.validated_by),
    )
    path, file_hash = store_encrypted_file(pdf_bytes, "lab_reports", f"{order.id}.pdf.enc")

    Document.objects.create(
        patient=order.patient,
        hospitalization=order.hospitalization,
        lab_order=order,
        document_type=Document.LAB_REPORT,
        title=f"CR Labo — {order.test_type.name}",
        file_path=path,
        mime_type="application/pdf",
        file_size=len(pdf_bytes),
        file_hash=file_hash,
        uploaded_by=request.auth,
        signed_at=timezone.now(),
        signed_by=order.validated_by,
        signature_hash=file_hash,
    )

    invalidate_dashboard_cache()
    log_audit(user=request.auth, action_type="PUBLISH", resource_type="LabOrder", resource_id=str(order.id))
    return _order_out(order)
