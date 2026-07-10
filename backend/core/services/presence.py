from datetime import timedelta

from django.utils import timezone

from core.models import RefreshToken, Role, User

ONLINE_ACTIVITY_WINDOW = timedelta(minutes=15)
ACTIVITY_TOUCH_INTERVAL = timedelta(seconds=60)


def touch_user_activity(user: User) -> None:
    """Met à jour last_seen_at (max 1 fois par minute)."""
    now = timezone.now()
    if user.last_seen_at and (now - user.last_seen_at) < ACTIVITY_TOUCH_INTERVAL:
        return
    User.objects.filter(pk=user.pk).update(last_seen_at=now)
    user.last_seen_at = now


def _role_labels() -> dict[str, str]:
    return dict(Role.ROLE_CHOICES)


def list_online_users(*, include_idle: bool = True) -> list[dict]:
    """
    Retourne les utilisateurs avec au moins une session JWT active.
    include_idle=False : uniquement activité récente (last_seen_at).
    """
    now = timezone.now()
    activity_cutoff = now - ONLINE_ACTIVITY_WINDOW
    labels = _role_labels()

    tokens = (
        RefreshToken.objects.filter(revoked=False, expires_at__gt=now, user__is_active=True)
        .select_related("user")
        .order_by("-updated_at")
    )

    by_user: dict[str, dict] = {}
    for token in tokens:
        user = token.user
        uid = str(user.id)
        if uid not in by_user:
            roles = user.get_role_codes()
            by_user[uid] = {
                "user_id": user.id,
                "username": user.username,
                "full_name": user.get_full_name() or user.username,
                "email": user.email,
                "roles": roles,
                "role_labels": [labels.get(r, r) for r in roles],
                "last_seen_at": user.last_seen_at,
                "last_login_ip": str(user.last_login_ip) if user.last_login_ip else None,
                "sessions": [],
            }

        by_user[uid]["sessions"].append({
            "session_id": token.id,
            "ip_address": str(token.ip_address) if token.ip_address else None,
            "user_agent": token.user_agent or "",
            "connected_at": token.created_at,
            "expires_at": token.expires_at,
        })

    result = list(by_user.values())
    if not include_idle:
        result = [
            u for u in result
            if u["last_seen_at"] and u["last_seen_at"] >= activity_cutoff
        ]

    result.sort(key=lambda u: u["last_seen_at"] or u["sessions"][0]["connected_at"], reverse=True)
    return result


def get_active_session_user_ids() -> set:
    """IDs des utilisateurs avec au moins une session JWT active."""
    now = timezone.now()
    return set(
        RefreshToken.objects.filter(
            revoked=False,
            expires_at__gt=now,
            user__is_active=True,
        ).values_list("user_id", flat=True)
    )


def is_recently_active(user: User) -> bool:
    if not user.last_seen_at:
        return False
    return (timezone.now() - user.last_seen_at) < ONLINE_ACTIVITY_WINDOW


def count_online_users() -> int:
    return len(get_active_session_user_ids())
