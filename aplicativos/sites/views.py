"""Views administrativas para o gerenciamento de projetos de sites e workspace."""

from typing import Any

from django.contrib import messages
from django.db import models
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from aplicativos.administracao.permissoes import RequerAutenticacaoAdministrativaMixin
from aplicativos.clientes.models import Cliente

from .forms import ProjetoSiteCriacaoForm, ProjetoSiteEdicaoForm
from .models import EventoAnalitico, ProjetoSite
from .servicos import duplicar_projeto


class WorkspaceSitesView(RequerAutenticacaoAdministrativaMixin, ListView):
    """
    Workspace administrativo e centro operacional 'Meus Sites'.

    Exibe os projetos de BioSites e páginas cadastradas, com busca no backend,
    filtros por status e cliente, métricas em tempo real e paginação estruturada.
    """

    model = ProjetoSite
    template_name = "painel/sites/lista.html"
    context_object_name = "sites"
    paginate_by = 12

    def get_queryset(self):
        # Evita N+1 carregando cliente, publicação ativa e endereços vinculados
        qs = (
            ProjetoSite.objects.select_related("cliente", "publicacao_ativa")
            .prefetch_related("enderecos")
            .annotate(
                total_views=models.Count(
                    "eventos_analiticos",
                    filter=models.Q(
                        eventos_analiticos__tipo_evento=EventoAnalitico.TipoEvento.PAGE_VIEW
                    ),
                    distinct=True,
                )
            )
            .order_by("-atualizado_em")
        )

        termo = self.request.GET.get("q", "").strip()
        if termo:
            qs = qs.filter(
                models.Q(nome__icontains=termo)
                | models.Q(slug__icontains=termo)
                | models.Q(cliente__nome__icontains=termo)
                | models.Q(cliente__nome_fantasia__icontains=termo)
                | models.Q(enderecos__host__icontains=termo)
            ).distinct()

        # Filtro por cliente
        cliente_ref = self.request.GET.get("cliente", "").strip()
        if cliente_ref:
            if cliente_ref.isdigit():
                qs = qs.filter(cliente_id=int(cliente_ref))
            else:
                qs = qs.filter(cliente__uuid=cliente_ref)

        # Filtro por status
        filtro_status = self.request.GET.get("status", "ativos").strip().lower()
        if filtro_status in ("no_ar", "publicados", "publicado"):
            qs = qs.filter(
                status=ProjetoSite.Status.PUBLICADO,
                publicacao_ativa__isnull=False,
            )
        elif filtro_status in ("fora_do_ar", "offline"):
            qs = qs.filter(status=ProjetoSite.Status.RASCUNHO)
        elif filtro_status == "rascunho":
            qs = qs.filter(
                status=ProjetoSite.Status.RASCUNHO,
                publicacoes__isnull=True,
            )
        elif filtro_status in ("pendentes", "alteracoes"):
            # Publicados que possuem alterações não publicadas
            projetos_pub = ProjetoSite.objects.filter(
                status=ProjetoSite.Status.PUBLICADO,
                publicacao_ativa__isnull=False,
            ).select_related("publicacao_ativa")
            uuids_pendentes = [p.uuid for p in projetos_pub if p.tem_alteracoes_nao_publicadas()]
            qs = qs.filter(uuid__in=uuids_pendentes)
        elif filtro_status == "arquivados":
            qs = qs.filter(status=ProjetoSite.Status.ARQUIVADO)
        elif filtro_status == "todos":
            pass  # Exibe todos os projetos
        else:
            # Por padrão exibe projetos ativos/rascunhos (não arquivados)
            qs = qs.exclude(status=ProjetoSite.Status.ARQUIVADO)

        return qs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Dashboard"
        context["q"] = self.request.GET.get("q", "")
        context["status_atual"] = self.request.GET.get("status", "ativos")
        context["cliente_atual"] = self.request.GET.get("cliente", "")
        context["total_geral"] = ProjetoSite.objects.count()

        # Dados reais para os KPI Cards operacionais superiores
        context["total_clientes"] = Cliente.objects.count()
        context["total_sites_no_ar"] = ProjetoSite.objects.filter(
            status=ProjetoSite.Status.PUBLICADO, publicacao_ativa__isnull=False
        ).count()
        context["total_sites_fora_ar"] = (
            ProjetoSite.objects.filter(status=ProjetoSite.Status.RASCUNHO)
            .exclude(status=ProjetoSite.Status.ARQUIVADO)
            .count()
        )

        projetos_publicados = ProjetoSite.objects.filter(
            status=ProjetoSite.Status.PUBLICADO, publicacao_ativa__isnull=False
        ).select_related("publicacao_ativa")
        context["total_alteracoes_pendentes"] = sum(
            1 for p in projetos_publicados if p.tem_alteracoes_nao_publicadas()
        )

        context["clientes_filtro"] = Cliente.objects.all().order_by("nome")
        return context


