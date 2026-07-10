import io
from datetime import datetime

import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from core.services.patient_identity import build_patient_identity_payload, patient_identity_qr_text

CURRENCY_LABEL = "FCFA"
CURRENCY_FULL = "Franc CFA (XAF — zone CEMAC)"


def _format_fcfa(amount) -> str:
    try:
        n = float(amount)
    except (TypeError, ValueError):
        return f"— {CURRENCY_LABEL}"
    formatted = f"{n:,.0f}".replace(",", " ")
    return f"{formatted} {CURRENCY_LABEL}"


def generate_lab_report_pdf(*, patient_name: str, test_name: str, result_data: dict, validated_by: str) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "SGHL — Compte-rendu de laboratoire")

    c.setFont("Helvetica", 11)
    y = height - 90
    c.drawString(50, y, f"Patient : {patient_name}")
    y -= 20
    c.drawString(50, y, f"Examen : {test_name}")
    y -= 20
    c.drawString(50, y, f"Date : {datetime.now():%d/%m/%Y %H:%M}")
    y -= 30

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Résultats")
    y -= 20
    c.setFont("Helvetica", 11)
    for key, value in result_data.items():
        c.drawString(60, y, f"{key} : {value}")
        y -= 18

    y -= 20
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(50, y, f"Validé par : {validated_by}")
    c.drawString(50, y - 15, "Signature électronique SGHL")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()


def _make_qr_image(qr_text: str, *, box_size: int = 6) -> ImageReader:
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=box_size, border=2)
    qr.add_data(qr_text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


def generate_patient_identity_pdf(*, patient, doctor=None) -> bytes:
    """Carte patient SGHL : identifiants visibles + QR contenant toutes les infos (dont médecin)."""
    payload = build_patient_identity_payload(patient, doctor)
    qr_text = patient_identity_qr_text(patient, doctor)
    pinfo = payload["patient"]
    dinfo = payload.get("doctor")

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 48, "Centre Hospitalier SGHL — Dolisie (RC)")

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 72, "Carte d'identité patient")

    c.setFont("Helvetica", 10)
    c.drawString(50, height - 88, f"Émise le {datetime.now():%d/%m/%Y à %H:%M}")

    y = height - 120
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Identifiants patient")
    y -= 22
    c.setFont("Helvetica", 11)

    visible_lines = [
        ("N° dossier", pinfo["id"]),
        ("Nom complet", pinfo["full_name"]),
        ("Date de naissance", datetime.fromisoformat(pinfo["date_of_birth"]).strftime("%d/%m/%Y")),
        ("Sexe", pinfo["gender_label"]),
        ("Téléphone", pinfo["phone"] or "—"),
        ("Email", pinfo["email"] or "—"),
        ("Compte", pinfo["account_username"] or "—"),
        ("N° sécurité sociale", pinfo["social_security_number"] or "—"),
        ("Adresse", pinfo["address"] or "—"),
        ("Contact urgence", pinfo["emergency_contact"] or "—"),
        ("Tél. urgence", pinfo["emergency_phone"] or "—"),
    ]
    for label, value in visible_lines:
        c.drawString(55, y, f"{label} :")
        c.drawString(185, y, str(value)[:70])
        y -= 17

    y -= 8
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Médecin référent")
    y -= 20
    c.setFont("Helvetica", 11)
    if dinfo:
        doctor_lines = [
            ("Nom", dinfo["full_name"]),
            ("Spécialité", dinfo["specialty"]),
            ("Service", dinfo["department_name"] or dinfo["department_code"] or "—"),
            ("Email", dinfo["email"] or "—"),
            ("Identifiant", dinfo["username"]),
        ]
        for label, value in doctor_lines:
            c.drawString(55, y, f"{label} :")
            c.drawString(185, y, str(value)[:70])
            y -= 17
    else:
        c.drawString(55, y, "Aucun médecin sélectionné.")
        y -= 17

    clinical = payload.get("clinical_summary") or {}
    y -= 6
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Synthèse médicale (médecin)")
    y -= 20
    c.setFont("Helvetica", 10)
    diagnoses = clinical.get("primary_diagnoses") or []
    if diagnoses:
        c.drawString(55, y, "Diagnostics (CIM-10) :")
        y -= 14
        for d in diagnoses[:4]:
            c.drawString(65, y, f"• {d['code']} — {d['label'][:55]}")
            y -= 13
    else:
        c.drawString(55, y, "Diagnostics : — (scan QR pour le détail)")
        y -= 14

    consultations = clinical.get("consultations") or []
    if consultations:
        latest = consultations[0]
        c.drawString(55, y, f"Dernière consultation ({latest.get('date', '')[:10]}) :")
        y -= 14
        if latest.get("symptoms"):
            c.drawString(65, y, f"Symptômes : {str(latest['symptoms'])[:60]}")
            y -= 13
        if latest.get("clinical_notes"):
            c.drawString(65, y, f"Notes médecin : {str(latest['clinical_notes'])[:60]}")
            y -= 13
    elif clinical.get("hospitalization"):
        h = clinical["hospitalization"]
        c.drawString(55, y, f"Motif admission : {str(h.get('admission_reason', '—'))[:60]}")
        y -= 14

    qr_size = 200
    qr_x = width - qr_size - 55
    qr_y = max(y - qr_size - 20, 120)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(qr_x, qr_y + qr_size + 8, "QR — dossier & diagnostics")
    c.drawImage(_make_qr_image(qr_text), qr_x, qr_y, width=qr_size, height=qr_size)

    c.setFont("Helvetica-Oblique", 8)
    c.drawString(50, 72, "Scannez le QR : identité, diagnostics CIM-10, notes du médecin et ordonnances.")
    c.drawString(50, 58, payload.get("verify_url", "")[:95])

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()


