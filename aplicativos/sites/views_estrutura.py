"""Views administrativas para o gerenciamento estrutural de páginas, seções, containers e elementos."""

import json
import logging
from typing import Any

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.text import slugify
from django.views import View
from django.views.generic import DetailView

from aplicativos.administracao.permissoes import RequerAutenticacaoAdministrativaMixin

from .elementos import RegistroElementos
from .models import ContainerSite, ElementoSite, PaginaSite, ProjetoSite, SecaoSite
from .servicos_estrutura import (
    auditar_integridade_projeto,
    criar_secao_com_container_padrao,
    duplicar_elemento,
    duplicar_secao,
    garantir_pagina_inicial,
    obter_estrutura_projeto,
    reordenar_entidades,
)

logger = logging.getLogger("aplicativos.sites.views_estrutura")


class EstruturaSiteView(RequerAutenticacaoAdministrativaMixin, DetailView):
    """
    Visualização hierárquica em árvore da estrutura do site.

    Exibe Páginas > Seções > Containers > Elementos e permite operações estruturais.
    """

    model = ProjetoSite
    slug_field = "uuid"
    slug_url_kwarg = "uuid"
    template_name = "painel/sites/estrutura.html"
    context_object_name = "site"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        projeto: ProjetoSite = self.object

        # Garante a existência da página inicial caso ainda não exista
        garantir_pagina_inicial(projeto)

        # Obtém árvore completa otimizada (sem N+1)
        estrutura = obter_estrutura_projeto(projeto)
        context["estrutura"] = estrutura
        context["tipos_elementos"] = RegistroElementos.obter_tipos_registrados()
        context["tipos_secao"] = SecaoSite.Tipo.choices
        context["tipos_layout"] = ContainerSite.TipoLayout.choices
        context["anomalias"] = auditar_integridade_projeto(projeto)
        context["titulo_pagina"] = f"Estrutura: {projeto.nome}"
        return context


class EstruturaSiteJsonView(RequerAutenticacaoAdministrativaMixin, View):
    """Retorna a árvore estrutural do projeto formatada em JSON."""

    def get(self, request: HttpRequest, uuid: str) -> JsonResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        apenas_ativos = request.GET.get("apenas_ativos", "0") in ("1", "true", "True")
        dados = obter_estrutura_projeto(projeto, apenas_ativos=apenas_ativos)
        return JsonResponse(dados, json_dumps_params={"ensure_ascii": False, "indent": 2})


class PaginaCriarView(RequerAutenticacaoAdministrativaMixin, View):
    """Cria uma nova página dentro do projeto com validação de unicidade de slug."""

    def post(self, request: HttpRequest, uuid: str) -> HttpResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        titulo = request.POST.get("titulo", "").strip()
        slug_informado = request.POST.get("slug", "").strip()

        if not titulo:
            messages.error(request, "O título da página é obrigatório.")
            return redirect("painel:site_estrutura", uuid=projeto.uuid)

        slug_base = slugify(slug_informado) if slug_informado else slugify(titulo)
        if not slug_base:
            slug_base = "pagina"

        # Garante slug único dentro do projeto
        candidato = slug_base
        contador = 2
        while PaginaSite.objects.filter(projeto=projeto, slug=candidato).exists():
            candidato = f"{slug_base}-{contador}"
            contador += 1

        maior_ordem = projeto.paginas.aggregate(max_ordem=Max("ordem"))["max_ordem"] or 0

        with transaction.atomic():
            nova_pagina = PaginaSite.objects.create(
                projeto=projeto,
                titulo=titulo,
                slug=candidato,
                ordem=maior_ordem + 10,
                eh_inicial=False,
                ativa=True,
            )
            # Cria automaticamente uma seção padrão com container
            criar_secao_com_container_padrao(nova_pagina, nome_interno="Seção Principal")

        messages.success(request, f"Página '{nova_pagina.titulo}' criada com sucesso.")
        return redirect("painel:site_estrutura", uuid=projeto.uuid)


