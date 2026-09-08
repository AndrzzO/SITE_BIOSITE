"""
Testes automatizados para publicação, snapshots imutáveis, rollback, SEO e rotas públicas (Prompt 8).
"""

import json
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from aplicativos.clientes.models import Cliente

from .models import (
    ElementoSite,
    MidiaSite,
    ProjetoSite,
)
from .servicos_estrutura import garantir_pagina_inicial
from .servicos_publicacao import (
    despublicar_projeto,
    publicar_projeto,
    restaurar_versao_no_editor,
    rollback_publicacao,
    validar_pre_publicacao,
    verificar_alteracoes_pendentes,
)

Usuario = get_user_model()


class BasePublicacaoTestCase(TestCase):
    """Fixture base com usuário, cliente e projeto populado."""

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username="editor_publicacao",
            email="pub@biosite.local",
            password="SenhaSegura123!",
            is_staff=True,
        )
        self.client_auth = Client()
        self.client_auth.force_login(self.usuario)

        self.cliente = Cliente.objects.create(nome="Clínica Bem Estar")
        self.projeto = ProjetoSite.objects.create(
            cliente=self.cliente,
            nome="BioSite Dra. Ana",
            slug="dra-ana",
            titulo_seo="Dra. Ana Silva | Nutrição Clínica",
            descricao_seo="Agende sua consulta com a Dra. Ana Silva.",
            indexavel=True,
        )
        self.pagina_inicial = garantir_pagina_inicial(self.projeto)
        self.secao = self.pagina_inicial.secoes.first()
        self.container = self.secao.containers.first()

        self.elemento_titulo = ElementoSite.objects.create(
            container=self.container,
            tipo="TITULO",
            ordem=1,
            conteudo={"texto": "Bem-vindo ao meu BioSite", "nivel": "h1"},
        )
        self.elemento_botao = ElementoSite.objects.create(
            container=self.container,
            tipo="BOTAO",
            ordem=2,
            conteudo={
                "texto": "Fale Comigo no WhatsApp",
                "url": "https://wa.me/5511999999999",
                "estilo": "primario",
            },
        )


