"""Views e endpoints do Editor Visual Mobile-First (Prompt 5)."""

import json
import logging
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from django.views import View
from django.views.generic import DetailView

from aplicativos.administracao.permissoes import RequerAutenticacaoAdministrativaMixin

from .elementos import RegistroElementos
from .elementos.base import calcular_contraste_wcag
from .models import (
    ConfiguracaoVisualProjeto,
    ContainerSite,
    ElementoSite,
    MidiaSite,
    PaginaSite,
    ProjetoSite,
    SecaoSite,
    garantir_configuracao_visual,
)
from .renderer import RenderizadorBioSite
from .servicos_estrutura import (
    atualizar_conteudo_e_estilos_elemento,
    atualizar_propriedades_secao,
    criar_secao_com_container_padrao,
    duplicar_elemento,
    duplicar_secao,
    garantir_pagina_inicial,
    mover_elemento,
    obter_estrutura_projeto,
    reordenar_entidades,
)
from .servicos_midia import criar_midia_projeto

logger = logging.getLogger("aplicativos.sites.views_editor")

PRESETS_DESIGN = [
    {
        "id": "clean_light",
        "nome": "Clean Light",
        "cor_primaria": "#2563eb",
        "cor_secundaria": "#38bdf8",
        "cor_fundo": "#ffffff",
        "cor_superficie": "#f8fafc",
        "cor_texto": "#0f172a",
        "cor_texto_secundario": "#64748b",
        "fonte_principal": "Inter, sans-serif",
        "fonte_titulos": "Inter, sans-serif",
        "radius_padrao": "12px",
        "sombra_padrao": "suave",
    },
    {
        "id": "dark_premium",
        "nome": "Dark Premium",
        "cor_primaria": "#38bdf8",
        "cor_secundaria": "#818cf8",
        "cor_fundo": "#0b0f19",
        "cor_superficie": "#111827",
        "cor_texto": "#f8fafc",
        "cor_texto_secundario": "#94a3b8",
        "fonte_principal": "Plus Jakarta Sans, sans-serif",
        "fonte_titulos": "Plus Jakarta Sans, sans-serif",
        "radius_padrao": "16px",
        "sombra_padrao": "glow",
    },
    {
        "id": "minimalist_mono",
        "nome": "Minimalist Black & White",
        "cor_primaria": "#000000",
        "cor_secundaria": "#52525b",
        "cor_fundo": "#ffffff",
        "cor_superficie": "#f4f4f5",
        "cor_texto": "#18181b",
        "cor_texto_secundario": "#71717a",
        "fonte_principal": "Roboto, sans-serif",
        "fonte_titulos": "Montserrat, sans-serif",
        "radius_padrao": "8px",
        "sombra_padrao": "suave",
    },
    {
        "id": "pastel_elegante",
        "nome": "Editorial & Elegante",
        "cor_primaria": "#854d0e",
        "cor_secundaria": "#ca8a04",
        "cor_fundo": "#fefce8",
        "cor_superficie": "#fef9c3",
        "cor_texto": "#422006",
        "cor_texto_secundario": "#713f12",
        "fonte_principal": "Inter, sans-serif",
        "fonte_titulos": "Playfair Display, serif",
        "radius_padrao": "8px",
        "sombra_padrao": "media",
    },
    {
        "id": "emerald_pro",
        "nome": "Emerald Professional",
        "cor_primaria": "#059669",
        "cor_secundaria": "#34d399",
        "cor_fundo": "#f0fdf4",
        "cor_superficie": "#dcfce7",
        "cor_texto": "#064e3b",
        "cor_texto_secundario": "#065f46",
        "fonte_principal": "Poppins, sans-serif",
        "fonte_titulos": "Poppins, sans-serif",
        "radius_padrao": "20px",
        "sombra_padrao": "suave",
    },
]


