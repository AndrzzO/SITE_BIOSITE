"""
Serviços centrais para gestão, geração de tokens criptográficos e resolução de Links Inteligentes,
Tags NFC físicas e QR Codes (Prompt 10).
"""

import logging
import secrets
import string

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from .models import HistoricoVinculoTag, LinkInteligente, ProjetoSite
from .servicos_dominios import (
    obter_base_domain,
    obter_public_scheme,
    obter_url_publica_projeto,
)

logger = logging.getLogger("aplicativos.sites.servicos_links")

# Alfabeto Base62 seguro para tokens de URL (0-9, a-z, A-Z)
ALFABETO_TOKEN = string.ascii_letters + string.digits
TAMANHO_TOKEN = 10
CACHE_TTL_SMARTLINK = 60  # Cache de resolução rápida (60 segundos)


def gerar_token_link(max_tentativas: int = 5) -> str:
    """
    Gera um token aleatório criptograficamente seguro, não-sequencial e imprevisível.
    Possui entropia de 62^10 (~8.39e17 combinações), tornando enumeração impossível.
    Verifica unicidade no banco de dados com limite de tentativas.
    """
    for _ in range(max_tentativas):
        candidato = "".join(secrets.choice(ALFABETO_TOKEN) for _ in range(TAMANHO_TOKEN))
        if not LinkInteligente.objects.filter(token=candidato).exists():
            return candidato

    raise RuntimeError("Não foi possível gerar um token único após múltiplas tentativas.")


def obter_base_url_redirector(request=None) -> str:
    """
    Retorna a URL base estável do serviço de redirecionamento de links inteligentes.

    Regras:
    1. Se `SMART_LINK_BASE_URL` estiver configurada no .env/settings, utiliza-a diretamente.
    2. Em ambiente de desenvolvimento local (DEBUG=True ou localhost):
       Utiliza o host da requisição atual ou http://127.0.0.1:8000.
    3. Em produção:
       Utiliza o esquema público e o host dedicado configurado (ex: https://go.seudominio.com).
    """
    configurada = getattr(settings, "SMART_LINK_BASE_URL", "").strip().rstrip("/")
    if configurada:
        return configurada

    base_domain = obter_base_domain()
    scheme = obter_public_scheme()

    # Ambiente de desenvolvimento local
    if settings.DEBUG or base_domain in ("localhost", "127.0.0.1"):
        if request is not None:
            try:
                host = request.get_host()
                return f"http://{host}"
            except Exception:
                pass
        return "http://127.0.0.1:8000"

    smart_host = getattr(settings, "SMART_LINK_HOST", f"go.{base_domain}")
    return f"{scheme}://{smart_host}"


def obter_url_completa_link(link: LinkInteligente, request=None) -> str:
    """
    Gera a URL oficial e imutável que deve ser gravada fisicamente no chip NFC ou no QR Code.
    Exemplo: https://go.seudominio.com/n/Ab7Kp2X9/ ou https://go.seudominio.com/q/X9p2K7Ab/
    """
    base_url = obter_base_url_redirector(request=request)
    prefixo = "n" if link.tipo == LinkInteligente.Tipo.NFC else "q"
    return f"{base_url}/{prefixo}/{link.token}/"


def invalidar_cache_link(token: str) -> None:
    """Invalida o cache de resolução para o token fornecido."""
    cache.delete(f"biosite:smartlink:{token}")


