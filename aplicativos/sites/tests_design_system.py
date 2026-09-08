"""Testes automatizados completos para o Design System, Componentes Premium e Upload de Mídia (Prompt 6)."""

import io
import uuid

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from PIL import Image

from aplicativos.clientes.models import Cliente
from aplicativos.sites.elementos import registro_elementos
from aplicativos.sites.elementos.base import (
    calcular_contraste_wcag,
    calcular_luminancia_relativa,
)
from aplicativos.sites.models import (
    ConfiguracaoVisualProjeto,
    ContainerSite,
    ElementoSite,
    MidiaSite,
    PaginaSite,
    ProjetoSite,
    SecaoSite,
    garantir_configuracao_visual,
    validar_cor_hex,
)
from aplicativos.sites.renderer import RenderizadorBioSite, renderizar_pagina
from aplicativos.sites.servicos_midia import criar_midia_projeto

Usuario = get_user_model()


def criar_imagem_em_memoria(
    formato: str = "PNG", cor: str = "blue", tamanho: tuple[int, int] = (100, 100)
) -> io.BytesIO:
    """Gera um buffer de imagem válido em memória para testes."""
    buffer = io.BytesIO()
    img = Image.new("RGB", tamanho, color=cor)
    img.save(buffer, format=formato)
    buffer.seek(0)
    return buffer


class DesignSystemTokensTests(TestCase):
    """Testes de modelo, tokens CSS e geração de estilos da identidade visual."""

    def setUp(self):
        self.cliente = Cliente.objects.create(nome="Cliente Design")
        self.projeto = ProjetoSite.objects.create(
            cliente=self.cliente,
            nome="Projeto Design",
            slug="projeto-design",
        )

    def test_configuracao_visual_padrao_criada_automaticamente(self):
        config = garantir_configuracao_visual(self.projeto)
        self.assertIsNotNone(config)
        self.assertEqual(config.cor_primaria, "#2563eb")
        self.assertEqual(config.cor_fundo, "#ffffff")
        self.assertEqual(config.radius_padrao, "12px")
        self.assertEqual(config.sombra_padrao, "suave")
        self.assertEqual(config.largura_maxima_mobile, 390)

    def test_obter_tokens_css_retorna_dicionario_completo(self):
        config = garantir_configuracao_visual(self.projeto)
        tokens = config.obter_tokens_css()
        self.assertIn("--cor-primaria", tokens)
        self.assertIn("--cor-secundaria", tokens)
        self.assertIn("--cor-fundo", tokens)
        self.assertIn("--cor-superficie", tokens)
        self.assertIn("--cor-texto", tokens)
        self.assertIn("--fonte-principal", tokens)
        self.assertIn("--fonte-titulos", tokens)
        self.assertIn("--radius-padrao", tokens)
        self.assertIn("--sombra-padrao", tokens)
        self.assertIn("--largura-maxima-mobile", tokens)

    def test_gerar_bloco_css_formata_custom_properties(self):
        config = garantir_configuracao_visual(self.projeto)
        config.cor_primaria = "#10b981"
        config.save()
        bloco_css = config.gerar_bloco_css()
        self.assertIn(":root, .biosite-canvas-root", bloco_css)
        self.assertIn("--cor-primaria: #10b981;", bloco_css)
        self.assertIn("--radius-padrao: 12px;", bloco_css)

    def test_validar_cor_hex(self):
        # Válidos
        self.assertIsNone(validar_cor_hex("#fff"))
        self.assertIsNone(validar_cor_hex("#10b981"))
        self.assertIsNone(validar_cor_hex("#AABBCC"))

        # Inválidos
        with self.assertRaises(ValidationError):
            validar_cor_hex("10b981")
        with self.assertRaises(ValidationError):
            validar_cor_hex("#zzzzzz")
        with self.assertRaises(ValidationError):
            validar_cor_hex("rgb(0,0,0)")


