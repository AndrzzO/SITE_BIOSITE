"""Configuração ASGI para o projeto BioSite NFC."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "configuracao.settings.desenvolvimento")

application = get_asgi_application()