class SecaoCriarView(RequerAutenticacaoAdministrativaMixin, View):
    """Cria uma nova seção vinculada a uma página com container padrão."""

    def post(self, request: HttpRequest, uuid: str) -> HttpResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        pagina_id = request.POST.get("pagina_id")
        nome_interno = request.POST.get("nome_interno", "").strip() or "Nova Seção"
        tipo = request.POST.get("tipo", SecaoSite.Tipo.NORMAL)

        pagina = get_object_or_404(PaginaSite, id=pagina_id, projeto=projeto)

        secao, _ = criar_secao_com_container_padrao(
            pagina=pagina,
            nome_interno=nome_interno,
            tipo=tipo,
        )

        messages.success(request, f"Seção '{secao.nome_interno}' adicionada com sucesso.")
        return redirect("painel:site_estrutura", uuid=projeto.uuid)


class SecaoDuplicarView(RequerAutenticacaoAdministrativaMixin, View):
    """Duplica profundamente uma seção existente."""

    def post(self, request: HttpRequest, uuid: str, secao_id: int) -> HttpResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        secao = get_object_or_404(SecaoSite, id=secao_id, pagina__projeto=projeto)

        nova_secao = duplicar_secao(secao)
        messages.success(request, f"Seção '{nova_secao.nome_interno}' duplicada com sucesso.")
        return redirect("painel:site_estrutura", uuid=projeto.uuid)


class SecaoExcluirView(RequerAutenticacaoAdministrativaMixin, View):
    """Exclui uma seção e toda a sua árvore em cascata."""

    def post(self, request: HttpRequest, uuid: str, secao_id: int) -> HttpResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        secao = get_object_or_404(SecaoSite, id=secao_id, pagina__projeto=projeto)

        nome = secao.nome_interno
        secao.delete()
        messages.success(request, f"Seção '{nome}' excluída com sucesso.")
        return redirect("painel:site_estrutura", uuid=projeto.uuid)


class ContainerCriarView(RequerAutenticacaoAdministrativaMixin, View):
    """Cria um novo container dentro de uma seção ou como filho de outro container."""

    def post(self, request: HttpRequest, uuid: str) -> HttpResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        secao_id = request.POST.get("secao_id")
        parent_id = request.POST.get("parent_id") or None
        tipo_layout = request.POST.get("tipo_layout", ContainerSite.TipoLayout.STACK)

        secao = get_object_or_404(SecaoSite, id=secao_id, pagina__projeto=projeto)

        parent_container = None
        if parent_id:
            parent_container = get_object_or_404(ContainerSite, id=parent_id, secao=secao)

        maior_ordem = (
            secao.containers.filter(parent=parent_container).aggregate(max_ordem=Max("ordem"))[
                "max_ordem"
            ]
            or 0
        )

        try:
            container = ContainerSite(
                secao=secao,
                parent=parent_container,
                tipo_layout=tipo_layout,
                ordem=maior_ordem + 10,
                ativo=True,
            )
            container.full_clean()
            container.save()
            messages.success(request, "Container adicionado com sucesso.")
        except ValidationError as e:
            messages.error(
                request, f"Erro ao criar container: {e.message if hasattr(e, 'message') else e}"
            )

        return redirect("painel:site_estrutura", uuid=projeto.uuid)


