from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from ninja import Router, Schema
from ninja.errors import HttpError

from clinical.models import (
    CarePlan,
    CareTask,
    Consultation,
    Hospitalization,
    ICD10Code,
    InterHospitalTransfer,
    PartnerHospital,
    Patient,
    PatientMovementHistory,
    Prescription,
    PrescriptionItem,
    TransferLog,
    VitalSign,
)
from clinical.services.movement_events import bed_location_lines, record_movement_event
from clinical.services.patient_search import filter_by_patient_name
from core.auth import jwt_auth
from core.models import Role, User
from core.permissions import require_any_permission, require_permission, require_role_or_permission
from core.services.audit import log_audit
from core.services.dashboard import invalidate_dashboard_cache
from core.services.pharmacy import deduct_for_prescription
from core.services.validators import ValidationError, validate_medical_text

router = Router(tags=["Clinique — Soins"])


class ICD10Out(Schema):
    id: UUID
    code: str
    description: str


class ConsultationIn(Schema):
    hospitalization_id: UUID
    symptoms: str
    clinical_notes: str = ""
    icd10_code_ids: list[UUID] = []


class ConsultationOut(Schema):
    id: UUID
    hospitalization_id: UUID
    doctor_id: UUID
    consultation_date: datetime
    symptoms: str
    icd10_codes: list[str]


class PrescriptionItemIn(Schema):
    medicine_name: str
    dosage: str
    frequency: str
    duration_days: int = 7
    route: str = "oral"


class PrescriptionIn(Schema):
    consultation_id: UUID
    instructions: str = ""
    items: list[PrescriptionItemIn]


class PrescriptionOut(Schema):
    id: UUID
    consultation_id: UUID
    status: str
    items: list[dict]
    stock_alerts: list[str] = []


class ValidatedPrescriptionOut(Schema):
    id: UUID
    patient_id: UUID
    patient_name: str
    patient_email: str = ""
    patient_phone: str = ""
    validated_at: datetime | None
    items: list[dict]


class VitalSignIn(Schema):
    hospitalization_id: UUID
    temperature: float | None = None
    blood_pressure_systolic: int | None = None
    blood_pressure_diastolic: int | None = None
    heart_rate: int | None = None
    respiratory_rate: int | None = None
    oxygen_saturation: int | None = None
    notes: str = ""


class VitalSignOut(Schema):
    id: UUID
    recorded_at: datetime
    temperature: float | None
    heart_rate: int | None
    oxygen_saturation: int | None


class CareTaskOut(Schema):
    id: UUID
    description: str
    scheduled_at: datetime
    status: str


class PatientCareTaskOut(Schema):
    id: UUID
    description: str
    scheduled_at: datetime
    status: str
    plan_title: str


class TransferIn(Schema):
    hospitalization_id: UUID
    to_bed_id: UUID
    reason: str = ""


class PartnerHospitalOut(Schema):
    id: UUID
    name: str
    city: str
    address: str
    phone: str
    specialties: str
    available_beds: int
    total_beds: int
    can_receive: bool


class InterHospitalTransferIn(Schema):
    hospitalization_id: UUID
    partner_hospital_id: UUID
    reason: str
    clinical_summary: str = ""


class InterHospitalTransferOut(Schema):
    id: UUID
    hospitalization_id: UUID
    patient_name: str
    admission_reason: str
    admission_date: datetime
    department_name: str
    room_number: str
    bed_label: str
    partner_hospital_id: UUID
    partner_hospital_name: str
    partner_hospital_city: str
    partner_hospital_address: str
    partner_hospital_phone: str
    partner_hospital_specialties: str
    reason: str
    clinical_summary: str
    status: str
    status_label: str
    requested_by_name: str
    validated_by_name: str | None
    validated_at: datetime | None
    created_at: datetime


class InterHospitalTransferRejectIn(Schema):
    rejection_reason: str = ""


