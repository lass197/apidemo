from uuid import UUID

from django.db import transaction
from ninja.errors import HttpError

from core.models import Role, User, UserRole
from core.services.presence import get_active_session_user_ids, is_recently_active
from core.services.audit import log_audit
from core.services.validators import (
    validate_email_format,
    validate_person_name,
    validate_phone,
    validate_username,
)


def _sanitize_user_data(data: dict, *, creating: bool = False) -> dict:
    out = dict(data)
    if creating:
        out["username"] = validate_username(out.get("username", ""))
    if out.get("first_name"):
        out["first_name"] = validate_person_name(out["first_name"], field="Prénom")
    if out.get("last_name"):
        out["last_name"] = validate_person_name(out["last_name"], field="Nom")
    if "phone" in out:
        out["phone"] = validate_phone(out.get("phone", ""))
    if creating or out.get("email"):
        out["email"] = validate_email_format(out.get("email"), required=creating)
    return out


def user_to_dict(user: User, *, include_status: bool = False, online_ids: set | None = None) -> dict:
    roles = user.get_role_codes()
    labels = dict(Role.ROLE_CHOICES)
    data = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone": user.phone,
        "roles": roles,
        "role_labels": [labels.get(r, r) for r in roles],
        "mfa_enabled": user.mfa_enabled,
        "is_staff": user.is_staff,
        "last_login": user.last_login,
        "last_login_ip": str(user.last_login_ip) if user.last_login_ip else None,
        "last_seen_at": user.last_seen_at,
    }
    if include_status:
        has_session = user.id in online_ids if online_ids is not None else user.id in get_active_session_user_ids()
        data["is_active"] = user.is_active
        data["date_joined"] = user.date_joined
        data["has_active_session"] = has_session
        data["is_online"] = has_session and is_recently_active(user)
    return data


def create_user(actor: User, data: dict) -> User:
    data = _sanitize_user_data(data, creating=True)
    if User.objects.filter(username=data["username"]).exists():
        raise ValueError("Ce nom d'utilisateur existe déjà.")
    if User.objects.filter(email__iexact=data["email"]).exists():
        raise ValueError("Cet email est déjà utilisé.")

    with transaction.atomic():
        user = User.objects.create_user(
            username=data["username"],
            email=data["email"],
            password=data["password"],
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            phone=data.get("phone", ""),
            is_staff=data.get("is_staff", False),
        )
        for role_code in data.get("role_codes", []):
            role = Role.objects.get(code=role_code, is_active=True)
            UserRole.objects.create(user=user, role=role, assigned_by=actor)

    log_audit(
        user=actor,
        action_type="CREATE",
        resource_type="User",
        resource_id=str(user.id),
        new_value={"username": user.username, "roles": data.get("role_codes", [])},
    )
    return user


def update_user(actor: User, user: User, data: dict) -> User:
    old = user_to_dict(user)
    data = _sanitize_user_data(data, creating=False)
    if "email" in data and data["email"]:
        if User.objects.filter(email__iexact=data["email"]).exclude(pk=user.pk).exists():
            raise ValueError("Cet email est déjà utilisé.")
    fields = ["email", "first_name", "last_name", "phone", "is_staff", "mfa_enabled"]
    for field in fields:
        if field in data:
            setattr(user, field, data[field])
    if data.get("password"):
        user.set_password(data["password"])
    user.save()

    if "role_codes" in data:
        UserRole.objects.filter(user=user).update(is_active=False)
        for role_code in data["role_codes"]:
            role = Role.objects.get(code=role_code, is_active=True)
            ur, _ = UserRole.objects.get_or_create(user=user, role=role)
            ur.is_active = True
            ur.assigned_by = actor
            ur.save()

    log_audit(
        user=actor,
        action_type="UPDATE",
        resource_type="User",
        resource_id=str(user.id),
        old_value=old,
        new_value=user_to_dict(user),
    )
    return user


def deactivate_user(actor: User, user: User) -> User:
    if user.id == actor.id:
        raise ValueError("Vous ne pouvez pas désactiver votre propre compte.")
    user.is_active = False
    user.save(update_fields=["is_active"])
    log_audit(
        user=actor,
        action_type="UPDATE",
        resource_type="User",
        resource_id=str(user.id),
        new_value={"is_active": False},
    )
    return user


def activate_user(actor: User, user: User) -> User:
    user.is_active = True
    user.save(update_fields=["is_active"])
    log_audit(
        user=actor,
        action_type="UPDATE",
        resource_type="User",
        resource_id=str(user.id),
        new_value={"is_active": True},
    )
    return user
