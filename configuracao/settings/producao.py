"""Configurações para o ambiente de produção."""

from django.core.exceptions import ImproperlyConfigured

from aplicativos.sites.allowed_hosts import DynamicAllowedHosts

from .base import *

# Em produção, DEBUG é obrigatoriamente False
DEBUG = False

# Validação estrita de SECRET_KEY: nunca permitir chaves padrão ou vazias
SECRET_KEY = env("DJANGO_SECRET_KEY", default="")
if not SECRET_KEY or "insecure" in SECRET_KEY or SECRET_KEY == "troque-esta-chave":
    raise ImproperlyConfigured(
        "A variável DJANGO_SECRET_KEY deve ser configurada com uma chave segura e "
        "exclusiva para o ambiente de produção."
    )

# Hosts permitidos obrigatórios via variável de ambiente
_raw_allowed_hosts = env.list("DJANGO_ALLOWED_HOSTS", default=[])
if not _raw_allowed_hosts:
    raise ImproperlyConfigured(
        "A variável de ambiente DJANGO_ALLOWED_HOSTS é obrigatória em produção."
    )
ALLOWED_HOSTS = DynamicAllowedHosts(_raw_allowed_hosts)

# Origens confiáveis para proteção CSRF
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

# Banco de dados de produção (PostgreSQL obrigatório via DATABASE_URL)
if "DATABASE_URL" not in env:
    raise ImproperlyConfigured(
        "A variável de ambiente DATABASE_URL deve ser definida para o banco de produção."
    )
DATABASES = {"default": env.db("DATABASE_URL")}

# Cabeçalhos e Redirecionamentos de Segurança HTTP
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = env.bool("DJANGO_SESSION_COOKIE_SECURE", default=True)
CSRF_COOKIE_SECURE = env.bool("DJANGO_CSRF_COOKIE_SECURE", default=True)

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=31536000)  # 1 ano
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True)
SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=False)

# Configuração de Storages para produção (cache busting de arquivos estáticos)
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
    },
}
