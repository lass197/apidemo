from functools import wraps

from ninja.errors import HttpError

from core.auth import jwt_auth
from core.models import Role


def require_permission(codename: str):
    """Décorateur API : vérifie la permission RBAC."""

    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = request.auth
            if not user.has_perm_code(codename):
                raise HttpError(403, f"Permission requise : {codename}")
            return func(request, *args, **kwargs)

        return wrapper

    return decorator


def require_role_or_permission(*role_codes: str, permission: str = ""):
    """Accès si l'utilisateur a l'un des rôles actifs ou la permission indiquée."""

    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = request.auth
            if role_codes and user.roles.filter(is_active=True, role__code__in=role_codes).exists():
                return func(request, *args, **kwargs)
            if permission and user.has_perm_code(permission):
                return func(request, *args, **kwargs)
            raise HttpError(403, "Accès réservé aux médecins.")

        return wrapper

    return decorator


def require_any_permission(*codenames: str):
    """Accès si l'utilisateur possède au moins une des permissions."""

    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = request.auth
            if any(user.has_perm_code(c) for c in codenames):
                return func(request, *args, **kwargs)
            raise HttpError(
                403,
                f"Permission requise : {' ou '.join(codenames)}",
            )

        return wrapper

    return decorator


__all__ = [
    "jwt_auth",
    "require_permission",
    "require_role_or_permission",
    "require_any_permission",
]
