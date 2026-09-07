"""Testes automatizados para projetos de sites e workspace (Prompt 3)."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse

from aplicativos.clientes.models import Cliente

from .models import ProjetoSite
from .servicos import duplicar_projeto, gerar_slug_unico, validar_slug_permitido

Usuario = get_user_model()


class ProjetoSiteModelTests(TestCase):
    """Testes de integridade do modelo ProjetoSite."""

    def setUp(self):
        self.cliente = Cliente.objects.create(nome="Studio Alpha")

    def test_criar_projeto_com_sucesso(self):
        projeto = ProjetoSite.objects.create(
            cliente=self.cliente,
            nome="BioSite Studio Alpha",
            slug="studio-alpha",
        )

        self.assertEqual(projeto.nome, "BioSite Studio Alpha")
        self.assertEqual(projeto.slug, "studio-alpha")
        self.assertEqual(projeto.status, ProjetoSite.Status.RASCUNHO)
        self.assertEqual(projeto.tipo, ProjetoSite.Tipo.BIOSITE)
        self.assertIsNotNone(projeto.uuid)
        self.assertEqual(str(projeto), "BioSite Studio Alpha")

    def test_on_delete_protect_ao_tentar_excluir_cliente_com_projetos(self):
        """Garante que cliente com sites vinculados não pode ser excluído acidentalmente."""
        ProjetoSite.objects.create(
            cliente=self.cliente,
            nome="Site Protegido",
            slug="site-protegido",
        )

        with self.assertRaises(ProtectedError):
            self.cliente.delete()

    def test_arquivar_e_restaurar_projeto(self):
        projeto = ProjetoSite.objects.create(
            cliente=self.cliente,
            nome="Site para Arquivar",
            slug="site-arquivar",
        )

        projeto.arquivar()
        self.assertEqual(projeto.status, ProjetoSite.Status.ARQUIVADO)
        self.assertIsNotNone(projeto.arquivado_em)

        projeto.restaurar()
        self.assertEqual(projeto.status, ProjetoSite.Status.RASCUNHO)
        self.assertIsNone(projeto.arquivado_em)


class ProjetoSiteServicosTests(TestCase):
    """Testes dos serviços de slug e duplicação."""

    def setUp(self):
        self.cliente = Cliente.objects.create(nome="Cliente Servicos")

    def test_gerar_slug_automatico(self):
        slug = gerar_slug_unico(nome="Dra. Ana Maria & Filhos")
        self.assertEqual(slug, "dra-ana-maria-filhos")

    def test_gerar_slug_com_colisao_adiciona_sufixo(self):
        ProjetoSite.objects.create(
            cliente=self.cliente,
            nome="Barbearia Central",
            slug="barbearia-central",
        )

        novo_slug = gerar_slug_unico(nome="Barbearia Central")
        self.assertEqual(novo_slug, "barbearia-central-2")

    def test_slug_palavra_reservada_lanca_validation_error(self):
        with self.assertRaises(ValidationError):
            validar_slug_permitido("admin")

        with self.assertRaises(ValidationError):
            validar_slug_permitido("painel")

        with self.assertRaises(ValidationError):
            validar_slug_permitido("login")

    def test_duplicar_projeto_atomico(self):
        original = ProjetoSite.objects.create(
            cliente=self.cliente,
            nome="Cardápio Digital Prime",
            slug="cardapio-prime",
            tipo=ProjetoSite.Tipo.CARDAPIO,
            descricao_interna="Notas do cardápio",
        )

        duplicado = duplicar_projeto(original)

        self.assertNotEqual(duplicado.pk, original.pk)
        self.assertNotEqual(duplicado.uuid, original.uuid)
        self.assertEqual(duplicado.nome, "Cópia de Cardápio Digital Prime")
        self.assertEqual(duplicado.slug, "cardapio-prime-copia")
        self.assertEqual(duplicado.status, ProjetoSite.Status.RASCUNHO)
        self.assertEqual(duplicado.tipo, ProjetoSite.Tipo.CARDAPIO)
        self.assertEqual(duplicado.descricao_interna, "Notas do cardápio")
        self.assertEqual(duplicado.cliente, self.cliente)


class ProjetoSiteViewsTests(TestCase):
    """Testes das views do Workspace Meus Sites e gerenciamento de projetos."""

    def setUp(self):
        self.operador = Usuario.objects.create_user(
            username="operador_workspace",
            email="workspace@biosite.local",
            password="SenhaForte123!",
            is_staff=True,
        )
        self.client.force_login(self.operador)

        self.cliente = Cliente.objects.create(
            nome="Advocacia Santos", nome_fantasia="Santos & Associados"
        )
        self.projeto_ativo = ProjetoSite.objects.create(
            cliente=self.cliente,
            nome="BioSite Advocacia Santos",
            slug="advocacia-santos",
        )
        self.projeto_arquivado = ProjetoSite.objects.create(
            cliente=self.cliente,
            nome="Landing Antiga",
            slug="landing-antiga",
            status=ProjetoSite.Status.ARQUIVADO,
        )

    def test_workspace_meus_sites_retorna_200_com_projetos_ativos(self):
        url = reverse("painel:sites")
        resposta = self.client.get(url)

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "BioSite Advocacia Santos")
        # Por padrão não exibe arquivados
        self.assertNotContains(resposta, "Landing Antiga")

    def test_workspace_filtro_arquivados(self):
        url = f"{reverse('painel:sites')}?status=arquivados"
        resposta = self.client.get(url)

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Landing Antiga")
        self.assertNotContains(resposta, "BioSite Advocacia Santos")

    def test_workspace_busca_por_nome_e_cliente(self):
        url = f"{reverse('painel:sites')}?q=Santos"
        resposta = self.client.get(url)

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "BioSite Advocacia Santos")

    def test_criar_novo_projeto_via_form(self):
        url = reverse("painel:site_novo")
        dados = {
            "cliente": self.cliente.pk,
            "nome": "Novo BioSite Exemplo",
            "slug": "exemplo-slug",
            "tipo": ProjetoSite.Tipo.BIOSITE,
        }
        resposta = self.client.post(url, dados)

        projeto = ProjetoSite.objects.filter(slug="exemplo-slug").first()
        self.assertIsNotNone(projeto)
        self.assertRedirects(
            resposta,
            reverse("painel:site_detalhe", kwargs={"uuid": projeto.uuid}),
        )

    def test_criar_novo_projeto_sem_slug_gera_automatico(self):
        url = reverse("painel:site_novo")
        dados = {
            "cliente": self.cliente.pk,
            "nome": "BioSite Sem Slug Informado",
            "slug": "",
            "tipo": ProjetoSite.Tipo.BIOSITE,
        }
        resposta = self.client.post(url, dados)
        self.assertEqual(resposta.status_code, 302)

        projeto = ProjetoSite.objects.filter(nome="BioSite Sem Slug Informado").first()
        self.assertIsNotNone(projeto)
        self.assertEqual(projeto.slug, "biosite-sem-slug-informado")

    def test_detalhes_do_projeto(self):
        url = reverse("painel:site_detalhe", kwargs={"uuid": self.projeto_ativo.uuid})
        resposta = self.client.get(url)

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "BioSite Advocacia Santos")
        self.assertContains(resposta, "/advocacia-santos")
        self.assertContains(resposta, "Preview Mobile-First (390px)")

    def test_duplicar_projeto_via_post(self):
        url = reverse("painel:site_duplicar", kwargs={"uuid": self.projeto_ativo.uuid})
        resposta = self.client.post(url)

        duplicado = ProjetoSite.objects.filter(slug="advocacia-santos-copia").first()
        self.assertIsNotNone(duplicado)
        self.assertRedirects(
            resposta,
            reverse("painel:site_detalhe", kwargs={"uuid": duplicado.uuid}),
        )

    def test_duplicar_projeto_via_get_rejeitado(self):
        url = reverse("painel:site_duplicar", kwargs={"uuid": self.projeto_ativo.uuid})
        resposta = self.client.get(url)
        self.assertEqual(resposta.status_code, 405)

    def test_arquivar_projeto_via_post(self):
        url = reverse("painel:site_arquivar", kwargs={"uuid": self.projeto_ativo.uuid})
        resposta = self.client.post(url)

        self.projeto_ativo.refresh_from_db()
        self.assertEqual(self.projeto_ativo.status, ProjetoSite.Status.ARQUIVADO)
        self.assertRedirects(resposta, reverse("painel:sites"))

    def test_restaurar_projeto_via_post(self):
        url = reverse("painel:site_restaurar", kwargs={"uuid": self.projeto_arquivado.uuid})
        resposta = self.client.post(url)

        self.projeto_arquivado.refresh_from_db()
        self.assertEqual(self.projeto_arquivado.status, ProjetoSite.Status.RASCUNHO)
        self.assertRedirects(
            resposta,
            reverse("painel:site_detalhe", kwargs={"uuid": self.projeto_arquivado.uuid}),
        )

    def test_criar_projeto_sem_cliente_falha(self):
        url = reverse("painel:site_novo")
        dados = {
            "cliente": "",
            "nome": "Projeto Sem Cliente",
            "slug": "sem-cliente",
            "tipo": ProjetoSite.Tipo.BIOSITE,
        }
        resposta = self.client.post(url, dados)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("cliente", resposta.context["form"].errors)

    def test_paginacao_de_projetos_no_workspace(self):
        # Criar 13 novos projetos para exceder o paginate_by (12)
        for i in range(13):
            ProjetoSite.objects.create(
                cliente=self.cliente,
                nome=f"Site Paginado {i}",
                slug=f"site-paginado-{i}",
            )

        url = f"{reverse('painel:sites')}?page=2"
        resposta = self.client.get(url)
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.context["is_paginated"])
