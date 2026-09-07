"""Modelos para gerenciamento de projetos de sites, páginas, seções, containers e elementos."""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from aplicativos.core.models import ModeloBase

from .elementos.registry import registro_elementos


class ProjetoSite(ModeloBase):
    """
    Representa a identidade administrativa de um projeto de site ou BioSite.

    REGRAS ARQUITETURAIS:
    1. Vinculado obrigatoriamente a um Cliente comercial via PROTECT (impede deleção cascateada acidental).
    2. Possui slug único validado contra palavras reservadas.
    3. Status inicial estrito como RASCUNHO.
    4. Base relacional para o motor de páginas e elementos.
    """

    class Tipo(models.TextChoices):
        BIOSITE = "biosite", _("BioSite")
        LANDING_PAGE = "landing_page", _("Landing Page")
        SITE = "site", _("Site Institucional")
        PORTFOLIO = "portfolio", _("Portfólio")
        CARDAPIO = "cardapio", _("Cardápio Digital")
        OUTRO = "outro", _("Outro")

    class Status(models.TextChoices):
        RASCUNHO = "rascunho", _("Rascunho")
        PUBLICADO = "publicado", _("Publicado")
        ARQUIVADO = "arquivado", _("Arquivado")
        SUSPENSO = "suspenso", _("Suspenso")

    cliente = models.ForeignKey(
        "clientes.Cliente",
        on_delete=models.PROTECT,
        related_name="projetos",
        verbose_name=_("Cliente"),
        help_text=_("Cliente comercial proprietário deste projeto."),
    )
    nome = models.CharField(
        _("Nome do Projeto"),
        max_length=150,
        help_text=_("Nome de identificação administrativa do projeto."),
    )
    slug = models.SlugField(
        _("Endereço (Slug)"),
        max_length=100,
        unique=True,
        db_index=True,
        help_text=_("Identificador amigável de URL exclusivo do site."),
    )
    tipo = models.CharField(
        _("Tipo de Projeto"),
        max_length=30,
        choices=Tipo.choices,
        default=Tipo.BIOSITE,
        db_index=True,
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=Status.choices,
        default=Status.RASCUNHO,
        db_index=True,
    )
    descricao_interna = models.TextField(
        _("Descrição Interna"),
        blank=True,
        help_text=_("Notas administrativas internas sobre o escopo ou contrato."),
    )
    thumbnail = models.ImageField(
        _("Miniatura"),
        upload_to="projetos/thumbnails/",
        null=True,
        blank=True,
        help_text=_("Imagem de visualização no workspace (opcional)."),
    )
    arquivado_em = models.DateTimeField(
        _("Arquivado em"),
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("projeto de site")
        verbose_name_plural = _("projetos de sites")
        ordering = ["-atualizado_em"]

    def __str__(self) -> str:
        return self.nome

    def arquivar(self) -> None:
        """Move o projeto para o status arquivado."""
        self.status = self.Status.ARQUIVADO
        self.arquivado_em = timezone.now()
        self.save(update_fields=["status", "arquivado_em", "atualizado_em"])

    def restaurar(self) -> None:
        """Restaura o projeto para o status de rascunho ativo."""
        self.status = self.Status.RASCUNHO
        self.arquivado_em = None
        self.save(update_fields=["status", "arquivado_em", "atualizado_em"])


class PaginaSite(ModeloBase):
    """
    Representa uma página de um ProjetoSite.

    REGRAS:
    - Um projeto possui exatamente uma página inicial (eh_inicial=True).
    - O slug é único dentro do escopo daquele projeto específico.
    - Ordenação sequencial explícita.
    """

    projeto = models.ForeignKey(
        ProjetoSite,
        on_delete=models.CASCADE,
        related_name="paginas",
        verbose_name=_("Projeto"),
    )
    titulo = models.CharField(
        _("Título da Página"),
        max_length=150,
        help_text=_("Ex: Início, Sobre, Serviços, Contato."),
    )
    slug = models.SlugField(
        _("Slug da Página"),
        max_length=100,
        help_text=_("Identificador da página na URL (ex: inicio, sobre)."),
    )
    ordem = models.PositiveIntegerField(
        _("Ordem"),
        default=10,
        help_text=_("Ordem sequencial da página na navegação."),
    )
    eh_inicial = models.BooleanField(
        _("Página Inicial"),
        default=False,
        help_text=_("Indica se esta é a página principal exibida na raiz do site."),
    )
    ativa = models.BooleanField(
        _("Ativa"),
        default=True,
        help_text=_("Páginas inativas ficam ocultas na navegação pública."),
    )

    class Meta:
        verbose_name = _("página do site")
        verbose_name_plural = _("páginas do site")
        ordering = ["ordem", "criado_em"]
        constraints = [
            models.UniqueConstraint(
                fields=["projeto", "slug"],
                name="unique_pagina_slug_por_projeto",
            ),
            models.UniqueConstraint(
                fields=["projeto"],
                condition=models.Q(eh_inicial=True),
                name="unique_pagina_inicial_por_projeto",
            ),
        ]

    def __str__(self) -> str:
        sufixo = " (Início)" if self.eh_inicial else ""
        return f"{self.titulo}{sufixo}"

    def clean(self) -> None:
        super().clean()
        if self.eh_inicial and self.projeto_id:
            qs = PaginaSite.objects.filter(projeto_id=self.projeto_id, eh_inicial=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError(
                    _("O projeto já possui uma página inicial definida."),
                    code="multiple_home_pages",
                )


class SecaoSite(ModeloBase):
    """
    Representa um grande bloco vertical na composição da página.

    Exemplos: Hero, Apresentação, Grade de Serviços, Contato.
    """

    class Tipo(models.TextChoices):
        NORMAL = "normal", _("Normal")
        ALTURA_MINIMA = "altura_minima", _("Altura Mínima")
        TELA_CHEIA = "tela_cheia", _("Tela Cheia")

    pagina = models.ForeignKey(
        PaginaSite,
        on_delete=models.CASCADE,
        related_name="secoes",
        verbose_name=_("Página"),
    )
    nome_interno = models.CharField(
        _("Nome Interno"),
        max_length=150,
        help_text=_("Identificador administrativo da seção (ex: Hero Principal, Contato)."),
    )
    ordem = models.PositiveIntegerField(
        _("Ordem"),
        default=10,
        help_text=_("Posição vertical da seção na página."),
    )
    tipo = models.CharField(
        _("Tipo de Seção"),
        max_length=30,
        choices=Tipo.choices,
        default=Tipo.NORMAL,
    )
    ativa = models.BooleanField(
        _("Ativa"),
        default=True,
        help_text=_("Seções desativadas não são renderizadas publicamente."),
    )
    configuracao = models.JSONField(
        _("Configuração"),
        default=dict,
        blank=True,
    )
    estilos = models.JSONField(
        _("Estilos"),
        default=dict,
        blank=True,
        help_text=_("Estilos estruturais mobile-first: {'base': {...}, 'desktop': {...}}."),
    )

    class Meta:
        verbose_name = _("seção do site")
        verbose_name_plural = _("seções do site")
        ordering = ["ordem", "criado_em"]

    def __str__(self) -> str:
        return f"{self.nome_interno} ({self.pagina.titulo})"


class ContainerSite(ModeloBase):
    """
    Controla o layout interno e a distribuição dos elementos dentro de uma Seção.

    Padrão mobile: STACK (elementos empilhados verticalmente).
    Suporta aninhamento controlado até 3 níveis de profundidade.
    """

    MAX_PROFUNDIDADE: int = 3

    class TipoLayout(models.TextChoices):
        STACK = "stack", _("Pilha Vertical (Stack)")
        ROW = "row", _("Linha Horizontal (Row)")
        GRID = "grid", _("Grade (Grid)")
        OVERLAY = "overlay", _("Sobreposição (Overlay)")

    secao = models.ForeignKey(
        SecaoSite,
        on_delete=models.CASCADE,
        related_name="containers",
        verbose_name=_("Seção"),
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="filhos",
        verbose_name=_("Container Pai"),
        help_text=_("Container ancestral para layouts compostos (máx 3 níveis)."),
    )
    ordem = models.PositiveIntegerField(
        _("Ordem"),
        default=10,
    )
    tipo_layout = models.CharField(
        _("Tipo de Layout"),
        max_length=30,
        choices=TipoLayout.choices,
        default=TipoLayout.STACK,
    )
    ativo = models.BooleanField(
        _("Ativo"),
        default=True,
    )
    configuracao = models.JSONField(
        _("Configuração"),
        default=dict,
        blank=True,
    )
    estilos = models.JSONField(
        _("Estilos"),
        default=dict,
        blank=True,
    )

    class Meta:
        verbose_name = _("container do site")
        verbose_name_plural = _("containers do site")
        ordering = ["ordem", "criado_em"]

    def __str__(self) -> str:
        return f"Container {self.get_tipo_layout_display()} [#{self.id}]"

    def obter_profundidade(self) -> int:
        """Calcula a profundidade do container na árvore hierárquica (1 = raiz da seção)."""
        profundidade = 1
        atual = self.parent
        visitados = {self.pk} if self.pk else set()

        while atual is not None:
            if atual.pk in visitados:
                raise ValidationError(_("Ciclo detectado na hierarquia de containers."))
            visitados.add(atual.pk)
            profundidade += 1
            if profundidade > self.MAX_PROFUNDIDADE + 5:
                break
            atual = atual.parent

        return profundidade

    def clean(self) -> None:
        super().clean()
        if self.parent:
            # Não pode cruzar seções diferentes
            if self.parent.secao_id != self.secao_id:
                raise ValidationError(
                    _("O container pai deve pertencer obrigatoriamente à mesma seção."),
                    code="cross_section_parent",
                )

            # Prevenção de ciclos (A -> B -> A)
            ancestral = self.parent
            while ancestral is not None:
                if self.pk and ancestral.pk == self.pk:
                    raise ValidationError(
                        _(
                            "Ciclo proibido: um container não pode ser pai de si mesmo ou de um ancestral."
                        ),
                        code="container_cycle",
                    )
                ancestral = ancestral.parent

            # Limite de profundidade máxima
            if self.parent.obter_profundidade() >= self.MAX_PROFUNDIDADE:
                raise ValidationError(
                    _("A profundidade máxima de aninhamento de %(max)d containers foi atingida."),
                    code="max_depth_exceeded",
                    params={"max": self.MAX_PROFUNDIDADE},
                )


class ElementoSite(ModeloBase):
    """
    Unidade atômica de conteúdo do construtor de sites.

    REGRAS DE SEGURANÇA:
    1. Nunca armazena código HTML/JS/CSS arbitrário ou sem validação.
    2. Valida o payload de 'conteudo' contra o schema do tipo registrado em RegistroElementos.
    3. Estilos estruturados seguindo o padrão mobile-first: {'base': {...}, 'desktop': {...}}.
    """

    container = models.ForeignKey(
        ContainerSite,
        on_delete=models.CASCADE,
        related_name="elementos",
        verbose_name=_("Container"),
    )
    tipo = models.CharField(
        _("Tipo de Elemento"),
        max_length=50,
        db_index=True,
    )
    ordem = models.PositiveIntegerField(
        _("Ordem"),
        default=10,
    )
    ativo = models.BooleanField(
        _("Ativo"),
        default=True,
    )
    conteudo = models.JSONField(
        _("Conteúdo"),
        default=dict,
        blank=True,
    )
    estilos = models.JSONField(
        _("Estilos"),
        default=dict,
        blank=True,
        help_text=_("Estilos mobile-first: {'base': {...}, 'desktop': {...}}."),
    )
    configuracao = models.JSONField(
        _("Configuração"),
        default=dict,
        blank=True,
    )
    versao_schema = models.PositiveIntegerField(
        _("Versão do Schema"),
        default=1,
    )

    class Meta:
        verbose_name = _("elemento do site")
        verbose_name_plural = _("elementos do site")
        ordering = ["ordem", "criado_em"]

    def __str__(self) -> str:
        return f"{self.tipo.capitalize()} [#{self.id}] em {self.container}"

    def clean(self) -> None:
        super().clean()
        # Validação do tipo no Registry
        definicao = registro_elementos.obter(self.tipo)

        # Preenchimento de defaults se vazios
        if not self.conteudo:
            self.conteudo = definicao.conteudo_padrao()
        if not self.estilos:
            self.estilos = definicao.estilos_padrao()

        # Validação estrita do schema do tipo
        definicao.validar_conteudo(self.conteudo)
        definicao.validar_estilos(self.estilos)

    def renderizar(self, contexto: dict | None = None) -> str:
        """Renderiza o elemento em HTML sanitizado através de sua definição de tipo."""
        definicao = registro_elementos.obter(self.tipo)
        return definicao.render(self, contexto)
