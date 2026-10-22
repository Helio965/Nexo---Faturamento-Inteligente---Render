"""Logs Flask/Werkzeug/Gunicorn e respostas de bearer sem serviços reais."""

import io
import logging
import unittest

from gunicorn.glogging import SafeAtoms
from itsdangerous import URLSafeTimedSerializer

from log_security import install_token_log_redaction
from tests.test_auth_tokens_security import _TokenCase


class SensitiveLogFactoryTests(unittest.TestCase):
    def setUp(self):
        self.previous_factory = logging.getLogRecordFactory()
        self.addCleanup(logging.setLogRecordFactory, self.previous_factory)
        install_token_log_redaction()
        self.token = URLSafeTimedSerializer("isolated-log-test-key").dumps({
            "uid": 42, "purpose": "recovery", "synthetic": "repeated" * 40,
        })

    def _logger(self, name):
        logger = logging.getLogger(name)
        old = logger.handlers[:], logger.level, logger.propagate, logger.disabled
        def restore():
            logger.handlers[:], logger.level, logger.propagate, logger.disabled = old
        self.addCleanup(restore)
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.Formatter("%(name)s %(levelname)s %(message)s"))
        logger.handlers[:] = [handler]
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        logger.disabled = False
        return logger, stream

    def test_install_is_idempotent_and_preserves_existing_factory(self):
        installed = logging.getLogRecordFactory()
        install_token_log_redaction()
        self.assertIs(logging.getLogRecordFactory(), installed)
        calls = []
        def upstream(*args, **kwargs):
            record = self.previous_factory(*args, **kwargs)
            calls.append(record)
            record.upstream_marker = True
            return record
        logging.setLogRecordFactory(upstream)
        install_token_log_redaction()
        logger, stream = self._logger("nexo.tests.factory")
        logger.info("ordinary %s %d", "message", 7)
        self.assertEqual(stream.getvalue().strip(), "nexo.tests.factory INFO ordinary message 7")
        self.assertEqual(calls[-1].args, ("message", 7))
        self.assertTrue(calls[-1].upstream_marker)

    def test_werkzeug_and_gunicorn_request_and_referer_paths_are_redacted(self):
        for name in ("werkzeug", "gunicorn.access", "gunicorn.error"):
            with self.subTest(logger=name):
                logger, stream = self._logger(name)
                logger.info('"GET %s HTTP/1.1" referer="%s" status=%d',
                            "/auth/resetar-senha/" + self.token,
                            "https://app.example.invalid/auth/primeiro-acesso/" + self.token, 200)
                text = stream.getvalue()
                self.assertNotIn(self.token, text)
                self.assertIn("/auth/resetar-senha/[REDACTED]", text)
                self.assertIn("/auth/primeiro-acesso/[REDACTED]", text)
                self.assertIn("status=200", text)

    def test_gunicorn_safe_atoms_mapping_keeps_custom_header_default(self):
        logger, stream = self._logger("gunicorn.access")
        atoms = SafeAtoms({
            "r": "GET /auth/resetar-senha/" + self.token + " HTTP/1.1",
            "f": "https://app.example.invalid/auth/primeiro-acesso/" + self.token,
        })
        logger.info('%(r)s "%(f)s" %({x-missing}i)s', atoms)
        self.assertNotIn(self.token, stream.getvalue())
        self.assertIn("HTTP/1.1", stream.getvalue())
        self.assertTrue(stream.getvalue().rstrip().endswith('" -'))

    def test_signed_bearer_alone_in_exception_is_redacted_and_stack_is_preserved(self):
        logger, stream = self._logger("nexo.tests.exception")
        try:
            raise ValueError(self.token)
        except ValueError:
            logger.exception("Falha de teste")
        text = stream.getvalue()
        self.assertNotIn(self.token, text)
        self.assertIn("Traceback", text)
        self.assertIn("ValueError: [REDACTED]", text)
        self.assertIn("test_sensitive_http_logs.py", text)

    def test_short_or_percent_encoded_path_token_is_redacted(self):
        logger, stream = self._logger("werkzeug")
        logger.info("%s %s", "/auth/resetar-senha/x%2Ey%2Ez?query=synthetic",
                    "/auth/primeiro-acesso/short-token")
        self.assertNotIn("x%2Ey%2Ez", stream.getvalue())
        self.assertNotIn("short-token", stream.getvalue())

    def test_encoded_route_prefix_and_bare_signed_token_are_redacted(self):
        logger, stream = self._logger("gunicorn.access")
        logger.info("%s", "/%61uth/%72esetar-senha/" + self.token.replace(".", "%2E"))
        logger.info("%s", self.token)
        self.assertNotIn(self.token, stream.getvalue())
        self.assertNotIn(self.token.replace(".", "%2E"), stream.getvalue())
        self.assertEqual(stream.getvalue().count("[REDACTED]"), 2)

    def test_invalid_format_does_not_raise_or_print_sensitive_arguments(self):
        logger, stream = self._logger("gunicorn.error")
        logger.info("Código %d", self.token)
        self.assertNotIn(self.token, stream.getvalue())
        self.assertIn("formatação inválida", stream.getvalue())


class SensitiveHttpResponseTests(_TokenCase):
    def test_token_pages_and_rejections_prevent_referrers_and_caching(self):
        for purpose, user in (("recovery", "active"), ("activation", "pending")):
            token = self._token(user, purpose)
            for value in (token, "invalid-token"):
                with self.subTest(purpose=purpose, valid=value == token):
                    response = self.client.get(self._path(value, purpose))
                    self.assertIn(response.status_code, (200, 302))
                    self.assertEqual(response.headers["Referrer-Policy"], "no-referrer")
                    self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_token_post_success_and_csrf_error_keep_security_headers(self):
        token = self._token()
        missing_csrf = self.client.post(self._path(token), data={})
        success = self._post(token)
        for response, status in ((missing_csrf, 400), (success, 302)):
            self.assertEqual(response.status_code, status)
            self.assertEqual(response.headers["Referrer-Policy"], "no-referrer")
            self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_real_flask_exception_log_redacts_request_path_and_exception(self):
        self.app.config.update(TESTING=False, PROPAGATE_EXCEPTIONS=False)
        token = self._token()
        @self.app.route("/auth/resetar-senha/<token>/synthetic-error")
        def synthetic_error(token):
            raise ValueError(token)

        logger = self.app.logger
        previous = logger.handlers[:], logger.level, logger.propagate, logger.disabled
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        logger.handlers[:] = [handler]
        logger.setLevel(logging.ERROR)
        logger.propagate = False
        logger.disabled = False
        try:
            response = self.client.get(self._path(token) + "/synthetic-error")
        finally:
            logger.handlers[:], logger.level, logger.propagate, logger.disabled = previous
        self.assertEqual(response.status_code, 500)
        self.assertNotIn(token, stream.getvalue())
        self.assertIn("Traceback", stream.getvalue())
        self.assertIn("ValueError: [REDACTED]", stream.getvalue())
        self.assertIn("/auth/resetar-senha/[REDACTED]/synthetic-error", stream.getvalue())
        self.assertEqual(response.headers["Referrer-Policy"], "no-referrer")
        self.assertEqual(response.headers["Cache-Control"], "no-store")
