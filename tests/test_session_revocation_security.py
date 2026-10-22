"""NEXO-SEC-003: sessões reais e Socket.IO com banco/usuários sintéticos."""

from unittest.mock import patch

from flask import jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import delete, event
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash

from . import test_auth_tokens_security as token_cases
from extensions import db, socketio
from models import Notificacao, Usuario
import notifications
import realtime
import session_security


class SessionRevocationCases:
    """Cenários comuns; não é TestCase e não duplica a suíte SEC-002."""

    def _session_routes(self):
        @login_required
        def protected():
            return jsonify(private="synthetic-private-data", uid=current_user.id_usuario,
                           company=current_user.id_empresa)
        self.app.add_url_rule("/_security/protected", "security_protected", protected)

    def _login_client(self, user="active", password=token_cases.OLD_PASSWORD):
        client = self.app.test_client()
        response = client.post("/auth/login", data={
            "email": f"{user}@example.invalid", "senha": password,
            "csrf_token": self._csrf(client),
        })
        self.assertEqual(response.status_code, 302)
        return client

    def _assert_private_denied(self, client):
        response = client.get("/_security/protected")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.headers["Location"])
        self.assertNotIn("synthetic-private-data", response.get_data(as_text=True))
        with client.session_transaction() as session:
            self.assertNotIn("_user_id", session)

    def _reset_password(self, user="active"):
        token = self._token(user)
        self._assert_success(self._post(token, client=self.app.test_client()))
        return token

    def _socket(self, client):
        connection = socketio.test_client(self.app, flask_test_client=client)
        def close():
            if connection.is_connected():
                connection.disconnect()
        self.addCleanup(close)
        return connection

    def _notify(self, user="active", text="Synthetic private notification", commit=True):
        with self.app.app_context():
            result = notifications.criar_notificacao(self.ids[user], text, "/cliente/dashboard")
            identifier = result.id_notificacao
            if commit:
                db.session.commit()
            else:
                db.session.rollback()
            return identifier

    @staticmethod
    def _received(connection):
        return connection.get_received() if connection.is_connected() else []

    def test_login_and_current_session_access_protected_http(self):
        client = self._login_client()
        response = client.get("/_security/protected")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["uid"], self.ids["active"])

    def test_client_session_contains_only_credential_fingerprint_not_hash(self):
        client = self._login_client()
        with client.session_transaction() as session:
            self.assertIn(session_security.CHAVE_CREDENCIAL, session)
            fingerprint = session[session_security.CHAVE_CREDENCIAL]
            self.assertRegex(fingerprint, r"^[0-9a-f]{64}$")
            self.assertNotIn(token_cases.FIXTURE_HASH, repr(dict(session)))
            self.assertNotIn(token_cases.OLD_PASSWORD, repr(dict(session)))
        self.assertNotEqual(fingerprint, self._token())

    def test_recovery_revokes_both_preexisting_http_sessions(self):
        first, second = self._login_client(), self._login_client()
        self._reset_password()
        self._assert_private_denied(first)
        self._assert_private_denied(second)

    def test_replayed_old_cookie_is_denied_even_in_new_client(self):
        previous = self._login_client()
        cookie = previous.get_cookie(self.app.config["SESSION_COOKIE_NAME"]).value
        self._reset_password()
        replay = self.app.test_client()
        replay.set_cookie(self.app.config["SESSION_COOKIE_NAME"], cookie)
        self._assert_private_denied(replay)

    def test_new_password_logs_in_and_old_password_does_not(self):
        self._reset_password()
        stale = self.app.test_client()
        response = stale.post("/auth/login", data={
            "email": "active@example.invalid", "senha": token_cases.OLD_PASSWORD,
            "csrf_token": self._csrf(stale),
        })
        self.assertEqual(response.status_code, 200)
        self._assert_private_denied(stale)
        renewed = self._login_client(password=token_cases.NEW_PASSWORD)
        self.assertEqual(renewed.get("/_security/protected").status_code, 200)

    def test_legitimate_external_credential_change_revokes_http_cookie(self):
        client = self._login_client()
        self._change(senha_hash=generate_password_hash("Synthetic-external-password-789!"))
        self._assert_private_denied(client)

    def test_same_password_with_new_salt_revokes_previous_session(self):
        client = self._login_client()
        token = self._token()
        self._assert_success(self._post(token, password=token_cases.OLD_PASSWORD,
                                       client=self.app.test_client()))
        self._assert_private_denied(client)

    def test_legacy_session_without_fingerprint_is_not_accepted(self):
        client = self._login_client()
        with client.session_transaction() as session:
            session.pop(session_security.CHAVE_CREDENCIAL)
        self._assert_private_denied(client)

    def test_session_fingerprint_from_other_user_cannot_authenticate(self):
        first, other = self._login_client(), self._login_client("other")
        with first.session_transaction() as session:
            foreign_fingerprint = session[session_security.CHAVE_CREDENCIAL]
        with other.session_transaction() as session:
            session[session_security.CHAVE_CREDENCIAL] = foreign_fingerprint
        self._assert_private_denied(other)
        self.assertEqual(first.get("/_security/protected").status_code, 200)

    def test_malformed_session_fingerprint_fails_closed(self):
        for value in (None, [], "é" * 64, "0" * 63, "0" * 64):
            with self.subTest(value_type=type(value).__name__):
                client = self._login_client()
                with client.session_transaction() as session:
                    session[session_security.CHAVE_CREDENCIAL] = value
                self._assert_private_denied(client)

    def test_deactivated_user_loses_existing_http_session(self):
        client = self._login_client()
        self._change(ativo=False)
        self._assert_private_denied(client)

    def test_deleted_user_cookie_is_cleared_without_private_response(self):
        client = self._login_client()
        with self.app.app_context():
            db.session.execute(delete(Usuario).where(Usuario.id_usuario == self.ids["active"]))
            db.session.commit()
        self._assert_private_denied(client)

    def test_server_restart_still_invalidates_existing_session(self):
        client = self._login_client()
        self.app.config["BOOT_ID"] = "synthetic-next-boot"
        self._assert_private_denied(client)

    def test_database_read_failure_denies_http_and_clears_authentication(self):
        client = self._login_client()
        def fail_select(connection, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith("SELECT"):
                raise SQLAlchemyError("PRIVATE_DB_SENTINEL")
        event.listen(self.engine, "before_cursor_execute", fail_select)
        try:
            response = client.get("/_security/protected")
        finally:
            event.remove(self.engine, "before_cursor_execute", fail_select)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("PRIVATE_DB_SENTINEL", response.get_data(as_text=True))
        self.assertNotIn("synthetic-private-data", response.get_data(as_text=True))
        with client.session_transaction() as session:
            self.assertNotIn("_user_id", session)
        self._assert_private_denied(client)

    def test_first_access_renews_only_current_session(self):
        first, second = self._login_client("pending"), self._login_client("pending")
        csrf = self._csrf(first, "/auth/primeiro-acesso")
        response = first.post("/auth/primeiro-acesso", data={
            "nova_senha": token_cases.NEW_PASSWORD, "confirma_senha": token_cases.NEW_PASSWORD,
            "csrf_token": csrf,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/cliente/dashboard"))
        self.assertEqual(first.get("/_security/protected").status_code, 200)
        self._assert_private_denied(second)
        self.assertFalse(self._account("pending")[1])

    def test_activation_link_invalidates_logged_pending_session(self):
        client = self._login_client("pending")
        token = self._token("pending", "activation")
        self._assert_success(self._post(token, "activation", client=self.app.test_client()))
        self._assert_private_denied(client)

    def test_password_reset_does_not_revoke_other_user_or_company(self):
        changed, other = self._login_client(), self._login_client("other")
        self._reset_password()
        self._assert_private_denied(changed)
        response = other.get("/_security/protected")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["uid"], self.ids["other"])

    def test_valid_socket_handshake_connects_but_anonymous_does_not(self):
        valid = self._socket(self._login_client())
        self.assertTrue(valid.is_connected())
        self.assertFalse(self._socket(self.app.test_client()).is_connected())

    def test_socket_handshake_rejects_pending_first_access(self):
        self.assertFalse(self._socket(self._login_client("pending")).is_connected())

    def test_socket_handshake_rejects_previous_credential_cookie(self):
        client = self._login_client()
        self._reset_password()
        self.assertFalse(self._socket(client).is_connected())

    def test_authenticated_event_rechecks_credential_before_private_handler(self):
        executed = []
        def private_probe():
            executed.append(True)
            socketio.emit("_security_private_probe", {"private": "PRIVATE_AUTHENTICATED_EVENT"},
                          to=request.sid)
            return True
        socketio.on_event("_security_probe", realtime.guarded_socket_event(private_probe))
        connection = self._socket(self._login_client())
        self.assertTrue(connection.emit("_security_probe", callback=True))
        self.assertIn("PRIVATE_AUTHENTICATED_EVENT", repr(self._received(connection)))
        self._change(senha_hash=generate_password_hash("Synthetic-external-password-789!"))
        response = connection.emit("_security_probe", callback=True)
        self.assertNotIn("PRIVATE_AUTHENTICATED_EVENT", repr(response))
        self.assertEqual(executed, [True])
        self.assertFalse(connection.is_connected())

    def test_sweep_disconnects_revoked_open_socket_using_persisted_credential(self):
        connection = self._socket(self._login_client())
        self._change(senha_hash=generate_password_hash("Synthetic-external-password-789!"))
        with self.app.app_context():
            realtime.revogar_sockets_invalidos(self.app)
        self.assertFalse(connection.is_connected())

    def test_sweep_disconnects_deactivated_or_previous_boot_socket(self):
        connection = self._socket(self._login_client())
        self.app.config["BOOT_ID"] = "synthetic-next-boot"
        with self.app.app_context():
            realtime.revogar_sockets_invalidos(self.app)
        self.assertFalse(connection.is_connected())

    def test_sweep_disconnects_deactivated_user_socket(self):
        connection = self._socket(self._login_client())
        self._change(ativo=False)
        with self.app.app_context():
            realtime.revogar_sockets_invalidos(self.app)
        self.assertFalse(connection.is_connected())

    def test_database_error_rejects_socket_event_without_private_ack(self):
        executed = []
        def private_probe():
            executed.append(True)
            socketio.emit("_security_private_probe", {"private": "PRIVATE_DB_FAILURE_EVENT"},
                          to=request.sid)
            return True
        socketio.on_event("_security_db_probe", realtime.guarded_socket_event(private_probe))
        connection = self._socket(self._login_client())
        def fail_select(connection, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith("SELECT"):
                raise SQLAlchemyError("PRIVATE_SOCKET_DB_SENTINEL")
        event.listen(self.engine, "before_cursor_execute", fail_select)
        try:
            response = connection.emit("_security_db_probe", callback=True)
        finally:
            event.remove(self.engine, "before_cursor_execute", fail_select)
        self.assertNotIn("PRIVATE_DB_FAILURE_EVENT", repr(response))
        self.assertNotIn("PRIVATE_SOCKET_DB_SENTINEL", repr(response))
        self.assertEqual(executed, [])
        self.assertFalse(connection.is_connected())

    def test_password_recovery_disconnects_preexisting_socket(self):
        connection = self._socket(self._login_client())
        self.assertTrue(connection.is_connected())
        self._reset_password()
        self.assertFalse(connection.is_connected())

    def test_password_change_preserves_other_company_socket_and_private_delivery(self):
        changed = self._socket(self._login_client())
        other = self._socket(self._login_client("other"))
        self._reset_password()
        self.assertFalse(changed.is_connected())
        self.assertTrue(other.is_connected())
        self._notify("other", text="OTHER_COMPANY_STILL_AUTHORIZED")
        self.assertIn("OTHER_COMPANY_STILL_AUTHORIZED", repr(self._received(other)))

    def test_revoked_open_socket_never_receives_new_private_notification(self):
        connection = self._socket(self._login_client())
        self._change(senha_hash=generate_password_hash("Synthetic-external-password-789!"))
        # Externo ao fluxo de recuperação: não houve callback local de revogação.
        # A proteção deve vir da credencial persistida, mesmo antes da varredura.
        self._notify(text="PRIVATE_AFTER_REVOCATION")
        self.assertNotIn("PRIVATE_AFTER_REVOCATION", repr(self._received(connection)))

    def test_notifications_are_isolated_between_users_and_companies(self):
        first, other = self._socket(self._login_client()), self._socket(self._login_client("other"))
        self._notify(text="PRIVATE_COMPANY_ONE")
        messages = self._received(first)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["name"], "nova_notificacao")
        self.assertEqual(messages[0]["args"][0]["texto"], "PRIVATE_COMPANY_ONE")
        self.assertNotIn("PRIVATE_COMPANY_ONE", repr(self._received(other)))

    def test_new_socket_after_new_login_receives_current_generation_only(self):
        old = self._socket(self._login_client())
        self._reset_password()
        new = self._socket(self._login_client(password=token_cases.NEW_PASSWORD))
        self.assertTrue(new.is_connected())
        self._notify(text="CURRENT_GENERATION_PRIVATE")
        self.assertNotIn("CURRENT_GENERATION_PRIVATE", repr(self._received(old)))
        self.assertIn("CURRENT_GENERATION_PRIVATE", repr(self._received(new)))

    def test_notification_is_emitted_only_after_business_commit(self):
        connection = self._socket(self._login_client())
        with self.app.app_context():
            notification = notifications.criar_notificacao(self.ids["active"], "COMMITTED_PRIVATE", "/")
            self.assertIsNotNone(notification.id_notificacao)
            self.assertEqual(self._received(connection), [])
            db.session.commit()
        self.assertIn("COMMITTED_PRIVATE", repr(self._received(connection)))

    def test_notification_rollback_emits_nothing_and_persists_nothing(self):
        connection = self._socket(self._login_client())
        identifier = self._notify(text="ROLLED_BACK_PRIVATE", commit=False)
        self.assertEqual(self._received(connection), [])
        with self.app.app_context():
            self.assertIsNone(db.session.get(Notificacao, identifier))

    def test_savepoint_commit_does_not_emit_before_outer_commit(self):
        connection = self._socket(self._login_client())
        with self.app.app_context():
            notifications.criar_notificacao(self.ids["active"], "OUTER_COMMITTED_PRIVATE", "/")
            with db.session.begin_nested():
                notifications.criar_notificacao(self.ids["active"], "NESTED_COMMITTED_PRIVATE", "/")
            self.assertEqual(self._received(connection), [])
            db.session.commit()
        messages = repr(self._received(connection))
        self.assertIn("OUTER_COMMITTED_PRIVATE", messages)
        self.assertIn("NESTED_COMMITTED_PRIVATE", messages)

    def test_savepoint_rollback_preserves_outer_notification_only(self):
        connection = self._socket(self._login_client())
        with self.app.app_context():
            outer = notifications.criar_notificacao(self.ids["active"], "OUTER_STILL_COMMITTED_PRIVATE", "/")
            outer_id = outer.id_notificacao
            try:
                with db.session.begin_nested():
                    inner = notifications.criar_notificacao(self.ids["active"], "NESTED_ROLLED_BACK_PRIVATE", "/")
                    inner_id = inner.id_notificacao
                    raise ValueError("synthetic savepoint rollback")
            except ValueError:
                pass
            self.assertEqual(self._received(connection), [])
            db.session.commit()
            self.assertIsNotNone(db.session.get(Notificacao, outer_id))
            self.assertIsNone(db.session.get(Notificacao, inner_id))
        messages = repr(self._received(connection))
        self.assertIn("OUTER_STILL_COMMITTED_PRIVATE", messages)
        self.assertNotIn("NESTED_ROLLED_BACK_PRIVATE", messages)

    def test_outer_rollback_discards_already_released_savepoint_notifications(self):
        connection = self._socket(self._login_client())
        with self.app.app_context():
            outer = notifications.criar_notificacao(self.ids["active"], "OUTER_ROLLBACK_PRIVATE", "/")
            outer_id = outer.id_notificacao
            with db.session.begin_nested():
                inner = notifications.criar_notificacao(self.ids["active"], "INNER_ROLLBACK_PRIVATE", "/")
                inner_id = inner.id_notificacao
            db.session.rollback()
            self.assertIsNone(db.session.get(Notificacao, outer_id))
            self.assertIsNone(db.session.get(Notificacao, inner_id))
        self.assertEqual(self._received(connection), [])

    def test_failed_password_commit_does_not_revoke_valid_session(self):
        client = self._login_client()
        connection = self._socket(client)
        token = self._token()
        anonymous = self.app.test_client()
        csrf = self._csrf(anonymous)
        with patch.object(db.session, "commit", side_effect=SQLAlchemyError("PRIVATE_COMMIT_SENTINEL")):
            self._assert_rejected(self._post(token, client=anonymous, csrf=csrf))
        self.assertEqual(client.get("/_security/protected").status_code, 200)
        self.assertTrue(connection.is_connected())
        self.assertEqual(self._account()[0], token_cases.FIXTURE_HASH)


class SessionRevocationSecurityTests(SessionRevocationCases, token_cases._TokenCase):
    def setUp(self):
        super().setUp()
        self._session_routes()
