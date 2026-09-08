"""
Suíte de testes de Segurança, Hardening, Anti-IDOR, XSS, Mobile QA e E2E (Prompt 12).
"""

import json

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from aplicativos.clientes.models import Cliente
from aplicativos.sites.elementos.tipos import (
    ElementoBotao,
    ElementoTexto,
    ElementoTitulo,
    ElementoWhatsApp,
)
from aplicativos.sites.models import (
    LinkInteligente,
    ProjetoSite,
)
from aplicativos.sites.renderer import RenderizadorBioSite
from aplicativos.sites.servicos_analytics import (
    gerar_token_clique,
    gerar_token_pageview,
    obter_metricas_projeto,
)
from aplicativos.sites.servicos_links import criar_link_inteligente
from aplicativos.sites.servicos_publicacao import (
    publicar_projeto,
    rollback_publicacao,
)
from aplicativos.sites.servicos_templates import instanciar_template

Usuario = get_user_model()


class BaseHardeningTestCase(TestCase):
    """Base com fixtures e isolamento de cache para testes de hardening."""

    def setUp(self):
        cache.clear()
        self.client = Client()

        # Usuário Administrador / Staff
        self.admin = Usuario.objects.create_superuser(
            username="admin_audit",
            email="admin_audit@biosite.com",
            password="SenhaAuditForte123!",
        )

        # Usuário Comum sem permissão staff
        self.usuario_comum = Usuario.objects.create_user(
            username="usuario_comum",
            email="comum@biosite.com",
            password="SenhaComumForte123!",
            is_staff=False,
        )

        # Cliente e Projetos
        self.cliente = Cliente.objects.create(
            nome="Dra. Beatriz Santos",
            email="beatriz@clinica.com",
            documento="11144477735",
        )
        self.projeto = ProjetoSite.objects.create(
            cliente=self.cliente,
            nome="BioSite Dra Beatriz",
            slug="dra-beatriz",
            status=ProjetoSite.Status.RASCUNHO,
        )

        # Estrutura base de página para o projeto
        from aplicativos.sites.models import (
            ContainerSite,
            ElementoSite,
            PaginaSite,
            SecaoSite,
        )

        self.pagina = PaginaSite.objects.create(
            projeto=self.projeto,
            titulo="Início",
            slug="",
            eh_inicial=True,
            ordem=0,
            ativa=True,
        )
        self.secao = SecaoSite.objects.create(
            pagina=self.pagina,
            nome_interno="Hero",
            ordem=0,
            ativa=True,
        )
        self.container = ContainerSite.objects.create(
            secao=self.secao,
            ordem=0,
            ativo=True,
        )
        self.elemento_titulo = ElementoSite.objects.create(
            container=self.container,
            tipo="titulo",
            conteudo={"texto": "Dra. Beatriz Santos", "nivel": "h1"},
            ordem=0,
            ativo=True,
        )
        self.elemento_whatsapp = ElementoSite.objects.create(
            container=self.container,
            tipo="whatsapp",
            conteudo={"numero": "5511999998888", "texto": "Falar no WhatsApp"},
            ordem=1,
            ativo=True,
        )


