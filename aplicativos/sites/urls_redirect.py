"""
Roteamento público para o redirector central de Tags NFC e QR Codes (Prompt 10).
"""

from django.urls import path

from .views_redirecionamento import RedirectSmartLinkView

urlpatterns = [
    path("n/<str:token>/", RedirectSmartLinkView.as_view(tipo_esperado="nfc"), name="redirect_nfc"),
    path("q/<str:token>/", RedirectSmartLinkView.as_view(tipo_esperado="qr"), name="redirect_qr"),
]