class CalculoContrasteWcagTests(TestCase):
    """Testes para cálculo matemático de contraste WCAG 2.1."""

    def test_contraste_preto_e_branco_maximo(self):
        resultado = calcular_contraste_wcag("#ffffff", "#000000")
        self.assertAlmostEqual(resultado["ratio"], 21.0, places=1)
        self.assertTrue(resultado["adequado_texto_normal"])
        self.assertFalse(resultado["alerta"])

    def test_contraste_mesma_cor_minimo(self):
        resultado = calcular_contraste_wcag("#ffffff", "#ffffff")
        self.assertAlmostEqual(resultado["ratio"], 1.0, places=1)
        self.assertFalse(resultado["adequado_texto_normal"])
        self.assertTrue(resultado["alerta"])

    def test_luminancia_relativa(self):
        lum_branco = calcular_luminancia_relativa("#ffffff")
        lum_preto = calcular_luminancia_relativa("#000000")
        self.assertEqual(lum_branco, 1.0)
        self.assertEqual(lum_preto, 0.0)

    def test_fallback_cor_invalida(self):
        resultado = calcular_contraste_wcag("invalido", "#000000")
        self.assertEqual(resultado["ratio"], 11.0)
        self.assertTrue(resultado["adequado_texto_normal"])


class NovosComponentesPremiumTests(TestCase):
    """Testes dos componentes adicionados e aprimorados no catálogo do Prompt 6."""

    def setUp(self):
        self.cliente = Cliente.objects.create(nome="Cliente Componentes")
        self.projeto = ProjetoSite.objects.create(
            cliente=self.cliente,
            nome="Projeto Componentes",
            slug="projeto-comp",
        )
        self.pagina = PaginaSite.objects.create(
            projeto=self.projeto,
            titulo="Home",
            slug="home",
            eh_inicial=True,
        )
        self.secao = SecaoSite.objects.create(
            pagina=self.pagina,
            nome_interno="Principal",
            ordem=1,
        )
        self.container = ContainerSite.objects.create(
            secao=self.secao,
            ordem=1,
        )

    def test_elemento_whatsapp_normalizacao_e_cta(self):
        elem = ElementoSite(
            container=self.container,
            tipo="WHATSAPP",
            conteudo={
                "numero": "+55 (11) 98765-4321",
                "mensagem": "Olá! Gostaria de um orçamento.",
                "texto": "Falar no WhatsApp",
                "estilo_botao": "flutuante",
            },
        )
        elem.full_clean()
        elem.save()

        definicao = registro_elementos.obter("whatsapp")
        html = definicao.render(elem)
        self.assertIn("5511987654321", html)
        self.assertIn("wa.me/5511987654321", html)
        self.assertIn("Ol%C3%A1%21%20Gostaria%20de%20um%20or%C3%A7amento.", html)
        self.assertIn("biosite-whatsapp-flutuante", html)

    def test_elemento_whatsapp_rejeita_numero_invalido(self):
        elem = ElementoSite(
            container=self.container,
            tipo="WHATSAPP",
            conteudo={"numero": "sem-numeros", "texto": "Zap"},
        )
        with self.assertRaises(ValidationError):
            elem.full_clean()

    def test_elemento_telefone_render(self):
        elem = ElementoSite(
            container=self.container,
            tipo="TELEFONE",
            conteudo={"numero": "(11) 98888-7777", "texto": "Ligue Agora"},
        )
        elem.full_clean()
        elem.save()

        definicao = registro_elementos.obter("telefone")
        html = definicao.render(elem)
        self.assertIn('href="tel:11988887777"', html)
        self.assertIn("Ligue Agora", html)

    def test_elemento_email_validacao_e_render(self):
        elem_invalido = ElementoSite(
            container=self.container,
            tipo="EMAIL",
            conteudo={"email": "email-invalido", "texto": "Contato"},
        )
        with self.assertRaises(ValidationError):
            elem_invalido.full_clean()

        elem_valido = ElementoSite(
            container=self.container,
            tipo="EMAIL",
            conteudo={
                "email": "contato@empresa.com",
                "texto": "Enviar Mensagem",
                "assunto": "Parceria",
            },
        )
        elem_valido.full_clean()
        elem_valido.save()

        definicao = registro_elementos.obter("email")
        html = definicao.render(elem_valido)
        self.assertIn('href="mailto:contato@empresa.com?subject=Parceria"', html)
        self.assertIn("Enviar Mensagem", html)

    def test_elemento_website_render(self):
        elem = ElementoSite(
            container=self.container,
            tipo="WEBSITE",
            conteudo={
                "url": "https://meubiosite.com.br",
                "texto": "Visite Nosso Portal",
            },
        )
        elem.full_clean()
        elem.save()

        definicao = registro_elementos.obter("website")
        html = definicao.render(elem)
        self.assertIn('href="https://meubiosite.com.br"', html)
        self.assertIn("Visite Nosso Portal", html)

    def test_elemento_redes_sociais_render_multicanais(self):
        elem = ElementoSite(
            container=self.container,
            tipo="REDES_SOCIAIS",
            conteudo={
                "itens": [
                    {"rede": "instagram", "url": "https://instagram.com/meu_insta"},
                    {"rede": "youtube", "url": "https://youtube.com/@meucanal"},
                    {"rede": "linkedin", "url": "https://linkedin.com/in/meu-perfil"},
                ],
                "formato": "icones",
            },
        )
        elem.full_clean()
        elem.save()

        definicao = registro_elementos.obter("redes_sociais")
        html = definicao.render(elem)
        self.assertIn("https://instagram.com/meu_insta", html)
        self.assertIn("https://youtube.com/@meucanal", html)
        self.assertIn("https://linkedin.com/in/meu-perfil", html)
        self.assertIn("formato-icones", html)

    def test_elemento_agendamento_externo_render(self):
        elem = ElementoSite(
            container=self.container,
            tipo="AGENDAMENTO_EXTERNO",
            conteudo={
                "url": "https://calendar.google.com/calendar/u/0/appointments/schedules/123",
                "texto": "Agendar Consulta",
            },
        )
        elem.full_clean()
        elem.save()

        definicao = registro_elementos.obter("agendamento_externo")
        html = definicao.render(elem)
        self.assertIn("Agendar Consulta", html)
        self.assertIn("calendar.google.com", html)

    def test_elemento_mapa_render_sem_api_paga(self):
        elem = ElementoSite(
            container=self.container,
            tipo="MAPA",
            conteudo={
                "endereco": "Av. Paulista, 1000 - São Paulo, SP",
                "texto": "Ver Localização no Mapa",
            },
        )
        elem.full_clean()
        elem.save()

        definicao = registro_elementos.obter("mapa")
        html = definicao.render(elem)
        self.assertIn("https://www.google.com/maps/search/?api=1&amp;query=", html)
        self.assertIn("Ver Localização no Mapa", html)

    def test_elemento_servicos_render(self):
        elem = ElementoSite(
            container=self.container,
            tipo="SERVICOS",
            conteudo={
                "itens": [
                    {
                        "titulo": "Consultoria VIP",
                        "descricao": "1 hora de mentoria dedicada.",
                        "preco": "R$ 450",
                        "link_cta": "https://wa.me/5511999999999",
                        "texto_cta": "Contratar",
                    }
                ]
            },
        )
        elem.full_clean()
        elem.save()

        definicao = registro_elementos.obter("servicos")
        html = definicao.render(elem)
        self.assertIn("Consultoria VIP", html)
        self.assertIn("R$ 450", html)
        self.assertIn("Contratar", html)

    def test_elemento_galeria_render_grid_e_scroll(self):
        elem_grid = ElementoSite(
            container=self.container,
            tipo="GALERIA",
            conteudo={
                "layout": "grid",
                "colunas": 3,
                "imagens": [
                    {"url": "https://exemplo.com/1.jpg", "alt": "Foto 1"},
                    {"url": "https://exemplo.com/2.jpg", "alt": "Foto 2"},
                ],
            },
        )
        elem_grid.full_clean()
        definicao = registro_elementos.obter("galeria")
        html_grid = definicao.render(elem_grid)
        self.assertIn("galeria-grid", html_grid)
        self.assertIn("colunas-3", html_grid)

        elem_carrossel = ElementoSite(
            container=self.container,
            tipo="GALERIA",
            conteudo={
                "layout": "carrossel",
                "imagens": [
                    {"url": "https://exemplo.com/1.jpg", "alt": "Slide 1"},
                ],
            },
        )
        elem_carrossel.full_clean()
        html_carrossel = definicao.render(elem_carrossel)
        self.assertIn("galeria-carrossel", html_carrossel)

    def test_elemento_avatar_render(self):
        elem = ElementoSite(
            container=self.container,
            tipo="AVATAR",
            conteudo={
                "url": "https://exemplo.com/foto.jpg",
                "alt": "Dra. Maria",
                "forma": "circulo",
                "tamanho": 120,
                "borda": True,
            },
        )
        elem.full_clean()
        definicao = registro_elementos.obter("avatar")
        html = definicao.render(elem)
        self.assertIn("avatar-circulo", html)
        self.assertIn("avatar-borda", html)
        self.assertIn("width:120px", html)

    def test_elemento_divisor_render(self):
        elem = ElementoSite(
            container=self.container,
            tipo="DIVISOR",
            conteudo={
                "estilo": "dashed",
                "espessura": 2,
                "largura": "80%",
            },
        )
        elem.full_clean()
        definicao = registro_elementos.obter("divisor")
        html = definicao.render(elem)
        self.assertIn("<hr", html)
        self.assertIn("border-top: 2px dashed", html)


