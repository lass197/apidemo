from ninja import NinjaAPI

from administration.api import router as admin_router
from core.api.auth import router as auth_router

admin_api = NinjaAPI(
    title="SGHL Administration API",
    version="1.0.0",
    urls_namespace="sghl-admin",
    docs_url="/docs",
)

admin_api.add_router("/auth", auth_router)
admin_api.add_router("", admin_router)
