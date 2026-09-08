"""
Testes automatizados para Links Inteligentes, Tags NFC, QR Codes e Redirecionamento Dinâmico (Prompt 10).
"""

from io import BytesIO, StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, TestCase
from PIL import Image

from aplicativos.clientes.models import Cliente

from .models import (
    EnderecoSite,
    HistoricoVinculoTag,
    LinkInteligente,
    ProjetoSite,
)
from .servicos import duplicar_projeto
from .servicos_dominios import (
    adicionar_dominio_personalizado,
    criar_subdominio_padrao,
    definir_endereco_principal,
)
from .servicos_estrutura import garantir_pagina_inicial
from .servicos_links import (
    TAMANHO_TOKEN,
    alterar_vinculo_projeto,
    alternar_status_link,
    criar_link_inteligente,
    gerar_token_link,
    resolver_link_inteligente,
)
from .servicos_publicacao import despublicar_projeto, publicar_projeto
from .servicos_qrcode import TAMANHOS_PERMITIDOS_QR, gerar_imagem_qrcode

Usuario = get_user_model()


class BaseLinksInteligentesTestCase(TestCase):
    """Fixture base com usuário, cliente e projeto publicado."""

    def setUp(self):
        cache.clear()
        self.usuario = Usuario.objects.create_user(
            username="admin_nfc",
            email="nfc@biosite.local",
            password="SenhaSegura123!",
            is_staff=True,
        )
        self.client_auth = Client()
        self.client_auth.force_login(self.usuario)

        self.cliente = Cliente.objects.create(nome="Clínica Médica Vida")
        self.projeto_a = ProjetoSite.objects.create(
            cliente=self.cliente,
            nome="BioSite Dr. João",
            slug="dr-joao",
        )
        garantir_pagina_inicial(self.projeto_a)
        self.endereco_a = criar_subdominio_padrao(self.projeto_a, "dr-joao")
        self.pub_a = publicar_projeto(self.projeto_a, usuario=self.usuario)

        self.projeto_b = ProjetoSite.objects.create(
            cliente=self.cliente,
            nome="BioSite Dra. Maria",
            slug="dra-maria",
        )
        garantir_pagina_inicial(self.projeto_b)
        self.endereco_b = criar_subdominio_padrao(self.projeto_b, "dra-maria")
        self.pub_b = publicar_projeto(self.projeto_b, usuario=self.usuario)


class TestGeracaoTokens(TestCase):
    """Testes de geração de tokens criptograficamente seguros e imprevisíveis."""

    def test_gerar_token_formato_e_entropia(self):
        token = gerar_token_link()
        self.assertEqual(len(token), TAMANHO_TOKEN)
        self.assertTrue(token.isalnum())

        # Testa unicidade prática gerando 100 tokens
        tokens = {gerar_token_link() for _ in range(100)}
        self.assertEqual(len(tokens), 100)

    @patch("secrets.choice")
    def test_gerar_token_retry_colisao(self, mock_choice):
        cliente = Cliente.objects.create(nome="Cliente Token")
        proj = ProjetoSite.objects.create(cliente=cliente, nome="P", slug="p")
        # Cria um link com token conhecido
        LinkInteligente.objects.create(
            projeto=proj,
            token="TOKENEXIST",
            tipo=LinkInteligente.Tipo.NFC,
        )

        # Configura o mock para simular 2 colisões e depois gerar novo
        # Cada token tem 10 caracteres
        chamadas = 0

        def side_effect(seq):
            nonlocal chamadas
            chamadas += 1
            if chamadas <= 10:
                # Primeiro token "TOKENEXIST" (10 chars)
                return "TOKENEXIST"[chamadas - 1]
            return "A"

        mock_choice.side_effect = side_effect
        token_gerado = gerar_token_link(max_tentativas=5)
        self.assertEqual(token_gerado, "A" * 10)


