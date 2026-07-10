from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from clinical.models import (
    Bed,
    Consultation,
    Hospitalization,
    ICD10Code,
    Patient,
    Prescription,
    PrescriptionItem,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Ajoute une consultation démo (diagnostic CIM-10) pour alice.moreau / Dr Martin."

    def handle(self, *args, **options):
        user = User.objects.filter(username="alice.moreau").first()
        if not user:
            self.stdout.write(self.style.ERROR("alice.moreau introuvable."))
            return
        patient = Patient.objects.filter(user=user).first()
        if not patient:
            self.stdout.write(self.style.ERROR("Dossier patient alice introuvable."))
            return

        doctor = User.objects.filter(username="dr.martin", is_active=True).first()
        if not doctor:
            self.stdout.write(self.style.ERROR("dr.martin introuvable."))
            return

        icd = ICD10Code.objects.filter(code="I10").first()
        hosp = Hospitalization.objects.filter(patient=patient, status=Hospitalization.ACTIVE).first()
        if not hosp:
            bed = Bed.objects.filter(status=Bed.AVAILABLE, is_active=True).first()
            if not bed:
                self.stdout.write(self.style.ERROR("Aucun lit disponible — lancez seed_sghl."))
                return
            secretary = User.objects.filter(username="sec.dupont").first()
            hosp = Hospitalization.objects.create(
                patient=patient,
                bed=bed,
                referring_doctor=doctor,
                admission_date=timezone.now() - timedelta(days=2),
                expected_discharge_date=(timezone.now() + timedelta(days=5)).date(),
                admission_reason="Suivi cardiologique — hypertension artérielle",
                admitted_by=secretary,
            )
            bed.status = Bed.OCCUPIED
            bed.save(update_fields=["status", "updated_at"])
            self.stdout.write(self.style.SUCCESS("Hospitalisation démo créée pour Alice."))

        consult = (
            Consultation.objects.filter(hospitalization=hosp, doctor=doctor)
            .order_by("-consultation_date")
            .first()
        )
        if not consult:
            consult = Consultation.objects.create(
                hospitalization=hosp,
                doctor=doctor,
                symptoms="Céphalées matinales, tension mesurée à 16/10, fatigue légère.",
                clinical_notes=(
                    "Hypertension artérielle essentielle. Traitement adapté. "
                    "Repos relatif, régime pauvre en sel, contrôle tensionnel hebdomadaire."
                ),
            )
            if icd:
                consult.icd10_codes.add(icd)
            self.stdout.write(self.style.SUCCESS("Consultation démo créée."))

        rx = Prescription.objects.filter(consultation=consult, status=Prescription.VALIDATED).first()
        if not rx:
            rx = Prescription.objects.create(
                consultation=consult,
                doctor=doctor,
                status=Prescription.VALIDATED,
                validated_at=timezone.now(),
                instructions="Prendre les médicaments après le petit-déjeuner.",
            )
            PrescriptionItem.objects.create(
                prescription=rx,
                medicine_name="Amlodipine 5 mg",
                dosage="1 comprimé",
                frequency="1 fois par jour le matin",
                duration_days=90,
                route="oral",
            )
            self.stdout.write(self.style.SUCCESS("Ordonnance démo ajoutée."))

        self.stdout.write(self.style.SUCCESS("Données cliniques QR prêtes pour alice.moreau + Dr Martin."))
