"""
Testes automatizados para o sistema de Templates, Blocos Reutilizáveis e Criação Rápida (Prompt 7 de 12).
"""

import json

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from aplicativos.clientes.models import Cliente

from .models import (
    BlocoReutilizavel,
    ElementoSite,
    ProjetoSite,
    TemplateSite,
)
from .renderer import RenderizadorBioSite
from .servicos_templates import (
    PLACEHOLDERS,
    criar_bloco_a_partir_secao,
    criar_template_a_partir_projeto,
    instanciar_bloco,
    instanciar_template,
)
from .validadores_templates import (
    validar_snapshot_bloco,
    validar_snapshot_template,
)

Usuario = get_user_model()


def _criar_snapshot_exemplo():
    return {
        "schema_version": 1,
        "configuracao_visual": {
            "tema_preset": "dark",
            "cor_primaria": "#38bdf8",
            "cor_secundaria": "#818cf8",
            "cor_fundo": "#0f172a",
            "cor_superficie": "#1e293b",
            "cor_texto": "#f8fafc",
            "cor_texto_secundario": "#94a3b8",
            "fonte_titulos": "Plus Jakarta Sans",
            "fonte_principal": "Inter",
            "radius_padrao": "12px",
            "sombra_padrao": "suave",
        },
        "paginas": [
            {
                "titulo": "Início",
                "slug": "inicio",
                "eh_inicial": True,
                "secoes": [
                    {
                        "nome_interno": "Seção Hero",
                        "tipo": "normal",
                        "estilos": {"base": {"padding_topo": 24, "padding_baixo": 24}},
                        "containers": [
                            {
                                "tipo_layout": "stack",
                                "estilos": {},
                                "elementos": [
                                    {
                                        "tipo": "avatar",
                                        "conteudo": {
                                            "url": "",
                                            "alt": "Foto de Perfil",
                                            "forma": "circulo",
                                            "tamanho": 100,
                                            "borda": True,
                                        },
                                        "estilos": {},
                                    },
                                    {
                                        "tipo": "botao",
                                        "conteudo": {
                                            "texto": "Agende Agora",
                                            "url": "https://wa.me/5511999999999",
                                        },
                                        "estilos": {},
                                    },
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
    }


def _criar_snapshot_bloco_exemplo():
    return {
        "schema_version": 1,
        "secao": {
            "nome_interno": "Bloco Contato",
            "tipo": "normal",
            "estilos": {"base": {"padding_topo": 20, "padding_baixo": 20}},
            "containers": [
                {
                    "tipo_layout": "stack",
                    "elementos": [
                        {
                            "tipo": "texto",
                            "conteudo": {"texto": "Entre em contato conosco."},
                            "estilos": {},
                        }
                    ],
                }
            ],
        },
    }


class ValidadoresTemplatesTests(TestCase):
    """Testes de validação de snapshots estruturais."""

    def test_snapshot_valido_passa_sem_erro(self):
        snap = _criar_snapshot_exemplo()
        validar_snapshot_template(snap)

    def test_snapshot_schema_version_invalida_falha(self):
        snap = _criar_snapshot_exemplo()
        snap["schema_version"] = 99
        with self.assertRaises(ValidationError) as ctx:
            validar_snapshot_template(snap)
        self.assertIn("Versão de schema", str(ctx.exception))

    def test_snapshot_sem_paginas_falha(self):
        snap = _criar_snapshot_exemplo()
        snap["paginas"] = []
        with self.assertRaises(ValidationError) as ctx:
            validar_snapshot_template(snap)
        self.assertIn("pelo menos uma página", str(ctx.exception))

    def test_snapshot_elemento_tipo_desconhecido_falha(self):
        snap = _criar_snapshot_exemplo()
        snap["paginas"][0]["secoes"][0]["containers"][0]["elementos"][0]["tipo"] = (
            "elemento_fantasma"
        )
        with self.assertRaises(ValidationError) as ctx:
            validar_snapshot_template(snap)
        self.assertIn("não registrado", str(ctx.exception))

    def test_snapshot_url_perigosa_rejeitada(self):
        snap = _criar_snapshot_exemplo()
        snap["paginas"][0]["secoes"][0]["containers"][0]["elementos"][1]["conteudo"]["url"] = (
            "javascript:alert(1)"
        )
        with self.assertRaises(ValidationError) as ctx:
            validar_snapshot_template(snap)
        self.assertIn("perigoso", str(ctx.exception))

    def test_snapshot_bloco_valido(self):
        snap_bloco = _criar_snapshot_bloco_exemplo()
        validar_snapshot_bloco(snap_bloco)


class ServicosTemplatesTests(TestCase):
    """Testes dos serviços de clonagem profunda atômica e sanitização."""

    def setUp(self):
        self.cliente = Cliente.objects.create(nome="Cliente Teste", email="cliente@teste.com")
        self.template = TemplateSite.objects.create(
            nome="Template Modelo Teste",
            slug="template-modelo-teste",
            categoria=TemplateSite.Categoria.BIOSITE,
            origem=TemplateSite.Origem.SISTEMA,
            versao=1,
            ativo=True,
            ordem=1,
            estrutura_snapshot=_criar_snapshot_exemplo(),
        )
        self.bloco = BlocoReutilizavel.objects.create(
            nome="Bloco Hero Teste",
            slug="bloco-hero-teste",
            categoria=BlocoReutilizavel.Categoria.HERO,
            origem=BlocoReutilizavel.Origem.SISTEMA,
            versao=1,
            ativo=True,
            ordem=1,
            estrutura_snapshot=_criar_snapshot_bloco_exemplo(),
        )

    def test_instanciar_template_cria_arvore_relacional_completa(self):
        projeto = instanciar_template(
            template=self.template,
            cliente=self.cliente,
            nome="Meu Novo BioSite",
            slug="meu-novo-biosite",
        )

        self.assertIsNotNone(projeto.id)
        self.assertEqual(projeto.status, ProjetoSite.Status.RASCUNHO)
        self.assertEqual(projeto.template_origem, self.template)
        self.assertEqual(projeto.cliente, self.cliente)

        # Configuração visual foi clonada
        self.assertIsNotNone(projeto.configuracao_visual)
        self.assertEqual(projeto.configuracao_visual.cor_primaria, "#38bdf8")

        # Páginas, seções, containers e elementos
        self.assertEqual(projeto.paginas.count(), 1)
        pagina = projeto.paginas.first()
        self.assertTrue(pagina.eh_inicial)
        self.assertEqual(pagina.secoes.count(), 1)

        secao = pagina.secoes.first()
        self.assertEqual(secao.nome_interno, "Seção Hero")
        self.assertEqual(secao.containers.count(), 1)

        container = secao.containers.first()
        self.assertEqual(container.elementos.count(), 2)

        elem_avatar = container.elementos.filter(tipo="AVATAR").first()
        self.assertIsNotNone(elem_avatar)
        self.assertEqual(elem_avatar.conteudo.get("alt"), "Foto de Perfil")

    def test_independencia_total_apos_instanciacao(self):
        projeto = instanciar_template(
            template=self.template,
            cliente=self.cliente,
            nome="Site Isolado",
        )

        # Alterar o projeto não afeta o snapshot do template
        projeto.nome = "Nome Totalmente Alterado"
        projeto.save()
        pagina = projeto.paginas.first()
        pagina.titulo = "Nova Página Principal"
        pagina.save()

        self.template.refresh_from_db()
        self.assertEqual(self.template.nome, "Template Modelo Teste")
        self.assertEqual(self.template.estrutura_snapshot["paginas"][0]["titulo"], "Início")

        # Alterar o template não afeta o projeto existente
        snapshot_modificado = _criar_snapshot_exemplo()
        snapshot_modificado["paginas"][0]["titulo"] = "Título Modificado no Template"
        self.template.estrutura_snapshot = snapshot_modificado
        self.template.save()

        pagina.refresh_from_db()
        self.assertEqual(pagina.titulo, "Nova Página Principal")

    def test_rollback_atomico_em_falha_de_instanciacao(self):
        # Template com snapshot corrompido propositalmente
        template_invalido = TemplateSite.objects.create(
            nome="Template Corrompido",
            slug="template-corrompido",
            categoria=TemplateSite.Categoria.BIOSITE,
            origem=TemplateSite.Origem.SISTEMA,
            estrutura_snapshot={"schema_version": 1, "paginas": []},
        )

        total_projetos_antes = ProjetoSite.objects.count()

        with self.assertRaises(ValidationError):
            instanciar_template(
                template=template_invalido,
                cliente=self.cliente,
                nome="Projeto Invalido",
            )

        # Nenhum projeto ou nó órfão deve ter sido criado
        self.assertEqual(ProjetoSite.objects.count(), total_projetos_antes)

    def test_instanciar_bloco_em_pagina(self):
        projeto = instanciar_template(
            template=self.template,
            cliente=self.cliente,
            nome="Projeto Para Bloco",
        )
        pagina = projeto.paginas.first()
        total_secoes_antes = pagina.secoes.count()

        nova_secao = instanciar_bloco(self.bloco, pagina)
        self.assertIsNotNone(nova_secao.id)
        self.assertEqual(pagina.secoes.count(), total_secoes_antes + 1)
        self.assertEqual(nova_secao.nome_interno, "Bloco Contato")
        self.assertEqual(nova_secao.containers.first().elementos.count(), 1)

    def test_criar_template_a_partir_de_projeto_com_sanitizacao(self):
        projeto = instanciar_template(
            template=self.template,
            cliente=self.cliente,
            nome="Projeto com Dados do Cliente",
        )
        # Adiciona elemento com dados reais
        container = projeto.paginas.first().secoes.first().containers.first()
        ElementoSite.objects.create(
            container=container,
            tipo="WHATSAPP",
            ordem=30,
            ativo=True,
            conteudo={"numero": "5511987654321", "mensagem": "Mensagem privada do cliente"},
        )

        template_gerado = criar_template_a_partir_projeto(
            projeto=projeto,
            nome="Template Derivado",
            categoria=TemplateSite.Categoria.PROFISSIONAL,
            descricao="Criado a partir do projeto",
            substituir_placeholders=True,
        )

        self.assertEqual(template_gerado.origem, TemplateSite.Origem.USUARIO)
        self.assertEqual(template_gerado.nome, "Template Derivado")

        # Verifica sanitização
        snap = template_gerado.estrutura_snapshot
        elem_zap = snap["paginas"][0]["secoes"][0]["containers"][0]["elementos"][2]
        self.assertEqual(elem_zap["conteudo"]["numero"], PLACEHOLDERS["whatsapp_num"])
        self.assertEqual(elem_zap["conteudo"]["mensagem"], PLACEHOLDERS["whatsapp_msg"])

    def test_criar_bloco_a_partir_de_secao_com_sanitizacao(self):
        projeto = instanciar_template(
            template=self.template,
            cliente=self.cliente,
            nome="Projeto Bloco Secao",
        )
        secao = projeto.paginas.first().secoes.first()

        bloco_gerado = criar_bloco_a_partir_secao(
            secao=secao,
            nome="Meu Bloco Personalizado",
            categoria=BlocoReutilizavel.Categoria.HERO,
            substituir_placeholders=True,
        )

        self.assertEqual(bloco_gerado.origem, BlocoReutilizavel.Origem.USUARIO)
        self.assertEqual(bloco_gerado.nome, "Meu Bloco Personalizado")
        validar_snapshot_bloco(bloco_gerado.estrutura_snapshot)


class RenderizadorBioSiteSnapshotTests(TestCase):
    """Testes de renderização pura em memória a partir de snapshots JSON."""

    def test_renderizar_snapshot_template_em_memoria(self):
        renderer = RenderizadorBioSite(modo="preview")
        snapshot = _criar_snapshot_exemplo()
        html = renderer.renderizar_snapshot(snapshot)

        self.assertIn("biosite-canvas-root", html)
        self.assertIn("Agende Agora", html)
        self.assertIn("--cor-primaria: #38bdf8", html)

    def test_renderizar_snapshot_secao_em_memoria(self):
        renderer = RenderizadorBioSite(modo="preview")
        snapshot_bloco = _criar_snapshot_bloco_exemplo()
        html = renderer.renderizar_snapshot_secao(snapshot_bloco["secao"])

        self.assertIn("Entre em contato conosco.", html)


class ManagementCommandsTemplatesTests(TestCase):
    """Testes dos comandos de gestão carregar_templates_sistema e validar_templates."""

    def test_carregar_templates_sistema_idempotente(self):
        # Executa carga inicial
        call_command("carregar_templates_sistema")
        self.assertEqual(
            TemplateSite.objects.filter(origem=TemplateSite.Origem.SISTEMA).count(),
            8,
        )
        self.assertEqual(
            BlocoReutilizavel.objects.filter(origem=BlocoReutilizavel.Origem.SISTEMA).count(),
            15,
        )

        # Executa novamente: deve atualizar sem duplicar
        call_command("carregar_templates_sistema")
        self.assertEqual(
            TemplateSite.objects.filter(origem=TemplateSite.Origem.SISTEMA).count(),
            8,
        )
        self.assertEqual(
            BlocoReutilizavel.objects.filter(origem=BlocoReutilizavel.Origem.SISTEMA).count(),
            15,
        )

    def test_validar_templates_command(self):
        call_command("carregar_templates_sistema")
        # Deve executar sem erros
        call_command("validar_templates")


class ViewsTemplatesTests(TestCase):
    """Testes para as telas administrativas de biblioteca, previews e criação com templates."""

    def setUp(self):
        self.usuario = Usuario.objects.create_superuser(
            username="admin_templates",
            email="admin@templates.com",
            password="senha_segura_123",
        )
        self.client.force_login(self.usuario)

        self.cliente = Cliente.objects.create(nome="Cliente BioSite")
        self.template_sistema = TemplateSite.objects.create(
            nome="Template Sistema",
            slug="template-sistema",
            categoria=TemplateSite.Categoria.BIOSITE,
            origem=TemplateSite.Origem.SISTEMA,
            estrutura_snapshot=_criar_snapshot_exemplo(),
            ativo=True,
            ordem=1,
        )
        self.template_usuario = TemplateSite.objects.create(
            nome="Template Usuario",
            slug="template-usuario",
            categoria=TemplateSite.Categoria.PROFISSIONAL,
            origem=TemplateSite.Origem.USUARIO,
            estrutura_snapshot=_criar_snapshot_exemplo(),
            ativo=True,
            ordem=2,
        )
        self.bloco_sistema = BlocoReutilizavel.objects.create(
            nome="Bloco Sistema",
            slug="bloco-sistema",
            categoria=BlocoReutilizavel.Categoria.HERO,
            origem=BlocoReutilizavel.Origem.SISTEMA,
            estrutura_snapshot=_criar_snapshot_bloco_exemplo(),
            ativo=True,
            ordem=1,
        )

    def test_template_list_view_autenticado(self):
        url = reverse("painel:templates_lista")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Template Sistema")
        self.assertContains(resp, "Template Usuario")

    def test_template_list_view_filtro_origem(self):
        url = reverse("painel:templates_lista") + "?origem=usuario"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Template Usuario")
        self.assertNotContains(resp, "Template Sistema")

    def test_template_preview_view(self):
        url = reverse("painel:template_preview", kwargs={"uuid": self.template_sistema.uuid})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Agende Agora")
        self.assertContains(resp, "390px (Padrão)")
        self.assertContains(resp, "Usar Este Modelo")

    def test_template_duplicar_view(self):
        url = reverse("painel:template_duplicar", kwargs={"uuid": self.template_sistema.uuid})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)

        copia = TemplateSite.objects.filter(slug__startswith="template-sistema-copia").first()
        self.assertIsNotNone(copia)
        self.assertEqual(copia.origem, TemplateSite.Origem.USUARIO)

    def test_template_arquivar_e_excluir_usuario(self):
        # Arquivar
        url_arq = reverse("painel:template_arquivar", kwargs={"uuid": self.template_usuario.uuid})
        resp = self.client.post(url_arq)
        self.assertEqual(resp.status_code, 302)
        self.template_usuario.refresh_from_db()
        self.assertFalse(self.template_usuario.ativo)

        # Excluir
        url_del = reverse("painel:template_excluir", kwargs={"uuid": self.template_usuario.uuid})
        resp = self.client.post(url_del)
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(TemplateSite.objects.filter(id=self.template_usuario.id).exists())

    def test_template_sistema_imovel_bloqueia_exclusao_e_arquivamento(self):
        url_del = reverse("painel:template_excluir", kwargs={"uuid": self.template_sistema.uuid})
        self.client.post(url_del)
        self.assertTrue(TemplateSite.objects.filter(id=self.template_sistema.id).exists())

        url_arq = reverse("painel:template_arquivar", kwargs={"uuid": self.template_sistema.uuid})
        self.client.post(url_arq)
        self.template_sistema.refresh_from_db()
        self.assertTrue(self.template_sistema.ativo)

    def test_salvar_como_template_via_editor(self):
        projeto = instanciar_template(
            template=self.template_sistema,
            cliente=self.cliente,
            nome="Projeto Base Para Template",
        )
        url = reverse("painel:site_salvar_template", kwargs={"uuid": projeto.uuid})
        payload = {
            "nome": "Novo Template Criado",
            "categoria": "profissional",
            "descricao": "Meu modelo salvo",
            "substituir_placeholders": True,
        }
        resp = self.client.post(url, json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertTrue(TemplateSite.objects.filter(nome="Novo Template Criado").exists())

    def test_editor_blocos_listar_view(self):
        projeto = instanciar_template(
            template=self.template_sistema,
            cliente=self.cliente,
            nome="Projeto Listar Blocos",
        )
        url = reverse("painel:site_editor_blocos_listar", kwargs={"uuid": projeto.uuid})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertGreaterEqual(len(data["blocos"]), 1)

    def test_editor_bloco_inserir_view(self):
        projeto = instanciar_template(
            template=self.template_sistema,
            cliente=self.cliente,
            nome="Projeto Inserir Bloco",
        )
        url = reverse("painel:site_editor_bloco_inserir", kwargs={"uuid": projeto.uuid})
        payload = {
            "bloco_id": self.bloco_sistema.id,
            "pagina_id": projeto.paginas.first().id,
        }
        resp = self.client.post(url, json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertIn("secao_id", data)
        self.assertIn("html", data)

    def test_editor_secao_salvar_bloco_view(self):
        projeto = instanciar_template(
            template=self.template_sistema,
            cliente=self.cliente,
            nome="Projeto Salvar Bloco",
        )
        secao = projeto.paginas.first().secoes.first()
        url = reverse(
            "painel:site_editor_secao_salvar_bloco",
            kwargs={"uuid": projeto.uuid, "secao_id": secao.id},
        )
        payload = {
            "nome": "Meu Bloco Extraído",
            "categoria": "hero",
            "descricao": "Bloco criado do editor",
            "substituir_placeholders": True,
        }
        resp = self.client.post(url, json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertTrue(BlocoReutilizavel.objects.filter(nome="Meu Bloco Extraído").exists())

    def test_criar_site_a_partir_de_template_redireciona_editor(self):
        url = reverse("painel:site_novo")
        dados = {
            "cliente": self.cliente.pk,
            "nome": "Site a partir de Modelo",
            "slug": "site-do-modelo",
            "tipo": ProjetoSite.Tipo.BIOSITE,
            "template_origem": self.template_sistema.pk,
        }
        resp = self.client.post(url, dados)
        projeto = ProjetoSite.objects.filter(slug="site-do-modelo").first()
        self.assertIsNotNone(projeto)
        self.assertEqual(projeto.template_origem, self.template_sistema)
        # Redireciona diretamente para o editor
        self.assertRedirects(resp, reverse("painel:site_editor", kwargs={"uuid": projeto.uuid}))

    def test_controle_acesso_anonimo_bloqueado(self):
        self.client.logout()
        url = reverse("painel:templates_lista")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