class TestServicosLinksInteligentes(BaseLinksInteligentesTestCase):
    """Testes dos serviços de resolução, vinculação e ciclo de vida de links inteligentes."""

    def test_criar_link_inteligente(self):
        link = criar_link_inteligente(
            projeto=self.projeto_a,
            tipo=LinkInteligente.Tipo.NFC,
            nome="Cartão Dr. João",
            tipo_midia_fisica=LinkInteligente.TipoMidiaFisica.CARTAO,
            usuario=self.usuario,
        )
        self.assertEqual(link.status, LinkInteligente.Status.ATIVO)
        self.assertEqual(link.tipo, LinkInteligente.Tipo.NFC)
        self.assertTrue(len(link.token) >= 10)
        self.assertTrue(link.esta_operacional())

        # Verifica histórico de vínculo
        hist = HistoricoVinculoTag.objects.filter(link=link).first()
        self.assertIsNotNone(hist)
        self.assertIsNone(hist.projeto_anterior)
        self.assertEqual(hist.projeto_novo, self.projeto_a)

    def test_resolver_link_inteligente_sucesso(self):
        link = criar_link_inteligente(projeto=self.projeto_a, tipo=LinkInteligente.Tipo.NFC)
        sucesso, url_destino, link_resolvido = resolver_link_inteligente(link.token)

        self.assertTrue(sucesso)
        self.assertIsNotNone(url_destino)
        self.assertIn(self.endereco_a.host, url_destino)

    def test_resolver_link_inteligente_inativo(self):
        link = criar_link_inteligente(projeto=self.projeto_a)
        alternar_status_link(link, ativar=False)

        sucesso, url_destino, _ = resolver_link_inteligente(link.token)
        self.assertFalse(sucesso)
        self.assertIsNone(url_destino)

    def test_resolver_link_projeto_despublicado(self):
        link = criar_link_inteligente(projeto=self.projeto_a)
        # Despublica o projeto
        despublicar_projeto(self.projeto_a, usuario=self.usuario)

        sucesso, url_destino, _ = resolver_link_inteligente(link.token)
        self.assertFalse(sucesso)
        self.assertIsNone(url_destino)

        # Ao republicar, a MESMA URL NFC volta a funcionar automaticamente
        publicar_projeto(self.projeto_a, usuario=self.usuario)
        sucesso_rep, url_rep, _ = resolver_link_inteligente(link.token)
        self.assertTrue(sucesso_rep)
        self.assertIsNotNone(url_rep)

    def test_resolver_link_projeto_arquivado(self):
        link = criar_link_inteligente(projeto=self.projeto_a)
        self.projeto_a.arquivar()

        sucesso, url_destino, _ = resolver_link_inteligente(link.token)
        self.assertFalse(sucesso)

    def test_independencia_de_dominio_mesmo_token(self):
        """Trocar o domínio principal do projeto atualiza o destino da tag sem mudar o token."""
        link = criar_link_inteligente(projeto=self.projeto_a)
        token_original = link.token

        # Adiciona domínio customizado e torna principal
        end_custom = adicionar_dominio_personalizado(self.projeto_a, "www.drjoaosilva.med.br")
        end_custom.status = EnderecoSite.Status.VERIFICADO
        end_custom.save()
        definir_endereco_principal(self.projeto_a, end_custom)

        # Resolve novamente com o MESMO token original
        sucesso, novo_destino, _ = resolver_link_inteligente(token_original)
        self.assertTrue(sucesso)
        self.assertIn("www.drjoaosilva.med.br", novo_destino)

    def test_trocar_vinculo_de_projeto(self):
        """Alterar o BioSite vinculado à tag preserva o token e grava histórico auditável."""
        link = criar_link_inteligente(projeto=self.projeto_a, nome="Cartão Flex")
        token = link.token

        # Altera destino para Projeto B
        alterar_vinculo_projeto(
            link=link,
            novo_projeto=self.projeto_b,
            usuario=self.usuario,
            motivo="Transferência para nova médica parceira.",
        )

        # O mesmo token agora resolve para o Projeto B
        sucesso, destino_b, _ = resolver_link_inteligente(token)
        self.assertTrue(sucesso)
        self.assertIn(self.endereco_b.host, destino_b)

        # Verifica histórico de vínculo
        historicos = list(HistoricoVinculoTag.objects.filter(link=link).order_by("criado_em"))
        self.assertEqual(len(historicos), 2)
        self.assertEqual(historicos[1].projeto_anterior, self.projeto_a)
        self.assertEqual(historicos[1].projeto_novo, self.projeto_b)
        self.assertEqual(historicos[1].alterado_por, self.usuario)


