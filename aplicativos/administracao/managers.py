"""Managers customizados para o aplicativo de administração."""

from django.contrib.auth.models import UserManager
from django.utils.translation import gettext_lazy as _


class UsuarioAdministrativoManager(UserManager):
    """
    Manager customizado para o modelo UsuarioAdministrativo.

    Garante validações de e-mail e configurações de permissões de superusuário.
    """

    def create_user(
        self, username: str, email: str | None = None, password: str | None = None, **extra_fields
    ):
        """Cria e salva um usuário administrativo comum."""
        if not username:
            raise ValueError(_("O nome de usuário é obrigatório."))
        if not email:
            raise ValueError(_("O endereço de e-mail é obrigatório para usuários administrativos."))

        email = self.normalize_email(email)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self, username: str, email: str | None = None, password: str | None = None, **extra_fields
    ):
        """Cria e salva um superusuário administrativo."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("O superusuário deve conter is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("O superusuário deve conter is_superuser=True."))

        return self.create_user(username, email, password, **extra_fields)
