"""Configurações para o ambiente de desenvolvimento local."""

from aplicativos.sites.allowed_hosts import DynamicAllowedHosts

from .base import *

DEBUG = env.bool("DJANGO_DEBUG", default=True)

ALLOWED_HOSTS = DynamicAllowedHosts(
    env.list(
        "DJANGO_ALLOWED_HOSTS",
        default=["localhost", "127.0.0.1", "[::1]"],
    )
)

# Banco de dados local padrão: SQLite com facilidade de uso
# Suporta transição imediata para PostgreSQL via DATABASE_URL se configurada
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}

# Nível de logging em desenvolvimento
LOGGING["loggers"]["aplicativos"]["level"] = "DEBUG"
LOGGING["loggers"]["django"]["level"] = "INFO"
