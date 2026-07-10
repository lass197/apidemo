from datetime import datetime
from typing import Optional
from uuid import UUID

from django.db.models import Count, Q
from django.utils import timezone
from ninja import Router, Schema
from ninja.errors import HttpError

from clinical.models import Bed, Building, Department, PatientMovementHistory, Room
from core.auth import jwt_auth
from core.models import AuditLog, LoginLog, Permission, Role, User, UserRole
from core.services.presence import count_online_users, get_active_session_user_ids, list_online_users
from core.permissions import require_permission
from core.services.audit import log_audit
from core.services.dashboard import get_dashboard_kpis, invalidate_dashboard_cache
from core.services.users import (
    activate_user,
    create_user,
    deactivate_user,
    update_user,
    user_to_dict,
)

router = Router(tags=["Administration"])


class AdminStatsOut(Schema):
    kpis: dict
    users_total: int
    users_active: int
    users_online: int
    audit_today: int
    failed_logins_today: int


class OnlineSessionOut(Schema):
    session_id: UUID
    ip_address: Optional[str]
    user_agent: str
    connected_at: datetime
    expires_at: datetime


class OnlineUserOut(Schema):
    user_id: UUID
    username: str
    full_name: str
    email: str
    roles: list[str]
    role_labels: list[str]
    last_seen_at: Optional[datetime]
    last_login_ip: Optional[str]
    sessions: list[OnlineSessionOut]


class UserCreateIn(Schema):
    username: str
    email: str
    password: str
    first_name: str = ""
    last_name: str = ""
    phone: str = ""
    is_staff: bool = False
    role_codes: list[str] = []


class UserUpdateIn(Schema):
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    is_staff: Optional[bool] = None
    mfa_enabled: Optional[bool] = None
    role_codes: Optional[list[str]] = None


class RoleOut(Schema):
    id: UUID
    code: str
    name: str
    description: str
    permissions: list[str]
    user_count: int = 0


class PermissionOut(Schema):
    id: UUID
    codename: str
    name: str
    module: str


class RbacMatrixOut(Schema):
    modules: list[str]
    permissions: list[PermissionOut]
    roles: list[RoleOut]
    matrix: dict[str, dict[str, bool]]


class AuditLogOut(Schema):
    id: UUID
    timestamp: datetime
    username: Optional[str]
    action_type: str
    resource_type: str
    resource_id: str
    ip_address: Optional[str]


class LoginLogOut(Schema):
    id: UUID
    created_at: datetime
    username_attempt: str
    status: str
    ip_address: Optional[str]
    failure_reason: str


class BuildingOut(Schema):
    id: UUID
    name: str
    code: str
    address: str
    beds_total: int
    beds_available: int
    departments_count: int = 0
    is_active: bool = True


class BuildingIn(Schema):
    name: str
    code: str
    address: str = ""


class BuildingUpdateIn(Schema):
    name: Optional[str] = None
    code: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None


class DepartmentOut(Schema):
    id: UUID
    building_id: UUID
    building_code: str
    name: str
    code: str
    rooms_count: int = 0
    is_active: bool = True


class DepartmentIn(Schema):
    building_id: UUID
    name: str
    code: str


class DepartmentUpdateIn(Schema):
    name: Optional[str] = None
    code: Optional[str] = None
    is_active: Optional[bool] = None


class RoomOut(Schema):
    id: UUID
    department_id: UUID
    department_name: str
    building_code: str
    number: str
    floor: int
    beds_count: int = 0
    is_active: bool = True


class RoomIn(Schema):
    department_id: UUID
    number: str
    floor: int = 0


class RoomUpdateIn(Schema):
    number: Optional[str] = None
    floor: Optional[int] = None
    is_active: Optional[bool] = None


class BedOut(Schema):
    id: UUID
    room_id: UUID
    building_code: str
    department_name: str
    room_number: str
    label: str
    status: str
    is_active: bool = True


class BedIn(Schema):
    room_id: UUID
    label: str
    status: str = Bed.AVAILABLE


class BedUpdateIn(Schema):
    label: Optional[str] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/stats/", response=AdminStatsOut, auth=jwt_auth)
