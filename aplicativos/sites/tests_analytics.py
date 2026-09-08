"""
Testes automatizados do sistema de Analytics, Eventos e Métricas (Prompt 11).
"""

import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from aplicativos.clientes.models import Cliente
from aplicativos.sites.models import (
    EventoAnalitico,
    LinkInteligente,
    ProjetoSite,
    PublicacaoSite,
)
from aplicativos.sites.servicos_analytics import (
    gerar_token_clique,
    gerar_token_pageview,
    obter_metricas_globais,
    obter_metricas_link,
    obter_metricas_projeto,
    obter_metricas_smart_links_projeto,
    obter_serie_temporal_projeto,
    obter_top_componentes_projeto,
    registrar_evento,
    validar_token_evento,
)
from aplicativos.sites.servicos_links import criar_link_inteligente

Usuario = get_user_model()


class AnalyticsBaseTestCase(TestCase):
    """Base com fixtures e dados comuns para testes de analytics."""

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.admin = Usuario.objects.create_superuser(
            username="admin_analytics",
            email="admin_ana@teste.com",
            password="SenhaForteAdmin123!",
        )
        self.cliente = Cliente.objects.create(
            nome="Dra. Mariana Costa",
            email="mariana@clinica.com",
            documento="11144477735",
        )
        self.projeto = ProjetoSite.objects.create(
            cliente=self.cliente,
            nome="BioSite Dra Mariana",
            slug="dra-mariana",
            status=ProjetoSite.Status.PUBLICADO,
        )
        self.publicacao = PublicacaoSite.objects.create(
            projeto=self.projeto,
            numero_versao=1,
            snapshot={
                "configuracao_visual": {},
                "paginas": [
                    {
                        "slug": "",
                        "eh_inicial": True,
                        "secoes": [
                            {
                                "tipo": "hero",
                                "containers": [
                                    {
                                        "tipo_layout": "stack",
                                        "elementos": [
                                            {
                                                "tipo": "whatsapp",
                                                "conteudo": {
                                                    "numero": "5511999999999",
                                                    "texto": "Agendar WhatsApp",
                                                },
                                            }
                                        ],
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
            hash_conteudo="hash-mock-1",
            ativa=True,
        )
        self.projeto.publicacao_ativa = self.publicacao
        self.projeto.save()

        # Tag NFC e QR
        self.link_nfc = criar_link_inteligente(
            projeto=self.projeto,
            tipo=LinkInteligente.Tipo.NFC,
            nome="Cartão Principal Dra Mariana",
        )
        self.link_qr = criar_link_inteligente(
            projeto=self.projeto,
            tipo=LinkInteligente.Tipo.QR,
            nome="Placa Recepção QR",
        )


class TokenAssinadoTests(AnalyticsBaseTestCase):
    """Testes de assinatura criptográfica de tokens e integridade."""

    def test_geracao_e_validacao_token_pageview(self):
        token = gerar_token_pageview(self.projeto.id, self.publicacao.id, pagina_slug="contato")
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 20)

        dados = validar_token_evento(token)
        self.assertIsNotNone(dados)
        self.assertEqual(dados["p"], self.projeto.id)
        self.assertEqual(dados["v"], self.publicacao.id)
        self.assertEqual(dados["pg"], "contato")
        self.assertEqual(dados["t"], EventoAnalitico.TipoEvento.PAGE_VIEW)

    def test_geracao_e_validacao_token_clique(self):
        token = gerar_token_clique(
            self.projeto.id,
            self.publicacao.id,
            tipo_componente="WHATSAPP",
            elemento_id="elem_123",
            subitem_id="sub_cta",
        )
        self.assertIsInstance(token, str)

        dados = validar_token_evento(token)
        self.assertIsNotNone(dados)
        self.assertEqual(dados["p"], self.projeto.id)
        self.assertEqual(dados["v"], self.publicacao.id)
        self.assertEqual(dados["c"], "WHATSAPP")
        self.assertEqual(dados["e"], "elem_123")
        self.assertEqual(dados["s"], "sub_cta")
        self.assertEqual(dados["t"], EventoAnalitico.TipoEvento.COMPONENT_CLICK)

    def test_token_adulterado_rejeitado(self):
        token = gerar_token_pageview(self.projeto.id, self.publicacao.id)
        token_adulterado = token[:-5] + "XXXXX"
        dados = validar_token_evento(token_adulterado)
        self.assertIsNone(dados)

    def test_token_string_vazia_ou_invalida(self):
        self.assertIsNone(validar_token_evento(""))
        self.assertIsNone(validar_token_evento("token-nao-assinado-qualquer"))


class IngestionEndpointTests(AnalyticsBaseTestCase):
    """Testes do endpoint público de beacon /e/."""

    def test_ingestao_pageview_sucesso_retorna_204(self):
        token = gerar_token_pageview(self.projeto.id, self.publicacao.id)
        payload = json.dumps({"token": token})

        response = self.client.post(
            "/e/",
            data=payload,
            content_type="application/json",
            HTTP_USER_AGENT="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")

        # Verifica persistência no banco
        evento = EventoAnalitico.objects.filter(
            projeto=self.projeto, tipo_evento=EventoAnalitico.TipoEvento.PAGE_VIEW
        ).first()
        self.assertIsNotNone(evento)
        self.assertEqual(evento.publicacao, self.publicacao)

    def test_ingestao_clique_sucesso_retorna_204(self):
        token = gerar_token_clique(
            self.projeto.id,
            self.publicacao.id,
            tipo_componente="WHATSAPP",
            elemento_id="elem-btn-1",
        )
        payload = json.dumps({"token": token})

        response = self.client.post(
            "/e/",
            data=payload,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 204)

        evento = EventoAnalitico.objects.filter(
            projeto=self.projeto, tipo_evento=EventoAnalitico.TipoEvento.COMPONENT_CLICK
        ).first()
        self.assertIsNotNone(evento)
        self.assertEqual(evento.tipo_componente, "WHATSAPP")
        self.assertEqual(evento.elemento_uuid, "elem-btn-1")

    def test_ingestao_metodo_get_rejeitado(self):
        response = self.client.get("/e/")
        self.assertEqual(response.status_code, 405)

    def test_ingestao_payload_grande_rejeitado(self):
        token = gerar_token_pageview(self.projeto.id, self.publicacao.id)
        payload = json.dumps({"token": token, "lixo": "A" * 3000})

        response = self.client.post(
            "/e/",
            data=payload,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_ingestao_token_invalido_retorna_400(self):
        payload = json.dumps({"token": "token-falso-invalido"})
        response = self.client.post(
            "/e/",
            data=payload,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_ingestao_cookieless(self):
        token = gerar_token_pageview(self.projeto.id, self.publicacao.id)
        response = self.client.post(
            "/e/",
            data=json.dumps({"token": token}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 204)
        # Nenhuma sessão ou cookie de analytics é injetado
        self.assertNotIn("sessionid", response.cookies)
        self.assertNotIn("csrftoken", response.cookies)
        self.assertNotIn("analytics_id", response.cookies)

    def test_privacidade_sem_ip_e_sem_user_agent_no_banco(self):
        token = gerar_token_pageview(self.projeto.id, self.publicacao.id)
        self.client.post(
            "/e/",
            data=json.dumps({"token": token}),
            content_type="application/json",
            REMOTE_ADDR="198.51.100.42",
            HTTP_USER_AGENT="CustomMobileBrowser/1.0",
        )
        evento = EventoAnalitico.objects.last()
        self.assertIsNotNone(evento)
        # Verifica que IP e User-Agent NÃO constam em nenhum campo
        ctx = evento.contexto_minimo
        self.assertNotIn("198.51.100.42", str(ctx))
        self.assertNotIn("CustomMobileBrowser", str(ctx))

    def test_filtro_bots_user_agent(self):
        token = gerar_token_pageview(self.projeto.id, self.publicacao.id)
        # Simula Googlebot
        response = self.client.post(
            "/e/",
            data=json.dumps({"token": token}),
            content_type="application/json",
            HTTP_USER_AGENT="Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        )
        self.assertEqual(response.status_code, 204)
        # Nenhum evento deve ser persistido
        self.assertEqual(EventoAnalitico.objects.count(), 0)


class SmartLinkAnalyticsIntegrationTests(AnalyticsBaseTestCase):
    """Testes de registro analítico na camada de redirect de NFC e QR Code (Prompt 10 + 11)."""

    def test_acesso_nfc_registra_evento_smartlink_nfc(self):
        response = self.client.get(f"/n/{self.link_nfc.token}/")
        self.assertEqual(response.status_code, 302)

        evento = EventoAnalitico.objects.filter(
            tipo_evento=EventoAnalitico.TipoEvento.SMARTLINK_NFC
        ).first()
        self.assertIsNotNone(evento)
        self.assertEqual(evento.projeto, self.projeto)
        self.assertEqual(evento.link_inteligente, self.link_nfc)
        self.assertEqual(evento.origem, EventoAnalitico.OrigemAcesso.NFC)

    def test_acesso_qr_registra_evento_smartlink_qr(self):
        response = self.client.get(f"/q/{self.link_qr.token}/")
        self.assertEqual(response.status_code, 302)

        evento = EventoAnalitico.objects.filter(
            tipo_evento=EventoAnalitico.TipoEvento.SMARTLINK_QR
        ).first()
        self.assertIsNotNone(evento)
        self.assertEqual(evento.projeto, self.projeto)
        self.assertEqual(evento.link_inteligente, self.link_qr)
        self.assertEqual(evento.origem, EventoAnalitico.OrigemAcesso.QR)

    def test_redirect_fail_open_se_analytics_falhar(self):
        # Simula falha catastrófica no banco durante escrita do analytics
        with patch(
            "aplicativos.sites.views_redirecionamento.registrar_evento",
            side_effect=Exception("Database locked"),
        ):
            response = self.client.get(f"/n/{self.link_nfc.token}/")
            # O redirect DEVE continuar funcionando (HTTP 302)
            self.assertEqual(response.status_code, 302)

    def test_bot_em_smartlink_continua_redirecionando_sem_gravar_evento(self):
        response = self.client.get(
            f"/n/{self.link_nfc.token}/",
            HTTP_USER_AGENT="Twitterbot/1.0",
        )
        self.assertEqual(response.status_code, 302)
        # Bot não grava evento no banco
        self.assertEqual(EventoAnalitico.objects.count(), 0)


class PublicSiteViewAnalyticsTests(AnalyticsBaseTestCase):
    """Testes de inclusão de tokens e script na renderização pública do BioSite."""

    def test_public_site_contem_script_analytics_e_token(self):
        response = self.client.get(f"/b/{self.projeto.slug}/")
        self.assertEqual(response.status_code, 200)
        conteudo = response.content.decode("utf-8")

        self.assertIn("site-analytics.js", conteudo)
        self.assertIn("window.__BIO_ANALYTICS__", conteudo)
        self.assertIn("pageviewToken", conteudo)
        self.assertIn("data-event-token", conteudo)

    def test_preview_nao_contem_analytics(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("painel:site_preview", kwargs={"uuid": self.projeto.uuid})
        )
        self.assertEqual(response.status_code, 200)
        conteudo = response.content.decode("utf-8")
        # Modo preview não deve disparar analytics
        self.assertNotIn("site-analytics.js", conteudo)


class ServicesAnalyticsQueryTests(AnalyticsBaseTestCase):
    """Testes dos serviços de agregação e métricas do dashboard."""

    def setUp(self):
        super().setUp()
        agora = timezone.now()

        # Cria 10 pageviews
        for _ in range(10):
            EventoAnalitico.objects.create(
                projeto=self.projeto,
                publicacao=self.publicacao,
                tipo_evento=EventoAnalitico.TipoEvento.PAGE_VIEW,
                ocorrido_em=agora,
            )

        # Cria 3 acessos NFC
        for _ in range(3):
            EventoAnalitico.objects.create(
                projeto=self.projeto,
                tipo_evento=EventoAnalitico.TipoEvento.SMARTLINK_NFC,
                link_inteligente=self.link_nfc,
                origem=EventoAnalitico.OrigemAcesso.NFC,
                ocorrido_em=agora,
            )

        # Cria 2 acessos QR
        for _ in range(2):
            EventoAnalitico.objects.create(
                projeto=self.projeto,
                tipo_evento=EventoAnalitico.TipoEvento.SMARTLINK_QR,
                link_inteligente=self.link_qr,
                origem=EventoAnalitico.OrigemAcesso.QR,
                ocorrido_em=agora,
            )

        # Cria 4 cliques em WhatsApp
        for _ in range(4):
            EventoAnalitico.objects.create(
                projeto=self.projeto,
                publicacao=self.publicacao,
                tipo_evento=EventoAnalitico.TipoEvento.COMPONENT_CLICK,
                tipo_componente="WHATSAPP",
                elemento_uuid="btn-wa",
                ocorrido_em=agora,
            )

    def test_metricas_projeto_calculadas_corretamente(self):
        metricas = obter_metricas_projeto(self.projeto, periodo="30d")
        self.assertEqual(metricas["visualizacoes"], 10)
        self.assertEqual(metricas["acessos_nfc"], 3)
        self.assertEqual(metricas["acessos_qr"], 2)
        self.assertEqual(metricas["cliques_totais"], 4)
        self.assertEqual(metricas["cliques_whatsapp"], 4)
        # CTR = 4 cliques / 10 pageviews = 40.0%
        self.assertEqual(metricas["ctr_aproximado"], 40.0)

    def test_zero_division_em_ctr_quando_sem_pageviews(self):
        # Novo projeto sem nenhum evento
        novo_proj = ProjetoSite.objects.create(
            cliente=self.cliente,
            nome="Projeto Zerado",
            slug="projeto-zerado",
        )
        metricas = obter_metricas_projeto(novo_proj, periodo="30d")
        self.assertEqual(metricas["visualizacoes"], 0)
        self.assertEqual(metricas["cliques_totais"], 0)
        self.assertEqual(metricas["ctr_aproximado"], 0.0)
        self.assertEqual(metricas["ctr_whatsapp"], 0.0)

    def test_isolamento_de_metricas_entre_projetos(self):
        outro_proj = ProjetoSite.objects.create(
            cliente=self.cliente,
            nome="Outro Projeto B",
            slug="outro-projeto-b",
        )
        metricas_b = obter_metricas_projeto(outro_proj, periodo="30d")
        self.assertEqual(metricas_b["visualizacoes"], 0)
        self.assertEqual(metricas_b["acessos_nfc"], 0)

    def test_serie_temporal_agrupa_corretamente(self):
        serie = obter_serie_temporal_projeto(self.projeto, periodo="7d")
        self.assertIsInstance(serie, list)
        self.assertTrue(len(serie) >= 7)
        total_vis = sum(p["visualizacoes"] for p in serie)
        self.assertEqual(total_vis, 10)

    def test_top_componentes_ranking(self):
        top = obter_top_componentes_projeto(self.projeto, periodo="30d")
        self.assertTrue(len(top) >= 1)
        self.assertEqual(top[0]["tipo_componente"], "WHATSAPP")
        self.assertEqual(top[0]["total"], 4)

    def test_smart_links_desempenho_por_midia(self):
        links_resumo = obter_metricas_smart_links_projeto(self.projeto, periodo="30d")
        self.assertEqual(len(links_resumo), 2)
        link_nfc_dados = next(x for x in links_resumo if x["id"] == self.link_nfc.id)
        self.assertEqual(link_nfc_dados["total_acessos"], 3)

    def test_metricas_link_individual(self):
        m_nfc = obter_metricas_link(self.link_nfc)
        self.assertEqual(m_nfc["total"], 3)
        self.assertEqual(m_nfc["hoje"], 3)

    def test_metricas_globais_da_plataforma(self):
        globais = obter_metricas_globais(periodo="30d")
        self.assertEqual(globais["total_visualizacoes"], 10)
        self.assertEqual(globais["total_nfc"], 3)
        self.assertEqual(globais["total_qr"], 2)
        self.assertEqual(globais["total_cliques"], 4)


class DashboardsViewsPermissionsTests(AnalyticsBaseTestCase):
    """Testes de acesso e autenticação às views dos dashboards."""

    def test_usuario_anonimo_redirecionado_ao_login(self):
        res_global = self.client.get(reverse("painel:analytics_global"))
        self.assertEqual(res_global.status_code, 302)

        res_proj = self.client.get(
            reverse("painel:site_analytics", kwargs={"uuid": self.projeto.uuid})
        )
        self.assertEqual(res_proj.status_code, 302)

    def test_usuario_admin_acessa_dashboard_global(self):
        registrar_evento(
            projeto=self.projeto,
            tipo_evento=EventoAnalitico.TipoEvento.PAGE_VIEW,
            publicacao=self.publicacao,
        )
        self.client.force_login(self.admin)
        res = self.client.get(reverse("painel:analytics_global"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Analytics Global")
        self.assertContains(res, "Dra Mariana")

    def test_usuario_admin_acessa_dashboard_do_projeto(self):
        self.client.force_login(self.admin)
        res = self.client.get(reverse("painel:site_analytics", kwargs={"uuid": self.projeto.uuid}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "BioSite Dra Mariana")
        self.assertContains(res, "Visualizações")


class ManagementCommandVerificarAnalyticsTests(AnalyticsBaseTestCase):
    """Testes do comando de auditoria verificar_analytics."""

    def test_execucao_comando_verificar_analytics(self):
        # Registra evento normal
        registrar_evento(
            projeto=self.projeto,
            tipo_evento=EventoAnalitico.TipoEvento.PAGE_VIEW,
        )
        call_command("verificar_analytics")
        # Sem exceção levantada indica execução limpa
