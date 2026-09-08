"""
Serviços centrais para gestão de subdomínios, domínios personalizados e URLs canônicas (Prompt 9).
"""

import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import EnderecoSite, HistoricoEnderecoSite, ProjetoSite
from .validadores_dominios import (
    normalizar_host,
    validar_formato_host,
    validar_subdominio,
)

logger = logging.getLogger("aplicativos.sites.servicos_dominios")

# Tempo padrão de reserva de subdomínio desvinculado (quarentena contra takeover)
DIAS_QUARENTENA_ENDERECO = 30


def obter_base_domain() -> str:
    """Retorna o domínio base configurado para a plataforma (ex: 'biosite.local' ou 'seudominio.com')."""
    base = getattr(settings, "PUBLIC_BASE_DOMAIN", "localhost")
    return str(base).strip().lower()


def obter_public_scheme() -> str:
    """Retorna o esquema público padrão (https ou http)."""
    return getattr(settings, "PUBLIC_SCHEME", "https" if not settings.DEBUG else "http")


def gerar_host_subdominio(subdominio: str) -> str:
    """Gera o hostname completo para um subdomínio da plataforma."""
    base = obter_base_domain()
    sub = subdominio.strip().lower()
    return f"{sub}.{base}"


def obter_url_publica_projeto(projeto: ProjetoSite, request=None, caminho: str = "") -> str:
    """
    Retorna a URL pública oficial e canônica de um BioSite.

    REGRA DE OURO (Prompt 9):
    1. Se o projeto possuir um EnderecoSite principal ativo/verificado:
       Usa 'https://<host>/' (ou http em dev) sem depender do Host do request do usuário.
    2. Fallback de compatibilidade (Prompt 8):
       Se não houver endereço principal configurado, utiliza '/b/<slug>/'.
    """
    if caminho and not caminho.startswith("/"):
        caminho = f"/{caminho}"

    # Busca o endereço principal do projeto
    endereco_principal = projeto.enderecos.filter(
        principal=True,
        status__in=[EnderecoSite.Status.ATIVO, EnderecoSite.Status.VERIFICADO],
    ).first()

    if endereco_principal:
        scheme = obter_public_scheme()
        caminho_final = caminho if caminho else "/"
        return f"{scheme}://{endereco_principal.host}{caminho_final}"

    # Fallback seguro: rota legada /b/<slug>/
    from django.urls import reverse

    caminho_legado = reverse("publico:site_publico", kwargs={"slug": projeto.slug})
    if caminho and caminho != "/":
        caminho_legado = f"{caminho_legado.rstrip('/')}{caminho}"

    if request is not None:
        return request.build_absolute_uri(caminho_legado)
    return caminho_legado


