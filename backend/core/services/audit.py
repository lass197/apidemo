from datetime import date, datetime
from uuid import UUID

from core.middleware import get_client_ip, get_current_request
from core.models import AuditLog, User


def _json_safe(value):
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def log_audit(
    *,
    action_type: str,
    resource_type: str,
    resource_id: str = "",
    old_value: dict | None = None,
    new_value: dict | None = None,
    metadata: dict | None = None,
    user: User | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    request = get_current_request()
    resolved_user = user
    if resolved_user is None and request and hasattr(request, "auth_user"):
        resolved_user = request.auth_user

    return AuditLog.objects.create(
        user=resolved_user,
        ip_address=ip_address or (get_client_ip(request) if request else None),
        action_type=action_type,
        resource_type=resource_type,
        resource_id=resource_id,
        old_value=_json_safe(old_value) if old_value is not None else None,
        new_value=_json_safe(new_value) if new_value is not None else None,
        metadata=_json_safe(metadata) if metadata is not None else None,
    )
