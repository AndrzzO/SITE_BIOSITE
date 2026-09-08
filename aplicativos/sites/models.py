import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from aplicativos.core.models import ModeloBase

from .elementos.registry import registro_elementos

HEX_COLOR_REGEX = re.compile(r"^#(?:[0-9a-fA-F]{3}){1,2}$")


def validar_cor_hex(valor: str) -> None:
    """Valida se o valor informado é uma cor hexadecimal válida (#RGB ou #RRGGBB)."""
    if valor and not HEX_COLOR_REGEX.match(str(valor).strip()):
        raise ValidationError(_("Cor hexadecimal inválida. Utilize o formato #RGB ou #RRGGBB."))


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
    template_origem = models.ForeignKey(
        "TemplateSite",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projetos_derivados",
        verbose_name=_("Modelo de Origem"),
        help_text=_("Modelo/template utilizado como ponto de partida inicial (informativo)."),
    )
    # Publicação e SEO (Prompt 8)
    publicacao_ativa = models.ForeignKey(
        "PublicacaoSite",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projeto_ativo_set",
        verbose_name=_("Publicação Ativa"),
        help_text=_("Ponteiro direto para a versão de publicação atualmente no ar."),
    )
    titulo_seo = models.CharField(
        _("Título SEO"),
        max_length=160,
        blank=True,
        help_text=_(
            "Título para mecanismos de busca e redes sociais (deixe vazio para usar o nome do site)."
        ),
    )
    descricao_seo = models.CharField(
        _("Descrição SEO"),
        max_length=255,
        blank=True,
        help_text=_("Meta description para mecanismos de busca e prévia no WhatsApp."),
    )
    imagem_compartilhamento = models.ForeignKey(
        "MidiaSite",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projetos_imagem_og",
        verbose_name=_("Imagem de Compartilhamento (OG)"),
        help_text=_("Imagem exibida em links compartilhados no WhatsApp, Facebook, etc."),
    )
    indexavel = models.BooleanField(
        _("Indexável por Buscadores"),
        default=True,
        help_text=_(
            "Permite indexação pelo Google e outros buscadores quando o site estiver publicado."
        ),
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

    def obter_endereco_principal(self):
        """Retorna o EnderecoSite marcado como principal, se houver."""
        return self.enderecos.filter(principal=True).first()

    def obter_url_publica(self, request=None, caminho: str = "") -> str:
        """Retorna a URL pública canônica do BioSite baseada no endereço principal ou fallback /b/<slug>/."""
        from .servicos_dominios import obter_url_publica_projeto

        return obter_url_publica_projeto(self, request=request, caminho=caminho)

    def tem_alteracoes_nao_publicadas(self) -> bool:
        """Verifica se o rascunho atual possui alterações ainda não publicadas."""
        if not self.publicacao_ativa:
            return True
        from .servicos_publicacao import verificar_alteracoes_pendentes

        return verificar_alteracoes_pendentes(self)

    def esta_publicado(self) -> bool:
        """Indica se o site possui publicação ativa e status publicado."""
        return self.status == self.Status.PUBLICADO and self.publicacao_ativa is not None

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


class ConfiguracaoVisualProjeto(ModeloBase):
    """
    Configuração visual global do BioSite (Design System).

    Define os tokens de cores, tipografia, bordas, sombras e layout para
    garantir coerência visual em todas as páginas e componentes do projeto.
    """

    FONTE_CHOICES = [
        ("Inter, sans-serif", "Inter (Moderna / Clean)"),
        ("Roboto, sans-serif", "Roboto (Equilibrada)"),
        ("Poppins, sans-serif", "Poppins (Geométrica / Tech)"),
        ("Montserrat, sans-serif", "Montserrat (Marcante)"),
        ("Playfair Display, serif", "Playfair Display (Elegante / Editorial)"),
        ("Plus Jakarta Sans, sans-serif", "Plus Jakarta Sans (Moderna / Premium)"),
        ("-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", "Sistema (Nativa)"),
    ]

    projeto = models.OneToOneField(
        ProjetoSite,
        on_delete=models.CASCADE,
        related_name="configuracao_visual",
        verbose_name=_("Projeto"),
    )

    # Paleta de Cores do Projeto
    cor_primaria = models.CharField(
        _("Cor Primária"),
        max_length=20,
        default="#2563eb",
        validators=[validar_cor_hex],
        help_text=_("Cor de destaque para botões principais e elementos ativos."),
    )
    cor_secundaria = models.CharField(
        _("Cor Secundária"),
        max_length=20,
        default="#38bdf8",
        validators=[validar_cor_hex],
        help_text=_("Cor de apoio para detalhes, tags e acentos."),
    )
    cor_fundo = models.CharField(
        _("Cor de Fundo"),
        max_length=20,
        default="#ffffff",
        validators=[validar_cor_hex],
        help_text=_("Cor de fundo da página do BioSite."),
    )
    cor_superficie = models.CharField(
        _("Cor de Superfície"),
        max_length=20,
        default="#f8fafc",
        validators=[validar_cor_hex],
        help_text=_("Cor de fundo para cards, containers e caixas."),
    )
    cor_texto = models.CharField(
        _("Cor do Texto"),
        max_length=20,
        default="#0f172a",
        validators=[validar_cor_hex],
        help_text=_("Cor principal para títulos e textos corridos."),
    )
    cor_texto_secundario = models.CharField(
        _("Cor do Texto Secundário"),
        max_length=20,
        default="#64748b",
        validators=[validar_cor_hex],
        help_text=_("Cor para subtítulos, legendas e metadados."),
    )

    # Tipografia Global
    fonte_principal = models.CharField(
        _("Fonte Principal"),
        max_length=100,
        choices=FONTE_CHOICES,
        default="Inter, sans-serif",
    )
    fonte_titulos = models.CharField(
        _("Fonte de Títulos"),
        max_length=100,
        choices=FONTE_CHOICES,
        default="Inter, sans-serif",
    )

    # Presets de Forma e Elevação
    radius_padrao = models.CharField(
        _("Raio de Borda Padrão"),
        max_length=20,
        default="12px",
        help_text=_("Ex: 0px, 8px, 12px, 20px, 9999px (pill)."),
    )
    sombra_padrao = models.CharField(
        _("Sombra Padrão"),
        max_length=20,
        default="suave",
        help_text=_("nenhuma, suave, media, forte, glow."),
    )
    largura_maxima_mobile = models.PositiveIntegerField(
        _("Largura Máxima Mobile"),
        default=390,
        help_text=_("Largura de referência mobile (320px a 430px)."),
    )

    # Configurações extras extensíveis
    configuracoes_extras = models.JSONField(
        _("Configurações Extras"),
        default=dict,
        blank=True,
    )

    class Meta:
        verbose_name = _("configuração visual do projeto")
        verbose_name_plural = _("configurações visuais dos projetos")

    def __str__(self) -> str:
        return f"Design System: {self.projeto.nome}"

    def obter_tokens_css(self) -> dict[str, str]:
        """Gera dicionário de variáveis CSS prontas para injeção no canvas e preview."""
        mapeamento_sombras = {
            "nenhuma": "none",
            "suave": "0 2px 8px -2px rgba(0, 0, 0, 0.08), 0 1px 4px -1px rgba(0, 0, 0, 0.04)",
            "media": "0 6px 16px -4px rgba(0, 0, 0, 0.12), 0 2px 6px -1px rgba(0, 0, 0, 0.06)",
            "forte": "0 12px 28px -6px rgba(0, 0, 0, 0.2), 0 4px 12px -2px rgba(0, 0, 0, 0.1)",
            "glow": f"0 0 24px {self.cor_primaria}40",
        }
        sombra_css = mapeamento_sombras.get(self.sombra_padrao, mapeamento_sombras["suave"])

        return {
            "--cor-primaria": self.cor_primaria,
            "--cor-secundaria": self.cor_secundaria,
            "--cor-fundo": self.cor_fundo,
            "--cor-superficie": self.cor_superficie,
            "--cor-texto": self.cor_texto,
            "--cor-texto-secundario": self.cor_texto_secundario,
            "--fonte-principal": self.fonte_principal,
            "--fonte-titulos": self.fonte_titulos,
            "--radius-padrao": self.radius_padrao,
            "--sombra-padrao": sombra_css,
            "--largura-maxima-mobile": f"{self.largura_maxima_mobile}px",
        }

    def gerar_bloco_css(self) -> str:
        """Retorna as CSS custom properties prontas para uso em tags <style>."""
        tokens = self.obter_tokens_css()
        linhas = [f"    {chave}: {valor};" for chave, valor in tokens.items()]
        return ":root, .biosite-canvas-root {\n" + "\n".join(linhas) + "\n}"


def garantir_configuracao_visual(projeto: ProjetoSite) -> ConfiguracaoVisualProjeto:
    """Garante de forma idempotente que o projeto possua uma ConfiguracaoVisualProjeto."""
    config, _ = ConfiguracaoVisualProjeto.objects.get_or_create(projeto=projeto)
    return config


class MidiaSite(ModeloBase):
    """
    Armazenamento e metadados de mídias enviadas para o BioSite.

    Validadas contra executáveis e arquivos maliciosos, com sanitização EXIF
    e otimização automática para telas de smartphone.
    """

    class Tipo(models.TextChoices):
        IMAGEM = "IMAGEM", _("Imagem")
        AVATAR = "AVATAR", _("Foto de Perfil / Avatar")
        ICONE = "ICONE", _("Ícone")
        LOGO = "LOGO", _("Logotipo")

    projeto = models.ForeignKey(
        ProjetoSite,
        on_delete=models.CASCADE,
        related_name="midias",
        verbose_name=_("Projeto"),
    )
    arquivo = models.ImageField(
        _("Arquivo"),
        upload_to="sites/midias/%Y/%m/",
    )
    nome_original = models.CharField(
        _("Nome Original"),
        max_length=255,
    )
    mime_type = models.CharField(
        _("Tipo MIME"),
        max_length=100,
        default="image/jpeg",
    )
    tamanho_bytes = models.PositiveIntegerField(
        _("Tamanho (bytes)"),
        default=0,
    )
    largura = models.PositiveIntegerField(
        _("Largura (px)"),
        default=0,
    )
    altura = models.PositiveIntegerField(
        _("Altura (px)"),
        default=0,
    )
    tipo = models.CharField(
        _("Tipo de Mídia"),
        max_length=20,
        choices=Tipo.choices,
        default=Tipo.IMAGEM,
    )

    class Meta:
        verbose_name = _("mídia do site")
        verbose_name_plural = _("mídias do site")
        ordering = ["-criado_em"]

    def __str__(self) -> str:
        return f"{self.nome_original} ({self.projeto.nome})"

    @property
    def url(self) -> str:
        if self.arquivo:
            return self.arquivo.url
        return ""

    def delete(self, *args, **kwargs):
        if hasattr(self, "publicacoes_que_utilizam") and self.publicacoes_que_utilizam.exists():
            raise ValidationError(
                _(
                    "Esta mídia não pode ser excluída pois está vinculada a versões publicadas do site."
                )
            )
        return super().delete(*args, **kwargs)


class TemplateSite(ModeloBase):
    """
    Modelo de blueprint estrutural reutilizável para criação ágil de BioSites.

    Armazena um snapshot estrutural validado (configuração visual, páginas,
    seções, containers e elementos) sem manter acoplamento com projetos instanciados.
    """

    class Categoria(models.TextChoices):
        BIOSITE = "biosite", _("BioSite")
        CARTAO_DIGITAL = "cartao_digital", _("Cartão Digital NFC")
        PROFISSIONAL = "profissional", _("Profissional Liberal")
        EMPRESA = "empresa", _("Empresa / Negócio")
        COMERCIO = "comercio", _("Comércio / Varejo")
        RESTAURANTE = "restaurante", _("Restaurante / Gastronomia")
        PORTFOLIO = "portfolio", _("Portfólio / Criativo")
        LANDING_PAGE = "landing_page", _("Landing Page")
        OUTRO = "outro", _("Outro")

    class Origem(models.TextChoices):
        SISTEMA = "sistema", _("Sistema")
        USUARIO = "usuario", _("Meus Modelos")

    nome = models.CharField(
        _("Nome do Modelo"),
        max_length=120,
    )
    slug = models.SlugField(
        _("Slug"),
        max_length=120,
        unique=True,
        db_index=True,
    )
    descricao = models.TextField(
        _("Descrição"),
        blank=True,
    )
    categoria = models.CharField(
        _("Categoria"),
        max_length=30,
        choices=Categoria.choices,
        default=Categoria.BIOSITE,
        db_index=True,
    )
    origem = models.CharField(
        _("Origem"),
        max_length=20,
        choices=Origem.choices,
        default=Origem.SISTEMA,
        db_index=True,
    )
    versao = models.PositiveIntegerField(
        _("Versão"),
        default=1,
    )
    thumbnail = models.ImageField(
        _("Miniatura"),
        upload_to="templates/thumbnails/",
        null=True,
        blank=True,
    )
    ativo = models.BooleanField(
        _("Ativo"),
        default=True,
    )
    ordem = models.PositiveIntegerField(
        _("Ordem"),
        default=10,
    )
    estrutura_snapshot = models.JSONField(
        _("Snapshot Estrutural"),
        default=dict,
        blank=True,
        help_text=_("Snapshot validado contendo configuracao_visual e árvore de páginas."),
    )

    class Meta:
        verbose_name = _("modelo de site")
        verbose_name_plural = _("modelos de sites")
        ordering = ["ordem", "nome"]

    def __str__(self) -> str:
        return f"{self.nome} ({self.get_origem_display()})"


class BlocoReutilizavel(ModeloBase):
    """
    Composição reutilizável de uma seção completa para inserção no editor visual.

    Armazena um snapshot de SecaoSite (containers e elementos) que herda
    automaticamente os tokens de design do projeto de destino ao ser inserido.
    """

    class Categoria(models.TextChoices):
        HERO = "hero", _("Hero / Destaque")
        PERFIL = "perfil", _("Perfil / Bio")
        LINKS = "links", _("Links / Botões")
        SERVICOS = "servicos", _("Serviços / Produtos")
        GALERIA = "galeria", _("Galeria / Fotos")
        CONTATO = "contato", _("Contato / Conexão")
        CTA = "cta", _("Chamada para Ação")
        LOCALIZACAO = "localizacao", _("Localização / Mapa")
        RODAPE = "rodape", _("Rodapé")
        OUTRO = "outro", _("Outro")

    class Origem(models.TextChoices):
        SISTEMA = "sistema", _("Sistema")
        USUARIO = "usuario", _("Meus Blocos")

    nome = models.CharField(
        _("Nome do Bloco"),
        max_length=120,
    )
    slug = models.SlugField(
        _("Slug"),
        max_length=120,
        unique=True,
        db_index=True,
    )
    descricao = models.TextField(
        _("Descrição"),
        blank=True,
    )
    categoria = models.CharField(
        _("Categoria"),
        max_length=30,
        choices=Categoria.choices,
        default=Categoria.HERO,
        db_index=True,
    )
    origem = models.CharField(
        _("Origem"),
        max_length=20,
        choices=Origem.choices,
        default=Origem.SISTEMA,
        db_index=True,
    )
    versao = models.PositiveIntegerField(
        _("Versão"),
        default=1,
    )
    thumbnail = models.ImageField(
        _("Miniatura"),
        upload_to="blocos/thumbnails/",
        null=True,
        blank=True,
    )
    ativo = models.BooleanField(
        _("Ativo"),
        default=True,
    )
    ordem = models.PositiveIntegerField(
        _("Ordem"),
        default=10,
    )
    estrutura_snapshot = models.JSONField(
        _("Snapshot Estrutural"),
        default=dict,
        blank=True,
        help_text=_(
            "Snapshot validado contendo a estrutura de uma seção com containers e elementos."
        ),
    )

    class Meta:
        verbose_name = _("bloco reutilizável")
        verbose_name_plural = _("blocos reutilizáveis")
        ordering = ["ordem", "nome"]

    def __str__(self) -> str:
        return f"{self.nome} ({self.get_categoria_display()})"


class PublicacaoSite(ModeloBase):
    """
    Representa uma versão publicada imutável de um ProjetoSite (Prompt 8).

    REGRAS ARQUITETURAIS:
    1. Imutabilidade absoluta: o snapshot nunca é alterado após a criação da versão.
    2. Sequenciamento versionado: v1, v2, v3... único por projeto (UniqueConstraint).
    3. Conteúdo público estável: o público consome exclusivamente a publicação com ativa=True.
    4. Rollback cronológico: restaurar uma versão gera uma nova versão com o snapshot alvo.
    5. Retenção de mídia: mídias referenciadas ficam protegidas contra exclusão acidental.
    """

    projeto = models.ForeignKey(
        ProjetoSite,
        on_delete=models.CASCADE,
        related_name="publicacoes",
        verbose_name=_("Projeto"),
    )
    numero_versao = models.PositiveIntegerField(
        _("Número da Versão"),
        db_index=True,
    )
    snapshot = models.JSONField(
        _("Snapshot Publicado"),
        help_text=_("Snapshot estrutural canônico, validado e imutável do site publicado."),
    )
    schema_version = models.PositiveIntegerField(
        _("Versão do Schema"),
        default=1,
    )
    hash_conteudo = models.CharField(
        _("Hash SHA-256 do Conteúdo"),
        max_length=64,
        db_index=True,
        help_text=_("Hash determinístico da representação canônica do conteúdo publicado."),
    )
    publicado_em = models.DateTimeField(
        _("Publicado em"),
        default=timezone.now,
        db_index=True,
    )
    publicado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="publicacoes_realizadas",
        verbose_name=_("Publicado por"),
    )
    ativa = models.BooleanField(
        _("Publicação Ativa"),
        default=False,
        db_index=True,
    )
    metadata = models.JSONField(
        _("Metadados Técnicos"),
        default=dict,
        blank=True,
    )
    midias_referenciadas = models.ManyToManyField(
        MidiaSite,
        blank=True,
        related_name="publicacoes_que_utilizam",
        verbose_name=_("Mídias Referenciadas"),
    )

    class Meta:
        verbose_name = _("publicação de site")
        verbose_name_plural = _("publicações de sites")
        ordering = ["-numero_versao"]
        constraints = [
            models.UniqueConstraint(
                fields=["projeto", "numero_versao"],
                name="unique_projeto_numero_versao",
            )
        ]

    def __str__(self) -> str:
        status_txt = " [ATIVA]" if self.ativa else ""
        return f"{self.projeto.nome} — v{self.numero_versao}{status_txt}"


