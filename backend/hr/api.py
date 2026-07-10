from datetime import datetime, timedelta
from uuid import UUID

from django.utils import timezone
from ninja import Router, Schema
from ninja.errors import HttpError

from clinical.models import Patient
from core.auth import jwt_auth
from core.models import Role, User
from core.permissions import require_permission
from core.services.audit import log_audit
from hr.models import Appointment, ChatMessage, DoctorAvailability, DoctorProfile, HospitalService, MedicationReminder, Shift
from hr.services.doctor_directory import (
    build_doctor_entry,
    compute_doctor_slots,
    is_doctor_slot_available,
    list_doctor_directory,
    list_specialties,
    slot_availability_message,
)
from hr.services.notifications import (
    notify_patient_appointment,
    notify_patient_appointment_cancelled,
    notify_patient_appointment_confirmed,
    notify_patient_appointment_postponed,
    notify_patient_appointment_status_change,
    notify_secretaries_new_appointment,
)

router = Router(tags=["RH & Patient"])


class ShiftIn(Schema):
    staff_id: UUID
    department_code: str
    start_at: datetime
    end_at: datetime
    notes: str = ""


class ShiftOut(Schema):
    id: UUID
    staff_name: str
    department_code: str
    start_at: datetime
    end_at: datetime


class AvailabilityIn(Schema):
    start_at: datetime
    end_at: datetime
    slot_duration_minutes: int = 30


class AvailabilityOut(Schema):
    id: UUID
    doctor_id: UUID
    start_at: datetime
    end_at: datetime
    slot_duration_minutes: int


class AppointmentIn(Schema):
    patient_id: UUID
    doctor_id: UUID
    scheduled_at: datetime
    reason: str = ""
    service_id: UUID | None = None
    status: str | None = None


class AppointmentUpdateIn(Schema):
    patient_id: UUID | None = None
    doctor_id: UUID | None = None
    service_id: UUID | None = None
    scheduled_at: datetime | None = None
    reason: str | None = None
    staff_notes: str | None = None
    rejection_reason: str | None = None
    status: str | None = None
    duration_minutes: int | None = None


class AppointmentReviewIn(Schema):
    action: str
    scheduled_at: datetime | None = None
    staff_notes: str = ""
    rejection_reason: str = ""


class AppointmentOut(Schema):
    id: UUID
    patient_id: UUID
    patient_name: str
    patient_email: str = ""
    patient_phone: str = ""
    doctor_id: UUID
    doctor_name: str
    service_id: UUID | None = None
    service_name: str = ""
    scheduled_at: datetime
    status: str
    reason: str = ""
    staff_notes: str = ""
    rejection_reason: str = ""
    reviewed_at: datetime | None = None
    doctor_slot_available: bool = True
    doctor_slot_message: str = ""


class DoctorPatientBriefOut(Schema):
    id: UUID
    name: str
    email: str
    phone: str
    next_appointment_at: datetime | None = None


class HospitalServiceOut(Schema):
    id: UUID
    code: str
    name: str
    description: str
    icon: str
    department_code: str = ""
    duration_minutes: int
    price_hint: str
    opening_hours: str = ""
    location_hint: str = ""
    is_bookable_online: bool


class SlotOut(Schema):
    scheduled_at: datetime
    available: bool


class ChatIn(Schema):
    patient_id: UUID
    content: str


class ChatOut(Schema):
    id: UUID
    sender_id: UUID
    content: str
    created_at: datetime


class ReminderIn(Schema):
    medicine_name: str
    dosage: str
    schedule_time: str


class DoctorOut(Schema):
    id: UUID
    name: str
    email: str
    specialty: str = "Médecine générale"
    department_name: str = ""


class DoctorAgendaBlockOut(Schema):
    id: str
    start_at: datetime
    end_at: datetime
    slot_duration_minutes: int


class DoctorSlotOut(Schema):
    scheduled_at: datetime
    available: bool


class DoctorAgendaDayOut(Schema):
    date: str
    weekday: str
    weekday_label: str
    sessions: list[dict]


