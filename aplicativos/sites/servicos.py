"""Serviços de domínio para projetos de sites e BioSites."""

import logging

from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from .models import ProjetoSite

logger = logging.getLogger("aplicativos.sites.servicos")

# Rotas e termos reservados pelo sistema que não podem ser usados como slug público
PALAVRAS_RESERVADAS: frozenset[str] = frozenset(
    {
        "admin",
        "painel",
        "login",
        "logout",
        "static",
        "media",
        "health",
        "api",
        "nfc",
        "qr",
        "qrcode",
        "sites",
        "clientes",
        "core",
        "sistema",
        "suporte",
        "app",
        "dashboard",
        "auth",
    }
)


def validar_slug_permitido(slug: str) -> None:
    """Valida se o slug não conflita com rotas reservadas da plataforma."""
    slug_normalizado = slug.strip().lower()
    if slug_normalizado in PALAVRAS_RESERVADAS:
        raise ValidationError(
            _(
                "O endereço '%(slug)s' é uma palavra reservada do sistema. Por favor, escolha outro."
            ),
            code="reserved_slug",
            params={"slug": slug_normalizado},
        )


def gerar_slug_unico(
    nome: str,
    slug_sugerido: str | None = None,
    instancia_id: int | None = None,
) -> str:
    """
    Gera ou valida um slug amigável único para o projeto.

    Tratamento:
    - Normalização com slugify (remove acentos, pontuação, força minúsculas).
    - Evita palavras reservadas adicionando prefixo/sufixo seguro.
    - Se houver colisão de unicidade no banco, anexa sufixo incremental (-2, -3...).
    """
    base = slugify(slug_sugerido) if slug_sugerido else slugify(nome)
    if not base:
        base = "site"

    if base in PALAVRAS_RESERVADAS:
        base = f"{base}-site"

    candidato = base
    contador = 2

    while True:
        qs = ProjetoSite.objects.filter(slug=candidato)
        if instancia_id:
            qs = qs.exclude(id=instancia_id)

        if not qs.exists():
            return candidato

        candidato = f"{base}-{contador}"
        contador += 1


def duplicar_projeto(projeto_original: ProjetoSite) -> ProjetoSite:
    """
    Cria uma cópia administrativa independente e profunda de um projeto de site.

    Duplica atomicamente o projeto e toda a sua árvore estrutural (páginas,
    seções, containers e elementos) gerando novos IDs, UUIDs e status RASCUNHO.
    """
    from .servicos_estrutura import duplicar_projeto_completo

    return duplicar_projeto_completo(projeto_original)
