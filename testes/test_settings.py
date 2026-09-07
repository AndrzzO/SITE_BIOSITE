"""Testes para garantir o comportamento correto dos módulos de configurações."""

import importlib
import os
from unittest import mock

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase


class SettingsTests(SimpleTestCase):
    """Testes de integridade das configurações do projeto."""

    def test_timezone_e_idioma_padrao(self):
        """Verifica se o idioma é pt-br e o fuso horário é America/Sao_Paulo."""
        self.assertEqual(settings.LANGUAGE_CODE, "pt-br")
        self.assertEqual(settings.TIME_ZONE, "America/Sao_Paulo")
        self.assertTrue(settings.USE_TZ)

    def test_auth_user_model_configurado_corretamente(self):
        """Verifica se AUTH_USER_MODEL aponta para o modelo customizado."""
        self.assertEqual(settings.AUTH_USER_MODEL, "administracao.UsuarioAdministrativo")

    def test_producao_rejeita_secret_key_ausente_ou_insegura(self):
        """Garante que a configuração de produção falha se DJANGO_SECRET_KEY for inválida."""
        with mock.patch.dict(
            os.environ, {"DJANGO_SECRET_KEY": "", "DJANGO_ALLOWED_HOSTS": "exemplo.com"}, clear=True
        ):
            with self.assertRaises(ImproperlyConfigured):
                import configuracao.settings.producao as prod

                importlib.reload(prod)

    def test_producao_rejeita_allowed_hosts_vazio(self):
        """Garante que a configuração de produção falha se DJANGO_ALLOWED_HOSTS não for fornecido."""
        with mock.patch.dict(
            os.environ,
            {
                "DJANGO_SECRET_KEY": "uma-chave-longa-e-realmente-segura-para-este-teste-12345",
                "DJANGO_ALLOWED_HOSTS": "",
                "DATABASE_URL": "postgres://user:pass@localhost:5432/db",
            },
            clear=True,
        ):
            with self.assertRaises(ImproperlyConfigured):
                import configuracao.settings.producao as prod

                importlib.reload(prod)

    def test_producao_rejeita_database_url_ausente(self):
        """Garante que a configuração de produção falha se DATABASE_URL não for informada."""
        with mock.patch.dict(
            os.environ,
            {
                "DJANGO_SECRET_KEY": "uma-chave-longa-e-realmente-segura-para-este-teste-12345",
                "DJANGO_ALLOWED_HOSTS": "biosite.com.br",
            },
            clear=True,
        ):
            with self.assertRaises(ImproperlyConfigured):
                import configuracao.settings.producao as prod

                importlib.reload(prod)
