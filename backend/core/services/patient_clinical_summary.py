from uuid import UUID

from django.utils import timezone as django_tz

from clinical.models import Consultation, Hospitalization, Prescription
from core.models import User
from hr.models import Appointment


def _format_dt(value) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def build_clinical_summary(patient, doctor: User | None = None) -> dict:
    """Synthèse médicale pour QR / carte patient : diagnostics, notes médecin, ordonnances."""
    hosp_qs = (
        Hospitalization.objects.filter(patient=patient)
        .select_related("bed__room__department", "referring_doctor")
        .order_by("-admission_date")
    )
    active_hosp = hosp_qs.filter(status=Hospitalization.ACTIVE).first()
    last_hosp = hosp_qs.first()

    hospitalization_block = None
    if active_hosp or last_hosp:
        h = active_hosp or last_hosp
        hospitalization_block = {
            "status": h.status,
            "admission_date": _format_dt(h.admission_date),
            "admission_reason": h.admission_reason or "",
            "department": (
                h.bed.room.department.name
                if h.bed_id and h.bed.room_id and h.bed.room.department_id
                else ""
            ),
            "room": h.bed.room.number if h.bed_id and h.bed.room_id else "",
            "bed": h.bed.label if h.bed_id else "",
            "referring_doctor": str(h.referring_doctor) if h.referring_doctor_id else "",
        }

    consult_qs = (
        Consultation.objects.filter(hospitalization__patient=patient)
        .select_related("doctor", "doctor__doctor_profile", "hospitalization")
        .prefetch_related("icd10_codes", "prescriptions__items")
        .order_by("-consultation_date")
    )
    if doctor:
        consult_qs = consult_qs.filter(doctor_id=doctor.id)

    consultations = []
    for c in consult_qs[:8]:
        prescriptions = []
        for rx in c.prescriptions.filter(status=Prescription.VALIDATED).order_by("-validated_at")[:3]:
            prescriptions.append(
                {
                    "id": str(rx.id),
                    "validated_at": _format_dt(rx.validated_at) if rx.validated_at else None,
                    "instructions": rx.instructions or "",
                    "items": [
                        {
                            "medicine_name": item.medicine_name,
                            "dosage": item.dosage,
                            "frequency": item.frequency,
                            "duration_days": item.duration_days,
                            "route": item.route,
                        }
                        for item in rx.items.all()
                    ],
                }
            )
        consultations.append(
            {
                "id": str(c.id),
                "date": _format_dt(c.consultation_date),
                "doctor_name": str(c.doctor),
                "doctor_specialty": getattr(getattr(c.doctor, "doctor_profile", None), "specialty", None)
                or "Médecine générale",
                "symptoms": c.symptoms or "",
                "clinical_notes": c.clinical_notes or "",
                "diagnoses": [
                    {"code": code.code, "label": code.description}
                    for code in c.icd10_codes.all()
                ],
                "prescriptions": prescriptions,
            }
        )

    appt_qs = Appointment.objects.filter(patient=patient).select_related("doctor", "service").order_by("-scheduled_at")
    if doctor:
        appt_qs = appt_qs.filter(doctor_id=doctor.id)
    recent_appointments = [
        {
            "date": _format_dt(a.scheduled_at),
            "status": a.status,
            "reason": a.reason or "",
            "staff_notes": a.staff_notes or "",
            "doctor_name": str(a.doctor),
            "service": a.service.name if a.service_id else "",
        }
        for a in appt_qs.filter(status__in=[Appointment.CONFIRMED, Appointment.COMPLETED])[:5]
    ]

    primary_diagnoses = []
    seen = set()
    for c in consultations:
        for d in c["diagnoses"]:
            key = d["code"]
            if key not in seen:
                seen.add(key)
                primary_diagnoses.append(d)

    return {
        "generated_at": django_tz.now().isoformat(),
        "hospitalization": hospitalization_block,
        "primary_diagnoses": primary_diagnoses,
        "consultations": consultations,
        "recent_appointments": recent_appointments,
        "has_clinical_data": bool(consultations or primary_diagnoses or hospitalization_block),
    }
