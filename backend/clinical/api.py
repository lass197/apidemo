from typing import Optional

from datetime import date, datetime
from uuid import UUID

from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from ninja import Router, Schema
from ninja.errors import HttpError

from clinical.models import Bed, Hospitalization, InterHospitalTransfer, Patient, PatientMovementHistory
from clinical.services.movement_events import bed_location_lines, movement_history_out, record_movement_event
from clinical.services.patient_search import filter_by_patient_name
from core.auth import jwt_auth
from core.models import Role, User
from core.permissions import require_any_permission, require_permission
from core.services.audit import log_audit
from core.services.patient_identity import resolve_doctor_for_patient
from core.services.pdf import generate_patient_identity_pdf
from core.services.patient_registration import normalize_email
from core.services.validators import sanitize_patient_payload, validate_email_format

router = Router(tags=["Clinique"])


class PatientOut(Schema):
    id: UUID
    first_name: str
    last_name: str
    date_of_birth: date
    gender: str
    phone: str
    email: str = ""


class PatientUpdateIn(Schema):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class PatientIn(Schema):
    first_name: str
    last_name: str
    date_of_birth: date
    gender: str
    phone: str = ""
    email: str = ""
    address: str = ""
    social_security_number: str = ""
    emergency_contact: str = ""
    emergency_phone: str = ""


class BedOut(Schema):
    id: UUID
    label: str
    room_number: str
    department_name: str
    status: str


class HospitalizationOut(Schema):
    id: UUID
    patient_id: UUID
    patient_name: str
    bed_id: UUID
    bed_label: str = ""
    room_number: str = ""
    department_name: str = ""
    referring_doctor_id: UUID
    admission_date: datetime
    expected_discharge_date: date
    status: str
    admission_reason: str


def _hospitalization_out(h: Hospitalization) -> dict:
    bed = h.bed
    return {
        "id": h.id,
        "patient_id": h.patient_id,
        "patient_name": str(h.patient),
        "bed_id": h.bed_id,
        "bed_label": bed.label if bed else "",
        "room_number": bed.room.number if bed and bed.room_id else "",
        "department_name": bed.room.department.name if bed and bed.room_id else "",
        "referring_doctor_id": h.referring_doctor_id,
        "admission_date": h.admission_date,
        "expected_discharge_date": h.expected_discharge_date,
        "status": h.status,
        "admission_reason": h.admission_reason,
    }


class AdmissionIn(Schema):
    patient_id: UUID
    bed_id: UUID
    referring_doctor_id: UUID
    expected_discharge_date: date
    admission_reason: str
    notes: str = ""


class DoctorOut(Schema):
    id: UUID
    first_name: str
    last_name: str
    username: str


@router.get("/doctors/", response=list[DoctorOut], auth=jwt_auth)
@require_permission("clinical.admit_patient")
def list_doctors(request, search: str = ""):
    doctors = User.objects.filter(
        is_active=True,
        roles__role__code=Role.DOCTOR,
        roles__is_active=True,
    ).distinct()
    term = (search or "").strip()
    if term:
        from django.db.models import Q

        words = [w for w in term.split() if len(w) >= 2] or [term]
        for word in words:
            doctors = doctors.filter(
                Q(first_name__icontains=word)
                | Q(last_name__icontains=word)
                | Q(username__icontains=word)
            )
    doctors = doctors.order_by("last_name", "first_name")[:30]
    return [
        {
            "id": d.id,
            "first_name": d.first_name,
            "last_name": d.last_name,
            "username": d.username,
        }
        for d in doctors
    ]


def _patient_email(p: Patient) -> str:
    if p.email and str(p.email).strip():
        return str(p.email).strip()
    if p.user_id and getattr(p, "user", None) and p.user.email:
        return p.user.email.strip()
    return ""


def _patient_out(p: Patient) -> dict:
    return {
        "id": p.id,
        "first_name": p.first_name,
        "last_name": p.last_name,
        "date_of_birth": p.date_of_birth,
        "gender": p.gender,
        "phone": p.phone or "",
        "email": _patient_email(p),
    }


def _prepare_patient_email(email: str | None) -> str | None:
    """Normalise email dossier patient ; vide → NULL (unicité partielle)."""
    if not email or not str(email).strip():
        return None
    return normalize_email(str(email).strip())


def _validate_patient_email_unique(email: str | None, *, exclude_patient_id: UUID | None = None) -> None:
    if not email:
        return
    if User.objects.filter(email__iexact=email).exists():
        raise HttpError(409, "Un compte utilisateur existe déjà avec cet email.")
    qs = Patient.objects.filter(email__iexact=email, is_active=True)
    if exclude_patient_id:
        qs = qs.exclude(pk=exclude_patient_id)
    if qs.exists():
        raise HttpError(409, "Un dossier patient existe déjà avec cet email.")


