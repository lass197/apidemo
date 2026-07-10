from datetime import datetime, timezone
from uuid import UUID

from django.utils import timezone as django_tz

from clinical.models import Patient
from core.models import Role, User
from core.services.patient_clinical_summary import build_clinical_summary
from core.services.patient_qr import build_patient_qr_url
from hr.models import Appointment, DoctorProfile


GENDER_LABELS = {"M": "Masculin", "F": "Féminin", "O": "Autre"}


def _doctor_payload(doctor: User) -> dict:
    profile = getattr(doctor, "doctor_profile", None)
    return {
        "id": str(doctor.id),
        "username": doctor.username,
        "first_name": doctor.first_name,
        "last_name": doctor.last_name,
        "full_name": str(doctor),
        "email": doctor.email or "",
        "specialty": getattr(profile, "specialty", None) or "Médecine générale",
        "department_code": getattr(profile, "department_code", None) or "",
        "department_name": getattr(profile, "department_name", None) or "",
    }


def _patient_payload(patient: Patient) -> dict:
    user = getattr(patient, "user", None)
    return {
        "id": str(patient.id),
        "first_name": patient.first_name,
        "last_name": patient.last_name,
        "full_name": str(patient),
        "date_of_birth": patient.date_of_birth.isoformat(),
        "gender": patient.gender,
        "gender_label": GENDER_LABELS.get(patient.gender, patient.gender),
        "phone": patient.phone or "",
        "email": (patient.email or (user.email if user else "") or "").strip(),
        "address": patient.address or "",
        "social_security_number": patient.social_security_number or "",
        "emergency_contact": patient.emergency_contact or "",
        "emergency_phone": patient.emergency_phone or "",
        "account_username": user.username if user else "",
    }


def resolve_doctor_for_patient(patient: Patient, doctor_id: UUID | None = None) -> User | None:
    if doctor_id:
        return (
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

    upcoming = (
        Appointment.objects.filter(
            patient_id=patient.id,
            status__in=[Appointment.PENDING, Appointment.CONFIRMED],
            scheduled_at__gte=django_tz.now(),
        )
        .select_related("doctor", "doctor__doctor_profile")
        .order_by("scheduled_at")
        .first()
    )
    if upcoming:
        return upcoming.doctor

    last_appt = (
        Appointment.objects.filter(patient_id=patient.id)
        .select_related("doctor", "doctor__doctor_profile")
        .order_by("-scheduled_at")
        .first()
    )
    return last_appt.doctor if last_appt else None


def build_patient_identity_payload(patient: Patient, doctor: User | None = None) -> dict:
    issued_at = datetime.now(timezone.utc)
    clinical = build_clinical_summary(patient, doctor)
    return {
        "type": "SGHL_PATIENT_IDENTITY",
        "version": 2,
        "issued_at": issued_at.isoformat(),
        "verify_url": build_patient_qr_url(patient.id, doctor.id if doctor else None, issued_at),
        "hospital": {
            "name": "Centre Hospitalier SGHL",
            "city": "Dolisie",
            "country": "République du Congo",
        },
        "patient": _patient_payload(patient),
        "doctor": _doctor_payload(doctor) if doctor else None,
        "clinical_summary": clinical,
    }


def patient_identity_qr_text(patient: Patient, doctor: User | None = None) -> str:
    issued_at = datetime.now(timezone.utc)
    return build_patient_qr_url(patient.id, doctor.id if doctor else None, issued_at)
