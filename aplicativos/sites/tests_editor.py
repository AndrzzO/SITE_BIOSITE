"""Testes automatizados completos do Editor Visual Mobile-First e Preview (Prompt 5)."""

import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from aplicativos.clientes.models import Cliente
from aplicativos.sites.models import ElementoSite, PaginaSite, ProjetoSite, SecaoSite
from aplicativos.sites.renderer import RenderizadorBioSite
from aplicativos.sites.servicos_estrutura import (
    criar_secao_com_container_padrao,
    garantir_pagina_inicial,
)

Usuario = get_user_model()


class EditorVisualTestCase(TestCase):
    """Base com dados de teste para o estúdio de edição visual e preview."""

    def setUp(self):
        self.client = Client()
        self.usuario = Usuario.objects.create_superuser(
            username="editor_admin",
            email="editor@teste.com",
            password="SenhaForte123!",
        )
        self.cliente_obj = Cliente.objects.create(nome="Cliente Studio Teste")
        self.projeto = ProjetoSite.objects.create(
            cliente=self.cliente_obj,
            nome="BioSite Visual Studio",
            slug="biosite-visual-studio",
            tipo="PORTFOLIO",
            status="rascunho",
        )

        # Outro projeto para testar segurança IDOR
        self.outro_cliente = Cliente.objects.create(nome="Outro Cliente")
        self.outro_projeto = ProjetoSite.objects.create(
            cliente=self.outro_cliente,
            nome="Outro BioSite",
            slug="outro-biosite",
            tipo="LINK_BIO",
            status="rascunho",
        )

        # Estrutura inicial do projeto principal
        self.pagina = garantir_pagina_inicial(self.projeto)
        self.pagina.secoes.all().delete()  # Limpa para controle exato nos testes
        self.secao, self.container = criar_secao_com_container_padrao(
            pagina=self.pagina,
            nome_interno="Hero Section",
            tipo=SecaoSite.Tipo.NORMAL,
        )
        self.elemento_titulo = ElementoSite.objects.create(
            container=self.container,
            tipo="TITULO",
            conteudo={"texto": "Meu Título Principal", "nivel": "h1"},
            estilos={"base": {"alinhamento": "center", "cor_texto": "#0f172a"}},
            ordem=10,
        )
        self.elemento_texto = ElementoSite.objects.create(
            container=self.container,
            tipo="TEXTO",
            conteudo={"texto": "Este é um parágrafo explicativo da minha bio."},
            estilos={"base": {"alinhamento": "left"}},
            ordem=20,
        )

        # Estrutura do outro projeto (para IDOR)
        self.outra_pagina = garantir_pagina_inicial(self.outro_projeto)
        self.outra_pagina.secoes.all().delete()
        self.outra_secao, self.outro_container = criar_secao_com_container_padrao(
            pagina=self.outra_pagina,
            nome_interno="Secao Alheia",
        )
        self.outro_elemento = ElementoSite.objects.create(
            container=self.outro_container,
            tipo="TITULO",
            conteudo={"texto": "Título Alheio", "nivel": "h2"},
            ordem=10,
        )


