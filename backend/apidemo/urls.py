"""
Routes SGHL
  /admin/          → Console admin Vue.js (SPA personnalisée)
  /api/v1/admin/   → API administration
  /api/v1/         → API REST métier
  /*               → Frontend staff Vue.js (SPA)
"""

from django.urls import path, re_path

from administration.router import admin_api
from apidemo.views import serve_admin, serve_frontend
from core.api.router import api

urlpatterns = [
    path("api/v1/admin/", admin_api.urls),
    path("admin/", serve_admin, name="admin-home"),
    re_path(r"^admin/(?P<resource>.+)$", serve_admin, name="admin"),
    path("api/v1/", api.urls),
    path("", serve_frontend, name="frontend-home"),
    re_path(r"^(?!(admin|api)/)(?P<resource>.+)$", serve_frontend, name="frontend"),
]
