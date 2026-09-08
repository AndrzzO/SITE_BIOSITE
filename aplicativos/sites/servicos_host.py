"""
Serviço de resolução de Host e identificação de BioSites por domínio/subdomínio (Prompt 9).
"""

import logging
from dataclasses import dataclass
from enum import StrEnum

from django.conf import settings
from django.core.cache import cache

from .models import EnderecoSite, ProjetoSite, PublicacaoSite
from .servicos_dominios import (
    normalizar_host,
    obter_base_domain,
    obter_url_publica_projeto,
)

logger = logging.getLogger("aplicativos.sites.servicos_host")

CACHE_TIMEOUT_RESOLUCAO_HOST = 300  # 5 minutos


class ClasseHost(StrEnum):
    HOST_PLATAFORMA = "plataforma"
    HOST_SITE = "site"
    HOST_DESCONHECIDO = "desconhecido"


@dataclass
class ResultadoResolucaoHost:
    sucesso: bool
    endereco: EnderecoSite | None = None
    projeto: ProjetoSite | None = None
    publicacao: PublicacaoSite | None = None
    eh_principal: bool = False
    deve_redirecionar_para_principal: bool = False
    url_redirecionamento: str | None = None
    motivo_falha: str = ""


def obter_hosts_plataforma() -> set[str]:
    """Retorna o conjunto de hosts administrativos e internos da plataforma."""
    base_domain = obter_base_domain()
    hosts = {
        "localhost",
        "127.0.0.1",
        "[::1]",
        "testserver",
        base_domain,
        f"app.{base_domain}",
        f"admin.{base_domain}",
        f"painel.{base_domain}",
        f"go.{base_domain}",
    }
    smart_host = getattr(settings, "SMART_LINK_HOST", None)
    if smart_host:
        hosts.add(normalizar_host(smart_host))
    configurados = getattr(settings, "PLATFORM_HOSTS", None)
    if configurados:
        hosts.update({normalizar_host(h) for h in configurados if h})
    return hosts


def classificar_host(host_bruto: str) -> tuple[ClasseHost, str]:
    """Classifica a origem da requisição em plataforma, site de cliente ou desconhecido."""
    host = normalizar_host(host_bruto)
    if not host:
        return ClasseHost.HOST_DESCONHECIDO, ""

    plataforma = obter_hosts_plataforma()
    if host in plataforma:
        return ClasseHost.HOST_PLATAFORMA, host

    # Verifica se é um endereço cadastrado e ativo/verificado
    existe_site = EnderecoSite.objects.filter(
        host=host,
        status__in=[EnderecoSite.Status.ATIVO, EnderecoSite.Status.VERIFICADO],
    ).exists()

    if existe_site:
        return ClasseHost.HOST_SITE, host

    # Verifica subdomínio direto da base da plataforma
    base_domain = obter_base_domain()
    if host.endswith(f".{base_domain}"):
        sub = host[: -len(f".{base_domain}")]
        if EnderecoSite.objects.filter(
            subdominio=sub,
            status__in=[EnderecoSite.Status.ATIVO, EnderecoSite.Status.VERIFICADO],
        ).exists():
            return ClasseHost.HOST_SITE, host

    return ClasseHost.HOST_DESCONHECIDO, host


