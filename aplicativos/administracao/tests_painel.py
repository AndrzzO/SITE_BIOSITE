"""Testes automatizados para autenticação privada e workspace administrativo (Prompt 2)."""

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from aplicativos.administracao.servicos.rate_limit import ServicoRateLimitLogin

Usuario = get_user_model()


class AutenticacaoPrivadaTests(TestCase):
    """Testes dos fluxos de login, logout e controle de acesso do painel administrativo."""

    def setUp(self):
        cache.clear()
        self.senha_padrao = "SenhaForteSegura123!"

        # Operador administrativo staff
        self.admin_user = Usuario.objects.create_user(
            username="operador_admin",
            email="admin@biosite.local",
            password=self.senha_padrao,
            is_staff=True,
            is_active=True,
        )

        # Usuário inativo
        self.inactive_user = Usuario.objects.create_user(
            username="operador_inativo",
            email="inativo@biosite.local",
            password=self.senha_padrao,
            is_staff=True,
            is_active=False,
        )

        # Usuário comum (não staff)
        self.regular_user = Usuario.objects.create_user(
            username="usuario_comum",
            email="comum@biosite.local",
            password=self.senha_padrao,
            is_staff=False,
            is_active=True,
        )

    def tearDown(self):
        cache.clear()

    def test_tela_de_login_carrega_com_sucesso(self):
        """Verifica se a tela de login responde com HTTP 200 e campos esperados."""
        url = reverse("painel:login")
        resposta = self.client.get(url)

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Acesso Administrativo")
        self.assertContains(resposta, "E-mail ou Usuário")
        self.assertContains(resposta, "Senha")
        # Garante ausência estrita de links de auto-cadastro público
        self.assertNotContains(resposta, "Cadastre-se")
        self.assertNotContains(resposta, "Criar conta")

    def test_login_com_username_valido_redireciona_ao_workspace(self):
        """Valida autenticação com username válido."""
        url = reverse("painel:login")
        resposta = self.client.post(
            url,
            {
                "identificador": "operador_admin",
                "password": self.senha_padrao,
            },
        )

        self.assertRedirects(resposta, reverse("painel:sites"))
        # Confirma que a sessão do usuário foi autenticada
        self.assertTrue("_auth_user_id" in self.client.session)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.admin_user.pk)

    def test_login_com_email_valido_redireciona_ao_workspace(self):
        """Valida autenticação utilizando o endereço de e-mail."""
        url = reverse("painel:login")
        resposta = self.client.post(
            url,
            {
                "identificador": "admin@biosite.local",
                "password": self.senha_padrao,
            },
        )

        self.assertRedirects(resposta, reverse("painel:sites"))
        self.assertTrue("_auth_user_id" in self.client.session)

    def test_login_com_senha_incorreta_exibe_mensagem_generica(self):
        """Garante mensagem genérica de erro sem expor detalhes da conta."""
        url = reverse("painel:login")
        resposta = self.client.post(
            url,
            {
                "identificador": "operador_admin",
                "password": "SenhaErradaTotalmenteInvalida!",
            },
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Usuário ou senha inválidos.")
        self.assertFalse("_auth_user_id" in self.client.session)

    def test_login_com_usuario_inativo_falha(self):
        """Garante que usuários com is_active=False não conseguem autenticar."""
        url = reverse("painel:login")
        resposta = self.client.post(
            url,
            {
                "identificador": "operador_inativo",
                "password": self.senha_padrao,
            },
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Usuário ou senha inválidos.")
        self.assertFalse("_auth_user_id" in self.client.session)

    def test_usuario_autenticado_sem_staff_recebe_403(self):
        """Usuários que não possuem is_staff=True recebem 403 ao tentar acessar o painel."""
        self.client.force_login(self.regular_user)
        url = reverse("painel:sites")
        resposta = self.client.get(url)

        self.assertEqual(resposta.status_code, 403)

    def test_usuario_anonimo_e_redirecionado_ao_login(self):
        """Acesso anônimo a qualquer rota protegida do painel redireciona para login."""
        url = reverse("painel:sites")
        resposta = self.client.get(url)

        esperado = f"{reverse('painel:login')}?next={url}"
        self.assertRedirects(resposta, esperado)

    def test_logout_via_post_encerra_sessao_e_redireciona(self):
        """Logout encerra a sessão administrativa e redireciona ao login."""
        self.client.force_login(self.admin_user)
        url_logout = reverse("painel:logout")

        resposta = self.client.post(url_logout)
        self.assertRedirects(resposta, reverse("painel:login"))
        self.assertFalse("_auth_user_id" in self.client.session)

        # Verificar que rota privada não pode mais ser acessada
        resposta_apos = self.client.get(reverse("painel:sites"))
        self.assertEqual(resposta_apos.status_code, 302)

    def test_open_redirect_e_rejeitado_no_login(self):
        """Tentativa de open redirect para domínio externo é neutralizada."""
        url_login = f"{reverse('painel:login')}?next=https://site-malicioso-externo.com"
        resposta = self.client.post(
            url_login,
            {
                "identificador": "operador_admin",
                "password": self.senha_padrao,
            },
        )

        # Deve redirecionar para a rota padrão segura do workspace
        self.assertRedirects(resposta, reverse("painel:sites"))

    def test_open_redirect_interno_valido_e_respeitado(self):
        """Parâmetro next seguro interno é respeitado pós-autenticação."""
        next_valido = "/painel/sites/"
        url_login = f"{reverse('painel:login')}?next={next_valido}"
        resposta = self.client.post(
            url_login,
            {
                "identificador": "operador_admin",
                "password": self.senha_padrao,
            },
        )

        self.assertRedirects(resposta, next_valido)

    def test_usuario_ja_autenticado_ao_acessar_login_e_redirecionado(self):
        """Operador já autenticado acessando /painel/login/ é enviado ao workspace."""
        self.client.force_login(self.admin_user)
        url_login = reverse("painel:login")
        resposta = self.client.get(url_login)

        self.assertRedirects(resposta, reverse("painel:sites"))

    def test_workspace_exibe_estado_vazio_quando_sem_projetos(self):
        """Workspace Meus Sites exibe estado vazio limpo com botão de novo site."""
        self.client.force_login(self.admin_user)
        url = reverse("painel:sites")
        resposta = self.client.get(url)

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Meus Sites")
        self.assertContains(resposta, "Você ainda não criou nenhum site")
        self.assertContains(resposta, "Novo Site")

    def test_rate_limiting_bloqueia_apos_exceder_limite(self):
        """Exceder MAX_TENTATIVAS bloqueia tentativas subsequentes de login."""
        url = reverse("painel:login")
        ip = "192.168.1.100"

        # Simular 5 tentativas incorretas
        for i in range(ServicoRateLimitLogin.MAX_TENTATIVAS):
            resposta = self.client.post(
                url,
                {"identificador": "operador_admin", "password": f"SenhaErrada{i}!"},
                REMOTE_ADDR=ip,
            )
            self.assertEqual(resposta.status_code, 200)

        # 6ª tentativa deve ser bloqueada pelo rate limit
        resposta_bloqueada = self.client.post(
            url,
            {"identificador": "operador_admin", "password": self.senha_padrao},
            REMOTE_ADDR=ip,
        )

        self.assertEqual(resposta_bloqueada.status_code, 200)
        self.assertContains(resposta_bloqueada, "Muitas tentativas inválidas")
        self.assertFalse("_auth_user_id" in self.client.session)