@router.get("/patients/me/", response=PatientOut, auth=jwt_auth)
def my_patient_profile(request):
    patient = getattr(request.auth, "patient_profile", None)
    if not patient:
        raise HttpError(404, "Profil patient non lié à ce compte.")
    return _patient_out(patient)


@router.get("/patients/me/identity-pdf/", auth=jwt_auth)
def download_my_patient_identity_pdf(request, doctor_id: UUID | None = None):
    """Carte patient PDF avec identifiants et QR code (infos complètes + médecin choisi)."""
    patient = getattr(request.auth, "patient_profile", None)
    if not patient:
        raise HttpError(404, "Profil patient non lié à ce compte.")

    doctor = resolve_doctor_for_patient(patient, doctor_id)
    if doctor_id and not doctor:
        raise HttpError(404, "Médecin introuvable.")

    pdf_bytes = generate_patient_identity_pdf(patient=patient, doctor=doctor)
    filename = f"carte-patient-{patient.last_name}-{patient.first_name}.pdf".replace(" ", "-")
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@router.get("/patients/{patient_id}/", response=PatientOut, auth=jwt_auth)
@require_permission("clinical.view_patient")
def get_patient(request, patient_id: UUID):
    try:
        patient = Patient.objects.get(pk=patient_id, is_active=True)
    except Patient.DoesNotExist as exc:
        raise HttpError(404, "Patient introuvable.") from exc
    return _patient_out(patient)


@router.get("/patients/", response=list[PatientOut], auth=jwt_auth)
@require_permission("clinical.view_patient")
def list_patients(request, page: int = 1, page_size: int = 20, search: str = ""):
    offset = (page - 1) * page_size
    qs = Patient.objects.filter(is_active=True).select_related("user").order_by("last_name", "first_name")
    if search.strip():
        qs = filter_by_patient_name(qs, search.strip())
    patients = qs[offset : offset + page_size]
    return [_patient_out(p) for p in patients]


@router.post("/patients/", response=PatientOut, auth=jwt_auth)
@require_any_permission("clinical.admit_patient", "pharmacy.dispense")
def create_patient(request, payload: PatientIn):
    try:
        data = sanitize_patient_payload(payload.dict(), partial=False)
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc
    data["email"] = _prepare_patient_email(data.get("email"))
    if data["email"]:
        try:
            data["email"] = validate_email_format(data["email"])
        except ValueError as exc:
            raise HttpError(400, str(exc)) from exc
    _validate_patient_email_unique(data["email"])
    patient = Patient.objects.create(**data)
    log_audit(
        user=request.auth,
        action_type="CREATE",
        resource_type="Patient",
        resource_id=str(patient.id),
        new_value=_patient_out(patient),
    )
    return _patient_out(patient)


@router.patch("/patients/{patient_id}/", response=PatientOut, auth=jwt_auth)
@require_permission("clinical.admit_patient")
def update_patient(request, patient_id: UUID, payload: PatientUpdateIn):
    try:
        patient = Patient.objects.get(pk=patient_id, is_active=True)
    except Patient.DoesNotExist as exc:
        raise HttpError(404, "Patient introuvable.") from exc

    updates = payload.dict(exclude_unset=True)
    if "email" in updates:
        updates["email"] = _prepare_patient_email(updates["email"])
        if updates["email"]:
            try:
                validate_email_format(updates["email"])
            except ValueError as exc:
                raise HttpError(400, str(exc)) from exc
        _validate_patient_email_unique(updates["email"], exclude_patient_id=patient.id)

    if not updates:
        return _patient_out(patient)

    try:
        updates = sanitize_patient_payload(updates, partial=True)
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc

    for field, value in updates.items():
        setattr(patient, field, value)
    patient.save(update_fields=[*updates.keys(), "updated_at"])

    log_audit(
        user=request.auth,
        action_type="UPDATE",
        resource_type="Patient",
        resource_id=str(patient.id),
        new_value=_patient_out(patient),
    )
    return _patient_out(patient)


@router.delete("/patients/{patient_id}/", auth=jwt_auth)
@require_permission("clinical.admit_patient")
def archive_patient(request, patient_id: UUID):
    try:
        patient = Patient.objects.get(pk=patient_id, is_active=True)
    except Patient.DoesNotExist as exc:
        raise HttpError(404, "Patient introuvable.") from exc
    if Hospitalization.objects.filter(patient=patient, status=Hospitalization.ACTIVE).exists():
        raise HttpError(409, "Impossible d'archiver : hospitalisation active.")
    patient.is_active = False
    patient.save(update_fields=["is_active", "updated_at"])
    log_audit(
        user=request.auth,
        action_type="DELETE",
        resource_type="Patient",
        resource_id=str(patient.id),
    )
    return {"detail": "Dossier patient archivé."}


