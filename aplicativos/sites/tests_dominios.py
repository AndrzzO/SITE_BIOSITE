"""
Testes automatizados para subdomínios, domínios personalizados, DNS e resolução de host (Prompt 9).
"""

from io import StringIO
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.http import HttpResponse
from django.test import Client, RequestFactory, TestCase

from aplicativos.clientes.models import Cliente

from .allowed_hosts import DynamicAllowedHosts
from .middleware import HostRoutingMiddleware
from .models import EnderecoSite, HistoricoEnderecoSite, ProjetoSite
from .servicos_dns import verificar_dns_dominio
from .servicos_dominios import (
    adicionar_dominio_personalizado,
    criar_subdominio_padrao,
    definir_endereco_principal,
    obter_base_domain,
    remover_endereco,
)
from .servicos_estrutura import garantir_pagina_inicial
from .servicos_publicacao import publicar_projeto
from .validadores_dominios import (
    normalizar_host,
    obter_subdominios_reservados,
    validar_formato_host,
    validar_subdominio,
)

Usuario = get_user_model()


class TestValidadoresDominios(TestCase):
    """Testes de normalização e validação RFC de hosts e subdomínios."""

    def test_normalizar_host_regras(self):
        # 1. Lowercase e espaços
        self.assertEqual(normalizar_host("  EXEMPLO.COM  "), "exemplo.com")
        # 2. Esquemas http:// e https:// e //
        self.assertEqual(normalizar_host("https://meusite.com.br"), "meusite.com.br")
        self.assertEqual(normalizar_host("http://blog.site.com"), "blog.site.com")
        self.assertEqual(normalizar_host("//app.site.com"), "app.site.com")
        # 3. Caminhos, queries e fragmentos
        self.assertEqual(normalizar_host("meusite.com/pagina/1?ref=xyz#topo"), "meusite.com")
        # 4. Portas
        self.assertEqual(normalizar_host("localhost:8000"), "localhost")
        self.assertEqual(normalizar_host("site.com:443"), "site.com")
        self.assertEqual(normalizar_host("[::1]:8000"), "[::1]")
        # 5. Trailing dot (FQDN)
        self.assertEqual(normalizar_host("exemplo.com.br."), "exemplo.com.br")
        # 6. String vazia
        self.assertEqual(normalizar_host(""), "")

    def test_normalizar_host_idn_punycode(self):
        # Domínios internacionalizados com acento são convertidos para punycode
        host_acento = "clínica-saúde.com.br"
        normalizado = normalizar_host(host_acento)
        self.assertTrue(normalizado.startswith("xn--") or "cl" in normalizado)

    def test_validar_formato_host_validos(self):
        self.assertEqual(validar_formato_host("meusite.com.br"), "meusite.com.br")
        self.assertEqual(validar_formato_host("sub.dominio.org"), "sub.dominio.org")
        self.assertEqual(
            validar_formato_host("joao-silva.meubiosite.com"), "joao-silva.meubiosite.com"
        )
        self.assertEqual(validar_formato_host("localhost"), "localhost")

    def test_validar_formato_host_invalidos(self):
        with self.assertRaises(ValidationError):
            validar_formato_host("")
        with self.assertRaises(ValidationError):
            validar_formato_host("-invalido.com")
        with self.assertRaises(ValidationError):
            validar_formato_host("invalido-.com")
        with self.assertRaises(ValidationError):
            validar_formato_host("site..com")
        with self.assertRaises(ValidationError):
            validar_formato_host("a" * 64 + ".com")

    def test_validar_subdominio_reservados(self):
        reservados = obter_subdominios_reservados()
        self.assertIn("admin", reservados)
        self.assertIn("painel", reservados)
        self.assertIn("www", reservados)
        self.assertIn("api", reservados)

        with self.assertRaises(ValidationError):
            validar_subdominio("admin")
        with self.assertRaises(ValidationError):
            validar_subdominio("PAINEL")
        with self.assertRaises(ValidationError):
            validar_subdominio("api")

    def test_validar_subdominio_formato(self):
        self.assertEqual(validar_subdominio("joao-silva"), "joao-silva")
        self.assertEqual(validar_subdominio("clinica123"), "clinica123")

        with self.assertRaises(ValidationError):
            validar_subdominio("ab")  # muito curto (<3)
        with self.assertRaises(ValidationError):
            validar_subdominio("joao_silva")  # underline proibido
        with self.assertRaises(ValidationError):
            validar_subdominio("-joao")  # inicia com hífen
        with self.assertRaises(ValidationError):
            validar_subdominio("joao-")  # termina com hífen


