"""
Views para atendimento de requisições públicas de BioSites publicados (Prompt 8).

REGRAS ARQUITETURAIS:
1. Desacoplamento absoluto: renderiza exclusivamente a partir de PublicacaoSite.snapshot ativo.
2. O rascunho em edição nunca é consultado ou exposto ao visitante.
3. Alta performance: caching em memória, conditional GET (ETag), zero overhead administrativo.
4. SEO completo: Open Graph, Twitter Cards, canonical, meta description e mobile-first.
"""

import logging
from typing import Any

from django.core.cache import cache
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseNotModified,
)
from django.template.loader import render_to_string
from django.views import View

from .models import ProjetoSite
from .renderer import RenderizadorBioSite
from .servicos_publicacao import (
    CACHE_TTL_SITE_PUBLICO,
    obter_cache_key_site_publico,
)

logger = logging.getLogger("aplicativos.sites.views_publicas")


class PublicSiteView(View):
    """
    Renderiza a versão estável publicada de um BioSite para o público (/b/<slug>/).
    """

    def head(self, request: HttpRequest, slug: str, pagina_slug: str | None = None) -> HttpResponse:
        response = self.get(request, slug=slug, pagina_slug=pagina_slug)
        response.content = b""
        return response

    def get(self, request: HttpRequest, slug: str, pagina_slug: str | None = None) -> HttpResponse:
        # 1. Resolução do Projeto e Publicação Ativa
        projeto = (
            ProjetoSite.objects.filter(slug=slug)
            .select_related("publicacao_ativa", "imagem_compartilhamento")
            .first()
        )

        if (
            not projeto
            or projeto.status != ProjetoSite.Status.PUBLICADO
            or not projeto.publicacao_ativa
        ):
            # Não expõe rascunhos ou projetos inexistentes
            raise Http404("BioSite não encontrado ou ainda não publicado.")

        publicacao = projeto.publicacao_ativa
        etag_val = f'"{publicacao.hash_conteudo}"'

        # 2. Conditional GET (304 Not Modified)
        if_none_match = request.headers.get("If-None-Match")
        if if_none_match and if_none_match == etag_val:
            resp_not_modified = HttpResponseNotModified()
            self._aplicar_security_headers(resp_not_modified, etag_val)
            return resp_not_modified

        # 3. Cache em Memória
        cache_key = obter_cache_key_site_publico(
            str(projeto.uuid), publicacao.numero_versao, pagina_slug or ""
        )
        cached_html = cache.get(cache_key)
        if cached_html:
            response = HttpResponse(cached_html, content_type="text/html; charset=utf-8")
            self._aplicar_security_headers(response, etag_val)
            return response

        # 4. Renderização do Snapshot em Memória com RenderizadorBioSite Compartilhado
        renderer = RenderizadorBioSite(modo="publico")
        html_conteudo = renderer.renderizar_snapshot(publicacao.snapshot, pagina_slug=pagina_slug)

        # 5. Metadados de SEO e Open Graph
        imagem_og = ""
        if projeto.imagem_compartilhamento and projeto.imagem_compartilhamento.arquivo:
            try:
                imagem_og = request.build_absolute_uri(projeto.imagem_compartilhamento.arquivo.url)
            except Exception:
                imagem_og = projeto.imagem_compartilhamento.arquivo.url

        canonical_url = request.build_absolute_uri(request.path)

        contexto: dict[str, Any] = {
            "projeto": projeto,
            "publicacao": publicacao,
            "titulo_seo": projeto.titulo_seo or projeto.nome,
            "descricao_seo": projeto.descricao_seo or "",
            "canonical_url": canonical_url,
            "imagem_og": imagem_og,
            "indexavel": projeto.indexavel,
            "html_conteudo": html_conteudo,
        }

        # 6. Renderiza Template Público Puro
        html_final = render_to_string("sites/publico.html", contexto, request=request)

        # 7. Armazena no Cache
        cache.set(cache_key, html_final, CACHE_TTL_SITE_PUBLICO)

        response = HttpResponse(html_final, content_type="text/html; charset=utf-8")
        self._aplicar_security_headers(response, etag_val)
        return response

    def _aplicar_security_headers(self, response: HttpResponse, etag: str) -> None:
        """Aplica cabeçalhos de segurança e cache HTTP."""
        response["ETag"] = etag
        response["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=86400"
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "SAMEORIGIN"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
