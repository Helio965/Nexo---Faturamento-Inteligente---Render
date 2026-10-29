"""SEC-006B: o instalador verifica a origem antes de processar requisitos.

Todos os downloads e processos de instalação são simulados. Um probe isolado
somente lê versão e caminhos do pip efetivo, sem instalar pacotes ou usar rede.
Os contratos YAML preservam os jobs existentes e exigem o mesmo caminho de
instalação no CI e no build.
"""

from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.error
import urllib.request

import yaml

from tools import install_dependencies as installer


ROOT = Path(__file__).resolve().parents[1]


class VerifiedInstallerTests(unittest.TestCase):
    @staticmethod
    def _opener(payload):
        opener = Mock()
        opener.open.return_value = io.BytesIO(payload)
        return opener

    @staticmethod
    def _fake_download(directory):
        wheel = Path(directory) / installer.PIP_WHEEL
        wheel.write_bytes(b"synthetic-wheel-not-executed")
        return wheel

    @staticmethod
    def _process_results():
        return [
            subprocess.CompletedProcess([], 0),
            subprocess.CompletedProcess([], 0, stdout="pip=" + installer.PIP_VERSION + "\n"),
            subprocess.CompletedProcess([], 0),
            subprocess.CompletedProcess([], 0),
        ]

    def test_verified_download_accepts_only_matching_bytes(self):
        payload = b"synthetic-wheel-bytes"
        opener = self._opener(payload)
        with tempfile.TemporaryDirectory(prefix="nexo-installer-unit-") as directory:
            with patch.object(installer.urllib.request, "build_opener", return_value=opener), \
                    patch.object(installer, "PIP_SHA256", hashlib.sha256(payload).hexdigest()):
                result = installer.download_verified_wheel(directory)
            self.assertEqual(result.read_bytes(), payload)
            self.assertEqual(result.name, installer.PIP_WHEEL)
            opener.open.assert_called_once_with(installer.PIP_URL, timeout=30)

    def test_hash_mismatch_prevents_every_installation_process(self):
        opener = self._opener(b"modified-untrusted-wheel")
        with patch.object(installer.urllib.request, "build_opener", return_value=opener), \
                patch.object(installer.subprocess, "run") as run:
            with self.assertRaisesRegex(installer.BootstrapError, "SHA256"):
                installer.install()
        run.assert_not_called()

    def test_oversized_download_prevents_every_installation_process(self):
        opener = self._opener(b"x" * 9)
        with patch.object(installer.urllib.request, "build_opener", return_value=opener), \
                patch.object(installer, "MAX_WHEEL_BYTES", 8), \
                patch.object(installer.subprocess, "run") as run:
            with self.assertRaisesRegex(installer.BootstrapError, "limite"):
                installer.install()
        run.assert_not_called()

    def test_official_redirect_handler_rejects_unapproved_origins(self):
        handler = installer.OfficialWheelRedirects()
        request = urllib.request.Request(installer.PIP_URL)
        for target in (
            "https://packages.invalid/pip.whl",
            "https://files.pythonhosted.org.packages.invalid/pip.whl",
            "http://files.pythonhosted.org/pip.whl",
            "https://files.pythonhosted.org:8443/pip.whl",
            "https://synthetic-user@files.pythonhosted.org/pip.whl",
            "https://synthetic-user:synthetic-password@files.pythonhosted.org/pip.whl",
        ):
            with self.subTest(target=target):
                with self.assertRaises(installer.BootstrapError):
                    handler.redirect_request(request, None, 302, "Found", {}, target)

    def test_redirect_rejection_prevents_every_installation_process(self):
        opener = Mock()
        opener.open.side_effect = installer.BootstrapError("Origem não autorizada.")
        with patch.object(installer.urllib.request, "build_opener", return_value=opener), \
                patch.object(installer.subprocess, "run") as run:
            with self.assertRaises(installer.BootstrapError):
                installer.install()
        run.assert_not_called()

    def test_installer_environment_filters_secrets_and_preserves_network_controls(self):
        synthetic = {
            "PATH": "/synthetic/bin", "LANG": "C.UTF-8",
            "HTTPS_PROXY": "https://managed-proxy.invalid:8443",
            "NO_PROXY": "localhost,127.0.0.1",
            "SSL_CERT_FILE": "/synthetic/managed-ca.pem",
            "PIP_INDEX_URL": "https://unapproved-index.invalid/simple",
            "PIP_EXTRA_INDEX_URL": "https://unapproved-extra.invalid/simple",
            "PIP_TRUSTED_HOST": "unapproved-index.invalid",
            "PIP_CONFIG_FILE": "/synthetic/unapproved-pip.conf",
            "PYTHONPATH": "/synthetic/unapproved-imports",
            "NETRC": "/synthetic/credentials-not-to-read",
            "SECRET_KEY": "synthetic-secret-not-to-copy",
            "DATABASE_URL": "postgresql://synthetic.invalid/not-to-connect",
            "DIRECT_URL": "postgresql://synthetic.invalid/not-to-connect-directly",
            "BREVO_API_KEY": "synthetic-api-key-not-to-copy",
            "MAIL_PASSWORD": "synthetic-mail-password-not-to-copy",
            "HF_API_TOKEN": "synthetic-ai-token-not-to-copy",
        }
        with patch.dict(os.environ, synthetic, clear=True):
            environment = installer.installer_environment("/synthetic/empty-netrc")
        for key in ("PATH", "LANG", "HTTPS_PROXY", "NO_PROXY", "SSL_CERT_FILE"):
            self.assertEqual(environment[key], synthetic[key])
        self.assertEqual(environment["PIP_CONFIG_FILE"], os.devnull)
        self.assertEqual(environment["NETRC"], "/synthetic/empty-netrc")
        self.assertEqual({k for k in environment if k.startswith("PIP_")}, {"PIP_CONFIG_FILE"})
        for key in (
            "PYTHONPATH", "SECRET_KEY", "DATABASE_URL", "DIRECT_URL",
            "BREVO_API_KEY", "MAIL_PASSWORD", "HF_API_TOKEN",
        ):
            self.assertNotIn(key, environment)

    def test_bootstrap_runs_verified_wheel_before_any_application_requirements(self):
        events = []

        def run(command, **kwargs):
            environment = kwargs["env"]
            self.assertEqual(Path(environment["NETRC"]).read_bytes(), b"")
            self.assertEqual(environment["PIP_CONFIG_FILE"], os.devnull)
            events.append(command)
            if len(events) == 1:
                # O pip disponível no ambiente não é chamado para instalar o
                # bootstrap; o launcher importa exclusivamente o wheel validado.
                self.assertEqual(command[:4], [sys.executable, "-I", "-B", "-c"])
                self.assertIn("sys.path.insert(0,wheel)", command[4])
                self.assertIn("runpy.run_module('pip'", command[4])
                self.assertEqual(Path(command[5]).name, installer.PIP_WHEEL)
                for option in ("--isolated", "--no-index", "--no-deps", "--force-reinstall"):
                    self.assertIn(option, command)
                return subprocess.CompletedProcess(command, 0)
            if len(events) == 2:
                self.assertIn("importlib.metadata.version('pip')", command[-1])
                return subprocess.CompletedProcess(command, 0, stdout="pip=" + installer.PIP_VERSION)
            return subprocess.CompletedProcess(command, 0)

        with patch.object(installer, "download_verified_wheel", side_effect=self._fake_download), \
                patch.object(installer.subprocess, "run", side_effect=run), \
                redirect_stdout(io.StringIO()):
            installer.install("requirements-dev.txt")
        self.assertEqual(len(events), 4)
        dependencies, check = events[2:]
        self.assertEqual(dependencies[:5], [sys.executable, "-I", "-B", "-m", "pip"])
        self.assertIn("--isolated", dependencies)
        self.assertEqual(dependencies[dependencies.index("--index-url") + 1], "https://pypi.org/simple")
        self.assertEqual(dependencies[dependencies.index("-r") + 1], str(ROOT / "requirements-dev.txt"))
        self.assertEqual(dependencies[dependencies.index("--keyring-provider") + 1], "disabled")
        self.assertNotIn("--trusted-host", dependencies)
        self.assertEqual(check[-1], "check")

    def test_wrong_installed_version_stops_before_application_requirements(self):
        results = [subprocess.CompletedProcess([], 0), subprocess.CompletedProcess([], 1, stdout="")]
        with patch.object(installer, "download_verified_wheel", side_effect=self._fake_download), \
                patch.object(installer.subprocess, "run", side_effect=results) as run:
            with self.assertRaisesRegex(installer.BootstrapError, "Versão efetiva"):
                installer.install()
        self.assertEqual(run.call_count, 2)
        self.assertTrue(all("-r" not in call.args[0] for call in run.call_args_list))

    def test_prepare_only_never_installs_application_requirements(self):
        with patch.object(installer, "download_verified_wheel", side_effect=self._fake_download), \
                patch.object(installer.subprocess, "run", side_effect=self._process_results()[:2]) as run, \
                redirect_stdout(io.StringIO()):
            installer.install(prepare_only=True)
        self.assertEqual(run.call_count, 2)
        self.assertTrue(all("-r" not in call.args[0] for call in run.call_args_list))

    def test_unapproved_requirements_are_rejected_before_download(self):
        with patch.object(installer, "download_verified_wheel") as download, \
                patch.object(installer.subprocess, "run") as run:
            for name in ("../requirements.txt", "/synthetic/requirements.txt", "https://packages.invalid/req.txt"):
                with self.subTest(name=name):
                    with self.assertRaises(installer.BootstrapError):
                        installer.install(name)
        download.assert_not_called()
        run.assert_not_called()

    def test_bootstrap_failure_never_reaches_verification_or_dependencies(self):
        with patch.object(installer, "download_verified_wheel", side_effect=self._fake_download), \
                patch.object(installer.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "synthetic")) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                installer.install()
        self.assertEqual(run.call_count, 1)

    def test_cli_network_error_does_not_expose_proxy_or_credential_details(self):
        private_detail = "synthetic-private-proxy-detail-not-for-logs"
        error = urllib.error.URLError(private_detail)
        output = io.StringIO()
        with patch.object(sys, "argv", ["install_dependencies.py", "--prepare-only"]), \
                patch.object(installer, "install", side_effect=error), redirect_stderr(output):
            with self.assertRaises(SystemExit) as raised:
                installer.main()
        self.assertEqual(raised.exception.code, 1)
        self.assertIn("Preparação/instalação segura falhou", output.getvalue())
        self.assertNotIn(private_detail, output.getvalue())


