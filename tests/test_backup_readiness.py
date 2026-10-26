"""Verificações locais com arquivos fictícios; sem app, .env ou bancos reais."""

import contextlib
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import stat
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
        with patch.object(readiness, "locate_tool", side_effect=lambda name: name if found else None), \
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
        # O caminho não vai no argv: o Python reabre o caminho já resolvido após o hash e
        # entrega o conteúdo pelo stdin; uma troca nesse intervalo não é detectada.
        self.assertEqual(call.args[0], ["pg_restore", "--list"])
        archive = call.kwargs["stdin"]
        self.assertEqual((archive.name, archive.mode, archive.closed), (str(self.backup.resolve()), "rb", True))
        self.assertIs(call.kwargs["shell"], False)
        self.assertEqual(call.kwargs["stdout"], subprocess.DEVNULL)
        self.assertEqual(call.kwargs["stderr"], subprocess.DEVNULL)
        self.assertEqual(call.kwargs["timeout"], 15)
        self.assertEqual(call.kwargs["env"]["PGPASSFILE"], os.devnull)
        self.assertEqual(call.kwargs["env"]["PGSERVICEFILE"], os.devnull)
        self.assertNotIn(secret, str(call.kwargs["env"]))
        self.assertNotIn(secret, output)
        self.assertNotIn(str(self.backup), output)
        self.assertIn("metadados não exibidos", output)

    def test_truncated_archive_failing_pg_restore_is_not_validated(self):
        stdout = io.StringIO()
        responses = [SimpleNamespace(returncode=0)] * 3 + [SimpleNamespace(returncode=1)]
        with patch.object(readiness, "locate_tool", side_effect=lambda name: name), \
                patch.object(readiness.subprocess, "run", side_effect=responses), \
                contextlib.redirect_stdout(stdout):
            code = readiness.cli(["--backup", str(self.backup), "--list"])
        self.assertEqual(code, 1)
        self.assertIn("backup não validado", stdout.getvalue())
        self.assertNotIn("--list concluído", stdout.getvalue())

    def test_failed_version_check_marks_tool_unavailable_and_skips_listing(self):
        stdout = io.StringIO()
        responses = [SimpleNamespace(returncode=0), SimpleNamespace(returncode=1), SimpleNamespace(returncode=0)]
        with patch.object(readiness, "locate_tool", side_effect=lambda name: name), \
                patch.object(readiness.subprocess, "run", side_effect=responses) as run, \
                contextlib.redirect_stdout(stdout):
            code = readiness.cli(["--backup", str(self.backup), "--list"])
        self.assertEqual(code, 3)
        self.assertEqual(run.call_count, 3)
        self.assertIn("inspeção pendente", stdout.getvalue())
        self.assertNotIn("backup não validado", stdout.getvalue())

    def test_backup_unavailable_when_reopened_for_listing_is_not_validated(self):
        inspect_backup = readiness.inspect_backup

        def inspect_then_remove(filename, expected_sha256):
            path = inspect_backup(filename, expected_sha256)
            self.backup.unlink()
            return path

        with patch.object(readiness, "inspect_backup", side_effect=inspect_then_remove):
            code, output, run = self.invoke(["--backup", str(self.backup), "--list"])
        self.assertEqual(code, 1)
        self.assertIn("Catálogo: não foi possível executar; backup não validado.", output)
        self.assertNotIn(str(self.backup), output)
        self.assertEqual(run.call_count, 3)

    def test_locate_tool_ignores_current_directory_relative_entries_and_wrappers(self):
        suffix = ".exe" if os.name == "nt" else ""
        trusted = self.directory / "bin"
        planted = self.directory / "trabalho"
        trusted.mkdir()
        planted.mkdir()
        tool = trusted / ("pg_restore" + suffix)
        for executable in (tool, planted / ("pg_restore" + suffix)):
            executable.write_bytes(b"")
            executable.chmod(0o700)
        with contextlib.chdir(planted):
            # Entrada relativa que, a partir de planted, aponta para o próprio planted.
            relative = os.path.join(os.pardir, "trabalho")
            with patch.dict(os.environ, {"PATH": os.pathsep.join([".", "", relative, str(trusted)])}):
                self.assertEqual(readiness.locate_tool("pg_restore"), str(tool))
            with patch.dict(os.environ, {"PATH": os.pathsep.join([".", ""])}):
                self.assertIsNone(readiness.locate_tool("pg_restore"))
        # Entrada relativa simples, sem "." inicial: a partir de self.directory, aponta para planted.
        with contextlib.chdir(self.directory), \
                patch.dict(os.environ, {"PATH": os.pathsep.join([planted.name, str(trusted)])}):
            self.assertEqual(readiness.locate_tool("pg_restore"), str(tool))
        if os.name == "nt":
            wrappers = self.directory / "wrappers"
            wrappers.mkdir()
            for extension in (".bat", ".cmd", ".com"):
                (wrappers / ("pg_restore" + extension)).write_bytes(b"")
            with patch.dict(os.environ, {"PATH": str(wrappers)}):
                self.assertIsNone(readiness.locate_tool("pg_restore"))
            # Sem unidade, "\dir" depende da unidade atual; os.path.isabs (3.12) o aceitaria.
            with contextlib.chdir(self.directory), \
                    patch.dict(os.environ, {"PATH": os.path.splitdrive(str(trusted))[1]}):
                self.assertIsNone(readiness.locate_tool("pg_restore"))

    def test_locate_tool_requires_an_executable_regular_file(self):
        filename = "pg_restore" + (".exe" if os.name == "nt" else "")
        decoy = self.directory / "decoy"
        trusted = self.directory / "bin"
        (decoy / filename).mkdir(parents=True)
        trusted.mkdir()
        tool = trusted / filename
        tool.write_bytes(b"")
        tool.chmod(0o700)
        with patch.dict(os.environ, {"PATH": os.pathsep.join([str(decoy), str(trusted)])}):
            self.assertEqual(readiness.locate_tool("pg_restore"), str(tool))
            # Bits de execução dependem do sistema de arquivos: vale o que os.access informar.
            with patch.object(readiness.os, "access", return_value=False) as access:
                self.assertIsNone(readiness.locate_tool("pg_restore"))
        access.assert_called_once_with(str(tool), os.X_OK)

    def test_read_only_backup_is_hashed_and_listed_without_write_access(self):
        self.backup.chmod(stat.S_IREAD)
        self.addCleanup(self.backup.chmod, stat.S_IREAD | stat.S_IWRITE)
        digest = hashlib.sha256(self.content).hexdigest()
        code, output, run = self.invoke(["--backup", str(self.backup), "--sha256", digest, "--list"])
        self.assertEqual(code, 0)
        self.assertIn("coincide com a referência", output)
        self.assertIn("metadados não exibidos", output)
        self.assertEqual(run.call_count, 4)
        self.assertEqual(self.backup.read_bytes(), self.content)

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
                with patch.object(readiness, "locate_tool", side_effect=lambda name: name), \
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