class DoctorDirectoryOut(Schema):
    id: UUID
    name: str
    email: str
    specialty: str
    department_code: str
    department_name: str
    bio: str
    is_accepting_appointments: bool
    agenda: list[DoctorAgendaBlockOut]
    agenda_calendar: list[DoctorAgendaDayOut] = []
    available_slots_count: int
    next_available_at: datetime | None = None
    upcoming_slots: list[DoctorSlotOut]


class ReminderOut(Schema):
    id: UUID
    medicine_name: str
    dosage: str
    schedule_time: str
    is_active: bool


def _patient_contact(patient: Patient) -> tuple[str, str]:
    email = (patient.email or "").strip()
    if not email and patient.user_id:
        user = getattr(patient, "user", None)
        if user and user.email:
            email = user.email.strip()
    return email, (patient.phone or "").strip()


def _appointment_out(a: Appointment) -> dict:
    email, phone = _patient_contact(a.patient)
    ok, reason = is_doctor_slot_available(
        a.doctor_id,
        a.scheduled_at,
        exclude_appointment_id=a.id if a.status in (Appointment.PENDING, Appointment.CONFIRMED) else None,
    )
    return {
        "id": a.id,
        "patient_id": a.patient_id,
        "patient_name": str(a.patient),
        "patient_email": email,
        "patient_phone": phone,
        "doctor_id": a.doctor_id,
        "doctor_name": str(a.doctor),
        "service_id": a.service_id,
        "service_name": a.service.name if a.service_id else "",
        "scheduled_at": a.scheduled_at,
        "status": a.status,
        "reason": a.reason or "",
        "staff_notes": a.staff_notes or "",
        "rejection_reason": a.rejection_reason or "",
        "reviewed_at": a.reviewed_at,
        "doctor_slot_available": ok,
        "doctor_slot_message": slot_availability_message(reason),
    }


def _assert_doctor_slot_available(
    doctor_id: UUID,
    scheduled_at: datetime,
    *,
    exclude_appointment_id: UUID | None = None,
) -> None:
    ok, reason = is_doctor_slot_available(
        doctor_id,
        scheduled_at,
        exclude_appointment_id=exclude_appointment_id,
    )
    if not ok:
        raise HttpError(409, slot_availability_message(reason))


def _user_is_doctor(user: User) -> bool:
    return user.roles.filter(is_active=True, role__code=Role.DOCTOR).exists()


def _appointment_slot_taken(doctor_id: UUID, scheduled_at: datetime, exclude_id: UUID | None = None) -> bool:
    qs = Appointment.objects.filter(
        doctor_id=doctor_id,
        scheduled_at=scheduled_at,
        status__in=[Appointment.PENDING, Appointment.CONFIRMED],
    )
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    return qs.exists()


def _assert_appointment_access(request, patient_id: UUID) -> None:
    profile = getattr(request.auth, "patient_profile", None)
    if profile and profile.id == patient_id:
        return
    if request.auth.has_perm_code("hr.review_appointments") or request.auth.has_perm_code("hr.manage_schedule"):
        return
    if request.auth.has_perm_code("clinical.consult"):
        return
    raise HttpError(403, "Accès refusé.")


@router.get("/services/", response=list[HospitalServiceOut], auth=jwt_auth)
def list_hospital_services(request):
    services = HospitalService.objects.filter(is_active=True, is_bookable_online=True).order_by("sort_order", "name")
    return [
        {
            "id": s.id,
            "code": s.code,
            "name": s.name,
            "description": s.description,
            "icon": s.icon,
            "department_code": s.department_code,
            "duration_minutes": s.duration_minutes,
            "price_hint": s.price_hint,
            "opening_hours": s.opening_hours,
            "location_hint": s.location_hint,
            "is_bookable_online": s.is_bookable_online,
        }
        for s in services
    ]


@router.get("/services/manage/", response=list[HospitalServiceOut], auth=jwt_auth)
@require_permission("hr.review_appointments")
def list_services_for_staff(request):
    services = HospitalService.objects.filter(is_active=True).order_by("sort_order", "name")
    return [
        {
            "id": s.id,
            "code": s.code,
            "name": s.name,
            "description": s.description,
            "icon": s.icon,
            "department_code": s.department_code,
            "duration_minutes": s.duration_minutes,
            "price_hint": s.price_hint,
            "opening_hours": s.opening_hours,
            "location_hint": s.location_hint,
            "is_bookable_online": s.is_bookable_online,
        }
        for s in services
    ]