class AccessControlMatrixTests(BaseHardeningTestCase):
    """Auditoria de Controle de Acesso e Matriz de Autorização (Prompt items 29-32, 319-320)."""

    def test_anonimo_bloqueado_em_rotas_privadas(self):
        rotas_privadas = [
            reverse("painel:sites"),
            reverse("painel:site_novo"),
            reverse("painel:site_detalhe", kwargs={"uuid": self.projeto.uuid}),
            reverse("painel:site_editor", kwargs={"uuid": self.projeto.uuid}),
            reverse("painel:site_preview", kwargs={"uuid": self.projeto.uuid}),
            reverse("painel:site_publicar", kwargs={"uuid": self.projeto.uuid}),
            reverse("painel:site_analytics", kwargs={"uuid": self.projeto.uuid}),
            reverse("painel:clientes_lista"),
            reverse("painel:templates_lista"),
            reverse("painel:links_lista"),
            reverse("painel:analytics_global"),
        ]

        for rota in rotas_privadas:
            res = self.client.get(rota)
            self.assertEqual(
                res.status_code,
                302,
                f"Rota privada {rota} permitiu acesso a usuário anônimo!",
            )
            self.assertIn("/painel/login/", res.headers.get("Location", ""))

    def test_usuario_autenticado_sem_staff_bloqueado(self):
        self.client.force_login(self.usuario_comum)
        rotas_privadas = [
            reverse("painel:sites"),
            reverse("painel:site_detalhe", kwargs={"uuid": self.projeto.uuid}),
            reverse("painel:site_editor", kwargs={"uuid": self.projeto.uuid}),
            reverse("painel:site_analytics", kwargs={"uuid": self.projeto.uuid}),
            reverse("painel:analytics_global"),
        ]

        for rota in rotas_privadas:
            res = self.client.get(rota)
            # O sistema deve redirecionar para login ou retornar 403
            self.assertIn(
                res.status_code,
                (302, 403),
                f"Usuário não-staff acessou {rota} com status {res.status_code}!",
            )

    def test_admin_acessa_rotas_privadas_com_sucesso(self):
        self.client.force_login(self.admin)
        rotas_privadas = [
            reverse("painel:sites"),
            reverse("painel:site_detalhe", kwargs={"uuid": self.projeto.uuid}),
            reverse("painel:site_editor", kwargs={"uuid": self.projeto.uuid}),
            reverse("painel:clientes_lista"),
            reverse("painel:templates_lista"),
            reverse("painel:links_lista"),
            reverse("painel:analytics_global"),
        ]

        for rota in rotas_privadas:
            res = self.client.get(rota)
            self.assertEqual(
                res.status_code,
                200,
                f"Admin legítimo teve acesso negado a {rota}!",
            )


