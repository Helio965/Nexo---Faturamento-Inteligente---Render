"""SEC-006: Gunicorn/WSGI de produção simulada, só loopback e PostgreSQL privado."""

import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

from sqlalchemy import URL

from .postgresql_support import PrivatePostgreSQL


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = """
import os
import dotenv
dotenv.load_dotenv = lambda *a, **kw: False
import app as application_module
original_flask = application_module.Flask
application_module.Flask = lambda *a, **kw: original_flask(
    *a, instance_path=os.environ['NEXO_SEC006_INSTANCE'], **kw
)
from gunicorn.app.wsgiapp import run
run()
"""


@unittest.skipUnless(
    os.name == "posix" and os.environ.get("NEXO_TEST_POSTGRES_BIN"),
    "Gunicorn simulado exige POSIX e os binários do PostgreSQL privado de teste.",
)
class DependencyProductionRuntimeTests(unittest.TestCase):
    def test_production_wsgi_gunicorn_health_database_and_secure_login_cookie(self):
        # O helper exclui credenciais/conexões do ambiente e cria Unix socket
        # privado. Nenhuma URL de serviço existente é aceita como entrada.
        cluster = PrivatePostgreSQL()
        self.addCleanup(cluster.close)
        database = cluster.create_database()
        self.addCleanup(cluster.drop_database, database)
        with tempfile.TemporaryDirectory(prefix="nexo-sec006-wsgi-") as temporary:
            work = Path(temporary)
            environment = cluster.environment.copy()
            # URL.set(host=None) preserva o host anterior. Criar explicitamente
            # a URI evita serializar o caminho Unix como hostname de uma URI.
            url = URL.create(
                "postgresql+psycopg2", username=cluster.username, database=database,
                query={"host": str(cluster.socket), "port": str(cluster.port)},
            )
            environment.update({
                "FLASK_ENV": "production", "PYTHON_DOTENV_DISABLED": "1",
                "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1",
                "SECRET_KEY": secrets.token_hex(32),
                "DATABASE_URL": url.render_as_string(hide_password=False),
                "DIRECT_URL": "", "NEXO_DB_DIRECT": "0",
                # SEC-005: produção exige origem canônica https (no Render vem de
                # RENDER_EXTERNAL_URL); valor sintético para a factory validar.
                "NEXO_PUBLIC_URL": "https://nexo-sintetico.example.invalid",
                # O único cliente deste ensaio é o loopback: host extra confiável,
                # como um operador configuraria (TRUSTED_HOSTS ignora a porta).
                "NEXO_TRUSTED_HOSTS": "127.0.0.1",
                "PGPASSFILE": str(cluster.passfile),
                "UPLOAD_FOLDER": str(work / "uploads"),
                "NEXO_SEC006_INSTANCE": str(work / "instance"),
                "PROXY_FIX_HOPS": "1", "RATELIMIT_STORAGE_URI": "memory://",
                "BREVO_API_KEY": "", "MAIL_USERNAME": "", "MAIL_PASSWORD": "",
                "ANTHROPIC_API_KEY": "", "HF_API_TOKEN": "",
            })
            # A porta permanece reservada; Gunicorn herda o listener, sem corrida
            # entre escolher a porta e bind. Somente 127.0.0.1 é exposto.
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
                listener.bind(("127.0.0.1", 0))
                listener.listen(8)
                port = listener.getsockname()[1]
                process = subprocess.Popen(
                    [sys.executable, "-B", "-c", BOOTSTRAP,
                     "--workers", "1", "--threads", "50", "--timeout", "20",
                     "--bind", f"fd://{listener.fileno()}",
                     "--access-logfile", os.devnull,
                     "--error-logfile", str(work / "gunicorn.log"), "wsgi:app"],
                    cwd=ROOT, env=environment, pass_fds=(listener.fileno(),),
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, start_new_session=True,
                )
                try:
                    base = f"http://127.0.0.1:{port}"
                    # O ambiente do helper não herda proxies ou serviços externos.
                    opener = urllib.request.build_opener()
                    ready = False
                    deadline = time.monotonic() + 25
                    while time.monotonic() < deadline:
                        if process.poll() is not None:
                            self.fail("Gunicorn encerrou antes do health check; logs privados omitidos.")
                        try:
                            with opener.open(base + "/healthz", timeout=0.5) as response:
                                ready = response.status == 200 and b'"ok"' in response.read()
                            if ready:
                                break
                        except (OSError, urllib.error.URLError):
                            time.sleep(0.05)
                    self.assertTrue(ready, "Gunicorn não confirmou inicialização no prazo.")
                    with opener.open(base + "/healthz/db", timeout=5) as response:
                        self.assertEqual(response.status, 200)
                        self.assertIn(b'"db":"ok"', response.read())
                    request = urllib.request.Request(base + "/auth/login", headers={
                        "X-Forwarded-Proto": "https",
                    })
                    with opener.open(request, timeout=5) as response:
                        self.assertEqual(response.status, 200)
                        cookie = response.headers.get("Set-Cookie", "")
                        self.assertIn("Secure", cookie)
                        self.assertIn("HttpOnly", cookie)
                        self.assertIn("SameSite=Lax", cookie)
                        self.assertIn("Cookie", response.headers.get("Vary", ""))
                finally:
                    if process.poll() is None:
                        os.killpg(process.pid, signal.SIGTERM)
                        try:
                            process.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            os.killpg(process.pid, signal.SIGKILL)
                            process.wait(timeout=5)
