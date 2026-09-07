"""Registro administrativo do modelo Cliente."""

from django.contrib import admin

from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "nome_fantasia", "email", "telefone", "status", "criado_em")
    list_filter = ("status", "criado_em")
    search_fields = ("nome", "nome_fantasia", "email", "telefone", "documento")
    readonly_fields = ("uuid", "criado_em", "atualizado_em", "arquivado_em")
