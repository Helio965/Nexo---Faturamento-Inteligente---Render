"""NEXO-SEC-002: tokens e consumo atômico com dados inteiramente fictícios.

Executar da raiz: python -B -m unittest tests.test_auth_tokens_security -v
SQLite fica em TemporaryDirectory, fora do checkout; não há Supabase, serviços
externos, migrações ou seeds. As três corridas usam sessões/conexões distintas e
uma barreira antes do UPDATE real, exigindo rowcounts 1 e 0, não database locked.
Isso demonstra o CAS em SQLite; PostgreSQL real não é acessado por esta suíte.
"""

import contextlib
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import logging
from pathlib import Path
import re
import tempfile
import threading
import time
from urllib.parse import urlsplit
import unittest
from unittest.mock import patch

from flask import Flask
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy import event, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from werkzeug.security import check_password_hash, generate_password_hash

from blueprints import auth, admin
from extensions import db
from models import Empresa, Plano, Segmento, Usuario


OLD_PASSWORD = "Synthetic-old-password-123!"
# Sem conter nome/e-mail de nenhuma fixture (inclusive o usuário "Synthetic New"
# do cadastro) nem termo comum: a política de senha (politica_senha.py) recusaria.
NEW_PASSWORD = "Troca-de-chave-robusta-2026"
# Mesmo hash entre fixtures torna a vinculação ao ID ainda mais verificável;
# produção continua gerando salt individual em cada definição de senha.
FIXTURE_HASH = generate_password_hash(OLD_PASSWORD)


