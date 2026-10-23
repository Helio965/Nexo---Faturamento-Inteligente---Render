"""Migração SEC-004 real em cluster PostgreSQL privado, sem DSN existente."""

import unittest

from sqlalchemy import event, inspect, text
from sqlalchemy.exc import DBAPIError

from . import test_company_restore_migration as migration_cases
from .postgresql_support import PrivatePostgreSQL


class PostgreSQLCompanyRestoreMigrationTests(migration_cases.CompanyRestoreMigrationCases, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.postgresql = PrivatePostgreSQL()
        cls.addClassCleanup(cls.postgresql.close)

    def setUp(self):
        database = self.postgresql.create_database()
        self.addCleanup(self.postgresql.drop_database, database)
        self._create_app(self.postgresql.url(database), {
            "connect_args": {
                "connect_timeout": 5,
                "password": "",
                "passfile": str(self.postgresql.passfile),
                "options": "-c statement_timeout=15000 -c lock_timeout=10000",
            },
        })
        self.assertEqual(self.engine.url.host, str(self.postgresql.socket))
        self.assertEqual(self.engine.url.database, database)

    def test_postgresql_failure_rolls_back_column_data_and_revision_atomically(self):
        failed = []

        def fail_legacy_update(connection, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith("UPDATE USUARIO SET"):
                failed.append(True)
                # Erro real, dentro da transação que já executou o ADD COLUMN.
                cursor.execute("SELECT 1 / 0")

        event.listen(self.engine, "before_cursor_execute", fail_legacy_update)
        try:
            with self.assertRaises(DBAPIError):
                self._upgrade()
        finally:
            event.remove(self.engine, "before_cursor_execute", fail_legacy_update)
        self.assertEqual(failed, [True])
        self.assertEqual(self._revision(), migration_cases.OLD_HEAD)
        self.assertNotIn("geracao_autorizacao", {
            item["name"] for item in inspect(self.engine).get_columns("usuario")
        })
        self.assertEqual(self._counts(), self.before_counts)
        with self.engine.connect() as connection:
            self.assertTrue(connection.scalar(text("SELECT ativo FROM usuario WHERE id_usuario=4")))
        # Recuperada a causa, a mesma revisão pode ser aplicada integralmente.
        self._upgrade()
        self.assertEqual(self._states()[4][:2], (False, 1))
