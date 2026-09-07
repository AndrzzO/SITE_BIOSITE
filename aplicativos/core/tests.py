"""Testes automatizados para o aplicativo core."""

from django.db import models
from django.test import TestCase
from django.urls import reverse

from aplicativos.core.models import ModeloBase


# Modelo concreto auxiliar apenas para teste de ModeloBase
class EntidadeExemplo(ModeloBase):
    nome = models.CharField(max_length=100)

    class Meta:
        app_label = "core"


class HealthCheckTests(TestCase):
    """Testes do endpoint de liveness /health/."""

    def test_health_check_retorna_200_com_status_ok(self):
        url = reverse("health:liveness")
        resposta = self.client.get(url)

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json(), {"status": "ok"})
        self.assertEqual(resposta["Content-Type"], "application/json")

    def test_health_check_nao_expõe_informacoes_sensiveis(self):
        url = reverse("health:liveness")
        resposta = self.client.get(url)
        dados = resposta.json()

        # Garante que dados de stack, segredos ou infraestrutura não vazam
        self.assertNotIn("database", dados)
        self.assertNotIn("secret_key", dados)
        self.assertNotIn("version", dados)
        self.assertNotIn("django", dados)


class HomeViewTests(TestCase):
    """Testes da rota inicial temporária."""

    def test_home_retorna_status_200(self):
        url = reverse("core:home")
        resposta = self.client.get(url)
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Plataforma BioSite NFC")

    def test_rota_inexistente_retorna_404(self):
        resposta = self.client.get("/rota-inexistente-12345/")
        self.assertEqual(resposta.status_code, 404)


class ModeloBaseTests(TestCase):
    """Testes de herança e comportamento do ModeloBase."""

    def test_modelo_base_possui_campos_obrigatorios(self):
        campos = [campo.name for campo in ModeloBase._meta.fields]
        self.assertIn("id", campos)
        self.assertIn("uuid", campos)
        self.assertIn("criado_em", campos)
        self.assertIn("atualizado_em", campos)

    def test_campo_uuid_e_unico_e_nao_editavel(self):
        campo_uuid = ModeloBase._meta.get_field("uuid")
        self.assertTrue(campo_uuid.unique)
        self.assertFalse(campo_uuid.editable)
        self.assertTrue(campo_uuid.db_index)
