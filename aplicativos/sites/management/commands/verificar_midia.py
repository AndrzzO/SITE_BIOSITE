"""
Comando de auditoria de arquivos de mídia (Prompt 12).

Audita a integridade do armazenamento de mídia:
1. Registros em MidiaSite cujo arquivo físico não existe no disco (mídia sem arquivo).
2. Arquivos físicos no storage que não possuem registro em MidiaSite (arquivo sem registro).
3. Mídias registradas mas não referenciadas em nenhum snapshot de publicação ou rascunho de projeto.
"""

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from aplicativos.sites.models import MidiaSite, ProjetoSite, PublicacaoSite


class Command(BaseCommand):
    help = "Audita a integridade do sistema de mídia, arquivos órfãos e referências ativas."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Iniciando auditoria de arquivos de mídia..."))

        total_midias = MidiaSite.objects.count()
        self.stdout.write(f"Total de registros em MidiaSite: {total_midias}")

        erros_encontrados = 0
        avisos_encontrados = 0

        # 1. Registros de MidiaSite sem arquivo no disco
        midias_sem_arquivo = []
        for midia in MidiaSite.objects.iterator():
            if not midia.arquivo:
                midias_sem_arquivo.append((midia.id, str(midia.uuid), "Campo arquivo vazio"))
                continue
            try:
                if not midia.arquivo.storage.exists(midia.arquivo.name):
                    midias_sem_arquivo.append((midia.id, str(midia.uuid), midia.arquivo.name))
            except Exception as err:
                midias_sem_arquivo.append(
                    (midia.id, str(midia.uuid), f"Erro ao acessar storage: {err}")
                )

        if midias_sem_arquivo:
            self.stdout.write(
                self.style.ERROR(
                    f"  [ERRO] {len(midias_sem_arquivo)} registro(s) de mídia sem arquivo físico correspondente:"
                )
            )
            for m_id, m_uuid, path in midias_sem_arquivo[:10]:
                self.stdout.write(f"    - ID {m_id} (UUID: {m_uuid}): {path}")
            if len(midias_sem_arquivo) > 10:
                self.stdout.write(f"    ... e mais {len(midias_sem_arquivo) - 10} arquivo(s).")
            erros_encontrados += len(midias_sem_arquivo)
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "  [OK] 100% dos registros de mídia possuem arquivo físico no disco."
                )
            )

        # 2. Arquivos físicos no diretório media sem registro no banco
        media_root = Path(settings.MEDIA_ROOT)
        arquivos_fisicos = set()
        if media_root.exists():
            for p in media_root.rglob("*"):
                if p.is_file() and p.name != ".gitkeep":
                    rel_path = str(p.relative_to(media_root)).replace("\\", "/")
                    arquivos_fisicos.add(rel_path)

        arquivos_registrados = set(
            MidiaSite.objects.exclude(arquivo="").values_list("arquivo", flat=True)
        )
        # Normaliza barras para comparação
        arquivos_registrados = {str(a).replace("\\", "/") for a in arquivos_registrados}

        arquivos_nao_registrados = arquivos_fisicos - arquivos_registrados
        if arquivos_nao_registrados:
            self.stdout.write(
                self.style.WARNING(
                    f"  [AVISO] {len(arquivos_nao_registrados)} arquivo(s) físico(s) no storage sem registro em MidiaSite:"
                )
            )
            for f in sorted(arquivos_nao_registrados)[:10]:
                self.stdout.write(f"    - {f}")
            if len(arquivos_nao_registrados) > 10:
                self.stdout.write(
                    f"    ... e mais {len(arquivos_nao_registrados) - 10} arquivo(s)."
                )
            avisos_encontrados += len(arquivos_nao_registrados)
        else:
            self.stdout.write(
                self.style.SUCCESS("  [OK] Nenhum arquivo físico órfão detectado no storage.")
            )

        # 3. Mídias sem nenhuma referência em publicações ativas ou rascunhos de projetos
        todas_urls_usadas = set()

        # Coleta URLs referenciadas em snapshots de publicações
        for pub in PublicacaoSite.objects.values_list("snapshot", flat=True):
            if isinstance(pub, dict):
                snap_str = json.dumps(pub)
                for midia in MidiaSite.objects.iterator():
                    if midia.arquivo and midia.arquivo.name in snap_str:
                        todas_urls_usadas.add(midia.id)

        # Coleta URLs em configurações visuais de projetos
        for cfg in ProjetoSite.objects.values_list("configuracao_visual", flat=True):
            if isinstance(cfg, dict):
                cfg_str = json.dumps(cfg)
                for midia in MidiaSite.objects.iterator():
                    if midia.arquivo and midia.arquivo.name in cfg_str:
                        todas_urls_usadas.add(midia.id)

        midias_nao_referenciadas = (
            MidiaSite.objects.exclude(id__in=todas_urls_usadas).count() if total_midias > 0 else 0
        )
        if midias_nao_referenciadas > 0:
            self.stdout.write(
                self.style.NOTICE(
                    f"  [INFO] {midias_nao_referenciadas} mídia(s) cadastrada(s) sem vínculo em publicações ativas (disponíveis no catálogo do projeto)."
                )
            )

        # Relatório final
        self.stdout.write("")
        if erros_encontrados == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    "Auditoria de mídia concluída com sucesso! Nenhum erro de consistência encontrado."
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    f"Auditoria concluída com {erros_encontrados} erro(s) crítico(s) e {avisos_encontrados} aviso(s)."
                )
            )