class ServicosPublicacaoTests(BasePublicacaoTestCase):
    """Testes dos serviços de domínio de publicação (servicos_publicacao.py)."""

    def test_validar_pre_publicacao_valido(self):
        valido, erros, avisos = validar_pre_publicacao(self.projeto)
        self.assertTrue(valido)
        self.assertEqual(len(erros), 0)

    def test_validar_pre_publicacao_erro_sem_paginas(self):
        # Exclui páginas para simular rascunho corrompido
        self.projeto.paginas.all().delete()
        valido, erros, avisos = validar_pre_publicacao(self.projeto)
        self.assertFalse(valido)
        self.assertTrue(any("nenhuma página ativa" in e for e in erros))

    def test_publicar_projeto_v1_cria_snapshot_imutavel(self):
        publicacao = publicar_projeto(self.projeto, usuario=self.usuario)

        self.assertEqual(publicacao.numero_versao, 1)
        self.assertTrue(publicacao.ativa)
        self.assertEqual(publicacao.publicado_por, self.usuario)
        self.assertEqual(len(publicacao.hash_conteudo), 64)  # SHA-256 hex string

        self.projeto.refresh_from_db()
        self.assertEqual(self.projeto.status, ProjetoSite.Status.PUBLICADO)
        self.assertEqual(self.projeto.publicacao_ativa, publicacao)
        self.assertTrue(self.projeto.esta_publicado())
        self.assertFalse(verificar_alteracoes_pendentes(self.projeto))

    def test_publicar_sem_alteracoes_lanca_validation_error_salvo_forcado(self):
        publicar_projeto(self.projeto, usuario=self.usuario)

        # Segunda tentativa sem alterar rascunho deve falhar se forcar=False
        with self.assertRaises(ValidationError) as ctx:
            publicar_projeto(self.projeto, usuario=self.usuario, forcar=False)
        self.assertIn("Não há alterações pendentes no rascunho", str(ctx.exception))

        # Se forçar, publica nova versão
        pub2 = publicar_projeto(self.projeto, usuario=self.usuario, forcar=True)
        self.assertEqual(pub2.numero_versao, 2)
        self.assertTrue(pub2.ativa)

    def test_publicar_com_alteracoes_no_rascunho_gera_v2_e_desativa_v1(self):
        pub1 = publicar_projeto(self.projeto, usuario=self.usuario)
        self.assertEqual(pub1.numero_versao, 1)
        self.assertTrue(pub1.ativa)

        # Altera elemento no rascunho
        self.elemento_titulo.conteudo = {"texto": "Novo Título Atualizado 2026", "nivel": "h1"}
        self.elemento_titulo.save()

        self.assertTrue(verificar_alteracoes_pendentes(self.projeto))

        pub2 = publicar_projeto(self.projeto, usuario=self.usuario)
        self.assertEqual(pub2.numero_versao, 2)
        self.assertTrue(pub2.ativa)

        pub1.refresh_from_db()
        self.assertFalse(pub1.ativa)
        self.assertNotEqual(pub1.hash_conteudo, pub2.hash_conteudo)

    def test_rollback_cronologico_preserva_historico_e_gera_v3(self):
        pub1 = publicar_projeto(self.projeto, usuario=self.usuario)

        # Modifica e gera v2
        self.elemento_titulo.conteudo = {"texto": "Título Versão 2", "nivel": "h1"}
        self.elemento_titulo.save()
        pub2 = publicar_projeto(self.projeto, usuario=self.usuario)

        self.assertEqual(pub2.numero_versao, 2)

        # Rollback para v1 deve criar v3 com o snapshot de v1
        pub3 = rollback_publicacao(self.projeto, publicacao_alvo=pub1, usuario=self.usuario)

        self.assertEqual(pub3.numero_versao, 3)
        self.assertTrue(pub3.ativa)
        self.assertEqual(pub3.hash_conteudo, pub1.hash_conteudo)
        self.assertEqual(pub3.metadata.get("versao_restaurada"), 1)

        # Verifica integridade cronológica de todas as publicações
        self.assertEqual(self.projeto.publicacoes.count(), 3)
        pub1.refresh_from_db()
        pub2.refresh_from_db()
        self.assertFalse(pub1.ativa)
        self.assertFalse(pub2.ativa)

    def test_despublicar_projeto_e_reativar_publicacao(self):
        pub1 = publicar_projeto(self.projeto, usuario=self.usuario)
        self.assertTrue(self.projeto.esta_publicado())

        despublicar_projeto(self.projeto, usuario=self.usuario)

        self.projeto.refresh_from_db()
        self.assertEqual(self.projeto.status, ProjetoSite.Status.RASCUNHO)
        self.assertIsNone(self.projeto.publicacao_ativa)
        self.assertFalse(self.projeto.esta_publicado())

        # Publicações continuam arquivadas no histórico
        self.assertEqual(self.projeto.publicacoes.count(), 1)
        pub1.refresh_from_db()
        self.assertFalse(pub1.ativa)

    def test_restaurar_versao_no_editor(self):
        pub1 = publicar_projeto(self.projeto, usuario=self.usuario)

        # Altera e exclui coisas no rascunho
        self.elemento_botao.delete()
        self.elemento_titulo.conteudo = {"texto": "Texto Provisório", "nivel": "h1"}
        self.elemento_titulo.save()

        # Restaura v1 no editor
        restaurar_versao_no_editor(self.projeto, pub1)

        # O botão excluído voltou a existir no rascunho reconstruído
        elementos = ElementoSite.objects.filter(container__secao__pagina__projeto=self.projeto)
        self.assertEqual(elementos.count(), 2)
        titulo_restaurado = elementos.filter(tipo="TITULO").first()
        self.assertEqual(titulo_restaurado.conteudo["texto"], "Bem-vindo ao meu BioSite")

    def test_protecao_exclusao_midia_utilizada_em_publicacoes(self):
        midia = MidiaSite.objects.create(
            projeto=self.projeto,
            nome_original="foto_perfil.jpg",
            tipo="IMAGEM",
            largura=800,
            altura=800,
            tamanho_bytes=1024,
            mime_type="image/jpeg",
        )
        self.elemento_titulo.conteudo["imagem_id"] = str(midia.uuid)
        self.elemento_titulo.save()

        publicar_projeto(self.projeto, usuario=self.usuario)

        # Tentar deletar midia deve falhar com ValidationError
        with self.assertRaises(ValidationError) as ctx:
            midia.delete()
        self.assertIn("está vinculada a versões publicadas", str(ctx.exception))


