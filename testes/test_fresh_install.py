"""
Teste de instalação limpa em banco vazio (Prompt 12, itens 388-392).

Verifica que todas as migrações são aplicáveis desde o zero em um banco SQLite limpo,
sem depender de dados pré-existentes e sem afetar o banco principal.
"""

import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from django.test import SimpleTestCase


class FreshDatabaseInstallTests(SimpleTestCase):
    """Testa a integridade de todas as migrações em um banco SQLite temporário vazio."""

    def test_migracao_completa_em_banco_limpo(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_db = Path(temp_dir) / "fresh.sqlite3"
            env = os.environ.copy()
            env["DATABASE_URL"] = f"sqlite:///{temp_db.as_posix()}"
            env["DJANGO_SETTINGS_MODULE"] = "configuracao.settings.desenvolvimento"

            # 1. Executa migrate completo
            res_migrate = subprocess.run(
                [sys.executable, "manage.py", "migrate", "--noinput"],
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                res_migrate.returncode,
                0,
                f"Migrate em banco limpo falhou:\nSTDOUT:\n{res_migrate.stdout}\nSTDERR:\n{res_migrate.stderr}",
            )
            self.assertIn("Applying", res_migrate.stdout)

            # 2. Executa check no banco migrado
            res_check = subprocess.run(
                [sys.executable, "manage.py", "check"],
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                res_check.returncode,
                0,
                f"Check no banco limpo falhou:\n{res_check.stderr}",
            )

            # 3. Valida integridade física e tabelas fundamentais
            self.assertTrue(temp_db.exists())
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()

            cursor.execute("PRAGMA integrity_check;")
            self.assertEqual(cursor.fetchone()[0], "ok")

            cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table';")
            total_tabelas = cursor.fetchone()[0]
            self.assertGreaterEqual(total_tabelas, 25)

            # Verifica tabelas principais do projeto
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ("
                "'administracao_usuarioadministrativo', "
                "'clientes_cliente', "
                "'sites_projetosite', "
                "'sites_publicacaosite', "
                "'sites_templatesite', "
                "'sites_enderecosite', "
                "'sites_linkinteligente', "
                "'sites_eventoanalitico'"
                ");"
            )
            tabelas_encontradas = {row[0] for row in cursor.fetchall()}
            self.assertEqual(
                len(tabelas_encontradas),
                8,
                f"Faltam tabelas essenciais no banco limpo: {8 - len(tabelas_encontradas)} ausentes.",
            )

            conn.close()
