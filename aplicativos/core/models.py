"""Modelos base compartilhados para o sistema BioSite NFC."""

import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class ModeloBase(models.Model):
    """
    Modelo base abstrato para as entidades de negócio da plataforma.

    Fornece:
    - id: Chave primária relacional sequencial interna (alta performance em índices e FKs).
    - uuid: Identificador universal público único e imutável (seguro para URLs públicas, NFC e QR Codes).
    - criado_em: Data e hora de criação do registro.
    - atualizado_em: Data e hora da última modificação do registro.
    """

    id = models.BigAutoField(
        primary_key=True,
        verbose_name=_("ID interno"),
    )
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
        verbose_name=_("UUID público"),
        help_text=_("Identificador único global exposto em URLs e integrações externas."),
    )
    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Criado em"),
    )
    atualizado_em = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Atualizado em"),
    )

    class Meta:
        abstract = True
        ordering = ["-criado_em"]