class ProjetoSiteCreateView(RequerAutenticacaoAdministrativaMixin, CreateView):
    """Criação de novos projetos vinculados obrigatoriamente a um cliente."""

    model = ProjetoSite
    form_class = ProjetoSiteCriacaoForm
    template_name = "painel/sites/form.html"

    def get_initial(self) -> dict[str, Any]:
        initial = super().get_initial()
        # Permite pré-selecionar cliente ao clicar a partir da tela de detalhes do cliente
        cliente_uuid = self.request.GET.get("cliente", "")
        if cliente_uuid:
            cliente = Cliente.objects.filter(uuid=cliente_uuid, status=Cliente.Status.ATIVO).first()
            if cliente:
                initial["cliente"] = cliente

        # Permite pré-selecionar template ao clicar a partir da biblioteca de templates
        template_uuid = self.request.GET.get("template", "")
        if template_uuid:
            from .models import TemplateSite

            template = TemplateSite.objects.filter(uuid=template_uuid, ativo=True).first()
            if template:
                initial["template_origem"] = template

        return initial

    def form_valid(self, form: ProjetoSiteCriacaoForm) -> HttpResponse:
        template_origem = form.cleaned_data.get("template_origem")
        if template_origem:
            from django.core.exceptions import ValidationError

            from .servicos_templates import instanciar_template

            try:
                self.object = instanciar_template(
                    template=template_origem,
                    cliente=form.cleaned_data["cliente"],
                    nome=form.cleaned_data["nome"],
                    slug=form.cleaned_data.get("slug"),
                    tipo=form.cleaned_data.get("tipo", ProjetoSite.Tipo.BIOSITE),
                    descricao_interna=form.cleaned_data.get("descricao_interna", ""),
                )
                messages.success(
                    self.request,
                    f"Projeto '{self.object.nome}' criado com sucesso a partir do modelo '{template_origem.nome}'!",
                )
                return redirect("painel:site_editor", uuid=self.object.uuid)
            except ValidationError as e:
                form.add_error(None, f"Erro ao instanciar modelo: {e}")
                return self.form_invalid(form)

        # Criação em branco tradicional
        response = super().form_valid(form)
        from .servicos_estrutura import garantir_pagina_inicial

        garantir_pagina_inicial(self.object)
        messages.success(self.request, f"Projeto '{self.object.nome}' criado com sucesso!")
        return response

    def get_success_url(self) -> str:
        return reverse("painel:site_detalhe", kwargs={"uuid": self.object.uuid})

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        from .models import TemplateSite

        context["titulo_pagina"] = "Novo Projeto de Site"
        context["templates_disponiveis"] = TemplateSite.objects.filter(ativo=True).order_by(
            "ordem", "nome"
        )
        template_uuid = self.request.GET.get("template", "")
        if template_uuid:
            context["template_preselecionado"] = TemplateSite.objects.filter(
                uuid=template_uuid, ativo=True
            ).first()
        return context


