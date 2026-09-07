"""Testes automatizados completos do Motor Estrutural de Páginas, Seções, Containers e Elementos (Prompt 4)."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from aplicativos.clientes.models import Cliente

from .elementos import RegistroElementos
from .models import ContainerSite, ElementoSite, PaginaSite, ProjetoSite, SecaoSite
from .servicos import duplicar_projeto
from .servicos_estrutura import (
    auditar_integridade_projeto,
    criar_secao_com_container_padrao,
    duplicar_elemento,
    duplicar_pagina,
    duplicar_secao,
    garantir_pagina_inicial,
    obter_estrutura_projeto,
    reordenar_entidades,
)

Usuario = get_user_model()


class EstruturaModelosTests(TestCase):
    """Testes de integridade, representação e constraints dos modelos estruturais."""

    def setUp(self):
        self.cliente = Cliente.objects.create(nome="Cliente Teste Estrutura")
        self.projeto = ProjetoSite.objects.create(
            cliente=self.cliente,
            nome="BioSite Estrutura",
            slug="biosite-estrutura",
        )

    def test_criar_hierarquia_completa(self):
        pagina = PaginaSite.objects.create(
            projeto=self.projeto,
            titulo="Início",
            slug="inicio",
            ordem=10,
            eh_inicial=True,
        )
        secao = SecaoSite.objects.create(
            pagina=pagina,
            nome_interno="Hero",
            ordem=10,
            tipo=SecaoSite.Tipo.NORMAL,
        )
        container = ContainerSite.objects.create(
            secao=secao,
            ordem=10,
            tipo_layout=ContainerSite.TipoLayout.STACK,
        )
        elemento = ElementoSite.objects.create(
            container=container,
            tipo="TITULO",
            ordem=10,
            conteudo={"texto": "Bem-vindo ao BioSite", "nivel": "h1"},
        )

        self.assertIn("Início", str(pagina))
        self.assertIn("Hero", str(secao))
        self.assertIn("Stack", str(container))
        self.assertIn("Titulo", str(elemento))
        self.assertIsNotNone(pagina.uuid)

        self.assertIsNotNone(secao.uuid)
        self.assertIsNotNone(container.uuid)
        self.assertIsNotNone(elemento.uuid)

    def test_constraint_unicidade_slug_pagina_por_projeto(self):
        PaginaSite.objects.create(
            projeto=self.projeto,
            titulo="Sobre",
            slug="sobre",
            eh_inicial=False,
        )

        # Tentativa de duplicar o slug no mesmo projeto deve falhar
        with self.assertRaises(IntegrityError):
            PaginaSite.objects.create(
                projeto=self.projeto,
                titulo="Sobre a Empresa",
                slug="sobre",
                eh_inicial=False,
            )

    def test_slug_identico_em_projetos_diferentes_permitido(self):
        outro_projeto = ProjetoSite.objects.create(
            cliente=self.cliente,
            nome="Outro Site",
            slug="outro-site",
        )
        p1 = PaginaSite.objects.create(
            projeto=self.projeto,
            titulo="Contato",
            slug="contato",
            eh_inicial=False,
        )
        p2 = PaginaSite.objects.create(
            projeto=outro_projeto,
            titulo="Contato",
            slug="contato",
            eh_inicial=False,
        )
        self.assertNotEqual(p1.projeto, p2.projeto)
        self.assertEqual(p1.slug, p2.slug)

    def test_constraint_unicidade_pagina_inicial_por_projeto(self):
        PaginaSite.objects.create(
            projeto=self.projeto,
            titulo="Home 1",
            slug="home-1",
            eh_inicial=True,
        )

        # Criar segunda página com eh_inicial=True no mesmo projeto deve violar a constraint
        with self.assertRaises(IntegrityError):
            PaginaSite.objects.create(
                projeto=self.projeto,
                titulo="Home 2",
                slug="home-2",
                eh_inicial=True,
            )

    def test_multiplas_paginas_nao_iniciais_permitidas(self):
        PaginaSite.objects.create(
            projeto=self.projeto,
            titulo="Página 1",
            slug="p1",
            eh_inicial=False,
        )
        PaginaSite.objects.create(
            projeto=self.projeto,
            titulo="Página 2",
            slug="p2",
            eh_inicial=False,
        )
        self.assertEqual(self.projeto.paginas.filter(eh_inicial=False).count(), 2)

    def test_auto_adicao_pagina_inicial_ao_criar_projeto_via_service(self):
        novo_proj = ProjetoSite.objects.create(
            cliente=self.cliente,
            nome="Site Sem Home",
            slug="site-sem-home",
        )
        home = garantir_pagina_inicial(novo_proj)
        self.assertTrue(home.eh_inicial)
        self.assertEqual(home.slug, "inicio")
        self.assertEqual(home.projeto, novo_proj)
        self.assertGreaterEqual(home.secoes.count(), 1)


class ContainerIntegridadeTests(TestCase):
    """Testes de regras de negócio, limites de aninhamento e integridade de containers."""

    def setUp(self):
        self.cliente = Cliente.objects.create(nome="Cliente Container")
        self.projeto = ProjetoSite.objects.create(
            cliente=self.cliente,
            nome="Site Container",
            slug="site-container",
        )
        self.pagina = PaginaSite.objects.create(
            projeto=self.projeto,
            titulo="Home",
            slug="inicio",
            eh_inicial=True,
        )
        self.secao1 = SecaoSite.objects.create(
            pagina=self.pagina,
            nome_interno="Secao 1",
            ordem=10,
        )
        self.secao2 = SecaoSite.objects.create(
            pagina=self.pagina,
            nome_interno="Secao 2",
            ordem=20,
        )

    def test_container_raiz_e_filho_valido(self):
        raiz = ContainerSite.objects.create(
            secao=self.secao1,
            parent=None,
            tipo_layout=ContainerSite.TipoLayout.STACK,
        )
        raiz.full_clean()

        filho = ContainerSite.objects.create(
            secao=self.secao1,
            parent=raiz,
            tipo_layout=ContainerSite.TipoLayout.ROW,
        )
        filho.full_clean()

        self.assertEqual(raiz.obter_profundidade(), 1)
        self.assertEqual(filho.obter_profundidade(), 2)

    def test_bloqueio_container_pai_em_secao_diferente(self):
        container_secao1 = ContainerSite.objects.create(
            secao=self.secao1,
            parent=None,
        )

        container_invalido = ContainerSite(
            secao=self.secao2,
            parent=container_secao1,
        )

        with self.assertRaises(ValidationError) as ctx:
            container_invalido.full_clean()
        self.assertIn("mesma seção", str(ctx.exception))

    def test_bloqueio_container_pai_de_si_mesmo(self):
        container = ContainerSite.objects.create(
            secao=self.secao1,
            parent=None,
        )
        container.parent = container

        with self.assertRaises(ValidationError) as ctx:
            container.full_clean()
        self.assertIn("não pode ser pai de si mesmo", str(ctx.exception))

    def test_bloqueio_profundidade_maxima_excedida(self):
        c1 = ContainerSite.objects.create(secao=self.secao1, parent=None)
        c2 = ContainerSite.objects.create(secao=self.secao1, parent=c1)
        c3 = ContainerSite.objects.create(secao=self.secao1, parent=c2)

        self.assertEqual(c3.obter_profundidade(), 3)

        # Nível 4 deve ser bloqueado
        c4 = ContainerSite(secao=self.secao1, parent=c3)
        with self.assertRaises(ValidationError) as ctx:
            c4.full_clean()
        self.assertIn("profundidade", str(ctx.exception).lower())


class ElementoRegistryESegurancaTests(TestCase):
    """Testes do registry extensível, schemas de conteúdo, sanitização e segurança XSS."""

    def setUp(self):
        self.cliente = Cliente.objects.create(nome="Cliente Registry")
        self.projeto = ProjetoSite.objects.create(
            cliente=self.cliente,
            nome="Site Registry",
            slug="site-registry",
        )
        self.pagina = PaginaSite.objects.create(
            projeto=self.projeto,
            titulo="Home",
            slug="inicio",
            eh_inicial=True,
        )
        self.secao = SecaoSite.objects.create(
            pagina=self.pagina,
            nome_interno="Secao",
        )
        self.container = ContainerSite.objects.create(
            secao=self.secao,
        )

    def test_tipos_padrao_registrados(self):
        tipos = RegistroElementos.obter_tipos_registrados()
        for t in ["TITULO", "TEXTO", "BOTAO", "IMAGEM", "ESPACADOR", "ICONE"]:
            self.assertIn(t, tipos)

    def test_tipo_nao_registrado_rejeitado(self):
        elem = ElementoSite(
            container=self.container,
            tipo="TIPO_INEXISTENTE_HACK",
            conteudo={},
        )

        with self.assertRaises(ValidationError) as ctx:
            elem.full_clean()
        self.assertIn("não registrado", str(ctx.exception).lower())

    def test_elemento_titulo_sanitizacao_e_validacao(self):
        elem = ElementoSite(
            container=self.container,
            tipo="TITULO",
            conteudo={"texto": "<script>alert('xss')</script>Título Seguro", "nivel": "h1"},
        )
        elem.full_clean()
        elem.save()

        # O script deve ser escapado
        self.assertNotIn("<script>", elem.conteudo["texto"])
        self.assertIn("&lt;script&gt;", elem.conteudo["texto"])

    def test_elemento_botao_bloqueia_javascript_protocol(self):
        elem = ElementoSite(
            container=self.container,
            tipo="BOTAO",
            conteudo={"texto": "Clique Aqui", "url": "javascript:alert(document.cookie)"},
        )
        with self.assertRaises(ValidationError) as ctx:
            elem.full_clean()
        self.assertIn("javascript:", str(ctx.exception).lower())

    def test_elemento_botao_aceita_urls_seguras(self):
        for url_valida in [
            "https://meubiosite.com/contato",
            "mailto:contato@site.com",
            "tel:+5511999999999",
            "/sobre",
        ]:
            elem = ElementoSite(
                container=self.container,
                tipo="BOTAO",
                conteudo={"texto": "Botão", "url": url_valida},
            )
            elem.full_clean()
            self.assertEqual(elem.conteudo["url"], url_valida)

    def test_validacao_estilos_mobile_first_allowlist(self):
        # Propriedade de estilo arbitrária não permitida deve ser rejeitada
        elem = ElementoSite(
            container=self.container,
            tipo="TITULO",
            conteudo={"texto": "Título"},
            estilos={"base": {"expressao_arbitraria_css": "hack"}},
        )
        with self.assertRaises(ValidationError) as ctx:
            elem.full_clean()
        self.assertIn("não permitida", str(ctx.exception).lower())

        # Propriedades da allowlist válidas
        elem_valido = ElementoSite(
            container=self.container,
            tipo="TITULO",
            conteudo={"texto": "Título"},
            estilos={
                "base": {"color": "#1e293b", "font-size": "24px", "text-align": "center"},
                "desktop": {"font-size": "36px"},
            },
        )
        elem_valido.full_clean()


class EstruturaDuplicacaoTests(TestCase):
    """Testes de duplicação profunda de elementos, seções, páginas e do projeto completo."""

    def setUp(self):
        self.cliente = Cliente.objects.create(nome="Cliente Duplicação")
        self.projeto = ProjetoSite.objects.create(
            cliente=self.cliente,
            nome="Site Original Completo",
            slug="site-original-completo",
            status=ProjetoSite.Status.PUBLICADO,
        )
        self.pagina = PaginaSite.objects.create(
            projeto=self.projeto,
            titulo="Início",
            slug="inicio",
            eh_inicial=True,
        )
        self.secao, self.container = criar_secao_com_container_padrao(
            pagina=self.pagina,
            nome_interno="Hero Seção",
        )
        self.elemento = ElementoSite.objects.create(
            container=self.container,
            tipo="TITULO",
            conteudo={"texto": "Título Original", "nivel": "h2"},
            estilos={"base": {"color": "#000000"}},
        )

    def test_duplicar_elemento_isolado(self):
        copia = duplicar_elemento(self.elemento)

        self.assertNotEqual(copia.id, self.elemento.id)
        self.assertNotEqual(copia.uuid, self.elemento.uuid)
        self.assertEqual(copia.tipo, self.elemento.tipo)
        self.assertEqual(copia.conteudo, self.elemento.conteudo)
        self.assertEqual(copia.ordem, self.elemento.ordem + 10)

        # Modificação no clone não pode afetar o original
        copia.conteudo["texto"] = "Título Modificado"
        copia.save()
        self.elemento.refresh_from_db()
        self.assertEqual(self.elemento.conteudo["texto"], "Título Original")

    def test_duplicar_secao_recursivamente(self):
        copia_secao = duplicar_secao(self.secao)

        self.assertNotEqual(copia_secao.id, self.secao.id)
        self.assertNotEqual(copia_secao.uuid, self.secao.uuid)
        self.assertIn("Cópia", copia_secao.nome_interno)
        self.assertEqual(copia_secao.containers.count(), 1)

        clone_container = copia_secao.containers.first()
        self.assertEqual(clone_container.elementos.count(), 1)
        self.assertEqual(clone_container.elementos.first().conteudo["texto"], "Título Original")

    def test_duplicar_pagina_recursivamente(self):
        copia_pagina = duplicar_pagina(self.pagina)

        self.assertNotEqual(copia_pagina.id, self.pagina.id)
        self.assertNotEqual(copia_pagina.uuid, self.pagina.uuid)
        self.assertFalse(
            copia_pagina.eh_inicial
        )  # Cópia não pode ser inicial para não violar constraint
        self.assertIn("-copia", copia_pagina.slug)
        self.assertEqual(copia_pagina.secoes.count(), 1)

    def test_duplicar_projeto_completo_profundo(self):
        # Chama a função unificada duplicar_projeto
        copia_proj = duplicar_projeto(self.projeto)

        self.assertNotEqual(copia_proj.id, self.projeto.id)
        self.assertNotEqual(copia_proj.uuid, self.projeto.uuid)
        self.assertEqual(copia_proj.status, ProjetoSite.Status.RASCUNHO)
        self.assertEqual(copia_proj.slug, "site-original-completo-copia")
        self.assertEqual(copia_proj.paginas.count(), 1)

        clone_pag = copia_proj.paginas.first()
        self.assertTrue(clone_pag.eh_inicial)
        self.assertEqual(clone_pag.secoes.count(), 1)

        clone_sec = clone_pag.secoes.first()
        self.assertEqual(clone_sec.containers.count(), 1)
        self.assertEqual(clone_sec.containers.first().elementos.count(), 1)


class EstruturaServicosEPerformanceTests(TestCase):
    """Testes de ordenação, serialização, auditoria e consultas N+1."""

    def setUp(self):
        self.cliente = Cliente.objects.create(nome="Cliente Performance")
        self.projeto = ProjetoSite.objects.create(
            cliente=self.cliente,
            nome="Site Performance",
            slug="site-performance",
        )
        self.pagina = PaginaSite.objects.create(
            projeto=self.projeto,
            titulo="Início",
            slug="inicio",
            eh_inicial=True,
        )

    def test_reordenar_entidades_passos_de_10(self):
        s1, _ = criar_secao_com_container_padrao(self.pagina, "Seção A")
        s2, _ = criar_secao_com_container_padrao(self.pagina, "Seção B")
        s3, _ = criar_secao_com_container_padrao(self.pagina, "Seção C")

        # Inverte a ordem: C, A, B
        reordenar_entidades(SecaoSite, [s3.id, s1.id, s2.id], "pagina_id", self.pagina.id)

        s1.refresh_from_db()
        s2.refresh_from_db()
        s3.refresh_from_db()

        self.assertEqual(s3.ordem, 10)
        self.assertEqual(s1.ordem, 20)
        self.assertEqual(s2.ordem, 30)

    def test_auditar_integridade_projeto(self):
        # Projeto com 1 home saudável
        anomalias = auditar_integridade_projeto(self.projeto)
        self.assertEqual(anomalias, [])

        # Projeto sem home
        self.pagina.eh_inicial = False
        self.pagina.save()
        anomalias = auditar_integridade_projeto(self.projeto)
        self.assertTrue(any("não possui página inicial" in a for a in anomalias))

    def test_obter_estrutura_projeto_queries_otimizadas(self):
        """Verifica que a serialização da árvore completa não gera consultas N+1."""
        # Cria árvore rica: 2 páginas adicionais, 4 seções, 6 containers, 12 elementos
        for i in range(2):
            pag = PaginaSite.objects.create(
                projeto=self.projeto,
                titulo=f"Pag {i}",
                slug=f"pag-{i}",
                eh_inicial=False,
            )

            for j in range(2):
                sec, cont = criar_secao_com_container_padrao(pag, f"Sec {j}")
                for k in range(3):
                    ElementoSite.objects.create(
                        container=cont,
                        tipo="TEXTO",
                        conteudo={"texto": f"Texto {k}"},
                    )

        # A serialização com prefetch_related executa exatamente 5 queries (zero N+1)
        with self.assertNumQueries(5):
            estrutura = obter_estrutura_projeto(self.projeto)

        self.assertEqual(len(estrutura["paginas"]), 3)  # self.pagina + 2 novas
        self.assertEqual(estrutura["projeto"]["slug"], "site-performance")


class EstruturaViewsTests(TestCase):
    """Testes de views administrativas de estrutura e proteção contra IDOR."""

    def setUp(self):
        self.operador = Usuario.objects.create_user(
            username="operador_estrutura",
            email="estrutura@biosite.local",
            password="SenhaForte123!",
            is_staff=True,
        )
        self.client.force_login(self.operador)

        self.cliente = Cliente.objects.create(nome="Cliente Views")
        self.projeto = ProjetoSite.objects.create(
            cliente=self.cliente,
            nome="Site Views",
            slug="site-views",
        )
        self.pagina = PaginaSite.objects.create(
            projeto=self.projeto,
            titulo="Início",
            slug="inicio",
            eh_inicial=True,
        )
        self.secao, self.container = criar_secao_com_container_padrao(
            pagina=self.pagina,
            nome_interno="Hero Views",
        )

        # Outro projeto para testes de IDOR
        self.outro_projeto = ProjetoSite.objects.create(
            cliente=self.cliente,
            nome="Outro Site",
            slug="outro-site-views",
        )
        self.outra_pagina = PaginaSite.objects.create(
            projeto=self.outro_projeto,
            titulo="Início",
            slug="inicio",
            eh_inicial=True,
        )
        self.outra_secao, self.outro_container = criar_secao_com_container_padrao(
            pagina=self.outra_pagina,
            nome_interno="Hero Alheia",
        )

    def test_visualizar_estrutura_200_ok(self):
        url = reverse("painel:site_estrutura", kwargs={"uuid": self.projeto.uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hero Views")
        self.assertContains(response, "Início")

    def test_visualizar_estrutura_json_200_ok(self):
        url = reverse("painel:site_estrutura_json", kwargs={"uuid": self.projeto.uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        dados = response.json()
        self.assertEqual(dados["projeto"]["slug"], "site-views")
        self.assertGreaterEqual(len(dados["paginas"]), 1)

    def test_criar_pagina_via_post(self):
        url = reverse("painel:site_estrutura_pagina_criar", kwargs={"uuid": self.projeto.uuid})
        response = self.client.post(url, {"titulo": "Quem Somos", "slug": "quem-somos"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(PaginaSite.objects.filter(projeto=self.projeto, slug="quem-somos").exists())

    def test_criar_elemento_via_post(self):
        url = reverse("painel:site_estrutura_elemento_criar", kwargs={"uuid": self.projeto.uuid})
        response = self.client.post(
            url,
            {
                "container_id": self.container.id,
                "tipo": "BOTAO",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ElementoSite.objects.filter(container=self.container, tipo="BOTAO").exists()
        )

    def test_protecao_idor_ao_tentar_duplicar_secao_de_outro_projeto(self):
        """Não permite que requisição na URL do projeto A manipule seção pertencente ao projeto B."""
        url = reverse(
            "painel:site_estrutura_secao_duplicar",
            kwargs={"uuid": self.projeto.uuid, "secao_id": self.outra_secao.id},
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)

    def test_protecao_idor_ao_tentar_excluir_secao_de_outro_projeto(self):
        url = reverse(
            "painel:site_estrutura_secao_excluir",
            kwargs={"uuid": self.projeto.uuid, "secao_id": self.outra_secao.id},
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)
        # Garante que a seção alheia continua existindo intacta
        self.assertTrue(SecaoSite.objects.filter(id=self.outra_secao.id).exists())
