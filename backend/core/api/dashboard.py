from ninja import Router

from core.auth import jwt_auth
from core.permissions import require_permission
from core.schemas import MessageOut
from core.services.dashboard import get_dashboard_kpis

router = Router(tags=["Dashboard"])


@router.get("/kpis/", auth=jwt_auth)
@require_permission("core.view_dashboard")
def dashboard_kpis(request):
    return get_dashboard_kpis()
