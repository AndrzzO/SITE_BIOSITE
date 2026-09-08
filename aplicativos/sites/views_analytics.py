"""
Views para ingestão de eventos e dashboards analíticos (Prompt 11).

REGRAS ARQUITETURAIS:
1. Ingestão Segura e Cookieless: Endpoint público /e/ aceita apenas POST com token assinado,
   rejeita payloads grandes (>2KB) e responde com HTTP 204 No Content.
2. CSRF Exempt estrito: Aplicado EXCLUSIVAMENTE ao endpoint de ingestão de beacon; todas as
   outras rotas da plataforma mantêm proteção CSRF integral.
3. Dashboards Administrativos: Acesso restrito a operadores autenticados
   (RequerAutenticacaoAdministrativaMixin).
4. Sem Mock Data: Se não houver eventos no banco, exibe 0 e estado vazio informativo.
5. Honestidade Semântica: Termos corretos (Visualizações, Cliques, CTR aproximado), nunca
   "pessoas", "vendas" ou "visitas únicas".
"""

import json
import logging
from typing import Any

from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    JsonResponse,
)
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import DetailView, TemplateView

from aplicativos.administracao.views import RequerAutenticacaoAdministrativaMixin

from .models import EventoAnalitico, LinkInteligente, ProjetoSite, PublicacaoSite
from .servicos_analytics import (
    obter_metricas_globais,
    obter_metricas_link,
    obter_metricas_projeto,
    obter_metricas_smart_links_projeto,
    obter_origens_acesso_projeto,
    obter_serie_temporal_projeto,
    obter_top_componentes_projeto,
    registrar_evento,
    validar_token_evento,
)

logger = logging.getLogger("aplicativos.sites.views_analytics")


