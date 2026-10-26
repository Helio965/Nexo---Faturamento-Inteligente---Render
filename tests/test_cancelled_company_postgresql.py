"""NEXO-AJ-06.1: cancelamento de empresa com locks reais de PostgreSQL.

Por padrão o ensaio é ignorado. Para habilitar, indique apenas o diretório dos
binários PostgreSQL em NEXO_TEST_POSTGRES_BIN e execute:
    python -B -m unittest tests.test_cancelled_company_postgresql -v

Um processo separado, com ambiente filtrado e dotenv desabilitado, inicializa
seu próprio cluster temporário (porta aleatória em 127.0.0.1, sem socket Unix)
e aplica as migrações reais. Nenhum banco ou servidor existente é usado.
"""

import contextlib
from datetime import date
import io
import json
import os
from pathlib import Path
import re
import secrets
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ("initdb", "pg_ctl", "createdb")
SAFE_ENV_KEYS = {
    "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "SYSTEMDRIVE",
    "TEMP", "TMP", "USERPROFILE", "LOCALAPPDATA", "APPDATA", "PROGRAMFILES",
    "PROGRAMFILES(X86)", "PROCESSOR_ARCHITECTURE", "NUMBER_OF_PROCESSORS",
}
CHECKS = (
    "private_engine", "migrations", "active_login", "suspended_keeps_generation",
    "suspended_keeps_session", "failed_commit_rolls_back_status_and_generation",
    "delivery_holds_share_lock", "cancel_waits_for_share_lock", "delivery_before_commit_was_authorized",
    "generation_incremented", "status_cancelled", "later_delivery_denied", "old_session_denied",
    "cancelled_login_denied", "other_company_kept", "admin_kept", "repeated_cancel_no_new_revocation",
    "reactivation_revokes_again", "old_cookie_stays_invalid", "new_login_after_reactivation",
)
PASSWORD = "Synthetic-pg-password-061!"


def _safe_environment():
    """Nunca herdar DATABASE_URL, PGSERVICE, PGPASSWORD ou chaves de serviços."""
    env = {key: value for key, value in os.environ.items() if key.upper() in SAFE_ENV_KEYS}
    env.update({"PYTHONUTF8": "1", "FLASK_ENV": "development", "NEXO_DB_DIRECT": "0"})
    return env


def _tool(bin_dir, name):
    return bin_dir / (name + (".exe" if os.name == "nt" else ""))


class PostgreSQLCancelledCompanyTests(unittest.TestCase):
    def test_cancellation_serializes_with_real_postgresql_locks(self):
        raw_bin = os.environ.get("NEXO_TEST_POSTGRES_BIN")
        if not raw_bin:
            self.skipTest("Defina NEXO_TEST_POSTGRES_BIN para criar um cluster PostgreSQL temporário isolado.")
        self.assertTrue("://" not in raw_bin and Path(raw_bin).is_absolute(),
                        "NEXO_TEST_POSTGRES_BIN aceita apenas um caminho local absoluto; URLs são recusadas.")
        try:
            bin_dir = Path(raw_bin).resolve(strict=True)
        except (OSError, ValueError):
            self.fail("NEXO_TEST_POSTGRES_BIN não indica um diretório local acessível; valor omitido.")
        self.assertTrue(all(_tool(bin_dir, tool).is_file() for tool in TOOLS),
                        "O diretório precisa conter initdb, pg_ctl e createdb.")
        with tempfile.TemporaryDirectory(prefix="nexo-aj061-pg-") as work:
            work_dir = Path(work).resolve()
            data_dir = work_dir / "private-cluster"
            try:
                result = subprocess.run(
                    [sys.executable, "-B", str(Path(__file__).resolve()), "--isolated-worker", str(bin_dir), str(work_dir)],
                    cwd=str(ROOT), env=_safe_environment(), capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=180, check=False,
                )
            except subprocess.TimeoutExpired:
                self.fail("O ensaio isolado excedeu 180 segundos; nenhuma saída ou credencial foi exibida.")
            finally:
                self.assertTrue(data_dir.resolve().is_relative_to(work_dir))
                if (data_dir / "postmaster.pid").is_file():
                    subprocess.run(
                        [str(_tool(bin_dir, "pg_ctl")), "--pgdata", str(data_dir), "--mode", "fast",
                         "--wait", "--timeout", "20", "stop"],
                        env=_safe_environment(), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL, timeout=30, check=False,
                    )
        try:
            report = json.loads(result.stdout)
        except (json.JSONDecodeError, TypeError):
            self.fail("O processo isolado não produziu um relatório seguro válido; saídas brutas omitidas.")
        self.assertEqual(result.returncode, 0,
                         f"Ensaio isolado falhou na etapa {report.get('stage', 'desconhecida')} "
                         f"({report.get('error', 'erro não identificado')}); saídas brutas omitidas.")
        self.assertEqual(report.get("status"), "ok")
        self.assertEqual(sorted(report.get("checks", [])), sorted(CHECKS))
        self.assertFalse(report.get("production_access"))
        print("\nEnsaio PostgreSQL AJ-06.1: " + json.dumps(report, ensure_ascii=True, sort_keys=True))


