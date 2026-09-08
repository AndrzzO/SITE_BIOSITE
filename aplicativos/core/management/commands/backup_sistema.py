"""
Comando operacional de backup consistente e validação de restauração (Prompt 12).

REGRAS ARQUITETURAIS:
1. SQLite Online Backup: Utiliza a API nativa sqlite3.Connection.backup() para extrair snapshot
   transacionalmente consistente sem corrupção mesmo sob escritas ativas (Prompt item 339).
2. Não colocar backups em diretório público (Prompt item 342).
3. Inclui banco de dados e arquivos de mídia essenciais (Prompt item 341).
4. Suporte a --test-restore: Valida restauração em ambiente isolado sem sobrepor banco real (Prompt items 343-345).
"""

import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Gera backup transacionalmente consistente da plataforma (SQLite + Mídia) com suporte a teste de restauração."

    def add_arguments(self, parser):
        parser.add_argument(
            "--test-restore",
            action="store_true",
            help="Executa uma restauração de teste controlada em diretório temporário para validar a integridade.",
        )
        parser.add_argument(
            "--output-dir",
            type=str,
            default=None,
            help="Diretório de destino do arquivo de backup (padrão: [BASE_DIR]/backups/).",
        )

    def handle(self, *args, **options):
        test_restore = options.get("test_restore", False)
        base_dir = Path(settings.BASE_DIR)
        output_dir = Path(options["output_dir"]) if options["output_dir"] else base_dir / "backups"
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"biosite_backup_{timestamp}.zip"
        backup_zip_path = output_dir / backup_filename

        self.stdout.write(self.style.NOTICE(f"Iniciando procedimento de backup ({timestamp})..."))

        # Cria diretório temporário para consolidação dos artefatos
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            db_backup_file = temp_dir / "database.sqlite3"

            # 1. Backup do Banco de Dados SQLite
            is_sqlite = connection.vendor == "sqlite"
            if is_sqlite:
                self.stdout.write(
                    "  -> Criando snapshot transacional online do SQLite via API backup()..."
                )
                # Assegura conexão aberta
                connection.ensure_connection()
                source_conn = connection.connection
                dest_conn = sqlite3.connect(str(db_backup_file))
                try:
                    # Executa o backup online página por página
                    source_conn.backup(dest_conn)
                    dest_conn.close()
                    self.stdout.write(
                        self.style.SUCCESS(
                            "  [OK] Snapshot do banco SQLite gerado com integridade."
                        )
                    )
                except Exception as err:
                    dest_conn.close()
                    self.stdout.write(
                        self.style.ERROR(f"  [ERRO] Falha ao gerar snapshot do banco: {err}")
                    )
                    return
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"  [AVISO] Banco configurado ({connection.vendor}) não é SQLite. "
                        "Utilize pg_dump para ambientes PostgreSQL."
                    )
                )

            # 2. Compactação em arquivo ZIP seguro
            self.stdout.write(
                f"  -> Empacotando banco e arquivos de mídia em {backup_zip_path.name}..."
            )
            media_root = Path(settings.MEDIA_ROOT)

            with zipfile.ZipFile(backup_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                if db_backup_file.exists():
                    zf.write(db_backup_file, arcname="db.sqlite3")

                if media_root.exists():
                    for item in media_root.rglob("*"):
                        if item.is_file() and item.name != ".gitkeep":
                            arcname = "media/" + str(item.relative_to(media_root)).replace(
                                "\\", "/"
                            )
                            zf.write(item, arcname=arcname)

            tamanho_kb = backup_zip_path.stat().st_size / 1024
            self.stdout.write(
                self.style.SUCCESS(
                    f"Backup concluído com sucesso! Arquivo: {backup_zip_path} ({tamanho_kb:.1f} KB)"
                )
            )

        # 3. Teste de Restauração Controlado (Prompt item 343 e 344)
        if test_restore:
            self.stdout.write("")
            self.stdout.write(
                self.style.NOTICE(
                    "Iniciando teste de restauração isolado em ambiente temporário..."
                )
            )
            self._executar_teste_restauracao(backup_zip_path)

    def _executar_teste_restauracao(self, backup_zip_path: Path) -> None:
        """Restaura o backup em diretório efêmero e valida consistência do SQLite sem tocar no banco real."""
        with tempfile.TemporaryDirectory() as restore_temp_str:
            restore_dir = Path(restore_temp_str)
            self.stdout.write(
                f"  -> Descompactando {backup_zip_path.name} em diretório de teste..."
            )

            try:
                with zipfile.ZipFile(backup_zip_path, "r") as zf:
                    zf.extractall(restore_dir)
            except Exception as err:
                self.stdout.write(self.style.ERROR(f"  [ERRO] Falha ao extrair backup: {err}"))
                return

            restored_db = restore_dir / "db.sqlite3"
            if not restored_db.exists():
                self.stdout.write(
                    self.style.ERROR("  [ERRO] Arquivo de banco db.sqlite3 ausente no backup.")
                )
                return

            self.stdout.write(
                "  -> Validando integridade física do SQLite (PRAGMA integrity_check)..."
            )
            try:
                conn = sqlite3.connect(str(restored_db))
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check;")
                result = cursor.fetchone()
                if result and result[0] == "ok":
                    self.stdout.write(
                        self.style.SUCCESS("  [OK] PRAGMA integrity_check retornou: OK")
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f"  [ERRO] Integridade física comprometida: {result}")
                    )
                    conn.close()
                    return

                # Verifica contagem de tabelas principais
                cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table';")
                total_tabelas = cursor.fetchone()[0]
                self.stdout.write(f"  [OK] Total de tabelas restauradas: {total_tabelas}")
                conn.close()
            except Exception as err:
                self.stdout.write(
                    self.style.ERROR(f"  [ERRO] Falha ao consultar banco restaurado: {err}")
                )
                return

            # Valida arquivos de mídia restaurados
            restored_media = restore_dir / "media"
            total_midia = 0
            if restored_media.exists():
                total_midia = sum(1 for p in restored_media.rglob("*") if p.is_file())
            self.stdout.write(f"  [OK] Total de arquivos de mídia restaurados: {total_midia}")

            self.stdout.write(
                self.style.SUCCESS(
                    "Teste de restauração concluído com 100% de sucesso! O backup é íntegro e operacional."
                )
            )
