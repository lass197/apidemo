import re
from datetime import date

from django.db import transaction

from clinical.models import Patient
from core.models import Role, User, UserRole
from core.services.audit import log_audit
from core.services.validators import (
    ValidationError,
    validate_date_of_birth,
    validate_email_format,
    validate_gender,
    validate_patient_password,
    validate_person_name,
    validate_phone,
    validate_username,
)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _unique_username(base: str) -> str:
    """Génère un identifiant unique à partir de l'email."""
    slug = re.sub(r"[^a-z0-9._-]", "", base.lower().replace("@", "."))[:40] or "patient"
    candidate = slug
    n = 1
    while User.objects.filter(username=candidate).exists():
        candidate = f"{slug}{n}"
        n += 1
    return candidate


def email_already_used(email: str, *, exclude_user_id=None) -> bool:
    """Vérifie l'unicité email côté User et Patient (comptes vérifiés uniquement)."""
    email = normalize_email(email)
    user_qs = User.objects.filter(email__iexact=email, email_verified=True)
    if exclude_user_id:
        user_qs = user_qs.exclude(pk=exclude_user_id)
    if user_qs.exists():
        return True
    patient_qs = Patient.objects.filter(email__iexact=email, is_active=True)
    if exclude_user_id:
        patient_qs = patient_qs.exclude(user_id=exclude_user_id)
    return patient_qs.filter(user__isnull=False, user__email_verified=True).exists()


def register_patient(
    *,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    date_of_birth: date,
    gender: str,
    phone: str = "",
    username: str | None = None,
) -> tuple[User, Patient, bool]:
    """
    Inscription patient self-service.
    Retourne (user, patient, created_new_patient).
    Lie un dossier patient existant (sans compte) si l'email correspond.
    """
    email = validate_email_format(normalize_email(email), required=True)

    first_name = validate_person_name(first_name, field="Prénom")
    last_name = validate_person_name(last_name, field="Nom")
    gender = validate_gender(gender)
    date_of_birth = validate_date_of_birth(date_of_birth)
    phone = validate_phone(phone)

    if email_already_used(email):
        raise ValueError("Un compte existe déjà avec cet email.")

    existing_user = User.objects.filter(email__iexact=email, is_active=True).first()
    if existing_user:
        if existing_user.email_verified:
            raise ValueError("Un compte existe déjà avec cet email.")
        if not existing_user.roles.filter(role__code=Role.PATIENT, is_active=True).exists():
            raise ValueError("Un compte existe déjà avec cet email.")
        try:
            validate_patient_password(password)
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc

        existing_patient = Patient.objects.filter(user=existing_user, is_active=True).first()
        if not existing_patient:
            existing_patient = Patient.objects.filter(email__iexact=email, is_active=True).first()

        with transaction.atomic():
            existing_user.set_password(password)
            existing_user.first_name = first_name
            existing_user.last_name = last_name
            existing_user.phone = phone
            existing_user.save(update_fields=["password", "first_name", "last_name", "phone"])

            if existing_patient:
                existing_patient.first_name = first_name
                existing_patient.last_name = last_name
                existing_patient.date_of_birth = date_of_birth
                existing_patient.gender = gender
                if phone:
                    existing_patient.phone = phone
                existing_patient.user = existing_user
                existing_patient.save(
                    update_fields=[
                        "user", "first_name", "last_name", "date_of_birth",
                        "gender", "phone", "updated_at",
                    ]
                )
            else:
                existing_patient = Patient.objects.create(
                    user=existing_user,
                    first_name=first_name,
                    last_name=last_name,
                    date_of_birth=date_of_birth,
                    gender=gender,
                    phone=phone,
                    email=email,
                )

        return existing_user, existing_patient, False

    existing_patient = Patient.objects.filter(email__iexact=email, is_active=True).first()
    if existing_patient and existing_patient.user_id:
        raise ValueError("Un compte patient existe déjà pour cet email.")

    if username and str(username).strip():
        username = validate_username(username)
        if User.objects.filter(username=username).exists():
            raise ValueError("Cet identifiant est déjà pris.")
    else:
        username = _unique_username(email.split("@")[0])

    try:
        validate_patient_password(password)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc

    role = Role.objects.get(code=Role.PATIENT, is_active=True)

    with transaction.atomic():
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            is_staff=False,
            email_verified=False,
        )
        UserRole.objects.create(user=user, role=role)

        created_new = False
        if existing_patient:
            patient = existing_patient
            patient.user = user
            patient.first_name = first_name
            patient.last_name = last_name
            patient.date_of_birth = date_of_birth
            patient.gender = gender
            if phone:
                patient.phone = phone
            patient.save(
                update_fields=[
                    "user",
                    "first_name",
                    "last_name",
                    "date_of_birth",
                    "gender",
                    "phone",
                    "updated_at",
                ]
            )
        else:
            patient = Patient.objects.create(
                user=user,
                first_name=first_name,
                last_name=last_name,
                date_of_birth=date_of_birth,
                gender=gender,
                phone=phone,
                email=email,
            )
            created_new = True

        log_audit(
            user=user,
            action_type="CREATE",
            resource_type="PatientRegistration",
            resource_id=str(patient.id),
            new_value={"email": email, "linked_existing": not created_new},
        )

    return user, patient, created_new