@router.get("/doctors/", response=list[DoctorOut], auth=jwt_auth)
def list_doctors(request):
    doctors = (
        User.objects.filter(
            roles__role__code="DOCTOR", roles__is_active=True, is_active=True
        )
        .distinct()
        .select_related("doctor_profile")
    )
    return [
        {
            "id": d.id,
            "name": str(d),
            "email": d.email or "",
            "specialty": getattr(d.doctor_profile, "specialty", None) or "Médecine générale",
            "department_name": getattr(d.doctor_profile, "department_name", None) or "",
        }
        for d in doctors
    ]


@router.get("/doctors/directory/", response=list[DoctorDirectoryOut], auth=jwt_auth)
def doctors_directory(request, specialty: str | None = None, only_available: bool = False):
    """Annuaire : médecins, spécialités, plages d'agenda et créneaux libres."""
    return list_doctor_directory(specialty=specialty, only_available=only_available)


@router.get("/doctors/specialties/", response=list[str], auth=jwt_auth)
def doctors_specialties(request):
    return list_specialties()


@router.get("/doctors/{doctor_id}/", response=DoctorDirectoryOut, auth=jwt_auth)
def get_doctor_detail(request, doctor_id: UUID):
    doctor = (
        User.objects.select_related("doctor_profile")
        .filter(
            pk=doctor_id,
            is_active=True,
            roles__role__code=Role.DOCTOR,
            roles__is_active=True,
        )
        .distinct()
        .first()
    )
    if not doctor:
        raise HttpError(404, "Médecin introuvable.")
    return build_doctor_entry(doctor, slot_limit=48)


@router.post("/shifts/", response=ShiftOut, auth=jwt_auth)
@require_permission("hr.manage_schedule")
def create_shift(request, payload: ShiftIn):
    try:
        staff = User.objects.get(pk=payload.staff_id, is_active=True)
    except User.DoesNotExist as exc:
        raise HttpError(404, "Personnel introuvable.") from exc

    shift = Shift.objects.create(
        staff=staff,
        department_code=payload.department_code,
        start_at=payload.start_at,
        end_at=payload.end_at,
        notes=payload.notes,
    )
    return {
        "id": shift.id,
        "staff_name": str(staff),
        "department_code": shift.department_code,
        "start_at": shift.start_at,
        "end_at": shift.end_at,
    }


@router.get("/shifts/", response=list[ShiftOut], auth=jwt_auth)
@require_permission("hr.manage_schedule")
def list_shifts(request):
    shifts = Shift.objects.select_related("staff").filter(end_at__gte=timezone.now()).order_by("start_at")
    return [
        {
            "id": s.id,
            "staff_name": str(s.staff),
            "department_code": s.department_code,
            "start_at": s.start_at,
            "end_at": s.end_at,
        }
        for s in shifts[:50]
    ]


@router.post("/availabilities/", response=AvailabilityOut, auth=jwt_auth)
@require_permission("clinical.consult")
def create_availability(request, payload: AvailabilityIn):
    av = DoctorAvailability.objects.create(
        doctor=request.auth,
        start_at=payload.start_at,
        end_at=payload.end_at,
        slot_duration_minutes=payload.slot_duration_minutes,
    )
    return {
        "id": av.id,
        "doctor_id": request.auth.id,
        "start_at": av.start_at,
        "end_at": av.end_at,
        "slot_duration_minutes": av.slot_duration_minutes,
    }


@router.get("/availabilities/{doctor_id}/slots/", response=list[SlotOut], auth=jwt_auth)
def list_available_slots(request, doctor_id: UUID):
    return compute_doctor_slots(doctor_id, limit=120)


@router.get("/availabilities/{doctor_id}/", response=list[AvailabilityOut], auth=jwt_auth)
def list_availabilities(request, doctor_id: UUID):
    avs = DoctorAvailability.objects.filter(
        doctor_id=doctor_id, is_bookable=True, end_at__gte=timezone.now()
    ).order_by("start_at")
    return [
        {
            "id": a.id,
            "doctor_id": a.doctor_id,
            "start_at": a.start_at,
            "end_at": a.end_at,
            "slot_duration_minutes": a.slot_duration_minutes,
        }
        for a in avs
    ]


