"""Logs de e-mail sem dados privados, com transportes e rede isolados."""

import contextlib
import io
import smtplib
import traceback
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from flask import Flask

import emails


class EmailLoggingTests(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        for target in ("socket.socket.connect", "socket.socket.connect_ex", "socket.create_connection"):
            self.stack.enter_context(patch(target, side_effect=AssertionError("Rede proibida no teste")))
        # Migrações executadas por outros testes podem desabilitar este logger.
        self.stack.enter_context(patch.object(emails.logger, "disabled", False))
        self.app = Flask(__name__)
        self.app.config.update(
            BREVO_API_KEY=None,
            BREVO_API_URL="https://email-test.example.invalid/v3/smtp/email",
        )
        self.message = SimpleNamespace(
            sender="sender-test@example.invalid",
            recipients=["recipient-test@example.invalid"],
            subject="PRIVATE_SUBJECT_SENTINEL",
            html="<p>PRIVATE_BODY_SENTINEL</p>",
        )

    def assert_no_private_content(self, output):
        for value in (self.message.sender, *self.message.recipients,
                      self.message.subject, "PRIVATE_BODY_SENTINEL", "PRIVATE_ERROR_SENTINEL"):
            self.assertNotIn(value, output)

    def test_success_logs_no_subject_or_addresses(self):
        for transport in ("smtp", "brevo"):
            with self.subTest(transport=transport):
                self.app.config["BREVO_API_KEY"] = "fake-test-key" if transport == "brevo" else None
                with patch.object(emails.mail, "send") as smtp, \
                        patch.object(emails, "_enviar_brevo") as brevo, \
                        self.assertLogs(emails.logger, level="INFO") as logs:
                    emails._enviar_async(self.app, self.message)
                if transport == "smtp":
                    smtp.assert_called_once_with(self.message)
                    brevo.assert_not_called()
                else:
                    brevo.assert_called_once_with(self.app, self.message)
                    smtp.assert_not_called()
                self.assertEqual(len(logs.records), 1)
                self.assertEqual(logs.records[0].levelname, "INFO")
                self.assert_no_private_content("\n".join(logs.output))

    def test_smtp_failure_logs_only_exception_type(self):
        error = smtplib.SMTPRecipientsRefused({
            self.message.recipients[0]: (550, b"PRIVATE_ERROR_SENTINEL"),
        })
        with patch.object(emails.mail, "send", side_effect=error) as send, \
                self.assertLogs(emails.logger, level="WARNING") as logs:
            emails._enviar_async(self.app, self.message)
        send.assert_called_once_with(self.message)
        self.assertEqual(len(logs.records), 1)
        self.assertIn("SMTPRecipientsRefused", logs.records[0].getMessage())
        self.assertIsNone(logs.records[0].exc_info)
        self.assert_no_private_content("\n".join(logs.output))

    def _brevo_error(self):
        return HTTPError(
            self.app.config["BREVO_API_URL"], 400, "PRIVATE_ERROR_SENTINEL",
            hdrs=None, fp=io.BytesIO(b'{"message": "PRIVATE_BODY_SENTINEL"}'),
        )

    def test_brevo_error_does_not_expose_provider_body_or_context(self):
        self.app.config["BREVO_API_KEY"] = "fake-test-key"
        with patch.object(emails.urllib.request, "urlopen", side_effect=self._brevo_error()) as request:
            with self.assertRaises(RuntimeError) as caught:
                emails._enviar_brevo(self.app, self.message)
        request.assert_called_once()
        self.assertEqual(str(caught.exception), "Brevo HTTP 400")
        self.assertTrue(caught.exception.__suppress_context__)
        self.assert_no_private_content("".join(traceback.format_exception(caught.exception)))

    def test_brevo_failure_logs_no_provider_body(self):
        self.app.config["BREVO_API_KEY"] = "fake-test-key"
        with patch.object(emails.urllib.request, "urlopen", side_effect=self._brevo_error()) as request, \
                patch.object(emails.mail, "send") as smtp, \
                self.assertLogs(emails.logger, level="WARNING") as logs:
            emails._enviar_async(self.app, self.message)
        request.assert_called_once()
        smtp.assert_not_called()
        self.assertEqual(len(logs.records), 1)
        self.assertIn("RuntimeError", logs.records[0].getMessage())
        self.assertIsNone(logs.records[0].exc_info)
        self.assert_no_private_content("\n".join(logs.output))


if __name__ == "__main__":
    unittest.main()
