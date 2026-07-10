"""Validateurs métier SGHL — cohérence backend / frontend."""

import re
from datetime import date

from django.utils import timezone

# Lettres unicode (accents FR), espaces, apostrophe, tiret — pas de chiffres
PERSON_NAME_RE = re.compile(r"^[a-zA-ZÀ-ÿ\s'\-]+$")
PHONE_RE = re.compile(r"^\+?[0-9\s.\-()]{8,20}$")
EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
USERNAME_RE = re.compile(r"^[a-z0-9._\-]{3,40}$")
BUILDING_CODE_RE = re.compile(r"^[A-Z0-9\-_]{2,20}$")


class ValidationError(ValueError):
    """Erreur de validation métier (→ HTTP 400)."""


def validate_patient_password(password: str) -> None:
    """Règles mot de passe patient — plus simples que AUTH_PASSWORD_VALIDATORS Django."""
    if not password or len(password) < 10:
        raise ValidationError("Mot de passe : minimum 10 caractères.")
    if password.isdigit():
        raise ValidationError("Le mot de passe ne peut pas être entièrement numérique.")


def validate_person_name(value: str, *, field: str = "Nom") -> str:
    value = (value or "").strip()
    if len(value) < 2:
        raise ValidationError(f"{field} : minimum 2 caractères.")
    if re.search(r"\d", value):
        raise ValidationError(f"{field} : les chiffres ne sont pas autorisés.")
    if not PERSON_NAME_RE.match(value):
        raise ValidationError(f"{field} : lettres, espaces, apostrophe et tiret uniquement.")
    return value


def validate_phone(value: str | None, *, required: bool = False) -> str:
    if not value or not str(value).strip():
        if required:
            raise ValidationError("Téléphone obligatoire.")
        return ""
    value = str(value).strip()
    if not PHONE_RE.match(value):
        raise ValidationError("Téléphone invalide (8 à 15 chiffres, + optionnel).")
    digits = re.sub(r"\D", "", value)
    if len(digits) < 8 or len(digits) > 15:
        raise ValidationError("Téléphone invalide (8 à 15 chiffres).")
    return value


def validate_email_format(value: str | None, *, required: bool = False) -> str:
    if not value or not str(value).strip():
        if required:
            raise ValidationError("Email obligatoire.")
        return ""
    value = str(value).strip().lower()
    if not EMAIL_RE.match(value):
        raise ValidationError("Format email invalide.")
    return value


def validate_gender(value: str) -> str:
    if value not in ("M", "F", "O"):
        raise ValidationError("Genre invalide (M, F ou O).")
    return value


def validate_date_of_birth(value: date) -> date:
    today = timezone.now().date()
    if value > today:
        raise ValidationError("La date de naissance ne peut pas être dans le futur.")
    age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
    if age > 120:
        raise ValidationError("Date de naissance invalide.")
    if age < 0:
        raise ValidationError("Date de naissance invalide.")
    return value


def validate_username(value: str | None) -> str:
    if not value or not str(value).strip():
        raise ValidationError("Identifiant obligatoire.")
    value = str(value).strip().lower()
    if not USERNAME_RE.match(value):
        raise ValidationError("Identifiant : 3–40 caractères (a-z, 0-9, . _ -).")
    return value


def validate_medical_text(
    value: str | None,
    *,
    field: str = "Texte",
    required: bool = True,
    min_len: int = 10,
) -> str:
    value = (value or "").strip()
    if not value:
        if required:
            raise ValidationError(f"{field} est obligatoire.")
        return ""
    if len(value) < min_len:
        raise ValidationError(f"{field} : minimum {min_len} caractères.")
    if value.isdigit():
        raise ValidationError(f"{field} : ne peut pas être uniquement numérique.")
    if not re.search(r"[a-zA-ZÀ-ÿ]", value):
        raise ValidationError(f"{field} : doit contenir des lettres.")
    return value


def sanitize_patient_payload(data: dict, *, partial: bool = False) -> dict:
    """Valide et nettoie les champs patient (create ou update)."""
    out = dict(data)
    if "first_name" in out or not partial:
        out["first_name"] = validate_person_name(out.get("first_name", ""), field="Prénom")
    if "last_name" in out or not partial:
        out["last_name"] = validate_person_name(out.get("last_name", ""), field="Nom")
    if "gender" in out or not partial:
        out["gender"] = validate_gender(out.get("gender", "F"))
    if "date_of_birth" in out or not partial:
        out["date_of_birth"] = validate_date_of_birth(out["date_of_birth"])
    if "phone" in out or (not partial and "phone" in data):
        out["phone"] = validate_phone(out.get("phone", ""))
    if "emergency_contact" in out and out.get("emergency_contact"):
        out["emergency_contact"] = validate_person_name(out["emergency_contact"], field="Contact urgence")
    if "emergency_phone" in out and out.get("emergency_phone"):
        out["emergency_phone"] = validate_phone(out["emergency_phone"])
    return out
