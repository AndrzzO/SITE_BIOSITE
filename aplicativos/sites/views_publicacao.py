"""
Views administrativas para o ciclo de vida de publicação, histórico, rollback e validação (Prompt 8).
"""

import json
import logging
from typing import Any

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView

from aplicativos.administracao.permissoes import RequerAutenticacaoAdministrativaMixin

from .models import ProjetoSite, PublicacaoSite
from .renderer import RenderizadorBioSite
from .servicos_publicacao import (
    despublicar_projeto,
    publicar_projeto,
    restaurar_versao_no_editor,
    rollback_publicacao,
    validar_pre_publicacao,
    verificar_alteracoes_pendentes,
)

logger = logging.getLogger("aplicativos.sites.views_publicacao")


def _extrair_payload(request: HttpRequest) -> dict[str, Any]:
    if request.body and request.content_type == "application/json":
        try:
            return json.loads(request.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
    return request.POST.dict()


class ValidarPrePublicacaoView(RequerAutenticacaoAdministrativaMixin, View):
    """Executa checagem pré-publicação do rascunho e retorna erros e avisos."""

    def get(self, request: HttpRequest, uuid: str) -> JsonResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        valido, erros, avisos = validar_pre_publicacao(projeto)
        return JsonResponse(
            {
                "ok": True,
                "valido": valido,
                "erros": erros,
                "avisos": avisos,
                "total_erros": len(erros),
                "total_avisos": len(avisos),
            }
        )


class PublicarProjetoView(RequerAutenticacaoAdministrativaMixin, View):
    """
    Endpoint assíncrono para publicar o rascunho atual.
    Cria uma nova versão imutável estável (v1, v2...) e coloca no ar.
    """

    def post(self, request: HttpRequest, uuid: str) -> JsonResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        payload = _extrair_payload(request)
        forcar = payload.get("forcar", False)
        if isinstance(forcar, str):
            forcar = forcar.lower() in ("true", "1", "t", "sim")

        try:
            publicacao = publicar_projeto(projeto, usuario=request.user, forcar=forcar)
            url_publica = projeto.obter_url_publica(request)
            return JsonResponse(
                {
                    "ok": True,
                    "esta_publicado": True,
                    "versao": publicacao.numero_versao,
                    "hash": publicacao.hash_conteudo[:8],
                    "publicado_em": publicacao.publicado_em.strftime("%d/%m/%Y às %H:%M"),
                    "url_publica": url_publica,
                    "mensagem": f"Site publicado com sucesso na versão v{publicacao.numero_versao}!",
                }
            )
        except ValidationError as e:
            msg = str(e)
            if hasattr(e, "messages") and e.messages:
                msg = "; ".join(e.messages)
            return JsonResponse({"ok": False, "erro": msg}, status=422)
        except Exception as e:
            logger.exception("Erro inesperado ao publicar projeto %s: %s", uuid, e)
            return JsonResponse(
                {"ok": False, "erro": f"Erro interno ao processar publicação: {e}"},
                status=500,
            )


class PublicacaoStatusView(RequerAutenticacaoAdministrativaMixin, View):
    """Retorna o estado de publicação e sincronização do rascunho vs produção."""

    def get(self, request: HttpRequest, uuid: str) -> JsonResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        esta_publicado = projeto.esta_publicado()
        versao_ativa = projeto.publicacao_ativa.numero_versao if projeto.publicacao_ativa else None
        pendente = verificar_alteracoes_pendentes(projeto)
        url_publica = projeto.obter_url_publica(request) if esta_publicado else ""

        return JsonResponse(
            {
                "ok": True,
                "publicado": esta_publicado,
                "versao_atual": versao_ativa,
                "alteracoes_pendentes": pendente,
                "url_publica": url_publica,
                "status_label": (
                    "Publicado • Alterações não publicadas"
                    if (esta_publicado and pendente)
                    else ("Publicado" if esta_publicado else "Rascunho")
                ),
            }
        )


class PublicacoesHistoricoView(RequerAutenticacaoAdministrativaMixin, View):
    """Lista as versões publicadas do projeto."""

    def get(self, request: HttpRequest, uuid: str) -> JsonResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        publicacoes = projeto.publicacoes.all().order_by("-numero_versao")

        dados = [
            {
                "id": p.id,
                "uuid": str(p.uuid),
                "numero_versao": p.numero_versao,
                "versao_label": f"v{p.numero_versao}",
                "hash_curto": p.hash_conteudo[:8],
                "publicado_em": p.publicado_em.strftime("%d/%m/%Y às %H:%M"),
                "autor": p.publicado_por.get_full_name() or p.publicado_por.username
                if p.publicado_por
                else "Operador",
                "ativa": p.ativa,
                "url_preview": reverse(
                    "painel:publicacao_preview",
                    kwargs={"uuid": projeto.uuid, "versao": p.numero_versao},
                ),
            }
            for p in publicacoes
        ]

        return JsonResponse({"ok": True, "publicacoes": dados})


class PublicacaoPreviewView(RequerAutenticacaoAdministrativaMixin, DetailView):
    """
    Visualização isolada de uma versão histórica de publicação em viewport de smartphone (390px).
    Garante 'noindex, nofollow' estrito e renderiza em memória sem afetar o rascunho.
    """

    model = PublicacaoSite
    template_name = (
        "painel/templates/preview.html"  # Reutiliza o mesmo shell de simulator do Prompt 7
    )
    context_object_name = "publicacao"

    def get_object(self, queryset=None):
        projeto_uuid = self.kwargs.get("uuid")
        versao = self.kwargs.get("versao")
        return get_object_or_404(
            PublicacaoSite,
            projeto__uuid=projeto_uuid,
            numero_versao=versao,
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        publicacao: PublicacaoSite = self.object
        projeto = publicacao.projeto

        renderer = RenderizadorBioSite(modo="preview")
        html_preview = renderer.renderizar_snapshot(publicacao.snapshot)

        context["html_preview"] = html_preview
        context["titulo_pagina"] = f"{projeto.nome} — Versão v{publicacao.numero_versao}" + (
            " (Atual no Ar)" if publicacao.ativa else " (Histórico)"
        )
        context["template"] = type(
            "FakeTemplate",
            (),
            {
                "nome": f"{projeto.nome} (v{publicacao.numero_versao})",
                "uuid": projeto.uuid,
                "get_categoria_display": lambda: (
                    f"v{publicacao.numero_versao}" + (" • NO AR" if publicacao.ativa else "")
                ),
            },
        )()
        context["is_publicacao_preview"] = True
        context["versao_numero"] = publicacao.numero_versao
        context["versao_ativa"] = publicacao.ativa
        context["projeto_uuid"] = str(projeto.uuid)
        return context


class PublicacaoRollbackView(RequerAutenticacaoAdministrativaMixin, View):
    """
    Executa rollback seguro para uma versão histórica selecionada.
    Gera uma nova versão com o conteúdo daquela versão antiga e a torna ativa no ar.
    """

    def post(self, request: HttpRequest, uuid: str, versao: int) -> HttpResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        publicacao_alvo = get_object_or_404(PublicacaoSite, projeto=projeto, numero_versao=versao)

        try:
            nova_pub = rollback_publicacao(
                projeto=projeto,
                publicacao_alvo=publicacao_alvo,
                usuario=request.user,
            )
            msg = f"Rollback realizado com sucesso! O site foi restaurado para a versão v{publicacao_alvo.numero_versao} (agora no ar como v{nova_pub.numero_versao})."

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "ok": True,
                        "nova_versao": nova_pub.numero_versao,
                        "mensagem": msg,
                        "url_publica": projeto.obter_url_publica(request),
                    }
                )

            messages.success(request, msg)
            return redirect("painel:site_detalhe", uuid=projeto.uuid)
        except ValidationError as e:
            msg_erro = str(e)
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"ok": False, "erro": msg_erro}, status=422)
            messages.error(request, msg_erro)
            return redirect("painel:site_detalhe", uuid=projeto.uuid)