@router.get("/beds/available/", response=list[BedOut], auth=jwt_auth)
@require_any_permission("clinical.admit_patient", "clinical.transfer")
def list_available_beds(request, search: str = ""):
    beds = (
        Bed.objects.filter(status=Bed.AVAILABLE, is_active=True)
        .select_related("room__department")
        .order_by("room__department__name", "room__number", "label")
    )
    term = (search or "").strip().lower()
    if term:
        beds = [
            b
            for b in beds
            if term in b.label.lower()
            or term in b.room.number.lower()
            or term in b.room.department.name.lower()
        ]
    return [
        {
            "id": b.id,
            "label": b.label,
            "room_number": b.room.number,
            "department_name": b.room.department.name,
            "status": b.status,
        }
        for b in beds
    ]


@router.post("/admissions/", response=HospitalizationOut, auth=jwt_auth)
@require_permission("clinical.admit_patient")
def admit_patient(request, payload: AdmissionIn):
    try:
        patient = Patient.objects.get(pk=payload.patient_id, is_active=True)
        doctor = User.objects.get(pk=payload.referring_doctor_id, is_active=True)
    except Patient.DoesNotExist as exc:
        raise HttpError(404, "Patient introuvable.") from exc
    except User.DoesNotExist as exc:
        raise HttpError(404, "Médecin référent introuvable.") from exc

    if Hospitalization.objects.filter(patient=patient, status=Hospitalization.ACTIVE).exists():
        raise HttpError(409, "Le patient a déjà une hospitalisation active.")

    try:
        with transaction.atomic():
            bed = Bed.objects.select_for_update().get(pk=payload.bed_id, is_active=True)
            if bed.status != Bed.AVAILABLE:
                raise HttpError(409, "Lit non disponible.")

            hosp = Hospitalization.objects.create(
                patient=patient,
                bed=bed,
                referring_doctor=doctor,
                admission_date=timezone.now(),
                expected_discharge_date=payload.expected_discharge_date,
                admission_reason=payload.admission_reason,
                notes=payload.notes,
                admitted_by=request.auth,
            )

            bed.status = Bed.OCCUPIED
            bed.save(update_fields=["status", "updated_at"])
    except Bed.DoesNotExist as exc:
        raise HttpError(404, "Lit introuvable.") from exc

    log_audit(
        user=request.auth,
        action_type="CREATE",
        resource_type="Hospitalization",
        resource_id=str(hosp.id),
        new_value={
            "patient_id": str(patient.id),
            "bed_id": str(bed.id),
            "referring_doctor_id": str(doctor.id),
            "admission_date": hosp.admission_date.isoformat(),
        },
    )

    record_movement_event(
        event_type=PatientMovementHistory.ADMISSION,
        patient=patient,
        hospitalization=hosp,
        event_at=hosp.admission_date,
        performed_by=request.auth,
        details={
            **bed_location_lines(bed),
            "doctor": f"Dr. {doctor.last_name} {doctor.first_name}".strip(),
            "admission_reason": hosp.admission_reason,
            "expected_discharge": str(hosp.expected_discharge_date),
        },
    )

    hosp = Hospitalization.objects.select_related(
        "patient", "bed__room__department", "referring_doctor"
    ).get(pk=hosp.id)
    return _hospitalization_out(hosp)


@router.get("/hospitalizations/active/", response=list[HospitalizationOut], auth=jwt_auth)
@require_permission("clinical.view_patient")
def list_active_hospitalizations(request, page: int = 1, page_size: int = 50, search: str = ""):
    offset = (page - 1) * page_size
    qs = (
        Hospitalization.objects.filter(status=Hospitalization.ACTIVE)
        .select_related("patient", "bed__room__department", "referring_doctor")
        .order_by("-admission_date")
    )
    if search.strip():
        qs = filter_by_patient_name(qs, search.strip(), prefix="patient__")
    hospitalizations = qs[offset : offset + page_size]
    return [_hospitalization_out(h) for h in hospitalizations]


class AdmissionDatePatchIn(Schema):
    admission_date: datetime
    reason: str = ""


