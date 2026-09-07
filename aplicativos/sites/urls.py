"""Roteamento de URLs para projetos de sites e workspace."""

from django.urls import path

from .views import (
    ProjetoSiteArquivarView,
    ProjetoSiteCreateView,
    ProjetoSiteDetailView,
    ProjetoSiteDuplicarView,
    ProjetoSiteRestaurarView,
    ProjetoSiteUpdateView,
    WorkspaceSitesView,
)

urlpatterns = [
    path("", WorkspaceSitesView.as_view(), name="sites"),
    path("novo/", ProjetoSiteCreateView.as_view(), name="site_novo"),
    path("<uuid:uuid>/", ProjetoSiteDetailView.as_view(), name="site_detalhe"),
    path("<uuid:uuid>/editar/", ProjetoSiteUpdateView.as_view(), name="site_editar"),
    path("<uuid:uuid>/duplicar/", ProjetoSiteDuplicarView.as_view(), name="site_duplicar"),
    path("<uuid:uuid>/arquivar/", ProjetoSiteArquivarView.as_view(), name="site_arquivar"),
    path("<uuid:uuid>/restaurar/", ProjetoSiteRestaurarView.as_view(), name="site_restaurar"),
]
