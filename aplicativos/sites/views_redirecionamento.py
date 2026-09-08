"""
Views públicas para resolução e redirecionamento dinâmico de Tags NFC e QR Codes (Prompt 10).
"""

import logging

from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseNotFound,
    HttpResponseRedirect,
)
from django.views import View

from .servicos_links import resolver_link_inteligente

logger = logging.getLogger("aplicativos.sites.views_redirecionamento")


class RedirectSmartLinkView(View):
    """
    Endpoint público de alta performance e privacidade para redirecionamento de links inteligentes.

    REGRAS ARQUITETURAIS:
    1. HTTP 302 Found (Redirecionamento temporário): Nunca usa 301 para evitar que o navegador
       ou proxy congele o destino em cache caso o domínio ou projeto seja alterado.
    2. Cookieless e sem sessão: Nenhum cookie de sessão administrativa ou rastreador é injetado.
    3. Proteção SEO: Cabeçalho 'X-Robots-Tag: noindex, nofollow'.
    4. Anti-Open Redirect: Destino é estritamente resolvido via registro confiável de ProjetoSite.
    5. Resposta Neutra: Se a tag estiver inativa ou o site não estiver publicado, retorna 404 neutro
       sem vazar dados internos do cliente ou projeto.
    """

    tipo_esperado: str | None = None

    def head(self, request: HttpRequest, token: str) -> HttpResponse:
        response = self.get(request, token=token)
        response.content = b""
        return response

    def get(self, request: HttpRequest, token: str) -> HttpResponse:
        sucesso, url_destino, link = resolver_link_inteligente(
            token=token, tipo_esperado=self.tipo_esperado
        )

        if not sucesso or not url_destino:
            # Resposta neutra sem vazar informações confidenciais
            resp_erro = HttpResponseNotFound(
                "<html><body style='font-family: sans-serif; text-align: center; padding: 4rem;'>"
                "<h2>Link indisponível</h2>"
                "<p style='color: #666;'>Este link inteligente não está ativo ou o site ainda não foi publicado.</p>"
                "</body></html>",
                content_type="text/html; charset=utf-8",
            )
            resp_erro["X-Robots-Tag"] = "noindex, nofollow"
            return resp_erro

        # Redirecionamento HTTP 302 temporário
        response = HttpResponseRedirect(url_destino)
        response["X-Robots-Tag"] = "noindex, nofollow"
        response["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response["Pragma"] = "no-cache"
        response["Expires"] = "0"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
