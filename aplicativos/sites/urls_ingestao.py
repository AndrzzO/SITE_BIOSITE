"""Roteamento público para ingestão de eventos analíticos (/e/)."""

from django.urls import path

from .views_analytics import AnalyticsIngestionView

urlpatterns = [
    path("", AnalyticsIngestionView.as_view(), name="analytics_ingestao"),
]