class InstalledInstallerCompatibilityTests(unittest.TestCase):
    def test_effective_pip_and_vendor_are_the_fixed_installer_for_this_python(self):
        # Este teste torna a preparação do instalador verificável também na CI:
        # metadata, módulo e código vendorizado devem vir do Python de destino.
        with tempfile.TemporaryDirectory(prefix="nexo-installer-probe-") as directory:
            netrc = Path(directory) / "empty-netrc"
            netrc.touch(mode=0o600)
            environment = installer.installer_environment(netrc)
            output = io.StringIO()
            with redirect_stdout(output):
                installer.verify_installed_pip(environment)
            self.assertEqual(output.getvalue().strip(), "pip=" + installer.PIP_VERSION)
            probe = """
import importlib.metadata
import json
from pathlib import Path
import sys
import pip
import pip._vendor.requests
root = Path(pip.__file__).resolve().parent
vendor = Path(pip._vendor.requests.__file__).resolve()
assert root.is_relative_to(Path(sys.prefix).resolve())
assert vendor.is_relative_to(root / '_vendor')
print(json.dumps({'metadata_version': importlib.metadata.version('pip'),
                  'module_version': pip.__version__, 'vendor_within_pip': True}))
"""
            result = subprocess.run(
                [sys.executable, "-I", "-B", "-c", probe], cwd=ROOT, env=environment,
                capture_output=True, text=True, check=True, timeout=15,
            )
        actual = json.loads(result.stdout)
        self.assertEqual(actual["metadata_version"], installer.PIP_VERSION)
        self.assertEqual(actual["module_version"], installer.PIP_VERSION)
        self.assertTrue(actual["vendor_within_pip"])