@router.post("/appointments/", response=AppointmentOut, auth=jwt_auth)
def book_appointment(request, payload: AppointmentIn):
    try:
        patient = Patient.objects.get(pk=payload.patient_id, is_active=True)
        doctor = User.objects.get(pk=payload.doctor_id, is_active=True)
    except (Patient.DoesNotExist, User.DoesNotExist) as exc:
        raise HttpError(404, "Patient ou médecin introuvable.") from exc

    profile = getattr(request.auth, "patient_profile", None)
    is_staff = request.auth.has_perm_code("hr.review_appointments")
    if profile and profile.id != patient.id and not is_staff:
        raise HttpError(403, "Vous ne pouvez réserver que pour votre propre profil.")

    service = None
    duration = 30
    if payload.service_id:
        try:
            service = HospitalService.objects.get(pk=payload.service_id, is_active=True)
            if not is_staff and not service.is_bookable_online:
                raise HospitalService.DoesNotExist
            duration = service.duration_minutes
        except HospitalService.DoesNotExist as exc:
            raise HttpError(404, "Prestation introuvable.") from exc

    if _appointment_slot_taken(doctor.id, payload.scheduled_at):
        raise HttpError(409, "Créneau déjà réservé.")

    initial_status = Appointment.PENDING
    if is_staff and payload.status in (Appointment.PENDING, Appointment.CONFIRMED):
        initial_status = payload.status

    if initial_status == Appointment.CONFIRMED:
        _assert_doctor_slot_available(doctor.id, payload.scheduled_at)

    appt = Appointment.objects.create(
        patient=patient,
        doctor=doctor,
        service=service,
        scheduled_at=payload.scheduled_at,
        duration_minutes=duration,
        reason=payload.reason,
        status=initial_status,
    )
    log_audit(
        user=request.auth,
        action_type="CREATE",
        resource_type="Appointment",
        resource_id=str(appt.id),
        new_value={"status": Appointment.PENDING},
    )
    notify_secretaries_new_appointment(
        str(patient),
        str(doctor),
        appt.scheduled_at,
        service.name if service else "",
    )
    if patient.email:
        notify_patient_appointment(
            patient.email,
            "SGHL — Demande de rendez-vous reçue",
            f"Votre demande de rendez-vous avec Dr {doctor.last_name} le {appt.scheduled_at:%d/%m/%Y à %H:%M} "
            f"est en cours de validation par notre secrétariat.",
        )
    return _appointment_out(appt)


@router.get("/appointments/pending/", response=list[AppointmentOut], auth=jwt_auth)
@require_permission("hr.review_appointments")
def list_pending_appointments(request):
    appts = (
        Appointment.objects.filter(status=Appointment.PENDING)
        .select_related("patient", "patient__user", "doctor", "service")
        .order_by("scheduled_at")
    )
    return [_appointment_out(a) for a in appts]


@router.get("/appointments/mine/", response=list[AppointmentOut], auth=jwt_auth)
@require_permission("clinical.consult")
def list_my_appointments(request, status: str | None = None, upcoming: bool = False):
    """RDV du médecin connecté (avec email patient)."""
    if not _user_is_doctor(request.auth):
        raise HttpError(403, "Réservé aux médecins.")
    qs = Appointment.objects.filter(doctor_id=request.auth.id).select_related(
        "patient", "patient__user", "doctor", "service"
    )
    if status:
        qs = qs.filter(status=status.upper())
    if upcoming:
        qs = qs.filter(
            status__in=[Appointment.PENDING, Appointment.CONFIRMED],
            scheduled_at__gte=timezone.now(),
        )
    appts = qs.order_by("scheduled_at" if upcoming else "-scheduled_at")[:200]
    return [_appointment_out(a) for a in appts]