class TransferPatientSearchOut(Schema):
    patient_id: UUID
    patient_name: str
    hospitalization_id: UUID | None = None
    is_hospitalized: bool
    admission_reason: str = ""
    department_name: str = ""
    room_number: str = ""
    bed_label: str = ""
    status_label: str = ""


def _inter_transfer_out(t: InterHospitalTransfer) -> dict:
    status_labels = dict(InterHospitalTransfer.STATUS_CHOICES)
    hosp = t.hospitalization
    bed = hosp.bed if hosp else None
    partner = t.partner_hospital
    return {
        "id": t.id,
        "hospitalization_id": t.hospitalization_id,
        "patient_name": str(hosp.patient) if hosp else "",
        "admission_reason": hosp.admission_reason if hosp else "",
        "admission_date": hosp.admission_date if hosp else t.created_at,
        "department_name": bed.room.department.name if bed and bed.room_id else "",
        "room_number": bed.room.number if bed and bed.room_id else "",
        "bed_label": bed.label if bed else "",
        "partner_hospital_id": t.partner_hospital_id,
        "partner_hospital_name": partner.name,
        "partner_hospital_city": partner.city,
        "partner_hospital_address": partner.address,
        "partner_hospital_phone": partner.phone,
        "partner_hospital_specialties": partner.specialties,
        "reason": t.reason,
        "clinical_summary": t.clinical_summary,
        "status": t.status,
        "status_label": status_labels.get(t.status, t.status),
        "requested_by_name": t.requested_by.get_full_name() if t.requested_by else "",
        "validated_by_name": t.validated_by.get_full_name() if t.validated_by else None,
        "validated_at": t.validated_at,
        "created_at": t.created_at,
    }


class DischargeIn(Schema):
    hospitalization_id: UUID
    expected_version: int | None = None


def _require_active_hospitalization(hosp_id: UUID) -> Hospitalization:
    try:
        hosp = Hospitalization.objects.get(pk=hosp_id, status=Hospitalization.ACTIVE)
    except Hospitalization.DoesNotExist as exc:
        raise HttpError(404, "Hospitalisation active introuvable.") from exc
    return hosp


@router.get("/icd10/", response=list[ICD10Out], auth=jwt_auth)
@require_permission("clinical.consult")
def list_icd10(request, search: str = ""):
    qs = ICD10Code.objects.all()
    if search:
        qs = qs.filter(Q(code__icontains=search) | Q(description__icontains=search))
    return [{"id": c.id, "code": c.code, "description": c.description} for c in qs[:50]]


@router.post("/consultations/", response=ConsultationOut, auth=jwt_auth)
@require_permission("clinical.consult")
def create_consultation(request, payload: ConsultationIn):
    hosp = _require_active_hospitalization(payload.hospitalization_id)
    consultation = Consultation.objects.create(
        hospitalization=hosp,
        doctor=request.auth,
        symptoms=payload.symptoms,
        clinical_notes=payload.clinical_notes,
    )
    if payload.icd10_code_ids:
        consultation.icd10_codes.set(ICD10Code.objects.filter(id__in=payload.icd10_code_ids))
    log_audit(
        user=request.auth,
        action_type="CREATE",
        resource_type="Consultation",
        resource_id=str(consultation.id),
    )
    return {
        "id": consultation.id,
        "hospitalization_id": hosp.id,
        "doctor_id": request.auth.id,
        "consultation_date": consultation.consultation_date,
        "symptoms": consultation.symptoms,
        "icd10_codes": list(consultation.icd10_codes.values_list("code", flat=True)),
    }


