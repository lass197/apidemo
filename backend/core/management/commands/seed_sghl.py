from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from billing.models import InsuranceProvider, PatientInsurance, ServicePrice
from clinical.models import (
    Bed,
    Building,
    Consultation,
    Department,
    Hospitalization,
    ICD10Code,
    PartnerHospital,
    Patient,
    Prescription,
    PrescriptionItem,
    Room,
)
from core.models import Role, UserRole
from core.services.rbac import seed_roles_and_permissions
from laboratory.models import LabTestType
from pharmacy.models import Medicine, StockLot

User = get_user_model()

DOCTORS = [
    ("dr.martin", "martin@sghl.local", "Jean", "Martin", "Cardiologie", "CARDIO", "Cardiologie", "Spécialiste des maladies cardiovasculaires et de l'hypertension."),
    ("dr.diallo", "diallo@sghl.local", "Amadou", "Diallo", "Médecine générale", "URG", "Urgences", "Consultations de premier recours, suivi et orientation."),
    ("dr.nguema", "nguema@sghl.local", "Clarisse", "Nguema", "Pédiatrie", "PEDIA", "Pédiatrie", "Suivi de l'enfant, vaccinations et croissance."),
    ("dr.kouassi", "kouassi@sghl.local", "Marie", "Kouassi", "Gynécologie", "GYN", "Gynécologie-obstétrique", "Consultations femmes, grossesse et maternité."),
    ("dr.mbemba", "mbemba@sghl.local", "Patrick", "Mbemba", "Dermatologie", "DERM", "Dermatologie", "Peau, allergies cutanées et dermatoses tropicales."),
    ("dr.ondo", "ondo@sghl.local", "Sylvie", "Ondo", "Neurologie", "NEURO", "Neurologie", "Céphalées, épilepsie et pathologies du système nerveux."),
    ("dr.sakho", "sakho@sghl.local", "Ibrahim", "Sakho", "Ophtalmologie", "OPHT", "Ophtalmologie", "Consultations vue, glaucome et chirurgie oculaire."),
    ("dr.tchicaya", "tchicaya@sghl.local", "Grace", "Tchicaya", "ORL", "ORL", "ORL", "Oreilles, nez, gorge et équilibre."),
    ("dr.makaya", "makaya@sghl.local", "Emmanuel", "Makaya", "Chirurgie générale", "CHIR", "Chirurgie", "Interventions digestives et traumatologie."),
    ("dr.biyogo", "biyogo@sghl.local", "Sandrine", "Biyogo", "Pneumologie", "PNEUM", "Pneumologie", "Asthme, BPCO et infections respiratoires."),
    ("dr.ndongo", "ndongo@sghl.local", "Luc", "Ndongo", "Urologie", "URO", "Urologie", "Appareil urinaire et andrologie."),
    ("dr.ilunga", "ilunga@sghl.local", "Cédric", "Ilunga", "Psychiatrie", "PSY", "Psychiatrie", "Anxiété, dépression et suivi psychologique."),
    ("dr.faye", "faye@sghl.local", "Aïssatou", "Faye", "Rhumatologie", "RHUM", "Rhumatologie", "Douleurs articulaires, arthrose et maladies auto-immunes."),
    ("dr.sow", "sow@sghl.local", "Ousmane", "Sow", "Endocrinologie", "ENDO", "Endocrinologie", "Diabète, thyroïde et troubles hormonaux."),
    ("dr.kabila", "kabila@sghl.local", "Henriette", "Kabila", "Radiologie", "RAD", "Imagerie médicale", "Échographie, radiographie et interprétation d'images."),
    ("dr.loubaki", "loubaki@sghl.local", "Fabien", "Loubaki", "Anesthésie-réanimation", "REA", "Réanimation", "Prise en charge peri-opératoire et soins intensifs."),
]

