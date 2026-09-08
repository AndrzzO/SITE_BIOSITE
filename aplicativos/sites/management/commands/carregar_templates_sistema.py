"""Comando de gerenciamento idempotente para carregar templates e blocos do sistema."""

from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from aplicativos.sites.dados_templates_sistema import BLOCOS_SISTEMA, TEMPLATES_SISTEMA
from aplicativos.sites.models import BlocoReutilizavel, TemplateSite
from aplicativos.sites.validadores_templates import (
    validar_snapshot_bloco,
    validar_snapshot_template,
)


class Command(BaseCommand):
    help = "Carrega ou atualiza de forma idempotente os 8 templates e 15 blocos padrão do sistema."

    def handle(self, *args: Any, **options: Any) -> None:
        self.stdout.write(self.style.NOTICE("Carregando templates e blocos do sistema..."))

        templates_criados = 0
        templates_atualizados = 0
        blocos_criados = 0
        blocos_atualizados = 0

        with transaction.atomic():
            # 1. Templates
            for t_dados in TEMPLATES_SISTEMA:
                snapshot = t_dados["estrutura_snapshot"]
                validar_snapshot_template(snapshot)

                template, criado = TemplateSite.objects.update_or_create(
                    slug=t_dados["slug"],
                    origem=TemplateSite.Origem.SISTEMA,
                    defaults={
                        "nome": t_dados["nome"],
                        "categoria": t_dados["categoria"],
                        "descricao": t_dados["descricao"],
                        "ordem": t_dados["ordem"],
                        "versao": 1,
                        "ativo": True,
                        "estrutura_snapshot": snapshot,
                    },
                )
                if criado:
                    templates_criados += 1
                else:
                    templates_atualizados += 1

            # 2. Blocos
            for b_dados in BLOCOS_SISTEMA:
                snapshot = b_dados["estrutura_snapshot"]
                validar_snapshot_bloco(snapshot)

                bloco, criado = BlocoReutilizavel.objects.update_or_create(
                    slug=b_dados["slug"],
                    origem=BlocoReutilizavel.Origem.SISTEMA,
                    defaults={
                        "nome": b_dados["nome"],
                        "categoria": b_dados["categoria"],
                        "descricao": b_dados["descricao"],
                        "ordem": b_dados["ordem"],
                        "versao": 1,
                        "ativo": True,
                        "estrutura_snapshot": snapshot,
                    },
                )
                if criado:
                    blocos_criados += 1
                else:
                    blocos_atualizados += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Sucesso! Templates: {templates_criados} criados, {templates_atualizados} atualizados. "
                f"Blocos: {blocos_criados} criados, {blocos_atualizados} atualizados."
            )
        )