@router.get("/prescriptions/validated/", response=list[ValidatedPrescriptionOut], auth=jwt_auth)
@require_permission("pharmacy.dispense")
def list_validated_prescriptions(request):
    prescriptions = (
        Prescription.objects.filter(status=Prescription.VALIDATED)
        .select_related("consultation__hospitalization__patient", "doctor")
        .order_by("-validated_at")[:50]
    )
    rows = []
    for p in prescriptions:
        patient = p.consultation.hospitalization.patient
        email = (patient.email or "").strip()
        if not email and patient.user_id and getattr(patient, "user", None) and patient.user.email:
            email = patient.user.email.strip()
        rows.append(
            {
                "id": p.id,
                "patient_id": patient.id,
                "patient_name": str(patient),
                "patient_email": email,
                "patient_phone": patient.phone or "",
                "validated_at": p.validated_at,
                "items": [
                    {"medicine_name": i.medicine_name, "dosage": i.dosage, "frequency": i.frequency}
                    for i in p.items.all()
                ],
            }
        )
    return rows


@router.post("/prescriptions/", response=PrescriptionOut, auth=jwt_auth)
@require_permission("clinical.prescribe")
def create_prescription(request, payload: PrescriptionIn):
    try:
        consultation = Consultation.objects.select_related("hospitalization").get(
            pk=payload.consultation_id
        )
    except Consultation.DoesNotExist as exc:
        raise HttpError(404, "Consultation introuvable.") from exc

    if consultation.hospitalization.status != Hospitalization.ACTIVE:
        raise HttpError(409, "Hospitalisation non active.")

    prescription = Prescription.objects.create(
        consultation=consultation,
        doctor=request.auth,
        instructions=payload.instructions,
    )
    items = []
    for item in payload.items:
        pi = PrescriptionItem.objects.create(prescription=prescription, **item.dict())
        items.append({"medicine_name": pi.medicine_name, "dosage": pi.dosage, "frequency": pi.frequency})

    log_audit(
        user=request.auth,
        action_type="CREATE",
        resource_type="Prescription",
        resource_id=str(prescription.id),
    )
    return {
        "id": prescription.id,
        "consultation_id": consultation.id,
        "status": prescription.status,
        "items": items,
    }


@router.post("/prescriptions/{prescription_id}/validate/", response=PrescriptionOut, auth=jwt_auth)
@require_permission("clinical.prescribe")
def validate_prescription(request, prescription_id: UUID):
    try:
        prescription = Prescription.objects.select_related("consultation").get(pk=prescription_id)
    except Prescription.DoesNotExist as exc:
        raise HttpError(404, "Prescription introuvable.") from exc

    if prescription.status == Prescription.VALIDATED:
        raise HttpError(409, "Prescription déjà validée et verrouillée.")

    prescription.status = Prescription.VALIDATED
    prescription.validated_at = timezone.now()
    prescription.save(update_fields=["status", "validated_at", "updated_at", "version"])

    # Générer plan de soins
    care_plan = CarePlan.objects.create(
        hospitalization=prescription.consultation.hospitalization,
        prescription=prescription,
        title=f"Plan — Ordonnance {prescription.id}",
    )
    for item in prescription.items.all():
        for day in range(item.duration_days):
            CareTask.objects.create(
                care_plan=care_plan,
                description=f"{item.medicine_name} {item.dosage} — {item.frequency}",
                scheduled_at=timezone.now() + timedelta(days=day),
            )

    log_audit(
        user=request.auth,
        action_type="VALIDATE",
        resource_type="Prescription",
        resource_id=str(prescription.id),
    )
    stock_alerts = deduct_for_prescription(prescription, request.auth)
    items = [
        {"medicine_name": i.medicine_name, "dosage": i.dosage, "frequency": i.frequency}
        for i in prescription.items.all()
    ]
    return {
        "id": prescription.id,
        "consultation_id": prescription.consultation_id,
        "status": prescription.status,
        "items": items,
        "stock_alerts": stock_alerts,
    }


