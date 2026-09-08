"""
Validadores e normalizadores para hosts, subdomínios e domínios personalizados (Prompt 9).
"""

import re
import urllib.parse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# Subdomínios reservados por padrão que nunca podem ser atribuídos a clientes
SUBDOMINIOS_RESERVADOS_PADRAO = frozenset(
    {
        "www",
        "admin",
        "painel",
        "api",
        "static",
        "media",
        "assets",
        "cdn",
        "go",
        "nfc",
        "qr",
        "mail",
        "email",
        "smtp",
        "pop",
        "imap",
        "ftp",
        "health",
        "status",
        "support",
        "suporte",
        "app",
        "apps",
        "auth",
        "login",
        "logout",
        "test",
        "dev",
        "stage",
        "staging",
        "beta",
        "docs",
        "ajuda",
        "help",
        "billing",
        "pagamento",
        "checkout",
        "ws",
        "webhook",
        "sites",
        "biosite",
        "root",
        "ns1",
        "ns2",
        "dns",
    }
)

# Regex para labels individuais de domínio (RFC 1035 / RFC 1123)
LABEL_REGEX = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$", re.IGNORECASE)
SUBDOMINIO_REGEX = re.compile(r"^[a-z0-9]([a-z0-9-]{1,61}[a-z0-9])?$")


def obter_subdominios_reservados() -> set[str]:
    """Retorna a união dos subdomínios reservados padrão com os configurados em settings."""
    reservados = set(SUBDOMINIOS_RESERVADOS_PADRAO)
    adicionais = getattr(settings, "RESERVED_SUBDOMAINS", None)
    if adicionais:
        reservados.update({str(s).strip().lower() for s in adicionais if s})
    return reservados


def normalizar_host(host_bruto: str) -> str:
    """
    Normaliza rigorosamente qualquer string de host de entrada.

    Regras aplicadas:
    1. Lowercase e remoção de espaços em branco.
    2. Remoção de esquemas (http://, https://, //).
    3. Remoção de caminhos (/path), query strings (?x=1) e fragmentos (#top).
    4. Remoção de portas (:8000, :443, etc.).
    5. Remoção de ponto final trailing (FQDN dot, ex: 'exemplo.com.').
    6. Codificação IDNA segura (Punycode para domínios internacionalizados).
    """
    if not host_bruto:
        return ""

    host = str(host_bruto).strip().lower()

    # Remove esquema caso fornecido
    if "://" in host:
        try:
            parsed = urllib.parse.urlparse(host)
            host = parsed.netloc or parsed.path
        except Exception:
            host = host.split("://", 1)[-1]
    elif host.startswith("//"):
        host = host[2:]

    # Remove qualquer barra ou o que vier após ela
    if "/" in host:
        host = host.split("/", 1)[0]

    # Remove query string e fragmento
    if "?" in host:
        host = host.split("?", 1)[0]
    if "#" in host:
        host = host.split("#", 1)[0]

    # Remove porta se presente (IPv4 e nomes normais; IPv6 tratados separadamente)
    if ":" in host:
        if not host.startswith("["):
            host = host.split(":", 1)[0]
        else:
            # IPv6 entre colchetes: [::1]:8000
            match = re.match(r"^(\[[a-f0-9:]+\])(?::\d+)?$", host)
            if match:
                host = match.group(1)

    # Remove ponto final FQDN
    host = host.rstrip(".")

    # Processamento IDNA para caracteres internacionais (Punycode)
    try:
        host = host.encode("idna").decode("ascii")
    except Exception:
        # Se falhar a conversão IDNA, mantém a versão sanitizada para o validador rejeitar
        pass

    return host.strip()


def validar_formato_host(host: str) -> None:
    """
    Valida se um host normalizado é um hostname sintaticamente válido.
    Levanta ValidationError caso contrário.
    """
    if not host:
        raise ValidationError(_("O nome de host não pode estar em branco."))

    if len(host) > 253:
        raise ValidationError(_("O host excede o comprimento máximo permitido de 253 caracteres."))

    # Permite localhost e IP loopback em desenvolvimento
    if host in ("localhost", "127.0.0.1", "[::1]"):
        return host

    # Proíbe caracteres perigosos ou ilegais
    if any(c in host for c in (" ", "\t", "\r", "\n", "/", "\\", "@", ":", "?", "#")):
        raise ValidationError(_("O host contém caracteres ilegais."))

    # Deve conter ao menos um ponto para ser um domínio ou subdomínio válido
    partes = host.split(".")
    if len(partes) < 2:
        raise ValidationError(
            _(
                "O host deve conter pelo menos um domínio e uma extensão válida (ex: biosite.com.br)."
            )
        )

    for parte in partes:
        if not parte:
            raise ValidationError(_("O host contém segmentos vazios."))
        if len(parte) > 63:
            raise ValidationError(_("Cada segmento do host pode ter no máximo 63 caracteres."))
        if not LABEL_REGEX.match(parte):
            raise ValidationError(
                _(
                    f"O segmento '{parte}' do host é inválido. Utilize apenas letras, números e hífens."
                )
            )

    return host


def validar_subdominio(subdominio: str) -> str:
    """
    Valida e normaliza o identificador de subdomínio da plataforma (ex: 'joao' para 'joao.seudominio.com').
    Retorna o subdomínio normalizado ou levanta ValidationError.
    """
    if not subdominio:
        raise ValidationError(_("O subdomínio não pode estar em branco."))

    sub = str(subdominio).strip().lower()

    if len(sub) < 3:
        raise ValidationError(_("O subdomínio deve conter pelo menos 3 caracteres."))
    if len(sub) > 63:
        raise ValidationError(_("O subdomínio não pode exceder 63 caracteres."))

    if not SUBDOMINIO_REGEX.match(sub):
        raise ValidationError(
            _(
                "O subdomínio deve conter apenas letras minúsculas (a-z), números (0-9) e hífens (-), "
                "e não pode começar nem terminar com hífen."
            )
        )

    if "--" in sub:
        raise ValidationError(_("O subdomínio não pode conter hífens consecutivos."))

    reservados = obter_subdominios_reservados()
    if sub in reservados:
        raise ValidationError(
            _(f"O subdomínio '{sub}' é reservado pela plataforma e não pode ser utilizado.")
        )

    return sub
