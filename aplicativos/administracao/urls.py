"""Roteamento de URLs do painel administrativo privado."""

from django.urls import include, path

from .views import (
    LoginAdministrativoView,
    LogoutAdministrativoView,
    WorkspaceRedirectView,
)

app_name = "painel"

urlpatterns = [
    path("login/", LoginAdministrativoView.as_view(), name="login"),
    path("logout/", LogoutAdministrativoView.as_view(), name="logout"),
    path("clientes/", include("aplicativos.clientes.urls")),
    path("sites/", include("aplicativos.sites.urls")),
    path("templates/", include("aplicativos.sites.urls_templates")),
    path("", WorkspaceRedirectView.as_view(), name="inicio"),
]
