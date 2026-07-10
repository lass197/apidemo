from ninja import Router
from ninja.errors import HttpError

from core.auth import jwt_auth
from core.middleware import get_client_ip
from core.schemas import (
    LoginIn,
    LogoutIn,
    MessageOut,
    MfaConfirmIn,
    MfaSetupOut,
    PatientRegisterIn,
    RefreshIn,
    RefreshOut,
    RegisterPendingOut,
    ResendOtpIn,
    TokenOut,
    VerifyEmailOtpIn,
)
from core.services.auth import login, logout, refresh_access_token
from core.services.email_otp import issue_registration_otp, resend_registration_otp, verify_registration_otp
from core.services.mfa import generate_mfa_secret, provisioning_uri, verify_mfa_code
from core.services.patient_registration import register_patient
from core.services.rate_limit import is_rate_limited

router = Router(tags=["Authentification"])


@router.post("/register/patient/", response=RegisterPendingOut)
def register_patient_account(request, payload: PatientRegisterIn):
    """Inscription patient — envoi d'un code OTP email (6 chiffres) avant activation."""
    ip = get_client_ip(request) or "unknown"
    if is_rate_limited(f"register:{ip}", limit=10, window=3600):
        raise HttpError(429, "Trop de tentatives d'inscription. Réessayez plus tard.")

    try:
        user, patient, _ = register_patient(
            email=payload.email,
            password=payload.password,
            first_name=payload.first_name,
            last_name=payload.last_name,
            date_of_birth=payload.date_of_birth,
            gender=payload.gender,
            phone=payload.phone,
            username=payload.username,
        )
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc

    otp_sent = bool(issue_registration_otp(user))
    return {
        "detail": "Compte créé. Saisissez le code à 6 chiffres reçu par email.",
        "email": user.email,
        "user_id": user.id,
        "otp_sent": otp_sent,
    }


@router.post("/register/patient/verify-otp/", response=TokenOut)
def verify_patient_registration(request, payload: VerifyEmailOtpIn):
    """Valide le code OTP et active le compte patient."""
    ip = get_client_ip(request) or "unknown"
    if is_rate_limited(f"verify-otp:{ip}", limit=20, window=3600):
        raise HttpError(429, "Trop de tentatives. Réessayez plus tard.")
    try:
        user = verify_registration_otp(payload.email, payload.code)
        return login(user.username, payload.password)
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc


@router.post("/register/patient/resend-otp/", response=MessageOut)
def resend_patient_otp(request, payload: ResendOtpIn):
    ip = get_client_ip(request) or "unknown"
    if is_rate_limited(f"resend-otp:{ip}", limit=5, window=3600):
        raise HttpError(429, "Trop de demandes. Réessayez plus tard.")
    try:
        resend_registration_otp(payload.email)
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc
    return {"detail": "Un nouveau code a été envoyé par email."}


@router.post("/login/", response=TokenOut)
def auth_login(request, payload: LoginIn):
    try:
        return login(payload.username, payload.password, payload.mfa_code)
    except ValueError as exc:
        raise HttpError(401, str(exc)) from exc


@router.post("/refresh/", response=RefreshOut)
def auth_refresh(request, payload: RefreshIn):
    try:
        return refresh_access_token(payload.refresh_token)
    except ValueError as exc:
        raise HttpError(401, str(exc)) from exc


@router.post("/logout/", response=MessageOut, auth=jwt_auth)
def auth_logout(request, payload: LogoutIn):
    logout(request.auth, payload.refresh_token)
    return {"detail": "Déconnexion réussie."}


@router.post("/mfa/setup/", response=MfaSetupOut, auth=jwt_auth)
def mfa_setup(request):
    secret = generate_mfa_secret()
    request.auth.mfa_secret = secret
    request.auth.save(update_fields=["mfa_secret"])
    return {
        "secret": secret,
        "provisioning_uri": provisioning_uri(request.auth.username, secret),
    }


@router.post("/mfa/confirm/", response=MessageOut, auth=jwt_auth)
def mfa_confirm(request, payload: MfaConfirmIn):
    if not request.auth.mfa_secret:
        raise HttpError(400, "Configurez d'abord le MFA.")
    if not verify_mfa_code(request.auth.mfa_secret, payload.code):
        raise HttpError(400, "Code invalide.")
    request.auth.mfa_enabled = True
    request.auth.save(update_fields=["mfa_enabled"])
    return {"detail": "MFA activé."}
