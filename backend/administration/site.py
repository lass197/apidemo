"""Site d'administration Django SGHL."""

from django.contrib.admin import AdminSite

from django.utils.translation import gettext_lazy as _


class SGHLAdminSite(AdminSite):
    site_header = _("SGHL — Administration hospitalière")
    site_title = _("SGHL Admin")
    index_title = _("Tableau de bord")


sghl_admin = SGHLAdminSite(name="sghl_admin")
