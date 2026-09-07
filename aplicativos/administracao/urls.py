"""Roteamento de URLs do painel administrativo privado."""

from django.urls import path

from .views import (
    LoginAdministrativoView,
    LogoutAdministrativoView,
    WorkspaceRedirectView,
    WorkspaceSitesView,
)

app_name = "painel"

urlpatterns = [
    path("login/", LoginAdministrativoView.as_view(), name="login"),
    path("logout/", LogoutAdministrativoView.as_view(), name="logout"),
    path("sites/", WorkspaceSitesView.as_view(), name="sites"),
    path("", WorkspaceRedirectView.as_view(), name="inicio"),
]
