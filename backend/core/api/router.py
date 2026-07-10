from ninja import NinjaAPI
from ninja.errors import HttpError

from billing.api import router as billing_router
from clinical.api import router as clinical_router
from clinical.api_care import router as clinical_care_router
from core.api.auth import router as auth_router
from core.api.dashboard import router as dashboard_router
from core.api.health import router as health_router
from core.api.public import router as public_router
from core.api.users import router as users_router
from documents.api import router as documents_router
from hr.api import router as hr_router
from laboratory.api import router as laboratory_router
from pharmacy.api import router as pharmacy_router

api = NinjaAPI(
    title="SGHL API",
    version="1.0.0",
    description="Système de Gestion Hospitalière et de Laboratoire",
    urls_namespace="sghl-v1",
)


@api.exception_handler(HttpError)
def http_error_handler(request, exc):
    return api.create_response(request, {"detail": exc.message}, status=exc.status_code)


@api.exception_handler(ValueError)
def value_error_handler(request, exc):
    return api.create_response(request, {"detail": str(exc)}, status=400)


api.add_router("/auth", auth_router)
api.add_router("/users", users_router)
api.add_router("/dashboard", dashboard_router)
api.add_router("", health_router)
api.add_router("", public_router)

api.add_router("/clinical", clinical_router)
api.add_router("/clinical", clinical_care_router)
api.add_router("/laboratory", laboratory_router)
api.add_router("/pharmacy", pharmacy_router)
api.add_router("/billing", billing_router)
api.add_router("/hr", hr_router)
api.add_router("/documents", documents_router)