class TestRedirectSmartLinkView(BaseLinksInteligentesTestCase):
    """Testes de ponta a ponta dos endpoints HTTP de redirecionamento /n/ e /q/."""

    def test_redirect_nfc_sucesso_302(self):
        link = criar_link_inteligente(projeto=self.projeto_a, tipo=LinkInteligente.Tipo.NFC)
        url = f"/n/{link.token}/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(self.endereco_a.host, response["Location"])
        # Valida headers de SEO e ausência de cache agressivo
        self.assertEqual(response["X-Robots-Tag"], "noindex, nofollow")
        self.assertIn("no-cache", response["Cache-Control"])

    def test_redirect_qr_sucesso_302(self):
        link_qr = criar_link_inteligente(projeto=self.projeto_a, tipo=LinkInteligente.Tipo.QR)
        url = f"/q/{link_qr.token}/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(self.endereco_a.host, response["Location"])

    def test_redirect_head_request(self):
        link = criar_link_inteligente(projeto=self.projeto_a)
        url = f"/n/{link.token}/"
        response = self.client.head(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.content, b"")

    def test_redirect_token_inexistente_retorna_404_neutro(self):
        response = self.client.get("/n/TOKENINEXISTENTE/")
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("Dr. João", response.content.decode())

    def test_redirect_link_inativo_retorna_404_neutro(self):
        link = criar_link_inteligente(projeto=self.projeto_a)
        alternar_status_link(link, ativar=False)

        response = self.client.get(f"/n/{link.token}/")
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("Dr. João", response.content.decode())

    def test_anti_open_redirect(self):
        """Garante que nenhum parâmetro externo possa sobrescrever o destino confiável."""
        link = criar_link_inteligente(projeto=self.projeto_a)
        response = self.client.get(f"/n/{link.token}/?url=https://evil.com&next=https://evil.com")
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("evil.com", response["Location"])
        self.assertIn(self.endereco_a.host, response["Location"])


class TestGeradorQRCode(BaseLinksInteligentesTestCase):
    """Testes de geração local de imagens de QR Code."""

    def test_gerar_qrcode_png_valido(self):
        link = criar_link_inteligente(projeto=self.projeto_a, tipo=LinkInteligente.Tipo.QR)
        png_bytes = gerar_imagem_qrcode(link, tamanho=512)

        self.assertTrue(len(png_bytes) > 0)
        # Verifica se PIL consegue abrir os bytes como imagem PNG válida
        img = Image.open(BytesIO(png_bytes))
        self.assertEqual(img.format, "PNG")
        self.assertEqual(img.size, (512, 512))

    def test_gerar_qrcode_tamanhos_permitidos(self):
        link = criar_link_inteligente(projeto=self.projeto_a, tipo=LinkInteligente.Tipo.QR)
        for tam in TAMANHOS_PERMITIDOS_QR:
            bytes_img = gerar_imagem_qrcode(link, tamanho=tam)
            img = Image.open(BytesIO(bytes_img))
            self.assertEqual(img.size, (tam, tam))

    def test_gerar_qrcode_tamanho_invalido_rejeitado(self):
        link = criar_link_inteligente(projeto=self.projeto_a)
        with self.assertRaises(ValidationError):
            gerar_imagem_qrcode(link, tamanho=99999)


