"""Configurações para o ambiente de testes automatizados."""

from aplicativos.sites.allowed_hosts import DynamicAllowedHosts

from .base import *

DEBUG = False

SECRET_KEY = "chave-secreta-para-ambiente-de-testes-automatizados-segura"

ALLOWED_HOSTS = DynamicAllowedHosts(
    ["localhost", "127.0.0.1", "testserver", ".testserver", ".localhost"]
)

# Banco de dados isolado em memória para os testes (nunca afeta banco real)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Hasher rápido para acelerar a execução dos testes
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Silencia logs não críticos durante os testes
LOGGING["handlers"]["console"]["level"] = "ERROR"
