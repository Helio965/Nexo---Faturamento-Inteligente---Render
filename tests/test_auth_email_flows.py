"""Fluxos reais de e-mail/token com Jinja e transporte controlado, sem rede."""

import html
import json
import logging
import re
import time
from urllib.parse import urlsplit
from unittest.mock import Mock, patch

from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import check_password_hash

from blueprints import admin, auth
import emails
from extensions import db
from models import Usuario
from tests.test_auth_tokens_security import _TokenCase, FIXTURE_HASH, NEW_PASSWORD, OLD_PASSWORD


class AuthEmailFlowTests(_TokenCase):
    def setUp(self):
        super().setUp()
        # Recoloca os helpers reais: os testes SEC002 básicos mockam esta borda.
        for target, name in (
            (auth, "email_recuperacao_senha"), (auth, "email_boas_vindas"),
            (admin, "email_boas_vindas"),
        ):
            self.stack.enter_context(patch.object(target, name, getattr(emails, name)))
        self.app.config.update(
            MAIL_ATIVO=True, BREVO_API_KEY=None,
            BREVO_API_URL="https://mail-test.example.invalid/v3/smtp/email",
            MAIL_DEFAULT_SENDER="sender@example.invalid",
        )
        self.jobs, self.sent = [], []
        jobs = self.jobs

        class QueuedThread:
            def __init__(thread, target, args, daemon):
                thread.target, thread.args = target, args
                self.assertTrue(daemon)

            def start(thread):
                jobs.append(thread)

            def run(thread):
                thread.target(*thread.args)

        self.thread = self.stack.enter_context(patch.object(emails.threading, "Thread", QueuedThread))
        self.transport = self.stack.enter_context(patch.object(emails.mail, "send", side_effect=self.sent.append))
        self.stack.enter_context(patch.object(emails.logger, "disabled", False))

    def _deliver_to_fake_transport(self):
        jobs, self.jobs[:] = list(self.jobs), []
        for job in jobs:
            job.run()

    def _link(self, message):
        links = [html.unescape(link) for link in re.findall(r'href="([^"]+)"', message.html)]
        links = [link for link in links if urlsplit(link).path.startswith((
            "/auth/primeiro-acesso/", "/auth/resetar-senha/",
        ))]
        self.assertEqual(len(links), 1)
        return links[0]

    def _request_message(self, email):
        response = self._request_link(email)
        self.assertEqual(len(self.jobs), 1)
        self.assertEqual(len(self.sent), 0)
        self._deliver_to_fake_transport()
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.sent[0].recipients, [email])
        self.assertNotIn(self._link(self.sent[0]), response.get_data(as_text=True))
        return self.sent[0]

    def _login_and_check_portal(self, email, password, accepted=True):
        client = self.app.test_client()
        response = client.post("/auth/login", data={
            "email": email, "senha": password, "csrf_token": self._csrf(client),
        })
        self.assertEqual(response.status_code, 302 if accepted else 200)
        if accepted:
            self.assertTrue(response.headers["Location"].endswith("/cliente/dashboard"))
            self.assertEqual(client.get(response.headers["Location"]).status_code, 200)

    def test_registration_renders_activation_email_then_activates_and_logs_in(self):
        client = self.app.test_client()
        client.post("/auth/login", data={
            "email": "admin@example.invalid", "senha": OLD_PASSWORD,
            "csrf_token": self._csrf(client),
        })
        response = client.post("/admin/empresas/nova", data={
            "csrf_token": self._csrf(client, "/admin/empresas/nova"),
            "data_contratacao": "2026-01-01", "id_segmento": str(self.segment_id),
            "id_plano_atual": str(self.plan_id), "cnpj": "99999999999999",
            "razao_social": "Synthetic email company", "email_contato": "company-new@example.invalid",
            "usuario_nome": "Synthetic New", "usuario_email": "new@example.invalid",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(self.jobs), 1)
        self._deliver_to_fake_transport()
        message = self.sent[0]
        self.assertEqual(message.recipients, ["new@example.invalid"])
        self.assertIn("Bem-vindo", message.subject)
        self.assertIn("Definir Senha de Acesso", message.html)
        self.assertIn("15 minutos", message.html)
        self.assertNotIn(NEW_PASSWORD, message.html)
        link = self._link(message)
        token = urlsplit(link).path.rsplit("/", 1)[1]
        self.assertTrue(urlsplit(link).path.startswith("/auth/primeiro-acesso/"))
        anonymous = self.app.test_client()
        self.assertEqual(anonymous.get(link).status_code, 200)
        self._assert_success(self._post(token, "activation", client=anonymous))
        with self.app.app_context():
            account = db.session.query(Usuario).filter_by(email="new@example.invalid").one()
            self.assertFalse(account.primeiro_acesso)
            self.assertTrue(check_password_hash(account.senha_hash, NEW_PASSWORD))
        self._login_and_check_portal("new@example.invalid", NEW_PASSWORD)
        self._assert_rejected(self._post(token, "activation", client=anonymous))

    def test_recovery_renders_email_and_rejects_old_password_and_replay(self):
        message = self._request_message("active@example.invalid")
        self.assertIn("Redefinição", message.subject)
        self.assertIn("Redefinir minha senha", message.html)
        self.assertIn("15 minutos", message.html)
        self.assertNotIn(FIXTURE_HASH, message.html)
        self.assertNotIn(OLD_PASSWORD, message.html)
        token = urlsplit(self._link(message)).path.rsplit("/", 1)[1]
        self._assert_success(self._post(token))
        self._login_and_check_portal("active@example.invalid", OLD_PASSWORD, accepted=False)
        self._login_and_check_portal("active@example.invalid", NEW_PASSWORD)
        self._assert_rejected(self._post(token))

    def test_expired_activation_is_reissued_with_real_template(self):
        now = int(time.time())
        with patch("itsdangerous.timed.TimestampSigner.get_timestamp", return_value=now):
            old_token = self._token("pending", "activation")
        with patch("itsdangerous.timed.TimestampSigner.get_timestamp", return_value=now + 901):
            self._assert_rejected(self._post(old_token, "activation"))
            message = self._request_message("pending@example.invalid")
            self.assertIn("Bem-vindo", message.subject)
            new_token = urlsplit(self._link(message)).path.rsplit("/", 1)[1]
            self.assertNotEqual(old_token, new_token)
            self._assert_success(self._post(new_token, "activation"))
            self._assert_rejected(self._post(old_token, "activation"))

    def test_legacy_link_rejected_and_recovery_can_issue_current_link(self):
        with self.app.app_context():
            old = URLSafeTimedSerializer(
                self.app.config["SECRET_KEY"], salt="nexo-reset-senha-v1",
            ).dumps("active@example.invalid")
        self._assert_rejected(self._post(old))
        message = self._request_message("active@example.invalid")
        token = urlsplit(self._link(message)).path.rsplit("/", 1)[1]
        self._assert_success(self._post(token))

    def test_thread_start_failure_returns_false_and_public_request_stays_generic(self):
        failed_thread = Mock()
        failed_thread.start.side_effect = RuntimeError("PRIVATE_SCHEDULER_SENTINEL")
        with patch.object(emails.threading, "Thread", return_value=failed_thread), \
                self.assertLogs(emails.logger, level=logging.WARNING) as logs:
            response = self._request_link("active@example.invalid")
        body = response.get_data(as_text=True)
        self.assertIn("Se o e-mail estiver cadastrado", body)
        self.assertNotIn("PRIVATE_SCHEDULER_SENTINEL", "\n".join(logs.output) + body)
        self.assertIn("RuntimeError", "\n".join(logs.output))
        self.assertEqual(self.jobs, [])
        self.transport.assert_not_called()
        self.assertEqual(self._account()[0], FIXTURE_HASH)

    def test_template_failure_returns_false_without_publishing_context(self):
        with self.app.test_request_context(), \
                patch.object(emails, "render_template", side_effect=ValueError("PRIVATE_TEMPLATE_SENTINEL")), \
                self.assertLogs(emails.logger, level=logging.WARNING) as logs:
            queued = emails.email_recuperacao_senha(
                db.session.get(Usuario, self.ids["active"]),
                "https://app.example.invalid/auth/resetar-senha/private-token",
            )
        self.assertFalse(queued)
        self.assertNotIn("PRIVATE_TEMPLATE_SENTINEL", "\n".join(logs.output))
        self.assertNotIn("private-token", "\n".join(logs.output))
        self.assertEqual(self.jobs, [])

    def test_async_failure_after_true_is_sanitized_and_does_not_claim_delivery(self):
        with self.app.test_request_context():
            queued = emails.email_recuperacao_senha(
                db.session.get(Usuario, self.ids["active"]),
                "https://app.example.invalid/auth/resetar-senha/private-token",
            )
        self.assertTrue(queued)
        self.transport.side_effect = RuntimeError("PRIVATE_PROVIDER_SENTINEL")
        with self.assertLogs(emails.logger, level=logging.WARNING) as logs:
            self._deliver_to_fake_transport()
        self.assertIn("RuntimeError", "\n".join(logs.output))
        self.assertNotIn("PRIVATE_PROVIDER_SENTINEL", "\n".join(logs.output))
        self.assertNotIn("private-token", "\n".join(logs.output))
        self.assertEqual(self.sent, [])
        self.assertEqual(self._account()[0], FIXTURE_HASH)

    def test_success_log_means_transport_acceptance_not_recipient_delivery(self):
        self._request_link("active@example.invalid")
        with self.assertLogs(emails.logger, level=logging.INFO) as logs:
            self._deliver_to_fake_transport()
        self.assertIn("aceito pelo transporte", "\n".join(logs.output))
        self.assertNotIn("entregue", "\n".join(logs.output))
        self.assertNotIn(self._link(self.sent[0]), "\n".join(logs.output))

    def test_real_brevo_adapter_receives_rendered_message_without_network(self):
        self.app.config["BREVO_API_KEY"] = "synthetic-test-key"
        self._request_link("active@example.invalid")
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        with patch.object(emails.urllib.request, "urlopen", return_value=response) as http:
            self._deliver_to_fake_transport()
        self.transport.assert_not_called()
        request = http.call_args.args[0]
        self.assertEqual(request.full_url, self.app.config["BREVO_API_URL"])
        self.assertEqual(request.method, "POST")
        payload = json.loads(request.data)
        self.assertEqual(payload["to"], [{"email": "active@example.invalid"}])
        self.assertIn("Redefinir minha senha", payload["htmlContent"])
        self.assertIn("/auth/resetar-senha/", payload["htmlContent"])

    def test_suppressed_registration_does_not_publish_token_or_claim_sent(self):
        self.app.config.update(MAIL_ATIVO=False, DEBUG=True)
        client = self.app.test_client()
        client.post("/auth/login", data={
            "email": "admin@example.invalid", "senha": OLD_PASSWORD,
            "csrf_token": self._csrf(client),
        })
        response = client.post("/admin/empresas/nova", data={
            "csrf_token": self._csrf(client, "/admin/empresas/nova"),
            "data_contratacao": "2026-01-01", "id_segmento": str(self.segment_id),
            "id_plano_atual": str(self.plan_id), "cnpj": "99999999999999",
            "razao_social": "Synthetic suppressed", "email_contato": "company-new@example.invalid",
            "usuario_nome": "Synthetic New", "usuario_email": "new@example.invalid",
        })
        self.assertEqual(response.status_code, 302)
        with client.session_transaction() as session:
            messages = " ".join(text for category, text in session.get("_flashes", []))
        self.assertIn("Não foi possível agendar", messages)
        self.assertNotIn("/auth/primeiro-acesso/", messages)
        self.assertNotIn("Enviamos", messages)
        self.assertEqual(self.jobs, [])
