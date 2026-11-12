"""Executa a sonda real do workflow com URIs sintéticas e PostgreSQL privado.

Nenhuma credencial ou conexão externa é aceita. Os testes PostgreSQL usam apenas
o cluster descartável por socket Unix de tests.postgresql_support.
"""

import contextlib
import io
import os
from pathlib import Path
import re
import textwrap
import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/nexo-supabase-bootstrap.yml"
SYNTHETIC_USER = "postgres.mgjdsbcohboxzcbicbuc"
SYNTHETIC_HOST = "aws-0-us-west-2.pooler.supabase.com"


def _probe_code():
    source = WORKFLOW.read_text(encoding="utf-8")
    step = source.split("      - name: Confirmar projeto, portas, TLS e estado inicial (somente leitura)", 1)[1]
    match = re.search(r"python - <<'PY'\n(.*?)\n          PY", step, re.S)
    if match is None:
        raise AssertionError("Sonda do bootstrap ausente no workflow.")
    return compile(textwrap.dedent(match.group(1)), str(WORKFLOW), "exec")


def _environment(scheme="postgresql"):
    base = f"{scheme}://{SYNTHETIC_USER}:synthetic-only@{SYNTHETIC_HOST}"
    return {
        "DATABASE_URL": base + ":6543/postgres?sslmode=require",
        "DIRECT_URL": base + ":5432/postgres?sslmode=require",
        "PGSSLMODE": "require",
    }


def _run_probe(factory, environment=None):
    # Substitui a única construção de engine antes de executar o código extraído.
    # Mesmo uma regressão da sonda nunca abre a URL Supabase sintética.
    with patch.dict(os.environ, environment or _environment(), clear=True), \
            patch("sqlalchemy.create_engine", side_effect=factory) as engine_factory, \
            contextlib.redirect_stdout(io.StringIO()):
        exec(_probe_code(), {"__name__": "__main__"})
    return engine_factory


class BootstrapDriverAndIdentityTests(unittest.TestCase):
    def test_every_accepted_uri_uses_the_installed_driver_before_connecting(self):
        for scheme in ("postgres", "postgresql", "postgresql+psycopg2"):
            with self.subTest(scheme=scheme):
                probe_engine = MagicMock()
                probe_engine.connect.return_value.__enter__.return_value.execute.return_value.scalars.return_value = []

                def construct(uri, **kwargs):
                    self.assertEqual(make_url(uri).drivername, "postgresql+psycopg2")
                    # Construir de verdade carrega o driver, sem abrir conexão.
                    engine = create_engine(uri, **kwargs)
                    self.assertEqual(engine.dialect.driver, "psycopg2")
                    engine.dispose()
                    return probe_engine

                factory = _run_probe(construct, _environment(scheme))
                factory.assert_called_once()
                probe_engine.dispose.assert_called_once()

    def test_wrong_project_host_port_or_tls_is_rejected_before_engine_creation(self):
        for value in (
            _environment()["DIRECT_URL"].replace(SYNTHETIC_USER, "postgres.other-project"),
            _environment()["DIRECT_URL"].replace(SYNTHETIC_HOST, "example.invalid"),
            _environment()["DIRECT_URL"].replace(":5432", ":6543"),
            _environment()["DIRECT_URL"].replace("sslmode=require", "sslmode=disable"),
        ):
            with self.subTest(value=value):
                environment = _environment()
                environment["DIRECT_URL"] = value
                factory = MagicMock(side_effect=AssertionError("Não pode criar engine com destino inválido."))
                with self.assertRaisesRegex(SystemExit, "não corresponde ao projeto"):
                    _run_probe(factory, environment)
                factory.assert_not_called()


@unittest.skipUnless(os.environ.get("NEXO_TEST_POSTGRES_BIN"), "PostgreSQL privado exige NEXO_TEST_POSTGRES_BIN.")
class BootstrapPostgreSQLGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests.postgresql_support import PrivatePostgreSQL
        cls.postgresql = PrivatePostgreSQL()
        cls.addClassCleanup(cls.postgresql.close)

    def setUp(self):
        self.database = self.postgresql.create_database()
        self.addCleanup(self.postgresql.drop_database, self.database)
        self.engine = create_engine(self.postgresql.url(self.database), connect_args={
            "connect_timeout": 5,
            "password": "",
            "passfile": str(self.postgresql.passfile),
            "options": "-c statement_timeout=15000 -c lock_timeout=10000",
        })
        self.addCleanup(self.engine.dispose)

    def _local_factory(self, uri, **kwargs):
        self.assertEqual(make_url(uri).drivername, "postgresql+psycopg2")
        self.assertEqual(self.engine.url.host, str(self.postgresql.socket))
        self.assertEqual(self.engine.url.database, self.database)
        return self.engine

    def _tables(self):
        with self.engine.connect() as conn:
            return set(conn.execute(text(
                "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public'"
            )).scalars())

    def test_empty_postgresql_database_passes_without_creating_tables(self):
        self.assertEqual(self._tables(), set())
        _run_probe(self._local_factory)
        self.assertEqual(self._tables(), set())

    def test_existing_table_blocks_bootstrap_without_changing_rows(self):
        with self.engine.begin() as conn:
            conn.execute(text("CREATE TABLE public.preexisting (id integer PRIMARY KEY, value text NOT NULL)"))
            conn.execute(text("INSERT INTO public.preexisting VALUES (1, 'preserve-me')"))
        with self.assertRaisesRegex(SystemExit, "bootstrap é exclusivo de banco novo"):
            _run_probe(self._local_factory)
        self.assertEqual(self._tables(), {"preexisting"})
        with self.engine.connect() as conn:
            self.assertEqual(conn.execute(text("SELECT id, value FROM public.preexisting")).all(), [(1, "preserve-me")])

    def test_alembic_version_alone_does_not_allow_reusing_an_existing_database(self):
        with self.engine.begin() as conn:
            conn.execute(text("CREATE TABLE public.alembic_version (version_num varchar(32) PRIMARY KEY)"))
            conn.execute(text("INSERT INTO public.alembic_version VALUES ('b6935e8de9d4')"))
        with self.assertRaisesRegex(SystemExit, "bootstrap é exclusivo de banco novo"):
            _run_probe(self._local_factory)
        self.assertEqual(self._tables(), {"alembic_version"})
        with self.engine.connect() as conn:
            self.assertEqual(conn.scalar(text("SELECT version_num FROM public.alembic_version")), "b6935e8de9d4")


if __name__ == "__main__":
    unittest.main()