class _PrivateCluster:
    """Auxiliar do processo isolado; não é um caso descoberto pelo unittest."""

    def __init__(self, bin_dir, work_dir):
        self.bin_dir, self.work_dir = bin_dir, work_dir
        self.env = _safe_environment()
        self.env["PATH"] = str(bin_dir) + os.pathsep + self.env.get("PATH", "")
        self.stage = "preparação"
        self.checks = []

    def command(self, name, *args):
        if name not in TOOLS:
            raise RuntimeError("Utilitário não permitido")
        try:
            result = subprocess.run([str(_tool(self.bin_dir, name)), *map(str, args)], env=self.env,
                                    cwd=str(self.work_dir), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, timeout=60, check=False)
        except (OSError, subprocess.TimeoutExpired):
            raise RuntimeError("Utilitário local indisponível ou excedeu o limite") from None
        if result.returncode:
            raise RuntimeError("Utilitário PostgreSQL retornou erro; saída omitida")

    def check(self, name, condition):
        if not condition:
            raise AssertionError(name)
        self.checks.append(name)

    def run(self):
        if any(self.work_dir.iterdir()):
            raise RuntimeError("A pasta de trabalho precisa começar vazia")
        data_dir = self.work_dir / "private-cluster"
        user = "nexo_aj061_" + secrets.token_hex(4)
        secret = secrets.token_urlsafe(24)
        # Apenas a porta é descoberta; nunca procura/conecta a servidores existentes.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as reserve:
            reserve.bind(("127.0.0.1", 0))
            port = reserve.getsockname()[1]
        password_file = self.work_dir / "init-password"
        password_file.write_text(secret + "\n", encoding="utf-8")
        password_file.chmod(0o600)
        self.stage = "initdb privado"
        self.command("initdb", "--pgdata", data_dir, "--username", user, "--pwfile", password_file,
                     "--auth", "scram-sha-256", "--encoding", "UTF8", "--locale", "C")
        password_file.unlink()
        with (data_dir / "postgresql.conf").open("a", encoding="utf-8") as config:
            config.write(f"\nlisten_addresses = '127.0.0.1'\nport = {port}\nunix_socket_directories = ''\n")
        self.env.update({"PGHOST": "127.0.0.1", "PGPORT": str(port), "PGUSER": user,
                         "PGPASSWORD": secret, "PGCONNECT_TIMEOUT": "5", "PGSSLMODE": "disable"})
        started = False
        app = None
        try:
            self.stage = "início do cluster privado"
            self.command("pg_ctl", "--pgdata", data_dir, "--log", self.work_dir / "postgres.log",
                         "--wait", "--timeout", "30", "start")
            started = True
            self.command("createdb", "--no-password", "--template=template0", "--encoding=UTF8", "nexo_aj061")
            app = self.scenarios(user, secret, port)
            return {"status": "ok", "checks": self.checks, "production_access": False}
        finally:
            if app is not None:
                with app.app_context():
                    from extensions import db
                    db.session.remove()
                    db.engine.dispose()
            if started or (data_dir / "postmaster.pid").exists():
                self.command("pg_ctl", "--pgdata", data_dir, "--mode", "fast", "--wait", "--timeout", "30", "stop")

    def scenarios(self, user, secret, port):
        self.stage = "migrações reais no banco fictício"
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        with patch.dict(os.environ, {k: v for k, v in self.env.items() if not k.startswith("PG")}, clear=True), \
                patch("dotenv.load_dotenv", return_value=False):
            from flask import Flask, jsonify
            from flask_login import current_user, login_required
            from flask_migrate import upgrade
            from sqlalchemy import URL, event, select
            from sqlalchemy.exc import SQLAlchemyError
            from sqlalchemy.orm import Session
            from config import DevelopmentConfig
            import app as app_module
            uri = URL.create("postgresql+psycopg2", username=user, password=secret,
                             host="127.0.0.1", port=port, database="nexo_aj061")
            values = {
                "SQLALCHEMY_DATABASE_URI": uri, "SQLALCHEMY_DIRECT_URI": uri,
                "SQLALCHEMY_ENGINE_OPTIONS": {"pool_pre_ping": True, "connect_args": {
                    "connect_timeout": 5, "options": "-c statement_timeout=15000 -c lock_timeout=8000"}},
                "DEBUG": False, "SQLALCHEMY_ECHO": False, "TESTING": True, "SECRET_KEY": secrets.token_hex(32),
                "UPLOAD_FOLDER": self.work_dir / "uploads", "MAIL_ATIVO": False, "MAIL_SUPPRESS_SEND": True,
                "BREVO_API_KEY": None, "ANTHROPIC_API_KEY": None, "HF_API_TOKEN": None,
                "RATELIMIT_ENABLED": False, "RATELIMIT_STORAGE_URI": "memory://", "PROXY_FIX_HOPS": 0,
            }
            with contextlib.ExitStack() as stack:
                for key, value in values.items():
                    stack.enter_context(patch.object(DevelopmentConfig, key, value, create=True))
                stack.enter_context(patch.object(app_module, "Flask", side_effect=lambda *a, **kw: Flask(
                    *a, instance_path=str(self.work_dir / "instance"), **kw)))
                app = app_module.create_app("development")

            @login_required
            def protected():
                return jsonify(private="synthetic-private-data", uid=current_user.id_usuario)
            app.add_url_rule("/_aj061/protected", "aj061_protected", protected)

            from extensions import db
            from models import Empresa, Plano, Segmento, Usuario
            from session_security import usuario_pode_acessar
            with app.app_context():
                url = db.engine.url
                self.check("private_engine", url.get_backend_name() == "postgresql"
                           and (url.host, url.port) == ("127.0.0.1", port))
                upgrade(directory=str(ROOT / "migrations"))
                self.checks.append("migrations")
                self.stage = "fixtures fictícias"
                plan = Plano(nome_plano="BRONZE", valor_mensal=100, qtd_analises_mes=1,
                             tipo_analise_permitida="MENSAL", nivel_entrega_analise="BASICA",
                             nivel_dashboard="RESUMIDO", nivel_atendimento="BAIXO")
                segment = Segmento(nome_segmento="AJ-06.1 sintético")
                db.session.add_all([plan, segment])
                db.session.flush()
                companies = [Empresa(id_segmento=segment.id_segmento, id_plano_atual=plan.id_plano,
                                     cnpj=f"0000000000006{i}", razao_social=f"Empresa sintética {i}",
                                     email_contato=f"empresa{i}@example.invalid", data_contratacao=date(2026, 1, 1))
                             for i in (1, 2)]
                db.session.add_all(companies)
                db.session.flush()
                users = {
                    "client": Usuario(nome="Cliente", email="client@example.invalid", role="CLIENTE",
                                      id_empresa=companies[0].id_empresa, primeiro_acesso=False),
                    "other": Usuario(nome="Outro", email="other@example.invalid", role="CLIENTE",
                                     id_empresa=companies[1].id_empresa, primeiro_acesso=False),
                    "admin": Usuario(nome="Admin", email="admin@example.invalid", role="ADMIN", primeiro_acesso=False),
                }
                for account in users.values():
                    account.set_senha(PASSWORD)
                db.session.add_all(users.values())
                db.session.commit()
                ids = {name: account.id_usuario for name, account in users.items()}
                company_id = companies[0].id_empresa

            def csrf(client, path="/auth/login"):
                page = client.get(path).get_data(as_text=True)
                return re.search(r'name="csrf_token"[^>]*value="([^"]+)"', page).group(1)

            def login(name):
                client = app.test_client()
                response = client.post("/auth/login", data={"email": f"{name}@example.invalid", "senha": PASSWORD,
                                                            "csrf_token": csrf(client)})
                return client, response

            def generation(name):
                with app.app_context():
                    return db.session.get(Usuario, ids[name]).geracao_autorizacao

            def status():
                with app.app_context():
                    return db.session.get(Empresa, company_id).status_conta

            admin, _ = login("admin")

            def set_status(value):
                path = f"/admin/empresas/{company_id}/editar"
                with app.app_context():
                    company = db.session.get(Empresa, company_id)
                    data = {"id_segmento": company.id_segmento, "id_plano_atual": company.id_plano_atual,
                            "razao_social": company.razao_social, "email_contato": company.email_contato,
                            "data_contratacao": company.data_contratacao.isoformat(), "status_conta": value,
                            "status_conta_exibido": company.status_conta}
                data["csrf_token"] = csrf(admin, path)
                return admin.post(path, data=data)

            self.stage = "cenários"
            client, response = login("client")
            self.check("active_login", response.status_code == 302
                       and client.get("/_aj061/protected").status_code == 200)
            start = generation("client")
            self.check("suspended_keeps_generation",
                       set_status("SUSPENSA").status_code == 302 and generation("client") == start)
            self.check("suspended_keeps_session", client.get("/_aj061/protected").status_code == 200)
            set_status("ATIVA")

            # Rollback real: a segunda escrita falha depois da primeira já enviada.
            sent = []
            def fail_second_update(conn, cursor, statement, parameters, context, executemany):
                if statement.lstrip().upper().startswith("UPDATE"):
                    sent.append(statement)
                    if len(sent) == 2:
                        raise SQLAlchemyError("synthetic failure")
            with app.app_context():
                engine = db.engine
            event.listen(engine, "before_cursor_execute", fail_second_update)
            try:
                set_status("CANCELADA")
            finally:
                event.remove(engine, "before_cursor_execute", fail_second_update)
            self.check("failed_commit_rolls_back_status_and_generation", len(sent) == 2
                       and status() == "ATIVA" and generation("client") == start
                       and client.get("/_aj061/protected").status_code == 200)

            # Entrega autorizada segurando FOR SHARE: o cancelamento espera seu fim.
            hold, locked, observed = 1.5, threading.Event(), {}
            def delivery():
                with app.app_context():
                    with Session(bind=db.engine) as query:
                        account = query.scalar(select(Usuario).where(
                            Usuario.id_usuario == ids["client"]).with_for_update(read=True))
                        observed["authorized"] = usuario_pode_acessar(account, consulta=query)
                        locked.set()
                        time.sleep(hold)
                        observed["released"] = time.monotonic()
                        query.commit()
            worker = threading.Thread(target=delivery)
            worker.start()
            self.check("delivery_holds_share_lock", locked.wait(10))
            begin = time.monotonic()
            response = set_status("CANCELADA")
            end = time.monotonic()
            worker.join(10)
            self.check("cancel_waits_for_share_lock", response.status_code == 302
                       and end - begin >= hold * 0.8 and end >= observed.get("released", end + 1))
            self.check("delivery_before_commit_was_authorized", observed.get("authorized") is True)
            self.check("generation_incremented", generation("client") == start + 1)
            self.check("status_cancelled", status() == "CANCELADA")
            with app.app_context():
                with Session(bind=db.engine) as query:
                    account = query.scalar(select(Usuario).where(
                        Usuario.id_usuario == ids["client"]).with_for_update(read=True))
                    self.check("later_delivery_denied", usuario_pode_acessar(account, consulta=query) is False)
                    query.rollback()
            old = client.get("/_aj061/protected")
            self.check("old_session_denied", old.status_code == 302
                       and "/auth/login" in old.headers.get("Location", ""))
            relogin, response = login("client")
            self.check("cancelled_login_denied", response.status_code == 200
                       and "desativada" in response.get_data(as_text=True)
                       and relogin.get("/_aj061/protected").status_code == 302)
            other, response = login("other")
            self.check("other_company_kept", response.status_code == 302
                       and other.get("/_aj061/protected").status_code == 200)
            self.check("admin_kept", admin.get("/admin/empresas").status_code == 200 and generation("admin") == 0)
            self.check("repeated_cancel_no_new_revocation",
                       set_status("CANCELADA").status_code == 302 and generation("client") == start + 1)
            self.check("reactivation_revokes_again",
                       set_status("ATIVA").status_code == 302 and generation("client") == start + 2)
            self.check("old_cookie_stays_invalid", client.get("/_aj061/protected").status_code == 302)
            fresh, response = login("client")
            self.check("new_login_after_reactivation", response.status_code == 302
                       and fresh.get("/_aj061/protected").status_code == 200)
            return app


def _worker_main(bin_dir, work_dir):
    cluster = _PrivateCluster(Path(bin_dir).resolve(), Path(work_dir).resolve())
    # Não encaminha mensagens de Flask, SQLAlchemy, Alembic ou PostgreSQL.
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            report = cluster.run()
    except Exception as error:
        detail = f": {error}" if isinstance(error, AssertionError) else ""
        print(json.dumps({"status": "error", "stage": cluster.stage, "error": type(error).__name__ + detail}))
        return 1
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--isolated-worker":
        raise SystemExit(_worker_main(sys.argv[2], sys.argv[3]))
    unittest.main()