@router.get("/appointments/mine/patients/", response=list[DoctorPatientBriefOut], auth=jwt_auth)
@require_permission("clinical.consult")
def list_my_appointment_patients(request):
    """Patients ayant un RDV avec le médecin connecté."""
    if not _user_is_doctor(request.auth):
        raise HttpError(403, "Réservé aux médecins.")
    appts = (
        Appointment.objects.filter(doctor_id=request.auth.id)
        .select_related("patient", "patient__user")
        .order_by("scheduled_at")
    )
    by_patient: dict = {}
    for appt in appts:
        pid = appt.patient_id
        email, phone = _patient_contact(appt.patient)
        entry = by_patient.get(pid)
        if not entry:
            by_patient[pid] = {
                "id": appt.patient_id,
                "name": str(appt.patient),
                "email": email,
                "phone": phone,
                "next_appointment_at": appt.scheduled_at
                if appt.status in (Appointment.PENDING, Appointment.CONFIRMED)
                and appt.scheduled_at >= timezone.now()
                else None,
            }
        elif (
            appt.status in (Appointment.PENDING, Appointment.CONFIRMED)
            and appt.scheduled_at >= timezone.now()
        ):
            current = entry["next_appointment_at"]
            if current is None or appt.scheduled_at < current:
                entry["next_appointment_at"] = appt.scheduled_at
    return sorted(by_patient.values(), key=lambda x: x["name"])


@router.get("/appointments/", response=list[AppointmentOut], auth=jwt_auth)
@require_permission("hr.review_appointments")
def list_all_appointments(request, status: str | None = None):
    qs = Appointment.objects.select_related("patient", "patient__user", "doctor", "service").order_by("-scheduled_at")
    if status:
        qs = qs.filter(status=status.upper())
    return [_appointment_out(a) for a in qs[:100]]


@router.get("/appointments/{appointment_id}/", response=AppointmentOut, auth=jwt_auth)
@require_permission("hr.review_appointments")
def get_appointment(request, appointment_id: UUID):
    try:
        appt = Appointment.objects.select_related("patient", "doctor", "service").get(pk=appointment_id)
    except Appointment.DoesNotExist as exc:
        raise HttpError(404, "Rendez-vous introuvable.") from exc
    return _appointment_out(appt)


@router.patch("/appointments/{appointment_id}/", response=AppointmentOut, auth=jwt_auth)
@require_permission("hr.review_appointments")
def update_appointment(request, appointment_id: UUID, payload: AppointmentUpdateIn):
    try:
        appt = Appointment.objects.select_related("patient", "doctor", "service").get(pk=appointment_id)
    except Appointment.DoesNotExist as exc:
        raise HttpError(404, "Rendez-vous introuvable.") from exc

    if appt.status == Appointment.COMPLETED:
        raise HttpError(409, "Un rendez-vous terminé ne peut plus être modifié.")

    old_status = appt.status
    old_scheduled_at = appt.scheduled_at

    data = payload.dict()
    changes = {}

    if data.get("patient_id"):
        try:
            appt.patient = Patient.objects.get(pk=data["patient_id"], is_active=True)
            changes["patient_id"] = str(data["patient_id"])
        except Patient.DoesNotExist as exc:
            raise HttpError(404, "Patient introuvable.") from exc
    if data.get("doctor_id"):
        try:
            appt.doctor = User.objects.get(pk=data["doctor_id"], is_active=True)
            changes["doctor_id"] = str(data["doctor_id"])
        except User.DoesNotExist as exc:
            raise HttpError(404, "Médecin introuvable.") from exc
    if data.get("service_id"):
        try:
            appt.service = HospitalService.objects.get(pk=data["service_id"], is_active=True)
            appt.duration_minutes = appt.service.duration_minutes
            changes["service_id"] = str(data["service_id"])
        except HospitalService.DoesNotExist as exc:
            raise HttpError(404, "Prestation introuvable.") from exc
    if data.get("scheduled_at"):
        appt.scheduled_at = data["scheduled_at"]
        changes["scheduled_at"] = data["scheduled_at"].isoformat()
    if data.get("reason") is not None:
        appt.reason = data["reason"]
        changes["reason"] = data["reason"]
    if data.get("staff_notes") is not None:
        appt.staff_notes = data["staff_notes"]
        changes["staff_notes"] = data["staff_notes"]
    if data.get("rejection_reason") is not None:
        appt.rejection_reason = data["rejection_reason"]
    if data.get("duration_minutes"):
        appt.duration_minutes = data["duration_minutes"]
    if data.get("status"):
        valid = {Appointment.PENDING, Appointment.CONFIRMED, Appointment.CANCELLED, Appointment.COMPLETED}
        if data["status"] not in valid:
            raise HttpError(400, f"Statut invalide. Valeurs : {', '.join(sorted(valid))}")
        appt.status = data["status"]
        changes["status"] = data["status"]

    doctor_id = appt.doctor_id
    scheduled_at = appt.scheduled_at
    if _appointment_slot_taken(doctor_id, scheduled_at, exclude_id=appt.id):
        raise HttpError(409, "Créneau déjà réservé pour ce médecin.")

    if appt.status == Appointment.CONFIRMED:
        _assert_doctor_slot_available(
            doctor_id,
            scheduled_at,
            exclude_appointment_id=appt.id,
        )

    appt.reviewed_at = timezone.now()
    appt.reviewed_by = request.auth
    appt.save()

    log_audit(
        user=request.auth,
        action_type="UPDATE",
        resource_type="Appointment",
        resource_id=str(appt.id),
        new_value=changes or data,
    )

    appt = Appointment.objects.select_related("patient", "doctor", "service").get(pk=appt.id)
    if changes:
        notify_patient_appointment_status_change(
            appt,
            old_status,
            previous_date=old_scheduled_at if old_scheduled_at != appt.scheduled_at else None,
        )

    return _appointment_out(appt)


