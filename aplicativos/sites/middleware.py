"""
Middleware para roteamento dinâmico de Hosts, isolamento de segurança e redirecionamento de aliases (Prompt 9).
"""

import logging

from django.http import (
    HttpResponseNotFound,
    HttpResponsePermanentRedirect,
)

from .servicos_host import ClasseHost, classificar_host, resolver_site_por_host

logger = logging.getLogger("aplicativos.sites.middleware")


class HostRoutingMiddleware:
    """
    Controlador central de roteamento baseado no cabeçalho Host.

    RESPONSABILIDADES DE SEGURANÇA E ARQUITETURA:
    1. Classifica a requisição em HOST_PLATAFORMA, HOST_SITE ou HOST_DESCONHECIDO.
    2. ISOLAMENTO ABSOLUTO: Bloqueia qualquer tentativa de acessar /painel/ ou /admin/
       a partir de um domínio ou subdomínio de cliente.
    3. ALIAS & CANONICAL: Redireciona 301 automaticamente aliases para o domínio principal.
    4. MULTI-SITE ONE-PAGE: Entrega a publicação ativa na raiz '/' para hosts de clientes,
       mantendo a rota legada /b/<slug>/ intacta para compatibilidade.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            host_bruto = request.get_host()
        except Exception:
            return HttpResponseNotFound("Host inválido.")

        classe_host, host_norm = classificar_host(host_bruto)

        # 1. Requisição destinada à plataforma (painel, health, login, /b/<slug>/)
        if classe_host == ClasseHost.HOST_PLATAFORMA:
            request.eh_host_plataforma = True
            request.site_resolvido = None
            return self.get_response(request)

        # 2. Requisição destinada a um BioSite de cliente (subdomínio ou custom domain)
        if classe_host == ClasseHost.HOST_SITE:
            request.eh_host_plataforma = False

            # BARREIRA DE SEGURANÇA: Domínio de cliente NUNCA acessa áreas administrativas
            caminho = request.path_info
            if caminho.startswith(("/painel", "/admin", "/health")):
                logger.warning(
                    "Tentativa de acesso a rota administrativa '%s' bloqueada no host de cliente '%s'.",
                    caminho,
                    host_norm,
                )
                return HttpResponseNotFound("Página não encontrada.")

            # Permite que arquivos estáticos e uploads de mídia passem livremente
            if caminho.startswith(("/static/", "/media/")):
                return self.get_response(request)

            resultado = resolver_site_por_host(host_norm)
            request.site_resolvido = resultado

            # Se for um alias (ex: subdomínio antigo quando há domínio customizado principal), redireciona 301
            if resultado.sucesso and resultado.deve_redirecionar_para_principal:
                url_destino = resultado.url_redirecionamento
                if caminho and caminho != "/":
                    url_destino = f"{url_destino.rstrip('/')}{caminho}"
                return HttpResponsePermanentRedirect(url_destino)

            # Se o site não estiver publicado, estiver arquivado ou inexistente
            if not resultado.sucesso or not resultado.projeto:
                return HttpResponseNotFound("Site não encontrado ou ainda não publicado.")

            # Renderiza o BioSite diretamente na raiz ou subpágina
            from .views_publicas import PublicSiteView

            return PublicSiteView.as_view()(
                request,
                projeto_resolvido=resultado.projeto,
                publicacao_resolvida=resultado.publicacao,
            )

        # 3. Host desconhecido
        request.eh_host_plataforma = False
        request.site_resolvido = None

        # Permite requisições de estáticos/mídia se necessário
        if request.path_info.startswith(("/static/", "/media/")):
            return self.get_response(request)

        # Retorno 404 neutro sem expor detalhes internos da infraestrutura
        return HttpResponseNotFound("Endereço não configurado nesta plataforma.")
