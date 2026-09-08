"""Views para gestão da Biblioteca de Templates, Previews e Blocos Reutilizáveis (Prompt 7)."""

import json
import logging
from typing import Any

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, ListView

from aplicativos.administracao.permissoes import RequerAutenticacaoAdministrativaMixin

from .models import BlocoReutilizavel, PaginaSite, ProjetoSite, SecaoSite, TemplateSite
from .renderer import RenderizadorBioSite
from .servicos_templates import (
    criar_bloco_a_partir_secao,
    criar_template_a_partir_projeto,
    instanciar_bloco,
)

logger = logging.getLogger("aplicativos.sites.views_templates")


def _extrair_json_body(request: HttpRequest) -> dict[str, Any]:
    """Auxiliar para parsear payload de corpo JSON ou POST padrão."""
    if request.body and request.content_type == "application/json":
        try:
            return json.loads(request.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
    return request.POST.dict()


class TemplateListView(RequerAutenticacaoAdministrativaMixin, ListView):
    """
    Biblioteca administrativa de templates de sites.

    Exibe os modelos do sistema e os modelos criados pelo usuário com filtros
    por categoria, origem (sistema vs meus modelos) e busca textual.
    """

    model = TemplateSite
    template_name = "painel/templates/lista.html"
    context_object_name = "templates"
    paginate_by = 24

    def get_queryset(self):
        qs = TemplateSite.objects.all()

        # Filtro de status (ativos por padrão)
        filtro_status = self.request.GET.get("status", "ativos")
        if filtro_status == "arquivados":
            qs = qs.filter(ativo=False)
        else:
            qs = qs.filter(ativo=True)

        # Filtro de origem
        filtro_origem = self.request.GET.get("origem", "todos")
        if filtro_origem == "sistema":
            qs = qs.filter(origem=TemplateSite.Origem.SISTEMA)
        elif filtro_origem == "usuario":
            qs = qs.filter(origem=TemplateSite.Origem.USUARIO)

        # Filtro de categoria
        filtro_categoria = self.request.GET.get("categoria", "")
        if filtro_categoria and filtro_categoria != "todos":
            qs = qs.filter(categoria=filtro_categoria)

        # Busca por texto
        termo_busca = self.request.GET.get("q", "").strip()
        if termo_busca:
            qs = qs.filter(nome__icontains=termo_busca) | qs.filter(
                descricao__icontains=termo_busca
            )

        return qs.order_by("ordem", "nome")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Biblioteca de Templates"
        context["categorias"] = TemplateSite.Categoria.choices
        context["categoria_atual"] = self.request.GET.get("categoria", "todos")
        context["origem_atual"] = self.request.GET.get("origem", "todos")
        context["status_atual"] = self.request.GET.get("status", "ativos")
        context["q"] = self.request.GET.get("q", "")
        context["total_sistema"] = TemplateSite.objects.filter(
            origem=TemplateSite.Origem.SISTEMA, ativo=True
        ).count()
        context["total_usuario"] = TemplateSite.objects.filter(
            origem=TemplateSite.Origem.USUARIO, ativo=True
        ).count()
        return context


class TemplatePreviewView(RequerAutenticacaoAdministrativaMixin, DetailView):
    """
    Visualização fiel e interativa de um TemplateSite em viewport smartphone de 390px.

    Renderiza o snapshot estrutural em memória sem gravar registros no banco de dados.
    """

    model = TemplateSite
    slug_field = "uuid"
    slug_url_kwarg = "uuid"
    template_name = "painel/templates/preview.html"
    context_object_name = "template"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        template: TemplateSite = self.object

        renderer = RenderizadorBioSite(modo="preview")
        html_preview = renderer.renderizar_snapshot(template.estrutura_snapshot)

        context["html_preview"] = html_preview
        context["titulo_pagina"] = f"Modelo: {template.nome}"
        return context


class TemplateSalvarComoView(RequerAutenticacaoAdministrativaMixin, View):
    """Transforma o ProjetoSite atual em um TemplateSite da categoria 'Meus Modelos'."""

    def post(self, request: HttpRequest, uuid: str) -> JsonResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        payload = _extrair_json_body(request)

        nome = payload.get("nome", "").strip()
        categoria = payload.get("categoria", TemplateSite.Categoria.BIOSITE)
        descricao = payload.get("descricao", "").strip()
        substituir_placeholders = payload.get("substituir_placeholders", True)

        if isinstance(substituir_placeholders, str):
            substituir_placeholders = substituir_placeholders.lower() in ("true", "1", "t", "sim")

        if not nome:
            return JsonResponse(
                {"ok": False, "erro": "O nome do modelo é obrigatório."}, status=400
            )

        try:
            template = criar_template_a_partir_projeto(
                projeto=projeto,
                nome=nome,
                categoria=categoria,
                descricao=descricao,
                substituir_placeholders=substituir_placeholders,
            )
            return JsonResponse(
                {
                    "ok": True,
                    "template_id": template.id,
                    "uuid": str(template.uuid),
                    "nome": template.nome,
                    "url_biblioteca": reverse("painel:templates_lista"),
                }
            )
        except ValidationError as e:
            return JsonResponse({"ok": False, "erro": str(e)}, status=422)


class TemplateDuplicarView(RequerAutenticacaoAdministrativaMixin, View):
    """Duplica um template (seja do sistema ou do usuário) para 'Meus Modelos'."""

    def post(self, request: HttpRequest, uuid: str) -> HttpResponse:
        template_orig = get_object_or_404(TemplateSite, uuid=uuid)

        novo_nome = f"{template_orig.nome} (Cópia)"
        slug_base = f"{template_orig.slug}-copia"
        contador = 2
        slug_cand = slug_base
        while TemplateSite.objects.filter(slug=slug_cand).exists():
            slug_cand = f"{slug_base}-{contador}"
            contador += 1

        TemplateSite.objects.create(
            nome=novo_nome,
            slug=slug_cand,
            categoria=template_orig.categoria,
            origem=TemplateSite.Origem.USUARIO,
            descricao=template_orig.descricao,
            versao=1,
            ativo=True,
            ordem=template_orig.ordem + 1,
            estrutura_snapshot=template_orig.estrutura_snapshot,
        )

        messages.success(request, f"Modelo '{novo_nome}' duplicado em 'Meus Modelos'.")
        return redirect(f"{reverse('painel:templates_lista')}?origem=usuario")


class TemplateExcluirView(RequerAutenticacaoAdministrativaMixin, View):
    """Exclui um modelo criado pelo usuário. Templates do sistema são imutáveis."""

    def post(self, request: HttpRequest, uuid: str) -> HttpResponse:
        template = get_object_or_404(TemplateSite, uuid=uuid)

        if template.origem == TemplateSite.Origem.SISTEMA:
            messages.error(request, "Modelos padrão do sistema não podem ser excluídos.")
            return redirect("painel:templates_lista")

        nome = template.nome
        template.delete()
        messages.success(request, f"Modelo '{nome}' excluído com sucesso.")
        return redirect(f"{reverse('painel:templates_lista')}?origem=usuario")


class TemplateArquivarView(RequerAutenticacaoAdministrativaMixin, View):
    """Alterna o status ativo/arquivado de um modelo do usuário."""

    def post(self, request: HttpRequest, uuid: str) -> HttpResponse:
        template = get_object_or_404(TemplateSite, uuid=uuid)
        if template.origem == TemplateSite.Origem.SISTEMA:
            messages.error(request, "Modelos padrão do sistema não podem ser arquivados.")
            return redirect("painel:templates_lista")

        template.ativo = not template.ativo
        template.save(update_fields=["ativo", "atualizado_em"])
        status_msg = "arquivado" if not template.ativo else "reativado"
        messages.success(request, f"Modelo '{template.nome}' {status_msg} com sucesso.")
        return redirect(f"{reverse('painel:templates_lista')}?origem=usuario")


# =============================================================================
# ENDPOINTS PARA BLOCOS REUTILIZÁVEIS NO ESTÚDIO
# =============================================================================


class EditorBlocosListarView(RequerAutenticacaoAdministrativaMixin, View):
    """Retorna a lista de blocos reutilizáveis para a aba 'BLOCOS' do editor visual."""

    def get(self, request: HttpRequest, uuid: str) -> JsonResponse:
        # Garante que o projeto existe
        get_object_or_404(ProjetoSite, uuid=uuid)

        blocos = BlocoReutilizavel.objects.filter(ativo=True).order_by("ordem", "nome")
        dados_blocos = [
            {
                "id": b.id,
                "uuid": str(b.uuid),
                "nome": b.nome,
                "slug": b.slug,
                "categoria": b.categoria,
                "categoria_label": b.get_categoria_display(),
                "origem": b.origem,
                "descricao": b.descricao,
            }
            for b in blocos
        ]
        return JsonResponse({"ok": True, "blocos": dados_blocos})


class EditorBlocoInserirView(RequerAutenticacaoAdministrativaMixin, View):
    """Instancia um BlocoReutilizavel como nova seção em uma página do projeto."""

    def post(self, request: HttpRequest, uuid: str) -> JsonResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        payload = _extrair_json_body(request)

        bloco_id = payload.get("bloco_id")
        bloco_uuid = payload.get("bloco_uuid")
        bloco_slug = payload.get("bloco_slug")
        pagina_id = payload.get("pagina_id")
        ordem = payload.get("ordem")

        # Busca bloco
        bloco = None
        if bloco_uuid:
            bloco = BlocoReutilizavel.objects.filter(uuid=bloco_uuid, ativo=True).first()
        elif bloco_id:
            bloco = BlocoReutilizavel.objects.filter(id=bloco_id, ativo=True).first()
        elif bloco_slug:
            bloco = BlocoReutilizavel.objects.filter(slug=bloco_slug, ativo=True).first()

        if not bloco:
            return JsonResponse(
                {"ok": False, "erro": "Bloco reutilizável não encontrado ou inativo."}, status=404
            )

        # Busca página vinculada ao projeto
        if pagina_id:
            pagina = get_object_or_404(PaginaSite, id=pagina_id, projeto=projeto)
        else:
            pagina = projeto.paginas.filter(eh_inicial=True).first()
            if not pagina:
                pagina = projeto.paginas.first()

        if not pagina:
            return JsonResponse(
                {"ok": False, "erro": "Página de destino não encontrada no projeto."}, status=404
            )

        try:
            nova_secao = instanciar_bloco(bloco, pagina, ordem=ordem)
            renderer = RenderizadorBioSite(modo="editor")
            html_secao = renderer.renderizar_secao(nova_secao)

            return JsonResponse(
                {
                    "ok": True,
                    "secao_id": nova_secao.id,
                    "nome_interno": nova_secao.nome_interno,
                    "ordem": nova_secao.ordem,
                    "html": html_secao,
                }
            )
        except ValidationError as e:
            return JsonResponse({"ok": False, "erro": str(e)}, status=422)


class EditorSecaoSalvarBlocoView(RequerAutenticacaoAdministrativaMixin, View):
    """Salva a seção selecionada no editor como um BlocoReutilizavel em 'Meus Blocos'."""

    def post(self, request: HttpRequest, uuid: str, secao_id: int) -> JsonResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        secao = get_object_or_404(SecaoSite, id=secao_id, pagina__projeto=projeto)
        payload = _extrair_json_body(request)

        nome = payload.get("nome", "").strip()
        categoria = payload.get("categoria", BlocoReutilizavel.Categoria.HERO)
        descricao = payload.get("descricao", "").strip()
        substituir_placeholders = payload.get("substituir_placeholders", True)

        if isinstance(substituir_placeholders, str):
            substituir_placeholders = substituir_placeholders.lower() in ("true", "1", "t", "sim")

        if not nome:
            return JsonResponse({"ok": False, "erro": "O nome do bloco é obrigatório."}, status=400)

        try:
            bloco = criar_bloco_a_partir_secao(
                secao=secao,
                nome=nome,
                categoria=categoria,
                descricao=descricao,
                substituir_placeholders=substituir_placeholders,
            )
            return JsonResponse(
                {
                    "ok": True,
                    "bloco_id": bloco.id,
                    "uuid": str(bloco.uuid),
                    "nome": bloco.nome,
                }
            )
        except ValidationError as e:
            return JsonResponse({"ok": False, "erro": str(e)}, status=422)
