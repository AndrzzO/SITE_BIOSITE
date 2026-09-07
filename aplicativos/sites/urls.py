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
from .views_estrutura import (
    ContainerCriarView,
    ElementoCriarView,
    ElementoDuplicarView,
    ElementoExcluirView,
    EstruturaSiteJsonView,
    EstruturaSiteView,
    PaginaCriarView,
    ReordenarNiveisView,
    SecaoCriarView,
    SecaoDuplicarView,
    SecaoExcluirView,
)

urlpatterns = [
    path("", WorkspaceSitesView.as_view(), name="sites"),
    path("novo/", ProjetoSiteCreateView.as_view(), name="site_novo"),
    path("<uuid:uuid>/", ProjetoSiteDetailView.as_view(), name="site_detalhe"),
    path("<uuid:uuid>/editar/", ProjetoSiteUpdateView.as_view(), name="site_editar"),
    path("<uuid:uuid>/duplicar/", ProjetoSiteDuplicarView.as_view(), name="site_duplicar"),
    path("<uuid:uuid>/arquivar/", ProjetoSiteArquivarView.as_view(), name="site_arquivar"),
    path("<uuid:uuid>/restaurar/", ProjetoSiteRestaurarView.as_view(), name="site_restaurar"),
    # Motor Estrutural de Páginas, Seções, Containers e Elementos (Prompt 4)
    path("<uuid:uuid>/estrutura/", EstruturaSiteView.as_view(), name="site_estrutura"),
    path(
        "<uuid:uuid>/estrutura/json/", EstruturaSiteJsonView.as_view(), name="site_estrutura_json"
    ),
    path(
        "<uuid:uuid>/estrutura/paginas/criar/",
        PaginaCriarView.as_view(),
        name="site_estrutura_pagina_criar",
    ),
    path(
        "<uuid:uuid>/estrutura/secoes/criar/",
        SecaoCriarView.as_view(),
        name="site_estrutura_secao_criar",
    ),
    path(
        "<uuid:uuid>/estrutura/secoes/<int:secao_id>/duplicar/",
        SecaoDuplicarView.as_view(),
        name="site_estrutura_secao_duplicar",
    ),
    path(
        "<uuid:uuid>/estrutura/secoes/<int:secao_id>/excluir/",
        SecaoExcluirView.as_view(),
        name="site_estrutura_secao_excluir",
    ),
    path(
        "<uuid:uuid>/estrutura/containers/criar/",
        ContainerCriarView.as_view(),
        name="site_estrutura_container_criar",
    ),
    path(
        "<uuid:uuid>/estrutura/elementos/criar/",
        ElementoCriarView.as_view(),
        name="site_estrutura_elemento_criar",
    ),
    path(
        "<uuid:uuid>/estrutura/elementos/<int:elemento_id>/duplicar/",
        ElementoDuplicarView.as_view(),
        name="site_estrutura_elemento_duplicar",
    ),
    path(
        "<uuid:uuid>/estrutura/elementos/<int:elemento_id>/excluir/",
        ElementoExcluirView.as_view(),
        name="site_estrutura_elemento_excluir",
    ),
    path(
        "<uuid:uuid>/estrutura/reordenar/",
        ReordenarNiveisView.as_view(),
        name="site_estrutura_reordenar",
    ),
]
