"""Bootstrap safety checks with synthetic credentials and no external services."""

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from werkzeug.security import generate_password_hash
import yaml

from scripts import bootstrap_supabase as bootstrap


class SupabaseBootstrapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password = "synthetic-bootstrap-password"
        cls.admin = {
            "role": "ADMIN", "ativo": True, "id_empresa": None,
            "senha_hash": generate_password_hash(cls.password),
        }

    def environment(self, **changes):
        values = {
            key: f"postgresql://postgres.{bootstrap.PROJECT}:synthetic%40password@"
                 f"{bootstrap.POOLER}:{port}/postgres?sslmode=require"
            for key, port in bootstrap.PORTS.items()
        }
        values.update(ADMIN_EMAIL="bootstrap@example.invalid", ADMIN_SENHA=self.password)
        values.update(changes)
        return values

    def test_expected_destination_and_explicit_driver(self):
        urls = bootstrap.validate_urls(self.environment())
        for key, url in urls.items():
            self.assertEqual(url.drivername, "postgresql+psycopg2")
            self.assertEqual(url.username, f"postgres.{bootstrap.PROJECT}")
            self.assertEqual(url.host, bootstrap.POOLER)
            self.assertEqual(url.port, bootstrap.PORTS[key])
            self.assertEqual(url.database, "postgres")
            self.assertEqual(url.password, "synthetic@password")
            self.assertEqual(url.query["sslmode"], "require")

    def test_wrong_project_host_port_and_database_are_rejected_without_values(self):
        original = self.environment()["DATABASE_URL"]
        for value, field in (
            (original.replace(bootstrap.PROJECT, "different-project"), "usuário"),
            (original.replace(bootstrap.POOLER, "wrong-host.example.invalid"), "host"),
            (original.replace(":6543/", ":5432/"), "porta"),
            (original.replace("/postgres?", "/different-database?"), "banco"),
        ):
            with self.subTest(field=field):
                with self.assertRaises(bootstrap.BootstrapError) as caught:
                    bootstrap.validate_urls(self.environment(DATABASE_URL=value))
                self.assertIn(field, str(caught.exception))
                for sensitive in (value, "synthetic", "different-project", "wrong-host", "different-database"):
                    self.assertNotIn(sensitive, str(caught.exception))

    def test_session_and_transaction_urls_cannot_be_swapped(self):
        env = self.environment()
        env["DATABASE_URL"], env["DIRECT_URL"] = env["DIRECT_URL"], env["DATABASE_URL"]
        with self.assertRaises(bootstrap.BootstrapError) as caught:
            bootstrap.validate_urls(env)
        self.assertIn("DATABASE_URL", str(caught.exception))
        self.assertIn("DIRECT_URL", str(caught.exception))

    def test_tls_and_destination_overrides_fail_before_any_connection(self):
        original = self.environment()["DIRECT_URL"]
        for value in (
            original.replace("require", "disable"),
            original + "&sslmode=disable",
            original + "&host=other.example.invalid",
            original + "&hostaddr=127.0.0.1",
            original + "&port=1234",
            original + "&dbname=other",
            original + "&service=other",
            original + "&options=-csearch_path%3Dother",
        ):
            with self.subTest(url=value):
                with patch.object(bootstrap, "inspect_database") as inspect:
                    with self.assertRaises(bootstrap.BootstrapError):
                        bootstrap.preflight(self.environment(DIRECT_URL=value))
                    inspect.assert_not_called()

    def test_missing_second_url_prevents_first_connection(self):
        with patch.object(bootstrap, "inspect_database") as inspect:
            with self.assertRaises(bootstrap.BootstrapError):
                bootstrap.preflight(self.environment(DIRECT_URL=""))
            inspect.assert_not_called()

    def inventory(self, tables=None, revisions=None, complete=False):
        bootstrap.validate_inventory(
            {"plano", "usuario", "alembic_version"} if tables is None else tables,
            ["current"] if revisions is None else revisions,
            required={"plano", "usuario"}, known_revisions={"old", "current"},
            head="current", complete=complete,
        )

    def test_empty_database_and_known_prior_revision_are_valid_for_preparation(self):
        self.inventory(tables=set(), revisions=[])
        self.inventory(tables={"alembic_version", "plano"}, revisions=["old"])

    def test_unversioned_unknown_and_multiple_revision_states_are_rejected(self):
        for tables, revisions in (
            ({"unrelated"}, []),
            ({"usuario"}, []),
            ({"alembic_version", "usuario"}, []),
            ({"alembic_version"}, ["unknown"]),
            ({"alembic_version"}, ["old", "current"]),
        ):
            with self.subTest(tables=tables, revisions=revisions):
                with self.assertRaises(bootstrap.BootstrapError):
                    self.inventory(tables, revisions)

    def test_final_inventory_requires_every_model_table_and_exact_head(self):
        self.inventory(complete=True)
        for tables, revisions in (
            ({"alembic_version", "plano"}, ["current"]),
            ({"alembic_version", "plano", "usuario"}, ["old"]),
            (set(), []),
        ):
            with self.subTest(tables=tables, revisions=revisions):
                with self.assertRaises(bootstrap.BootstrapError):
                    self.inventory(tables, revisions, complete=True)

    def test_existing_admin_requires_role_active_state_no_company_and_password(self):
        row = deepcopy(self.admin)
        bootstrap.validate_admin(row, self.password)
        self.assertEqual(row, self.admin)
        for changes, password in (
            ({"role": "CLIENTE"}, self.password),
            ({"ativo": False}, self.password),
            ({"id_empresa": 1}, self.password),
            ({}, "wrong-synthetic-password"),
        ):
            with self.subTest(changes=changes):
                row = dict(self.admin, **changes)
                before = row.copy()
                with self.assertRaises(bootstrap.BootstrapError) as caught:
                    bootstrap.validate_admin(row, password)
                self.assertEqual(row, before)
                self.assertNotIn(password, str(caught.exception))
                self.assertNotIn(row["senha_hash"], str(caught.exception))

    def fake_engine(self, *, tls=True, database="postgres", plans=None, admin=True):
        connection = MagicMock()
        connection.connection.driver_connection.info.ssl_in_use = tls

        def query(statement, parameters=None):
            result = MagicMock()
            sql = str(statement)
            if "current_database" in sql:
                result.scalar_one.return_value = database
            elif "pg_catalog.pg_tables" in sql:
                result.scalars.return_value = ["alembic_version", "plano", "usuario"]
            elif "version_num" in sql:
                result.scalars.return_value = ["current"]
            elif "senha_hash" in sql:
                result.mappings.return_value.one_or_none.return_value = self.admin if admin else None
            elif "nome_plano" in sql:
                result.scalars.return_value = ["BRONZE", "PRATA", "OURO"] if plans is None else plans
            return result

        connection.execute.side_effect = query
        engine = MagicMock()
        engine.connect.return_value.__enter__.return_value = connection
        return engine, connection

    def inspect(self, engine, *, complete=False):
        with patch.object(bootstrap, "migration_state", return_value=("current", {"old", "current"})), \
                patch.object(bootstrap, "model_tables", return_value={"plano", "usuario"}):
            return bootstrap.inspect_database(
                bootstrap.validate_urls(self.environment())["DIRECT_URL"],
                environment=self.environment(), complete=complete,
                engine_factory=lambda *args, **kwargs: engine,
            )

    def test_inspection_starts_server_read_only_transaction_and_disposes_engine(self):
        engine, connection = self.fake_engine()
        result = self.inspect(engine, complete=True)
        statements = [str(call.args[0]) for call in connection.execute.call_args_list]
        self.assertEqual(statements[0], "SET TRANSACTION READ ONLY")
        self.assertTrue(all(sql.startswith("SELECT ") for sql in statements[1:]))
        self.assertEqual(result, {"tables": 3, "revision": "current"})
        engine.dispose.assert_called_once()

    def test_no_tls_or_unexpected_effective_database_refuses_inspection(self):
        for changes in ({"tls": False}, {"database": "different"}):
            with self.subTest(changes=changes):
                engine, _ = self.fake_engine(**changes)
                with self.assertRaises(bootstrap.BootstrapError):
                    self.inspect(engine)
                engine.dispose.assert_called_once()

    def test_complete_inspection_checks_named_active_plans_and_admin(self):
        for changes in ({"plans": ["OTHER1", "OTHER2", "OTHER3"]}, {"admin": False}):
            with self.subTest(changes=changes):
                engine, _ = self.fake_engine(**changes)
                with self.assertRaises(bootstrap.BootstrapError):
                    self.inspect(engine, complete=True)
                engine.dispose.assert_called_once()

    def test_runtime_and_session_pooler_must_confirm_identical_inventory(self):
        with patch.object(bootstrap, "inspect_database", side_effect=(
            {"tables": 3, "revision": "current"}, {"tables": 2, "revision": "old"}
        )), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(bootstrap.BootstrapError):
                bootstrap.preflight(self.environment())

    def test_diagnostic_and_final_verification_never_run_official_write_commands(self):
        urls = bootstrap.validate_urls(self.environment())
        for stage in ("diagnosticar", "verificar"):
            with self.subTest(stage=stage), \
                    patch.object(bootstrap, "preflight", return_value=urls) as preflight, \
                    patch.object(bootstrap, "run_official_command") as run:
                bootstrap.execute(stage, self.environment())
                preflight.assert_called_once()
                self.assertEqual(preflight.call_args.kwargs["complete"], stage == "verificar")
                run.assert_not_called()

    def test_mutations_require_confirmation_before_preflight_or_subprocess(self):
        for stage in ("migrar", "seed"):
            for values in ({}, {"NEXO_BOOTSTRAP_CONFIRMATION": "wrong"},
                           {"NEXO_BOOTSTRAP_CONFIRMATION": "PREPARAR_NEXO", "ADMIN_SENHA": ""}):
                with self.subTest(stage=stage, values=values), \
                        patch.object(bootstrap, "preflight") as preflight, \
                        patch.object(bootstrap, "run_official_command") as run:
                    with self.assertRaises(bootstrap.BootstrapError):
                        bootstrap.execute(stage, self.environment(**values))
                    preflight.assert_not_called()
                    run.assert_not_called()

    def test_only_official_upgrade_uses_direct_url_and_clean_environment(self):
        env = self.environment(NEXO_BOOTSTRAP_CONFIRMATION="PREPARAR_NEXO",
                               PGHOST="untrusted.invalid", PGSERVICE="untrusted")
        # Encoded space must remain encoded when passed to the child parser.
        env["DIRECT_URL"] = env["DIRECT_URL"].replace("synthetic%40password", "synthetic%20password")
        urls = bootstrap.validate_urls(env)
        with patch.object(bootstrap, "preflight", return_value=urls), \
                patch.object(bootstrap, "run_official_command") as run:
            bootstrap.execute("migrar", env)
        arguments, child_env, _ = run.call_args.args
        self.assertEqual(arguments, ["-m", "flask", "--app", "app:create_app", "db", "upgrade"])
        self.assertEqual(child_env["NEXO_DB_DIRECT"], "1")
        self.assertFalse(any(key.startswith("PG") for key in child_env))
        self.assertEqual(child_env["PYTHON_DOTENV_DISABLED"], "1")
        self.assertEqual(bootstrap.validate_urls(child_env)["DIRECT_URL"].password, "synthetic password")

    def test_unknown_programmatic_stage_cannot_reach_seed(self):
        with patch.object(bootstrap, "preflight") as preflight, \
                patch.object(bootstrap, "run_official_command") as run:
            with self.assertRaises(bootstrap.BootstrapError):
                bootstrap.execute("unexpected", self.environment())
            preflight.assert_not_called()
            run.assert_not_called()

    def test_seed_refuses_intermediate_revision_even_after_authorization(self):
        env = self.environment(NEXO_BOOTSTRAP_CONFIRMATION="PREPARAR_NEXO")
        with patch.object(bootstrap, "preflight", return_value=bootstrap.validate_urls(env)), \
                patch.object(bootstrap, "migration_state", return_value=("current", {"old", "current"})), \
                patch.object(bootstrap, "model_tables", return_value={"plano", "usuario"}), \
                patch.object(bootstrap, "inspect_database", return_value={"tables": 3, "revision": "old"}), \
                patch.object(bootstrap, "run_official_command") as run:
            with self.assertRaises(bootstrap.BootstrapError):
                bootstrap.execute("seed", env)
            run.assert_not_called()

    def test_failed_subprocess_output_and_unexpected_exception_are_redacted(self):
        secret = "synthetic-secret-never-print-this"
        result = subprocess.CompletedProcess([], 1, stdout=secret.encode(), stderr=secret.encode())
        with patch.object(bootstrap.subprocess, "run", return_value=result) as run, \
                contextlib.redirect_stdout(io.StringIO()) as stdout:
            with self.assertRaises(bootstrap.BootstrapError) as caught:
                bootstrap.run_official_command(["seed.py"], {}, "Seed oficial")
        self.assertNotIn(secret, str(caught.exception) + stdout.getvalue())
        self.assertTrue(run.call_args.kwargs["capture_output"])
        with patch.object(bootstrap, "execute", side_effect=RuntimeError(secret)), \
                patch.dict(os.environ, self.environment(), clear=True), \
                contextlib.redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(bootstrap.main([]), 1)
        self.assertNotIn(secret, stderr.getvalue())

    def test_cli_default_is_diagnostic(self):
        with patch.object(bootstrap, "execute") as execute, patch.dict(os.environ, {}, clear=True):
            self.assertEqual(bootstrap.main([]), 0)
        self.assertEqual(execute.call_args.args[0], "diagnosticar")


class SupabaseBootstrapWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # GitHub uses YAML 1.2 semantics for "on"; BaseLoader keeps this key
        # textual instead of treating it as the YAML 1.1 boolean True.
        path = bootstrap.ROOT / ".github/workflows/nexo-supabase-bootstrap.yml"
        cls.workflow = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        cls.job = cls.workflow["jobs"]["preparar"]
        cls.steps = cls.job["steps"]

    def test_only_manual_runs_on_main_with_read_only_repository_permission(self):
        self.assertEqual(set(self.workflow["on"]), {"workflow_dispatch"})
        self.assertEqual(self.job["if"], "github.ref == 'refs/heads/main'")
        self.assertEqual(self.workflow["permissions"], {"contents": "read"})
        self.assertEqual(self.workflow["concurrency"]["cancel-in-progress"], "false")

    def test_default_action_diagnoses_without_requiring_write_confirmation(self):
        inputs = self.workflow["on"]["workflow_dispatch"]["inputs"]
        self.assertEqual(inputs["acao"]["default"], "diagnosticar")
        self.assertEqual(inputs["acao"]["options"], ["diagnosticar", "preparar"])
        self.assertEqual(inputs["confirmacao"]["required"], "false")
        diagnostics = [step for step in self.steps
                       if step.get("run", "").strip() == "python -m scripts.bootstrap_supabase diagnosticar"]
        self.assertEqual(len(diagnostics), 1)
        self.assertNotIn("if", diagnostics[0])

    def test_every_write_step_is_gated_and_receives_explicit_confirmation(self):
        writes = [step for step in self.steps if step.get("run", "").strip() in {
            "python -m scripts.bootstrap_supabase migrar",
            "python -m scripts.bootstrap_supabase seed",
        }]
        self.assertEqual(len(writes), 2)
        for step in writes:
            self.assertEqual(step["if"], "inputs.acao == 'preparar'")
            self.assertEqual(step["env"]["NEXO_BOOTSTRAP_CONFIRMATION"], "${{ inputs.confirmacao }}")
        diagnostic_index = next(i for i, step in enumerate(self.steps)
                                if step.get("run", "").strip().endswith("bootstrap_supabase diagnosticar"))
        self.assertTrue(all(self.steps.index(step) > diagnostic_index for step in writes))

    def test_workflow_confirmation_gate_runs_before_setup_and_rejects_missing_approval(self):
        gate = self.steps[0]
        self.assertEqual(gate["env"]["ACAO"], "${{ inputs.acao }}")
        self.assertEqual(gate["env"]["CONFIRMACAO"], "${{ inputs.confirmacao }}")
        synthetic = "synthetic-workflow-value-never-print"
        environment = {
            "PATH": os.environ.get("PATH", ""),
            "DATABASE_URL": synthetic, "DIRECT_URL": synthetic,
        }
        cases = (
            ({"ACAO": "diagnosticar", "CONFIRMACAO": ""}, True),
            ({"ACAO": "diagnosticar", "CONFIRMACAO": "PREPARAR_NEXO"}, True),
            ({"ACAO": "preparar", "CONFIRMACAO": ""}, False),
            ({"ACAO": "preparar", "CONFIRMACAO": "wrong"}, False),
            ({"ACAO": "preparar", "CONFIRMACAO": "PREPARAR_NEXO"}, False),
            ({"ACAO": "preparar", "CONFIRMACAO": "PREPARAR_NEXO",
              "ADMIN_EMAIL": synthetic, "ADMIN_SENHA": synthetic}, True),
            ({"ACAO": "unexpected", "CONFIRMACAO": "PREPARAR_NEXO"}, False),
        )
        for values, succeeds in cases:
            with self.subTest(action=values["ACAO"], succeeds=succeeds):
                result = subprocess.run(["bash", "-c", gate["run"]],
                                        env={**environment, **values},
                                        capture_output=True, text=True, timeout=5, check=False)
                self.assertEqual(result.returncode == 0, succeeds, result.stderr)
                self.assertNotIn(synthetic, result.stdout + result.stderr)

    def test_checkout_does_not_leave_write_credentials_and_actions_are_pinned(self):
        checkout = [step for step in self.steps if step.get("uses", "").startswith("actions/checkout@")]
        self.assertEqual(len(checkout), 1)
        self.assertEqual(checkout[0]["with"]["persist-credentials"], "false")
        for step in self.steps:
            if "uses" in step:
                self.assertRegex(step["uses"], r"@[0-9a-f]{40}$")

    def test_ephemeral_session_key_is_masked_before_later_steps_receive_it(self):
        generators = [step for step in self.steps
                      if "::add-mask::" in step.get("run", "") and "GITHUB_ENV" in step["run"]]
        self.assertEqual(len(generators), 1)
        scratch = bootstrap.ROOT / "work"
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="bootstrap-workflow-", dir=scratch) as temporary:
            environment_file = os.path.join(temporary, "github-env")
            result = subprocess.run(
                ["bash", "-c", generators[0]["run"]],
                env={"PATH": str(Path(sys.executable).parent)
                     + os.pathsep + os.environ.get("PATH", ""), "GITHUB_ENV": environment_file},
                capture_output=True, text=True, timeout=5, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            with open(environment_file, encoding="utf-8") as source:
                key_line = source.read()
            self.assertRegex(key_line, r"^SECRET_KEY=[0-9a-f]{64}\n$")
            generated_key = key_line.strip().partition("=")[2]
            self.assertEqual(result.stdout, f"::add-mask::{generated_key}\n")
            self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
