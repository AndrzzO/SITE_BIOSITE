"""
Views para gestão de subdomínios e domínios personalizados no painel administrativo (Prompt 9).
"""

import logging

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from aplicativos.administracao.permissoes import RequerAutenticacaoAdministrativaMixin

from .models import EnderecoSite, ProjetoSite
from .servicos_dns import verificar_dns_dominio
from .servicos_dominios import (
    adicionar_dominio_personalizado,
    criar_subdominio_padrao,
    definir_endereco_principal,
    remover_endereco,
)

logger = logging.getLogger("aplicativos.sites.views_dominios")


def _responder(
    request: HttpRequest,
    sucesso: bool,
    mensagem: str,
    projeto_uuid: str,
    dados_extras: dict | None = None,
) -> HttpResponse:
    """Helper para responder via JSON ou redirecionamento com mensagem flash."""
    eh_ajax = request.headers.get(
        "X-Requested-With"
    ) == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", "")
    if eh_ajax:
        payload = {"sucesso": sucesso, "mensagem": mensagem}
        if dados_extras:
            payload.update(dados_extras)
        return JsonResponse(payload, status=200 if sucesso else 400)

    if sucesso:
        messages.success(request, mensagem)
    else:
        messages.error(request, mensagem)
    return redirect("painel:site_detalhe", uuid=projeto_uuid)


class ConfigurarSubdominioView(RequerAutenticacaoAdministrativaMixin, View):
    """Atualiza ou cria o subdomínio da plataforma para o BioSite."""

    def post(self, request: HttpRequest, uuid: str) -> HttpResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        subdominio = request.POST.get("subdominio", "").strip()

        if not subdominio:
            return _responder(
                request,
                sucesso=False,
                mensagem="Por favor, informe um subdomínio válido.",
                projeto_uuid=str(projeto.uuid),
            )

        try:
            # Se o projeto não tiver nenhum domínio principal ou se for o único, mantém principal
            ja_tem_principal = projeto.enderecos.filter(
                principal=True,
                status__in=[EnderecoSite.Status.ATIVO, EnderecoSite.Status.VERIFICADO],
            ).exists()
            endereco = criar_subdominio_padrao(
                projeto=projeto,
                subdominio_sugerido=subdominio,
                forcar_principal=not ja_tem_principal,
            )
            return _responder(
                request,
                sucesso=True,
                mensagem=f"Subdomínio da plataforma atualizado para '{endereco.host}' com sucesso!",
                projeto_uuid=str(projeto.uuid),
                dados_extras={"host": endereco.host, "subdominio": endereco.subdominio},
            )
        except ValidationError as e:
            msg = "; ".join(e.messages) if hasattr(e, "messages") else str(e)
            return _responder(
                request,
                sucesso=False,
                mensagem=f"Não foi possível salvar o subdomínio: {msg}",
                projeto_uuid=str(projeto.uuid),
            )
        except Exception as e:
            logger.exception("Erro ao configurar subdomínio do projeto %s: %s", projeto.id, e)
            return _responder(
                request,
                sucesso=False,
                mensagem="Ocorreu um erro interno ao salvar o subdomínio. Tente novamente.",
                projeto_uuid=str(projeto.uuid),
            )