@router.delete("/appointments/{appointment_id}/", auth=jwt_auth)
@require_permission("hr.review_appointments")
def cancel_appointment(request, appointment_id: UUID):
    try:
        appt = Appointment.objects.select_related("patient").get(pk=appointment_id)
    except Appointment.DoesNotExist as exc:
        raise HttpError(404, "Rendez-vous introuvable.") from exc
    if appt.status == Appointment.COMPLETED:
        raise HttpError(409, "Impossible d'annuler un rendez-vous terminé.")
    appt.status = Appointment.CANCELLED
    appt.reviewed_at = timezone.now()
    appt.reviewed_by = request.auth
    appt.save(update_fields=["status", "reviewed_at", "reviewed_by", "updated_at"])
    log_audit(
        user=request.auth,
        action_type="DELETE",
        resource_type="Appointment",
        resource_id=str(appt.id),
        new_value={"status": Appointment.CANCELLED},
    )
    notify_patient_appointment_cancelled(appt)
    return {"detail": "Rendez-vous annulé."}


def _patient_appointments_queryset(patient_id: UUID):
    return (
        Appointment.objects.filter(patient_id=patient_id)
        .select_related("patient", "doctor", "service")
        .order_by("scheduled_at")
    )


@router.get("/appointments/patient/me/", response=list[AppointmentOut], auth=jwt_auth)
def list_my_patient_appointments(request):
    """Tous les RDV du patient connecté (réservés en ligne ou par le secrétariat)."""
    profile = getattr(request.auth, "patient_profile", None)
    if not profile:
        raise HttpError(404, "Profil patient non lié à ce compte.")
    appts = _patient_appointments_queryset(profile.id)
    return [_appointment_out(a) for a in appts]


@router.get("/appointments/patient/{patient_id}/", response=list[AppointmentOut], auth=jwt_auth)
def list_patient_appointments(request, patient_id: UUID):
    _assert_appointment_access(request, patient_id)
    appts = _patient_appointments_queryset(patient_id)
    return [_appointment_out(a) for a in appts]