class EstilosAvancadosERendererTests(TestCase):
    """Testes de renderização com tokens de design e classes sem markup administrativo no preview."""

    def setUp(self):
        self.cliente = Cliente.objects.create(nome="Cliente Render")
        self.projeto = ProjetoSite.objects.create(
            cliente=self.cliente,
            nome="Projeto Render",
            slug="projeto-render",
        )
        self.pagina = PaginaSite.objects.create(
            projeto=self.projeto,
            titulo="Início",
            slug="inicio",
            eh_inicial=True,
        )
        self.secao = SecaoSite.objects.create(
            pagina=self.pagina,
            nome_interno="Hero",
            ordem=1,
        )
        self.container = ContainerSite.objects.create(
            secao=self.secao,
            ordem=1,
        )
        self.elemento = ElementoSite.objects.create(
            container=self.container,
            tipo="TITULO",
            ordem=1,
            conteudo={"texto": "Meu BioSite VIP", "nivel": "h1"},
            estilos={
                "base": {
                    "sombra": "forte",
                    "animacao": "fade_up",
                    "estilo_borda": "solid",
                    "largura_borda": 2,
                    "cor_borda": "#2563eb",
                }
            },
        )

    def test_renderizar_pagina_injeta_tokens_css(self):
        html_editor = renderizar_pagina(self.pagina, modo_editor=True)
        self.assertIn('id="biosite-tokens-css"', html_editor)
        self.assertIn("--cor-primaria:", html_editor)

        html_preview = renderizar_pagina(self.pagina, modo_editor=False)
        self.assertIn('id="biosite-tokens-css"', html_preview)
        self.assertIn("--cor-primaria:", html_preview)

    def test_preview_livre_de_markup_administrativo(self):
        html_preview = renderizar_pagina(self.pagina, modo_editor=False)
        self.assertNotIn("data-elemento-id", html_preview)
        self.assertNotIn("data-container-id", html_preview)
        self.assertNotIn("data-secao-id", html_preview)
        self.assertNotIn("elemento-wrapper", html_preview)
        self.assertIn("Meu BioSite VIP", html_preview)

    def test_estilos_avancados_convertidos_em_css(self):
        self.elemento.estilos = {
            "base": {
                "sombra": "forte",
                "animacao": "fade-up",
                "estilo_borda": "solid",
                "largura_borda": 2,
                "cor_borda": "#2563eb",
            }
        }
        self.elemento.save()
        renderizador = RenderizadorBioSite(modo="preview")
        css = renderizador.converter_estilos_para_css(self.elemento.estilos, ".elemento-1")
        self.assertIn("box-shadow: 0 12px 28px -6px", css)
        self.assertIn("animation: biositeFadeInUp", css)
        self.assertIn("border-style: solid", css)