class AdicionarDominioPersonalizadoView(RequerAutenticacaoAdministrativaMixin, View):
    """Cadastra um novo domínio personalizado para o projeto no estado PENDENTE."""

    def post(self, request: HttpRequest, uuid: str) -> HttpResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        host = request.POST.get("host", "").strip()

        if not host:
            return _responder(
                request,
                sucesso=False,
                mensagem="Por favor, informe o domínio personalizado desejado.",
                projeto_uuid=str(projeto.uuid),
            )

        try:
            endereco = adicionar_dominio_personalizado(projeto=projeto, host_bruto=host)
            return _responder(
                request,
                sucesso=True,
                mensagem=(
                    f"Domínio '{endereco.host}' cadastrado com sucesso! "
                    f"Configure o apontamento DNS TXT conforme as instruções para ativá-lo."
                ),
                projeto_uuid=str(projeto.uuid),
                dados_extras={
                    "id": endereco.id,
                    "host": endereco.host,
                    "token": endereco.token_verificacao,
                    "status": endereco.status,
                },
            )
        except ValidationError as e:
            msg = "; ".join(e.messages) if hasattr(e, "messages") else str(e)
            return _responder(
                request,
                sucesso=False,
                mensagem=f"Erro ao adicionar domínio: {msg}",
                projeto_uuid=str(projeto.uuid),
            )
        except Exception as e:
            logger.exception("Erro ao adicionar domínio ao projeto %s: %s", projeto.id, e)
            return _responder(
                request,
                sucesso=False,
                mensagem="Erro interno ao cadastrar o domínio personalizado.",
                projeto_uuid=str(projeto.uuid),
            )


class VerificarDnsDominioView(RequerAutenticacaoAdministrativaMixin, View):
    """Verifica os registros DNS TXT do domínio personalizado para ativação segura."""

    def post(self, request: HttpRequest, uuid: str, endereco_id: int) -> HttpResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        endereco = get_object_or_404(EnderecoSite, id=endereco_id, projeto=projeto)

        sucesso, msg = verificar_dns_dominio(endereco)
        return _responder(
            request,
            sucesso=sucesso,
            mensagem=msg,
            projeto_uuid=str(projeto.uuid),
            dados_extras={
                "id": endereco.id,
                "status": endereco.status,
                "verificado_em": endereco.verificado_em.isoformat()
                if endereco.verificado_em
                else None,
            },
        )


class DefinirDominioPrincipalView(RequerAutenticacaoAdministrativaMixin, View):
    """Define um endereço como principal para o projeto."""

    def post(self, request: HttpRequest, uuid: str, endereco_id: int) -> HttpResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        endereco = get_object_or_404(EnderecoSite, id=endereco_id, projeto=projeto)

        try:
            definir_endereco_principal(projeto=projeto, endereco=endereco)
            return _responder(
                request,
                sucesso=True,
                mensagem=f"O endereço '{endereco.host}' agora é o endereço principal do BioSite!",
                projeto_uuid=str(projeto.uuid),
                dados_extras={"id": endereco.id, "host": endereco.host},
            )
        except ValidationError as e:
            msg = "; ".join(e.messages) if hasattr(e, "messages") else str(e)
            return _responder(
                request,
                sucesso=False,
                mensagem=msg,
                projeto_uuid=str(projeto.uuid),
            )
        except Exception as e:
            logger.exception("Erro ao definir endereço principal: %s", e)
            return _responder(
                request,
                sucesso=False,
                mensagem="Erro ao definir endereço principal.",
                projeto_uuid=str(projeto.uuid),
            )


class RemoverDominioView(RequerAutenticacaoAdministrativaMixin, View):
    """Remove um endereço de domínio ou subdomínio do projeto."""

    def post(self, request: HttpRequest, uuid: str, endereco_id: int) -> HttpResponse:
        projeto = get_object_or_404(ProjetoSite, uuid=uuid)
        endereco = get_object_or_404(EnderecoSite, id=endereco_id, projeto=projeto)
        host_removido = endereco.host

        try:
            remover_endereco(endereco)
            return _responder(
                request,
                sucesso=True,
                mensagem=f"O endereço '{host_removido}' foi removido com sucesso.",
                projeto_uuid=str(projeto.uuid),
            )
        except ValidationError as e:
            msg = "; ".join(e.messages) if hasattr(e, "messages") else str(e)
            return _responder(
                request,
                sucesso=False,
                mensagem=msg,
                projeto_uuid=str(projeto.uuid),
            )
        except Exception as e:
            logger.exception("Erro ao remover endereço: %s", e)
            return _responder(
                request,
                sucesso=False,
                mensagem="Erro interno ao remover endereço.",
                projeto_uuid=str(projeto.uuid),
            )
