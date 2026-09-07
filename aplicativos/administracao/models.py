"""Modelos para o aplicativo de administração e autenticação interna."""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from .managers import UsuarioAdministrativoManager


class UsuarioAdministrativo(AbstractUser):
    """
    Modelo de usuário customizado exclusivo para a administração interna da plataforma.

    PRINCÍPIOS ARQUITETURAIS:
    1. Clientes comerciais dos BioSites NÃO são usuários deste sistema (não possuem login aqui).
    2. Visitantes de BioSites NÃO possuem conta.
    3. Este modelo gerencia exclusivamente a equipe interna (proprietário, administradores, editores).
    4. Utiliza a infraestrutura nativa do Django (is_staff, is_active, grupos e permissões)
       para permitir expansão futura de perfis (Administrador, Editor, Atendimento, Financeiro).
    """

    email = models.EmailField(
        _("endereço de e-mail"),
        unique=True,
        error_messages={
            "unique": _("Já existe um usuário cadastrado com este e-mail."),
        },
    )

    objects = UsuarioAdministrativoManager()

    class Meta:
        verbose_name = _("usuário administrativo")
        verbose_name_plural = _("usuários administrativos")
        ordering = ["-date_joined"]

    def __str__(self) -> str:
        nome = self.get_full_name().strip()
        return nome if nome else self.username
