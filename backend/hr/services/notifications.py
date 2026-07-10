from hr.models import Appointment

from core.models import Role, User
from core.services.email_service import enqueue_email


def _secretary_emails() -> list[str]:
    return list(
        User.objects.filter(
            is_active=True,
            email__gt="",
            roles__role__code=Role.SECRETARY,
            roles__is_active=True,
        )
        .values_list("email", flat=True)
        .distinct()
    )


def _patient_email(appt) -> str:
    """Email du patient (dossier ou compte utilisateur)."""
    patient = appt.patient
    if patient.email:
        return patient.email.strip()
    if getattr(patient, "user", None) and patient.user and patient.user.email:
        return patient.user.email.strip()
    return ""


def _appointment_details(appt) -> str:
    service = appt.service.name if appt.service_id else "Consultation"
    return (
        f"Patient : {appt.patient}\n"
        f"Médecin : Dr {appt.doctor.get_full_name() or appt.doctor.username}\n"
        f"Prestation : {service}\n"
        f"Date et heure : {appt.scheduled_at:%d/%m/%Y à %H:%M}\n"
        f"Statut : {appt.get_status_display()}\n"
    )


def notify_secretaries_new_appointment(patient_name: str, doctor_name: str, scheduled_at, service_name: str = "") -> None:
    subject = "SGHL — Nouvelle demande de rendez-vous"
    service_line = f"Prestation : {service_name}\n" if service_name else ""
    body = (
        f"Une nouvelle demande de rendez-vous est en attente de validation.\n\n"
        f"Patient : {patient_name}\n"
        f"Médecin : {doctor_name}\n"
        f"{service_line}"
        f"Créneau demandé : {scheduled_at:%d/%m/%Y à %H:%M}\n\n"
        f"Connectez-vous à l'espace staff → Rendez-vous pour traiter la demande."
    )
    for email in _secretary_emails():
        enqueue_email(email, subject, body)


def notify_patient_appointment(patient_email: str, subject: str, body: str) -> None:
    if patient_email:
        enqueue_email(patient_email, subject, body)


def notify_patient_appointment_confirmed(appt) -> None:
    email = _patient_email(appt)
    if not email:
        return
    body = (
        f"Bonjour {appt.patient.first_name},\n\n"
        f"Votre rendez-vous à l'hôpital SGHL est confirmé.\n\n"
        f"{_appointment_details(appt)}"
    )
    if appt.staff_notes:
        body += f"\nNote de l'équipe : {appt.staff_notes}\n"
    body += "\nConnectez-vous à votre espace patient pour plus de détails.\n\n— SGHL"
    notify_patient_appointment(email, "SGHL — Rendez-vous confirmé", body)


def notify_patient_appointment_modified(appt, *, previous_date=None) -> None:
    """RDV modifié (date, médecin, etc.) sans changement de statut vers annulé."""
    email = _patient_email(appt)
    if not email:
        return
    body = (
        f"Bonjour {appt.patient.first_name},\n\n"
        f"Votre rendez-vous à l'hôpital SGHL a été modifié.\n\n"
        f"{_appointment_details(appt)}"
    )
    if previous_date and previous_date != appt.scheduled_at:
        body += f"\nAncienne date : {previous_date:%d/%m/%Y à %H:%M}\n"
    if appt.staff_notes:
        body += f"\nNote : {appt.staff_notes}\n"
    body += "\n— SGHL"
    notify_patient_appointment(email, "SGHL — Rendez-vous modifié", body)


def notify_patient_appointment_postponed(appt) -> None:
    email = _patient_email(appt)
    if not email:
        return
    body = (
        f"Bonjour {appt.patient.first_name},\n\n"
        f"Votre rendez-vous a été reporté. Il est en attente de confirmation définitive.\n\n"
        f"{_appointment_details(appt)}"
    )
    if appt.staff_notes:
        body += f"\nMotif : {appt.staff_notes}\n"
    body += "\n— SGHL"
    notify_patient_appointment(email, "SGHL — Rendez-vous reporté", body)


def notify_patient_appointment_cancelled(appt, *, reason: str = "") -> None:
    email = _patient_email(appt)
    if not email:
        return
    motif = reason or appt.rejection_reason or appt.staff_notes
    body = (
        f"Bonjour {appt.patient.first_name},\n\n"
        f"Votre rendez-vous du {appt.scheduled_at:%d/%m/%Y à %H:%M} "
        f"à l'hôpital SGHL a été annulé.\n"
    )
    if motif:
        body += f"\nMotif : {motif}\n"
    body += "\nVous pouvez prendre un nouveau rendez-vous depuis votre espace patient.\n\n— SGHL"
    notify_patient_appointment(email, "SGHL — Rendez-vous annulé", body)


def notify_patient_appointment_status_change(appt, old_status: str, *, previous_date=None) -> None:
    """Envoie l'email adapté selon le nouveau statut ou une modification."""
    if appt.status == Appointment.CONFIRMED:
        if old_status == Appointment.PENDING:
            notify_patient_appointment_confirmed(appt)
        else:
            notify_patient_appointment_modified(appt, previous_date=previous_date)
    elif appt.status == Appointment.CANCELLED:
        notify_patient_appointment_cancelled(appt)
    elif appt.status == Appointment.PENDING and old_status == Appointment.CONFIRMED:
        notify_patient_appointment_postponed(appt)
    elif appt.status == Appointment.COMPLETED:
        email = _patient_email(appt)
        if email:
            notify_patient_appointment(
                email,
                "SGHL — Rendez-vous terminé",
                (
                    f"Bonjour {appt.patient.first_name},\n\n"
                    f"Votre rendez-vous du {appt.scheduled_at:%d/%m/%Y} est marqué comme terminé.\n"
                    f"Merci de votre confiance.\n\n— SGHL"
                ),
            )
    else:
        notify_patient_appointment_modified(appt, previous_date=previous_date)
