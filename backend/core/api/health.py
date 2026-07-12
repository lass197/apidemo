from datetime import datetime, timezone
import os

from django.conf import settings
from django.db import connection
from ninja import Router

from core.schemas import HealthOut

router = Router(tags=["Santé"])


@router.get("/sante/", response=HealthOut)
def health_check(request):
    db_conf = settings.DATABASES.get("default", {})
    engine = db_conf.get("ENGINE", "")
    engine_label = "postgresql" if "postgresql" in engine else "sqlite" if "sqlite" in engine else engine
    has_url = bool(os.getenv("DATABASE_URL", "").strip())
    db_host = str(db_conf.get("HOST") or "")
    detail = ""
    db_ok = True
    try:
        connection.ensure_connection()
    except Exception as exc:
        db_ok = False
        detail = str(exc).split("\n")[0][:200]
        if not has_url and engine_label != "sqlite":
            detail = "DATABASE_URL manquant — collez l'External Database URL dans Render."

    if db_ok and engine_label == "sqlite" and os.getenv("RENDER"):
        detail = "SQLite actif : ajoutez DATABASE_URL (External Database URL) et redéployez."

    return {
        "status": "ok" if db_ok else "degraded",
        "version": "1.0.0",
        "database": "connected" if db_ok else "disconnected",
        "timestamp": datetime.now(timezone.utc),
        "engine": engine_label,
        "detail": detail,
        "has_database_url": has_url,
        "db_host": db_host,
    }
