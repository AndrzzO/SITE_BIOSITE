"""Configuração do modelo customizado no Django Admin."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import UsuarioAdministrativo


@admin.register(UsuarioAdministrativo)
class UsuarioAdministrativoAdmin(UserAdmin):
    """Administração do modelo de usuário customizado."""

    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_superuser",
        "is_active",
        "date_joined",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("username", "first_name", "last_name", "email")
    ordering = ("-date_joined",)

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Informações Pessoais"), {"fields": ("first_name", "last_name", "email")}),
        (
            _("Permissões"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Datas Importantes"), {"fields": ("last_login", "date_joined")}),
    )
