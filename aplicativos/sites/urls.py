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
from .views_dominios import (
    AdicionarDominioPersonalizadoView,
    ConfigurarSubdominioView,
    DefinirDominioPrincipalView,
    RemoverDominioView,
    VerificarDnsDominioView,
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
from .views_publicacao import (
    DespublicarProjetoView,
    PublicacaoPreviewView,
    PublicacaoRestaurarEditorView,
    PublicacaoRollbackView,
    PublicacaoStatusView,
    PublicacoesHistoricoView,
    PublicarProjetoView,
    ValidarPrePublicacaoView,
)
from .views_templates import (
    EditorBlocoInserirView,
    EditorBlocosListarView,
    EditorSecaoSalvarBlocoView,
    TemplateSalvarComoView,
)

urlpatterns = [
    path("", WorkspaceSitesView.as_view(), name="sites"),
    path("novo/", ProjetoSiteCreateView.as_view(), name="site_novo"),
    path("<uuid:uuid>/", ProjetoSiteDetailView.as_view(), name="site_detalhe"),
    path("<uuid:uuid>/editar/", ProjetoSiteUpdateView.as_view(), name="site_editar"),
    path("<uuid:uuid>/duplicar/", ProjetoSiteDuplicarView.as_view(), name="site_duplicar"),
    path("<uuid:uuid>/arquivar/", ProjetoSiteArquivarView.as_view(), name="site_arquivar"),
    path("<uuid:uuid>/restaurar/", ProjetoSiteRestaurarView.as_view(), name="site_restaurar"),
    path(
        "<uuid:uuid>/salvar-template/",
        TemplateSalvarComoView.as_view(),
        name="site_salvar_template",
    ),
    # Ciclo de Vida de Publicação e Versionamento (Prompt 8)
    path("<uuid:uuid>/publicar/", PublicarProjetoView.as_view(), name="site_publicar"),
    path(
        "<uuid:uuid>/publicar/validar/",
        ValidarPrePublicacaoView.as_view(),
        name="site_publicar_validar",
    ),
    path(
        "<uuid:uuid>/publicacao/status/",
        PublicacaoStatusView.as_view(),
        name="site_publicacao_status",
    ),
    path(
        "<uuid:uuid>/publicacoes/",
        PublicacoesHistoricoView.as_view(),
        name="site_publicacoes_historico",
    ),
    path(
        "<uuid:uuid>/publicacoes/<int:versao>/preview/",
        PublicacaoPreviewView.as_view(),
        name="publicacao_preview",
    ),
    path(
        "<uuid:uuid>/publicacoes/<int:versao>/restaurar/",
        PublicacaoRollbackView.as_view(),
        name="publicacao_rollback",
    ),
    path(
        "<uuid:uuid>/publicacoes/<int:versao>/restaurar-editor/",
        PublicacaoRestaurarEditorView.as_view(),
        name="publicacao_restaurar_editor",
    ),
    path("<uuid:uuid>/despublicar/", DespublicarProjetoView.as_view(), name="site_despublicar"),
    # Subdomínios e Domínios Personalizados (Prompt 9)
    path(
        "<uuid:uuid>/dominios/subdominio/",
        ConfigurarSubdominioView.as_view(),
        name="site_configurar_subdominio",
    ),
    path(
        "<uuid:uuid>/dominios/adicionar/",
        AdicionarDominioPersonalizadoView.as_view(),
        name="site_adicionar_dominio",
    ),
    path(
        "<uuid:uuid>/dominios/<int:endereco_id>/verificar/",
        VerificarDnsDominioView.as_view(),
        name="site_verificar_dominio",
    ),
    path(
        "<uuid:uuid>/dominios/<int:endereco_id>/principal/",
        DefinirDominioPrincipalView.as_view(),
        name="site_definir_dominio_principal",
    ),
    path(
        "<uuid:uuid>/dominios/<int:endereco_id>/remover/",
        RemoverDominioView.as_view(),
        name="site_remover_dominio",
    ),
    # Editor Visual Mobile-First e Preview (Prompt 5 & 6)
    path("<uuid:uuid>/editor/", EditorStudioView.as_view(), name="site_editor"),
    path("<uuid:uuid>/editor/dados/", EditorDadosJsonView.as_view(), name="site_editor_dados"),
    path(
        "<uuid:uuid>/editor/blocos/listar/",
        EditorBlocosListarView.as_view(),
        name="site_editor_blocos_listar",
    ),
    path(
        "<uuid:uuid>/editor/bloco/inserir/",
        EditorBlocoInserirView.as_view(),
        name="site_editor_bloco_inserir",
    ),
    path(
        "<uuid:uuid>/editor/secao/<int:secao_id>/salvar-bloco/",
        EditorSecaoSalvarBlocoView.as_view(),
        name="site_editor_secao_salvar_bloco",
    ),
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
