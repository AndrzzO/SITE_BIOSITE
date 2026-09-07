"""Views administrativas para gerenciamento de clientes."""

from typing import Any

from django.contrib import messages
from django.db import models
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from aplicativos.administracao.permissoes import RequerAutenticacaoAdministrativaMixin

from .forms import ClienteForm
from .models import Cliente


class ClienteListView(RequerAutenticacaoAdministrativaMixin, ListView):
    """Listagem paginada de clientes com busca e contagem de projetos."""

    model = Cliente
    template_name = "painel/clientes/lista.html"
    context_object_name = "clientes"
    paginate_by = 15

    def get_queryset(self):
        qs = Cliente.objects.annotate(total_projetos=models.Count("projetos")).order_by("nome")

        termo = self.request.GET.get("q", "").strip()
        if termo:
            qs = qs.filter(
                models.Q(nome__icontains=termo)
                | models.Q(nome_fantasia__icontains=termo)
                | models.Q(email__icontains=termo)
                | models.Q(telefone__icontains=termo)
                | models.Q(documento__icontains=termo)
            )

        filtro_status = self.request.GET.get("status", "").strip().lower()
        if filtro_status in [Cliente.Status.ATIVO, Cliente.Status.ARQUIVADO]:
            qs = qs.filter(status=filtro_status)

        return qs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "")
        context["status_atual"] = self.request.GET.get("status", "")
        context["total_geral"] = Cliente.objects.count()
        return context


class ClienteCreateView(RequerAutenticacaoAdministrativaMixin, CreateView):
    """Cadastro de novo cliente comercial."""

    model = Cliente
    form_class = ClienteForm
    template_name = "painel/clientes/form.html"

    def form_valid(self, form: ClienteForm) -> HttpResponse:
        response = super().form_valid(form)
        messages.success(self.request, f"Cliente '{self.object.nome}' cadastrado com sucesso!")
        return response

    def get_success_url(self) -> str:
        # Se veio com parâmetro para criar site em seguida
        proximo = self.request.GET.get("proximo", "")
        if proximo == "novo_site":
            return f"{reverse('painel:site_novo')}?cliente={self.object.uuid}"
        return reverse("painel:cliente_detalhe", kwargs={"uuid": self.object.uuid})

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["titulo_pagina"] = "Novo Cliente"
        context["proximo"] = self.request.GET.get("proximo", "")
        return context


class ClienteDetailView(RequerAutenticacaoAdministrativaMixin, DetailView):
    """Página de detalhes do cliente e projetos vinculados."""

    model = Cliente
    slug_field = "uuid"
    slug_url_kwarg = "uuid"
    template_name = "painel/clientes/detalhe.html"
    context_object_name = "cliente"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["projetos"] = self.object.projetos.all().order_by("-atualizado_em")
        return context


class ClienteUpdateView(RequerAutenticacaoAdministrativaMixin, UpdateView):
    """Edição cadastral de cliente existente."""

    model = Cliente
    slug_field = "uuid"
    slug_url_kwarg = "uuid"
    form_class = ClienteForm
    template_name = "painel/clientes/form.html"

    def form_valid(self, form: ClienteForm) -> HttpResponse:
        response = super().form_valid(form)
        messages.success(self.request, f"Cliente '{self.object.nome}' atualizado com sucesso!")
        return response

    def get_success_url(self) -> str:
        return reverse("painel:cliente_detalhe", kwargs={"uuid": self.object.uuid})

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["titulo_pagina"] = f"Editar Cliente: {self.object.nome}"
        context["cliente"] = self.object
        return context


class ClienteArquivarView(RequerAutenticacaoAdministrativaMixin, View):
    """Arquivamento administrativo de cliente via POST."""

    def post(self, request: HttpRequest, uuid: str) -> HttpResponse:
        cliente = get_object_or_404(Cliente, uuid=uuid)
        cliente.arquivar()
        messages.success(request, f"Cliente '{cliente.nome}' arquivado com sucesso.")
        return redirect("painel:cliente_detalhe", uuid=cliente.uuid)


class ClienteRestaurarView(RequerAutenticacaoAdministrativaMixin, View):
    """Restauração de cliente arquivado via POST."""

    def post(self, request: HttpRequest, uuid: str) -> HttpResponse:
        cliente = get_object_or_404(Cliente, uuid=uuid)
        cliente.restaurar()
        messages.success(request, f"Cliente '{cliente.nome}' restaurado com sucesso.")
        return redirect("painel:cliente_detalhe", uuid=cliente.uuid)