@require_permission("core.manage_users")
def admin_stats(request):
    today = timezone.now().date()
    return {
        "kpis": get_dashboard_kpis(),
        "users_total": User.objects.count(),
        "users_active": User.objects.filter(is_active=True).count(),
        "users_online": count_online_users(),
        "audit_today": AuditLog.objects.filter(timestamp__date=today).count(),
        "failed_logins_today": LoginLog.objects.filter(
            created_at__date=today, status=LoginLog.FAILURE
        ).count(),
    }


@router.get("/online-users/", response=list[OnlineUserOut], auth=jwt_auth)
@require_permission("core.manage_users")
def online_users(request, active_only: bool = False):
    """Utilisateurs connectés (session JWT active) avec leurs rôles."""
    return list_online_users(include_idle=not active_only)


@router.get("/users/", auth=jwt_auth)
@require_permission("core.manage_users")
def list_users(request, include_inactive: bool = False, role: str | None = None, search: str | None = None):
    qs = User.objects.all().order_by("username")
    if not include_inactive:
        qs = qs.filter(is_active=True)
    if role:
        qs = qs.filter(roles__role__code=role, roles__is_active=True).distinct()
    if search:
        qs = qs.filter(
            Q(username__icontains=search)
            | Q(email__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
        )
    online_ids = get_active_session_user_ids()
    return [user_to_dict(u, include_status=True, online_ids=online_ids) for u in qs]


@router.post("/users/", auth=jwt_auth)
@require_permission("core.manage_users")
def create_user_endpoint(request, payload: UserCreateIn):
    try:
        user = create_user(request.auth, payload.dict())
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc
    return user_to_dict(user, include_status=True)


@router.patch("/users/{user_id}/", auth=jwt_auth)
@require_permission("core.manage_users")
def update_user_endpoint(request, user_id: UUID, payload: UserUpdateIn):
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist as exc:
        raise HttpError(404, "Utilisateur introuvable.") from exc
    data = {k: v for k, v in payload.dict().items() if v is not None}
    try:
        user = update_user(request.auth, user, data)
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc
    return user_to_dict(user, include_status=True)


@router.post("/users/{user_id}/activate/", auth=jwt_auth)
@require_permission("core.manage_users")
def activate_user_endpoint(request, user_id: UUID):
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist as exc:
        raise HttpError(404, "Utilisateur introuvable.") from exc
    activate_user(request.auth, user)
    return user_to_dict(user, include_status=True)


@router.post("/users/{user_id}/deactivate/", auth=jwt_auth)
@require_permission("core.manage_users")
def deactivate_user_endpoint(request, user_id: UUID):
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist as exc:
        raise HttpError(404, "Utilisateur introuvable.") from exc
    try:
        deactivate_user(request.auth, user)
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc
    return user_to_dict(user, include_status=True)


@router.get("/roles/", response=list[RoleOut], auth=jwt_auth)
@require_permission("core.manage_users")
def list_roles(request):
    roles = Role.objects.filter(is_active=True).prefetch_related("permissions__permission")
    role_counts = {
        row["role__code"]: row["count"]
        for row in UserRole.objects.filter(is_active=True, user__is_active=True)
        .values("role__code")
        .annotate(count=Count("id"))
    }
    result = []
    for role in roles:
        perms = [
            rp.permission.codename
            for rp in role.permissions.select_related("permission").all()
        ]
        result.append({
            "id": role.id,
            "code": role.code,
            "name": role.name,
            "description": role.description,
            "permissions": perms,
            "user_count": role_counts.get(role.code, 0),
        })
    return result


@router.get("/rbac/matrix/", response=RbacMatrixOut, auth=jwt_auth)
@require_permission("core.manage_users")
def rbac_matrix(request):
    """Matrice complète rôles × permissions, groupée par module."""
    permissions = list(Permission.objects.all().order_by("module", "codename"))
    roles = Role.objects.filter(is_active=True).prefetch_related("permissions__permission")
    role_counts = {
        row["role__code"]: row["count"]
        for row in UserRole.objects.filter(is_active=True, user__is_active=True)
        .values("role__code")
        .annotate(count=Count("id"))
    }
    modules = sorted({p.module for p in permissions})
    matrix: dict[str, dict[str, bool]] = {}
    roles_out = []
    for role in roles:
        perm_set = {rp.permission.codename for rp in role.permissions.all()}
        matrix[role.code] = {p.codename: p.codename in perm_set for p in permissions}
        roles_out.append({
            "id": role.id,
            "code": role.code,
            "name": role.name,
            "description": role.description,
            "permissions": list(perm_set),
            "user_count": role_counts.get(role.code, 0),
        })
    return {
        "modules": modules,
        "permissions": permissions,
        "roles": roles_out,
        "matrix": matrix,
    }


@router.get("/permissions/", response=list[PermissionOut], auth=jwt_auth)
@require_permission("core.manage_users")
def list_permissions(request):
    return list(Permission.objects.all().order_by("module", "codename"))


@router.get("/audit/", response=list[AuditLogOut], auth=jwt_auth)
@require_permission("core.view_audit")
def list_audit_logs(request, limit: int = 100):
    logs = AuditLog.objects.select_related("user").order_by("-timestamp")[:limit]
    return [
        {
            "id": log.id,
            "timestamp": log.timestamp,
            "username": log.user.username if log.user else None,
            "action_type": log.action_type,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "ip_address": str(log.ip_address) if log.ip_address else None,
        }
        for log in logs
    ]


@router.get("/login-logs/", response=list[LoginLogOut], auth=jwt_auth)
@require_permission("core.view_audit")
def list_login_logs(request, limit: int = 100):
    logs = LoginLog.objects.order_by("-created_at")[:limit]
    return [
        {
            "id": log.id,
            "created_at": log.created_at,
            "username_attempt": log.username_attempt,
            "status": log.status,
            "ip_address": str(log.ip_address) if log.ip_address else None,
            "failure_reason": log.failure_reason,
        }
        for log in logs
    ]


@router.get("/patient-movements/", auth=jwt_auth)
@require_permission("core.view_audit")
def admin_list_patient_movements(
    request,
    patient_id: UUID | None = None,
    event_type: str = "",
    limit: int = 200,
):
    from clinical.services.movement_events import movement_history_out

    qs = PatientMovementHistory.objects.select_related("patient", "performed_by", "document").order_by(
        "-event_at", "-created_at"
    )
    if patient_id:
        qs = qs.filter(patient_id=patient_id)
    if event_type:
        qs = qs.filter(event_type=event_type)
    return [movement_history_out(e) for e in qs[:limit]]


@router.get("/documents/{document_id}/download/")
@require_permission("core.view_audit")
def admin_download_document(request, document_id: UUID):
    from django.conf import settings
    from django.http import HttpResponse
    from pathlib import Path

    from documents.models import Document
    from core.services.storage import decrypt_bytes

    try:
        doc = Document.objects.get(pk=document_id)
    except Document.DoesNotExist as exc:
        raise HttpError(404, "Document introuvable.") from exc

    file_path = Path(settings.MEDIA_ROOT) / doc.file_path
    if not file_path.exists():
        raise HttpError(404, "Fichier introuvable.")

    content = file_path.read_bytes()
    if doc.is_encrypted:
        content = decrypt_bytes(content)

    ext = ".pdf" if "pdf" in doc.mime_type else ""
    response = HttpResponse(content, content_type=doc.mime_type)
    response["Content-Disposition"] = f'attachment; filename="{doc.title}{ext}"'
    return response


def _building_stats(building: Building) -> dict:
    beds = Bed.objects.filter(room__department__building=building, is_active=True)
    total = beds.count()
    available = beds.filter(status=Bed.AVAILABLE).count()
    dept_count = building.departments.filter(is_active=True).count()
    return {
        "id": building.id,
        "name": building.name,
        "code": building.code,
        "address": building.address,
        "beds_total": total,
        "beds_available": available,
        "departments_count": dept_count,
        "is_active": building.is_active,
    }


@router.get("/infrastructure/buildings/", response=list[BuildingOut], auth=jwt_auth)
@require_permission("core.manage_users")
def list_buildings(request, include_inactive: bool = False):
    qs = Building.objects.all().order_by("name")
    if not include_inactive:
        qs = qs.filter(is_active=True)
    return [_building_stats(b) for b in qs]


@router.get("/infrastructure/buildings/{building_id}/", response=BuildingOut, auth=jwt_auth)
@require_permission("core.manage_users")
def get_building(request, building_id: UUID):
    try:
        building = Building.objects.get(pk=building_id)
    except Building.DoesNotExist as exc:
        raise HttpError(404, "Bâtiment introuvable.") from exc
    return _building_stats(building)


@router.post("/infrastructure/buildings/", response=BuildingOut, auth=jwt_auth)
@require_permission("core.manage_users")
def create_building(request, payload: BuildingIn):
    if Building.objects.filter(code=payload.code.strip().upper()).exists():
        raise HttpError(400, "Ce code bâtiment existe déjà.")
    building = Building.objects.create(
        name=payload.name,
        code=payload.code.strip().upper(),
        address=payload.address,
    )
    log_audit(
        user=request.auth,
        action_type="CREATE",
        resource_type="Building",
        resource_id=str(building.id),
        new_value={"code": building.code, "name": building.name},
    )
    return _building_stats(building)


@router.patch("/infrastructure/buildings/{building_id}/", response=BuildingOut, auth=jwt_auth)
@require_permission("core.manage_users")
def update_building(request, building_id: UUID, payload: BuildingUpdateIn):
    try:
        building = Building.objects.get(pk=building_id)
    except Building.DoesNotExist as exc:
        raise HttpError(404, "Bâtiment introuvable.") from exc
    data = payload.dict()
    if data.get("code") and Building.objects.filter(code=data["code"].strip().upper()).exclude(pk=building.pk).exists():
        raise HttpError(400, "Ce code bâtiment existe déjà.")
    old = {"name": building.name, "code": building.code, "is_active": building.is_active}
    if data.get("is_active") is False and building.is_active:
        occupied = Bed.objects.filter(
            room__department__building=building,
            status=Bed.OCCUPIED,
            is_active=True,
        ).exists()
        if occupied:
            raise HttpError(409, "Impossible de désactiver : des lits sont encore occupés.")
    for field in ("name", "code", "address", "is_active"):
        if data.get(field) is not None:
            value = data[field].strip().upper() if field == "code" else data[field]
            setattr(building, field, value)
    building.save()
    invalidate_dashboard_cache()
    log_audit(
        user=request.auth,
        action_type="UPDATE",
        resource_type="Building",
        resource_id=str(building.id),
        old_value=old,
        new_value={"name": building.name, "code": building.code, "is_active": building.is_active},
    )
    return _building_stats(building)


@router.delete("/infrastructure/buildings/{building_id}/", auth=jwt_auth)
@require_permission("core.delete_building")
def deactivate_building(request, building_id: UUID):
    try:
        building = Building.objects.get(pk=building_id)
    except Building.DoesNotExist as exc:
        raise HttpError(404, "Bâtiment introuvable.") from exc
    occupied = Bed.objects.filter(
        room__department__building=building,
        status=Bed.OCCUPIED,
        is_active=True,
    ).exists()
    if occupied:
        raise HttpError(409, "Impossible de désactiver : des lits sont encore occupés.")
    building.is_active = False
    building.save(update_fields=["is_active", "updated_at"])
    invalidate_dashboard_cache()
    log_audit(
        user=request.auth,
        action_type="DELETE",
        resource_type="Building",
        resource_id=str(building.id),
        new_value={"is_active": False},
    )
    return {"detail": "Bâtiment désactivé."}


@router.get("/infrastructure/departments/", response=list[DepartmentOut], auth=jwt_auth)
@require_permission("core.manage_users")
def list_departments(request, building_id: UUID | None = None, include_inactive: bool = False):
    qs = Department.objects.select_related("building").order_by("building__code", "name")
    if building_id:
        qs = qs.filter(building_id=building_id)
    if not include_inactive:
        qs = qs.filter(is_active=True, building__is_active=True)
    return [
        {
            "id": d.id,
            "building_id": d.building_id,
            "building_code": d.building.code,
            "name": d.name,
            "code": d.code,
            "rooms_count": d.rooms.filter(is_active=True).count(),
            "is_active": d.is_active,
        }
        for d in qs
    ]


@router.post("/infrastructure/departments/", response=DepartmentOut, auth=jwt_auth)
@require_permission("core.manage_users")
def create_department(request, payload: DepartmentIn):
    try:
        building = Building.objects.get(pk=payload.building_id, is_active=True)
    except Building.DoesNotExist as exc:
        raise HttpError(404, "Bâtiment introuvable.") from exc
    if Department.objects.filter(building=building, code=payload.code).exists():
        raise HttpError(400, "Ce code service existe déjà dans ce bâtiment.")
    dept = Department.objects.create(
        building=building,
        name=payload.name,
        code=payload.code.upper(),
    )
    invalidate_dashboard_cache()
    log_audit(
        user=request.auth,
        action_type="CREATE",
        resource_type="Department",
        resource_id=str(dept.id),
        new_value={"code": dept.code, "name": dept.name},
    )
    return {
        "id": dept.id,
        "building_id": dept.building_id,
        "building_code": building.code,
        "name": dept.name,
        "code": dept.code,
        "rooms_count": 0,
        "is_active": dept.is_active,
    }


@router.patch("/infrastructure/departments/{department_id}/", response=DepartmentOut, auth=jwt_auth)
@require_permission("core.manage_users")
def update_department(request, department_id: UUID, payload: DepartmentUpdateIn):
    try:
        dept = Department.objects.select_related("building").get(pk=department_id)
    except Department.DoesNotExist as exc:
        raise HttpError(404, "Service introuvable.") from exc
    data = payload.dict()
    if data.get("code") and Department.objects.filter(
        building=dept.building, code=data["code"]
    ).exclude(pk=dept.pk).exists():
        raise HttpError(400, "Ce code service existe déjà.")
    for field in ("name", "code", "is_active"):
        if data.get(field) is not None:
            setattr(dept, field, data["code"].upper() if field == "code" else data[field])
    dept.save()
    invalidate_dashboard_cache()
    return {
        "id": dept.id,
        "building_id": dept.building_id,
        "building_code": dept.building.code,
        "name": dept.name,
        "code": dept.code,
        "rooms_count": dept.rooms.filter(is_active=True).count(),
        "is_active": dept.is_active,
    }


@router.get("/infrastructure/rooms/", response=list[RoomOut], auth=jwt_auth)
@require_permission("core.manage_users")
def list_rooms(request, department_id: UUID | None = None, include_inactive: bool = False):
    qs = Room.objects.select_related("department__building").order_by(
        "department__building__code", "number"
    )
    if department_id:
        qs = qs.filter(department_id=department_id)
    if not include_inactive:
        qs = qs.filter(is_active=True, department__is_active=True)
    return [
        {
            "id": r.id,
            "department_id": r.department_id,
            "department_name": r.department.name,
            "building_code": r.department.building.code,
            "number": r.number,
            "floor": r.floor,
            "beds_count": r.beds.filter(is_active=True).count(),
            "is_active": r.is_active,
        }
        for r in qs
    ]


@router.post("/infrastructure/rooms/", response=RoomOut, auth=jwt_auth)
@require_permission("core.manage_users")
def create_room(request, payload: RoomIn):
    try:
        dept = Department.objects.select_related("building").get(pk=payload.department_id, is_active=True)
    except Department.DoesNotExist as exc:
        raise HttpError(404, "Service introuvable.") from exc
    if Room.objects.filter(department=dept, number=payload.number).exists():
        raise HttpError(400, "Ce numéro de chambre existe déjà.")
    room = Room.objects.create(
        department=dept,
        number=payload.number,
        floor=payload.floor,
    )
    invalidate_dashboard_cache()
    return {
        "id": room.id,
        "department_id": room.department_id,
        "department_name": dept.name,
        "building_code": dept.building.code,
        "number": room.number,
        "floor": room.floor,
        "beds_count": 0,
        "is_active": room.is_active,
    }


@router.patch("/infrastructure/rooms/{room_id}/", response=RoomOut, auth=jwt_auth)
@require_permission("core.manage_users")
def update_room(request, room_id: UUID, payload: RoomUpdateIn):
    try:
        room = Room.objects.select_related("department__building").get(pk=room_id)
    except Room.DoesNotExist as exc:
        raise HttpError(404, "Chambre introuvable.") from exc
    data = payload.dict()
    if data.get("number") and Room.objects.filter(
        department=room.department, number=data["number"]
    ).exclude(pk=room.pk).exists():
        raise HttpError(400, "Ce numéro de chambre existe déjà.")
    for field in ("number", "floor", "is_active"):
        if data.get(field) is not None:
            setattr(room, field, data[field])
    room.save()
    invalidate_dashboard_cache()
    return {
        "id": room.id,
        "department_id": room.department_id,
        "department_name": room.department.name,
        "building_code": room.department.building.code,
        "number": room.number,
        "floor": room.floor,
        "beds_count": room.beds.filter(is_active=True).count(),
        "is_active": room.is_active,
    }


@router.get("/infrastructure/beds/", response=list[BedOut], auth=jwt_auth)
@require_permission("core.manage_users")
def list_beds(request, include_inactive: bool = False):
    qs = Bed.objects.select_related("room__department__building").order_by(
        "room__department__building__code", "room__number", "label"
    )
    if not include_inactive:
        qs = qs.filter(is_active=True)
    beds = qs
    return [
        {
            "id": bed.id,
            "room_id": bed.room_id,
            "building_code": bed.room.department.building.code,
            "department_name": bed.room.department.name,
            "room_number": bed.room.number,
            "label": bed.label,
            "status": bed.status,
            "is_active": bed.is_active,
        }
        for bed in beds
    ]


@router.post("/infrastructure/beds/", response=BedOut, auth=jwt_auth)
@require_permission("core.manage_users")
def create_bed(request, payload: BedIn):
    valid = {Bed.AVAILABLE, Bed.OCCUPIED, Bed.MAINTENANCE}
    if payload.status not in valid:
        raise HttpError(400, f"Statut invalide. Valeurs : {', '.join(valid)}")
    try:
        room = Room.objects.select_related("department__building").get(pk=payload.room_id, is_active=True)
    except Room.DoesNotExist as exc:
        raise HttpError(404, "Chambre introuvable.") from exc
    if Bed.objects.filter(room=room, label=payload.label).exists():
        raise HttpError(400, "Ce lit existe déjà dans cette chambre.")
    bed = Bed.objects.create(room=room, label=payload.label, status=payload.status)
    invalidate_dashboard_cache()
    return {
        "id": bed.id,
        "room_id": bed.room_id,
        "building_code": room.department.building.code,
        "department_name": room.department.name,
        "room_number": room.number,
        "label": bed.label,
        "status": bed.status,
        "is_active": bed.is_active,
    }


@router.patch("/infrastructure/beds/{bed_id}/", response=BedOut, auth=jwt_auth)
@require_permission("core.manage_users")
def update_bed(request, bed_id: UUID, payload: BedUpdateIn):
    valid = {Bed.AVAILABLE, Bed.OCCUPIED, Bed.MAINTENANCE}
    try:
        bed = Bed.objects.select_related("room__department__building").get(pk=bed_id)
    except Bed.DoesNotExist as exc:
        raise HttpError(404, "Lit introuvable.") from exc
    data = payload.dict()
    if data.get("status") and data["status"] not in valid:
        raise HttpError(400, f"Statut invalide. Valeurs : {', '.join(valid)}")
    if data.get("label") and Bed.objects.filter(
        room=bed.room, label=data["label"]
    ).exclude(pk=bed.pk).exists():
        raise HttpError(400, "Ce libellé de lit existe déjà.")
    old_status = bed.status
    for field in ("label", "status", "is_active"):
        if data.get(field) is not None:
            setattr(bed, field, data[field])
    bed.save()
    invalidate_dashboard_cache()
    if data.get("status") and data["status"] != old_status:
        log_audit(
            user=request.auth,
            action_type="UPDATE",
            resource_type="Bed",
            resource_id=str(bed.id),
            old_value={"status": old_status},
            new_value={"status": bed.status},
        )
    return {
        "id": bed.id,
        "room_id": bed.room_id,
        "building_code": bed.room.department.building.code,
        "department_name": bed.room.department.name,
        "room_number": bed.room.number,
        "label": bed.label,
        "status": bed.status,
        "is_active": bed.is_active,
    }


@router.patch("/infrastructure/beds/{bed_id}/status/", auth=jwt_auth)
@require_permission("core.manage_users")
def update_bed_status(request, bed_id: UUID, status: str):
    valid = {Bed.AVAILABLE, Bed.OCCUPIED, Bed.MAINTENANCE}
    if status not in valid:
        raise HttpError(400, f"Statut invalide. Valeurs : {', '.join(valid)}")
    try:
        bed = Bed.objects.get(pk=bed_id)
    except Bed.DoesNotExist as exc:
        raise HttpError(404, "Lit introuvable.") from exc
    old_status = bed.status
    bed.status = status
    bed.save(update_fields=["status", "updated_at"])
    invalidate_dashboard_cache()
    log_audit(
        user=request.auth,
        action_type="UPDATE",
        resource_type="Bed",
        resource_id=str(bed.id),
        old_value={"status": old_status},
        new_value={"status": status},
    )
    return {"detail": "Statut mis à jour.", "status": status}