class ProjetoSiteDetailView(RequerAutenticacaoAdministrativaMixin, DetailView):
    """Página de detalhes e configurações administrativas do projeto."""

    model = ProjetoSite
    slug_field = "uuid"
    slug_url_kwarg = "uuid"
    template_name = "painel/sites/detalhe.html"
    context_object_name = "site"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        projeto: ProjetoSite = self.object
        context["publicacoes"] = projeto.publicacoes.select_related("publicado_por").order_by(
            "-numero_versao"
        )[:10]
        context["total_publicacoes"] = projeto.publicacoes.count()
        context["url_publica"] = projeto.obter_url_publica(self.request)
        context["esta_publicado"] = projeto.esta_publicado()
        context["tem_alteracoes_pendentes"] = (
            projeto.tem_alteracoes_nao_publicadas() if projeto.esta_publicado() else False
        )
        from .models import EnderecoSite
        from .servicos_dns import obter_cname_esperado
        from .servicos_dominios import obter_base_domain

        context["subdominio_atual"] = projeto.enderecos.filter(
            tipo=EnderecoSite.Tipo.SUBDOMINIO_PLATAFORMA
        ).first()
        context["dominios_personalizados"] = projeto.enderecos.filter(
            tipo=EnderecoSite.Tipo.DOMINIO_PERSONALIZADO
        ).order_by("-principal", "-criado_em")
        context["endereco_principal"] = projeto.obter_endereco_principal()
        context["base_domain"] = obter_base_domain()
        context["cname_target"] = obter_cname_esperado()
        context["links_inteligentes"] = projeto.links_inteligentes.all().order_by("-criado_em")
        context["todos_projetos_ativos"] = (
            ProjetoSite.objects.exclude(id=projeto.id)
            .exclude(status=ProjetoSite.Status.ARQUIVADO)
            .order_by("nome")
        )
        return context


class ProjetoSiteUpdateView(RequerAutenticacaoAdministrativaMixin, UpdateView):
    """Edição das informações básicas do projeto."""

    model = ProjetoSite
    slug_field = "uuid"
    slug_url_kwarg = "uuid"
    form_class = ProjetoSiteEdicaoForm
    template_name = "painel/sites/form.html"

    def form_valid(self, form: ProjetoSiteEdicaoForm) -> HttpResponse:
        response = super().form_valid(form)
        messages.success(self.request, f"Projeto '{self.object.nome}' atualizado com sucesso!")
        return response

    def get_success_url(self) -> str:
        return reverse("painel:site_detalhe", kwargs={"uuid": self.object.uuid})

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["titulo_pagina"] = f"Editar Projeto: {self.object.nome}"
        context["site"] = self.object
        return context


class ProjetoSiteDuplicarView(RequerAutenticacaoAdministrativaMixin, View):
    """Duplicação atômica de projeto via POST."""

    def post(self, request: HttpRequest, uuid: str) -> HttpResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        novo_projeto = duplicar_projeto(projeto)
        messages.success(
            request,
            f"Projeto '{novo_projeto.nome}' duplicado com sucesso a partir de '{projeto.nome}'.",
        )
        return redirect("painel:site_detalhe", uuid=novo_projeto.uuid)


class ProjetoSiteArquivarView(RequerAutenticacaoAdministrativaMixin, View):
    """Arquivamento de projeto via POST."""

    def post(self, request: HttpRequest, uuid: str) -> HttpResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        projeto.arquivar()
        messages.success(request, f"Projeto '{projeto.nome}' arquivado com sucesso.")
        return redirect("painel:sites")


class ProjetoSiteRestaurarView(RequerAutenticacaoAdministrativaMixin, View):
    """Restauração de projeto arquivado via POST."""

    def post(self, request: HttpRequest, uuid: str) -> HttpResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        projeto.restaurar()
        messages.success(request, f"Projeto '{projeto.nome}' restaurado para rascunho com sucesso.")
        return redirect("painel:site_detalhe", uuid=projeto.uuid)