@router.post("/vital-signs/", response=VitalSignOut, auth=jwt_auth)
@require_permission("clinical.nursing_care")
def record_vital_signs(request, payload: VitalSignIn):
    hosp = _require_active_hospitalization(payload.hospitalization_id)
    vs = VitalSign.objects.create(
        hospitalization=hosp,
        nurse=request.auth,
        temperature=payload.temperature,
        blood_pressure_systolic=payload.blood_pressure_systolic,
        blood_pressure_diastolic=payload.blood_pressure_diastolic,
        heart_rate=payload.heart_rate,
        respiratory_rate=payload.respiratory_rate,
        oxygen_saturation=payload.oxygen_saturation,
        notes=payload.notes,
    )
    return {
        "id": vs.id,
        "recorded_at": vs.recorded_at,
        "temperature": float(vs.temperature) if vs.temperature else None,
        "heart_rate": vs.heart_rate,
        "oxygen_saturation": vs.oxygen_saturation,
    }


@router.get("/vital-signs/{hospitalization_id}/", response=list[VitalSignOut], auth=jwt_auth)
@require_permission("clinical.view_patient")
def list_vital_signs(request, hospitalization_id: UUID):
    signs = VitalSign.objects.filter(hospitalization_id=hospitalization_id).order_by("-recorded_at")[:50]
    return [
        {
            "id": s.id,
            "recorded_at": s.recorded_at,
            "temperature": float(s.temperature) if s.temperature else None,
            "heart_rate": s.heart_rate,
            "oxygen_saturation": s.oxygen_saturation,
        }
        for s in signs
    ]


@router.get("/care-tasks/patient/{patient_id}/", response=list[PatientCareTaskOut], auth=jwt_auth)
def list_patient_care_tasks(request, patient_id: UUID):
    """Plan de soins visible par le patient (mobile)."""
    profile = getattr(request.auth, "patient_profile", None)
    if profile and profile.id != patient_id and not request.auth.has_perm_code("clinical.nursing_care"):
        raise HttpError(403, "Accès refusé.")

    tasks = (
        CareTask.objects.filter(
            care_plan__hospitalization__patient_id=patient_id,
            care_plan__is_active=True,
            care_plan__hospitalization__status=Hospitalization.ACTIVE,
        )
        .select_related("care_plan")
        .order_by("scheduled_at")[:50]
    )
    return [
        {
            "id": t.id,
            "description": t.description,
            "scheduled_at": t.scheduled_at,
            "status": t.status,
            "plan_title": t.care_plan.title,
        }
        for t in tasks
    ]


@router.get("/care-tasks/overdue/", response=list[CareTaskOut], auth=jwt_auth)
@require_permission("clinical.nursing_care")
def list_overdue_care_tasks(request):
    """Marque les tâches en retard comme MISSED et les retourne."""
    overdue = CareTask.objects.filter(
        status=CareTask.PENDING,
        scheduled_at__lt=timezone.now() - timedelta(hours=1),
    )
    overdue.update(status=CareTask.MISSED)
    tasks = CareTask.objects.filter(
        status__in=[CareTask.PENDING, CareTask.MISSED],
        scheduled_at__lte=timezone.now() + timedelta(hours=2),
    ).order_by("scheduled_at")[:50]
    return [
        {"id": t.id, "description": t.description, "scheduled_at": t.scheduled_at, "status": t.status}
        for t in tasks
    ]


@router.get("/care-tasks/pending/", response=list[CareTaskOut], auth=jwt_auth)
@require_permission("clinical.nursing_care")
def list_pending_care_tasks(request):
    tasks = CareTask.objects.filter(
        status=CareTask.PENDING,
        scheduled_at__lte=timezone.now() + timedelta(hours=2),
    ).order_by("scheduled_at")[:50]
    return [
        {"id": t.id, "description": t.description, "scheduled_at": t.scheduled_at, "status": t.status}
        for t in tasks
    ]


@router.post("/care-tasks/{task_id}/complete/", response=CareTaskOut, auth=jwt_auth)
@require_permission("clinical.nursing_care")
def complete_care_task(request, task_id: UUID):
    try:
        task = CareTask.objects.get(pk=task_id)
    except CareTask.DoesNotExist as exc:
        raise HttpError(404, "Tâche introuvable.") from exc
    task.status = CareTask.DONE
    task.administered_at = timezone.now()
    task.nurse = request.auth
    task.save(update_fields=["status", "administered_at", "nurse", "updated_at"])
    return {
        "id": task.id,
        "description": task.description,
        "scheduled_at": task.scheduled_at,
        "status": task.status,
    }


