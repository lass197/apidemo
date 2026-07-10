from datetime import datetime, timezone

from django.db import connection
from ninja import Router

from core.schemas import HealthOut

router = Router(tags=["Santé"])


@router.get("/sante/", response=HealthOut)
def health_check(request):
    db_ok = True
    try:
        connection.ensure_connection()
    except Exception:
        db_ok = False

    return {
        "status": "ok" if db_ok else "degraded",
        "version": "1.0.0",
        "database": "connected" if db_ok else "disconnected",
        "timestamp": datetime.now(timezone.utc),
    }