class DespublicarProjetoView(RequerAutenticacaoAdministrativaMixin, View):
    """Despublica o site imediatamente, preservando todo o histórico de publicações."""

    def post(self, request: HttpRequest, uuid: str) -> HttpResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)

        despublicar_projeto(projeto, usuario=request.user)
        msg = f"O site '{projeto.nome}' foi despublicado com sucesso e não está mais visível para o público."

        if request.headers.get(
            "X-Requested-With"
        ) == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", ""):
            return JsonResponse({"ok": True, "esta_publicado": False, "mensagem": msg})

        messages.success(request, msg)
        return redirect("painel:site_detalhe", uuid=projeto.uuid)


class PublicacaoRestaurarEditorView(RequerAutenticacaoAdministrativaMixin, View):
    """Substitui o rascunho em edição no editor pelo snapshot de uma versão publicada."""

    def post(self, request: HttpRequest, uuid: str, versao: int) -> JsonResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        publicacao = get_object_or_404(PublicacaoSite, projeto=projeto, numero_versao=versao)

        try:
            restaurar_versao_no_editor(projeto, publicacao)
            return JsonResponse(
                {
                    "ok": True,
                    "mensagem": f"O editor foi sincronizado com o conteúdo da versão v{versao}!",
                }
            )
        except ValidationError as e:
            return JsonResponse({"ok": False, "erro": str(e)}, status=422)
        except Exception as e:
            logger.exception("Erro ao restaurar versão no editor: %s", e)
            return JsonResponse({"ok": False, "erro": f"Erro inesperado: {e}"}, status=500)
