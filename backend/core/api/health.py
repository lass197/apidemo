from datetime import datetime, timezone
import os

from django.conf import settings
from django.db import connection
from ninja import Router

from core.schemas import HealthOut

router = Router(tags=["Santé"])


@router.get("/sante/", response=HealthOut)
def health_check(request):
    engine = settings.DATABASES.get("default", {}).get("ENGINE", "")
    engine_label = "postgresql" if "postgresql" in engine else "sqlite" if "sqlite" in engine else engine
    detail = ""
    db_ok = True
    try:
        connection.ensure_connection()
    except Exception as exc:
        db_ok = False
        # Message utile sans fuite de mot de passe
        detail = str(exc).split("\n")[0][:200]
        if not os.getenv("DATABASE_URL", "").strip() and "postgresql" in engine:
            detail = "DATABASE_URL manquant — configurez l'URL Postgres dans Render."

    return {
        "status": "ok" if db_ok else "degraded",
        "version": "1.0.0",
        "database": "connected" if db_ok else "disconnected",
        "timestamp": datetime.now(timezone.utc),
        "engine": engine_label,
        "detail": detail,
    }