class ElementoCriarView(RequerAutenticacaoAdministrativaMixin, View):
    """Cria um novo elemento dentro de um container com validação contra o registry."""

    def post(self, request: HttpRequest, uuid: str) -> HttpResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        container_id = request.POST.get("container_id")
        tipo_elemento = request.POST.get("tipo", "").strip().upper()

        container = get_object_or_404(
            ContainerSite, id=container_id, secao__pagina__projeto=projeto
        )

        definicao = RegistroElementos.obter(tipo_elemento)
        if not definicao:
            messages.error(request, f"Tipo de elemento '{tipo_elemento}' não é válido.")
            return redirect("painel:site_estrutura", uuid=projeto.uuid)

        # Se houver payload de conteúdo via JSON informado no form, parseia; senão, usa defaults do tipo
        conteudo_raw = request.POST.get("conteudo")
        if conteudo_raw:
            try:
                conteudo = json.loads(conteudo_raw)
            except json.JSONDecodeError:
                messages.error(request, "JSON de conteúdo inválido.")
                return redirect("painel:site_estrutura", uuid=projeto.uuid)
        else:
            conteudo = definicao.obter_conteudo_padrao()

        maior_ordem = container.elementos.aggregate(max_ordem=Max("ordem"))["max_ordem"] or 0

        try:
            elemento = ElementoSite(
                container=container,
                tipo=tipo_elemento,
                ordem=maior_ordem + 10,
                conteudo=conteudo,
                estilos={"base": {}, "desktop": {}},
                ativo=True,
            )
            elemento.full_clean()
            elemento.save()
            messages.success(request, f"Elemento '{definicao.nome}' criado com sucesso.")
        except ValidationError as e:
            msg = e.messages[0] if hasattr(e, "messages") else str(e)
            messages.error(request, f"Erro de validação do elemento: {msg}")

        return redirect("painel:site_estrutura", uuid=projeto.uuid)


class ElementoDuplicarView(RequerAutenticacaoAdministrativaMixin, View):
    """Duplica um elemento dentro do seu container."""

    def post(self, request: HttpRequest, uuid: str, elemento_id: int) -> HttpResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        elemento = get_object_or_404(
            ElementoSite, id=elemento_id, container__secao__pagina__projeto=projeto
        )

        novo_elemento = duplicar_elemento(elemento)
        messages.success(request, f"Elemento #{novo_elemento.id} duplicado com sucesso.")
        return redirect("painel:site_estrutura", uuid=projeto.uuid)


class ElementoExcluirView(RequerAutenticacaoAdministrativaMixin, View):
    """Exclui um elemento."""

    def post(self, request: HttpRequest, uuid: str, elemento_id: int) -> HttpResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        elemento = get_object_or_404(
            ElementoSite, id=elemento_id, container__secao__pagina__projeto=projeto
        )

        elemento.delete()
        messages.success(request, "Elemento excluído com sucesso.")
        return redirect("painel:site_estrutura", uuid=projeto.uuid)


class ReordenarNiveisView(RequerAutenticacaoAdministrativaMixin, View):
    """Reordena entidades irmãs atômica e seguramente."""

    def post(self, request: HttpRequest, uuid: str) -> HttpResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        tipo_entidade = request.POST.get("tipo_entidade", "").strip().lower()
        pai_id = request.POST.get("pai_id")
        ids_raw = request.POST.get("ids", "")

        try:
            ids = [int(i.strip()) for i in ids_raw.split(",") if i.strip()]
        except ValueError:
            messages.error(request, "Lista de IDs inválida para reordenação.")
            return redirect("painel:site_estrutura", uuid=projeto.uuid)

        if not ids:
            messages.warning(request, "Nenhum ID fornecido para reordenar.")
            return redirect("painel:site_estrutura", uuid=projeto.uuid)

        try:
            if tipo_entidade == "secao":
                pagina = get_object_or_404(PaginaSite, id=pai_id, projeto=projeto)
                reordenar_entidades(SecaoSite, ids, "pagina_id", pagina.id)
            elif tipo_entidade == "container":
                secao = get_object_or_404(SecaoSite, id=pai_id, pagina__projeto=projeto)
                reordenar_entidades(ContainerSite, ids, "secao_id", secao.id)
            elif tipo_entidade == "elemento":
                container = get_object_or_404(
                    ContainerSite, id=pai_id, secao__pagina__projeto=projeto
                )
                reordenar_entidades(ElementoSite, ids, "container_id", container.id)
            elif tipo_entidade == "pagina":
                reordenar_entidades(PaginaSite, ids, "projeto_id", projeto.id)
            else:
                messages.error(request, f"Tipo de entidade '{tipo_entidade}' desconhecido.")
                return redirect("painel:site_estrutura", uuid=projeto.uuid)

            messages.success(request, "Ordem atualizada com sucesso.")
        except ValidationError as e:
            messages.error(request, f"Erro na reordenação: {e}")

        return redirect("painel:site_estrutura", uuid=projeto.uuid)