@router.post("/transfers/", auth=jwt_auth)
@require_permission("clinical.transfer")
def transfer_patient(request, payload: TransferIn):
    from clinical.models import Bed

    try:
        reason = validate_medical_text(payload.reason, field="Motif médical")
    except ValidationError as exc:
        raise HttpError(400, str(exc)) from exc

    try:
        with transaction.atomic():
            hosp = Hospitalization.objects.select_for_update().select_related(
                "patient", "bed__room__department"
            ).get(
                pk=payload.hospitalization_id, status=Hospitalization.ACTIVE
            )
            to_bed = Bed.objects.select_for_update().select_related(
                "room__department"
            ).get(pk=payload.to_bed_id, is_active=True)
            if to_bed.status != Bed.AVAILABLE:
                raise HttpError(409, "Lit de destination non disponible.")

            from_bed = hosp.bed
            from_bed = Bed.objects.select_for_update().select_related("room__department").get(pk=from_bed.id)
            from_bed.status = Bed.AVAILABLE
            from_bed.save(update_fields=["status", "updated_at"])

            TransferLog.objects.create(
                hospitalization=hosp,
                from_bed=from_bed,
                to_bed=to_bed,
                transferred_by=request.auth,
                reason=reason,
            )

            from_loc = bed_location_lines(from_bed)
            to_loc = bed_location_lines(to_bed)

            hosp.bed = to_bed
            hosp.version += 1
            hosp.save(update_fields=["bed", "version", "updated_at"])

            to_bed.status = Bed.OCCUPIED
            to_bed.save(update_fields=["status", "updated_at"])
    except Hospitalization.DoesNotExist as exc:
        raise HttpError(404, "Hospitalisation introuvable.") from exc
    except Bed.DoesNotExist as exc:
        raise HttpError(404, "Lit introuvable.") from exc

    invalidate_dashboard_cache()
    log_audit(
        user=request.auth,
        action_type="TRANSFER",
        resource_type="Hospitalization",
        resource_id=str(hosp.id),
        new_value={"to_bed_id": str(to_bed.id)},
    )
    record_movement_event(
        event_type=PatientMovementHistory.INTERNAL_TRANSFER,
        patient=hosp.patient,
        hospitalization=hosp,
        event_at=timezone.now(),
        performed_by=request.auth,
        details={
            "from_department": from_loc.get("department", ""),
            "from_room": from_loc.get("room", ""),
            "from_bed": from_loc.get("bed", ""),
            "to_department": to_loc.get("department", ""),
            "to_room": to_loc.get("room", ""),
            "to_bed": to_loc.get("bed", ""),
            "reason": reason,
        },
    )
    return {"detail": "Transfert effectué.", "new_bed_id": str(to_bed.id)}


def _partner_hospital_out(h: PartnerHospital) -> dict:
    return {
        "id": h.id,
        "name": h.name,
        "city": h.city,
        "address": h.address,
        "phone": h.phone,
        "specialties": h.specialties,
        "available_beds": h.available_beds,
        "total_beds": h.total_beds,
        "can_receive": h.can_receive,
    }


