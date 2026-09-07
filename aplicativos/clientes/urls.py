"""Roteamento de URLs para a área de clientes."""

from django.urls import path

from .views import (
    ClienteArquivarView,
    ClienteCreateView,
    ClienteDetailView,
    ClienteListView,
    ClienteRestaurarView,
    ClienteUpdateView,
)

urlpatterns = [
    path("", ClienteListView.as_view(), name="clientes_lista"),
    path("novo/", ClienteCreateView.as_view(), name="cliente_novo"),
    path("<uuid:uuid>/", ClienteDetailView.as_view(), name="cliente_detalhe"),
    path("<uuid:uuid>/editar/", ClienteUpdateView.as_view(), name="cliente_editar"),
    path("<uuid:uuid>/arquivar/", ClienteArquivarView.as_view(), name="cliente_arquivar"),
    path("<uuid:uuid>/restaurar/", ClienteRestaurarView.as_view(), name="cliente_restaurar"),
]