def resolver_link_inteligente(
    token: str, tipo_esperado: str | None = None
) -> tuple[bool, str | None, LinkInteligente | None]:
    """
    Resolve um token público de link inteligente (NFC ou QR) para a URL pública do BioSite atual.

    FLUXO DE SEGURANÇA E ARQUITETURA (Prompt 10):
    1. Normaliza e consulta cache em memória.
    2. Busca o registro no banco com select_related('projeto').
    3. Valida se a tag está com status ATIVO.
    4. Valida se o projeto vinculado não está arquivado ou suspenso.
    5. Valida se o projeto possui publicação ativa (esta_publicado() == True).
    6. Obtém a URL pública canônica atual via obter_url_publica_projeto(projeto).
    7. Retorna (True, url_destino, link).
    8. Se qualquer validação falhar: retorna (False, None, None) para resposta neutra.
    """
    token_limpo = str(token).strip()
    if not token_limpo:
        return False, None, None

    cache_key = f"biosite:smartlink:{token_limpo}"
    cached_dest = cache.get(cache_key)
    if cached_dest:
        return True, cached_dest, None

    link = LinkInteligente.objects.select_related("projeto").filter(token=token_limpo).first()

    if not link:
        return False, None, None

    # Valida tipo de link se exigido pela rota
    if tipo_esperado and link.tipo != tipo_esperado:
        logger.info(
            "Token '%s' acessado com tipo divergente (esperado %s, gravado %s).",
            token_limpo,
            tipo_esperado,
            link.tipo,
        )

    # Tag inativa não redireciona
    if link.status != LinkInteligente.Status.ATIVO:
        return False, None, link

    projeto = link.projeto

    # Projeto arquivado, suspenso ou sem publicação ativa não redireciona
    if projeto.status == ProjetoSite.Status.ARQUIVADO or not projeto.esta_publicado():
        return False, None, link

    # Obtém a URL pública canônica oficial gerada pelo Prompt 9 (sem usar request.get_host)
    url_destino = obter_url_publica_projeto(projeto)

    # Armazena em cache por curto período
    cache.set(cache_key, url_destino, CACHE_TTL_SMARTLINK)

    return True, url_destino, link


def criar_link_inteligente(
    projeto: ProjetoSite,
    tipo: str = LinkInteligente.Tipo.NFC,
    nome: str = "",
    descricao: str = "",
    tipo_midia_fisica: str = LinkInteligente.TipoMidiaFisica.CARTAO,
    usuario=None,
    metadata: dict | None = None,
) -> LinkInteligente:
    """
    Cria um novo Link Inteligente com token criptográfico exclusivo e registra no histórico.
    """
    if not nome:
        tipo_label = "Tag NFC" if tipo == LinkInteligente.Tipo.NFC else "QR Code"
        nome = f"{tipo_label} {projeto.nome}"

    token = gerar_token_link()

    with transaction.atomic():
        link = LinkInteligente.objects.create(
            projeto=projeto,
            token=token,
            tipo=tipo,
            status=LinkInteligente.Status.ATIVO,
            tipo_midia_fisica=tipo_midia_fisica,
            nome=nome,
            descricao=descricao,
            ativado_em=timezone.now(),
            metadata=metadata or {},
        )

        # Registra histórico inicial de auditoria
        HistoricoVinculoTag.objects.create(
            link=link,
            projeto_anterior=None,
            projeto_novo=projeto,
            alterado_por=usuario,
            motivo="Criação inicial da tag.",
        )

    logger.info(
        "Link inteligente '%s' (Tipo: %s, Token: %s) criado para o projeto '%s'.",
        link.nome,
        link.tipo,
        link.token,
        projeto.nome,
    )
    return link


def alterar_vinculo_projeto(
    link: LinkInteligente,
    novo_projeto: ProjetoSite,
    usuario=None,
    motivo: str = "",
) -> None:
    """
    Altera o BioSite de destino de uma Tag NFC ou QR Code sem alterar o token gravado fisicamente.
    Registra histórico imutável para assegurar a integridade cronológica de analytics.
    """
    if link.projeto_id == novo_projeto.id:
        return

    with transaction.atomic():
        projeto_antigo = link.projeto

        HistoricoVinculoTag.objects.create(
            link=link,
            projeto_anterior=projeto_antigo,
            projeto_novo=novo_projeto,
            alterado_por=usuario,
            motivo=motivo or f"Reatribuição de '{projeto_antigo.nome}' para '{novo_projeto.nome}'.",
        )

        link.projeto = novo_projeto
        link.save(update_fields=["projeto", "atualizado_em"])

    invalidar_cache_link(link.token)
    logger.info(
        "Vínculo da tag '%s' (Token: %s) alterado de '%s' para '%s'.",
        link.nome,
        link.token,
        projeto_antigo.nome,
        novo_projeto.nome,
    )


def alternar_status_link(link: LinkInteligente, ativar: bool) -> None:
    """Ativa ou desativa operacionalmente o link inteligente."""
    novo_status = LinkInteligente.Status.ATIVO if ativar else LinkInteligente.Status.INATIVO
    if link.status == novo_status:
        return

    link.status = novo_status
    if ativar:
        link.ativado_em = timezone.now()
        link.desativado_em = None
    else:
        link.desativado_em = timezone.now()

    link.save(update_fields=["status", "ativado_em", "desativado_em", "atualizado_em"])
    invalidar_cache_link(link.token)

    logger.info("Link inteligente '%s' alterado para status '%s'.", link.token, novo_status)
