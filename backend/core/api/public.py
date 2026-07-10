from datetime import datetime
from uuid import UUID

from ninja import Router
from ninja.errors import HttpError

from clinical.models import Patient
from core.services.hospital_catalog import HOSPITAL_PROFILE
from core.services.patient_clinical_summary import build_clinical_summary
from core.services.patient_identity import _doctor_payload, _patient_payload, resolve_doctor_for_patient
from core.services.patient_qr import verify_patient_qr_token
from hr.models import HospitalService

router = Router(tags=["Public"])


@router.get("/public/hospital/")
def hospital_profile(request):
    """Informations publiques sur l'établissement (sans authentification)."""
    return HOSPITAL_PROFILE


@router.get("/public/hospital/services/")
def hospital_services(request):
    """Catalogue des prestations réservables en ligne."""
    services = HospitalService.objects.filter(is_active=True).order_by("sort_order", "name")
    if not services.exists():
        return [
            {
                "code": d["code"],
                "name": d["name"],
                "description": next(
                    (h["text"] for h in HOSPITAL_PROFILE.get("highlights", []) if d["code"] in h.get("title", "").upper() or d["code"] == "LAB" and "Lab" in h.get("title", "")),
                    f"Consultations et soins — {d['name']}.",
                ),
                "icon": next((h["icon"] for h in HOSPITAL_PROFILE.get("highlights", []) if d["name"].split()[0] in h.get("title", "")), "🏥"),
                "department_code": d["code"],
                "duration_minutes": 30,
                "price_hint": "Sur devis",
                "opening_hours": d.get("hours", HOSPITAL_PROFILE.get("opening_hours", "")),
                "location_hint": f"{d.get('floor', '')} — {d['name']}".strip(" —"),
                "is_bookable_online": d["code"] != "URG",
            }
            for d in HOSPITAL_PROFILE.get("departments", [])
        ]
    return [
        {
            "id": str(s.id),
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


@router.get("/public/patient-qr/")
def patient_qr_profile(request, p: UUID, t: str, at: str, d: UUID | None = None):
    """
    Dossier patient affiché après scan du QR code (carte PDF).
    Paramètres : p=patient_id, d=doctor_id (optionnel), t=token, at=YYYYMMDD
    """
    try:
        issued = datetime.strptime(at, "%Y%m%d")
    except ValueError as exc:
        raise HttpError(400, "Date QR invalide.") from exc

    if not verify_patient_qr_token(p, d, issued, t):
        raise HttpError(403, "QR code invalide ou expiré. Régénérez la carte patient.")

    try:
        patient = Patient.objects.select_related("user").get(pk=p, is_active=True)
    except Patient.DoesNotExist as exc:
        raise HttpError(404, "Patient introuvable.") from exc

    doctor = resolve_doctor_for_patient(patient, d)
    clinical = build_clinical_summary(patient, doctor)

    return {
        "hospital": {
            "name": HOSPITAL_PROFILE.get("name", "Centre Hospitalier SGHL"),
            "city": HOSPITAL_PROFILE.get("city", "Dolisie"),
            "country": HOSPITAL_PROFILE.get("country", "République du Congo"),
        },
        "patient": _patient_payload(patient),
        "doctor": _doctor_payload(doctor) if doctor else None,
        "clinical_summary": clinical,
        "issued_at": issued.date().isoformat(),
    }
