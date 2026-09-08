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
from .views_editor import (
    EditorDadosJsonView,
    EditorElementoCriarView,
    EditorElementoDuplicarView,
    EditorElementoExcluirView,
    EditorElementoMoverView,
    EditorElementoSalvarView,
    EditorMidiaListarView,
    EditorMidiaUploadView,
    EditorPaginaCriarView,
    EditorSecaoCriarView,
    EditorSecaoDuplicarView,
    EditorSecaoExcluirView,
    EditorSecaoMoverView,
    EditorSecaoPropriedadesView,
    EditorStudioView,
    EditorVisualConfigSalvarView,
    PreviewSiteView,
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
    # Editor Visual Mobile-First e Preview (Prompt 5 & 6)
    path("<uuid:uuid>/editor/", EditorStudioView.as_view(), name="site_editor"),
    path("<uuid:uuid>/editor/dados/", EditorDadosJsonView.as_view(), name="site_editor_dados"),
    path(
        "<uuid:uuid>/editor/design/salvar/",
        EditorVisualConfigSalvarView.as_view(),
        name="site_editor_design_salvar",
    ),
    path(
        "<uuid:uuid>/editor/midia/upload/",
        EditorMidiaUploadView.as_view(),
        name="site_editor_midia_upload",
    ),
    path(
        "<uuid:uuid>/editor/midia/listar/",
        EditorMidiaListarView.as_view(),
        name="site_editor_midia_listar",
    ),
    path(
        "<uuid:uuid>/editor/elemento/salvar/",
        EditorElementoSalvarView.as_view(),
        name="site_editor_elemento_salvar",
    ),
    path(
        "<uuid:uuid>/editor/elemento/criar/",
        EditorElementoCriarView.as_view(),
        name="site_editor_elemento_criar",
    ),
    path(
        "<uuid:uuid>/editor/elemento/mover/",
        EditorElementoMoverView.as_view(),
        name="site_editor_elemento_mover",
    ),
    path(
        "<uuid:uuid>/editor/elemento/<int:elemento_id>/duplicar/",
        EditorElementoDuplicarView.as_view(),
        name="site_editor_elemento_duplicar",
    ),
    path(
        "<uuid:uuid>/editor/elemento/<int:elemento_id>/excluir/",
        EditorElementoExcluirView.as_view(),
        name="site_editor_elemento_excluir",
    ),
    path(
        "<uuid:uuid>/editor/secao/criar/",
        EditorSecaoCriarView.as_view(),
        name="site_editor_secao_criar",
    ),
    path(
        "<uuid:uuid>/editor/secao/mover/",
        EditorSecaoMoverView.as_view(),
        name="site_editor_secao_mover",
    ),
    path(
        "<uuid:uuid>/editor/secao/<int:secao_id>/duplicar/",
        EditorSecaoDuplicarView.as_view(),
        name="site_editor_secao_duplicar",
    ),
    path(
        "<uuid:uuid>/editor/secao/<int:secao_id>/excluir/",
        EditorSecaoExcluirView.as_view(),
        name="site_editor_secao_excluir",
    ),
    path(
        "<uuid:uuid>/editor/secao/<int:secao_id>/propriedades/",
        EditorSecaoPropriedadesView.as_view(),
        name="site_editor_secao_propriedades",
    ),
    path(
        "<uuid:uuid>/editor/pagina/criar/",
        EditorPaginaCriarView.as_view(),
        name="site_editor_pagina_criar",
    ),
    path("<uuid:uuid>/preview/", PreviewSiteView.as_view(), name="site_preview"),
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
