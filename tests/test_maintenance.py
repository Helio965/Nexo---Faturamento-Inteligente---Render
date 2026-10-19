"""Maintenance safety checks with fake application/database modules only."""
import contextlib
import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]


def audit_temporary_directory():
    root = ROOT / ".audit_tmp"
    root.mkdir(exist_ok=True)
    return tempfile.TemporaryDirectory(prefix="maintenance-test-", dir=root)


def load_maintenance(name, static_folder="unused"):
    """Never import real app/config/extensions or read the local .env."""
    app = SimpleNamespace(
        config={}, static_folder=static_folder,
        app_context=lambda: contextlib.nullcontext(),
    )
    db = SimpleNamespace(
        engine=SimpleNamespace(echo=True), session=MagicMock(), func=MagicMock(),
    )
    factory = MagicMock(return_value=app)
    storage = ModuleType("storage")
    storage.PREFIXO_DB = "db:"
    storage.resolver = MagicMock(side_effect=lambda path: path)
    storage.salvar = MagicMock(side_effect=lambda content, key: "db:" + key)
    app_module = ModuleType("app")
    app_module.create_app = factory
    extensions = ModuleType("extensions")
    extensions.db = db
    models = ModuleType("models")
    for model in ("Plano", "Segmento", "Usuario", "GuiaTopico", "UploadRelatorio"):
        setattr(models, model, MagicMock())
    sqlalchemy = ModuleType("sqlalchemy")
    sqlalchemy.select = MagicMock()
    stubs = {
        "app": app_module, "extensions": extensions, "models": models,
        "storage": storage, "sqlalchemy": sqlalchemy,
    }
    spec = importlib.util.spec_from_file_location("_maintenance_" + name, ROOT / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    with patch.dict("sys.modules", stubs):
        spec.loader.exec_module(module)
    return module, app, db, factory, storage


def set_query_rows(app, db, uploads, topics):
    rows = iter((uploads, topics))

    def execute(_query):
        if db.engine.echo or app.config.get("SQLALCHEMY_ECHO") is not False:
            raise AssertionError("SQL echo must be off before the first query")
        result = MagicMock()
        result.scalars.return_value.all.return_value = next(rows)
        return result

    db.session.execute.side_effect = execute


class MaintenanceSafetyTests(unittest.TestCase):
    def test_importing_guide_seed_does_not_create_app_or_write(self):
        _module, _app, db, factory, _storage = load_maintenance("seed_guia")
        factory.assert_not_called()
        db.session.execute.assert_not_called()
        db.session.commit.assert_not_called()

    def test_seed_uses_factory_environment_and_disables_echo(self):
        module, app, db, factory, _storage = load_maintenance("seed")
        with patch.object(module, "seed_planos"), patch.object(module, "seed_segmentos"), \
                patch.object(module, "seed_admin"), contextlib.redirect_stdout(io.StringIO()):
            module.main()
        factory.assert_called_once_with()
        self.assertIs(app.config["SQLALCHEMY_ECHO"], False)
        self.assertIs(db.engine.echo, False)

    def test_migration_cli_requires_explicit_apply(self):
        module, _app, _db, _factory, _storage = load_maintenance("migrar_arquivos_para_db")
        for arguments, expected_dry_run in (([], True), (["--dry-run"], True), (["--apply"], False)):
            with self.subTest(arguments=arguments), patch.object(module, "main", return_value=0) as main:
                self.assertEqual(module.cli(arguments), 0)
                main.assert_called_once_with(dry_run=expected_dry_run)

    def test_migration_cli_rejects_unknown_or_conflicting_flags_before_work(self):
        module, _app, _db, _factory, _storage = load_maintenance("migrar_arquivos_para_db")
        for arguments in (["--dry-run-typo"], ["--app"], ["--apply", "--dry-run"]):
            with self.subTest(arguments=arguments), patch.object(module, "main") as main, \
                    contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    module.cli(arguments)
                self.assertEqual(error.exception.code, 2)
                main.assert_not_called()

    def test_default_migration_simulates_without_writes_or_source_removal(self):
        with audit_temporary_directory() as directory:
            path = Path(directory) / "report.csv"
            path.write_bytes(b"product,value\nexample,1\n")
            upload = SimpleNamespace(id_upload=1, caminho_arquivo=str(path), hash_arquivo=None)
            module, app, db, _factory, storage = load_maintenance("migrar_arquivos_para_db", directory)
            set_query_rows(app, db, [upload], [])
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(module.main(), 0)
            storage.salvar.assert_not_called()
            db.session.commit.assert_not_called()
            db.session.rollback.assert_called_once_with()
            self.assertEqual(upload.caminho_arquivo, str(path))
            self.assertTrue(path.exists())

    def test_apply_rolls_back_everything_on_missing_file_or_hash_mismatch(self):
        for failure in ("missing", "hash"):
            with self.subTest(failure=failure), audit_temporary_directory() as directory:
                path = Path(directory) / "valid.csv"
                path.write_bytes(b"valid source")
                invalid_path = Path(directory) / "invalid.csv"
                if failure == "hash":
                    invalid_path.write_bytes(b"unexpected source")
                uploads = [
                    SimpleNamespace(id_upload=1, caminho_arquivo=str(path), hash_arquivo=None),
                    SimpleNamespace(id_upload=2, caminho_arquivo=str(invalid_path), hash_arquivo="wrong-hash"),
                ]
                module, app, db, _factory, storage = load_maintenance("migrar_arquivos_para_db", directory)
                set_query_rows(app, db, uploads, [])
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(module.main(dry_run=False), 1)
                storage.salvar.assert_called_once()
                db.session.commit.assert_not_called()
                db.session.rollback.assert_called_once_with()
                self.assertIn("CANCELADO", output.getvalue())
                self.assertTrue(path.exists())

    def test_apply_commits_valid_uploads_and_guide_images_together(self):
        with audit_temporary_directory() as directory:
            upload_path = Path(directory) / "report.csv"
            upload_bytes = b"product,value\nexample,1\n"
            upload_path.write_bytes(upload_bytes)
            image_path = Path(directory) / "guide.png"
            image_bytes = b"fixture contents are never decoded by this migration"
            image_path.write_bytes(image_bytes)
            upload = SimpleNamespace(
                id_upload=1, caminho_arquivo=str(upload_path),
                hash_arquivo=hashlib.sha256(upload_bytes).hexdigest(),
            )
            topic = SimpleNamespace(id=1, imagem_url=image_path.name)
            module, app, db, _factory, storage = load_maintenance("migrar_arquivos_para_db", directory)
            set_query_rows(app, db, [upload], [topic])
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(module.main(dry_run=False), 0)
            db.session.commit.assert_called_once_with()
            db.session.rollback.assert_not_called()
            self.assertEqual(upload.caminho_arquivo, "db:report.csv")
            self.assertEqual(topic.imagem_url, "db:guia/guide.png")
            self.assertEqual(storage.salvar.call_count, 2)
            self.assertEqual(upload_path.read_bytes(), upload_bytes)
            self.assertEqual(image_path.read_bytes(), image_bytes)


if __name__ == "__main__":
    unittest.main()