class PatientMovementOut(Schema):
    id: UUID
    event_type: str
    event_type_label: str
    patient_id: UUID
    patient_name: str
    hospitalization_id: UUID | None
    event_at: datetime
    performed_by_name: str
    details: dict
    notes: str
    document_id: UUID | None
    created_at: datetime


@router.patch("/hospitalizations/{hospitalization_id}/admission-date/", response=HospitalizationOut, auth=jwt_auth)
@require_permission("clinical.edit_admission")
def patch_admission_date(request, hospitalization_id: UUID, payload: AdmissionDatePatchIn):
    try:
        with transaction.atomic():
            hosp = (
                Hospitalization.objects.select_for_update()
                .select_related("patient", "bed__room__department", "referring_doctor")
                .get(pk=hospitalization_id, status=Hospitalization.ACTIVE)
            )
            old_date = hosp.admission_date
            hosp.admission_date = payload.admission_date
            hosp.save(update_fields=["admission_date", "updated_at"])
    except Hospitalization.DoesNotExist as exc:
        raise HttpError(404, "Hospitalisation active introuvable.") from exc

    log_audit(
        user=request.auth,
        action_type="UPDATE",
        resource_type="Hospitalization",
        resource_id=str(hosp.id),
        old_value={"admission_date": old_date.isoformat()},
        new_value={"admission_date": hosp.admission_date.isoformat()},
    )
    record_movement_event(
        event_type=PatientMovementHistory.ADMISSION_CORRECTION,
        patient=hosp.patient,
        hospitalization=hosp,
        event_at=hosp.admission_date,
        performed_by=request.auth,
        details={
            **bed_location_lines(hosp.bed),
            "previous_admission_date": old_date.strftime("%d/%m/%Y à %H:%M"),
            "new_admission_date": hosp.admission_date.strftime("%d/%m/%Y à %H:%M"),
            "cancel_reason": payload.reason,
        },
        notes=payload.reason,
    )
    return _hospitalization_out(hosp)


@router.delete("/hospitalizations/{hospitalization_id}/cancel-admission/", auth=jwt_auth)
@require_permission("clinical.edit_admission")
def cancel_admission(request, hospitalization_id: UUID, reason: str = ""):
    try:
        with transaction.atomic():
            hosp = (
                Hospitalization.objects.select_for_update()
                .select_related("patient", "bed__room__department", "referring_doctor")
                .get(pk=hospitalization_id, status=Hospitalization.ACTIVE)
            )
            if hosp.consultations.exists():
                raise HttpError(409, "Impossible d'annuler : des consultations existent déjà.")
            if hosp.inter_hospital_transfers.filter(status=InterHospitalTransfer.PENDING).exists():
                raise HttpError(409, "Impossible d'annuler : une demande de transfert est en attente.")

            bed = Bed.objects.select_for_update().get(pk=hosp.bed_id)
            patient = hosp.patient
            event_at = timezone.now()
            details = {
                **bed_location_lines(bed),
                "admission_reason": hosp.admission_reason,
                "cancel_reason": reason or "Erreur de saisie",
            }
            hosp.status = Hospitalization.CANCELLED
            hosp.save(update_fields=["status", "updated_at"])
            bed.status = Bed.AVAILABLE
            bed.save(update_fields=["status", "updated_at"])
    except Hospitalization.DoesNotExist as exc:
        raise HttpError(404, "Hospitalisation active introuvable.") from exc

    log_audit(
        user=request.auth,
        action_type="DELETE",
        resource_type="Hospitalization",
        resource_id=str(hosp.id),
        new_value={"status": "CANCELLED", "reason": reason},
    )
    record_movement_event(
        event_type=PatientMovementHistory.ADMISSION_CANCEL,
        patient=patient,
        hospitalization=hosp,
        event_at=event_at,
        performed_by=request.auth,
        details=details,
        notes=reason,
    )
    return {"detail": "Admission annulée."}


@router.get("/patient-movements/", response=list[PatientMovementOut], auth=jwt_auth)
@require_any_permission("clinical.view_movement_history", "clinical.admit_patient")
def list_patient_movements(
    request,
    patient_id: UUID | None = None,
    hospitalization_id: UUID | None = None,
    event_type: str = "",
    page: int = 1,
    page_size: int = 50,
):
    qs = PatientMovementHistory.objects.select_related("patient", "performed_by", "document").order_by(
        "-event_at", "-created_at"
    )
    if patient_id:
        qs = qs.filter(patient_id=patient_id)
    if hospitalization_id:
        qs = qs.filter(hospitalization_id=hospitalization_id)
    if event_type:
        qs = qs.filter(event_type=event_type)
    offset = (page - 1) * page_size
    return [movement_history_out(e) for e in qs[offset : offset + page_size]]
