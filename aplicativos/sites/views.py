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
from .models import ProjetoSite
from .servicos import duplicar_projeto


class WorkspaceSitesView(RequerAutenticacaoAdministrativaMixin, ListView):
    """
    Workspace administrativo 'Meus Sites'.

    Exibe os projetos de BioSites e páginas cadastradas, com busca no backend,
    filtros por status e paginação estruturada.
    """

    model = ProjetoSite
    template_name = "painel/sites/lista.html"
    context_object_name = "sites"
    paginate_by = 12

    def get_queryset(self):
        # Evita N+1 carregando o cliente vinculado
        qs = ProjetoSite.objects.select_related("cliente").order_by("-atualizado_em")

        termo = self.request.GET.get("q", "").strip()
        if termo:
            qs = qs.filter(
                models.Q(nome__icontains=termo)
                | models.Q(slug__icontains=termo)
                | models.Q(cliente__nome__icontains=termo)
                | models.Q(cliente__nome_fantasia__icontains=termo)
            )

        filtro_status = self.request.GET.get("status", "ativos").strip().lower()
        if filtro_status == "arquivados":
            qs = qs.filter(status=ProjetoSite.Status.ARQUIVADO)
        elif filtro_status == "todos":
            pass  # Exibe todos os projetos
        else:
            # Por padrão exibe projetos ativos/rascunhos (não arquivados)
            qs = qs.exclude(status=ProjetoSite.Status.ARQUIVADO)

        return qs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Meus Sites"
        context["q"] = self.request.GET.get("q", "")
        context["status_atual"] = self.request.GET.get("status", "ativos")
        context["total_geral"] = ProjetoSite.objects.count()
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
        return initial

    def form_valid(self, form: ProjetoSiteCriacaoForm) -> HttpResponse:
        response = super().form_valid(form)
        messages.success(self.request, f"Projeto '{self.object.nome}' criado com sucesso!")
        return response

    def get_success_url(self) -> str:
        return reverse("painel:site_detalhe", kwargs={"uuid": self.object.uuid})

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["titulo_pagina"] = "Novo Projeto de Site"
        return context


class ProjetoSiteDetailView(RequerAutenticacaoAdministrativaMixin, DetailView):
    """Página de detalhes e configurações administrativas do projeto."""

    model = ProjetoSite
    slug_field = "uuid"
    slug_url_kwarg = "uuid"
    template_name = "painel/sites/detalhe.html"
    context_object_name = "site"


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
