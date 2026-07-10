import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings
from django.contrib.auth import authenticate
from django.utils import timezone as django_tz

from core.models import LoginLog, RefreshToken, Role, User
from core.middleware import get_client_ip, get_current_request
from core.services.mfa import verify_mfa_code
from core.services.rate_limit import is_rate_limited
from core.services.audit import log_audit


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "roles": user.get_role_codes(),
        "type": "access",
        "iat": now,
        "exp": now + settings.JWT_ACCESS_TOKEN_LIFETIME,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _create_refresh_token_string() -> str:
    return secrets.token_urlsafe(48)


def _store_refresh_token(user: User, raw_token: str) -> RefreshToken:
    request = get_current_request()
    expires_at = django_tz.now() + settings.JWT_REFRESH_TOKEN_LIFETIME
    return RefreshToken.objects.create(
        user=user,
        token_hash=_hash_token(raw_token),
        expires_at=expires_at,
        user_agent=(request.META.get("HTTP_USER_AGENT", "")[:255] if request else ""),
        ip_address=get_client_ip(request) if request else None,
    )


def _log_login(user: User | None, username: str, status: str, reason: str = ""):
    request = get_current_request()
    LoginLog.objects.create(
        user=user,
        username_attempt=username,
        status=status,
        ip_address=get_client_ip(request) if request else None,
        user_agent=(request.META.get("HTTP_USER_AGENT", "")[:255] if request else ""),
        failure_reason=reason,
    )


def login(username: str, password: str, mfa_code: str | None = None) -> dict:
    request = get_current_request()
    ip = get_client_ip(request) if request else "unknown"
    login_id = username.strip().lower()
    if is_rate_limited(f"login:{ip}:{login_id}", limit=5, window=300):
        _log_login(None, username, LoginLog.FAILURE, "Rate limit dépassé")
        raise ValueError("Trop de tentatives. Réessayez dans 5 minutes.")

    auth_username = username
    user_by_email = None
    if "@" in login_id:
        from core.services.validators import ValidationError, validate_email_format

        try:
            validate_email_format(login_id, required=True)
        except ValidationError as exc:
            _log_login(None, username, LoginLog.FAILURE, "Email invalide")
            raise ValueError(str(exc)) from exc

        user_by_email = User.objects.filter(email__iexact=login_id, is_active=True).first()
        if user_by_email:
            auth_username = user_by_email.username
        elif not User.objects.filter(email__iexact=login_id).exists():
            _log_login(None, username, LoginLog.FAILURE, "Email inconnu")
            raise ValueError(
                "Aucun compte enregistré avec cet email. "
                "Créez un compte ou vérifiez l'orthographe."
            )

    user = authenticate(username=auth_username, password=password)
    if user is None or not user.is_active:
        if user_by_email:
            _log_login(user_by_email, username, LoginLog.FAILURE, "Mot de passe incorrect")
            raise ValueError("Mot de passe incorrect.")
        _log_login(None, username, LoginLog.FAILURE, "Identifiants invalides")
        raise ValueError("Identifiants invalides.")

    if user.mfa_enabled:
        if not mfa_code or not verify_mfa_code(user.mfa_secret, mfa_code):
            raise ValueError("Code MFA requis ou invalide.")

    if Role.PATIENT in user.get_role_codes() and not user.email_verified:
        raise ValueError("Email non vérifié. Saisissez le code reçu par email ou demandez un renvoi.")

    request = get_current_request()
    if request:
        user.last_login_ip = get_client_ip(request)
        user.last_seen_at = django_tz.now()
        user.save(update_fields=["last_login_ip", "last_seen_at"])

    access = _create_access_token(user)
    refresh_raw = _create_refresh_token_string()
    _store_refresh_token(user, refresh_raw)

    _log_login(user, username, LoginLog.SUCCESS)
    log_audit(
        user=user,
        action_type="LOGIN",
        resource_type="User",
        resource_id=str(user.id),
        new_value={"username": user.username},
    )

    return {
        "access_token": access,
        "refresh_token": refresh_raw,
        "token_type": "Bearer",
        "expires_in": int(settings.JWT_ACCESS_TOKEN_LIFETIME.total_seconds()),
        "user": _user_payload(user),
    }


def refresh_access_token(refresh_token: str) -> dict:
    token_hash = _hash_token(refresh_token)
    stored = (
        RefreshToken.objects.select_related("user")
        .filter(token_hash=token_hash, revoked=False)
        .first()
    )
    if stored is None or stored.expires_at < django_tz.now():
        raise ValueError("Refresh token invalide ou expiré.")

    user = stored.user
    if not user.is_active:
        raise ValueError("Compte désactivé.")

    # Rotation : révoquer l'ancien, émettre un nouveau
    stored.revoked = True
    stored.save(update_fields=["revoked", "updated_at"])

    new_refresh_raw = _create_refresh_token_string()
    new_stored = _store_refresh_token(user, new_refresh_raw)
    stored.replaced_by = new_stored
    stored.save(update_fields=["replaced_by"])

    access = _create_access_token(user)
    return {
        "access_token": access,
        "refresh_token": new_refresh_raw,
        "token_type": "Bearer",
        "expires_in": int(settings.JWT_ACCESS_TOKEN_LIFETIME.total_seconds()),
    }


def logout(user: User, refresh_token: str | None = None) -> None:
    if refresh_token:
        RefreshToken.objects.filter(
            user=user,
            token_hash=_hash_token(refresh_token),
        ).update(revoked=True)

    _log_login(user, user.username, LoginLog.LOGOUT)
    log_audit(
        user=user,
        action_type="LOGOUT",
        resource_type="User",
        resource_id=str(user.id),
    )


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.PyJWTError as exc:
        raise ValueError("Token invalide.") from exc

    if payload.get("type") != "access":
        raise ValueError("Type de token invalide.")
    return payload


def get_user_from_token(token: str) -> User:
    payload = decode_access_token(token)
    try:
        return User.objects.get(pk=payload["sub"], is_active=True)
    except User.DoesNotExist as exc:
        raise ValueError("Utilisateur introuvable.") from exc


def _user_payload(user: User) -> dict:
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "roles": user.get_role_codes(),
        "permissions": user.get_permission_codes(),
        "mfa_enabled": user.mfa_enabled,
        "email_verified": user.email_verified,
    }
