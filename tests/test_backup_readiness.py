"""Verificações locais com arquivos fictícios; sem app, .env ou bancos reais."""

import contextlib
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "backup_readiness", ROOT / "scripts" / "verificar_prontidao_backup.py",
)
readiness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(readiness)


class BackupReadinessTests(unittest.TestCase):
    def setUp(self):
        root = ROOT / ".audit_tmp"
        root.mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix="backup-readiness-", dir=root)
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.backup = self.directory / "ficticio.dump"
        # Deliberadamente não é um backup real: cabeçalho sozinho não o valida.
        self.content = b"PGDMP\x01conteudo inteiramente ficticio"
        self.backup.write_bytes(self.content)

    def invoke(self, argv, *, found=True, command_result=None):
        stdout = io.StringIO()
        stderr = io.StringIO()
        if command_result is None:
            command_result = SimpleNamespace(returncode=0)
        with patch.object(readiness.shutil, "which", side_effect=lambda name: name if found else None), \
                patch.object(readiness.subprocess, "run", return_value=command_result) as run, \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                code = readiness.cli(argv)
            except SystemExit as exc:
                code = exc.code
        return code, stdout.getvalue() + stderr.getvalue(), run

    def test_default_only_checks_versions_without_database_arguments(self):
        code, output, run = self.invoke([])
        self.assertEqual(code, 0)
        self.assertIn("Modo seguro", output)
        self.assertIn("validação operacional permanece pendente", output)
        self.assertEqual([call.args[0] for call in run.call_args_list], [
            ["pg_dump", "--version"], ["pg_restore", "--version"], ["psql", "--version"],
        ])
        for call in run.call_args_list:
            self.assertIs(call.kwargs["shell"], False)
            self.assertEqual(call.kwargs["stdout"], subprocess.DEVNULL)
            self.assertEqual(call.kwargs["stderr"], subprocess.DEVNULL)
            self.assertEqual(call.kwargs["stdin"], subprocess.DEVNULL)
            self.assertEqual(call.kwargs["timeout"], 15)

    def test_dry_run_does_not_execute_subprocesses_or_modify_file(self):
        code, output, run = self.invoke(["--dry-run", "--backup", str(self.backup), "--list"])
        self.assertEqual(code, 0)
        run.assert_not_called()
        self.assertIn("não inspecionado (--dry-run)", output)
        self.assertEqual(self.backup.read_bytes(), self.content)
        self.assertEqual(list(self.directory.iterdir()), [self.backup])

    def test_missing_or_directory_backup_is_rejected_without_path_output(self):
        for path in (self.directory / "postgresql-secret-password.dump", self.directory):
            with self.subTest(path=path):
                code, output, run = self.invoke(["--dry-run", "--backup", str(path)])
                self.assertEqual(code, 1)
                self.assertIn("ausente, inacessível ou ilegível", output)
                self.assertNotIn(str(path), output)
                self.assertNotIn("secret-password", output)
                run.assert_not_called()

    def test_invalid_empty_and_header_only_backups_are_rejected(self):
        for content in (b"", b"not a dump", b"PGDM", b"PGDMP"):
            with self.subTest(content=content):
                self.backup.write_bytes(content)
                code, output, run = self.invoke(["--dry-run", "--backup", str(self.backup), "--list"])
                self.assertEqual(code, 1)
                self.assertIn("ausente ou truncado", output)
                run.assert_not_called()

    def test_sha256_matches_and_accepts_uppercase_reference(self):
        digest = hashlib.sha256(self.content).hexdigest()
        code, output, run = self.invoke([
            "--dry-run", "--backup", str(self.backup), "--sha256", digest.upper(),
        ])
        self.assertEqual(code, 0)
        self.assertIn(digest, output)
        self.assertIn("coincide com a referência", output)
        self.assertIn("conteúdo ainda não validado", output)
        run.assert_not_called()

    def test_sha256_mismatch_stops_before_catalog_inspection(self):
        code, output, run = self.invoke([
            "--backup", str(self.backup), "--sha256", "0" * 64, "--list",
        ])
        self.assertEqual(code, 1)
        self.assertIn("divergente", output)
        self.assertEqual(run.call_count, 3)

    def test_header_does_not_claim_full_validation_without_catalog(self):
        code, output, _run = self.invoke(["--backup", str(self.backup)])
        self.assertEqual(code, 0)
        self.assertIn("conteúdo ainda não validado", output)
        self.assertIn("sem referência externa", output)
        self.assertNotIn("Catálogo:", output)

    def test_list_only_invocation_sanitizes_environment_and_suppresses_metadata(self):
        secret = "fictitious-credential-do-not-print"
        with patch.dict(os.environ, {
            "PGPASSWORD": secret, "PGHOST": secret, "PGSERVICE": secret,
            "PGSERVICEFILE": secret, "PGPASSFILE": secret,
            "DATABASE_URL": secret, "DIRECT_URL": secret, "SUPABASE_KEY": secret,
        }):
            code, output, run = self.invoke(["--backup", str(self.backup), "--list"])
        self.assertEqual(code, 0)
        call = run.call_args_list[-1]
        self.assertEqual(call.args[0], ["pg_restore", "--list", "--", str(self.backup.resolve())])
        self.assertEqual(call.kwargs["env"]["PGPASSFILE"], os.devnull)
        self.assertEqual(call.kwargs["env"]["PGSERVICEFILE"], os.devnull)
        self.assertNotIn(secret, str(call.kwargs["env"]))
        self.assertNotIn(secret, output)
        self.assertNotIn(str(self.backup), output)
        self.assertIn("metadados não exibidos", output)

    def test_truncated_archive_failing_pg_restore_is_not_validated(self):
        stdout = io.StringIO()
        responses = [SimpleNamespace(returncode=0)] * 3 + [SimpleNamespace(returncode=1)]
        with patch.object(readiness.shutil, "which", side_effect=lambda name: name), \
                patch.object(readiness.subprocess, "run", side_effect=responses), \
                contextlib.redirect_stdout(stdout):
            code = readiness.cli(["--backup", str(self.backup), "--list"])
        self.assertEqual(code, 1)
        self.assertIn("backup não validado", stdout.getvalue())
        self.assertNotIn("--list concluído", stdout.getvalue())

    def test_missing_tools_is_reported_with_meaningful_exit_status(self):
        code, output, run = self.invoke([], found=False)
        self.assertEqual(code, 3)
        self.assertEqual(output.count("indisponível no PATH"), 3)
        run.assert_not_called()

    def test_list_without_pg_restore_does_not_run_a_restore(self):
        code, output, run = self.invoke(["--backup", str(self.backup), "--list"], found=False)
        self.assertEqual(code, 3)
        self.assertIn("inspeção pendente", output)
        run.assert_not_called()

    def test_timeout_and_missing_executable_do_not_leak_errors(self):
        secret = "postgresql://user:secret-password@invalid/db"
        for error in (subprocess.TimeoutExpired(secret, 15), OSError(secret)):
            with self.subTest(error=type(error).__name__):
                stdout = io.StringIO()
                with patch.object(readiness.shutil, "which", side_effect=lambda name: name), \
                        patch.object(readiness.subprocess, "run", side_effect=error), \
                        contextlib.redirect_stdout(stdout):
                    self.assertEqual(readiness.cli([]), 3)
                self.assertNotIn(secret, stdout.getvalue())
                self.assertNotIn("secret-password", stdout.getvalue())

    def test_dangerous_unknown_and_malformed_arguments_are_rejected_without_echo(self):
        secret = "postgresql://user:secret-password@invalid/db"
        cases = (
            ["--database", secret], ["--clean"], ["--create"], ["--apply"],
            ["--connection", secret], ["--sha256", secret], ["--backup"],
            ["--list"], ["--sha256", "0" * 64], ["--dry"],
            ["--backup", str(self.backup), "--sha256", ""],
        )
        for argv in cases:
            with self.subTest(argv=argv):
                code, output, run = self.invoke(argv)
                self.assertEqual(code, 2)
                self.assertNotIn(secret, output)
                self.assertNotIn("secret-password", output)
                run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
