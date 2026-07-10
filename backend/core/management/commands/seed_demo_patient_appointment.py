from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from clinical.models import Patient
from core.models import Role, UserRole
from django.contrib.auth import get_user_model
from hr.models import Appointment

User = get_user_model()


class Command(BaseCommand):
    help = "Crée un RDV démo secrétariat pour alice.moreau (visible dans l'app patient)."

    def handle(self, *args, **options):
        user = User.objects.filter(username="alice.moreau").first()
        if not user:
            self.stdout.write(self.style.ERROR("Utilisateur alice.moreau introuvable."))
            return

        patient = Patient.objects.filter(user=user).first()
        if not patient:
            patient = getattr(user, "patient_profile", None)
        if not patient:
            self.stdout.write(self.style.ERROR("Dossier patient non lié à alice.moreau."))
            return

        doctor = User.objects.filter(username="dr.martin", is_active=True).first()
        if not doctor:
            self.stdout.write(self.style.ERROR("Médecin dr.martin introuvable."))
            return

        slot = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=4)
        appt, created = Appointment.objects.update_or_create(
            patient=patient,
            doctor=doctor,
            scheduled_at=slot,
            defaults={
                "reason": "Consultation de suivi — planifiée par le secrétariat",
                "status": Appointment.CONFIRMED,
                "duration_minutes": 30,
                "staff_notes": "RDV démo créé par le secrétariat",
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"RDV {'créé' if created else 'mis à jour'} pour {patient} le {slot:%d/%m/%Y %H:%M} "
                f"avec Dr {doctor.last_name} (statut: {appt.status})."
            )
        )
