"""Testes automatizados para a gestão de clientes comerciais."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Cliente

Usuario = get_user_model()


class ClienteModelTests(TestCase):
    """Testes de integridade do modelo Cliente."""

    def test_criar_cliente_com_sucesso_apenas_com_nome(self):
        """Valida que apenas o campo nome é estritamente obrigatório."""
        cliente = Cliente.objects.create(nome="João da Silva")
        self.assertEqual(cliente.nome, "João da Silva")
        self.assertEqual(cliente.status, Cliente.Status.ATIVO)
        self.assertIsNotNone(cliente.uuid)
        self.assertIsNone(cliente.arquivado_em)
        self.assertEqual(str(cliente), "João da Silva")

    def test_criar_cliente_com_nome_fantasia(self):
        """Valida representação com nome fantasia."""
        cliente = Cliente.objects.create(
            nome="Empresa XPTO LTDA",
            nome_fantasia="Barbearia XPTO",
        )
        self.assertEqual(str(cliente), "Empresa XPTO LTDA (Barbearia XPTO)")

    def test_arquivar_e_restaurar_cliente(self):
        """Valida métodos de arquivamento e restauração."""
        cliente = Cliente.objects.create(nome="Cliente Teste")
        cliente.arquivar()

        self.assertEqual(cliente.status, Cliente.Status.ARQUIVADO)
        self.assertIsNotNone(cliente.arquivado_em)

        cliente.restaurar()
        self.assertEqual(cliente.status, Cliente.Status.ATIVO)
        self.assertIsNone(cliente.arquivado_em)


class ClienteViewsTests(TestCase):
    """Testes das views do CRUD de clientes."""

    def setUp(self):
        self.operador = Usuario.objects.create_user(
            username="operador_clientes",
            email="operador@biosite.local",
            password="SenhaForte123!",
            is_staff=True,
        )
        self.client.force_login(self.operador)

        self.cliente_ativo = Cliente.objects.create(
            nome="Clínica Sorriso",
            email="sorriso@clinica.com",
            telefone="11999990000",
        )
        self.cliente_arquivado = Cliente.objects.create(
            nome="Antiga Oficina",
            status=Cliente.Status.ARQUIVADO,
        )

    def test_listagem_clientes_autenticado_retorna_200(self):
        url = reverse("painel:clientes_lista")
        resposta = self.client.get(url)

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Clínica Sorriso")

    def test_listagem_clientes_anonimo_redireciona(self):
        self.client.logout()
        url = reverse("painel:clientes_lista")
        resposta = self.client.get(url)

        self.assertEqual(resposta.status_code, 302)
        self.assertIn(reverse("painel:login"), resposta.url)

    def test_busca_clientes_por_termo(self):
        url = f"{reverse('painel:clientes_lista')}?q=Sorriso"
        resposta = self.client.get(url)

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Clínica Sorriso")
        self.assertNotContains(resposta, "Antiga Oficina")

    def test_criar_novo_cliente_com_sucesso(self):
        url = reverse("painel:cliente_novo")
        dados = {
            "nome": "Restaurante Sabor Nobre",
            "nome_fantasia": "Sabor Nobre",
            "email": "contato@sabornobre.com",
        }
        resposta = self.client.post(url, dados)

        cliente_criado = Cliente.objects.filter(nome="Restaurante Sabor Nobre").first()
        self.assertIsNotNone(cliente_criado)
        self.assertRedirects(
            resposta,
            reverse("painel:cliente_detalhe", kwargs={"uuid": cliente_criado.uuid}),
        )

    def test_criar_cliente_sem_nome_falha(self):
        url = reverse("painel:cliente_novo")
        resposta = self.client.post(url, {"nome": ""})

        self.assertEqual(resposta.status_code, 200)
        self.assertIn("nome", resposta.context["form"].errors)
        self.assertIn("O nome do cliente é obrigatório.", resposta.context["form"].errors["nome"])

    def test_detalhes_do_cliente(self):
        url = reverse("painel:cliente_detalhe", kwargs={"uuid": self.cliente_ativo.uuid})
        resposta = self.client.get(url)

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Clínica Sorriso")
        self.assertContains(resposta, "sorriso@clinica.com")

    def test_editar_cliente(self):
        url = reverse("painel:cliente_editar", kwargs={"uuid": self.cliente_ativo.uuid})
        resposta = self.client.post(
            url,
            {
                "nome": "Clínica Sorriso Premium",
                "email": "novo@clinica.com",
            },
        )
        self.assertEqual(resposta.status_code, 302)

        self.cliente_ativo.refresh_from_db()
        self.assertEqual(self.cliente_ativo.nome, "Clínica Sorriso Premium")
        self.assertEqual(self.cliente_ativo.email, "novo@clinica.com")

    def test_arquivar_cliente_via_post(self):
        url = reverse("painel:cliente_arquivar", kwargs={"uuid": self.cliente_ativo.uuid})
        resposta = self.client.post(url)

        self.cliente_ativo.refresh_from_db()
        self.assertEqual(self.cliente_ativo.status, Cliente.Status.ARQUIVADO)
        self.assertRedirects(
            resposta,
            reverse("painel:cliente_detalhe", kwargs={"uuid": self.cliente_ativo.uuid}),
        )

    def test_arquivar_cliente_via_get_nao_funciona(self):
        """Garante que requisições GET não arquivam dados mutáveis."""
        url = reverse("painel:cliente_arquivar", kwargs={"uuid": self.cliente_ativo.uuid})
        resposta = self.client.get(url)

        # Retorna 405 Method Not Allowed
        self.assertEqual(resposta.status_code, 405)
        self.cliente_ativo.refresh_from_db()
        self.assertEqual(self.cliente_ativo.status, Cliente.Status.ATIVO)

    def test_restaurar_cliente_via_post(self):
        url = reverse("painel:cliente_restaurar", kwargs={"uuid": self.cliente_arquivado.uuid})
        resposta = self.client.post(url)
        self.assertEqual(resposta.status_code, 302)

        self.cliente_arquivado.refresh_from_db()
        self.assertEqual(self.cliente_arquivado.status, Cliente.Status.ATIVO)
