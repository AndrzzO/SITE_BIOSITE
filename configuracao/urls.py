"""Roteamento de URLs principal do projeto BioSite NFC."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Painel administrativo técnico do Django (administração interna de baixo nível)
    path("admin/", admin.site.urls),
    # Painel administrativo privado da plataforma (Workspace e Autenticação)
    path("painel/", include("aplicativos.administracao.urls", namespace="painel")),
    # Rota de monitoramento operacional de saúde (Health Check)
    path("health/", include("aplicativos.core.urls_health", namespace="health")),
    # BioSites Públicos (Prompt 8)
    path("b/", include("aplicativos.sites.urls_publicas", namespace="publico")),
    # Redirector Central de Links Inteligentes, Tags NFC e QR Code (Prompt 10)
    path("", include("aplicativos.sites.urls_redirect")),
    # Rotas públicas do aplicativo central (Home temporária)
    path("", include("aplicativos.core.urls", namespace="core")),
]

# Servir arquivos de mídia e estáticos em ambiente de desenvolvimento local
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
