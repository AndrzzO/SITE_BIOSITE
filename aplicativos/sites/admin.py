"""Registro administrativo do modelo ProjetoSite."""

from django.contrib import admin

from .models import HistoricoVinculoTag, LinkInteligente, ProjetoSite


@admin.register(ProjetoSite)
class ProjetoSiteAdmin(admin.ModelAdmin):
    list_display = ("nome", "cliente", "tipo", "status", "slug", "atualizado_em")
    list_filter = ("tipo", "status", "criado_em")
    search_fields = ("nome", "slug", "cliente__nome", "cliente__nome_fantasia")
    prepopulated_fields = {"slug": ("nome",)}
    readonly_fields = ("uuid", "criado_em", "atualizado_em", "arquivado_em")


@admin.register(LinkInteligente)
class LinkInteligenteAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo", "status", "token", "projeto", "criado_em")
    list_filter = ("tipo", "status", "tipo_midia_fisica", "criado_em")
    search_fields = ("nome", "token", "projeto__nome", "projeto__cliente__nome")
    readonly_fields = ("uuid", "token", "criado_em", "atualizado_em", "ativado_em", "desativado_em")


@admin.register(HistoricoVinculoTag)
class HistoricoVinculoTagAdmin(admin.ModelAdmin):
    list_display = ("link", "projeto_anterior", "projeto_novo", "alterado_por", "criado_em")
    list_filter = ("criado_em",)
    search_fields = ("link__nome", "link__token", "projeto_anterior__nome", "projeto_novo__nome")
    readonly_fields = ("uuid", "criado_em", "atualizado_em")
