"""Roteamento público para os BioSites publicados da plataforma."""

from django.urls import path

from .views_publicas import PublicSiteView

app_name = "publico"

urlpatterns = [
    path("<slug:slug>/", PublicSiteView.as_view(), name="site_publico"),
    path(
        "<slug:slug>/<slug:pagina_slug>/",
        PublicSiteView.as_view(),
        name="site_publico_pagina",
    ),
]
