"""Registro administrativo do modelo ProjetoSite."""

from django.contrib import admin

from .models import ProjetoSite


@admin.register(ProjetoSite)
class ProjetoSiteAdmin(admin.ModelAdmin):
    list_display = ("nome", "cliente", "tipo", "status", "slug", "atualizado_em")
    list_filter = ("tipo", "status", "criado_em")
    search_fields = ("nome", "slug", "cliente__nome", "cliente__nome_fantasia")
    prepopulated_fields = {"slug": ("nome",)}
    readonly_fields = ("uuid", "criado_em", "atualizado_em", "arquivado_em")