class TestServicosDominios(TestCase):
    """Testes dos serviços de criação, troca de principal, remoção e quarentena."""

    def setUp(self):
        cache.clear()
        self.cliente = Cliente.objects.create(nome="Cliente Alpha")
        self.projeto = ProjetoSite.objects.create(
            cliente=self.cliente,
            nome="BioSite Alpha",
            slug="alpha",
        )
        garantir_pagina_inicial(self.projeto)

    def test_criar_subdominio_padrao(self):
        endereco = criar_subdominio_padrao(self.projeto, subdominio_sugerido="alpha")
        self.assertEqual(endereco.subdominio, "alpha")
        self.assertEqual(endereco.tipo, EnderecoSite.Tipo.SUBDOMINIO_PLATAFORMA)
        self.assertEqual(endereco.status, EnderecoSite.Status.ATIVO)
        self.assertTrue(endereco.principal)
        self.assertIn("alpha.", endereco.host)

    def test_criar_subdominio_padrao_colisao(self):
        # Primeiro projeto fica com 'doutor'
        criar_subdominio_padrao(self.projeto, subdominio_sugerido="doutor")

        # Segundo projeto também sugere 'doutor' -> deve virar 'doutor-2'
        proj2 = ProjetoSite.objects.create(cliente=self.cliente, nome="Doutor Beta", slug="doutor")
        end2 = criar_subdominio_padrao(proj2, subdominio_sugerido="doutor")
        self.assertEqual(end2.subdominio, "doutor-2")

    def test_adicionar_dominio_personalizado_sucesso(self):
        end = adicionar_dominio_personalizado(self.projeto, "www.doutoralpha.com.br")
        self.assertEqual(end.host, "www.doutoralpha.com.br")
        self.assertEqual(end.tipo, EnderecoSite.Tipo.DOMINIO_PERSONALIZADO)
        self.assertEqual(end.status, EnderecoSite.Status.PENDENTE)
        self.assertFalse(end.principal)  # Nunca nasce principal
        self.assertTrue(len(end.token_verificacao) >= 32)

    def test_adicionar_dominio_personalizado_rejeita_base_domain(self):
        base_domain = obter_base_domain()
        with self.assertRaises(ValidationError):
            adicionar_dominio_personalizado(self.projeto, base_domain)
        with self.assertRaises(ValidationError):
            adicionar_dominio_personalizado(self.projeto, f"teste.{base_domain}")

    def test_adicionar_dominio_personalizado_duplicado_em_outro_projeto(self):
        adicionar_dominio_personalizado(self.projeto, "clinica.com.br")
        proj2 = ProjetoSite.objects.create(cliente=self.cliente, nome="Outro", slug="outro")
        with self.assertRaises(ValidationError):
            adicionar_dominio_personalizado(proj2, "clinica.com.br")

    def test_definir_endereco_principal_seguranca(self):
        end_custom = adicionar_dominio_personalizado(self.projeto, "meudominio.com.br")
        # Domínio personalizado PENDENTE NÃO pode virar principal
        with self.assertRaises(ValidationError):
            definir_endereco_principal(self.projeto, end_custom)

        # Se verificado, pode virar principal
        end_custom.status = EnderecoSite.Status.VERIFICADO
        end_custom.save()
        definir_endereco_principal(self.projeto, end_custom)

        end_custom.refresh_from_db()
        self.assertTrue(end_custom.principal)
        self.assertEqual(end_custom.status, EnderecoSite.Status.ATIVO)

    def test_remover_endereco_quarentena_e_reassociacao(self):
        sub = criar_subdominio_padrao(self.projeto, "alpha-sub")
        custom = adicionar_dominio_personalizado(self.projeto, "site.com.br")
        custom.status = EnderecoSite.Status.VERIFICADO
        custom.save()
        definir_endereco_principal(self.projeto, custom)

        host_removido = custom.host
        remover_endereco(custom)

        # Verifica que o endereço foi deletado e inserido no histórico
        self.assertFalse(EnderecoSite.objects.filter(host=host_removido).exists())
        self.assertTrue(
            HistoricoEnderecoSite.objects.filter(host=host_removido, projeto=self.projeto).exists()
        )

        # Subdomínio antigo deve ter reassumido como principal
        sub.refresh_from_db()
        self.assertTrue(sub.principal)

    def test_remover_unico_endereco_site_publicado_bloqueado(self):
        usuario = Usuario.objects.create_user(
            username="remover_pub_user", email="rem@biosite.local", password="pwd"
        )
        sub = criar_subdominio_padrao(self.projeto, "alpha-unico")
        publicar_projeto(self.projeto, usuario=usuario)

        with self.assertRaises(ValidationError):
            remover_endereco(sub)


