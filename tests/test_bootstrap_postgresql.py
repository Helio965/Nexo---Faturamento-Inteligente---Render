"""Primeira instalação real em PostgreSQL descartável, sem credenciais externas.

Habilitar com NEXO_TEST_POSTGRES_BIN apontando para os binários locais do
PostgreSQL. O helper cria um cluster exclusivo com socket Unix privado e
recusa URLs/servidores existentes. O schema vem somente do Flask-Migrate.
"""

import contextlib
import io
import os
from pathlib import Path
import re
import secrets
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


class BootstrapPostgreSQLTests(unittest.TestCase):
    def test_empty_database_migrations_seed_and_admin_login(self):
        if not os.environ.get("NEXO_TEST_POSTGRES_BIN"):
            self.skipTest("Defina NEXO_TEST_POSTGRES_BIN para o PostgreSQL privado.")

        from tests.postgresql_support import PrivatePostgreSQL

        cluster = PrivatePostgreSQL()
        self.addCleanup(cluster.close)
        database = cluster.create_database()
        uri = cluster.url(database)

        # Nenhum .env real pode ser lido, mesmo quando este módulo roda sozinho.
        with patch("dotenv.load_dotenv", return_value=False):
            import app as app_module
            from config import DevelopmentConfig
            from extensions import db
            from flask import Flask
            from flask_migrate import upgrade
            from alembic.autogenerate import compare_metadata
            from alembic.migration import MigrationContext
            from alembic.script import ScriptDirectory
            from sqlalchemy import func, inspect, select, text
            from models import Plano, Segmento, Usuario
            from seed import seed_admin, seed_planos, seed_segmentos

        password = secrets.token_urlsafe(24) + ":@#%[]/?!"
        settings = {
            "SQLALCHEMY_DATABASE_URI": uri,
            "SQLALCHEMY_DIRECT_URI": uri,
            "SQLALCHEMY_ENGINE_OPTIONS": {"hide_parameters": True},
            "SQLALCHEMY_ECHO": False,
            "SECRET_KEY": secrets.token_hex(32),
            "TESTING": True,
            "DEBUG": False,
            "RATELIMIT_ENABLED": False,
            "MAIL_ATIVO": False,
            "MAIL_SUPPRESS_SEND": True,
            "UPLOAD_FOLDER": cluster.root / "uploads",
            "ADMIN_EMAIL": "bootstrap-admin@example.invalid",
            "ADMIN_NOME": "Administrador sintético",
            "ADMIN_SENHA": password,
        }
        with contextlib.ExitStack() as stack:
            for key, value in settings.items():
                stack.enter_context(patch.object(DevelopmentConfig, key, value, create=True))
            stack.enter_context(patch.object(
                app_module, "Flask",
                side_effect=lambda *args, **kwargs: Flask(
                    *args, instance_path=str(cluster.root / "instance"), **kwargs,
                ),
            ))
            app = app_module.create_app("development")

        def dispose():
            with app.app_context():
                db.session.remove()
                db.engine.dispose()

        self.addCleanup(dispose)
        with app.app_context():
            self.assertEqual(db.engine.url.get_backend_name(), "postgresql")
            self.assertEqual(db.engine.url.host, str(cluster.socket))
            self.assertEqual(db.engine.url.database, database)
            self.assertEqual(inspect(db.engine).get_table_names(), [])

            # Não usar create_all/stamp: exercita a cadeia oficial desde zero.
            with patch("logging.config.fileConfig"), contextlib.redirect_stdout(io.StringIO()):
                upgrade(directory=str(ROOT / "migrations"))
                upgrade(directory=str(ROOT / "migrations"))
            expected_head = ScriptDirectory(str(ROOT / "migrations")).get_current_head()
            self.assertEqual(
                db.session.scalar(text("SELECT version_num FROM alembic_version")),
                expected_head,
            )
            self.assertEqual(
                set(inspect(db.engine).get_table_names()) - {"alembic_version"},
                set(db.metadata.tables),
            )
            with db.engine.connect() as connection:
                context = MigrationContext.configure(connection, opts={"compare_type": True})
                self.assertEqual(compare_metadata(context, db.metadata), [])

            for _ in range(2):
                with contextlib.redirect_stdout(io.StringIO()):
                    seed_planos()
                    seed_segmentos()
                    seed_admin(app)
                    db.session.commit()
            self.assertEqual(
                set(db.session.scalars(select(Plano.nome_plano).where(Plano.ativo.is_(True)))),
                {"BRONZE", "PRATA", "OURO"},
            )
            for model, count in ((Plano, 3), (Segmento, 3), (Usuario, 1)):
                self.assertEqual(db.session.scalar(select(func.count()).select_from(model)), count)
            admin = db.session.scalar(select(Usuario))
            self.assertEqual(admin.role, "ADMIN")
            self.assertTrue(admin.ativo)
            self.assertIsNone(admin.id_empresa)
            self.assertTrue(admin.check_senha(password))

            probe = Segmento(nome_segmento="BOOTSTRAP_ROLLBACK_SYNTHETIC")
            db.session.add(probe)
            db.session.flush()
            probe_id = probe.id_segmento
            self.assertIsNotNone(db.session.get(Segmento, probe_id))
            db.session.rollback()
            self.assertIsNone(db.session.get(Segmento, probe_id))
            db.session.remove()

        client = app.test_client()
        for path in ("/", "/como-aderir", "/auth/login", "/healthz", "/healthz/db"):
            with self.subTest(path=path):
                self.assertEqual(client.get(path).status_code, 200)
        login = client.get("/auth/login")
        token = re.search(
            r'name="csrf_token"[^>]*value="([^"]+)"', login.get_data(as_text=True),
        )
        self.assertIsNotNone(token)
        response = client.post("/auth/login", data={
            "email": app.config["ADMIN_EMAIL"], "senha": password,
            "csrf_token": token.group(1),
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/admin/dashboard")
        self.assertEqual(client.get("/admin/dashboard").status_code, 200)


if __name__ == "__main__":
    unittest.main()