def criar_subdominio_padrao(
    projeto: ProjetoSite,
    subdominio_sugerido: str | None = None,
    forcar_principal: bool = True,
) -> EnderecoSite:
    """
    Garante ou cria o subdomínio da plataforma para um projeto de forma determinística e idempotente.
    Trata colisões com outros projetos ou endereços em quarentena.
    """
    base_domain = obter_base_domain()

    # Se já existir um subdomínio da plataforma para este projeto, reutiliza
    existente = projeto.enderecos.filter(tipo=EnderecoSite.Tipo.SUBDOMINIO_PLATAFORMA).first()
    if existente and not subdominio_sugerido:
        return existente

    sugestao_base = subdominio_sugerido or projeto.slug
    # Sanitiza sugestão
    sugestao_limpa = normalizar_host(sugestao_base).replace(".", "-")
    if len(sugestao_limpa) < 3:
        sugestao_limpa = f"site-{sugestao_limpa}"

    # Valida formato e reservados; se falhar, ajusta para nome seguro
    try:
        sub_candidato = validar_subdominio(sugestao_limpa)
    except ValidationError:
        sub_candidato = f"site-{projeto.slug[:50]}"
        try:
            sub_candidato = validar_subdominio(sub_candidato)
        except ValidationError:
            sub_candidato = f"site-{projeto.id}"

    # Resolução de colisões
    sub_final = sub_candidato
    tentativa = 1
    while True:
        host_candidato = f"{sub_final}.{base_domain}"

        # Verifica se já está em uso por outro projeto
        em_uso = EnderecoSite.objects.filter(host=host_candidato).exclude(projeto=projeto).exists()
        # Verifica quarentena de histórico
        em_quarentena = (
            HistoricoEnderecoSite.objects.filter(
                host=host_candidato,
                reservado_ate__gt=timezone.now(),
            )
            .exclude(projeto=projeto)
            .exists()
        )

        if not em_uso and not em_quarentena:
            break

        tentativa += 1
        sub_final = f"{sub_candidato}-{tentativa}"

    host_final = f"{sub_final}.{base_domain}"

    with transaction.atomic():
        # Se for marcar como principal, desmarca os demais deste projeto
        if forcar_principal:
            projeto.enderecos.filter(principal=True).update(principal=False)

        endereco, criado = EnderecoSite.objects.update_or_create(
            projeto=projeto,
            tipo=EnderecoSite.Tipo.SUBDOMINIO_PLATAFORMA,
            defaults={
                "subdominio": sub_final,
                "host": host_final,
                "status": EnderecoSite.Status.ATIVO,
                "principal": forcar_principal,
                "verificado_em": timezone.now(),
                "erro_mensagem": "",
            },
        )

    # Invalida cache de resolução
    invalidar_cache_host(host_final)
    from .servicos_publicacao import invalidar_cache_site_publico

    invalidar_cache_site_publico(projeto)

    logger.info(
        "Subdomínio da plataforma '%s' associado ao projeto '%s' (Principal=%s)",
        host_final,
        projeto.nome,
        forcar_principal,
    )
    return endereco


def adicionar_dominio_personalizado(projeto: ProjetoSite, host_bruto: str) -> EnderecoSite:
    """
    Cadastra um novo domínio personalizado para o projeto no estado PENDENTE,
    gerando um token criptográfico único para verificação via DNS TXT.
    """
    host = normalizar_host(host_bruto)
    validar_formato_host(host)

    # Impede adicionar o próprio domínio base da plataforma como custom domain
    base_domain = obter_base_domain()
    if host == base_domain or host.endswith(f".{base_domain}"):
        raise ValidationError(
            _(
                "O domínio informado pertence à plataforma. "
                "Para subdomínios da plataforma, utilize a seção específica de subdomínio."
            )
        )

    # Verifica se já pertence a outro projeto
    outro = EnderecoSite.objects.filter(host=host).exclude(projeto=projeto).first()
    if outro:
        raise ValidationError(
            _(f"O domínio '{host}' já está vinculado a outro projeto na plataforma.")
        )

    # Verifica se o projeto já tem este domínio cadastrado
    existente = projeto.enderecos.filter(host=host).first()
    if existente:
        if existente.status == EnderecoSite.Status.REMOVIDO:
            # Reativa
            existente.status = EnderecoSite.Status.PENDENTE
            existente.token_verificacao = secrets.token_urlsafe(32)
            existente.verificado_em = None
            existente.save()
            return existente
        return existente

    # Gera token criptograficamente seguro
    token_verificacao = secrets.token_urlsafe(32)

    endereco = EnderecoSite.objects.create(
        projeto=projeto,
        host=host,
        tipo=EnderecoSite.Tipo.DOMINIO_PERSONALIZADO,
        status=EnderecoSite.Status.PENDENTE,
        principal=False,  # Nunca nasce como principal; precisa verificar antes
        token_verificacao=token_verificacao,
        metadata={"origem": "painel_administrativo"},
    )

    logger.info(
        "Domínio personalizado '%s' adicionado ao projeto '%s' com status PENDENTE",
        host,
        projeto.nome,
    )
    return endereco