class _TokenCase(unittest.TestCase):
    ENABLE_LIMITS = False

    def setUp(self):
        self.work = tempfile.TemporaryDirectory(prefix="nexo-auth-token-security-")
        self.addCleanup(self.work.cleanup)
        self.root = Path(self.work.name)
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        for target in ("socket.socket.connect", "socket.socket.connect_ex", "socket.create_connection"):
            self.stack.enter_context(patch(target, side_effect=AssertionError("Rede externa proibida")))
        with patch("dotenv.load_dotenv", return_value=False):
            import app as app_module
            from config import DevelopmentConfig
        uri = f"sqlite:///{(self.root / 'tokens.db').as_posix()}"
        with contextlib.ExitStack() as configuration:
            for key, value in {
                "SECRET_KEY": "isolated-auth-token-security-key",
                "SQLALCHEMY_DATABASE_URI": uri, "SQLALCHEMY_DIRECT_URI": uri,
                "UPLOAD_FOLDER": self.root / "uploads", "DEBUG": False,
                "SQLALCHEMY_ECHO": False, "TESTING": True,
                "MAIL_ATIVO": False, "MAIL_SUPPRESS_SEND": True,
                "RATELIMIT_ENABLED": self.ENABLE_LIMITS,
            }.items():
                configuration.enter_context(patch.object(DevelopmentConfig, key, value, create=True))
            configuration.enter_context(patch.object(
                app_module, "Flask", side_effect=lambda *a, **kw: Flask(
                    *a, instance_path=str(self.root / "instance"), **kw,
                ),
            ))
            self.app = app_module.create_app("development")
        self.recovery_mail = self.stack.enter_context(patch.object(
            auth, "email_recuperacao_senha", return_value=True,
        ))
        self.activation_mail = self.stack.enter_context(patch.object(
            auth, "email_boas_vindas", return_value=True,
        ))
        self.registration_mail = self.stack.enter_context(patch.object(
            admin, "email_boas_vindas", return_value=True,
        ))
        # Com os gatilhos substituídos, o transporte também: a recuperação não
        # para no aviso de "envio de e-mail indisponível" (MAIL_ATIVO=False).
        self.stack.enter_context(patch.object(auth, "transporte_configurado", return_value="smtp"))
        self.stack.enter_context(patch.object(auth.logger, "disabled", False))
        with self.app.app_context():
            self.engine = db.engine
            self.assertEqual(self.engine.url.get_backend_name(), "sqlite")
            self.assertTrue(Path(self.engine.url.database).resolve().is_relative_to(self.root))
            db.create_all()
            self._fixtures()
        self.addCleanup(self._dispose)
        self.client = self.app.test_client()

    def _dispose(self):
        with self.app.app_context():
            db.session.remove()
            self.engine.dispose()

    def _fixtures(self):
        plano = Plano(
            nome_plano="BRONZE", valor_mensal=100, qtd_analises_mes=1,
            tipo_analise_permitida="MENSAL", nivel_entrega_analise="BASICA",
            nivel_dashboard="RESUMIDO", nivel_atendimento="BAIXO",
        )
        segmento = Segmento(nome_segmento="Token security synthetic")
        db.session.add_all([plano, segmento])
        db.session.flush()
        empresas = [Empresa(
            id_segmento=segmento.id_segmento, id_plano_atual=plano.id_plano,
            cnpj=f"0000000000000{i}", razao_social=f"Synthetic company {i}",
            email_contato=f"company{i}@example.invalid", data_contratacao=date(2026, 1, 1),
        ) for i in (1, 2)]
        db.session.add_all(empresas)
        db.session.flush()
        users = {
            "active": Usuario(nome="Active", email="active@example.invalid", role="CLIENTE",
                              id_empresa=empresas[0].id_empresa, primeiro_acesso=False),
            "pending": Usuario(nome="Pending", email="pending@example.invalid", role="CLIENTE",
                               id_empresa=empresas[0].id_empresa, primeiro_acesso=True),
            "other": Usuario(nome="Other", email="other@example.invalid", role="CLIENTE",
                             id_empresa=empresas[1].id_empresa, primeiro_acesso=False),
            "inactive": Usuario(nome="Inactive", email="inactive@example.invalid", role="CLIENTE",
                                id_empresa=empresas[1].id_empresa, primeiro_acesso=False, ativo=False),
            # O ADMIN legado pode ter esta flag, sem estar em ativação de CLIENTE.
            "admin": Usuario(nome="Admin", email="admin@example.invalid", role="ADMIN", primeiro_acesso=True),
        }
        for user in users.values():
            user.senha_hash = FIXTURE_HASH
        db.session.add_all(users.values())
        db.session.commit()
        self.ids = {name: user.id_usuario for name, user in users.items()}
        self.plan_id, self.segment_id = plano.id_plano, segmento.id_segmento

    def _token(self, user="active", purpose="recovery"):
        with self.app.app_context():
            account = db.session.get(Usuario, self.ids[user])
            issuer = auth.gerar_token_definir_senha if purpose == "activation" else auth.gerar_token_recuperacao_senha
            return issuer(account)

    def _path(self, token, purpose="recovery"):
        return "/auth/" + ("primeiro-acesso/" if purpose == "activation" else "resetar-senha/") + token

    def _csrf(self, client=None, path="/auth/login"):
        response = (client or self.client).get(path)
        self.assertEqual(response.status_code, 200)
        match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', response.get_data(as_text=True))
        self.assertIsNotNone(match)
        return match.group(1)

    def _post(self, token, purpose="recovery", password=NEW_PASSWORD, confirmation=None, client=None, csrf=None):
        client = client or self.client
        return client.post(self._path(token, purpose), data={
            "nova_senha": password, "confirma_senha": password if confirmation is None else confirmation,
            "csrf_token": self._csrf(client) if csrf is None else csrf,
        })

    def _assert_success(self, response):
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/auth/login"))

    def _assert_rejected(self, response):
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/auth/recuperar-senha"))

    def _account(self, user="active"):
        with self.app.app_context():
            account = db.session.get(Usuario, self.ids[user])
            return account.senha_hash, account.primeiro_acesso, account.ativo

    def _change(self, user="active", **values):
        with self.app.app_context():
            db.session.execute(update(Usuario).where(Usuario.id_usuario == self.ids[user]).values(**values))
            db.session.commit()

    def _request_link(self, email, client=None):
        client = client or self.client
        response = client.post("/auth/recuperar-senha", data={"email": email, "csrf_token": self._csrf(client)})
        self.assertEqual(response.status_code, 302)
        return client.get(response.headers["Location"])