def generate_clinical_movement_pdf(
    *,
    title: str,
    patient_name: str,
    event_label: str,
    event_at,
    lines: list[tuple[str, str]],
    signed_by: str,
    signer_role: str = "Secrétaire médical(e)",
) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "SGHL — Document officiel")

    c.setFont("Helvetica-Bold", 13)
    c.drawString(50, height - 75, title)

    c.setFont("Helvetica", 11)
    y = height - 110
    c.drawString(50, y, f"Patient : {patient_name}")
    y -= 20
    c.drawString(50, y, f"Événement : {event_label}")
    y -= 20
    if hasattr(event_at, "strftime"):
        c.drawString(50, y, f"Date et heure : {event_at:%d/%m/%Y à %H:%M}")
    else:
        c.drawString(50, y, f"Date et heure : {event_at}")
    y -= 30

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Détails")
    y -= 22
    c.setFont("Helvetica", 11)
    for label, value in lines:
        if not value:
            continue
        c.drawString(60, y, f"{label} : {value}")
        y -= 18
        if y < 120:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 11)

    y = max(y - 30, 100)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Signature électronique")
    c.setFont("Helvetica", 10)
    c.drawString(50, y - 18, f"Signé par : {signed_by}")
    c.drawString(50, y - 33, f"Qualité : {signer_role}")
    c.drawString(50, y - 48, f"Émis le : {datetime.now():%d/%m/%Y à %H:%M}")
    c.line(50, y - 58, 280, y - 58)
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, y - 72, "Document certifié par le système SGHL — valeur probante interne")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()


def generate_invoice_pdf(*, invoice_number: str, patient_name: str, lines: list, total: str) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 45, "Centre Hospitalier SGHL — Dolisie (RC)")

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 68, f"Facture {invoice_number}")

    c.setFont("Helvetica", 10)
    c.drawString(50, height - 85, CURRENCY_FULL)

    c.setFont("Helvetica", 11)
    c.drawString(50, height - 108, f"Patient : {patient_name}")
    c.drawString(50, height - 126, f"Date d'émission : {datetime.now():%d/%m/%Y}")

    y = height - 160
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Description")
    c.drawString(400, y, f"Montant ({CURRENCY_LABEL})")
    y -= 22
    c.setFont("Helvetica", 10)
    for line in lines:
        c.drawString(50, y, line["description"][:55])
        c.drawRightString(545, y, _format_fcfa(line["total"]))
        y -= 16

    y -= 10
    c.line(50, y, 545, y)
    y -= 22
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Total part patient")
    c.drawRightString(545, y, _format_fcfa(total))

    y -= 28
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, y, "Paiements acceptés : Airtel Money · MTN Mobile Money (Congo-Brazzaville)")
    c.drawString(50, y - 14, "Document émis par le système SGHL — montants en francs CFA (FCFA)")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()