def _extrair_json_body(request: HttpRequest) -> dict[str, Any]:
    """Auxiliar para parsear payload de corpo JSON ou POST padrão."""
    if request.body and request.content_type == "application/json":
        try:
            return json.loads(request.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
    return request.POST.dict()


class EditorStudioView(RequerAutenticacaoAdministrativaMixin, DetailView):
    """
    Interface central do Editor Visual Mobile-First (Canva + Google Sites).

    Carrega por padrão a página inicial do projeto no canvas smartphone de 390px.
    """

    model = ProjetoSite
    slug_field = "uuid"
    slug_url_kwarg = "uuid"
    template_name = "painel/sites/editor.html"
    context_object_name = "site"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        projeto: ProjetoSite = self.object

        # Garante a existência da página inicial
        home = garantir_pagina_inicial(projeto)

        # Seleciona página solicitada ou cai na home
        pagina_id = self.request.GET.get("pagina")
        if pagina_id:
            pagina = get_object_or_404(PaginaSite, id=pagina_id, projeto=projeto)
        else:
            pagina = home

        renderer = RenderizadorBioSite(modo="editor")
        html_canvas = renderer.renderizar_pagina(pagina)

        context["pagina_atual"] = pagina
        context["paginas"] = projeto.paginas.order_by("ordem")
        context["tipos_elementos"] = RegistroElementos.listar_tipos()
        context["tipos_secao"] = SecaoSite.Tipo.choices
        context["tipos_layout"] = ContainerSite.TipoLayout.choices
        context["html_canvas"] = html_canvas
        context["titulo_pagina"] = f"Editor: {projeto.nome}"

        config_visual = garantir_configuracao_visual(projeto)
        context["config_visual"] = config_visual
        context["presets_design"] = PRESETS_DESIGN
        context["fontes_disponiveis"] = ConfiguracaoVisualProjeto.FONTE_CHOICES
        context["midias"] = projeto.midias.order_by("-criado_em")[:30]
        return context


class EditorDadosJsonView(RequerAutenticacaoAdministrativaMixin, View):
    """Retorna dados completos do projeto, página e definições do registry em JSON."""

    def get(self, request: HttpRequest, uuid: str) -> JsonResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        pagina_id = request.GET.get("pagina")
        if pagina_id:
            pagina = get_object_or_404(PaginaSite, id=pagina_id, projeto=projeto)
        else:
            pagina = garantir_pagina_inicial(projeto)

        estrutura = obter_estrutura_projeto(projeto)
        renderer = RenderizadorBioSite(modo="editor")
        config_visual = garantir_configuracao_visual(projeto)

        dados = {
            "ok": True,
            "projeto": {
                "id": projeto.id,
                "uuid": str(projeto.uuid),
                "nome": projeto.nome,
                "slug": projeto.slug,
                "status": projeto.status,
            },
            "pagina_atual": {
                "id": pagina.id,
                "uuid": str(pagina.uuid),
                "titulo": pagina.titulo,
                "slug": pagina.slug,
                "eh_inicial": pagina.eh_inicial,
            },
            "paginas": [
                {
                    "id": p.id,
                    "titulo": p.titulo,
                    "slug": p.slug,
                    "eh_inicial": p.eh_inicial,
                }
                for p in projeto.paginas.order_by("ordem")
            ],
            "catalogo_elementos": RegistroElementos.listar_tipos(),
            "configuracao_visual": {
                "cor_primaria": config_visual.cor_primaria,
                "cor_secundaria": config_visual.cor_secundaria,
                "cor_fundo": config_visual.cor_fundo,
                "cor_superficie": config_visual.cor_superficie,
                "cor_texto": config_visual.cor_texto,
                "cor_texto_secundario": config_visual.cor_texto_secundario,
                "fonte_principal": config_visual.fonte_principal,
                "fonte_titulos": config_visual.fonte_titulos,
                "radius_padrao": config_visual.radius_padrao,
                "sombra_padrao": config_visual.sombra_padrao,
                "largura_maxima_mobile": config_visual.largura_maxima_mobile,
                "tokens": config_visual.obter_tokens_css(),
            },
            "presets_design": PRESETS_DESIGN,
            "fontes_disponiveis": [
                {"valor": k, "nome": v} for k, v in ConfiguracaoVisualProjeto.FONTE_CHOICES
            ],
            "html_canvas": renderer.renderizar_pagina(pagina),
            "estrutura": estrutura,
        }
        return JsonResponse(dados, json_dumps_params={"ensure_ascii": False})


class EditorVisualConfigSalvarView(RequerAutenticacaoAdministrativaMixin, View):
    """Salva a configuração visual e tokens do Design System do projeto."""

    def post(self, request: HttpRequest, uuid: str) -> JsonResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        payload = _extrair_json_body(request)

        config_visual = garantir_configuracao_visual(projeto)

        campos_permitidos = [
            "cor_primaria",
            "cor_secundaria",
            "cor_fundo",
            "cor_superficie",
            "cor_texto",
            "cor_texto_secundario",
            "fonte_principal",
            "fonte_titulos",
            "radius_padrao",
            "sombra_padrao",
            "largura_maxima_mobile",
        ]

        for campo in campos_permitidos:
            if campo in payload and payload[campo] is not None:
                val = payload[campo]
                if campo == "largura_maxima_mobile":
                    try:
                        val = max(320, min(480, int(val)))
                    except (ValueError, TypeError):
                        val = 390
                setattr(config_visual, campo, val)

        try:
            config_visual.full_clean()
            config_visual.save()
            tokens = config_visual.obter_tokens_css()
            contraste = calcular_contraste_wcag(config_visual.cor_texto, config_visual.cor_fundo)
            return JsonResponse(
                {
                    "ok": True,
                    "tokens": tokens,
                    "bloco_css": config_visual.gerar_bloco_css(),
                    "contraste": contraste,
                }
            )
        except ValidationError as e:
            return JsonResponse({"ok": False, "erro": str(e)}, status=422)


class EditorMidiaUploadView(RequerAutenticacaoAdministrativaMixin, View):
    """Upload e otimização segura de imagens para o projeto."""

    def post(self, request: HttpRequest, uuid: str) -> JsonResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        arquivo = request.FILES.get("arquivo")
        tipo = request.POST.get("tipo", MidiaSite.Tipo.IMAGEM)

        if not arquivo:
            return JsonResponse({"ok": False, "erro": "Nenhum arquivo enviado."}, status=400)

        try:
            midia = criar_midia_projeto(projeto, arquivo, tipo=tipo)
            return JsonResponse(
                {
                    "ok": True,
                    "midia": {
                        "id": midia.id,
                        "uuid": str(midia.uuid),
                        "url": midia.url,
                        "nome": midia.nome_original,
                        "largura": midia.largura,
                        "altura": midia.altura,
                        "tamanho_bytes": midia.tamanho_bytes,
                        "tipo": midia.tipo,
                    },
                }
            )
        except ValidationError as e:
            msg = e.messages[0] if hasattr(e, "messages") else str(e)
            return JsonResponse({"ok": False, "erro": msg}, status=422)


class EditorMidiaListarView(RequerAutenticacaoAdministrativaMixin, View):
    """Lista mídias já enviadas do projeto para seleção no estúdio."""

    def get(self, request: HttpRequest, uuid: str) -> JsonResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        midias = [
            {
                "id": m.id,
                "uuid": str(m.uuid),
                "url": m.url,
                "nome": m.nome_original,
                "largura": m.largura,
                "altura": m.altura,
                "tipo": m.tipo,
            }
            for m in projeto.midias.order_by("-criado_em")[:50]
        ]
        return JsonResponse({"ok": True, "midias": midias})


class EditorElementoSalvarView(RequerAutenticacaoAdministrativaMixin, View):
    """Salva com debounce alterações de conteúdo e/ou estilos de um elemento (Autosave)."""

    def post(self, request: HttpRequest, uuid: str) -> JsonResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        payload = _extrair_json_body(request)

        elemento_id = payload.get("elemento_id")
        if not elemento_id:
            return JsonResponse({"ok": False, "erro": "elemento_id é obrigatório."}, status=400)

        elemento = get_object_or_404(
            ElementoSite, id=elemento_id, container__secao__pagina__projeto=projeto
        )

        conteudo = payload.get("conteudo")
        estilos = payload.get("estilos")

        # Converte string para dict se enviado como form-encoded
        if isinstance(conteudo, str):
            try:
                conteudo = json.loads(conteudo)
            except json.JSONDecodeError:
                return JsonResponse({"ok": False, "erro": "Conteúdo JSON inválido."}, status=400)

        if isinstance(estilos, str):
            try:
                estilos = json.loads(estilos)
            except json.JSONDecodeError:
                return JsonResponse({"ok": False, "erro": "Estilos JSON inválido."}, status=400)

        try:
            elemento = atualizar_conteudo_e_estilos_elemento(
                elemento, conteudo=conteudo, estilos=estilos
            )
            return JsonResponse(
                {
                    "ok": True,
                    "elemento_id": elemento.id,
                    "conteudo": elemento.conteudo,
                    "estilos": elemento.estilos,
                    "atualizado_em": elemento.atualizado_em.isoformat(),
                }
            )
        except ValidationError as e:
            msg = e.messages[0] if hasattr(e, "messages") else str(e)
            return JsonResponse({"ok": False, "erro": msg}, status=422)


class EditorElementoCriarView(RequerAutenticacaoAdministrativaMixin, View):
    """Cria um novo elemento dentro de um container via clique na paleta ou drag-and-drop."""

    def post(self, request: HttpRequest, uuid: str) -> JsonResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        payload = _extrair_json_body(request)

        container_id = payload.get("container_id")
        tipo = payload.get("tipo", "").strip().upper()

        if not container_id or not tipo:
            return JsonResponse(
                {"ok": False, "erro": "container_id e tipo são obrigatórios."}, status=400
            )

        container = get_object_or_404(
            ContainerSite, id=container_id, secao__pagina__projeto=projeto
        )

        definicao = RegistroElementos.obter(tipo)
        if not definicao:
            return JsonResponse(
                {"ok": False, "erro": f"Tipo '{tipo}' não reconhecido."}, status=400
            )

        conteudo = payload.get("conteudo")
        if isinstance(conteudo, str):
            try:
                conteudo = json.loads(conteudo)
            except json.JSONDecodeError:
                conteudo = None

        if not conteudo:
            conteudo = definicao.conteudo_padrao()

        ordem_recebida = payload.get("ordem")
        if ordem_recebida is not None:
            try:
                ordem = int(ordem_recebida)
            except ValueError:
                ordem = None
        else:
            ordem = None

        if ordem is None:
            maior = container.elementos.aggregate(max_ordem=Max("ordem"))["max_ordem"] or 0
            ordem = maior + 10

        try:
            elemento = ElementoSite(
                container=container,
                tipo=tipo,
                ordem=ordem,
                conteudo=conteudo,
                estilos=definicao.estilos_padrao(),
                ativo=True,
            )
            elemento.full_clean()
            elemento.save()

            renderer = RenderizadorBioSite(modo="editor")
            html_elemento = renderer.renderizar_elemento(elemento)

            return JsonResponse(
                {
                    "ok": True,
                    "elemento_id": elemento.id,
                    "tipo": elemento.tipo,
                    "ordem": elemento.ordem,
                    "container_id": container.id,
                    "html": html_elemento,
                    "conteudo": elemento.conteudo,
                    "estilos": elemento.estilos,
                }
            )
        except ValidationError as e:
            msg = e.messages[0] if hasattr(e, "messages") else str(e)
            return JsonResponse({"ok": False, "erro": msg}, status=422)


class EditorElementoMoverView(RequerAutenticacaoAdministrativaMixin, View):
    """Move ou reordena elementos dentro de containers (SortableJS)."""

    def post(self, request: HttpRequest, uuid: str) -> JsonResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        payload = _extrair_json_body(request)

        elemento_id = payload.get("elemento_id")
        novo_container_id = payload.get("novo_container_id")
        ordem_ids = payload.get("ordem_ids", [])

        if not elemento_id:
            return JsonResponse({"ok": False, "erro": "elemento_id obrigatório."}, status=400)

        elemento = get_object_or_404(
            ElementoSite, id=elemento_id, container__secao__pagina__projeto=projeto
        )

        alvo_container = elemento.container
        if novo_container_id:
            alvo_container = get_object_or_404(
                ContainerSite, id=novo_container_id, secao__pagina__projeto=projeto
            )

        try:
            mover_elemento(elemento, alvo_container)

            # Se recebeu nova ordem sequencial dos irmãos, reordena atômica e limpa
            if ordem_ids and isinstance(ordem_ids, list):
                clean_ids = [int(i) for i in ordem_ids if str(i).isdigit()]
                if clean_ids:
                    reordenar_entidades(ElementoSite, clean_ids, "container_id", alvo_container.id)

            return JsonResponse({"ok": True})
        except ValidationError as e:
            return JsonResponse({"ok": False, "erro": str(e)}, status=422)


class EditorElementoDuplicarView(RequerAutenticacaoAdministrativaMixin, View):
    """Duplica um elemento dentro do seu container."""

    def post(self, request: HttpRequest, uuid: str, elemento_id: int) -> JsonResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        elemento = get_object_or_404(
            ElementoSite, id=elemento_id, container__secao__pagina__projeto=projeto
        )

        novo_elem = duplicar_elemento(elemento)
        renderer = RenderizadorBioSite(modo="editor")
        html_elemento = renderer.renderizar_elemento(novo_elem)

        return JsonResponse(
            {
                "ok": True,
                "elemento_id": novo_elem.id,
                "tipo": novo_elem.tipo,
                "container_id": novo_elem.container_id,
                "html": html_elemento,
                "conteudo": novo_elem.conteudo,
                "estilos": novo_elem.estilos,
            }
        )


class EditorElementoExcluirView(RequerAutenticacaoAdministrativaMixin, View):
    """Exclui um elemento."""

    def post(self, request: HttpRequest, uuid: str, elemento_id: int) -> JsonResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        elemento = get_object_or_404(
            ElementoSite, id=elemento_id, container__secao__pagina__projeto=projeto
        )
        elemento.delete()
        return JsonResponse({"ok": True, "elemento_id": elemento_id})


class EditorSecaoCriarView(RequerAutenticacaoAdministrativaMixin, View):
    """Adiciona uma nova seção com container padrão à página ativa."""

    def post(self, request: HttpRequest, uuid: str) -> JsonResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        payload = _extrair_json_body(request)

        pagina_id = payload.get("pagina_id")
        nome_interno = payload.get("nome_interno", "").strip() or "Nova Seção"
        tipo = payload.get("tipo", SecaoSite.Tipo.NORMAL)

        pagina = get_object_or_404(PaginaSite, id=pagina_id, projeto=projeto)

        secao, container = criar_secao_com_container_padrao(
            pagina=pagina,
            nome_interno=nome_interno,
            tipo=tipo,
        )

        renderer = RenderizadorBioSite(modo="editor")
        html_secao = renderer.renderizar_secao(secao)

        return JsonResponse(
            {
                "ok": True,
                "secao_id": secao.id,
                "container_id": container.id,
                "nome_interno": secao.nome_interno,
                "tipo": secao.tipo,
                "ordem": secao.ordem,
                "html": html_secao,
            }
        )


class EditorSecaoMoverView(RequerAutenticacaoAdministrativaMixin, View):
    """Reordena verticalmente as seções de uma página (SortableJS)."""

    def post(self, request: HttpRequest, uuid: str) -> JsonResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        payload = _extrair_json_body(request)

        pagina_id = payload.get("pagina_id")
        ordem_ids = payload.get("ordem_ids", [])

        pagina = get_object_or_404(PaginaSite, id=pagina_id, projeto=projeto)

        if not ordem_ids or not isinstance(ordem_ids, list):
            return JsonResponse({"ok": False, "erro": "Lista de ordem_ids inválida."}, status=400)

        try:
            clean_ids = [int(i) for i in ordem_ids if str(i).isdigit()]
            reordenar_entidades(SecaoSite, clean_ids, "pagina_id", pagina.id)
            return JsonResponse({"ok": True})
        except ValidationError as e:
            return JsonResponse({"ok": False, "erro": str(e)}, status=422)


class EditorSecaoDuplicarView(RequerAutenticacaoAdministrativaMixin, View):
    """Duplica profundamente uma seção."""

    def post(self, request: HttpRequest, uuid: str, secao_id: int) -> JsonResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        secao = get_object_or_404(SecaoSite, id=secao_id, pagina__projeto=projeto)

        nova_s = duplicar_secao(secao)
        renderer = RenderizadorBioSite(modo="editor")
        html_secao = renderer.renderizar_secao(nova_s)

        return JsonResponse(
            {
                "ok": True,
                "secao_id": nova_s.id,
                "nome_interno": nova_s.nome_interno,
                "html": html_secao,
            }
        )


class EditorSecaoExcluirView(RequerAutenticacaoAdministrativaMixin, View):
    """Exclui uma seção e seus containers/elementos."""

    def post(self, request: HttpRequest, uuid: str, secao_id: int) -> JsonResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        secao = get_object_or_404(SecaoSite, id=secao_id, pagina__projeto=projeto)
        secao.delete()
        return JsonResponse({"ok": True, "secao_id": secao_id})


class EditorSecaoPropriedadesView(RequerAutenticacaoAdministrativaMixin, View):
    """Atualiza propriedades de layout/estilo de uma seção."""

    def post(self, request: HttpRequest, uuid: str, secao_id: int) -> JsonResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        secao = get_object_or_404(SecaoSite, id=secao_id, pagina__projeto=projeto)
        payload = _extrair_json_body(request)

        nome_interno = payload.get("nome_interno")
        tipo = payload.get("tipo")
        estilos = payload.get("estilos")

        if isinstance(estilos, str):
            try:
                estilos = json.loads(estilos)
            except json.JSONDecodeError:
                estilos = None

        try:
            secao = atualizar_propriedades_secao(
                secao, nome_interno=nome_interno, tipo=tipo, estilos=estilos
            )
            return JsonResponse(
                {
                    "ok": True,
                    "secao_id": secao.id,
                    "nome_interno": secao.nome_interno,
                    "tipo": secao.tipo,
                    "estilos": secao.estilos,
                }
            )
        except ValidationError as e:
            return JsonResponse({"ok": False, "erro": str(e)}, status=422)


class EditorPaginaCriarView(RequerAutenticacaoAdministrativaMixin, View):
    """Cria uma nova página dentro do projeto e a inicializa com seção padrão."""

    def post(self, request: HttpRequest, uuid: str) -> JsonResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        payload = _extrair_json_body(request)

        titulo = payload.get("titulo", "").strip()
        slug_informado = payload.get("slug", "").strip()

        if not titulo:
            return JsonResponse(
                {"ok": False, "erro": "Título da página é obrigatório."}, status=400
            )

        slug_base = slugify(slug_informado) if slug_informado else slugify(titulo)
        if not slug_base:
            slug_base = "pagina"

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
            criar_secao_com_container_padrao(nova_pagina, nome_interno="Seção Principal")

        return JsonResponse(
            {
                "ok": True,
                "pagina_id": nova_pagina.id,
                "titulo": nova_pagina.titulo,
                "slug": nova_pagina.slug,
            }
        )


class PreviewSiteView(RequerAutenticacaoAdministrativaMixin, DetailView):
    """
    Visualização fiel e completa do rascunho do BioSite.

    Garante 100% de paridade com o canvas do editor, renderizando
    HTML e CSS limpos, sem controles ou wrappers administrativos.
    """

    model = ProjetoSite
    slug_field = "uuid"
    slug_url_kwarg = "uuid"
    template_name = "painel/sites/preview.html"
    context_object_name = "site"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        projeto: ProjetoSite = self.object

        pagina_id = self.request.GET.get("pagina")
        if pagina_id:
            pagina = get_object_or_404(PaginaSite, id=pagina_id, projeto=projeto)
        else:
            pagina = garantir_pagina_inicial(projeto)

        renderer = RenderizadorBioSite(modo="preview")
        html_preview = renderer.renderizar_pagina(pagina)

        context["pagina_atual"] = pagina
        context["paginas"] = projeto.paginas.order_by("ordem")
        context["html_preview"] = html_preview
        context["titulo_pagina"] = f"Preview: {projeto.nome}"
        return context
