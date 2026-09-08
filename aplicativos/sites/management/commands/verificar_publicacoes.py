"""
Comando de gerenciamento para auditoria e verificação de integridade das publicações de BioSites.

Uso:
    python manage.py verificar_publicacoes
"""

from django.core.management.base import BaseCommand

from aplicativos.sites.models import ProjetoSite, PublicacaoSite
from aplicativos.sites.servicos_publicacao import (
    SCHEMA_VERSION_PUBLICACAO,
    calcular_hash_conteudo,
)


class Command(BaseCommand):
    help = "Verifica integridade criptográfica, esquemas e consistência das publicações ativas e históricas."

    def handle(self, *args, **options):
        self.stdout.write("Iniciando auditoria de publicações de BioSites...")

        publicacoes = PublicacaoSite.objects.all().select_related("projeto")
        total = publicacoes.count()
        if total == 0:
            self.stdout.write(
                self.style.WARNING("Nenhuma publicação encontrada no banco de dados.")
            )
            return

        self.stdout.write(f"Auditando {total} publicações...")
        erros = 0
        sucessos = 0

        for pub in publicacoes:
            falhas_pub = []

            # 1. Validação de Schema
            if pub.schema_version != SCHEMA_VERSION_PUBLICACAO:
                falhas_pub.append(
                    f"Versão de schema inesperada: {pub.schema_version} (esperado {SCHEMA_VERSION_PUBLICACAO})"
                )

            # 2. Integridade de Hash
            hash_recalculado = calcular_hash_conteudo(pub.snapshot)
            if hash_recalculado != pub.hash_conteudo:
                falhas_pub.append(
                    f"Hash divergente! Gravado: {pub.hash_conteudo[:8]} vs Calculado: {hash_recalculado[:8]}"
                )

            # 3. Validação de Estrutura Mínima no Snapshot
            if not isinstance(pub.snapshot, dict) or not pub.snapshot.get("paginas"):
                falhas_pub.append("Snapshot sem páginas ou estrutura corrompida.")

            # 4. Mídias Referenciadas
            for midia in pub.midias_referenciadas.all():
                if not midia.arquivo or not midia.arquivo.storage.exists(midia.arquivo.name):
                    falhas_pub.append(
                        f"Arquivo de mídia ausente no storage: {midia.nome_original} ({midia.id})"
                    )

            if falhas_pub:
                erros += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"  [ERRO] Projeto '{pub.projeto.nome}' — v{pub.numero_versao} (ID {pub.id}):"
                    )
                )
                for f in falhas_pub:
                    self.stdout.write(self.style.ERROR(f"    - {f}"))
            else:
                sucessos += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  [OK] Projeto '{pub.projeto.nome}' — v{pub.numero_versao} (Hash: {pub.hash_conteudo[:8]})"
                        + (" [ATIVA]" if pub.ativa else "")
                    )
                )

        # 5. Auditoria de Unicidade de Publicação Ativa por Projeto
        for proj in ProjetoSite.objects.all():
            ativas_count = proj.publicacoes.filter(ativa=True).count()
            if ativas_count > 1:
                erros += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"  [CONFLITO] Projeto '{proj.nome}' possui {ativas_count} publicações ativas simultâneas!"
                    )
                )

        self.stdout.write("--------------------------------------------------")
        if erros == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Auditoria concluída com sucesso! Todas as {sucessos} publicações estão íntegras."
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    f"Auditoria finalizada com {erros} inconsistência(s) detectada(s)."
                )
            )