@router.get("/transfers/patient-search/", response=list[TransferPatientSearchOut], auth=jwt_auth)
@require_any_permission("clinical.transfer", "clinical.validate_transfer")
def search_patients_for_transfer(request, search: str = ""):
    """Patients enregistrés avec statut d'hospitalisation."""
    term = (search or "").strip()
    if len(term) < 2:
        return []

    patients = filter_by_patient_name(
        Patient.objects.filter(is_active=True),
        term,
    ).order_by("last_name", "first_name")[:30]

    patient_ids = [p.id for p in patients]
    active_by_patient = {
        h.patient_id: h
        for h in Hospitalization.objects.filter(
            patient_id__in=patient_ids,
            status=Hospitalization.ACTIVE,
        ).select_related("bed__room__department")
    }

    results = []
    for patient in patients:
        hosp = active_by_patient.get(patient.id)
        if hosp:
            bed = hosp.bed
            results.append(
                {
                    "patient_id": patient.id,
                    "patient_name": str(patient),
                    "hospitalization_id": hosp.id,
                    "is_hospitalized": True,
                    "admission_reason": hosp.admission_reason,
                    "department_name": bed.room.department.name if bed and bed.room_id else "",
                    "room_number": bed.room.number if bed and bed.room_id else "",
                    "bed_label": bed.label if bed else "",
                    "status_label": "Hospitalisé — transfert possible",
                }
            )
        else:
            results.append(
                {
                    "patient_id": patient.id,
                    "patient_name": str(patient),
                    "hospitalization_id": None,
                    "is_hospitalized": False,
                    "admission_reason": "",
                    "department_name": "",
                    "room_number": "",
                    "bed_label": "",
                    "status_label": "Enregistré — admission requise avant transfert",
                }
            )

    results.sort(key=lambda row: (not row["is_hospitalized"], row["patient_name"]))
    return results


@router.get("/partner-hospitals/", response=list[PartnerHospitalOut], auth=jwt_auth)
@require_role_or_permission(Role.DOCTOR, permission="clinical.view_partner_hospitals")
def list_partner_hospitals(request, search: str = "", city: str = "", only_available: bool = False):
    hospitals = PartnerHospital.objects.filter(is_active=True, accepts_transfers=True).order_by("name")
    if search:
        hospitals = hospitals.filter(
            Q(name__icontains=search)
            | Q(city__icontains=search)
            | Q(specialties__icontains=search)
            | Q(address__icontains=search)
        )
    if city:
        hospitals = hospitals.filter(city__iexact=city)
    if only_available:
        hospitals = hospitals.filter(available_beds__gt=0)
    return [_partner_hospital_out(h) for h in hospitals]


@router.get("/partner-hospitals/cities/", auth=jwt_auth)
@require_role_or_permission(Role.DOCTOR, permission="clinical.view_partner_hospitals")
def list_partner_hospital_cities(request):
    cities = (
        PartnerHospital.objects.filter(is_active=True, accepts_transfers=True)
        .values_list("city", flat=True)
        .distinct()
        .order_by("city")
    )
    return list(cities)


@router.get("/inter-hospital-transfers/", response=list[InterHospitalTransferOut], auth=jwt_auth)
@require_any_permission("clinical.transfer", "clinical.validate_transfer")
def list_inter_hospital_transfers(request, status: str = ""):
    qs = (
        InterHospitalTransfer.objects.select_related(
            "hospitalization__patient",
            "hospitalization__bed__room__department",
            "partner_hospital",
            "requested_by",
            "validated_by",
        )
        .order_by("-created_at")[:50]
    )
    if status:
        qs = qs.filter(status=status.upper())
    return [_inter_transfer_out(t) for t in qs]


