"""SEC-006B: dotenv com configuração sintética e escrita atômica controlada.

O .env do checkout nunca é aberto. Os testes da aplicação usam um processo
novo e redirecionam a chamada explícita de config.py para um arquivo privado.
O probe de escrita modela EXDEV sem outro filesystem ou serviço externo.
"""

import errno
import io
import os
from pathlib import Path
import secrets
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from dotenv import dotenv_values, load_dotenv, set_key, unset_key


ROOT = Path(__file__).resolve().parents[1]


class DotenvParsingCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory(prefix="nexo-sec006b-dotenv-")
        self.addCleanup(self.work.cleanup)
        self.directory = Path(self.work.name)
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def _file(self, contents):
        path = self.directory / ".env.synthetic"
        path.write_text(contents, encoding="utf-8")
        path.chmod(0o600)
        return path

    def test_existing_environment_has_precedence_without_override(self):
        path = self._file("SEC006B_VALUE=from-file\nSEC006B_NEW=created\n")
        os.environ["SEC006B_VALUE"] = "from-environment"
        self.assertTrue(load_dotenv(path))
        self.assertEqual(os.environ["SEC006B_VALUE"], "from-environment")
        self.assertEqual(os.environ["SEC006B_NEW"], "created")

    def test_explicit_override_controls_value_and_interpolation(self):
        path = self._file("SEC006B_BASE=file\nSEC006B_EXPANDED=${SEC006B_BASE}/child\n")
        os.environ["SEC006B_BASE"] = "environment"
        self.assertTrue(load_dotenv(path, override=False))
        self.assertEqual(os.environ["SEC006B_EXPANDED"], "environment/child")
        self.assertTrue(load_dotenv(path, override=True))
        self.assertEqual(os.environ["SEC006B_BASE"], "file")
        self.assertEqual(os.environ["SEC006B_EXPANDED"], "file/child")

    def test_utf8_quotes_escapes_and_empty_values_are_preserved(self):
        path = self._file(
            'export SEC006B_LABEL="ação sintética"\n'
            'SEC006B_LINES="first\\nsecond"\n'
            "SEC006B_LITERAL='path\\with\\slashes'\n"
            "SEC006B_EMPTY=\n"
            "SEC006B_UNASSIGNED\n"
        )
        self.assertTrue(load_dotenv(path, encoding="utf-8"))
        self.assertEqual(os.environ["SEC006B_LABEL"], "ação sintética")
        self.assertEqual(os.environ["SEC006B_LINES"], "first\nsecond")
        self.assertEqual(os.environ["SEC006B_LITERAL"], r"path\with\slashes")
        self.assertEqual(os.environ["SEC006B_EMPTY"], "")
        self.assertNotIn("SEC006B_UNASSIGNED", os.environ)

    def test_values_only_parsing_does_not_mutate_environment(self):
        os.environ["SEC006B_EXISTING"] = "environment"
        values = dotenv_values(stream=io.StringIO("SEC006B_PARSED=synthetic\n"))
        self.assertEqual(values, {"SEC006B_PARSED": "synthetic"})
        self.assertEqual(dict(os.environ), {"SEC006B_EXISTING": "environment"})

    def test_missing_explicit_file_does_not_load_another_env(self):
        self.assertFalse(load_dotenv(self.directory / "missing.env"))
        self.assertEqual(dict(os.environ), {})

    def test_disable_flag_prevents_reading_even_an_explicit_file(self):
        path = self._file("SEC006B_SHOULD_NOT_LOAD=synthetic\n")
        os.environ["PYTHON_DOTENV_DISABLED"] = "1"
        self.assertFalse(load_dotenv(path))
        self.assertNotIn("SEC006B_SHOULD_NOT_LOAD", os.environ)