class AuthTokenSecurityTests(_TokenCase):
    def test_activation_token_and_first_consumption(self):
        token = self._token("pending", "activation")
        self.assertEqual(self.client.get(self._path(token, "activation")).status_code, 200)
        self._assert_success(self._post(token, "activation"))
        hashed, pending, active = self._account("pending")
        self.assertTrue(check_password_hash(hashed, NEW_PASSWORD))
        self.assertFalse(pending)
        self.assertTrue(active)

    def test_recovery_token_and_first_consumption(self):
        token = self._token()
        self.assertEqual(self.client.get(self._path(token)).status_code, 200)
        self._assert_success(self._post(token))
        self.assertTrue(check_password_hash(self._account()[0], NEW_PASSWORD))

    def test_activation_cannot_be_used_for_recovery_or_after_activation(self):
        token = self._token("pending", "activation")
        self._assert_rejected(self._post(token))
        self.assertEqual(self._account("pending")[0], FIXTURE_HASH)
        self._assert_success(self._post(token, "activation"))
        self._assert_rejected(self._post(token, "activation", password="Another-password-123!"))

    def test_recovery_cannot_be_used_for_activation(self):
        token = self._token()
        self._assert_rejected(self._post(token, "activation"))
        self.assertEqual(self._account()[0], FIXTURE_HASH)

    def test_token_is_bound_to_user_without_exposing_password_hash_or_email(self):
        token = self._token()
        with self.app.app_context():
            payload = auth._serializer("recovery").loads(token)
            self.assertEqual(set(payload), {"v", "uid", "purpose", "credential"})
            self.assertEqual(payload["uid"], self.ids["active"])
            self.assertEqual(payload["purpose"], "recovery")
            self.assertEqual(payload["v"], 2)
            self.assertRegex(payload["credential"], r"^[0-9a-f]{64}$")
            self.assertNotIn(FIXTURE_HASH, repr(payload))
            self.assertNotIn(OLD_PASSWORD, repr(payload))
            self.assertNotIn("active@example.invalid", repr(payload))
            state = auth._ler_token_reset(token)
            self.assertNotIn(FIXTURE_HASH, repr(state))

    def test_changed_user_id_cannot_reuse_another_users_fingerprint(self):
        with self.app.app_context():
            payload = auth._serializer("recovery").loads(self._token())
            payload["uid"] = self.ids["other"]
            forged = auth._serializer("recovery").dumps(payload)
        self._assert_rejected(self._post(forged))
        self.assertEqual(self._account()[0], FIXTURE_HASH)
        self.assertEqual(self._account("other")[0], FIXTURE_HASH)

    def test_token_only_updates_its_user_even_with_an_extra_posted_user_id(self):
        token = self._token()
        response = self.client.post(self._path(token), data={
            "nova_senha": NEW_PASSWORD, "confirma_senha": NEW_PASSWORD,
            "id_usuario": str(self.ids["other"]), "csrf_token": self._csrf(),
        })
        self._assert_success(response)
        self.assertTrue(check_password_hash(self._account()[0], NEW_PASSWORD))
        self.assertEqual(self._account("other")[0], FIXTURE_HASH)

    def test_tampered_token_does_not_change_password(self):
        token = self._token()
        stem, signature = token.rsplit(".", 1)
        tampered = stem + "." + ("A" if signature[0] != "A" else "B") + signature[1:]
        self._assert_rejected(self._post(tampered))
        self.assertEqual(self._account()[0], FIXTURE_HASH)

    def test_expired_token_is_rejected_and_900_seconds_is_the_limit(self):
        now = int(time.time())
        with patch("itsdangerous.timed.TimestampSigner.get_timestamp", return_value=now):
            token = self._token()
        with self.app.app_context():
            with patch("itsdangerous.timed.TimestampSigner.get_timestamp", return_value=now + 900):
                self.assertIsNotNone(auth._ler_token_reset(token))
            with patch("itsdangerous.timed.TimestampSigner.get_timestamp", return_value=now + 901):
                self.assertIsNone(auth._ler_token_reset(token))

    def test_signed_malformed_payloads_are_rejected(self):
        with self.app.app_context():
            good = auth._serializer("recovery").loads(self._token())
            bad = [None, [], "email@example.invalid", 1, {}, {**good, "extra": "x"}]
            for field, value in (
                ("v", 1), ("v", True), ("v", 2.0),
                ("uid", True), ("uid", "1"), ("uid", -1),
                ("purpose", "activation"), ("credential", []),
                ("credential", "é" * 64), ("credential", "0" * 63),
            ):
                bad.append({**good, field: value})
            for payload in bad:
                with self.subTest(payload_type=type(payload).__name__, keys=list(payload) if isinstance(payload, dict) else None):
                    self.assertIsNone(auth._ler_token_reset(auth._serializer("recovery").dumps(payload)))
            for raw in (None, 1, "", "not-a-token", "x" * 2049):
                self.assertIsNone(auth._ler_token_reset(raw))

    def test_legacy_email_only_tokens_are_not_accepted(self):
        with self.app.app_context():
            legacy = URLSafeTimedSerializer(self.app.config["SECRET_KEY"], salt="nexo-reset-senha-v1").dumps("active@example.invalid")
        self._assert_rejected(self._post(legacy))
        self._assert_rejected(self._post(legacy, "activation"))

    def test_deleted_user_is_rejected(self):
        token = self._token()
        with self.app.app_context():
            db.session.delete(db.session.get(Usuario, self.ids["active"]))
            db.session.commit()
        self._assert_rejected(self._post(token))

    def test_deactivated_user_is_rejected(self):
        token = self._token()
        self._change(ativo=False)
        self._assert_rejected(self._post(token))
        self.assertEqual(self._account()[0], FIXTURE_HASH)

    def test_credential_changed_elsewhere_invalidates_token(self):
        token = self._token()
        changed = generate_password_hash("External-synthetic-change!")
        self._change(senha_hash=changed)
        self._assert_rejected(self._post(token))
        self.assertEqual(self._account()[0], changed)

    def test_second_recovery_consumption_is_rejected(self):
        token = self._token()
        self._assert_success(self._post(token))
        changed = self._account()[0]
        self._assert_rejected(self._post(token, password="Second-attempt-password!"))
        self.assertEqual(self._account()[0], changed)

    def test_selecting_same_password_is_refused_without_consuming_token(self):
        # Política de senha: a nova senha precisa ser diferente da atual; a
        # recusa acontece antes do CAS, então o token continua utilizável.
        token = self._token()
        response = self._post(token, password=OLD_PASSWORD)
        self.assertEqual(response.status_code, 200)
        self.assertIn("diferente da senha atual", response.get_data(as_text=True))
        self.assertEqual(self._account()[0], FIXTURE_HASH)
        self._assert_success(self._post(token))
        self.assertTrue(check_password_hash(self._account()[0], NEW_PASSWORD))
        self._assert_rejected(self._post(token))

    def test_two_tokens_before_the_change_both_become_invalid(self):
        now = int(time.time())
        with patch("itsdangerous.timed.TimestampSigner.get_timestamp", return_value=now - 2):
            first = self._token()
        second = self._token()
        self.assertNotEqual(first, second)
        self._assert_success(self._post(first))
        self._assert_rejected(self._post(first))
        self._assert_rejected(self._post(second))

    def test_invalid_password_and_mismatched_confirmation_do_not_consume(self):
        token = self._token()
        for password, confirmation in (("short", "short"), (NEW_PASSWORD, "different-password")):
            with self.subTest(kind="short" if len(password) < 8 else "mismatch"):
                response = self._post(token, password=password, confirmation=confirmation)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self._account()[0], FIXTURE_HASH)
        self._assert_success(self._post(token))

    def test_login_accepts_new_password_and_rejects_old_password(self):
        self._assert_success(self._post(self._token()))
        for password, accepted in ((OLD_PASSWORD, False), (NEW_PASSWORD, True)):
            client = self.app.test_client()
            response = client.post("/auth/login", data={
                "email": "active@example.invalid", "senha": password, "csrf_token": self._csrf(client),
            })
            self.assertEqual(response.status_code, 302 if accepted else 200)
            if accepted:
                self.assertTrue(response.headers["Location"].endswith("/cliente/dashboard"))

    def test_recovery_request_has_generic_response_for_unknown_inactive_and_known(self):
        texts = []
        for email in ("unknown@example.invalid", "inactive@example.invalid", "active@example.invalid", "pending@example.invalid"):
            response = self._request_link(email, self.app.test_client())
            self.assertEqual(response.status_code, 200)
            texts.append(response.get_data(as_text=True))
        generic = "Se o e-mail estiver cadastrado, enviaremos um link de redefinição válido por 15 minutos."
        for text in texts:
            self.assertIn(generic, text)
            self.assertNotIn("Modo simulação", text)

    def test_active_user_receives_recovery_link(self):
        self._request_link("active@example.invalid")
        self.recovery_mail.assert_called_once()
        self.activation_mail.assert_not_called()
        link = self.recovery_mail.call_args.args[1]
        self.assertTrue(urlsplit(link).path.startswith("/auth/resetar-senha/"))
        self.assertEqual(self.client.get(link).status_code, 200)

    def test_pending_client_receives_new_activation_link_not_recovery(self):
        self._request_link("pending@example.invalid")
        self.activation_mail.assert_called_once()
        self.recovery_mail.assert_not_called()
        link = self.activation_mail.call_args.args[1]
        token = urlsplit(link).path.rsplit("/", 1)[1]
        self.assertTrue(urlsplit(link).path.startswith("/auth/primeiro-acesso/"))
        self._assert_rejected(self._post(token))
        self._assert_success(self._post(token, "activation"))

    def test_admin_with_legacy_pending_flag_can_recover(self):
        self._request_link("admin@example.invalid")
        self.recovery_mail.assert_called_once()
        self.activation_mail.assert_not_called()
        token = urlsplit(self.recovery_mail.call_args.args[1]).path.rsplit("/", 1)[1]
        self._assert_success(self._post(token))
        self.assertTrue(check_password_hash(self._account("admin")[0], NEW_PASSWORD))

    def test_no_token_in_logs_or_public_debug_response(self):
        self.app.config["DEBUG"] = True
        self.recovery_mail.return_value = False
        self.activation_mail.return_value = False
        with self.assertLogs(auth.logger, level=logging.INFO) as captured:
            responses = [
                self._request_link("active@example.invalid"),
                self._request_link("pending@example.invalid", self.app.test_client()),
            ]
        for mail in (self.recovery_mail, self.activation_mail):
            link = mail.call_args.args[1]
            token = urlsplit(link).path.rsplit("/", 1)[1]
            self.assertNotIn(token, "\n".join(captured.output))
            for response in responses:
                self.assertNotIn(token, response.get_data(as_text=True))
        self.assertNotIn("active@example.invalid", "\n".join(captured.output))
        self.assertNotIn("pending@example.invalid", "\n".join(captured.output))

    def test_csrf_is_required_on_all_password_post_routes(self):
        for user, purpose in (("active", "recovery"), ("pending", "activation")):
            token = self._token(user, purpose)
            response = self.client.post(self._path(token, purpose), data={
                "nova_senha": NEW_PASSWORD, "confirma_senha": NEW_PASSWORD,
            })
            self.assertEqual(response.status_code, 400)
            self.assertEqual(self._account(user)[0], FIXTURE_HASH)
        self.assertEqual(self.client.post("/auth/recuperar-senha", data={"email": "active@example.invalid"}).status_code, 400)
        client = self.app.test_client()
        login = client.post("/auth/login", data={
            "email": "pending@example.invalid", "senha": OLD_PASSWORD,
            "csrf_token": self._csrf(client),
        })
        self.assertEqual(login.status_code, 302)
        self.assertEqual(client.get("/auth/primeiro-acesso").status_code, 200)
        response = client.post("/auth/primeiro-acesso", data={
            "nova_senha": NEW_PASSWORD, "confirma_senha": NEW_PASSWORD,
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self._account("pending")[:2], (FIXTURE_HASH, True))

    def test_registration_emits_activation_for_the_persisted_new_user(self):
        login = self.client.post("/auth/login", data={
            "email": "admin@example.invalid", "senha": OLD_PASSWORD, "csrf_token": self._csrf(),
        })
        self.assertEqual(login.status_code, 302)
        response = self.client.post("/admin/empresas/nova", data={
            "csrf_token": self._csrf(path="/admin/empresas/nova"),
            "data_contratacao": "2026-01-01", "id_segmento": str(self.segment_id),
            "id_plano_atual": str(self.plan_id), "cnpj": "99999999999999",
            "razao_social": "New synthetic customer", "email_contato": "company-new@example.invalid",
            "usuario_nome": "New synthetic user", "usuario_email": "new@example.invalid",
        })
        self.assertEqual(response.status_code, 302)
        self.registration_mail.assert_called_once()
        link = self.registration_mail.call_args.args[1]
        token = urlsplit(link).path.rsplit("/", 1)[1]
        with self.app.app_context():
            user = db.session.scalar(select(Usuario).where(Usuario.email == "new@example.invalid"))
            self.assertIsNotNone(user)
            state = auth._ler_token_ativacao(token)
            self.assertEqual(state.id_usuario, user.id_usuario)
            self.assertTrue(user.primeiro_acesso)
        self._assert_success(self._post(token, "activation", client=self.app.test_client()))

    def test_logged_in_first_access_consumes_previously_issued_activation(self):
        token = self._token("pending", "activation")
        client = self.app.test_client()
        client.post("/auth/login", data={
            "email": "pending@example.invalid", "senha": OLD_PASSWORD,
            "csrf_token": self._csrf(client),
        })
        response = client.post("/auth/primeiro-acesso", data={
            "nova_senha": NEW_PASSWORD, "confirma_senha": NEW_PASSWORD,
            "csrf_token": self._csrf(client, "/auth/primeiro-acesso"),
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/cliente/dashboard"))
        self.assertFalse(self._account("pending")[1])
        self._assert_rejected(self._post(token, "activation"))

    def test_database_read_error_is_sanitized_and_rolls_back(self):
        token = self._token()
        csrf = self._csrf()
        with patch.object(db.session, "get", side_effect=SQLAlchemyError("PRIVATE_DB_SENTINEL")), \
                patch.object(db.session, "rollback", wraps=db.session.rollback) as rollback, \
                self.assertLogs(auth.logger, level=logging.WARNING) as logs:
            response = self._post(token, csrf=csrf)
        self._assert_rejected(response)
        rollback.assert_called_once()
        self.assertNotIn("PRIVATE_DB_SENTINEL", "\n".join(logs.output))
        self.assertNotIn(token, "\n".join(logs.output))
        self.assertEqual(self._account()[0], FIXTURE_HASH)
        self._assert_success(self._post(token))

    def test_update_error_is_sanitized_and_does_not_consume_token(self):
        token = self._token()
        csrf = self._csrf()
        execute = db.session.execute
        def fail_update(statement, *args, **kwargs):
            if getattr(statement, "is_update", False):
                raise SQLAlchemyError("PRIVATE_SQL_SENTINEL")
            return execute(statement, *args, **kwargs)
        with patch.object(db.session, "execute", side_effect=fail_update), \
                self.assertLogs(auth.logger, level=logging.WARNING) as logs:
            self._assert_rejected(self._post(token, csrf=csrf))
        self.assertNotIn("PRIVATE_SQL_SENTINEL", "\n".join(logs.output))
        self.assertEqual(self._account()[0], FIXTURE_HASH)
        self._assert_success(self._post(token))

    def test_commit_failure_rolls_back_and_token_can_be_retried(self):
        token = self._token()
        csrf = self._csrf()
        with patch.object(db.session, "commit", side_effect=SQLAlchemyError("PRIVATE_COMMIT_SENTINEL")), \
                patch.object(db.session, "rollback", wraps=db.session.rollback) as rollback, \
                self.assertLogs(auth.logger, level=logging.WARNING) as logs:
            self._assert_rejected(self._post(token, csrf=csrf))
        rollback.assert_called_once()
        self.assertNotIn("PRIVATE_COMMIT_SENTINEL", "\n".join(logs.output))
        self.assertEqual(self._account()[0], FIXTURE_HASH)
        self._assert_success(self._post(token))

    def test_deactivation_between_validation_and_update_prevents_consumption(self):
        with self.app.app_context():
            state = auth._ler_token_reset(self._token())
            # A separate transaction changes eligibility after the initial read.
            db.session.rollback()
            with self.engine.begin() as connection:
                connection.execute(update(Usuario).where(Usuario.id_usuario == self.ids["active"]).values(ativo=False))
            self.assertFalse(auth._atualizar_credencial(state, NEW_PASSWORD))
        self.assertEqual(self._account()[0], FIXTURE_HASH)
        self.assertFalse(self._account()[2])

    def _assert_concurrent_consumption(self, user, purpose, logged_first_access=False):
        token = self._token(user, purpose)
        clients = [self.app.test_client(), self.app.test_client()]
        csrf = [self._csrf(client) for client in clients]
        if logged_first_access:
            for i, client in enumerate(clients):
                response = client.post("/auth/login", data={
                    "email": "pending@example.invalid", "senha": OLD_PASSWORD, "csrf_token": csrf[i],
                })
                self.assertEqual(response.status_code, 302)
                csrf[i] = self._csrf(client, "/auth/primeiro-acesso")
        barrier = threading.Barrier(2, timeout=15)
        rowcounts, commits = [], []
        lock = threading.Lock()
        def is_password_update(statement):
            upper = statement.lstrip().upper()
            return upper.startswith("UPDATE USUARIO SET") and "SENHA_HASH" in upper
        def before(connection, cursor, statement, parameters, context, executemany):
            if is_password_update(statement):
                barrier.wait()
        def after(connection, cursor, statement, parameters, context, executemany):
            if is_password_update(statement):
                with lock:
                    rowcounts.append(cursor.rowcount)
        def committed(session):
            if threading.current_thread().name.startswith("token-race"):
                with lock:
                    commits.append(1)
        event.listen(self.engine, "before_cursor_execute", before)
        event.listen(self.engine, "after_cursor_execute", after)
        event.listen(Session, "after_commit", committed)
        def worker(index):
            password = NEW_PASSWORD + str(index)
            path = "/auth/primeiro-acesso" if logged_first_access else self._path(token, purpose)
            response = clients[index].post(path, data={
                "nova_senha": password, "confirma_senha": password, "csrf_token": csrf[index],
            })
            return index, response.status_code, response.headers.get("Location", ""), response.get_data(as_text=True)
        try:
            with ThreadPoolExecutor(max_workers=2, thread_name_prefix="token-race") as executor:
                futures = [executor.submit(worker, i) for i in range(2)]
                results = [future.result(timeout=25) for future in futures]
        finally:
            event.remove(self.engine, "before_cursor_execute", before)
            event.remove(self.engine, "after_cursor_execute", after)
            event.remove(Session, "after_commit", committed)
        self.assertEqual(sorted(rowcounts), [0, 1], "Ambos os UPDATEs devem executar; lock não prova CAS")
        self.assertEqual(len(commits), 1)
        success_target = "/cliente/dashboard" if logged_first_access else "/auth/login"
        winners = [r for r in results if r[1] == 302 and r[2].endswith(success_target)]
        if logged_first_access:
            # A rejeição segura volta ao login, sem uma segunda alteração.
            self.assertEqual(len(winners), 1)
            losers = [r for r in results if r not in winners]
            self.assertEqual(len(losers), 1)
            self.assertEqual(losers[0][1], 302)
            self.assertTrue(losers[0][2].endswith("/auth/login"))
        else:
            self.assertEqual(len(winners), 1)
            self.assertEqual(sum(r[2].endswith("/auth/recuperar-senha") for r in results), 1)
        for result in results:
            self.assertNotIn("Traceback", result[3])
            self.assertNotIn("senha_hash", result[3])
        hashed = self._account(user)[0]
        self.assertTrue(check_password_hash(hashed, NEW_PASSWORD + str(winners[0][0])))
        self.assertFalse(check_password_hash(hashed, OLD_PASSWORD))

    def test_two_concurrent_recovery_requests_confirm_only_one_change(self):
        self._assert_concurrent_consumption("active", "recovery")

    def test_two_concurrent_activation_requests_confirm_only_one_change(self):
        self._assert_concurrent_consumption("pending", "activation")

    def test_logged_first_access_uses_the_same_atomic_guard(self):
        self._assert_concurrent_consumption("pending", "activation", logged_first_access=True)


class AuthTokenRateLimitTests(_TokenCase):
    ENABLE_LIMITS = True

    def test_recovery_rate_limit_remains_active(self):
        csrf = self._csrf()
        # E-mails distintos: aqui vale o limite por IP (o limite por conta é
        # mais apertado e tem teste próprio em test_password_policy_security).
        responses = [self.client.post("/auth/recuperar-senha", data={
            "email": f"unknown{i}@example.invalid", "csrf_token": csrf,
        }) for i in range(6)]
        self.assertEqual([response.status_code for response in responses], [302] * 5 + [429])

    def test_login_rate_limit_remains_active(self):
        csrf = self._csrf()
        responses = [self.client.post("/auth/login", data={
            "email": "unknown@example.invalid", "senha": "synthetic-wrong-password", "csrf_token": csrf,
        }) for _ in range(11)]
        self.assertEqual([response.status_code for response in responses], [200] * 10 + [429])


if __name__ == "__main__":
    unittest.main()