@router.post("/inter-hospital-transfers/", response=InterHospitalTransferOut, auth=jwt_auth)
@require_permission("clinical.transfer")
def create_inter_hospital_transfer(request, payload: InterHospitalTransferIn):
    try:
        reason = validate_medical_text(payload.reason, field="Motif médical du transfert")
        clinical_summary = validate_medical_text(
            payload.clinical_summary,
            field="Résumé clinique",
            required=False,
            min_len=5,
        )
    except ValidationError as exc:
        raise HttpError(400, str(exc)) from exc

    hosp = _require_active_hospitalization(payload.hospitalization_id)
    if InterHospitalTransfer.objects.filter(
        hospitalization=hosp, status=InterHospitalTransfer.PENDING
    ).exists():
        raise HttpError(409, "Une demande de transfert est déjà en attente pour ce patient.")

    try:
        partner = PartnerHospital.objects.get(
            pk=payload.partner_hospital_id, is_active=True, accepts_transfers=True
        )
    except PartnerHospital.DoesNotExist as exc:
        raise HttpError(404, "Hôpital partenaire introuvable.") from exc
    if not partner.can_receive:
        raise HttpError(409, "Cet établissement n'a plus de capacité d'accueil.")

    transfer = InterHospitalTransfer.objects.create(
        hospitalization=hosp,
        partner_hospital=partner,
        reason=reason,
        clinical_summary=clinical_summary,
        requested_by=request.auth,
    )
    transfer = InterHospitalTransfer.objects.select_related(
        "hospitalization__patient",
        "hospitalization__bed__room__department",
        "partner_hospital",
        "requested_by",
        "validated_by",
    ).get(pk=transfer.id)
    log_audit(
        user=request.auth,
        action_type="CREATE",
        resource_type="InterHospitalTransfer",
        resource_id=str(transfer.id),
    )
    return _inter_transfer_out(transfer)


@router.post("/inter-hospital-transfers/{transfer_id}/validate/", response=InterHospitalTransferOut, auth=jwt_auth)
@require_permission("clinical.validate_transfer")
def validate_inter_hospital_transfer(request, transfer_id: UUID):
    from clinical.models import Bed

    try:
        with transaction.atomic():
            transfer = (
                InterHospitalTransfer.objects.select_for_update()
                .select_related("hospitalization__patient", "partner_hospital", "requested_by")
                .get(pk=transfer_id)
            )
            if transfer.status != InterHospitalTransfer.PENDING:
                raise HttpError(409, "Ce transfert ne peut plus être validé.")

            partner = PartnerHospital.objects.select_for_update().get(pk=transfer.partner_hospital_id)
            if not partner.can_receive:
                raise HttpError(409, "L'établissement destinataire n'a plus de capacité.")

            hosp = Hospitalization.objects.select_for_update().select_related(
                "patient", "bed__room__department", "referring_doctor"
            ).get(
                pk=transfer.hospitalization_id, status=Hospitalization.ACTIVE
            )
            bed = Bed.objects.select_for_update().get(pk=hosp.bed_id)
            bed_loc = bed_location_lines(bed)
            bed.status = Bed.AVAILABLE
            bed.save(update_fields=["status", "updated_at"])

            hosp.status = Hospitalization.TRANSFERRED
            hosp.actual_discharge_date = timezone.now()
            hosp.version += 1
            hosp.save(update_fields=["status", "actual_discharge_date", "version", "updated_at"])

            partner.available_beds = max(0, partner.available_beds - 1)
            partner.save(update_fields=["available_beds", "updated_at"])

            transfer.status = InterHospitalTransfer.APPROVED
            transfer.validated_by = request.auth
            transfer.validated_at = timezone.now()
            transfer.save(update_fields=["status", "validated_by", "validated_at", "updated_at"])
    except InterHospitalTransfer.DoesNotExist as exc:
        raise HttpError(404, "Demande de transfert introuvable.") from exc

    invalidate_dashboard_cache()
    log_audit(
        user=request.auth,
        action_type="UPDATE",
        resource_type="InterHospitalTransfer",
        resource_id=str(transfer.id),
        new_value={"status": InterHospitalTransfer.APPROVED},
    )
    record_movement_event(
        event_type=PatientMovementHistory.INTER_TRANSFER,
        patient=transfer.hospitalization.patient,
        hospitalization=transfer.hospitalization,
        event_at=transfer.validated_at or timezone.now(),
        performed_by=request.auth,
        details={
            **bed_loc,
            "partner_hospital": transfer.partner_hospital.name,
            "partner_city": transfer.partner_hospital.city,
            "reason": transfer.reason,
            "clinical_summary": transfer.clinical_summary,
            "doctor": (
                f"Dr. {transfer.requested_by.last_name} {transfer.requested_by.first_name}".strip()
                if transfer.requested_by
                else ""
            ),
        },
    )
    transfer = InterHospitalTransfer.objects.select_related(
        "hospitalization__patient",
        "hospitalization__bed__room__department",
        "partner_hospital",
        "requested_by",
        "validated_by",
    ).get(pk=transfer.id)
    return _inter_transfer_out(transfer)


