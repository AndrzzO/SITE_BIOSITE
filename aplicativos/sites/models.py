"""Modelos para gerenciamento de projetos de sites e BioSites."""

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from aplicativos.core.models import ModeloBase


class ProjetoSite(ModeloBase):
    """
    Representa a identidade administrativa de um projeto de site ou BioSite.

    REGRAS ARQUITETURAIS:
    1. Vinculado obrigatoriamente a um Cliente comercial via PROTECT (impede deleção cascateada acidental).
    2. Possui slug único validado contra palavras reservadas.
    3. Status inicial estrito como RASCUNHO.
    4. Base para o futuro motor visual (Prompt 4) sem sobrecarregar este modelo com estilos ou blocos.
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
