import hashlib
import logging
import random
import threading
from datetime import timedelta

from django.utils import timezone

from core.models import EmailOTP, Role, User
from core.services.email_service import enqueue_email

logger = logging.getLogger(__name__)

PURPOSE_REGISTRATION = EmailOTP.REGISTRATION
OTP_TTL_MINUTES = 15
MAX_OTP_ATTEMPTS = 5


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _generate_code() -> str:
    return f"{random.randint(0, 999999):06d}"


def issue_registration_otp(user: User) -> str:
    """Génère un OTP 6 chiffres, l'enregistre et l'envoie par email (async)."""
    EmailOTP.objects.filter(
        user=user,
        purpose=PURPOSE_REGISTRATION,
        used_at__isnull=True,
    ).update(used_at=timezone.now())

    code = _generate_code()
    EmailOTP.objects.create(
        user=user,
        code_hash=_hash_code(code),
        purpose=PURPOSE_REGISTRATION,
        expires_at=timezone.now() + timedelta(minutes=OTP_TTL_MINUTES),
    )

    body = (
        f"Bonjour {user.first_name},\n\n"
        f"Votre code de vérification SGHL : {code}\n\n"
        f"Ce code est valable {OTP_TTL_MINUTES} minutes.\n"
        f"Ne le partagez avec personne.\n\n"
        f"— Centre Hospitalier SGHL"
    )
    enqueue_email(user.email, "SGHL — Code de vérification (6 chiffres)", body)
    logger.info("OTP inscription généré pour %s (dev: %s)", user.email, code)
    return code


def verify_registration_otp(email: str, code: str) -> User:
    email = email.strip().lower()
    user = User.objects.filter(email__iexact=email, is_active=True).first()
    if not user:
        raise ValueError("Compte introuvable.")

    otp = (
        EmailOTP.objects.filter(
            user=user,
            purpose=PURPOSE_REGISTRATION,
            used_at__isnull=True,
        )
        .order_by("-created_at")
        .first()
    )
    if not otp:
        raise ValueError("Aucun code actif. Demandez un nouveau code.")
    if otp.expires_at < timezone.now():
        raise ValueError("Code expiré. Demandez un nouveau code.")
    if otp.attempts >= MAX_OTP_ATTEMPTS:
        raise ValueError("Trop de tentatives. Demandez un nouveau code.")

    if _hash_code(code.strip()) != otp.code_hash:
        otp.attempts += 1
        otp.save(update_fields=["attempts"])
        raise ValueError("Code incorrect.")

    otp.used_at = timezone.now()
    otp.save(update_fields=["used_at"])
    user.email_verified = True
    user.save(update_fields=["email_verified"])
    return user


def resend_registration_otp(email: str) -> User:
    email = email.strip().lower()
    user = User.objects.filter(email__iexact=email, is_active=True).first()
    if not user:
        raise ValueError("Compte introuvable.")
    if user.email_verified:
        raise ValueError("Email déjà vérifié.")
    if not user.roles.filter(role__code=Role.PATIENT, is_active=True).exists():
        raise ValueError("Compte patient introuvable.")
    issue_registration_otp(user)
    return user