@router.patch("/appointments/{appointment_id}/review/", response=AppointmentOut, auth=jwt_auth)
@require_permission("hr.review_appointments")
def review_appointment(request, appointment_id: UUID, payload: AppointmentReviewIn):
    try:
        appt = Appointment.objects.select_related("patient", "doctor", "service").get(pk=appointment_id)
    except Appointment.DoesNotExist as exc:
        raise HttpError(404, "Rendez-vous introuvable.") from exc

    if appt.status not in (Appointment.PENDING, Appointment.CONFIRMED):
        raise HttpError(409, "Ce rendez-vous ne peut plus être modifié.")

    action = payload.action.lower().strip()
    old_status = appt.status

    if action == "confirm":
        target_at = payload.scheduled_at or appt.scheduled_at
        _assert_doctor_slot_available(
            appt.doctor_id,
            target_at,
            exclude_appointment_id=appt.id,
        )
        appt.status = Appointment.CONFIRMED
        if payload.scheduled_at:
            appt.scheduled_at = payload.scheduled_at
        appt.staff_notes = payload.staff_notes.strip()
        appt.confirmation_sent = True
    elif action == "postpone":
        if not payload.scheduled_at:
            raise HttpError(400, "Nouvelle date requise pour un report.")
        appt.scheduled_at = payload.scheduled_at
        appt.status = Appointment.PENDING
        appt.staff_notes = payload.staff_notes.strip()
    elif action == "reject":
        appt.status = Appointment.CANCELLED
        appt.rejection_reason = payload.rejection_reason.strip() or payload.staff_notes.strip()
    else:
        raise HttpError(400, "Action invalide (confirm, postpone, reject).")

    appt.reviewed_at = timezone.now()
    appt.reviewed_by = request.auth
    appt.save()

    log_audit(
        user=request.auth,
        action_type="UPDATE",
        resource_type="Appointment",
        resource_id=str(appt.id),
        new_value={"action": action, "status": appt.status},
    )

    if action == "confirm":
        notify_patient_appointment_confirmed(appt)
    elif action == "postpone":
        notify_patient_appointment_postponed(appt)
    elif action == "reject":
        notify_patient_appointment_cancelled(appt, reason=appt.rejection_reason)
    else:
        notify_patient_appointment_status_change(appt, old_status)

    return _appointment_out(appt)


@router.post("/chat/", response=ChatOut, auth=jwt_auth)
def send_chat_message(request, payload: ChatIn):
    try:
        patient = Patient.objects.get(pk=payload.patient_id, is_active=True)
    except Patient.DoesNotExist as exc:
        raise HttpError(404, "Patient introuvable.") from exc

    if hasattr(patient, "user") and patient.user_id and patient.user_id != request.auth.id:
        if not request.auth.has_perm_code("clinical.consult"):
            raise HttpError(403, "Accès refusé.")

    doctor = User.objects.filter(roles__role__code="DOCTOR", roles__is_active=True).first()
    if not doctor:
        raise HttpError(404, "Médecin non disponible.")

    msg = ChatMessage.objects.create(
        patient=patient,
        doctor=doctor,
        sender=request.auth,
        content=payload.content,
    )
    return {
        "id": msg.id,
        "sender_id": msg.sender_id,
        "content": msg.content,
        "created_at": msg.created_at,
    }


@router.get("/chat/{patient_id}/", response=list[ChatOut], auth=jwt_auth)
def list_chat_messages(request, patient_id: UUID):
    msgs = ChatMessage.objects.filter(patient_id=patient_id).order_by("created_at")[:100]
    return [
        {"id": m.id, "sender_id": m.sender_id, "content": m.content, "created_at": m.created_at}
        for m in msgs
    ]


@router.get("/reminders/patient/{patient_id}/", response=list[ReminderOut], auth=jwt_auth)
def list_reminders(request, patient_id: UUID):
    profile = getattr(request.auth, "patient_profile", None)
    if profile and profile.id != patient_id and not request.auth.has_perm_code("clinical.consult"):
        raise HttpError(403, "Accès refusé.")
    reminders = MedicationReminder.objects.filter(patient_id=patient_id, is_active=True)
    return [
        {
            "id": r.id,
            "medicine_name": r.medicine_name,
            "dosage": r.dosage,
            "schedule_time": r.schedule_time.strftime("%H:%M"),
            "is_active": r.is_active,
        }
        for r in reminders
    ]


@router.post("/reminders/{patient_id}/", auth=jwt_auth)
def create_reminder(request, patient_id: UUID, payload: ReminderIn):
    from datetime import time as time_cls

    try:
        patient = Patient.objects.get(pk=patient_id, is_active=True)
    except Patient.DoesNotExist as exc:
        raise HttpError(404, "Patient introuvable.") from exc

    h, m, *_ = payload.schedule_time.split(":")
    reminder = MedicationReminder.objects.create(
        patient=patient,
        medicine_name=payload.medicine_name,
        dosage=payload.dosage,
        schedule_time=time_cls(int(h), int(m)),
    )
    return {"id": str(reminder.id), "detail": "Rappel créé."}