class EnderecoSite(ModeloBase):
    """
    Representa um endereço de acesso web (subdomínio da plataforma ou domínio personalizado)
    vinculado a um ProjetoSite.

    REGRA FUNDAMENTAL:
    O domínio identifica o ProjetoSite; o ProjetoSite identifica a PublicacaoSite atual no ar.
    Apenas um endereço por projeto pode ter principal=True.
    """

    class Tipo(models.TextChoices):
        SUBDOMINIO_PLATAFORMA = "subdominio_plataforma", _("Subdomínio da Plataforma")
        DOMINIO_PERSONALIZADO = "dominio_personalizado", _("Domínio Personalizado")

    class Status(models.TextChoices):
        PENDENTE = "pendente", _("Pendente de Verificação")
        VERIFICADO = "verificado", _("Verificado / Pronto")
        ATIVO = "ativo", _("Ativo no Ar")
        ERRO = "erro", _("Falha de Configuração DNS")
        REMOVIDO = "removido", _("Removido")

    projeto = models.ForeignKey(
        ProjetoSite,
        on_delete=models.CASCADE,
        related_name="enderecos",
        verbose_name=_("Projeto"),
    )
    host = models.CharField(
        _("Host / Domínio Completo"),
        max_length=255,
        unique=True,
        db_index=True,
        help_text=_(
            "Hostname normalizado e sem protocolo (ex: joao.seudominio.com ou www.joao.com.br)."
        ),
    )
    subdominio = models.CharField(
        _("Subdomínio"),
        max_length=63,
        blank=True,
        null=True,
        db_index=True,
        help_text=_("Identificador do subdomínio da plataforma (ex: 'joao')."),
    )
    tipo = models.CharField(
        _("Tipo de Endereço"),
        max_length=30,
        choices=Tipo.choices,
        default=Tipo.SUBDOMINIO_PLATAFORMA,
        db_index=True,
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDENTE,
        db_index=True,
    )
    principal = models.BooleanField(
        _("Endereço Principal"),
        default=False,
        db_index=True,
        help_text=_("Endereço oficial para SEO canonical, compartilhamento, links e NFC."),
    )
    token_verificacao = models.CharField(
        _("Token de Verificação DNS"),
        max_length=64,
        blank=True,
        help_text=_("Token criptográfico para verificação de propriedade via registro TXT."),
    )
    verificado_em = models.DateTimeField(
        _("Verificado em"),
        null=True,
        blank=True,
    )
    ultima_checagem_em = models.DateTimeField(
        _("Última Checagem em"),
        null=True,
        blank=True,
    )
    erro_mensagem = models.TextField(
        _("Mensagem de Erro"),
        blank=True,
    )
    metadata = models.JSONField(
        _("Metadados"),
        default=dict,
        blank=True,
    )

    class Meta:
        verbose_name = _("endereço do site")
        verbose_name_plural = _("endereços dos sites")
        ordering = ["-principal", "tipo", "host"]
        constraints = [
            models.UniqueConstraint(
                fields=["projeto"],
                condition=models.Q(principal=True),
                name="unique_endereco_principal_por_projeto",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.host} ({'Principal' if self.principal else 'Alias'})"

    def clean(self):
        super().clean()
        from .validadores_dominios import normalizar_host, validar_formato_host

        self.host = normalizar_host(self.host)
        validar_formato_host(self.host)

    def save(self, *args, **kwargs):
        from .validadores_dominios import normalizar_host

        if self.host:
            self.host = normalizar_host(self.host)
        super().save(*args, **kwargs)


class HistoricoEnderecoSite(ModeloBase):
    """
    Armazena o histórico de endereços que pertenceram a projetos, permitindo redirecionamentos 301
    legados e prevenindo o sequestro imediato (domain takeover) de subdomínios desvinculados.
    """

    host = models.CharField(
        _("Host"),
        max_length=255,
        db_index=True,
    )
    projeto = models.ForeignKey(
        ProjetoSite,
        on_delete=models.CASCADE,
        related_name="historico_enderecos",
        verbose_name=_("Projeto"),
    )
    motivo = models.CharField(
        _("Motivo"),
        max_length=50,
        default="alteracao",
        help_text=_("Ex: alteracao_subdominio, remocao_dominio, arquivamento."),
    )
    reservado_ate = models.DateTimeField(
        _("Reservado Até"),
        null=True,
        blank=True,
        help_text=_(
            "Período de quarentena durante o qual o endereço não pode ser reivindicado por outro cliente."
        ),
    )

    class Meta:
        verbose_name = _("histórico de endereço")
        verbose_name_plural = _("histórico de endereços")
        ordering = ["-criado_em"]

    def __str__(self) -> str:
        return f"{self.host} -> {self.projeto.nome} ({self.motivo})"