@method_decorator(csrf_exempt, name="dispatch")
class AnalyticsIngestionView(View):
    """
    Endpoint público de alta performance para ingestão de beacons analíticos (/e/).
    """

    http_method_names = ["post"]

    def post(self, request: HttpRequest) -> HttpResponse:
        # 1. Limite estrito de tamanho de payload (máximo 2048 bytes)
        content_length = request.META.get("CONTENT_LENGTH")
        if content_length:
            try:
                if int(content_length) > 2048:
                    return HttpResponseBadRequest("Payload excede o limite máximo permitido.")
            except ValueError:
                return HttpResponseBadRequest("Tamanho de payload inválido.")

        if len(request.body) > 2048:
            return HttpResponseBadRequest("Payload excede o limite máximo permitido.")

        # 2. Parsing do corpo JSON
        try:
            dados_req = json.loads(request.body.decode("utf-8") or "{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            return HttpResponseBadRequest("Formato JSON inválido.")

        token = dados_req.get("token")
        if not token or not isinstance(token, str):
            return HttpResponseBadRequest("Token ausente ou inválido.")

        # 3. Validação do token criptográfico assinado
        dados_token = validar_token_evento(token)
        if not dados_token:
            return HttpResponseBadRequest("Token analítico inválido ou expirado.")

        projeto_id = dados_token.get("p")
        publicacao_id = dados_token.get("v")
        tipo_evento = dados_token.get("t")

        if not projeto_id or not tipo_evento:
            return HttpResponseBadRequest("Parâmetros do token incompletos.")

        projeto = ProjetoSite.objects.filter(id=projeto_id).first()
        if not projeto:
            return HttpResponseBadRequest("ProjetoSite não encontrado.")

        publicacao = None
        if publicacao_id:
            publicacao = PublicacaoSite.objects.filter(id=publicacao_id, projeto=projeto).first()

        # 4. Registro com proteção fail-open
        if tipo_evento == EventoAnalitico.TipoEvento.PAGE_VIEW:
            pagina_slug = dados_token.get("pg")
            registrar_evento(
                projeto=projeto,
                publicacao=publicacao,
                tipo_evento=EventoAnalitico.TipoEvento.PAGE_VIEW,
                origem=EventoAnalitico.OrigemAcesso.DIRETO_DESCONHECIDO,
                pagina_uuid=pagina_slug,
                request=request,
            )
        elif tipo_evento == EventoAnalitico.TipoEvento.COMPONENT_CLICK:
            tipo_componente = dados_token.get("c")
            elemento_uuid = dados_token.get("e")
            subitem_id = dados_token.get("s")
            registrar_evento(
                projeto=projeto,
                publicacao=publicacao,
                tipo_evento=EventoAnalitico.TipoEvento.COMPONENT_CLICK,
                origem=EventoAnalitico.OrigemAcesso.INTERNO,
                tipo_componente=tipo_componente,
                elemento_uuid=elemento_uuid,
                subitem_id=subitem_id,
                request=request,
            )

        # 5. Retorna HTTP 204 No Content sem criar cookies ou expor dados
        response = HttpResponse(status=204)
        response["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response["Pragma"] = "no-cache"
        return response


class AnalyticsGlobalView(RequerAutenticacaoAdministrativaMixin, TemplateView):
    """
    Dashboard administrativo com a visão analítica global da plataforma (/painel/analytics/).
    """

    template_name = "painel/analytics/global.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        periodo = self.request.GET.get("periodo", "30d")
        data_inicio = self.request.GET.get("data_inicio")
        data_fim = self.request.GET.get("data_fim")

        metricas = obter_metricas_globais(
            periodo=periodo, data_inicio=data_inicio, data_fim=data_fim
        )

        context.update(
            {
                "metricas": metricas,
                "periodo_atual": periodo,
                "data_inicio_atual": data_inicio or "",
                "data_fim_atual": data_fim or "",
            }
        )
        return context


class ProjetoAnalyticsView(RequerAutenticacaoAdministrativaMixin, DetailView):
    """
    Dashboard analítico dedicado para um BioSite específico (/painel/sites/<uuid>/analytics/).
    """

    model = ProjetoSite
    template_name = "painel/analytics/projeto.html"
    context_object_name = "site"

    def get_object(self, queryset=None) -> ProjetoSite:
        identificador = self.kwargs.get("uuid") or self.kwargs.get("pk")
        return get_object_or_404(
            ProjetoSite.objects.select_related("cliente", "publicacao_ativa"),
            uuid=identificador,
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        projeto = self.object

        periodo = self.request.GET.get("periodo", "30d")
        data_inicio = self.request.GET.get("data_inicio")
        data_fim = self.request.GET.get("data_fim")
        versao_param = self.request.GET.get("versao")

        versao = None
        if versao_param and versao_param.isdigit():
            versao = int(versao_param)

        metricas = obter_metricas_projeto(
            projeto=projeto,
            periodo=periodo,
            data_inicio=data_inicio,
            data_fim=data_fim,
            versao=versao,
        )
        serie_temporal = obter_serie_temporal_projeto(
            projeto=projeto,
            periodo=periodo,
            data_inicio=data_inicio,
            data_fim=data_fim,
            versao=versao,
        )
        origens = obter_origens_acesso_projeto(
            projeto=projeto,
            periodo=periodo,
            data_inicio=data_inicio,
            data_fim=data_fim,
            versao=versao,
        )
        top_componentes = obter_top_componentes_projeto(
            projeto=projeto,
            periodo=periodo,
            data_inicio=data_inicio,
            data_fim=data_fim,
            versao=versao,
        )
        smart_links = obter_metricas_smart_links_projeto(
            projeto=projeto,
            periodo=periodo,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )

        versoes_disponiveis = (
            projeto.publicacoes.all()
            .values("numero_versao", "publicado_em")
            .order_by("-numero_versao")
        )

        context.update(
            {
                "metricas": metricas,
                "serie_temporal": serie_temporal,
                "origens": origens,
                "top_componentes": top_componentes,
                "smart_links": smart_links,
                "versoes_disponiveis": versoes_disponiveis,
                "versao_selecionada": versao,
                "periodo_atual": periodo,
                "data_inicio_atual": data_inicio or "",
                "data_fim_atual": data_fim or "",
            }
        )
        return context


class LinkInteligenteMetricasJsonView(RequerAutenticacaoAdministrativaMixin, View):
    """Retorna métricas de um Link Inteligente específico em JSON para modais."""

    def get(self, request: HttpRequest, pk: str) -> JsonResponse:
        link = get_object_or_404(LinkInteligente, uuid=pk)
        metricas = obter_metricas_link(link)
        return JsonResponse(
            {
                "sucesso": True,
                "link": {
                    "id": link.id,
                    "uuid": str(link.uuid),
                    "nome": link.nome,
                    "tipo": link.tipo,
                    "tipo_display": link.get_tipo_display(),
                    "token_mascarado": link.token_mascarado(),
                },
                "metricas": metricas,
            }
        )
