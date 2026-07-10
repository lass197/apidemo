"""Annuaire médecins : spécialités, agendas et créneaux disponibles."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from datetime import timedelta

from django.utils import timezone

from core.models import Role, User
from hr.models import Appointment, DoctorAvailability, DoctorProfile
from hr.services.doctor_schedules import summarize_agenda_blocks


def compute_doctor_slots(doctor_id: UUID, *, limit: int = 48) -> list[dict]:
    """Créneaux futurs d'un médecin (disponibles ou non)."""
    now = timezone.now()
    avs = DoctorAvailability.objects.filter(
        doctor_id=doctor_id, is_bookable=True, end_at__gte=now
    ).order_by("start_at")

    booked = set(
        Appointment.objects.filter(
            doctor_id=doctor_id,
            status__in=[Appointment.PENDING, Appointment.CONFIRMED],
            scheduled_at__gte=now,
        ).values_list("scheduled_at", flat=True)
    )

    slots: list[dict] = []
    for av in avs:
        cursor = av.start_at
        if cursor < now:
            step = av.slot_duration_minutes
            if step > 0:
                elapsed = int((now - av.start_at).total_seconds() // 60)
                skip = elapsed // step + (1 if elapsed % step else 0)
                cursor = av.start_at + timedelta(minutes=skip * step)
            else:
                cursor = now.replace(second=0, microsecond=0)
        while cursor < av.end_at:
            if cursor >= now:
                slots.append({"scheduled_at": cursor, "available": cursor not in booked})
            cursor += timedelta(minutes=av.slot_duration_minutes)

    return sorted(slots, key=lambda s: s["scheduled_at"])[:limit]


SLOT_REASON_MESSAGES = {
    "available": "Créneau disponible",
    "outside_agenda": "Hors agenda du médecin",
    "slot_taken": "Créneau déjà réservé",
    "doctor_not_accepting": "Le médecin n'accepte plus de rendez-vous",
    "past_slot": "Date passée",
}


def _slot_on_agenda(scheduled_at, av: DoctorAvailability) -> bool:
    if scheduled_at < av.start_at or scheduled_at >= av.end_at:
        return False
    delta_min = int((scheduled_at - av.start_at).total_seconds() // 60)
    if delta_min < 0 or delta_min % av.slot_duration_minutes != 0:
        return False
    slot_end = scheduled_at + timedelta(minutes=av.slot_duration_minutes)
    return slot_end <= av.end_at


def is_doctor_slot_available(
    doctor_id: UUID,
    scheduled_at,
    *,
    exclude_appointment_id: UUID | None = None,
) -> tuple[bool, str]:
    """Vérifie qu'un créneau est dans l'agenda médecin et libre."""
    now = timezone.now()
    if scheduled_at < now:
        return False, "past_slot"

    profile = DoctorProfile.objects.filter(user_id=doctor_id).first()
    if profile and not profile.is_accepting_appointments:
        return False, "doctor_not_accepting"

    avs = DoctorAvailability.objects.filter(
        doctor_id=doctor_id,
        is_bookable=True,
        start_at__lte=scheduled_at,
        end_at__gt=scheduled_at,
    )
    if not any(_slot_on_agenda(scheduled_at, av) for av in avs):
        return False, "outside_agenda"

    qs = Appointment.objects.filter(
        doctor_id=doctor_id,
        scheduled_at=scheduled_at,
        status__in=[Appointment.PENDING, Appointment.CONFIRMED],
    )
    if exclude_appointment_id:
        qs = qs.exclude(pk=exclude_appointment_id)
    if qs.exists():
        return False, "slot_taken"

    return True, "available"


def slot_availability_message(reason: str) -> str:
    return SLOT_REASON_MESSAGES.get(reason, reason)


def _profile_fields(doctor: User) -> dict:
    profile = getattr(doctor, "doctor_profile", None)
    if profile:
        return {
            "specialty": profile.specialty,
            "department_code": profile.department_code,
            "department_name": profile.department_name,
            "bio": profile.bio,
            "is_accepting_appointments": profile.is_accepting_appointments,
        }
    return {
        "specialty": "Médecine générale",
        "department_code": "",
        "department_name": "",
        "bio": "",
        "is_accepting_appointments": True,
    }


def build_doctor_entry(doctor: User, *, slot_limit: int = 48) -> dict:
    fields = _profile_fields(doctor)
    now = timezone.now()
    cutoff = now + timedelta(days=28)
    agenda_qs = DoctorAvailability.objects.filter(
        doctor=doctor, is_bookable=True, end_at__gte=now, start_at__lte=cutoff
    ).order_by("start_at")

    agenda = [
        {
            "id": str(a.id),
            "start_at": a.start_at,
            "end_at": a.end_at,
            "slot_duration_minutes": a.slot_duration_minutes,
        }
        for a in agenda_qs
    ]
    agenda_calendar = summarize_agenda_blocks(agenda)

    slots = compute_doctor_slots(doctor.id, limit=slot_limit)
    available_slots = [s for s in slots if s["available"]]
    next_slot = available_slots[0]["scheduled_at"] if available_slots else None

    return {
        "id": doctor.id,
        "name": doctor.get_full_name() or doctor.username,
        "email": doctor.email or "",
        **fields,
        "agenda": agenda,
        "agenda_calendar": agenda_calendar,
        "available_slots_count": len(available_slots),
        "next_available_at": next_slot,
        "upcoming_slots": available_slots[:12],
    }


def list_doctor_directory(
    *,
    specialty: str | None = None,
    only_available: bool = False,
) -> list[dict]:
    doctors = (
        User.objects.filter(
            roles__role__code=Role.DOCTOR,
            roles__is_active=True,
            is_active=True,
        )
        .distinct()
        .select_related("doctor_profile")
        .order_by("last_name", "first_name")
    )

    needle = (specialty or "").strip().lower()
    results: list[dict] = []
    for doctor in doctors:
        entry = build_doctor_entry(doctor)
        if not entry["is_accepting_appointments"]:
            continue
        if needle and needle not in entry["specialty"].lower():
            continue
        if only_available and entry["available_slots_count"] == 0:
            continue
        results.append(entry)

    results.sort(
        key=lambda d: (
            -d["available_slots_count"],
            d["next_available_at"].isoformat() if d["next_available_at"] else "9999",
            d["name"],
        )
    )
    return results


def list_specialties() -> list[str]:
    qs = DoctorProfile.objects.filter(
        user__is_active=True,
        user__roles__role__code=Role.DOCTOR,
        user__roles__is_active=True,
        is_accepting_appointments=True,
    ).values_list("specialty", flat=True).distinct()
    specialties = sorted({s.strip() for s in qs if s.strip()})
    if not specialties:
        return ["Médecine générale"]
    return specialties
