"""Homologação SEC-002 em PostgreSQL local, separada do discovery SQLite.

Executar explicitamente (não há skip silencioso se os binários faltarem):
    NEXO_TEST_POSTGRES_BIN=/caminho/local/bin python -B -m unittest tests.postgresql_auth_tokens -v

Reutiliza os cenários existentes sem duplicar seus corpos nem alterar a suíte
SQLite. Só a preparação muda: cada caso recebe banco próprio em cluster privado,
sem TCP, sem .env/servidor existente e sem envio de e-mail.
"""

import contextlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from flask import Flask
from sqlalchemy import event, text
from werkzeug.security import check_password_hash

from . import test_auth_tokens_security as token_cases
from .postgresql_support import PrivatePostgreSQL
from blueprints import auth, admin
from extensions import db


class PostgreSQLAuthTokenSecurityTests(token_cases.AuthTokenSecurityTests):
    @classmethod
    def setUpClass(cls):
        cls.postgresql = PrivatePostgreSQL()
        cls.addClassCleanup(cls.postgresql.close)

    def setUp(self):
        self.work = tempfile.TemporaryDirectory(prefix="nexo-pg-token-app-")
        self.addCleanup(self.work.cleanup)
        self.root = Path(self.work.name)
        self.database = self.postgresql.create_database()
        self.addCleanup(self.postgresql.drop_database, self.database)
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        for target in ("socket.socket.connect", "socket.socket.connect_ex", "socket.create_connection"):
            self.stack.enter_context(patch(target, side_effect=AssertionError("Rede externa proibida")))
        with patch("dotenv.load_dotenv", return_value=False):
            import app as app_module
            from config import DevelopmentConfig
        uri = self.postgresql.url(self.database)
        values = {
            "SECRET_KEY": "isolated-postgresql-token-security-key",
            "SQLALCHEMY_DATABASE_URI": uri, "SQLALCHEMY_DIRECT_URI": uri,
            "SQLALCHEMY_ENGINE_OPTIONS": {"pool_pre_ping": True, "connect_args": {
                "connect_timeout": 5, "password": "", "passfile": str(self.postgresql.passfile),
                "options": "-c statement_timeout=15000 -c lock_timeout=10000",
            }},
            "UPLOAD_FOLDER": self.root / "uploads", "DEBUG": False,
            "SQLALCHEMY_ECHO": False, "TESTING": True,
            "MAIL_ATIVO": False, "MAIL_SUPPRESS_SEND": True,
            "MAIL_USERNAME": None, "MAIL_PASSWORD": None,
            "BREVO_API_KEY": None, "ANTHROPIC_API_KEY": None, "HF_API_TOKEN": None,
            "RATELIMIT_ENABLED": False, "PROXY_FIX_HOPS": 0,
        }
        with contextlib.ExitStack() as configuration:
            for key, value in values.items():
                configuration.enter_context(patch.object(DevelopmentConfig, key, value, create=True))
            configuration.enter_context(patch.object(
                app_module, "Flask", side_effect=lambda *a, **kw: Flask(
                    *a, instance_path=str(self.root / "instance"), **kw,
                ),
            ))
            self.app = app_module.create_app("development")
        for attribute, module, name in (
            ("recovery_mail", auth, "email_recuperacao_senha"),
            ("activation_mail", auth, "email_boas_vindas"),
            ("registration_mail", admin, "email_boas_vindas"),
        ):
            setattr(self, attribute, self.stack.enter_context(patch.object(module, name, return_value=True)))
        self.stack.enter_context(patch.object(auth.logger, "disabled", False))
        with self.app.app_context():
            self.engine = db.engine
            self.assertEqual(self.engine.url.get_backend_name(), "postgresql")
            self.assertEqual(self.engine.url.host, str(self.postgresql.socket))
            self.assertEqual(self.engine.url.database, self.database)
            self.assertEqual(db.session.scalar(text("SHOW transaction_isolation")), "read committed")
            self.assertIsNone(db.session.scalar(text("SELECT inet_server_addr()")))
            db.create_all()
            self._fixtures()
        self.addCleanup(self._dispose)
        self.client = self.app.test_client()

    def test_real_postgresql_statement_error_rolls_back_and_allows_retry(self):
        """O servidor, não um mock SQLAlchemy, aborta a transação do UPDATE."""
        token = self._token()
        csrf = self._csrf()
        failed = []

        def fail_once(connection, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith("UPDATE USUARIO SET") and not failed:
                failed.append(True)
                # Erro real do PostgreSQL coloca a transação em estado abortado.
                cursor.execute("SELECT 1 / 0")

        event.listen(self.engine, "before_cursor_execute", fail_once)
        try:
            with self.assertLogs(auth.logger, level="WARNING") as captured:
                self._assert_rejected(self._post(token, csrf=csrf))
        finally:
            event.remove(self.engine, "before_cursor_execute", fail_once)
        self.assertEqual(failed, [True])
        self.assertNotIn(token, "\n".join(captured.output))
        self.assertNotIn("SELECT", "\n".join(captured.output))
        self.assertEqual(self._account()[0], token_cases.FIXTURE_HASH)
        self._assert_success(self._post(token))
        self.assertTrue(check_password_hash(self._account()[0], token_cases.NEW_PASSWORD))
        self._assert_rejected(self._post(token))

    def test_concurrent_credential_update_does_not_overwrite_newer_password(self):
        """Credencial muda depois da validação, em outra transação PostgreSQL."""
        with self.app.app_context():
            state = auth._ler_token_reset(self._token())
            from sqlalchemy import update
            from models import Usuario
            from werkzeug.security import generate_password_hash
            newer = generate_password_hash("Synthetic-concurrent-new-password-789!")
            with self.engine.begin() as connection:
                connection.execute(update(Usuario).where(
                    Usuario.id_usuario == self.ids["active"],
                ).values(senha_hash=newer))
            self.assertFalse(auth._atualizar_credencial(state, token_cases.NEW_PASSWORD))
        self.assertEqual(self._account()[0], newer)


class PostgreSQLIsolationSafetyTests(unittest.TestCase):
    def test_poisoned_connection_environment_cannot_select_an_existing_server(self):
        """Os valores sentinela nunca chegam a libpq nem aos subprocessos."""
        poisoned = {
            "DATABASE_URL": "postgresql://synthetic:sentinel@192.0.2.1/external",
            "DIRECT_URL": "postgresql://synthetic:sentinel@192.0.2.1/external",
            "PGHOSTADDR": "192.0.2.1", "PGHOST": "external.invalid",
            "PGSERVICE": "nonexistent-private-test-sentinel",
            "PGSERVICEFILE": "/nonexistent-service-sentinel",
            "PGPASSFILE": "/nonexistent-password-sentinel",
            "PGPASSWORD": "private-test-password-sentinel",
        }
        with patch.dict(os.environ, poisoned):
            cluster = PrivatePostgreSQL()
            try:
                for key in poisoned:
                    self.assertNotIn(key, os.environ)
                    self.assertNotIn(key, cluster.environment)
                connection = cluster.connect()
                try:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT inet_server_addr(), current_user")
                        address, user = cursor.fetchone()
                    self.assertIsNone(address)
                    self.assertEqual(user, cluster.username)
                finally:
                    connection.close()
            finally:
                cluster.close()
            # Restaura o processo chamador apenas depois de fechar seu cluster.
            self.assertEqual(os.environ.get("PGSERVICE"), poisoned["PGSERVICE"])


# ---------------------------------------------------------------------------
# E-mails transacionais em PostgreSQL: os mesmos cenários de
# tests/test_emails_transacionais.py (cadastro, recuperação e e-mails com
# maiúsculas/minúsculas, inclusive registros legados conflitantes), com a
# comparação lower(email) e a unicidade executadas pelo servidor real.
# ---------------------------------------------------------------------------
from . import test_emails_transacionais as email_cases  # noqa: E402


class _TokenPostgreSQL(token_cases._TokenCase):
    """Só a preparação PostgreSQL (sem herdar os testes de tokens)."""

    @classmethod
    def setUpClass(cls):
        cls.postgresql = PrivatePostgreSQL()
        cls.addClassCleanup(cls.postgresql.close)

    def setUp(self):
        PostgreSQLAuthTokenSecurityTests.setUp(self)


class PostgreSQLCadastroEmpresaTests(email_cases.CadastroEmpresaTests, _TokenPostgreSQL):
    pass


class PostgreSQLRecuperacaoSenhaTests(email_cases.RecuperacaoSenhaTests, _TokenPostgreSQL):
    pass


class PostgreSQLMaiusculasMinusculasTests(email_cases.MaiusculasMinusculasTests, _TokenPostgreSQL):
    pass