@unittest.skipUnless(os.name == "posix", "O probe de filesystem exige POSIX.")
class DotenvAtomicWriteSecurityTests(unittest.TestCase):
    def test_cross_device_failure_never_copies_through_a_symlink(self):
        # Antes da correção, um rename EXDEV levava shutil.move ao fallback
        # de cópia, que seguia o symlink. Todos os caminhos aqui são privados.
        with tempfile.TemporaryDirectory(prefix="nexo-sec006b-rewrite-") as work:
            for operation in ("set", "unset"):
                with self.subTest(operation=operation):
                    directory = Path(work) / operation
                    directory.mkdir(mode=0o700)
                    target = directory / "synthetic-target"
                    original = b"SEC006B_KEEP=original\nSEC006B_REMOVE=present\n"
                    target.write_bytes(original)
                    target.chmod(0o600)
                    link = directory / ".env.synthetic"
                    link.symlink_to(target.name)
                    error = OSError(errno.EXDEV, "Synthetic cross-device operation")
                    with patch("os.rename", side_effect=error), \
                            patch("os.replace", side_effect=error):
                        with self.assertRaises(OSError):
                            if operation == "set":
                                set_key(link, "SEC006B_KEEP", "changed")
                            else:
                                unset_key(link, "SEC006B_REMOVE")
                    self.assertEqual(target.read_bytes(), original)
                    self.assertTrue(link.is_symlink())
                    self.assertEqual(set(directory.iterdir()), {target, link})

    def test_regular_file_updates_keep_private_permissions_and_valid_contents(self):
        with tempfile.TemporaryDirectory(prefix="nexo-sec006b-private-env-") as work:
            path = Path(work) / ".env.synthetic"
            path.write_text("SEC006B_KEEP=original\n", encoding="utf-8")
            path.chmod(0o600)
            self.assertTrue(set_key(path, "SEC006B_NEW", "synthetic value")[0])
            self.assertTrue(unset_key(path, "SEC006B_KEEP")[0])
            self.assertEqual(dotenv_values(path), {"SEC006B_NEW": "synthetic value"})
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)


CONFIG_PROBE = r"""
import contextlib
import io
import os
from pathlib import Path
import socket
import sys

root, fixture, instance, mode = map(str, sys.argv[1:])
sys.path.insert(0, root)
import dotenv
real_load = dotenv.load_dotenv
loads = []
def synthetic_load(path, *args, **kwargs):
    assert Path(path) == Path(root) / '.env', 'Unexpected config dotenv path'
    loads.append(True)
    return real_load(fixture, *args, **kwargs)
dotenv.load_dotenv = synthetic_load
def no_network(*args, **kwargs):
    raise AssertionError('Network prohibited in the dotenv compatibility test')
socket.socket.connect = no_network
socket.socket.connect_ex = no_network
socket.create_connection = no_network

captured_out, captured_err = io.StringIO(), io.StringIO()
with contextlib.redirect_stdout(captured_out), contextlib.redirect_stderr(captured_err):
    import app as application_module
    original_flask = application_module.Flask
    application_module.Flask = lambda *a, **kw: original_flask(*a, instance_path=instance, **kw)
    if mode == 'production':
        from wsgi import app
    else:
        app = application_module.create_app('development')
        if mode == 'testing':
            app.config['TESTING'] = True
    assert len(loads) == 1, 'Config did not use the explicit dotenv loader exactly once'
    assert os.environ.get('SEC006B_FROM_FILE') == 'synthetic-file-loaded'
    assert app.config['SECRET_KEY'] == os.environ['SEC006B_EXPECTED_SECRET']
    assert app.config['MAX_CONTENT_LENGTH'] == 3 * 1024 * 1024
    assert app.config['PROXY_FIX_HOPS'] == 1
    assert app.config['WTF_CSRF_ENABLED']
    if mode == 'production':
        assert not app.debug
        assert app.config['SESSION_COOKIE_SECURE']
        assert app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgresql+psycopg2://')
    else:
        assert app.debug
        assert app.config['SQLALCHEMY_DATABASE_URI'] == 'sqlite:///:memory:'
        assert app.testing == (mode == 'testing')
    client = app.test_client()
    # SEC-005: em produção TRUSTED_HOSTS passa a valer, então a requisição chega
    # com o host canônico (como o Render roteia); em dev não há restrição de host.
    host_headers = {'Host': 'nexo-sintetico.example.invalid'} if mode == 'production' else {}
    health = client.get('/healthz', headers=host_headers)
    login = client.get('/auth/login', headers=host_headers)
    assert health.status_code == login.status_code == 200
    assert b'csrf_token' in login.data
    assert app.config['SECRET_KEY'].encode() not in login.data
assert os.environ['SEC006B_EXPECTED_SECRET'] not in captured_out.getvalue()
assert os.environ['SEC006B_EXPECTED_SECRET'] not in captured_err.getvalue()
"""


