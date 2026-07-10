from core.models import Permission, Role, RolePermission

DEFAULT_PERMISSIONS = [
    # Core
    ("core.manage_users", "Gérer les utilisateurs", "core"),
    ("core.delete_building", "Supprimer (désactiver) un bâtiment", "core"),
    ("core.view_audit", "Consulter l'audit trail", "core"),
    ("core.view_dashboard", "Consulter le dashboard admin", "core"),
    # Clinical
    ("clinical.admit_patient", "Admettre un patient", "clinical"),
    ("clinical.edit_admission", "Modifier ou annuler une admission", "clinical"),
    ("clinical.view_movement_history", "Consulter l'historique admissions/sorties/transferts", "clinical"),
    ("clinical.view_patient", "Consulter dossier patient", "clinical"),
    ("clinical.consult", "Effectuer une consultation", "clinical"),
    ("clinical.prescribe", "Prescrire des médicaments", "clinical"),
    ("clinical.transfer", "Transférer un patient", "clinical"),
    ("clinical.validate_transfer", "Valider les demandes de transfert", "clinical"),
    ("clinical.view_partner_hospitals", "Consulter les hôpitaux partenaires", "clinical"),
    ("clinical.nursing_care", "Saisir soins infirmiers", "clinical"),
    # Laboratory
    ("lab.order", "Commander un examen", "laboratory"),
    ("lab.enter_results", "Saisir résultats", "laboratory"),
    ("lab.validate_results", "Valider résultats (biologiste)", "laboratory"),
    ("lab.publish_results", "Publier résultats", "laboratory"),
    # Billing
    ("billing.create_invoice", "Créer une facture", "billing"),
    ("billing.view_finance", "Consulter finances", "billing"),
    ("billing.adjust", "Ajuster écritures comptables", "billing"),
    # Pharmacy
    ("pharmacy.manage_stock", "Gérer stocks pharmacie", "pharmacy"),
    ("pharmacy.dispense", "Dispenser médicaments", "pharmacy"),
    # HR
    ("hr.manage_schedule", "Gérer plannings", "hr"),
    ("hr.review_appointments", "Valider et gérer les rendez-vous", "hr"),
    # Documents
    ("documents.upload", "Uploader documents", "documents"),
    ("documents.view", "Consulter documents", "documents"),
]

ROLE_PERMISSIONS = {
    Role.ADMIN: [p[0] for p in DEFAULT_PERMISSIONS],
    Role.SECRETARY: [
        "core.view_dashboard",
        "clinical.admit_patient",
        "clinical.edit_admission",
        "clinical.view_movement_history",
        "clinical.view_patient",
        "clinical.validate_transfer",
        "billing.create_invoice",
        "billing.view_finance",
        "hr.review_appointments",
        "documents.upload",
        "documents.view",
        "hr.manage_schedule",
    ],
    Role.ACCOUNTANT: [
        "core.view_dashboard",
        "billing.view_finance",
        "billing.adjust",
        "documents.view",
    ],
    Role.DOCTOR: [
        "core.view_dashboard",
        "clinical.view_patient",
        "clinical.consult",
        "clinical.prescribe",
        "clinical.transfer",
        "clinical.view_partner_hospitals",
        "lab.order",
        "documents.upload",
        "documents.view",
        "hr.manage_schedule",
    ],
    Role.NURSE: [
        "core.view_dashboard",
        "clinical.view_patient",
        "clinical.nursing_care",
        "documents.view",
    ],
    Role.BIOLOGIST: [
        "core.view_dashboard",
        "clinical.view_patient",
        "lab.enter_results",
        "lab.validate_results",
        "lab.publish_results",
        "documents.view",
    ],
    Role.PHARMACIST: [
        "core.view_dashboard",
        "pharmacy.manage_stock",
        "pharmacy.dispense",
        "clinical.view_patient",
    ],
    Role.PATIENT: [
        "clinical.view_patient",
        "documents.view",
    ],
}


def seed_roles_and_permissions() -> None:
    """Initialise rôles et permissions par défaut."""
    roles_data = [
        (Role.ADMIN, "Administrateur", "Accès complet au système"),
        (Role.SECRETARY, "Secrétaire", "Admissions, facturation, documents"),
        (Role.ACCOUNTANT, "Comptable", "Suivi financier, journal et ajustements comptables"),
        (Role.DOCTOR, "Médecin", "Consultations, prescriptions, dossier médical"),
        (Role.NURSE, "Infirmier(ère)", "Soins et constantes vitales"),
        (Role.BIOLOGIST, "Biologiste", "Validation résultats laboratoire"),
        (Role.PHARMACIST, "Pharmacien", "Gestion stocks et dispensation"),
        (Role.PATIENT, "Patient", "Application mobile patient"),
    ]

    for code, name, desc in roles_data:
        Role.objects.get_or_create(
            code=code,
            defaults={"name": name, "description": desc},
        )

    for codename, name, module in DEFAULT_PERMISSIONS:
        Permission.objects.get_or_create(
            codename=codename,
            defaults={"name": name, "module": module},
        )

    for role_code, perm_codes in ROLE_PERMISSIONS.items():
        role = Role.objects.get(code=role_code)
        for codename in perm_codes:
            perm = Permission.objects.get(codename=codename)
            RolePermission.objects.update_or_create(
                role=role, permission=perm, defaults={"role": role, "permission": perm}
            )
        # Retirer permissions obsolètes
        RolePermission.objects.filter(role=role).exclude(
            permission__codename__in=perm_codes
        ).delete()
