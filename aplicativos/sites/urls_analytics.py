"""Roteamento de URLs do módulo de Analytics administrativo."""

from django.urls import path

from .views_analytics import (
    AnalyticsGlobalView,
    LinkInteligenteMetricasJsonView,
)

urlpatterns = [
    path("", AnalyticsGlobalView.as_view(), name="analytics_global"),
    path(
        "links/<uuid:pk>/metricas/",
        LinkInteligenteMetricasJsonView.as_view(),
        name="link_metricas_json",
    ),
]