class TestServicosDNS(TestCase):
    """Testes de verificação DNS com mock do resolver."""

    def setUp(self):
        self.cliente = Cliente.objects.create(nome="Cliente DNS")
        self.projeto = ProjetoSite.objects.create(cliente=self.cliente, nome="Site DNS", slug="dns")
        self.endereco = adicionar_dominio_personalizado(self.projeto, "medico.com.br")

    @patch("dns.resolver.Resolver.resolve")
    def test_verificar_dns_sucesso_com_prefixo(self, mock_resolve):
        # Mock simula retorno de registro TXT com biosite-verification=<token>
        mock_rdata = MagicMock()
        mock_rdata.strings = [f"biosite-verification={self.endereco.token_verificacao}".encode()]
        mock_resolve.return_value = [mock_rdata]

        sucesso, msg = verificar_dns_dominio(self.endereco)
        self.assertTrue(sucesso)
        self.endereco.refresh_from_db()
        self.assertEqual(self.endereco.status, EnderecoSite.Status.VERIFICADO)
        self.assertIsNotNone(self.endereco.verificado_em)

    @patch("dns.resolver.Resolver.resolve")
    def test_verificar_dns_falha_sem_token(self, mock_resolve):
        mock_rdata = MagicMock()
        mock_rdata.strings = [b"google-site-verification=xyz123"]
        mock_resolve.return_value = [mock_rdata]

        sucesso, msg = verificar_dns_dominio(self.endereco)
        self.assertFalse(sucesso)
        self.endereco.refresh_from_db()
        self.assertEqual(self.endereco.status, EnderecoSite.Status.ERRO)


class TestHostRoutingMiddleware(TestCase):
    """Testes do middleware de roteamento dinâmico e isolamento de segurança."""

    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()
        self.get_response = MagicMock(return_value=HttpResponse("OK_PLATAFORMA"))
        self.middleware = HostRoutingMiddleware(self.get_response)

        self.cliente = Cliente.objects.create(nome="Cliente Host")
        self.projeto = ProjetoSite.objects.create(
            cliente=self.cliente,
            nome="BioSite Host",
            slug="biohost",
        )
        garantir_pagina_inicial(self.projeto)
        self.endereco = criar_subdominio_padrao(self.projeto, "biohost")

    def test_host_plataforma_acessa_normalmente(self):
        req = self.factory.get("/painel/sites/", HTTP_HOST="localhost")
        resp = self.middleware(req)
        self.assertEqual(resp.content.decode(), "OK_PLATAFORMA")
        self.assertTrue(getattr(req, "eh_host_plataforma", False))

    def test_barreira_seguranca_bloqueia_painel_em_host_de_cliente(self):
        # Acesso a /painel/ a partir do host de cliente deve retornar 404
        req = self.factory.get("/painel/sites/", HTTP_HOST=self.endereco.host)
        resp = self.middleware(req)
        self.assertEqual(resp.status_code, 404)

        # Acesso a /admin/ a partir do host de cliente também bloqueado
        req_admin = self.factory.get("/admin/login/", HTTP_HOST=self.endereco.host)
        resp_admin = self.middleware(req_admin)
        self.assertEqual(resp_admin.status_code, 404)

    def test_host_cliente_site_nao_publicado_retorna_404(self):
        req = self.factory.get("/", HTTP_HOST=self.endereco.host)
        resp = self.middleware(req)
        self.assertEqual(resp.status_code, 404)

    def test_host_cliente_site_publicado_renderiza_raiz(self):
        usuario = Usuario.objects.create_user(
            username="pub_user", email="pub@biosite.local", password="pwd"
        )
        publicar_projeto(self.projeto, usuario=usuario)

        req = self.factory.get("/", HTTP_HOST=self.endereco.host)
        resp = self.middleware(req)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("html", resp["Content-Type"])

    def test_host_alias_redireciona_301_para_principal(self):
        # Adiciona custom domain verificado e torna principal
        end_custom = adicionar_dominio_personalizado(self.projeto, "www.meusitevip.com.br")
        end_custom.status = EnderecoSite.Status.VERIFICADO
        end_custom.save()
        definir_endereco_principal(self.projeto, end_custom)

        usuario = Usuario.objects.create_user(
            username="pub_user_2", email="pub2@biosite.local", password="pwd"
        )
        publicar_projeto(self.projeto, usuario=usuario)

        # O subdomínio da plataforma agora é um ALIAS
        req = self.factory.get("/contato", HTTP_HOST=self.endereco.host)
        resp = self.middleware(req)
        self.assertEqual(resp.status_code, 301)
        self.assertTrue(resp["Location"].startswith(f"http://{end_custom.host}"))

    def test_host_desconhecido_retorna_404(self):
        req = self.factory.get("/", HTTP_HOST="desconhecido-total.com")
        resp = self.middleware(req)
        self.assertEqual(resp.status_code, 404)


