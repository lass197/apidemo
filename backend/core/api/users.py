from ninja import Router

from core.auth import jwt_auth
from core.permissions import require_permission
from core.schemas import UserOut

router = Router(tags=["Utilisateurs"])


@router.get("/me/", response=UserOut, auth=jwt_auth)
def current_user(request):
    user = request.auth
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "roles": user.get_role_codes(),
        "permissions": user.get_permission_codes(),
        "mfa_enabled": user.mfa_enabled,
    }


@router.get("/", response=list[UserOut], auth=jwt_auth)
@require_permission("core.manage_users")
def list_users(request):
    from core.models import User

    users = User.objects.filter(is_active=True).order_by("username")
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "roles": u.get_role_codes(),
            "permissions": u.get_permission_codes(),
            "mfa_enabled": u.mfa_enabled,
        }
        for u in users
    ]
