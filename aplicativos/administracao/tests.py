"""Testes automatizados para o modelo de usuário customizado UsuarioAdministrativo."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from aplicativos.administracao.models import UsuarioAdministrativo


class UsuarioAdministrativoTests(TestCase):
    """Testes de criação, validação e integridade do UsuarioAdministrativo."""

    def setUp(self):
        self.user_model = get_user_model()

    def test_auth_user_model_aponta_para_usuario_administrativo(self):
        """Garante que o modelo ativo de autenticação do Django é o modelo customizado."""
        self.assertEqual(self.user_model, UsuarioAdministrativo)

    def test_criar_usuario_administrativo_com_sucesso(self):
        """Valida a criação de um usuário comum com senha com hash correto."""
        usuario = self.user_model.objects.create_user(
            username="administrador_teste",
            email="admin@biosite.local",
            password="SenhaSeguraForte123!",
        )

        self.assertEqual(usuario.username, "administrador_teste")
        self.assertEqual(usuario.email, "admin@biosite.local")
        self.assertTrue(usuario.is_active)
        self.assertFalse(usuario.is_staff)
        self.assertFalse(usuario.is_superuser)
        # Garante que a senha foi hasheada e não está em texto plano
        self.assertTrue(usuario.check_password("SenhaSeguraForte123!"))
        self.assertNotEqual(usuario.password, "SenhaSeguraForte123!")

    def test_criar_superuser_com_sucesso(self):
        """Valida a criação de um superusuário administrativo."""
        superuser = self.user_model.objects.create_superuser(
            username="superadmin",
            email="superadmin@biosite.local",
            password="SuperSenhaForte123!",
        )

        self.assertEqual(superuser.username, "superadmin")
        self.assertEqual(superuser.email, "superadmin@biosite.local")
        self.assertTrue(superuser.is_active)
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.check_password("SuperSenhaForte123!"))

    def test_criacao_sem_email_lanca_erro(self):
        """Valida que o e-mail é estritamente obrigatório."""
        with self.assertRaises(ValueError):
            self.user_model.objects.create_user(
                username="sem_email",
                email="",
                password="Senha123!",
            )

    def test_criacao_sem_username_lanca_erro(self):
        """Valida que o username é obrigatório."""
        with self.assertRaises(ValueError):
            self.user_model.objects.create_user(
                username="",
                email="teste@biosite.local",
                password="Senha123!",
            )

    def test_superuser_com_is_staff_falso_lanca_erro(self):
        """Valida que is_staff deve ser True para superusuário."""
        with self.assertRaises(ValueError):
            self.user_model.objects.create_superuser(
                username="super_invalido",
                email="invalido@biosite.local",
                password="Senha123!",
                is_staff=False,
            )

    def test_superuser_com_is_superuser_falso_lanca_erro(self):
        """Valida que is_superuser deve ser True para superusuário."""
        with self.assertRaises(ValueError):
            self.user_model.objects.create_superuser(
                username="super_invalido2",
                email="invalido2@biosite.local",
                password="Senha123!",
                is_superuser=False,
            )

    def test_representacao_em_string(self):
        """Valida o método __str__ do modelo."""
        usuario = self.user_model.objects.create_user(
            username="gestor",
            email="gestor@biosite.local",
            password="Senha123!",
            first_name="André",
            last_name="Silva",
        )
        self.assertEqual(str(usuario), "André Silva")

        usuario2 = self.user_model.objects.create_user(
            username="apenas_username",
            email="usuario2@biosite.local",
            password="Senha123!",
        )
        self.assertEqual(str(usuario2), "apenas_username")
