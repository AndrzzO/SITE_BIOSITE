"""
Serviço seguro de verificação de apontamento DNS para domínios personalizados (Prompt 9).
"""

import logging

from django.conf import settings
from django.utils import timezone

try:
    import dns.exception
    import dns.resolver

    DNS_DISPONIVEL = True
except ImportError:
    DNS_DISPONIVEL = False

from .models import EnderecoSite
from .servicos_dominios import invalidar_cache_host

logger = logging.getLogger("aplicativos.sites.servicos_dns")

TIMEOUT_CONSULTA_DNS = 3.0  # Timeout máximo em segundos para não travar a requisição


def obter_cname_esperado() -> str:
    """Retorna o alvo CNAME esperado para apontamentos de tráfego."""
    base = getattr(settings, "PUBLIC_BASE_DOMAIN", "localhost")
    return getattr(settings, "CUSTOM_DOMAIN_CNAME_TARGET", f"sites.{base}").strip().lower()


def verificar_dns_dominio(endereco: EnderecoSite) -> tuple[bool, str]:
    """
    Executa verificação criptográfica de propriedade do domínio via DNS TXT.

    Registros consultados:
    1. `_site-verification.<host>`
    2. `<host>` (fallback)

    Valor esperado:
    `biosite-verification=<token>` ou `<token>`.

    Retorna:
    - (True, "Domínio verificado com sucesso!")
    - (False, "Mensagem amigável explicando o status da propagação")
    """
    if endereco.tipo != EnderecoSite.Tipo.DOMINIO_PERSONALIZADO:
        return True, "Subdomínios da plataforma são validados automaticamente."

    if not endereco.token_verificacao:
        return False, "Token de verificação não encontrado para este domínio."

    endereco.ultima_checagem_em = timezone.now()

    if not DNS_DISPONIVEL:
        logger.warning("Biblioteca dnspython não está disponível. Verificação DNS ignorada.")
        return False, "O serviço de verificação DNS não está disponível no momento."

    resolver = dns.resolver.Resolver()
    resolver.lifetime = TIMEOUT_CONSULTA_DNS
    resolver.timeout = TIMEOUT_CONSULTA_DNS

    token_esperado = endereco.token_verificacao
    prefixo_token = f"biosite-verification={token_esperado}"

    nomes_para_consultar = [
        f"_site-verification.{endereco.host}",
        endereco.host,
    ]

    encontrado = False
    mensagem_erro = ""

    for nome_alvo in nomes_para_consultar:
        try:
            respostas = resolver.resolve(nome_alvo, "TXT")
            for rdata in respostas:
                for txt_bytes in rdata.strings:
                    txt_str = txt_bytes.decode("utf-8", errors="ignore").strip()
                    if txt_str in (token_esperado, prefixo_token):
                        encontrado = True
                        break
                if encontrado:
                    break
            if encontrado:
                break
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            continue
        except dns.resolver.LifetimeTimeout:
            mensagem_erro = (
                "Tempo limite esgotado ao consultar os servidores DNS. "
                "As alterações de DNS podem levar algum tempo para se propagar."
            )
            break
        except dns.exception.DNSException as e:
            logger.info("Exceção DNS ao consultar '%s': %s", nome_alvo, e)
            mensagem_erro = (
                "Ainda não encontramos a configuração necessária. "
                "Alterações de DNS podem levar algum tempo para se propagar mundialmente."
            )
            break

    if encontrado:
        endereco.status = EnderecoSite.Status.VERIFICADO
        endereco.verificado_em = timezone.now()
        endereco.erro_mensagem = ""
        endereco.save(
            update_fields=[
                "status",
                "verificado_em",
                "erro_mensagem",
                "ultima_checagem_em",
                "atualizado_em",
            ]
        )
        invalidar_cache_host(endereco.host)
        logger.info("Domínio personalizado '%s' verificado com sucesso!", endereco.host)
        return True, "Domínio verificado com sucesso! O apontamento foi confirmado."
    else:
        if not mensagem_erro:
            mensagem_erro = (
                "Ainda não encontramos o registro TXT esperado no DNS. "
                "Certifique-se de ter criado a entrada TXT '_site-verification' com o valor informado."
            )
        endereco.status = EnderecoSite.Status.ERRO
        endereco.erro_mensagem = mensagem_erro
        endereco.save(
            update_fields=["status", "erro_mensagem", "ultima_checagem_em", "atualizado_em"]
        )
        logger.info("Verificação DNS falhou para o domínio '%s': %s", endereco.host, mensagem_erro)
        return False, mensagem_erro