USERS = [
    ("admin", "admin@sghl.local", "Admin", "SGHL", Role.ADMIN, "Admin@SGHL2026", True, True),
    *[
        (username, email, fn, ln, Role.DOCTOR, "Medecin@2026", True, False)
        for username, email, fn, ln, *_ in DOCTORS
    ],
    ("sec.dupont", "sec@sghl.local", "Marie", "Dupont", Role.SECRETARY, "Secretaire@2026", True, False),
    ("comptable.moussou", "compta@sghl.local", "Jean-Baptiste", "Moussou", Role.ACCOUNTANT, "Comptable@2026", True, False),
    ("inf.bernard", "inf@sghl.local", "Sophie", "Bernard", Role.NURSE, "Infirmier@2026", True, False),
    ("bio.leroy", "bio@sghl.local", "Pierre", "Leroy", Role.BIOLOGIST, "Biologiste@2026", True, False),
    ("pharm.vidal", "pharm@sghl.local", "Anne", "Vidal", Role.PHARMACIST, "Pharmacien@2026", True, False),
]


class Command(BaseCommand):
    help = "Initialise rôles, permissions et données de démonstration SGHL."

    def handle(self, *args, **options):
        seed_roles_and_permissions()
        self.stdout.write(self.style.SUCCESS("Rôles et permissions créés."))

        for username, email, fn, ln, role_code, password, is_staff, is_super in USERS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "first_name": fn,
                    "last_name": ln,
                    "is_staff": is_staff,
                    "is_superuser": is_super,
                },
            )
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(self.style.SUCCESS(f"  {username} / {password}"))
            if not user.email_verified:
                user.email_verified = True
                user.save(update_fields=["email_verified"])
            UserRole.objects.update_or_create(
                user=user,
                role=Role.objects.get(code=role_code),
                defaults={"is_active": True},
            )

        # CIM-10
        icd10_data = [
            ("I10", "Hypertension essentielle", "Circulatoire"),
            ("E11", "Diabète sucré de type 2", "Endocrinien"),
            ("J18", "Pneumopathie", "Respiratoire"),
            ("I21", "Infarctus aigu du myocarde", "Circulatoire"),
        ]
        for code, desc, cat in icd10_data:
            ICD10Code.objects.get_or_create(code=code, defaults={"description": desc, "category": cat})

        # Infrastructure lits
        building, _ = Building.objects.get_or_create(
            code="A",
            defaults={
                "name": "Bâtiment Principal SGHL",
                "address": "35, Rue Mali — Quartier Gaïa, Dolisie (La Terre Jaune), République du Congo",
            },
        )
        for dept_code, dept_name in [
            ("CARDIO", "Cardiologie"),
            ("PEDIA", "Pédiatrie"),
            ("URG", "Urgences"),
            ("LAB", "Laboratoire"),
        ]:
            dept, _ = Department.objects.get_or_create(
                building=building, code=dept_code, defaults={"name": dept_name}
            )
            if dept_code == "LAB":
                rooms = [("101", 1, "Salle prélèvements"), ("102", 1, "Plateau technique")]
            elif dept_code == "PEDIA":
                rooms = [("301", 3, "Consultations pédiatrie"), ("302", 3, "Vaccination & suivi")]
            else:
                rooms = [("101", 1, "")]
            for room_num, floor, _ in rooms:
                room, _ = Room.objects.get_or_create(department=dept, number=room_num, defaults={"floor": floor})
                for label in ("A", "B", "C") if dept_code != "LAB" else ("1", "2"):
                    Bed.objects.get_or_create(room=room, label=label, defaults={"status": Bed.AVAILABLE})

        # Examens labo — catalogue LIS
        tests = [
            ("NFS", "Numération formule sanguine", "blood", Decimal("16400"), 4),
            ("GLY", "Glycémie à jeun", "blood", Decimal("9800"), 2),
            ("HBA1C", "Hémoglobine glyquée (HbA1c)", "blood", Decimal("18500"), 24),
            ("CRP", "Protéine C-réactive", "blood", Decimal("13100"), 4),
            ("VS", "Vitesse de sédimentation", "blood", Decimal("7200"), 4),
            ("IONO", "Ionogramme sanguin", "blood", Decimal("19650"), 4),
            ("UREE", "Urée sanguine", "blood", Decimal("8900"), 4),
            ("CREAT", "Créatininémie", "blood", Decimal("8900"), 4),
            ("ALAT", "Transaminases ALAT", "blood", Decimal("11200"), 4),
            ("ASAT", "Transaminases ASAT", "blood", Decimal("11200"), 4),
            ("BILI", "Bilirubine totale", "blood", Decimal("10500"), 4),
            ("TSH", "TSH — fonction thyroïdienne", "blood", Decimal("15800"), 24),
            ("HIV", "Sérologie VIH", "blood", Decimal("22000"), 24),
            ("HBS", "Ag HBs — hépatite B", "blood", Decimal("19800"), 24),
            ("ECBU", "Examen cytobactériologique urines", "urine", Decimal("14200"), 48),
            ("PARA", "Recherche paludisme (Goutte épaisse)", "blood", Decimal("8500"), 2),
            ("GSA", "Gazométrie artérielle", "blood", Decimal("24500"), 1),
            ("TPINR", "TP / INR — coagulation", "blood", Decimal("13400"), 4),
            ("FERR", "Ferritine", "blood", Decimal("17600"), 24),
            ("PSA", "Antigène prostatique (PSA)", "blood", Decimal("21000"), 24),
        ]
        for code, name, sample, price, turnaround in tests:
            LabTestType.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "sample_type": sample,
                    "price": price,
                    "turnaround_hours": turnaround,
                    "is_active": True,
                },
            )

        # Tarifs
        prices = [
            ("NUITEE", "Nuitée hospitalière", ServicePrice.NIGHT, Decimal("98250")),
            ("CONSULT", "Consultation spécialisée", ServicePrice.ACT, Decimal("52400")),
            ("PANSEMENT", "Pansement", ServicePrice.CONSUMABLE, Decimal("7860")),
            ("LAB-ACT", "Acte laboratoire", ServicePrice.ACT, Decimal("15000")),
        ]
        for code, label, stype, price in prices:
            ServicePrice.objects.get_or_create(
                code=code, defaults={"label": label, "service_type": stype, "unit_price": price}
            )

        # Assurance
        InsuranceProvider.objects.get_or_create(
            code="MUT-01",
            defaults={"name": "Mutuelle Santé Plus", "coverage_rate": Decimal("80.00")},
        )

        # Pharmacie — catalogue hospitalier élargi
        from datetime import date, timedelta

        pharmacy_catalog = [
            ("PARA500", "Paracétamol 500 mg", "comprimé", "boîte", "2300", 30, 180, "A1"),
            ("PARA1000", "Paracétamol 1 g", "comprimé", "boîte", "3100", 25, 120, "A1"),
            ("AMOX1G", "Amoxicilline 1 g", "comprimé", "boîte", "5240", 15, 85, "A2"),
            ("AMOX500", "Amoxicilline 500 mg", "gélule", "boîte", "4180", 20, 95, "A2"),
            ("CIPRO500", "Ciprofloxacine 500 mg", "comprimé", "boîte", "6800", 10, 45, "A3"),
            ("AZITH500", "Azithromycine 500 mg", "comprimé", "boîte", "7500", 12, 60, "A3"),
            ("METF850", "Metformine 850 mg", "comprimé", "boîte", "3406", 25, 110, "B1"),
            ("GLIB5", "Glibenclamide 5 mg", "comprimé", "boîte", "2900", 15, 70, "B1"),
            ("INSUL100", "Insuline rapide 100 UI/ml", "injection", "flacon", "12500", 8, 35, "B2-F"),
            ("LOSAR50", "Losartan 50 mg", "comprimé", "boîte", "4500", 20, 88, "B3"),
            ("AMLOD5", "Amlodipine 5 mg", "comprimé", "boîte", "3800", 20, 92, "B3"),
            ("SALBU100", "Salbutamol 100 µg", "aérosol", "flacon", "6200", 12, 48, "C1"),
            ("PRED5", "Prednisolone 5 mg", "comprimé", "boîte", "2700", 15, 75, "C2"),
            ("IBUP400", "Ibuprofène 400 mg", "comprimé", "boîte", "2600", 25, 130, "A1"),
            ("TRAM50", "Tramadol 50 mg", "gélule", "boîte", "5800", 10, 40, "D1-S"),
            ("MORPH10", "Morphine 10 mg", "injection", "ampoule", "8900", 5, 22, "D1-S"),
            ("CEFA1G", "Céfazoline 1 g", "poudre", "flacon", "7200", 10, 55, "A4"),
            ("METOC10", "Métoclopramide 10 mg", "injection", "ampoule", "1800", 20, 100, "C3"),
            ("RINGER", "Ringer lactate 500 ml", "perfusion", "poche", "1500", 30, 200, "E1"),
            ("NACL09", "NaCl 0,9 % 500 ml", "perfusion", "poche", "1200", 40, 250, "E1"),
            ("GLUC05", "Glucose 5 % 500 ml", "perfusion", "poche", "1300", 35, 180, "E2"),
            ("OMEP20", "Oméprazole 20 mg", "gélule", "boîte", "3200", 20, 90, "F1"),
            ("VITD1000", "Vitamine D3 1000 UI", "gélule", "boîte", "2100", 15, 65, "F2"),
            ("FER80", "Sulfate ferreux 80 mg", "comprimé", "boîte", "2400", 18, 80, "F2"),
            ("ATROP1", "Atropine 1 mg", "injection", "ampoule", "950", 10, 45, "D2-U"),
        ]
        today = date.today()
        for idx, (code, name, form, unit, price, threshold, qty, location) in enumerate(pharmacy_catalog):
            med, _ = Medicine.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "form": form,
                    "unit": unit,
                    "unit_price": Decimal(price),
                    "reorder_threshold": threshold,
                    "is_active": True,
                },
            )
            expiry = today + timedelta(days=365 + (idx % 3) * 180)
            lot_no = f"LOT-{code}-2026"
            StockLot.objects.update_or_create(
                medicine=med,
                lot_number=lot_no,
                defaults={
                    "expiry_date": expiry,
                    "quantity": qty if idx % 7 != 0 else max(threshold - 5, 3),
                    "location": location,
                },
            )
            if idx % 5 == 0:
                StockLot.objects.update_or_create(
                    medicine=med,
                    lot_number=f"LOT-{code}-RES",
                    defaults={
                        "expiry_date": today + timedelta(days=60),
                        "quantity": 12,
                        "location": location,
                    },
                )

        # Patient démo + compte mobile
        patient, _ = Patient.objects.get_or_create(
            first_name="Alice",
            last_name="Moreau",
            defaults={
                "date_of_birth": "1978-06-12",
                "gender": "F",
                "phone": "0612345678",
                "email": "alice.moreau@email.local",
                "is_active": True,
            },
        )
        if not patient.is_active:
            patient.is_active = True
            patient.save(update_fields=["is_active"])
        patient_user, created = User.objects.get_or_create(
            username="alice.moreau",
            defaults={
                "email": "alice.moreau@email.local",
                "first_name": "Alice",
                "last_name": "Moreau",
            },
        )
        if created:
            patient_user.set_password("Patient@2026")
            patient_user.save()
            self.stdout.write(self.style.SUCCESS("  alice.moreau / Patient@2026 (mobile)"))
        if not patient_user.email_verified:
            patient_user.email_verified = True
            patient_user.save(update_fields=["email_verified"])
        UserRole.objects.update_or_create(
            user=patient_user,
            role=Role.objects.get(code=Role.PATIENT),
            defaults={"is_active": True},
        )
        if not patient.user_id:
            patient.user = patient_user
            patient.save(update_fields=["user"])

        from datetime import timedelta

        from django.utils import timezone

        from hr.models import Appointment

        demo_doctor = User.objects.filter(username="dr.martin").first()
        if demo_doctor:
            staff_slot = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=4)
            Appointment.objects.update_or_create(
                patient=patient,
                doctor=demo_doctor,
                scheduled_at=staff_slot,
                defaults={
                    "reason": "Consultation de suivi — planifiée par le secrétariat",
                    "status": Appointment.CONFIRMED,
                    "duration_minutes": 30,
                    "staff_notes": "RDV démo créé par le secrétariat",
                },
            )

            demo_secretary = User.objects.filter(username="sec.dupont").first()
            icd_hta = ICD10Code.objects.filter(code="I10").first()
            free_bed = Bed.objects.filter(status=Bed.AVAILABLE, is_active=True).first()
            if free_bed and not Hospitalization.objects.filter(
                patient=patient, status=Hospitalization.ACTIVE
            ).exists():
                hosp = Hospitalization.objects.create(
                    patient=patient,
                    bed=free_bed,
                    referring_doctor=demo_doctor,
                    admission_date=timezone.now() - timedelta(days=2),
                    expected_discharge_date=(timezone.now() + timedelta(days=5)).date(),
                    admission_reason="Suivi cardiologique — hypertension artérielle",
                    admitted_by=demo_secretary,
                )
                free_bed.status = Bed.OCCUPIED
                free_bed.save(update_fields=["status", "updated_at"])
                consult = Consultation.objects.create(
                    hospitalization=hosp,
                    doctor=demo_doctor,
                    symptoms="Céphalées matinales, tension mesurée à 16/10, fatigue légère.",
                    clinical_notes=(
                        "Hypertension artérielle essentielle. Traitement adapté. "
                        "Repos relatif, régime pauvre en sel, contrôle tensionnel hebdomadaire."
                    ),
                )
                if icd_hta:
                    consult.icd10_codes.add(icd_hta)
                rx = Prescription.objects.create(
                    consultation=consult,
                    doctor=demo_doctor,
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

        provider = InsuranceProvider.objects.filter(code="MUT-01").first()
        if provider:
            from django.utils import timezone
            PatientInsurance.objects.get_or_create(
                patient=patient,
                provider=provider,
                defaults={
                    "policy_number": "POL-ALICE-001",
                    "is_primary": True,
                    "valid_from": timezone.now().date(),
                },
            )

        # Profils médecins et disponibilités RDV
        from datetime import timedelta

        from django.utils import timezone

        from hr.models import DoctorAvailability, DoctorProfile
        from hr.services.doctor_schedules import generate_doctor_availabilities

        for username, _email, _fn, _ln, specialty, dept_code, dept_name, bio in DOCTORS:
            doctor = User.objects.filter(username=username).first()
            if not doctor:
                continue
            DoctorProfile.objects.update_or_create(
                user=doctor,
                defaults={
                    "specialty": specialty,
                    "department_code": dept_code,
                    "department_name": dept_name,
                    "bio": bio,
                    "is_accepting_appointments": True,
                },
            )
            blocks = generate_doctor_availabilities(
                doctor,
                specialty=specialty,
                weeks_ahead=8,
                replace_existing=True,
            )

        self.stdout.write(self.style.SUCCESS(f"  {len(DOCTORS)} médecins avec profils et agendas."))

        from hr.models import HospitalService

        services_data = [
            (
                "CARDIO",
                "Cardiologie",
                "Diagnostic et traitement des maladies du cœur et des vaisseaux. Consultations, échocardiographies, stress tests et holters rythmiques. Centre Hospitalier SGHL, Dolisie.",
                "CARDIO",
                "❤️",
                45,
                "39 300 FCFA",
                "Lun - Ven : 8h00 - 18h00",
                "Étage 2 — Service Cardiologie · SGHL, Dolisie (RC)",
            ),
            (
                "NEURO",
                "Neurologie",
                "Prise en charge globale des pathologies neurologiques centrales et périphériques : épilepsie, migraines chroniques, troubles neurodégénératifs.",
                "NEURO",
                "🧠",
                45,
                "45 900 FCFA",
                "Lun - Ven : 9h00 - 17h00",
                "Étage 3 — Consultations neurologie · Dolisie (RC)",
            ),
            (
                "ORTHO",
                "Orthopédie",
                "Traitement chirurgical, arthroscopique et fonctionnel des pathologies de l'appareil locomoteur, des articulations et des traumatismes sportifs.",
                "ORTHO",
                "🦴",
                45,
                "42 600 FCFA",
                "Lun - Ven : 8h00 - 19h00",
                "Étage 1 — Bloc chirurgical · Dolisie (RC)",
            ),
            (
                "PNEUMO",
                "Pneumologie",
                "Diagnostic et suivi des affections respiratoires et pulmonaires : asthme, BPCO, insuffisance respiratoire et apnées du sommeil.",
                "PNEUMO",
                "😷",
                45,
                "39 300 FCFA",
                "Lun - Ven : 9h00 - 17h00",
                "Étage 2 — Service pneumologie · Dolisie (RC)",
            ),
            (
                "PED",
                "Pédiatrie",
                "Consultations pédiatriques sur place au SGHL : suivi de l'enfant, vaccinations, croissance et pathologies courantes. Dr Nguema et équipe pédiatrique.",
                "PEDIA",
                "👶",
                30,
                "16 400 FCFA",
                "Lun - Ven : 8h00 - 20h00 · Sam : 9h00 - 13h00",
                "Étage 3, salles 301-302 — Service Pédiatrie · Bâtiment A, 35 Rue Mali, Dolisie (RC)",
            ),
            (
                "GYNECO",
                "Gynécologie",
                "Suivi gynécologique périodique, obstétrique, échographies morphologiques et accompagnement personnalisé à la maternité.",
                "MAT",
                "♀️",
                45,
                "39 300 FCFA",
                "Lun - Ven : 8h00 - 18h00",
                "Étage 3 — Maternité & gynécologie · Dolisie (RC)",
            ),
            (
                "LABO",
                "Laboratoire d'analyses",
                "Analyses sanguines, urinaires et biologiques sur prescription ou sur rendez-vous. Prélèvements salle 101 — résultats en ligne.",
                "LAB",
                "🔬",
                20,
                "Variable",
                "Lun - Ven : 7h00 - 19h00 · Sam : 8h00 - 12h00",
                "Étage 1 — Salle 101 & plateau 102 · Rue Mali, Dolisie (RC)",
            ),
            (
                "MED-GEN",
                "Médecine générale",
                "Consultation de premier recours, bilan de santé, suivi des pathologies courantes et orientation vers les spécialistes si nécessaire.",
                "CARDIO",
                "🩺",
                30,
                "16 400 FCFA",
                "Lun - Ven : 8h00 - 18h00 · Sam : 9h00 - 13h00",
                "Rez-de-chaussée — Accueil consultations · Dolisie (RC)",
            ),
            (
                "URG",
                "Urgences",
                "Accueil et orientation des urgences non vitales. Urgences vitales : 06 904 89 62 / 06 659 25 64 / 06 828 82 37.",
                "URG",
                "🚑",
                30,
                "Selon acte",
                "24h/24 — 7j/7",
                "Rez-de-chaussée — Urgences · 35 Rue Mali, Dolisie (RC)",
            ),
        ]
        active_codes = []
        for i, (code, name, desc, dept, icon, dur, price, hours, location) in enumerate(services_data):
            active_codes.append(code)
            HospitalService.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "description": desc,
                    "department_code": dept,
                    "icon": icon,
                    "duration_minutes": dur,
                    "price_hint": price,
                    "opening_hours": hours,
                    "location_hint": location,
                    "sort_order": i,
                    "is_active": True,
                    "is_bookable_online": code != "URG",
                },
            )
        HospitalService.objects.exclude(code__in=active_codes).update(is_active=False)

        # Hôpitaux partenaires (transferts inter-établissements)
        partner_hospitals = [
            (
                "CHU de Brazzaville",
                "Brazzaville",
                "Avenue Amilcar Cabral, Brazzaville",
                "+242 06 123 45 01",
                "Urgences, Réanimation, Chirurgie, Cardiologie",
                8,
                120,
            ),
            (
                "Hôpital Général de Pointe-Noire",
                "Pointe-Noire",
                "Quartier Loandjili, Pointe-Noire",
                "+242 06 123 45 02",
                "Médecine générale, Pédiatrie, Maternité",
                5,
                80,
            ),
            (
                "Centre Hospitalier de Dolisie",
                "Dolisie",
                "Route nationale 1, Dolisie",
                "+242 06 123 45 03",
                "Médecine interne, Chirurgie, Laboratoire",
                3,
                45,
            ),
            (
                "Clinique Les Arcades",
                "Brazzaville",
                "Centre-ville, Brazzaville",
                "+242 06 123 45 04",
                "Cardiologie, Neurologie, Imagerie",
                0,
                30,
            ),
            (
                "Hôpital de Ouesso",
                "Ouesso",
                "Avenue de l'Indépendance, Ouesso",
                "+242 06 123 45 05",
                "Urgences, Médecine générale, Pédiatrie",
                4,
                35,
            ),
        ]
        for name, city, address, phone, specialties, avail, total in partner_hospitals:
            PartnerHospital.objects.update_or_create(
                name=name,
                city=city,
                defaults={
                    "address": address,
                    "phone": phone,
                    "specialties": specialties,
                    "available_beds": avail,
                    "total_beds": total,
                    "is_active": True,
                    "accepts_transfers": True,
                },
            )

        # Hospitalisations démo (transferts / admissions actives)
        from datetime import timedelta

        from django.utils import timezone

        demo_doctor = User.objects.filter(username="dr.martin").first()
        demo_secretary = User.objects.filter(username="sec.dupont").first()
        demo_admissions = [
            ("Paul", "Ngoma", "M", "1982-04-20", "Surveillance post-opératoire"),
            ("Fatou", "Sow", "F", "1990-11-08", "Pneumonie aiguë"),
        ]
        available_beds = list(
            Bed.objects.filter(status=Bed.AVAILABLE, is_active=True).order_by("room__department__name")[:3]
        )
        for idx, (fn, ln, gender, dob, reason) in enumerate(demo_admissions):
            demo_patient, _ = Patient.objects.get_or_create(
                first_name=fn,
                last_name=ln,
                defaults={"date_of_birth": dob, "gender": gender},
            )
            if (
                demo_doctor
                and idx < len(available_beds)
                and not Hospitalization.objects.filter(
                    patient=demo_patient, status=Hospitalization.ACTIVE
                ).exists()
            ):
                bed = available_beds[idx]
                Hospitalization.objects.create(
                    patient=demo_patient,
                    bed=bed,
                    referring_doctor=demo_doctor,
                    admission_date=timezone.now(),
                    expected_discharge_date=(timezone.now() + timedelta(days=7)).date(),
                    admission_reason=reason,
                    admitted_by=demo_secretary,
                )
                bed.status = Bed.OCCUPIED
                bed.save(update_fields=["status", "updated_at"])

        self.stdout.write(self.style.SUCCESS("Données de démonstration complètes."))
