"""Rotas de verificação operacional (Health Check)."""

from django.urls import path

from .views import health_check

app_name = "health"

urlpatterns = [
    path("", health_check, name="liveness"),
]
