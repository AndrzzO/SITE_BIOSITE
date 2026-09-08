"""Comando de gerenciamento para auditar e validar todos os templates e blocos."""

from typing import Any

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from aplicativos.sites.models import BlocoReutilizavel, TemplateSite
from aplicativos.sites.validadores_templates import (
    validar_snapshot_bloco,
    validar_snapshot_template,
)


class Command(BaseCommand):
    help = "Audita e valida a integridade de todos os snapshots de templates e blocos cadastrados."

    def handle(self, *args: Any, **options: Any) -> None:
        self.stdout.write(self.style.NOTICE("Iniciando auditoria de templates e blocos..."))

        erros = 0

        templates = TemplateSite.objects.all()
        self.stdout.write(f"Validando {templates.count()} templates...")
        for t in templates:
            try:
                validar_snapshot_template(t.estrutura_snapshot)
                self.stdout.write(f"  [OK] Template: {t.nome} ({t.slug})")
            except ValidationError as e:
                erros += 1
                self.stdout.write(self.style.ERROR(f"  [FALHA] Template {t.nome}: {e}"))

        blocos = BlocoReutilizavel.objects.all()
        self.stdout.write(f"Validando {blocos.count()} blocos...")
        for b in blocos:
            try:
                validar_snapshot_bloco(b.estrutura_snapshot)
                self.stdout.write(f"  [OK] Bloco: {b.nome} ({b.slug})")
            except ValidationError as e:
                erros += 1
                self.stdout.write(self.style.ERROR(f"  [FALHA] Bloco {b.nome}: {e}"))

        if erros > 0:
            self.stdout.write(
                self.style.ERROR(f"Auditoria concluída com {erros} erros encontrados.")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "Auditoria concluída! Todos os modelos e blocos estão 100% válidos."
                )
            )
