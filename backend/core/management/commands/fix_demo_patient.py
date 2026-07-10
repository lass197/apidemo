from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from clinical.models import Patient
from core.models import Role, UserRole

User = get_user_model()


class Command(BaseCommand):
    help = "Répare le compte démo patient mobile (alice.moreau → rôle PATIENT)."

    def handle(self, *args, **options):
        user = User.objects.filter(username="alice.moreau").first()
        if not user:
            self.stdout.write(self.style.ERROR("Utilisateur alice.moreau introuvable. Lancez seed_sghl."))
            return

        patient_role = Role.objects.get(code=Role.PATIENT)
        removed = UserRole.objects.filter(user=user).exclude(role=patient_role).delete()[0]
        ur, _ = UserRole.objects.get_or_create(user=user, role=patient_role)
        if not ur.is_active:
            ur.is_active = True
            ur.save(update_fields=["is_active"])

        patient = Patient.objects.filter(user=user).first()
        if patient and not patient.is_active:
            patient.is_active = True
            patient.save(update_fields=["is_active"])

        if not user.email_verified:
            user.email_verified = True
            user.save(update_fields=["email_verified"])

        user.set_password("Patient@2026")
        user.save(update_fields=["password"])

        roles = list(UserRole.objects.filter(user=user).values_list("role__code", flat=True))
        self.stdout.write(
            self.style.SUCCESS(
                f"alice.moreau réparé — rôles: {roles} — mot de passe: Patient@2026 "
                f"({removed} rôle(s) incorrect(s) supprimé(s))."
            )
        )
