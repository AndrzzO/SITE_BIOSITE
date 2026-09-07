"""Modelos para o gerenciamento de clientes comerciais."""

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from aplicativos.core.models import ModeloBase


class Cliente(ModeloBase):
    """
    Representa o cliente comercial contratante dos BioSites e páginas digitais.

    REGRAS ARQUITETURAIS:
    1. O cliente comercial NÃO é usuário do sistema (não possui login nem senha).
    2. Apenas o campo 'nome' é estritamente obrigatório no cadastro inicial.
    3. Proteção contra exclusão acidental: clientes com sites vinculados não devem ser deletados via CASCADE.
    """

    class Status(models.TextChoices):
        ATIVO = "ativo", _("Ativo")
        ARQUIVADO = "arquivado", _("Arquivado")

    nome = models.CharField(
        _("Nome do Cliente"),
        max_length=150,
        help_text=_("Nome da pessoa física ou razão social."),
    )
    nome_fantasia = models.CharField(
        _("Nome Fantasia / Marca"),
        max_length=150,
        blank=True,
        help_text=_("Nome comercial da marca ou estabelecimento."),
    )
    email = models.EmailField(
        _("E-mail"),
        blank=True,
        help_text=_("E-mail de contato principal."),
    )
    telefone = models.CharField(
        _("Telefone"),
        max_length=30,
        blank=True,
        help_text=_("Telefone fixo ou móvel."),
    )
    whatsapp = models.CharField(
        _("WhatsApp"),
        max_length=30,
        blank=True,
        help_text=_("Número de WhatsApp para contato rápido ou integração futura."),
    )
    documento = models.CharField(
        _("CPF / CNPJ"),
        max_length=30,
        blank=True,
        help_text=_("Documento fiscal (opcional)."),
    )
    observacoes = models.TextField(
        _("Observações Internas"),
        blank=True,
        help_text=_("Anotações administrativas sobre o cliente ou contrato."),
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=Status.choices,
        default=Status.ATIVO,
        db_index=True,
    )
    arquivado_em = models.DateTimeField(
        _("Arquivado em"),
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("cliente")
        verbose_name_plural = _("clientes")
        ordering = ["nome"]

    def __str__(self) -> str:
        if self.nome_fantasia:
            return f"{self.nome} ({self.nome_fantasia})"
        return self.nome

    def arquivar(self) -> None:
        """Marca o cliente como arquivado com timestamp de auditoria."""
        self.status = self.Status.ARQUIVADO
        self.arquivado_em = timezone.now()
        self.save(update_fields=["status", "arquivado_em", "atualizado_em"])

    def restaurar(self) -> None:
        """Restaura o cliente para o status ativo."""
        self.status = self.Status.ATIVO
        self.arquivado_em = None
        self.save(update_fields=["status", "arquivado_em", "atualizado_em"])