class TestDuplicacaoNaoCopiaLinks(BaseLinksInteligentesTestCase):
    """Garante que a cópia de um projeto nunca herda tags NFC ou QR codes."""

    def test_duplicar_projeto_zero_tags(self):
        # Cria 3 links no projeto A
        criar_link_inteligente(self.projeto_a, tipo=LinkInteligente.Tipo.NFC, nome="Tag 1")
        criar_link_inteligente(self.projeto_a, tipo=LinkInteligente.Tipo.NFC, nome="Tag 2")
        criar_link_inteligente(self.projeto_a, tipo=LinkInteligente.Tipo.QR, nome="QR 1")
        self.assertEqual(self.projeto_a.links_inteligentes.count(), 3)

        # Duplica o projeto A
        projeto_copia = duplicar_projeto(self.projeto_a)

        # O novo projeto nasce com ZERO links
        self.assertEqual(projeto_copia.links_inteligentes.count(), 0)
        self.assertEqual(projeto_copia.total_tags_nfc(), 0)
        self.assertEqual(projeto_copia.total_qr_codes(), 0)


class TestViewsPainelLinks(BaseLinksInteligentesTestCase):
    """Testes das views administrativas do painel para gestão de links."""

    def test_links_lista_global(self):
        criar_link_inteligente(self.projeto_a, nome="Tag A")
        criar_link_inteligente(self.projeto_b, nome="Tag B")

        resp = self.client_auth.get("/painel/links/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Tag A")
        self.assertContains(resp, "Tag B")

    def test_criar_link_via_post(self):
        url = f"/painel/sites/{self.projeto_a.uuid}/links/criar/"
        resp = self.client_auth.post(
            url,
            {
                "nome": "Cartão Balcão",
                "tipo": "nfc",
                "tipo_midia_fisica": "placa",
                "descricao": "Placa de acrílico",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            LinkInteligente.objects.filter(projeto=self.projeto_a, nome="Cartão Balcão").exists()
        )

    def test_alternar_status_link_via_post(self):
        link = criar_link_inteligente(self.projeto_a)
        url = f"/painel/links/{link.uuid}/status/"
        resp = self.client_auth.post(url, {"acao": "desativar"})
        self.assertEqual(resp.status_code, 302)

        link.refresh_from_db()
        self.assertEqual(link.status, LinkInteligente.Status.INATIVO)

    def test_alterar_destino_link_via_post(self):
        link = criar_link_inteligente(self.projeto_a)
        url = f"/painel/links/{link.uuid}/destino/"
        resp = self.client_auth.post(
            url,
            {
                "novo_projeto_uuid": str(self.projeto_b.uuid),
                "motivo": "Transferência de teste",
            },
        )
        self.assertEqual(resp.status_code, 302)
        link.refresh_from_db()
        self.assertEqual(link.projeto, self.projeto_b)

    def test_download_qrcode_png(self):
        link = criar_link_inteligente(self.projeto_a, tipo=LinkInteligente.Tipo.QR)
        url = f"/painel/links/{link.uuid}/qr/?tamanho=512&download=1"
        resp = self.client_auth.get(url)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "image/png")
        self.assertIn("attachment", resp["Content-Disposition"])


class TestComandoAuditoriaLinks(BaseLinksInteligentesTestCase):
    """Testa o comando python manage.py verificar_links_inteligentes."""

    def test_comando_verificar_links(self):
        criar_link_inteligente(self.projeto_a, nome="Tag Audit 1")
        criar_link_inteligente(self.projeto_b, nome="Tag Audit 2")

        out = StringIO()
        call_command("verificar_links_inteligentes", stdout=out)
        conteudo = out.getvalue()

        self.assertIn("Iniciando auditoria", conteudo)
        self.assertIn("Unicidade de tokens: 100% íntegra", conteudo)
        self.assertIn("Total de Links Auditados: 2", conteudo)