@router.post("/inter-hospital-transfers/{transfer_id}/reject/", response=InterHospitalTransferOut, auth=jwt_auth)
@require_permission("clinical.validate_transfer")
def reject_inter_hospital_transfer(request, transfer_id: UUID, payload: InterHospitalTransferRejectIn):
    try:
        with transaction.atomic():
            transfer = (
                InterHospitalTransfer.objects.select_for_update()
                .select_related("hospitalization__patient", "partner_hospital", "requested_by")
                .get(pk=transfer_id)
            )
            if transfer.status != InterHospitalTransfer.PENDING:
                raise HttpError(409, "Cette demande ne peut plus être refusée.")

            transfer.status = InterHospitalTransfer.REJECTED
            transfer.validated_by = request.auth
            transfer.validated_at = timezone.now()
            if payload.rejection_reason.strip():
                note = f"Motif du refus : {payload.rejection_reason.strip()}"
                transfer.clinical_summary = (
                    f"{transfer.clinical_summary}\n\n{note}".strip()
                    if transfer.clinical_summary
                    else note
                )
            transfer.save(
                update_fields=["status", "validated_by", "validated_at", "clinical_summary", "updated_at"]
            )
    except InterHospitalTransfer.DoesNotExist as exc:
        raise HttpError(404, "Demande de transfert introuvable.") from exc

    log_audit(
        user=request.auth,
        action_type="UPDATE",
        resource_type="InterHospitalTransfer",
        resource_id=str(transfer.id),
        new_value={"status": InterHospitalTransfer.REJECTED},
    )
    transfer = InterHospitalTransfer.objects.select_related(
        "hospitalization__patient",
        "hospitalization__bed__room__department",
        "partner_hospital",
        "requested_by",
        "validated_by",
    ).get(pk=transfer.id)
    return _inter_transfer_out(transfer)


@router.post("/discharges/", auth=jwt_auth)
@require_permission("clinical.admit_patient")
def discharge_patient(request, payload: DischargeIn):
    from clinical.models import Bed

    try:
        with transaction.atomic():
            hosp = Hospitalization.objects.select_for_update().select_related(
                "patient", "bed__room__department", "referring_doctor"
            ).get(
                pk=payload.hospitalization_id, status=Hospitalization.ACTIVE
            )
            if payload.expected_version is not None and hosp.version != payload.expected_version:
                raise HttpError(409, "Conflit de version — rechargez la page.")
            bed = Bed.objects.select_for_update().get(pk=hosp.bed_id)
            discharge_at = timezone.now()
            bed_loc = bed_location_lines(bed)
            hosp.status = Hospitalization.DISCHARGED
            hosp.actual_discharge_date = discharge_at
            hosp.save(update_fields=["status", "actual_discharge_date", "updated_at"])
            bed.status = Bed.AVAILABLE
            bed.save(update_fields=["status", "updated_at"])
    except Hospitalization.DoesNotExist as exc:
        raise HttpError(404, "Hospitalisation introuvable.") from exc

    invalidate_dashboard_cache()
    log_audit(
        user=request.auth,
        action_type="UPDATE",
        resource_type="Hospitalization",
        resource_id=str(hosp.id),
        new_value={"status": "DISCHARGED"},
    )
    record_movement_event(
        event_type=PatientMovementHistory.DISCHARGE,
        patient=hosp.patient,
        hospitalization=hosp,
        event_at=discharge_at,
        performed_by=request.auth,
        details={
            **bed_loc,
            "doctor": f"Dr. {hosp.referring_doctor.last_name} {hosp.referring_doctor.first_name}".strip(),
            "admission_reason": hosp.admission_reason,
        },
    )
    return {"detail": "Patient sorti."}