def definir_endereco_principal(projeto: ProjetoSite, endereco: EnderecoSite) -> None:
    """
    Define um EnderecoSite como o endereço principal do projeto.

    REGRA DE SEGURANÇA (Prompt 9):
    Domínios personalizados só podem virar principal se estiverem VERIFICADOS ou ATIVOS.
    """
    if endereco.projeto_id != projeto.id:
        raise ValidationError(_("Este endereço não pertence ao projeto informado."))

    if endereco.tipo == EnderecoSite.Tipo.DOMINIO_PERSONALIZADO:
        if endereco.status not in (EnderecoSite.Status.VERIFICADO, EnderecoSite.Status.ATIVO):
            raise ValidationError(
                _(
                    "Um domínio personalizado só pode se tornar o endereço principal "
                    "após a verificação com sucesso do apontamento DNS."
                )
            )

    with transaction.atomic():
        projeto_lock = ProjetoSite.objects.select_for_update().get(id=projeto.id)

        # Desmarca todos os outros
        projeto_lock.enderecos.exclude(id=endereco.id).update(principal=False)

        # Marca o escolhido
        endereco.principal = True
        endereco.status = EnderecoSite.Status.ATIVO
        endereco.save(update_fields=["principal", "status", "atualizado_em"])

    # Invalida cache de resolução de todos os hosts do projeto e cache público
    for h in projeto.enderecos.values_list("host", flat=True):
        invalidar_cache_host(h)

    from .servicos_publicacao import invalidar_cache_site_publico

    invalidar_cache_site_publico(projeto)

    logger.info(
        "Endereço '%s' definido como PRINCIPAL para o projeto '%s'",
        endereco.host,
        projeto.nome,
    )


def remover_endereco(endereco: EnderecoSite) -> None:
    """
    Remove um endereço associado ao projeto.
    Garante que se for o endereço principal, outro endereço válido assume a posição.
    Registra quarentena no histórico.
    """
    projeto = endereco.projeto

    # Não permite remover se for o único endereço de um projeto publicado
    total_ativos = (
        projeto.enderecos.exclude(id=endereco.id)
        .filter(status__in=[EnderecoSite.Status.ATIVO, EnderecoSite.Status.VERIFICADO])
        .count()
    )
    if projeto.esta_publicado() and total_ativos == 0:
        raise ValidationError(
            _(
                "Não é possível remover o único endereço de um site publicado. "
                "Crie ou ative outro endereço antes de remover este."
            )
        )

    with transaction.atomic():
        era_principal = endereco.principal
        host_removido = endereco.host

        # Registra no histórico para proteção de quarentena
        HistoricoEnderecoSite.objects.create(
            host=host_removido,
            projeto=projeto,
            motivo="remocao_usuario",
            reservado_ate=timezone.now() + timedelta(days=DIAS_QUARENTENA_ENDERECO),
        )

        # Exclui o registro do endereço
        endereco.delete()

        # Se era principal, elege um substituto automático
        if era_principal:
            substituto = (
                projeto.enderecos.filter(tipo=EnderecoSite.Tipo.SUBDOMINIO_PLATAFORMA).first()
                or projeto.enderecos.first()
            )
            if substituto:
                substituto.principal = True
                substituto.status = EnderecoSite.Status.ATIVO
                substituto.save(update_fields=["principal", "status", "atualizado_em"])

    invalidar_cache_host(host_removido)
    from .servicos_publicacao import invalidar_cache_site_publico

    invalidar_cache_site_publico(projeto)

    logger.info(
        "Endereço '%s' removido do projeto '%s'. Quarentena registrada.",
        host_removido,
        projeto.nome,
    )


def invalidar_cache_host(host: str) -> None:
    """Invalida o cache de resolução para o host especificado."""
    host_norm = normalizar_host(host)
    cache_key = f"biosite:host:{host_norm}"
    cache.delete(cache_key)
