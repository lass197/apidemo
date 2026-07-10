from django.utils import timezone

from clinical.models import PatientMovementHistory
from core.models import Role, User
from core.services.pdf import generate_clinical_movement_pdf
from core.services.storage import store_encrypted_file
from documents.models import Document


EVENT_TITLES = {
    PatientMovementHistory.ADMISSION: "Attestation d'admission",
    PatientMovementHistory.ADMISSION_CORRECTION: "Avenant — correction date d'admission",
    PatientMovementHistory.ADMISSION_CANCEL: "Annulation d'admission",
    PatientMovementHistory.DISCHARGE: "Attestation de sortie",
    PatientMovementHistory.INTERNAL_TRANSFER: "Attestation de transfert interne",
    PatientMovementHistory.INTER_TRANSFER: "Attestation de transfert inter-établissement",
}

DOCUMENT_TYPES = {
    PatientMovementHistory.ADMISSION: Document.ADMISSION,
    PatientMovementHistory.ADMISSION_CORRECTION: Document.ADMISSION,
    PatientMovementHistory.ADMISSION_CANCEL: Document.ADMISSION,
    PatientMovementHistory.DISCHARGE: Document.DISCHARGE,
    PatientMovementHistory.INTERNAL_TRANSFER: Document.TRANSFER,
    PatientMovementHistory.INTER_TRANSFER: Document.TRANSFER,
}


def signer_display(user: User) -> tuple[str, str]:
    name = f"{user.last_name} {user.first_name}".strip() or user.username
    role_codes = set(
        user.roles.filter(is_active=True).values_list("role__code", flat=True)
    )
    if Role.SECRETARY in role_codes:
        return name, "Secrétaire médical(e)"
    if Role.DOCTOR in role_codes:
        return name, "Médecin"
    if Role.ADMIN in role_codes:
        return name, "Administrateur"
    return name, "Personnel SGHL"


def _detail_lines(details: dict) -> list[tuple[str, str]]:
    labels = {
        "department": "Service",
        "room": "Chambre",
        "bed": "Lit",
        "doctor": "Médecin référent",
        "admission_reason": "Motif d'admission",
        "expected_discharge": "Sortie prévue",
        "from_department": "Service d'origine",
        "from_room": "Chambre d'origine",
        "from_bed": "Lit d'origine",
        "to_department": "Service de destination",
        "to_room": "Chambre de destination",
        "to_bed": "Lit de destination",
        "partner_hospital": "Établissement destinataire",
        "partner_city": "Ville",
        "reason": "Motif",
        "clinical_summary": "Résumé clinique",
        "previous_admission_date": "Ancienne date d'admission",
        "new_admission_date": "Nouvelle date d'admission",
        "cancel_reason": "Motif d'annulation",
    }
    lines = []
    for key, label in labels.items():
        value = details.get(key)
        if value:
            lines.append((label, str(value)))
    return lines


def issue_movement_pdf(history: PatientMovementHistory) -> Document:
    patient = history.patient
    performer = history.performed_by
    signed_by, signer_role = signer_display(performer) if performer else ("SGHL", "Secrétaire médical(e)")

    event_label = dict(PatientMovementHistory.EVENT_TYPES).get(history.event_type, history.event_type)
    title = EVENT_TITLES.get(history.event_type, "Attestation clinique")
    pdf_bytes = generate_clinical_movement_pdf(
        title=title,
        patient_name=str(patient),
        event_label=event_label,
        event_at=history.event_at,
        lines=_detail_lines(history.details),
        signed_by=signed_by,
        signer_role=signer_role,
    )
    path, file_hash = store_encrypted_file(
        pdf_bytes,
        "clinical_movements",
        f"{history.id}.pdf.enc",
    )
    doc_type = DOCUMENT_TYPES.get(history.event_type, Document.OTHER)
    doc_title = f"{title} — {patient.last_name} {patient.first_name}"
    return Document.objects.create(
        patient=patient,
        hospitalization=history.hospitalization,
        document_type=doc_type,
        title=doc_title,
        file_path=path,
        mime_type="application/pdf",
        file_size=len(pdf_bytes),
        file_hash=file_hash,
        is_encrypted=True,
        uploaded_by=performer,
        signed_at=timezone.now(),
        signed_by=performer,
        signature_hash=file_hash,
    )


def record_movement_event(
    *,
    event_type: str,
    patient,
    hospitalization,
    event_at,
    performed_by: User,
    details: dict | None = None,
    notes: str = "",
    issue_pdf: bool = True,
) -> PatientMovementHistory:
    history = PatientMovementHistory.objects.create(
        event_type=event_type,
        patient=patient,
        hospitalization=hospitalization,
        event_at=event_at,
        performed_by=performed_by,
        details=details or {},
        notes=notes,
    )
    if issue_pdf:
        doc = issue_movement_pdf(history)
        history.document = doc
        history.save(update_fields=["document", "updated_at"])
    return history


def bed_location_lines(bed) -> dict:
    if not bed:
        return {}
    room = bed.room if hasattr(bed, "room") else None
    dept = room.department if room and hasattr(room, "department") else None
    return {
        "department": dept.name if dept else "",
        "room": room.number if room else "",
        "bed": bed.label if bed else "",
    }


def movement_history_out(entry: PatientMovementHistory) -> dict:
    performer = entry.performed_by
    performer_name = ""
    if performer:
        performer_name = f"{performer.last_name} {performer.first_name}".strip() or performer.username
    return {
        "id": entry.id,
        "event_type": entry.event_type,
        "event_type_label": entry.get_event_type_display(),
        "patient_id": entry.patient_id,
        "patient_name": str(entry.patient),
        "hospitalization_id": entry.hospitalization_id,
        "event_at": entry.event_at,
        "performed_by_name": performer_name,
        "details": entry.details,
        "notes": entry.notes,
        "document_id": entry.document_id,
        "created_at": entry.created_at,
    }
