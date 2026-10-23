"""Migração SEC-004 real, a partir do head anterior, sem dados/serviços reais."""

from datetime import date, datetime
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from flask import Flask
from flask_migrate import downgrade, upgrade
from sqlalchemy import MetaData, event, inspect, select, text
from sqlalchemy.exc import IntegrityError

from extensions import db, migrate


OLD_HEAD = "b7c4e2a9f031"
NEW_HEAD = "e4c004a26b01"
MIGRATIONS = str(Path(__file__).resolve().parents[1] / "migrations")


class CompanyRestoreMigrationCases:
    """Os mesmos cenários rodam em SQLite e em PostgreSQL privado explícito."""

    def _create_app(self, uri, engine_options=None):
        self.work = tempfile.TemporaryDirectory(prefix="nexo-sec004-migration-")
        self.addCleanup(self.work.cleanup)
        self.app = Flask(__name__, instance_path=self.work.name)
        self.app.config.update(
            TESTING=True,
            SECRET_KEY="synthetic-migration-only",
            SQLALCHEMY_DATABASE_URI=uri,
            SQLALCHEMY_ENGINE_OPTIONS=engine_options or {},
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
        )
        db.init_app(self.app)
        migrate.init_app(self.app, db)
        with self.app.app_context():
            self.engine = db.engine
            if self.engine.dialect.name == "sqlite":
                @event.listens_for(self.engine, "connect")
                def enforce_foreign_keys(connection, record):
                    connection.execute("PRAGMA foreign_keys = ON")
            # O esquema vem das revisões reais, não do metadata já atualizado.
            self._run_migration(upgrade, OLD_HEAD)
            self.assertEqual(self._revision(), OLD_HEAD)
            self.assertNotIn(
                "geracao_autorizacao",
                {item["name"] for item in inspect(self.engine).get_columns("usuario")},
            )
            self._seed_previous_schema()
            self.before_constraints = self._constraints()
            self.before_counts = self._counts()
        self.addCleanup(self._dispose)

    def _dispose(self):
        with self.app.app_context():
            db.session.remove()
            self.engine.dispose()

    def _run_migration(self, operation, revision):
        # env.py configura logging global; não deixar o teste desabilitar os
        # loggers dos testes de autenticação que rodam depois no mesmo processo.
        # Somente logging é isolado; todas as revisões e o DDL são reais.
        with patch("logging.config.fileConfig"):
            operation(directory=MIGRATIONS, revision=revision)

    def _revision(self):
        with self.engine.connect() as connection:
            return connection.scalar(text("SELECT version_num FROM alembic_version"))

    def _tables(self):
        metadata = MetaData()
        metadata.reflect(bind=self.engine)
        return metadata.tables

    def _seed_previous_schema(self):
        tables = self._tables()
        with self.engine.begin() as connection:
            connection.execute(tables["plano"].insert(), dict(
                id_plano=1, nome_plano="BRONZE", valor_mensal=50,
                qtd_analises_mes=1, tipo_analise_permitida="MENSAL",
                nivel_entrega_analise="BASICA", nivel_dashboard="RESUMIDO",
                nivel_atendimento="BAIXO", ativo=True,
            ))
            connection.execute(tables["segmento"].insert(), dict(
                id_segmento=1, nome_segmento="Sintético", ativo=True,
            ))
            for identifier, deleted in ((1, None), (2, datetime(2026, 1, 1))):
                connection.execute(tables["empresa"].insert(), dict(
                    id_empresa=identifier, id_plano_atual=1, id_segmento=1,
                    cnpj=f"SYNTHETIC-{identifier}", razao_social=f"Empresa {identifier}",
                    email_contato=f"company{identifier}@example.invalid",
                    data_contratacao=date(2026, 1, 1), status_conta="ATIVA",
                    deletado_em=deleted,
                ))
            for identifier, company, active, role in (
                (1, 1, True, "CLIENTE"), (2, 1, False, "CLIENTE"),
                (3, 2, False, "CLIENTE"), (4, 2, True, "CLIENTE"),
                (5, None, True, "ADMIN"), (6, None, False, "ADMIN"),
            ):
                connection.execute(tables["usuario"].insert(), dict(
                    id_usuario=identifier, id_empresa=company, ativo=active,
                    role=role, nome=f"Pessoa {identifier}",
                    email=f"user{identifier}@example.invalid", senha_hash="synthetic-no-login-hash",
                    primeiro_acesso=identifier == 4,
                    # Datas contraditórias não são usadas como prova de ativo.
                    ultimo_acesso=datetime(2026, 2, 1) if identifier == 3 else None,
                ))
            connection.execute(tables["notificacao"].insert(), dict(
                id_notificacao=1, id_usuario=3, texto="Dado sintético preservado", lida=False,
            ))
            connection.execute(tables["chamado_suporte"].insert(), dict(
                id_chamado=1, id_empresa=2, id_usuario_cliente=3,
                assunto="Histórico sintético", categoria="DUVIDA_TECNICA",
                status_chamado="ABERTO", prioridade="BAIXA",
            ))
            connection.execute(tables["mensagem_suporte"].insert(), dict(
                id_mensagem=1, id_chamado=1, id_usuario_remetente=3,
                mensagem="Histórico sintético preservado", lida=False,
            ))

    def _constraints(self):
        inspector = inspect(self.engine)
        return {
            table: {
                "checks": sorted(
                    (item.get("name") or "", " ".join(item["sqltext"].split()))
                    for item in inspector.get_check_constraints(table)
                ),
                "unique": sorted(tuple(item["column_names"]) for item in inspector.get_unique_constraints(table)),
                "fks": sorted(
                    (tuple(item["constrained_columns"]), item["referred_table"], tuple(item["referred_columns"]))
                    for item in inspector.get_foreign_keys(table)
                ),
                "pk": tuple(inspector.get_pk_constraint(table)["constrained_columns"]),
            }
            for table in inspector.get_table_names() if table != "alembic_version"
        }

    def _counts(self):
        tables = self._tables()
        with self.engine.connect() as connection:
            return {name: connection.scalar(select(db.func.count()).select_from(table))
                    for name, table in tables.items() if name != "alembic_version"}

    def _upgrade(self):
        with self.app.app_context():
            self._run_migration(upgrade, NEW_HEAD)
        self.assertEqual(self._revision(), NEW_HEAD)

    def _states(self):
        usuario = self._tables()["usuario"]
        with self.engine.connect() as connection:
            return {row.id_usuario: tuple(row[1:]) for row in connection.execute(
                select(usuario.c.id_usuario, usuario.c.ativo, usuario.c.geracao_autorizacao,
                       usuario.c.role, usuario.c.primeiro_acesso, usuario.c.senha_hash)
                .order_by(usuario.c.id_usuario),
            )}

    def test_upgrade_blocks_unknown_legacy_states_and_preserves_other_accounts(self):
        self._upgrade()
        states = self._states()
        self.assertEqual(states[1][:2], (True, 0))
        self.assertEqual(states[2][:2], (False, 0))
        self.assertEqual(states[3][:2], (False, 1))
        self.assertEqual(states[4][:2], (False, 1))
        self.assertEqual(states[5][:2], (True, 0))
        self.assertEqual(states[6][:2], (False, 0))
        for identifier, state in states.items():
            self.assertEqual(state[2], "ADMIN" if identifier >= 5 else "CLIENTE")
            self.assertEqual(state[3], identifier == 4)
            self.assertEqual(state[4], "synthetic-no-login-hash")
        self.assertEqual(self._counts(), self.before_counts)
        with self.engine.connect() as connection:
            self.assertEqual(connection.scalar(text("SELECT texto FROM notificacao WHERE id_notificacao=1")),
                             "Dado sintético preservado")
            self.assertEqual(connection.scalar(text("SELECT mensagem FROM mensagem_suporte WHERE id_mensagem=1")),
                             "Histórico sintético preservado")

    def test_upgrade_preserves_existing_constraints_and_enforces_generation(self):
        self._upgrade()
        after = self._constraints()
        new_check = [item for item in after["usuario"]["checks"]
                     if item[0] == "ck_usuario_geracao_autorizacao"]
        self.assertEqual(len(new_check), 1)
        after["usuario"]["checks"].remove(new_check[0])
        self.assertEqual(after, self.before_constraints)
        for statement in (
            "UPDATE usuario SET geracao_autorizacao=-1 WHERE id_usuario=1",
            "UPDATE usuario SET geracao_autorizacao=NULL WHERE id_usuario=1",
            "UPDATE usuario SET role='ADMIN' WHERE id_usuario=1",
            "UPDATE usuario SET role='INVALID' WHERE id_usuario=5",
            "UPDATE usuario SET id_empresa=999999 WHERE id_usuario=1",
            "UPDATE usuario SET email='user1@example.invalid' WHERE id_usuario=2",
        ):
            with self.subTest(statement=statement), self.assertRaises(IntegrityError):
                with self.engine.begin() as connection:
                    connection.execute(text(statement))
        self.assertEqual(self._states()[1][:2], (True, 0))
        if self.engine.dialect.name == "sqlite":
            with self.engine.connect() as connection:
                self.assertEqual(connection.exec_driver_sql("PRAGMA foreign_key_check").all(), [])

    def test_new_rows_receive_safe_default_without_inventing_active_state(self):
        self._upgrade()
        usuario = self._tables()["usuario"]
        with self.engine.begin() as connection:
            connection.execute(usuario.insert(), dict(
                id_usuario=7, id_empresa=1, role="CLIENTE", ativo=False,
                nome="Nova conta sintética", email="new@example.invalid", senha_hash="synthetic-only",
            ))
        self.assertEqual(self._states()[7][:2], (False, 0))

    def test_repeating_upgrade_does_not_rewrite_reviewed_state_or_generation(self):
        self._upgrade()
        with self.engine.begin() as connection:
            connection.execute(text("UPDATE usuario SET geracao_autorizacao=4 WHERE id_usuario=3"))
        self._upgrade()
        self.assertEqual(self._states()[3][:2], (False, 4))
        self.assertEqual(self._counts(), self.before_counts)

    def test_disposable_downgrade_preserves_data_and_never_reactivates_legacy_accounts(self):
        self._upgrade()
        with self.app.app_context():
            self._run_migration(downgrade, OLD_HEAD)
        self.assertEqual(self._revision(), OLD_HEAD)
        self.assertNotIn("geracao_autorizacao", {item["name"] for item in inspect(self.engine).get_columns("usuario")})
        self.assertEqual(self._constraints(), self.before_constraints)
        self.assertEqual(self._counts(), self.before_counts)
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(text(
                "SELECT id_usuario FROM usuario WHERE ativo IS TRUE ORDER BY id_usuario",
            )).scalars().all(), [1, 5])
        self._upgrade()
        self.assertEqual(self._states()[3][:2], (False, 1))


class SQLiteCompanyRestoreMigrationTests(CompanyRestoreMigrationCases, unittest.TestCase):
    def setUp(self):
        self._sqlite_file = tempfile.TemporaryDirectory(prefix="nexo-sec004-migration-db-")
        self.addCleanup(self._sqlite_file.cleanup)
        self._create_app("sqlite:///" + str(Path(self._sqlite_file.name) / "synthetic.sqlite"))
