"""SEC-003 em PostgreSQL privado: execute explicitamente, sem DSN externo."""

from concurrent.futures import ThreadPoolExecutor
import threading
import time
from unittest.mock import patch

from flask import request
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session
from werkzeug.security import check_password_hash

from . import postgresql_auth_tokens as pg_cases
from . import test_auth_tokens_security as token_cases
from . import test_session_revocation_security as session_cases
from .postgresql_support import PrivatePostgreSQL
from extensions import db, socketio
from blueprints import auth
import notifications
import realtime


class PostgreSQLSessionRevocationSecurityTests(session_cases.SessionRevocationCases, token_cases._TokenCase):
    @classmethod
    def setUpClass(cls):
        cls.postgresql = PrivatePostgreSQL()
        cls.addClassCleanup(cls.postgresql.close)

    def setUp(self):
        pg_cases.PostgreSQLAuthTokenSecurityTests.setUp(self)
        self._session_routes()

    def _wait_for_update_to_be_blocked_by_read_lock(self):
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            with self.engine.connect() as connection:
                waiting = connection.scalar(text("""
                    SELECT count(*) FROM pg_stat_activity
                    WHERE datname = current_database() AND pid <> pg_backend_pid()
                      AND wait_event_type = 'Lock'
                      AND query ILIKE 'UPDATE usuario SET%'
                      AND cardinality(pg_blocking_pids(pid)) > 0
                """))
            if waiting:
                return
            threading.Event().wait(0.01)
        self.fail("O UPDATE real não demonstrou espera pelo lock PostgreSQL de autorização.")

    def _wait_for_blocked_statement(self, query_like):
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            with self.engine.connect() as connection:
                waiting = connection.scalar(text("""
                    SELECT count(*) FROM pg_stat_activity
                    WHERE datname = current_database() AND pid <> pg_backend_pid()
                      AND wait_event_type = 'Lock' AND query ILIKE :padrao
                      AND cardinality(pg_blocking_pids(pid)) > 0
                """), {"padrao": query_like})
            if waiting:
                return
            threading.Event().wait(0.01)
        self.fail(f"Nenhuma consulta {query_like!r} demonstrou espera pelo lock PostgreSQL.")

    def test_logout_waits_for_in_flight_delivery_and_later_deliveries_skip_the_session(self):
        """SEC-001: FOR UPDATE do logout espera a entrega (FOR SHARE) terminar;
        a sessão revogada deixa de ser destinatária de qualquer entrega posterior."""
        locked, release = threading.Event(), threading.Event()
        http = self._login_client()
        old_socket = self._socket(http)
        csrf = self._csrf(http, "/auth/logout")
        emitted = []
        original_emit = socketio.emit

        def recording_emit(*args, **kwargs):
            emitted.append((args[0], kwargs.get("room")))
            return original_emit(*args, **kwargs)

        def after(connection, cursor, statement, parameters, context, executemany):
            if "FOR SHARE" in statement.upper() and threading.current_thread().name.startswith("logout-race"):
                locked.set()
                if not release.wait(12):
                    raise AssertionError("Entrega de teste não foi liberada.")
        event.listen(self.engine, "after_cursor_execute", after)
        try:
            with patch.object(notifications.socketio, "emit", side_effect=recording_emit):
                with ThreadPoolExecutor(max_workers=2, thread_name_prefix="logout-race") as executor:
                    delivery = executor.submit(self._notify, text="AUTHORIZED_BEFORE_LOGOUT_COMMIT")
                    try:
                        self.assertTrue(locked.wait(8))
                        logout = executor.submit(http.post, "/auth/logout", data={"csrf_token": csrf})
                        self._wait_for_blocked_statement("SELECT%FOR UPDATE%")
                        self.assertEqual(self._session_rows(), [(False, None)])
                        self.assertEqual(emitted, [])
                    finally:
                        release.set()
                    delivery.result(timeout=12)
                    response = logout.result(timeout=12)
                self.assertEqual(response.status_code, 302)
        finally:
            release.set()
            event.remove(self.engine, "after_cursor_execute", after)
        self.assertEqual([name for name, _ in emitted], ["nova_notificacao"])
        self.assertEqual(self._session_rows(), [(True, "logout")])
        self.assertFalse(old_socket.is_connected())
        self._assert_private_denied(http)
        self._notify(text="PRIVATE_AFTER_LOGOUT")
        self.assertEqual(len(emitted), 1, "sessão revogada não pode ser destinatária")

    def test_notification_commit_delivers_with_single_connection_pool(self):
        """O despachante precisa aguardar a devolução da conexão do COMMIT."""
        with self.app.app_context():
            db.session.remove()
            previous = self.engine
            replacement = create_engine(
                previous.url, pool_size=1, max_overflow=0, pool_timeout=1,
                connect_args={
                    "connect_timeout": 5, "password": "", "passfile": str(self.postgresql.passfile),
                    "options": "-c statement_timeout=15000 -c lock_timeout=10000",
                },
            )
            # A extensão expõe o mapa de engines da aplicação. A troca afeta
            # somente este app/banco sintético e o cleanup dispõe o novo pool.
            db.engines[None] = replacement
            self.engine = replacement
            previous.dispose()
        connection = self._socket(self._login_client())
        self._notify(text="SINGLE_CONNECTION_POOL_PRIVATE")
        messages = self._received(connection)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["args"][0]["texto"], "SINGLE_CONNECTION_POOL_PRIVATE")

    def test_private_event_and_password_update_are_serialized_by_postgresql(self):
        entered, release_emit, enqueued, release_handler, update_attempted = (
            threading.Event() for _ in range(5)
        )
        def private_action():
            entered.set()
            if not release_emit.wait(12):
                raise AssertionError("Evento de teste não foi liberado.")
            socketio.emit("_security_private_probe", {"private": "AUTHORIZED_BEFORE_PASSWORD_COMMIT"},
                          to=request.sid)
            enqueued.set()
            if not release_handler.wait(12):
                raise AssertionError("Handler de teste não foi liberado.")
            return True
        socketio.on_event("_security_blocking_probe", realtime.guarded_socket_event(private_action))
        old_http = self._login_client()
        old_socket = self._socket(old_http)
        token = self._token()
        reset_client = self.app.test_client()
        csrf = self._csrf(reset_client)

        def before(connection, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith("UPDATE USUARIO SET"):
                update_attempted.set()
        event.listen(self.engine, "before_cursor_execute", before)
        try:
            with ThreadPoolExecutor(max_workers=2, thread_name_prefix="session-event-race") as executor:
                event_result = executor.submit(old_socket.emit, "_security_blocking_probe", callback=True)
                try:
                    self.assertTrue(entered.wait(8))
                    reset_result = executor.submit(self._post, token, client=reset_client, csrf=csrf)
                    self.assertTrue(update_attempted.wait(8))
                    self._wait_for_update_to_be_blocked_by_read_lock()
                    self.assertEqual(self._account()[0], token_cases.FIXTURE_HASH)
                    release_emit.set()
                    self.assertTrue(enqueued.wait(8))
                    self.assertIn("AUTHORIZED_BEFORE_PASSWORD_COMMIT", repr(self._received(old_socket)))
                    self.assertEqual(self._account()[0], token_cases.FIXTURE_HASH)
                finally:
                    release_emit.set()
                    release_handler.set()
                self.assertTrue(event_result.result(timeout=12))
                self._assert_success(reset_result.result(timeout=12))
        finally:
            release_emit.set()
            release_handler.set()
            event.remove(self.engine, "before_cursor_execute", before)
        self.assertTrue(check_password_hash(self._account()[0], token_cases.NEW_PASSWORD))
        self._assert_private_denied(old_http)
        self.assertFalse(old_socket.is_connected())
        self.assertFalse(self._socket(old_http).is_connected())
        self._assert_rejected(self._post(token, client=self.app.test_client()))

    def test_private_notification_holds_read_lock_until_emit_then_new_generation_excludes_old_socket(self):
        locked, release, update_attempted = threading.Event(), threading.Event(), threading.Event()
        old_socket = self._socket(self._login_client())
        token = self._token()
        reset_client = self.app.test_client()
        csrf = self._csrf(reset_client)

        def after(connection, cursor, statement, parameters, context, executemany):
            if "FOR SHARE" in statement.upper() and threading.current_thread().name.startswith("notification-race"):
                locked.set()
                if not release.wait(12):
                    raise AssertionError("Emissão de teste não foi liberada.")
        def before(connection, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith("UPDATE USUARIO SET"):
                update_attempted.set()
        event.listen(self.engine, "after_cursor_execute", after)
        event.listen(self.engine, "before_cursor_execute", before)
        try:
            with ThreadPoolExecutor(max_workers=2, thread_name_prefix="notification-race") as executor:
                emitted = executor.submit(self._notify, text="AUTHORIZED_BEFORE_PASSWORD_COMMIT")
                try:
                    self.assertTrue(locked.wait(8))
                    reset_result = executor.submit(self._post, token, client=reset_client, csrf=csrf)
                    self.assertTrue(update_attempted.wait(8))
                    self._wait_for_update_to_be_blocked_by_read_lock()
                    self.assertEqual(self._account()[0], token_cases.FIXTURE_HASH)
                finally:
                    release.set()
                emitted.result(timeout=12)
                self._assert_success(reset_result.result(timeout=12))
        finally:
            release.set()
            event.remove(self.engine, "after_cursor_execute", after)
            event.remove(self.engine, "before_cursor_execute", before)
        self.assertTrue(check_password_hash(self._account()[0], token_cases.NEW_PASSWORD))
        current = self._socket(self._login_client(password=token_cases.NEW_PASSWORD))
        self._notify(text="PRIVATE_AFTER_COMMIT")
        self.assertNotIn("PRIVATE_AFTER_COMMIT", repr(self._received(old_socket)))
        self.assertIn("PRIVATE_AFTER_COMMIT", repr(self._received(current)))

    def test_login_cannot_bind_old_password_verification_to_newer_credential(self):
        """Um login já validou a senha antiga quando outra sessão a modifica."""
        before_cookie, release = threading.Event(), threading.Event()
        client = self.app.test_client()
        csrf = self._csrf(client)
        reset_client = self.app.test_client()
        reset_csrf = self._csrf(reset_client)
        token = self._token()

        login_user = auth.login_user
        def pause_before_cookie(*args, **kwargs):
            before_cookie.set()
            if not release.wait(12):
                raise AssertionError("Login de teste não foi liberado.")
            return login_user(*args, **kwargs)
        try:
            with patch.object(auth, "login_user", side_effect=pause_before_cookie):
                with ThreadPoolExecutor(max_workers=1, thread_name_prefix="old-password-login") as executor:
                    login = executor.submit(client.post, "/auth/login", data={
                        "email": "active@example.invalid", "senha": token_cases.OLD_PASSWORD,
                        "csrf_token": csrf,
                    })
                    try:
                        self.assertTrue(before_cookie.wait(8))
                        self._assert_success(self._post(token, client=reset_client, csrf=reset_csrf))
                    finally:
                        release.set()
                    self.assertEqual(login.result(timeout=12).status_code, 302)
        finally:
            release.set()
        self._assert_private_denied(client)
        self.assertEqual(self._login_client(password=token_cases.NEW_PASSWORD)
                         .get("/_security/protected").status_code, 200)

    def test_first_access_renewal_does_not_adopt_a_later_password_change(self):
        """A renovação do próprio cookie usa o hash confirmado, sem refresh cego."""
        client = self._login_client("pending")
        csrf = self._csrf(client, "/auth/primeiro-acesso")
        first_committed, release = threading.Event(), threading.Event()
        def committed(session):
            if threading.current_thread().name.startswith("first-access-renewal"):
                first_committed.set()
                if not release.wait(12):
                    raise AssertionError("Renovação de teste não foi liberada.")
        event.listen(Session, "after_commit", committed)
        try:
            with ThreadPoolExecutor(max_workers=1, thread_name_prefix="first-access-renewal") as executor:
                first = executor.submit(client.post, "/auth/primeiro-acesso", data={
                    "nova_senha": token_cases.NEW_PASSWORD,
                    "confirma_senha": token_cases.NEW_PASSWORD, "csrf_token": csrf,
                })
                try:
                    self.assertTrue(first_committed.wait(8))
                    token = self._token("pending")
                    self._assert_success(self._post(token, password=token_cases.NEW_PASSWORD + "-second",
                                                   client=self.app.test_client()))
                finally:
                    release.set()
                self.assertEqual(first.result(timeout=12).status_code, 302)
        finally:
            release.set()
            event.remove(Session, "after_commit", committed)
        self.assertTrue(check_password_hash(self._account("pending")[0],
                                            token_cases.NEW_PASSWORD + "-second"))
        self._assert_private_denied(client)