class InstallationConfigurationContractsTests(unittest.TestCase):
    def test_both_ci_jobs_use_shared_installer_before_preserved_test_commands(self):
        workflow = yaml.safe_load((ROOT / ".github/workflows/nexo-security-ci.yml").read_text())
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        # supply-chain é um job ADVISÓRIO (SCA/SAST/segredos): não roda a suíte nem
        # usa o instalador compartilhado; o contrato abaixo vale para os jobs de teste.
        self.assertEqual(set(workflow["jobs"]), {"sqlite-browser", "postgresql-security", "supply-chain"})
        expected_tests = {
            "sqlite-browser": ("python -B -m unittest discover -s tests -t . -v",),
            "postgresql-security": (
                "python -B -m unittest tests.postgresql_auth_tokens -v",
                "python -B -m unittest tests.postgresql_session_revocation -v",
            ),
        }
        command = "python -I tools/install_dependencies.py --requirements requirements-dev.txt"
        for job_id, job in {k: workflow["jobs"][k] for k in expected_tests}.items():
            with self.subTest(job=job_id):
                self.assertEqual(job.get("permissions", workflow["permissions"]), {"contents": "read"})
                steps = job["steps"]
                python_positions = [i for i, step in enumerate(steps) if "actions/setup-python@" in step.get("uses", "")]
                self.assertEqual(len(python_positions), 1)
                self.assertEqual(steps[python_positions[0]]["with"]["python-version"], "3.12")
                installers = [i for i, step in enumerate(steps) if command in step.get("run", "").splitlines()]
                self.assertEqual(len(installers), 1)
                installer_position = installers[0]
                self.assertLess(python_positions[0], installer_position)
                for expected in expected_tests[job_id]:
                    matches = [i for i, step in enumerate(steps) if expected in step.get("run", "").splitlines()]
                    self.assertEqual(len(matches), 1)
                    self.assertGreater(matches[0], installer_position)
                for i, step in enumerate(steps):
                    run = step.get("run", "")
                    self.assertNotIn("pip install -r", run)
                    if "playwright install" in run:
                        self.assertGreater(i, installer_position)
        # Job advisório: permissões só-leitura, não roda a suíte e cada passo de
        # varredura é continue-on-error (nunca trava o PR nem reduz cobertura).
        sca = workflow["jobs"]["supply-chain"]
        self.assertEqual(sca.get("permissions", workflow["permissions"]), {"contents": "read"})
        scan_steps = [s for s in sca["steps"] if any(
            t in s.get("run", "") for t in ("pip-audit", "bandit", "varredura_segredos"))]
        self.assertTrue(scan_steps)
        for step in scan_steps:
            self.assertTrue(step.get("continue-on-error") is True)
        for step in sca["steps"]:
            self.assertNotIn("pip install -r", step.get("run", ""))
            self.assertNotIn("discover -s tests", step.get("run", ""))

    def test_render_prepares_same_installer_without_changing_runtime_contract(self):
        blueprint = yaml.safe_load((ROOT / "render.yaml").read_text())
        service = blueprint["services"][0]
        self.assertEqual(service["buildCommand"], "python -I tools/install_dependencies.py --requirements requirements.txt")
        self.assertEqual(service["branch"], "main")
        self.assertEqual(service["autoDeployTrigger"], "off")
        self.assertEqual(service["healthCheckPath"], "/healthz")
        self.assertEqual(service["startCommand"], "gunicorn -w 1 --threads 50 --timeout 180 -b 0.0.0.0:$PORT wsgi:app")
        python = next(value for value in service["envVars"] if value["key"] == "PYTHON_VERSION")
        self.assertEqual(python["value"], "3.12.10")


if __name__ == "__main__":
    unittest.main()
