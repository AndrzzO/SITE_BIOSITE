"""Roteamento de URLs para a biblioteca de templates e previews."""

from django.urls import path

from .views_templates import (
    TemplateArquivarView,
    TemplateDuplicarView,
    TemplateExcluirView,
    TemplateListView,
    TemplatePreviewView,
)

urlpatterns = [
    path("", TemplateListView.as_view(), name="templates_lista"),
    path("<uuid:uuid>/preview/", TemplatePreviewView.as_view(), name="template_preview"),
    path("<uuid:uuid>/duplicar/", TemplateDuplicarView.as_view(), name="template_duplicar"),
    path("<uuid:uuid>/arquivar/", TemplateArquivarView.as_view(), name="template_arquivar"),
    path("<uuid:uuid>/excluir/", TemplateExcluirView.as_view(), name="template_excluir"),
]