class NexoDotenvConfigurationTests(unittest.TestCase):
    def _probe(self, mode, *, environment_precedence=False):
        with tempfile.TemporaryDirectory(prefix="nexo-sec006b-config-") as work:
            directory = Path(work)
            fixture = directory / ".env.synthetic"
            file_secret = secrets.token_hex(32)
            expected_secret = secrets.token_hex(32) if environment_precedence else file_secret
            database = ("postgresql://127.0.0.1/sec006b_synthetic_no_connection"
                        if mode == "production" else "sqlite:///:memory:")
            fixture.write_text(
                f"SECRET_KEY={file_secret}\nDATABASE_URL={database}\n"
                f"UPLOAD_FOLDER={directory / 'uploads'}\n"
                # SEC-005: produção exige origem canônica https (no Render vem de
                # RENDER_EXTERNAL_URL). Valor sintético para a factory validar.
                "NEXO_PUBLIC_URL=https://nexo-sintetico.example.invalid\n"
                "SEC006B_FROM_FILE=synthetic-file-loaded\n"
                "MAX_CONTENT_LENGTH_MB=3\nPROXY_FIX_HOPS=1\n"
                "RATELIMIT_STORAGE_URI=memory://\n"
                "MAIL_USERNAME=\nMAIL_PASSWORD=\nBREVO_API_KEY=\n"
                "ANTHROPIC_API_KEY=\nHF_API_TOKEN=\n",
                encoding="utf-8",
            )
            fixture.chmod(0o600)
            # Somente variáveis de plataforma necessárias ao processo; nenhum
            # segredo, configuração libpq, proxy ou credencial é herdado.
            allowed = {"PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "SYSTEMDRIVE"}
            environment = {key: value for key, value in os.environ.items() if key.upper() in allowed}
            environment.update({
                "FLASK_ENV": "production" if mode == "production" else "development",
                "NEXO_DB_DIRECT": "0", "DIRECT_URL": "",
                "SEC006B_EXPECTED_SECRET": expected_secret,
            })
            if environment_precedence:
                environment["SECRET_KEY"] = expected_secret
            result = subprocess.run(
                [sys.executable, "-I", "-B", "-c", CONFIG_PROBE,
                 str(ROOT), str(fixture), str(directory / "instance"), mode],
                cwd=directory, env=environment, capture_output=True,
                text=True, encoding="utf-8", timeout=30,
            )
            self.assertTrue(file_secret not in result.stdout + result.stderr,
                            "O processo imprimiu um segredo sintético; saída omitida.")
            self.assertTrue(expected_secret not in result.stdout + result.stderr,
                            "O processo imprimiu um segredo sintético; saída omitida.")
            self.assertEqual(result.returncode, 0,
                             "Subprocesso de configuração sintética falhou; saída privada omitida.")

    def test_development_configuration_loads_only_the_synthetic_env(self):
        self._probe("development")

    def test_existing_environment_secret_overrides_synthetic_file(self):
        self._probe("development", environment_precedence=True)

    def test_testing_configuration_keeps_csrf_with_the_updated_loader(self):
        self._probe("testing")

    def test_production_wsgi_loads_synthetic_configuration_without_network(self):
        self._probe("production")


if __name__ == "__main__":
    unittest.main()