class PublicSiteViewTests(BasePublicacaoTestCase):
    """Testes da rota pública do BioSite (/b/<slug>/) e isolamento rascunho vs produção."""

    def test_site_nao_publicado_retorna_404(self):
        url = reverse("publico:site_publico", kwargs={"slug": self.projeto.slug})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)
        self.assertContains(resp, "Página Não Encontrada", status_code=404)

    def test_slug_inexistente_retorna_404(self):
        url = reverse("publico:site_publico", kwargs={"slug": "slug-inexistente-xyz"})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_site_publicado_retorna_200_com_seo_e_meta_tags(self):
        publicar_projeto(self.projeto, usuario=self.usuario)
        url = reverse("publico:site_publico", kwargs={"slug": self.projeto.slug})

        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        # Verifica conteúdo renderizado
        self.assertContains(resp, "Bem-vindo ao meu BioSite")
        self.assertContains(resp, "Fale Comigo no WhatsApp")

        # Verifica SEO tags no HTML
        self.assertContains(resp, "<title>Dra. Ana Silva | Nutrição Clínica</title>")
        self.assertContains(
            resp, 'name="description" content="Agende sua consulta com a Dra. Ana Silva."'
        )
        self.assertContains(resp, 'name="robots" content="index, follow')
        self.assertContains(resp, 'property="og:title" content="Dra. Ana Silva | Nutrição Clínica"')
        self.assertContains(resp, f"/b/{self.projeto.slug}/")

        # Verifica headers de performance e ETag
        self.assertIn("ETag", resp.headers)
        self.assertIn("Cache-Control", resp.headers)

    def test_isolamento_estrito_alteracoes_no_rascunho_nao_afetam_publico(self):
        publicar_projeto(self.projeto, usuario=self.usuario)
        url = reverse("publico:site_publico", kwargs={"slug": self.projeto.slug})

        # Altera o rascunho no banco de dados
        self.elemento_titulo.conteudo = {
            "texto": "Texto Secreto Rascunho Não Publicado",
            "nivel": "h1",
        }
        self.elemento_titulo.save()

        # Rota pública AINDA DEVE EXIBIR o texto da v1 publicada!
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Bem-vindo ao meu BioSite")
        self.assertNotContains(resp, "Texto Secreto Rascunho Não Publicado")

    def test_conditional_get_retorna_304_not_modified(self):
        publicar_projeto(self.projeto, usuario=self.usuario)
        url = reverse("publico:site_publico", kwargs={"slug": self.projeto.slug})

        resp1 = self.client.get(url)
        self.assertEqual(resp1.status_code, 200)
        etag = resp1.headers.get("ETag")
        self.assertIsNotNone(etag)

        # Envia requisição condicional com If-None-Match
        resp2 = self.client.get(url, HTTP_IF_NONE_MATCH=etag)
        self.assertEqual(resp2.status_code, 304)
        self.assertEqual(resp2.content, b"")

    def test_despublicacao_imediatamente_retorna_404_no_site_publico(self):
        publicar_projeto(self.projeto, usuario=self.usuario)
        url = reverse("publico:site_publico", kwargs={"slug": self.projeto.slug})

        # Primeiro acesso retorna 200
        resp1 = self.client.get(url)
        self.assertEqual(resp1.status_code, 200)

        # Despublica
        despublicar_projeto(self.projeto, usuario=self.usuario)

        # Agora deve retornar 404
        resp2 = self.client.get(url)
        self.assertEqual(resp2.status_code, 404)

    def test_head_request_retorna_headers_sem_corpo(self):
        publicar_projeto(self.projeto, usuario=self.usuario)
        url = reverse("publico:site_publico", kwargs={"slug": self.projeto.slug})

        resp = self.client.head(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("ETag", resp.headers)
        self.assertEqual(resp.content, b"")


class ViewsAdministrativasPublicacaoTests(BasePublicacaoTestCase):
    """Testes dos endpoints administrativos de publicação (views_publicacao.py)."""

    def test_validar_pre_publicacao_endpoint(self):
        url = reverse("painel:site_publicar_validar", kwargs={"uuid": self.projeto.uuid})
        resp = self.client_auth.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertTrue(data["valido"])
        self.assertEqual(data["total_erros"], 0)

    def test_publicar_projeto_endpoint(self):
        url = reverse("painel:site_publicar", kwargs={"uuid": self.projeto.uuid})
        resp = self.client_auth.post(
            url,
            data=json.dumps({"forcar": False}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["versao"], 1)
        self.assertIn(f"/b/{self.projeto.slug}/", data["url_publica"])

    def test_publicacao_status_endpoint(self):
        url = reverse("painel:site_publicacao_status", kwargs={"uuid": self.projeto.uuid})
        resp1 = self.client_auth.get(url)
        data1 = resp1.json()
        self.assertFalse(data1["publicado"])
        self.assertIsNone(data1["versao_atual"])

        # Publica
        publicar_projeto(self.projeto, usuario=self.usuario)
        resp2 = self.client_auth.get(url)
        data2 = resp2.json()
        self.assertTrue(data2["publicado"])
        self.assertEqual(data2["versao_atual"], 1)
        self.assertFalse(data2["alteracoes_pendentes"])

    def test_historico_publicacoes_endpoint(self):
        publicar_projeto(self.projeto, usuario=self.usuario)
        url = reverse("painel:site_publicacoes_historico", kwargs={"uuid": self.projeto.uuid})

        resp = self.client_auth.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(len(data["publicacoes"]), 1)
        self.assertEqual(data["publicacoes"][0]["numero_versao"], 1)
        self.assertTrue(data["publicacoes"][0]["ativa"])

    def test_preview_publicacao_endpoint(self):
        pub = publicar_projeto(self.projeto, usuario=self.usuario)
        url = reverse(
            "painel:publicacao_preview",
            kwargs={"uuid": self.projeto.uuid, "versao": pub.numero_versao},
        )
        resp = self.client_auth.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Bem-vindo ao meu BioSite")

    def test_rollback_publicacao_endpoint(self):
        pub1 = publicar_projeto(self.projeto, usuario=self.usuario)
        self.elemento_titulo.conteudo = {"texto": "V2 Título", "nivel": "h1"}
        self.elemento_titulo.save()
        publicar_projeto(self.projeto, usuario=self.usuario)

        url = reverse(
            "painel:publicacao_rollback",
            kwargs={"uuid": self.projeto.uuid, "versao": pub1.numero_versao},
        )
        resp = self.client_auth.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["nova_versao"], 3)

    def test_despublicar_projeto_endpoint(self):
        publicar_projeto(self.projeto, usuario=self.usuario)
        url = reverse("painel:site_despublicar", kwargs={"uuid": self.projeto.uuid})

        resp = self.client_auth.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.projeto.refresh_from_db()
        self.assertFalse(self.projeto.esta_publicado())

    def test_restaurar_versao_no_editor_endpoint(self):
        pub1 = publicar_projeto(self.projeto, usuario=self.usuario)
        self.elemento_titulo.conteudo = {"texto": "Alterado", "nivel": "h1"}
        self.elemento_titulo.save()

        url = reverse(
            "painel:publicacao_restaurar_editor",
            kwargs={"uuid": self.projeto.uuid, "versao": pub1.numero_versao},
        )
        resp = self.client_auth.post(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])

        # O elemento com texto original foi restaurado
        titulo = ElementoSite.objects.filter(
            container__secao__pagina__projeto=self.projeto, tipo="TITULO"
        ).first()
        self.assertIsNotNone(titulo)
        self.assertEqual(titulo.conteudo["texto"], "Bem-vindo ao meu BioSite")


class ManagementCommandTests(BasePublicacaoTestCase):
    """Testes do management command verificar_publicacoes."""

    def test_verificar_publicacoes_execucao(self):
        publicar_projeto(self.projeto, usuario=self.usuario)

        out = StringIO()
        call_command("verificar_publicacoes", stdout=out)
        output = out.getvalue()

        self.assertIn("Auditoria concluída com sucesso", output)
