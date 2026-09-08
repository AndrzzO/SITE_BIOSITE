"""
Roteamento do painel administrativo privado para Links Inteligentes, Tags NFC e QR Codes (Prompt 10).
"""

from django.urls import path

from .views_links import (
    LinkInteligenteAlterarDestinoView,
    LinkInteligenteAlternarStatusView,
    LinkInteligenteCriarView,
    LinkInteligenteQrDownloadView,
    LinksInteligentesGlobalListView,
)

urlpatterns = [
    path("", LinksInteligentesGlobalListView.as_view(), name="links_lista"),
    path("criar/", LinkInteligenteCriarView.as_view(), name="link_criar_global"),
    path("<uuid:uuid>/status/", LinkInteligenteAlternarStatusView.as_view(), name="link_status"),
    path("<uuid:uuid>/destino/", LinkInteligenteAlterarDestinoView.as_view(), name="link_destino"),
    path("<uuid:uuid>/qr/", LinkInteligenteQrDownloadView.as_view(), name="link_qr_download"),
]