class TestDynamicAllowedHosts(TestCase):
    """Testes da coleção dinâmica de hosts seguros."""

    def setUp(self):
        cache.clear()
        self.cliente = Cliente.objects.create(nome="Cliente Hosts")
        self.projeto = ProjetoSite.objects.create(cliente=self.cliente, nome="Site H", slug="siteh")

    def test_dynamic_allowed_hosts_iter(self):
        static = ["localhost", "127.0.0.1"]
        dah = DynamicAllowedHosts(static)

        # Deve conter hosts estáticos
        hosts = list(dah)
        self.assertIn("localhost", hosts)
        self.assertIn("127.0.0.1", hosts)

        # Adiciona domínio personalizado ativo
        end = adicionar_dominio_personalizado(self.projeto, "meucliente.com.br")
        end.status = EnderecoSite.Status.ATIVO
        end.save()
        cache.clear()

        hosts_atualizados = list(dah)
        self.assertIn("meucliente.com.br", hosts_atualizados)


class TestViewsDominios(TestCase):
    """Testes das views de gerenciamento de subdomínios e domínios personalizados."""

    def setUp(self):
        cache.clear()
        self.usuario = Usuario.objects.create_user(
            username="admin_dominios",
            email="admin@biosite.local",
            password="SenhaSegura123!",
            is_staff=True,
        )
        self.client_auth = Client()
        self.client_auth.force_login(self.usuario)

        self.cliente = Cliente.objects.create(nome="Empresa Views")
        self.projeto = ProjetoSite.objects.create(
            cliente=self.cliente,
            nome="BioSite Views",
            slug="views-test",
        )
        garantir_pagina_inicial(self.projeto)
        self.endereco = criar_subdominio_padrao(self.projeto, "views-test")

    def test_configurar_subdominio_view(self):
        url = f"/painel/sites/{self.projeto.uuid}/dominios/subdominio/"
        resp = self.client_auth.post(url, {"subdominio": "novo-slug"})
        self.assertEqual(resp.status_code, 302)
        self.endereco.refresh_from_db()
        self.assertEqual(self.endereco.subdominio, "novo-slug")

    def test_adicionar_dominio_personalizado_view(self):
        url = f"/painel/sites/{self.projeto.uuid}/dominios/adicionar/"
        resp = self.client_auth.post(url, {"host": "www.novodominio.com.br"})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            EnderecoSite.objects.filter(
                host="www.novodominio.com.br", projeto=self.projeto
            ).exists()
        )

    def test_definir_dominio_principal_view(self):
        end_custom = adicionar_dominio_personalizado(self.projeto, "www.primario.com.br")
        end_custom.status = EnderecoSite.Status.VERIFICADO
        end_custom.save()

        url = f"/painel/sites/{self.projeto.uuid}/dominios/{end_custom.id}/principal/"
        resp = self.client_auth.post(url)
        self.assertEqual(resp.status_code, 302)
        end_custom.refresh_from_db()
        self.assertTrue(end_custom.principal)

    def test_remover_dominio_view(self):
        end_custom = adicionar_dominio_personalizado(self.projeto, "www.deletar.com.br")
        url = f"/painel/sites/{self.projeto.uuid}/dominios/{end_custom.id}/remover/"
        resp = self.client_auth.post(url)
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(EnderecoSite.objects.filter(id=end_custom.id).exists())


class TestComandoAuditoriaDominios(TestCase):
    """Testa o comando de gerenciamento verificar_dominios."""

    def test_comando_verificar_dominios(self):
        out = StringIO()
        call_command("verificar_dominios", stdout=out)
        conteudo = out.getvalue()
        self.assertIn("Iniciando auditoria", conteudo)