def resolver_site_por_host(host_bruto: str) -> ResultadoResolucaoHost:
    """
    Resolve o ProjetoSite e a PublicacaoSite ativa correspondente ao Host requisitado.

    Garante:
    1. Resolução via cache de alta performance.
    2. Identificação de status do projeto (Rascunho / Publicado / Arquivado).
    3. Detecção de aliases e montagem de URL de redirecionamento 301 para o host principal.
    4. Proteção contra loops de redirecionamento.
    """
    host = normalizar_host(host_bruto)
    if not host:
        return ResultadoResolucaoHost(sucesso=False, motivo_falha="host_vazio")

    cache_key = f"biosite:host_res:{host}"
    dados_cached = cache.get(cache_key)
    if dados_cached is not None:
        if not dados_cached.get("sucesso"):
            return ResultadoResolucaoHost(
                sucesso=False,
                motivo_falha=dados_cached.get("motivo_falha", "desconhecido"),
            )
        try:
            endereco = EnderecoSite.objects.select_related(
                "projeto", "projeto__publicacao_ativa"
            ).get(id=dados_cached["endereco_id"])
            projeto = endereco.projeto
            publicacao = projeto.publicacao_ativa
            if projeto.esta_publicado() and publicacao:
                return ResultadoResolucaoHost(
                    sucesso=True,
                    endereco=endereco,
                    projeto=projeto,
                    publicacao=publicacao,
                    eh_principal=dados_cached["eh_principal"],
                    deve_redirecionar_para_principal=dados_cached["deve_redirecionar"],
                    url_redirecionamento=dados_cached.get("url_redirecionamento"),
                )
        except EnderecoSite.DoesNotExist:
            cache.delete(cache_key)

    # Busca no banco de dados
    endereco = (
        EnderecoSite.objects.select_related("projeto", "projeto__publicacao_ativa")
        .filter(
            host=host,
            status__in=[EnderecoSite.Status.ATIVO, EnderecoSite.Status.VERIFICADO],
        )
        .first()
    )

    if not endereco:
        base_domain = obter_base_domain()
        if host.endswith(f".{base_domain}"):
            sub = host[: -len(f".{base_domain}")]
            endereco = (
                EnderecoSite.objects.select_related("projeto", "projeto__publicacao_ativa")
                .filter(
                    subdominio=sub,
                    tipo=EnderecoSite.Tipo.SUBDOMINIO_PLATAFORMA,
                    status__in=[EnderecoSite.Status.ATIVO, EnderecoSite.Status.VERIFICADO],
                )
                .first()
            )

    if not endereco:
        # Cache negativo curto (30s) para mitigar sobrecarga de bots
        cache.set(cache_key, {"sucesso": False, "motivo_falha": "host_nao_encontrado"}, 30)
        return ResultadoResolucaoHost(sucesso=False, motivo_falha="host_nao_encontrado")

    projeto = endereco.projeto

    # Validações de integridade do projeto
    if projeto.status == ProjetoSite.Status.ARQUIVADO:
        return ResultadoResolucaoHost(
            sucesso=False,
            endereco=endereco,
            projeto=projeto,
            motivo_falha="projeto_arquivado",
        )

    if not projeto.esta_publicado() or not projeto.publicacao_ativa:
        return ResultadoResolucaoHost(
            sucesso=False,
            endereco=endereco,
            projeto=projeto,
            motivo_falha="projeto_nao_publicado",
        )

    publicacao = projeto.publicacao_ativa

    # Verifica se este endereço é o principal ou um alias que deve redirecionar
    deve_redirecionar = False
    url_redirecionamento = None

    if not endereco.principal:
        endereco_principal = projeto.enderecos.filter(
            principal=True,
            status__in=[EnderecoSite.Status.ATIVO, EnderecoSite.Status.VERIFICADO],
        ).first()

        if endereco_principal and endereco_principal.host != endereco.host:
            deve_redirecionar = True
            url_redirecionamento = obter_url_publica_projeto(projeto)

    # Armazena em cache
    cache.set(
        cache_key,
        {
            "sucesso": True,
            "endereco_id": endereco.id,
            "projeto_id": projeto.id,
            "publicacao_id": publicacao.id,
            "eh_principal": endereco.principal,
            "deve_redirecionar": deve_redirecionar,
            "url_redirecionamento": url_redirecionamento,
        },
        CACHE_TIMEOUT_RESOLUCAO_HOST,
    )

    return ResultadoResolucaoHost(
        sucesso=True,
        endereco=endereco,
        projeto=projeto,
        publicacao=publicacao,
        eh_principal=endereco.principal,
        deve_redirecionar_para_principal=deve_redirecionar,
        url_redirecionamento=url_redirecionamento,
    )
