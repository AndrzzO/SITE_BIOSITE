"""Configurações base compartilhadas entre todos os ambientes."""

from pathlib import Path

import environ

# Diretório raiz do projeto (c:\Users\andre\Documents\BIOSITEDJANGO)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
# Carregar arquivo .env caso exista na raiz do projeto
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)

# AVISO: Em produção, a SECRET_KEY é obrigatoriamente exigida pelo módulo producao.py
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="django-insecure-base-default-dev-only-key-replace-in-production",
)

# Aplicações Django
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
]

# Aplicações de terceiros
THIRD_PARTY_APPS: list[str] = []

# Aplicações locais do projeto
LOCAL_APPS = [
    "aplicativos.core.apps.CoreConfig",
    "aplicativos.administracao.apps.AdministracaoConfig",
    "aplicativos.clientes.apps.ClientesConfig",
    "aplicativos.sites.apps.SitesConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# Middlewares oficiais e seguros
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "aplicativos.sites.middleware.HostRoutingMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "configuracao.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "configuracao.wsgi.application"
ASGI_APPLICATION = "configuracao.asgi.application"

# Modelo de Usuário Customizado (Obrigatório antes das migrations iniciais)
# Usado exclusivamente para a administração da plataforma.
AUTH_USER_MODEL = "administracao.UsuarioAdministrativo"

# Validadores oficiais de senha do Django
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 8,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Configurações de Autenticação do Painel Privado
LOGIN_URL = "painel:login"
LOGIN_REDIRECT_URL = "painel:sites"
LOGOUT_REDIRECT_URL = "painel:login"

# Segurança e Duração da Sessão Administrativa (12 horas)
SESSION_COOKIE_AGE = 43200
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

# Internacionalização e Fuso Horário
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

# Arquivos Estáticos (CSS, JavaScript, Imagens do Sistema)
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Arquivos de Mídia (Uploads futuros: logos, avatares, capas)
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Tipo de chave primária padrão
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Configuração de Logging Base
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} [{name}:{lineno}] {message}",
            "style": "{",
        },
        "simples": {
            "format": "{levelname}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        "aplicativos": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
    },
}

# Configurações de Domínios, Subdomínios e Resolução de Host (Prompt 9)
PUBLIC_BASE_DOMAIN = env("PUBLIC_BASE_DOMAIN", default="localhost")
PUBLIC_SCHEME = env("PUBLIC_SCHEME", default="http")
CUSTOM_DOMAIN_CNAME_TARGET = env("CUSTOM_DOMAIN_CNAME_TARGET", default="sites.seudominio.com")
RESERVED_SUBDOMAINS = env.list("RESERVED_SUBDOMAINS", default=[])
PLATFORM_HOSTS = env.list(
    "PLATFORM_HOSTS",
    default=["localhost", "127.0.0.1", "[::1]", "testserver"],
)

# Configurações de Links Inteligentes, Tags NFC e QR Code (Prompt 10)
SMART_LINK_BASE_URL = env("SMART_LINK_BASE_URL", default="")
SMART_LINK_HOST = env("SMART_LINK_HOST", default="go.localhost")

# Cabeçalhos de Segurança HTTP Padrão
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"