class EditorAcessoEPaginaTests(EditorVisualTestCase):
    """Testes de autenticação, carregamento de página e alternância no editor."""

    def test_acesso_anonimo_redireciona_para_login(self):
        url = reverse("painel:site_editor", kwargs={"uuid": self.projeto.uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/painel/login/", response.url)

    def test_acesso_autenticado_retorna_200_com_viewport_390px(self):
        self.client.force_login(self.usuario)
        url = reverse("painel:site_editor", kwargs={"uuid": self.projeto.uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "painel/sites/editor.html")
        self.assertContains(response, "BioSite Visual Studio")
        self.assertContains(response, 'data-viewport="390"')
        self.assertContains(response, "biosite-canvas-root")
        self.assertContains(response, "Meu Título Principal")

    def test_acesso_projeto_inexistente_retorna_404(self):
        self.client.force_login(self.usuario)
        url = reverse("painel:site_editor", kwargs={"uuid": "00000000-0000-0000-0000-000000000000"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_obter_dados_editor_json(self):
        self.client.force_login(self.usuario)
        url = reverse("painel:site_editor_dados", kwargs={"uuid": self.projeto.uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        dados = response.json()
        self.assertTrue(dados["ok"])
        self.assertEqual(dados["projeto"]["nome"], "BioSite Visual Studio")
        self.assertEqual(len(dados["paginas"]), 1)
        self.assertIn("catalogo_elementos", dados)

    def test_criar_nova_pagina_via_editor(self):
        self.client.force_login(self.usuario)
        url = reverse("painel:site_editor_pagina_criar", kwargs={"uuid": self.projeto.uuid})
        response = self.client.post(
            url,
            data=json.dumps({"titulo": "Sobre Mim", "slug": "sobre"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        dados = response.json()
        self.assertTrue(dados["ok"])
        self.assertEqual(dados["titulo"], "Sobre Mim")
        self.assertEqual(dados["slug"], "sobre")

        # Verifica se foi criada no banco
        self.assertTrue(PaginaSite.objects.filter(projeto=self.projeto, slug="sobre").exists())


class EditorSecoesTests(EditorVisualTestCase):
    """Testes de gerenciamento de seções (criar, mover, duplicar, excluir, propriedades)."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.usuario)

    def test_criar_secao(self):
        url = reverse("painel:site_editor_secao_criar", kwargs={"uuid": self.projeto.uuid})
        response = self.client.post(
            url,
            data=json.dumps(
                {
                    "pagina_id": self.pagina.id,
                    "nome_interno": "Nova Seção Galeria",
                    "tipo": "NORMAL",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        dados = response.json()
        self.assertTrue(dados["ok"])
        self.assertEqual(dados["nome_interno"], "Nova Seção Galeria")
        self.assertIn("editor-secao-wrapper", dados["html"])

    def test_reordenar_secoes(self):
        secao2, _ = criar_secao_com_container_padrao(self.pagina, "Segunda Seção")
        url = reverse("painel:site_editor_secao_mover", kwargs={"uuid": self.projeto.uuid})
        response = self.client.post(
            url,
            data=json.dumps(
                {
                    "pagina_id": self.pagina.id,
                    "ordem_ids": [secao2.id, self.secao.id],
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

        self.secao.refresh_from_db()
        secao2.refresh_from_db()
        self.assertLess(secao2.ordem, self.secao.ordem)

    def test_duplicar_secao(self):
        url = reverse(
            "painel:site_editor_secao_duplicar",
            kwargs={"uuid": self.projeto.uuid, "secao_id": self.secao.id},
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        dados = response.json()
        self.assertTrue(dados["ok"])
        nova_secao_id = dados["secao_id"]
        self.assertNotEqual(nova_secao_id, self.secao.id)
        self.assertEqual(SecaoSite.objects.filter(pagina=self.pagina).count(), 2)

    def test_excluir_secao(self):
        url = reverse(
            "painel:site_editor_secao_excluir",
            kwargs={"uuid": self.projeto.uuid, "secao_id": self.secao.id},
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertFalse(SecaoSite.objects.filter(id=self.secao.id).exists())

    def test_atualizar_propriedades_secao(self):
        url = reverse(
            "painel:site_editor_secao_propriedades",
            kwargs={"uuid": self.projeto.uuid, "secao_id": self.secao.id},
        )
        novos_estilos = {"base": {"cor_fundo": "#f8fafc", "padding_topo": 40}}
        response = self.client.post(
            url,
            data=json.dumps(
                {
                    "nome_interno": "Seção Atualizada",
                    "tipo": SecaoSite.Tipo.TELA_CHEIA,
                    "estilos": novos_estilos,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.secao.refresh_from_db()
        self.assertEqual(self.secao.nome_interno, "Seção Atualizada")
        self.assertEqual(self.secao.tipo, SecaoSite.Tipo.TELA_CHEIA)
        self.assertEqual(self.secao.estilos.get("base", {}).get("cor_fundo"), "#f8fafc")

    def test_seguranca_idor_secao_de_outro_projeto_retorna_404(self):
        # Tenta excluir seção do outro_projeto usando a rota do projeto principal
        url = reverse(
            "painel:site_editor_secao_excluir",
            kwargs={"uuid": self.projeto.uuid, "secao_id": self.outra_secao.id},
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)


class EditorElementosTests(EditorVisualTestCase):
    """Testes de manipulação e persistência de elementos (criar, mover, duplicar, autosave)."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.usuario)

    def test_criar_elemento(self):
        url = reverse("painel:site_editor_elemento_criar", kwargs={"uuid": self.projeto.uuid})
        response = self.client.post(
            url,
            data=json.dumps(
                {
                    "container_id": self.container.id,
                    "tipo": "BOTAO",
                    "ordem": 30,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        dados = response.json()
        self.assertTrue(dados["ok"])
        self.assertEqual(dados["tipo"], "BOTAO")
        self.assertIn("editor-elemento-wrapper", dados["html"])
        self.assertTrue(ElementoSite.objects.filter(id=dados["elemento_id"]).exists())

    def test_autosave_conteudo_e_estilos_elemento(self):
        url = reverse(
            "painel:site_editor_elemento_salvar",
            kwargs={"uuid": self.projeto.uuid},
        )
        novo_conteudo = {"texto": "Título Atualizado pelo Autosave", "nivel": "h2"}
        novos_estilos = {
            "base": {"alinhamento": "center", "cor_texto": "#3b82f6", "tamanho_fonte": 28},
            "desktop": {"tamanho_fonte": 36},
        }

        response = self.client.post(
            url,
            data=json.dumps(
                {
                    "elemento_id": self.elemento_titulo.id,
                    "conteudo": novo_conteudo,
                    "estilos": novos_estilos,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

        self.elemento_titulo.refresh_from_db()
        self.assertEqual(self.elemento_titulo.conteudo["texto"], "Título Atualizado pelo Autosave")
        self.assertEqual(self.elemento_titulo.conteudo["nivel"], "h2")
        self.assertEqual(self.elemento_titulo.estilos["desktop"]["tamanho_fonte"], 36)

    def test_sanitizacao_xss_e_protocolo_inseguro_em_elemento(self):
        # Tenta salvar botão com protocolo inseguro javascript:
        elemento_btn = ElementoSite.objects.create(
            container=self.container,
            tipo="BOTAO",
            conteudo={"rotulo": "Clique Aqui", "url": "https://google.com"},
            ordem=30,
        )
        url = reverse(
            "painel:site_editor_elemento_salvar",
            kwargs={"uuid": self.projeto.uuid},
        )
        response = self.client.post(
            url,
            data=json.dumps(
                {
                    "elemento_id": elemento_btn.id,
                    "conteudo": {"rotulo": "Ataque", "url": "javascript:alert(1)"},
                }
            ),
            content_type="application/json",
        )
        # O validador rejeita com status 422
        self.assertEqual(response.status_code, 422)
        self.assertFalse(response.json()["ok"])

    def test_mover_elemento_para_outro_container(self):
        secao2, container2 = criar_secao_com_container_padrao(self.pagina, "Segunda Seção")
        url = reverse("painel:site_editor_elemento_mover", kwargs={"uuid": self.projeto.uuid})

        response = self.client.post(
            url,
            data=json.dumps(
                {
                    "elemento_id": self.elemento_titulo.id,
                    "novo_container_id": container2.id,
                    "ordem_ids": [self.elemento_titulo.id],
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

        self.elemento_titulo.refresh_from_db()
        self.assertEqual(self.elemento_titulo.container_id, container2.id)

    def test_duplicar_elemento(self):
        url = reverse(
            "painel:site_editor_elemento_duplicar",
            kwargs={"uuid": self.projeto.uuid, "elemento_id": self.elemento_titulo.id},
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        dados = response.json()
        self.assertTrue(dados["ok"])
        novo_id = dados["elemento_id"]
        self.assertNotEqual(novo_id, self.elemento_titulo.id)
        self.assertEqual(ElementoSite.objects.filter(container=self.container).count(), 3)

    def test_excluir_elemento(self):
        url = reverse(
            "painel:site_editor_elemento_excluir",
            kwargs={"uuid": self.projeto.uuid, "elemento_id": self.elemento_texto.id},
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertFalse(ElementoSite.objects.filter(id=self.elemento_texto.id).exists())

    def test_seguranca_idor_elemento_de_outro_projeto(self):
        url = reverse(
            "painel:site_editor_elemento_salvar",
            kwargs={"uuid": self.projeto.uuid},
        )
        response = self.client.post(
            url,
            data=json.dumps(
                {
                    "elemento_id": self.outro_elemento.id,
                    "conteudo": {"texto": "Hacked"},
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)


class PreviewFielTests(EditorVisualTestCase):
    """Testes de fidelidade e ausência de controles administrativos na rota de Preview."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.usuario)

    def test_preview_retorna_200_e_renderiza_conteudo(self):
        url = reverse("painel:site_preview", kwargs={"uuid": self.projeto.uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "painel/sites/preview.html")
        self.assertContains(response, "Meu Título Principal")
        self.assertContains(response, "Este é um parágrafo explicativo")

    def test_preview_livre_de_controles_e_wrappers_administrativos(self):
        """Garante que a visualização fiel não contenha nenhum artefato ou botão de edição."""
        url = reverse("painel:site_preview", kwargs={"uuid": self.projeto.uuid})
        response = self.client.get(url)

        conteudo_html = response.content.decode("utf-8")
        self.assertNotIn("editor-secao-drag-handle", conteudo_html)
        self.assertNotIn("editor-elemento-toolbar", conteudo_html)
        self.assertNotIn("btn-acao-elem", conteudo_html)
        self.assertNotIn("btn-acao-container", conteudo_html)
        self.assertNotIn("btn-add-secao-inline", conteudo_html)
        self.assertNotIn("sortable-container-elementos", conteudo_html)
        self.assertNotIn("editor-mode", conteudo_html)
        self.assertIn("preview-mode", conteudo_html)

    def test_renderizador_paridade_estilos_mobile_first(self):
        """Verifica a conversão precisa de estilos mobile e desktop via RenderizadorBioSite."""
        renderer = RenderizadorBioSite(modo="preview")
        estilos = {
            "base": {"alinhamento": "center", "tamanho_fonte": 20, "cor_texto": "#111827"},
            "desktop": {"alinhamento": "left", "tamanho_fonte": 32},
        }
        css = renderer.converter_estilos_para_css(estilos, ".teste-seletor")
        self.assertIn(
            ".teste-seletor { text-align: center; font-size: 20px; color: #111827; }", css
        )
        self.assertIn("@media (min-width: 768px)", css)
        self.assertIn("text-align: left; font-size: 32px;", css)