class MidiaSiteUploadESegurancaTests(TestCase):
    """Testes de segurança de upload, Pillow sanitization, conversão WebP e IDOR."""

    def setUp(self):
        self.client = Client()
        self.usuario = Usuario.objects.create_user(
            username="operador_midia",
            email="midia@teste.com",
            password="SenhaForte123!",
            is_staff=True,
        )
        self.client.force_login(self.usuario)

        self.cliente = Cliente.objects.create(nome="Cliente Mídia")
        self.projeto1 = ProjetoSite.objects.create(
            cliente=self.cliente,
            nome="Projeto 1",
            slug="proj-1",
        )

    def test_upload_imagem_valida_converte_webp(self):
        buffer = criar_imagem_em_memoria("PNG", "blue", (200, 200))
        arquivo = SimpleUploadedFile("foto.png", buffer.read(), content_type="image/png")

        url = reverse("painel:site_editor_midia_upload", kwargs={"uuid": self.projeto1.uuid})
        response = self.client.post(url, {"arquivo": arquivo, "titulo": "Foto de Perfil"})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["midia"]["largura"], 200)
        self.assertEqual(data["midia"]["altura"], 200)

        # Verifica banco de dados
        midia = MidiaSite.objects.get(id=data["midia"]["id"])
        self.assertEqual(midia.projeto, self.projeto1)
        self.assertTrue(midia.arquivo.name.endswith(".webp"))
        self.assertEqual(midia.mime_type, "image/webp")

    def test_upload_rejeita_arquivo_falso_executavel(self):
        conteudo_falso = b"MZ\x90\x00\x03\x00\x00\x00"  # Executável disfarçado
        arquivo_falso = SimpleUploadedFile("virus.jpg", conteudo_falso, content_type="image/jpeg")

        url = reverse("painel:site_editor_midia_upload", kwargs={"uuid": self.projeto1.uuid})
        response = self.client.post(url, {"arquivo": arquivo_falso})

        self.assertEqual(response.status_code, 422)
        self.assertFalse(response.json()["ok"])

    def test_upload_rejeita_svg(self):
        svg_conteudo = b'<svg><script>alert("xss")</script></svg>'
        arquivo_svg = SimpleUploadedFile("imagem.svg", svg_conteudo, content_type="image/svg+xml")

        url = reverse("painel:site_editor_midia_upload", kwargs={"uuid": self.projeto1.uuid})
        response = self.client.post(url, {"arquivo": arquivo_svg})

        self.assertEqual(response.status_code, 422)
        self.assertFalse(response.json()["ok"])

    def test_upload_sem_arquivo(self):
        url = reverse("painel:site_editor_midia_upload", kwargs={"uuid": self.projeto1.uuid})
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])

    def test_upload_uuid_inexistente_retorna_404(self):
        buffer = criar_imagem_em_memoria("JPEG", "green", (50, 50))
        arquivo = SimpleUploadedFile("teste.jpg", buffer.read(), content_type="image/jpeg")

        url = reverse("painel:site_editor_midia_upload", kwargs={"uuid": uuid.uuid4()})
        response = self.client.post(url, {"arquivo": arquivo})
        self.assertEqual(response.status_code, 404)

    def test_listar_midias_projeto(self):
        buffer = criar_imagem_em_memoria("PNG", "yellow", (100, 100))
        arquivo = SimpleUploadedFile("galeria.png", buffer.read(), content_type="image/png")
        criar_midia_projeto(self.projeto1, arquivo)

        url = reverse("painel:site_editor_midia_listar", kwargs={"uuid": self.projeto1.uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(len(data["midias"]), 1)


class EditorDesignEndpointsTests(TestCase):
    """Testes dos endpoints de salvamento do Design System e validações."""

    def setUp(self):
        self.client = Client()
        self.usuario = Usuario.objects.create_user(
            username="designer_editor",
            email="designer@teste.com",
            password="SenhaForte123!",
            is_staff=True,
        )
        self.client.force_login(self.usuario)

        self.cliente = Cliente.objects.create(nome="Cliente Design Studio")
        self.projeto1 = ProjetoSite.objects.create(
            cliente=self.cliente,
            nome="Projeto Design 1",
            slug="proj-des-1",
        )

    def test_salvar_configuracao_visual_sucesso(self):
        url = reverse("painel:site_editor_design_salvar", kwargs={"uuid": self.projeto1.uuid})
        payload = {
            "cor_primaria": "#10b981",
            "cor_secundaria": "#059669",
            "cor_fundo": "#0b0f19",
            "cor_superficie": "#111827",
            "cor_texto": "#f8fafc",
            "cor_texto_secundario": "#94a3b8",
            "fonte_principal": "Plus Jakarta Sans, sans-serif",
            "fonte_titulos": "Plus Jakarta Sans, sans-serif",
            "radius_padrao": "16px",
            "sombra_padrao": "glow",
            "largura_maxima_mobile": 390,
        }
        response = self.client.post(url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertIn("tokens", data)

        config = ConfiguracaoVisualProjeto.objects.get(projeto=self.projeto1)
        self.assertEqual(config.cor_primaria, "#10b981")
        self.assertEqual(config.radius_padrao, "16px")

    def test_salvar_configuracao_visual_rejeita_cor_invalida(self):
        url = reverse("painel:site_editor_design_salvar", kwargs={"uuid": self.projeto1.uuid})
        payload = {
            "cor_primaria": "cor-invalida",
        }
        response = self.client.post(url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 422)
        self.assertFalse(response.json()["ok"])

    def test_salvar_configuracao_visual_uuid_inexistente_retorna_404(self):
        url = reverse("painel:site_editor_design_salvar", kwargs={"uuid": uuid.uuid4()})
        response = self.client.post(
            url, data={"cor_primaria": "#123456"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 404)
