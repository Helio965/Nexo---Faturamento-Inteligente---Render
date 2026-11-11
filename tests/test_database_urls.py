"""Connection URL regressions using fictitious credentials, without network."""

import unittest
from urllib.parse import quote

from sqlalchemy.engine import make_url

from database_urls import (
    DatabaseURLValidationError,
    normalize_postgres_url,
    parse_postgres_url,
)


POOLER = "aws-0-us-west-2.pooler.supabase.com"
BASE = f"postgresql://postgres.mgjdsbcohboxzcbicbuc:fixture-secret@{POOLER}:6543/postgres"


class DatabaseURLTests(unittest.TestCase):
    def assert_invalid(self, value, expected_field=None):
        with self.assertRaises(DatabaseURLValidationError) as caught:
            parse_postgres_url(value)
        message = str(caught.exception)
        self.assertNotIn("fixture-secret", message)
        self.assertNotIn(POOLER, message)
        self.assertNotIn("postgres.mgjdsbcohboxzcbicbuc", message)
        self.assertTrue(caught.exception.fields)
        if expected_field:
            self.assertIn(expected_field, message)

    def test_aliases_use_installed_driver(self):
        for driver in ("postgres", "postgresql", "postgresql+psycopg2"):
            with self.subTest(driver=driver):
                result = parse_postgres_url(BASE.replace("postgresql://", driver + "://", 1))
                self.assertEqual(result.drivername, "postgresql+psycopg2")
                self.assertEqual(result.query["sslmode"], "require")

    def test_percent_encoded_password_roundtrips_exactly_once(self):
        for password in ("a@b:c/d#e[f]g%h", "%40", "a+b=c&d", "a space", "senha-ç"):
            with self.subTest(password=password):
                encoded = quote(password, safe="")
                value = BASE.replace("fixture-secret", encoded)
                parsed = parse_postgres_url(value)
                normalized = normalize_postgres_url(value)
                self.assertEqual(parsed.password, password)
                self.assertEqual(make_url(normalized).password, password)
                self.assertEqual(parse_postgres_url(normalized).password, password)
                self.assertEqual(normalize_postgres_url(normalized), normalized)

    def test_encoded_password_delimiters_cannot_override_destination(self):
        value = BASE.replace("fixture-secret", quote("x?host=other.invalid#@/[]", safe=""))
        parsed = parse_postgres_url(value)
        self.assertEqual(parsed.host, POOLER)
        self.assertEqual(parsed.port, 6543)
        self.assertEqual(parsed.password, "x?host=other.invalid#@/[]")

    def test_raw_password_delimiters_are_rejected_without_repair(self):
        for password in ("[YOUR-PASSWORD]", "demo[secret]", "x@y", "x:y", "123/x", "123?x", "x#y"):
            with self.subTest(password=password):
                self.assert_invalid(BASE.replace("fixture-secret", password))

    def test_placeholder_remains_invalid_when_encoded(self):
        for placeholder in ("[YOUR-PASSWORD]", "YOUR_PASSWORD", "<password>"):
            with self.subTest(placeholder=placeholder):
                self.assert_invalid(BASE.replace("fixture-secret", quote(placeholder, safe="")), "senha real")

    def test_malformed_percent_escapes_are_rejected(self):
        for password in ("x%", "x%2", "x%GG"):
            with self.subTest(password=password):
                self.assert_invalid(BASE.replace("fixture-secret", password), "codificação percentual")

    def test_whitespace_controls_and_external_quotes_are_rejected(self):
        for value in (" " + BASE, BASE + "\n", "'" + BASE + "'", '"' + BASE + '"',
                      BASE.replace("fixture-secret", "x\ty"),
                      BASE.replace("fixture-secret", "x%00y"),
                      BASE.replace("fixture-secret", "x%09y"),
                      BASE + "?application_name=x%0Ay"):
            with self.subTest(value=value):
                self.assert_invalid(value)

    def test_prisma_parameters_removed_but_valid_options_preserved(self):
        parsed = parse_postgres_url(
            BASE + "?pgbouncer=true&connection_limit=1&pool_timeout=5&schema=public"
            "&application_name=nexo&connect_timeout=15&options=-c%20statement_timeout%3D5000"
        )
        self.assertEqual(dict(parsed.query), {
            "sslmode": "require", "application_name": "nexo", "connect_timeout": "15",
            "options": "-c statement_timeout=5000",
        })

    def test_secure_tls_modes_are_preserved(self):
        for mode in ("require", "verify-ca", "verify-full"):
            with self.subTest(mode=mode):
                parsed = parse_postgres_url(BASE + f"?sslmode={mode}&sslrootcert=system")
                self.assertEqual(parsed.query["sslmode"], mode)
                self.assertEqual(parsed.query["sslrootcert"], "system")

    def test_blank_insecure_and_duplicate_tls_values_fail_closed(self):
        for query in ("sslmode=", "sslmode=disable", "sslmode=prefer", "sslmode=allow",
                      "sslmode=require&sslmode=disable", "sslmode=require&SSLMODE=require",
                      "sslrootcert=", "sslmode=require&sslmode=", "sslmode=require&sslrootcert="):
            with self.subTest(query=query):
                self.assert_invalid(BASE + "?" + query)

    def test_destination_and_other_tls_overrides_are_rejected(self):
        for key in ("host", "hostaddr", "port", "dbname", "user", "password", "service",
                    "servicefile", "passfile", "sslcert", "sslkey", "sslpassword",
                    "sslnegotiation", "%68ost", "HOST"):
            with self.subTest(key=key):
                self.assert_invalid(BASE + "?" + key + "=fixture-secret")

    def test_generic_local_postgres_keeps_transport_unspecified(self):
        result = parse_postgres_url("postgresql://localhost:5432/nexo_test")
        self.assertEqual(dict(result.query), {})
        self.assertEqual(result.host, "localhost")

    def test_unix_socket_supplies_the_only_destination(self):
        for port_query in ("", "&port=5432"):
            with self.subTest(port_query=port_query):
                value = "postgresql+psycopg2://localuser@/nexo_test?host=%2Ftmp%2Fnexo%2Fsock" + port_query
                result = parse_postgres_url(value)
                self.assertIsNone(result.host)
                self.assertIsNone(result.port)
                self.assertEqual(result.query["host"], "/tmp/nexo/sock")
                # Verify actual driver arguments without opening a connection.
                args, parameters = result.get_dialect()().create_connect_args(result)
                self.assertEqual(args, [])
                self.assertEqual(parameters["host"], "/tmp/nexo/sock")
                self.assertEqual(parameters["dbname"], "nexo_test")
                if port_query:
                    self.assertEqual(str(parameters["port"]), "5432")
                self.assertEqual(parse_postgres_url(normalize_postgres_url(value)), result)

    def test_socket_syntax_does_not_allow_overrides_or_multihost_destinations(self):
        prefix = "postgresql://localuser@/nexo_test?"
        for value in (
            BASE + "?host=%2Ftmp%2Fsock&port=5432",
            "postgresql://localuser@:5432/nexo_test?host=%2Ftmp%2Fsock",
            prefix + "host=relative%2Fsock&port=5432",
            prefix + "host=network.invalid&port=5432",
            prefix + "host=%2Ftmp%2Fsock%2Cnetwork.invalid&port=5432",
            prefix + "host=%2Ftmp%2Fsock&host=%2Ftmp%2Fother",
            prefix + "host=%2Ftmp%2Fsock%00&port=5432",
            prefix + "host=%2Ftmp%2Fsock&port=5432%2C6543",
            prefix + "host=%2Ftmp%2Fsock&port=invalid",
            prefix + "host=%2Ftmp%2Fsock&port=0",
            prefix + "host=%2Ftmp%2Fsock&port=65536",
            prefix + "host=%2Ftmp%2Fsock&port=",
            prefix + "port=5432",
            prefix + "host=%2Ftmp%2Fsock&hostaddr=127.0.0.1",
            prefix + "host=%2Ftmp%2Fsock&service=other",
        ):
            with self.subTest(value=value):
                self.assert_invalid(value)

    def test_supabase_direct_and_pooler_require_tls_by_default(self):
        for host in (POOLER, "db.mgjdsbcohboxzcbicbuc.supabase.co"):
            with self.subTest(host=host):
                result = parse_postgres_url(f"postgresql://u:fixture-secret@{host}:5432/postgres")
                self.assertEqual(result.query["sslmode"], "require")

    def test_invalid_driver_and_port_produce_sanitized_diagnostics(self):
        for value in ("mysql://u:fixture-secret@localhost/db", BASE.replace(":6543/", ":invalid/")):
            with self.subTest(value=value):
                self.assert_invalid(value)


if __name__ == "__main__":
    unittest.main()