class XSSSanitizationTests(BaseHardeningTestCase):
    """Testes de Sanitização contra Injeção de XSS em Componentes Editáveis (Prompt items 37-43)."""

    def test_xss_em_elemento_titulo(self):
        el = ElementoTitulo()
        from types import SimpleNamespace

        mock_elem = SimpleNamespace(
            conteudo={"texto": "<script>alert('xss-titulo')</script>", "nivel": "h1"},
            uuid="11111111-1111-1111-1111-111111111111",
        )
        html = el.render(mock_elem)

        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;alert(&#x27;xss-titulo&#x27;)&lt;/script&gt;", html)

    def test_xss_em_elemento_texto(self):
        el = ElementoTexto()
        from types import SimpleNamespace

        mock_elem = SimpleNamespace(
            conteudo={"texto": "<img src=x onerror=alert('xss-texto')>"},
            uuid="22222222-2222-2222-2222-222222222222",
        )
        html = el.render(mock_elem)

        self.assertNotIn("<img src=x", html)
        self.assertIn("&lt;img src=x onerror=alert(&#x27;xss-texto&#x27;)&gt;", html)

    def test_protocolo_javascript_bloqueado_em_botao(self):
        el = ElementoBotao()
        with self.assertRaises(ValidationError):
            el.validar_conteudo({"texto": "Botão Perigoso", "url": "javascript:alert(1)"})

        with self.assertRaises(ValidationError):
            el.validar_conteudo({"texto": "Botão Perigoso", "url": "vbscript:msgbox(1)"})

        with self.assertRaises(ValidationError):
            el.validar_conteudo({"texto": "Botão Perigoso", "url": "data:text/html,xss"})

    def test_sintaxe_html_limpa_em_ctas_rastreaveis(self):
        from types import SimpleNamespace

        el_wpp = ElementoWhatsApp()
        mock_wpp = SimpleNamespace(
            conteudo={
                "numero": "5511999999999",
                "texto": "WhatsApp Seguro",
                "largura_total": True,
            },
            uuid="33333333-3333-3333-3333-333333333333",
        )
        contexto = {"gerar_token_clique": lambda tipo, el_id, sub_id=None: "token_seguro_123"}
        html = el_wpp.render(mock_wpp, contexto=contexto)
        # Assegura que class="... btn-whatsapp btn-full-width" possui aspas de fechamento corretas
        self.assertIn('class="elemento-botao biosite-btn btn-whatsapp btn-full-width"', html)
        self.assertIn('data-event-token="token_seguro_123"', html)


class OpenRedirectAndHostSecurityTests(BaseHardeningTestCase):
    """Testes contra Open Redirect e Host Header Poisoning (Prompt items 48-62)."""

    def test_open_redirect_no_login_bloqueado(self):
        urls_maliciosas = [
            "https://evil.com",
            "http://phishing.com/roubo",
            "//evil.com",
            "javascript:alert(1)",
        ]
        for url in urls_maliciosas:
            res = self.client.post(
                reverse("painel:login"),
                data={
                    "identificador": self.admin.username,
                    "password": "SenhaAuditForte123!",
                    "next": url,
                },
            )
            # Deve redirecionar para /painel/sites/, nunca para o host externo
            self.assertEqual(res.status_code, 302)
            self.assertEqual(res.headers.get("Location"), reverse("painel:sites"))

    def test_host_desconhecido_retorna_404_neutro(self):
        res = self.client.get("/", HTTP_HOST="host-invasor-desconhecido.com")
        self.assertEqual(res.status_code, 404)
        conteudo = res.content.decode("utf-8", errors="ignore")
        self.assertTrue(
            "Host inválido." in conteudo or "não configurado" in conteudo,
            f"Resposta inesperada para host desconhecido: {conteudo}",
        )

    def test_smart_link_sem_open_redirect_arbitrario(self):
        link = criar_link_inteligente(projeto=self.projeto, tipo=LinkInteligente.Tipo.NFC)
        res = self.client.get(f"/n/{link.token}/?url=https://evil.com", HTTP_HOST="localhost")
        # Sem publicação ativa, retorna 404 neutro
        self.assertEqual(res.status_code, 404)


class MobileQAPerformanceTests(BaseHardeningTestCase):
    """Testes de Mobile QA, responsividade e viewport (Prompt items 164-175, 540-545)."""

    def test_viewports_mobile_suportados_no_renderizador(self):
        pub = publicar_projeto(self.projeto, usuario=self.admin)
        renderer = RenderizadorBioSite(modo="publico")
        html = renderer.renderizar_snapshot(pub.snapshot)

        # 1. Verifica container de viewport controlado
        self.assertIn("biosite-container", html)
        self.assertIn("--largura-maxima-mobile", html)

        # 2. Testa larguras de viewport mobile especificadas
        viewports_criticos = [320, 360, 375, 390, 393, 412, 430]
        for largura in viewports_criticos:
            # Garante que nenhum CSS injeta largura fixa maior que o viewport
            self.assertNotIn(f"width: {largura + 100}px", html)

        # 3. Viewport e safe area no HTML público
        res = self.client.get(f"/b/{self.projeto.slug}/", HTTP_HOST="localhost")
        self.assertEqual(res.status_code, 200)
        html_publico = res.content.decode("utf-8")
        self.assertIn("env(safe-area-inset-bottom", html_publico)
        self.assertIn("viewport", html_publico)
        self.assertIn("width=device-width", html_publico)


class EndToEndCompleteWorkflowTests(BaseHardeningTestCase):
    """Teste End-to-End cobrindo o ciclo de vida completo da plataforma (Prompt item 316, 582)."""

    def test_ciclo_de_vida_completo_e2e(self):
        # 1. Login Administrativo
        login_res = self.client.post(
            reverse("painel:login"),
            data={
                "identificador": self.admin.username,
                "password": "SenhaAuditForte123!",
            },
        )
        self.assertEqual(login_res.status_code, 302)

        # 2. Criar Cliente
        cliente_res = self.client.post(
            reverse("painel:cliente_novo"),
            data={
                "nome": "Dr. E2E Teste",
                "email": "e2e@clinica.com",
                "documento": "11144477735",
            },
        )
        self.assertEqual(cliente_res.status_code, 302)
        cliente_e2e = Cliente.objects.get(email="e2e@clinica.com")

        # 3. Criar BioSite a partir de Template
        from aplicativos.sites.models import TemplateSite

        tmpl = TemplateSite.objects.filter(slug="biosite-minimal").first()
        if tmpl:
            projeto_e2e = instanciar_template(
                tmpl,
                cliente=cliente_e2e,
                nome="BioSite E2E Completo",
                slug="e2e-completo",
            )
        else:
            projeto_e2e = ProjetoSite.objects.create(
                cliente=cliente_e2e,
                nome="BioSite E2E Completo",
                slug="e2e-completo",
            )
            # Cria página mínima
            from aplicativos.sites.models import (
                ContainerSite,
                ElementoSite,
                PaginaSite,
                SecaoSite,
            )

            p = PaginaSite.objects.create(
                projeto=projeto_e2e, titulo="Home", slug="", eh_inicial=True
            )
            s = SecaoSite.objects.create(pagina=p, nome_interno="Hero")
            c = ContainerSite.objects.create(secao=s)
            ElementoSite.objects.create(
                container=c,
                tipo="titulo",
                conteudo={"texto": "Dr. E2E", "nivel": "h1"},
            )
            ElementoSite.objects.create(
                container=c,
                tipo="whatsapp",
                conteudo={"numero": "5511999997777", "texto": "WhatsApp E2E"},
            )

        # 4. Preview do BioSite
        preview_res = self.client.get(
            reverse("painel:site_preview", kwargs={"uuid": projeto_e2e.uuid})
        )
        self.assertEqual(preview_res.status_code, 200)
        self.assertContains(preview_res, "Dr. E2E")

        # 5. Publicar Versão 1
        pub_v1 = publicar_projeto(projeto_e2e, usuario=self.admin)
        self.assertEqual(pub_v1.numero_versao, 1)
        projeto_e2e.refresh_from_db()
        self.assertTrue(projeto_e2e.esta_publicado())

        # 6. Acessar Site Público
        site_res = self.client.get(f"/b/{projeto_e2e.slug}/", HTTP_HOST="localhost")
        self.assertEqual(site_res.status_code, 200)
        self.assertContains(site_res, "Dr. E2E")

        # 7. Alterar Rascunho e Confirmar Imutabilidade da Produção
        cfg = projeto_e2e.configuracao_visual
        cfg.cor_primaria = "#ff0000"
        cfg.save()
        self.assertTrue(projeto_e2e.tem_alteracoes_nao_publicadas())

        # Produção v1 deve continuar com o snapshot antigo inalterado
        pub_v1.refresh_from_db()
        self.assertNotEqual(
            pub_v1.snapshot.get("configuracao_visual", {}).get("cor_primaria"),
            "#ff0000",
        )

        # 8. Publicar Versão 2
        pub_v2 = publicar_projeto(projeto_e2e, usuario=self.admin)
        self.assertEqual(pub_v2.numero_versao, 2)

        # 9. Rollback para Versão 1 (Gera Versão 3 com conteúdo da v1)
        pub_v3 = rollback_publicacao(projeto_e2e, pub_v1, usuario=self.admin)
        self.assertEqual(pub_v3.numero_versao, 3)
        self.assertEqual(pub_v3.hash_conteudo, pub_v1.hash_conteudo)

        # 10. Criar Tag NFC e QR Code
        link_nfc = criar_link_inteligente(
            projeto=projeto_e2e,
            tipo=LinkInteligente.Tipo.NFC,
            nome="Cartão NFC E2E",
        )
        link_qr = criar_link_inteligente(
            projeto=projeto_e2e,
            tipo=LinkInteligente.Tipo.QR,
            nome="Placa QR E2E",
        )

        # 11. Acessar NFC (HTTP 302 Found)
        nfc_res = self.client.get(f"/n/{link_nfc.token}/", HTTP_HOST="localhost")
        self.assertEqual(nfc_res.status_code, 302)
        self.assertIn(f"/b/{projeto_e2e.slug}/", nfc_res.headers.get("Location", ""))

        # 12. Acessar QR Code (HTTP 302 Found)
        qr_res = self.client.get(f"/q/{link_qr.token}/", HTTP_HOST="localhost")
        self.assertEqual(qr_res.status_code, 302)

        # 13. Ingestão de PageView e Clique via Beacon POST /e/
        token_pv = gerar_token_pageview(projeto_e2e.id, pub_v3.id, "")
        pv_res = self.client.post(
            "/e/",
            data=json.dumps({"token": token_pv}),
            content_type="application/json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(pv_res.status_code, 204)

        token_clk = gerar_token_clique(
            projeto_e2e.id,
            pub_v3.id,
            "11111111-1111-1111-1111-111111111111",
            "whatsapp",
        )
        clk_res = self.client.post(
            "/e/",
            data=json.dumps({"token": token_clk}),
            content_type="application/json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(clk_res.status_code, 204)

        # 14. Verificar Métricas no Analytics
        cache.clear()
        metricas = obter_metricas_projeto(projeto_e2e, "hoje")
        self.assertGreaterEqual(metricas["visualizacoes"], 1)
        self.assertGreaterEqual(metricas["acessos_nfc"], 1)
        self.assertGreaterEqual(metricas["acessos_qr"], 1)
        self.assertGreaterEqual(metricas["cliques_totais"], 1)

        # 15. Acessar Dashboard do Projeto
        dash_res = self.client.get(
            reverse("painel:site_analytics", kwargs={"uuid": projeto_e2e.uuid})
        )
        self.assertEqual(dash_res.status_code, 200)
        self.assertContains(dash_res, "BioSite E2E Completo")
        self.assertContains(dash_res, "Visualizações")
