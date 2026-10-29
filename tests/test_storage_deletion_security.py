"""SEC-004: arquivos legados só saem do disco depois do COMMIT, dentro de UPLOAD_FOLDER."""

from datetime import datetime, timezone
import os
from pathlib import Path
import re
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from .deploy_support import DeployTestCase
import pos_commit
import storage


class StorageDeletionSecurityTests(DeployTestCase):
    def setUp(self):
        super().setUp()
        from models import Analise, UploadRelatorio
        self.fixtures()
        self.uploads = Path(self.app.config["UPLOAD_FOLDER"])
        self.uploads.mkdir(parents=True, exist_ok=True)
        self.legado = self.uploads / "analise_legado_vendas.csv"
        self.legado.write_text("produto;valor\nfict;1\n", encoding="utf-8")
        self.fora = self.work_dir / "fora_da_pasta.csv"
        self.fora.write_text("private;1\n", encoding="utf-8")
        analise = self.db.session.get(Analise, self.analise_id)
        self.empresa_id = analise.id_empresa
        self.db.session.add_all([
            UploadRelatorio(id_analise=self.analise_id, id_usuario_admin=self.admin_id, tipo_relatorio="VENDAS",
                            nome_arquivo_original="vendas.csv", caminho_arquivo=str(self.legado),
                            extensao_arquivo="CSV", status_processamento="PENDENTE"),
            UploadRelatorio(id_analise=self.analise_id, id_usuario_admin=self.admin_id, tipo_relatorio="COMPRAS",
                            nome_arquivo_original="compras.csv", caminho_arquivo=str(self.fora),
                            extensao_arquivo="CSV", status_processamento="PENDENTE"),
        ])
        self.db.session.commit()
        self.assertTrue(self.legado.exists())
        self.assertTrue(self.fora.exists())
        # As migrações (fileConfig do Alembic) desativam loggers já criados.
        self.stack.enter_context(patch.object(storage.logger, "disabled", False))

    def _analise(self):
        from models import Analise
        self.db.session.expire_all()
        return self.db.session.get(Analise, self.analise_id)

    def _uploads(self):
        from models import UploadRelatorio
        self.db.session.expire_all()
        return self.db.session.scalars(select(UploadRelatorio).where(
            UploadRelatorio.id_analise == self.analise_id)).all()

    def test_legacy_file_is_removed_only_after_a_successful_commit(self):
        from blueprints.admin import _excluir_analise
        removidos = []
        original = os.remove

        def observar(caminho):
            removidos.append(("remove", caminho))
            return original(caminho)
        commits = []
        original_commit = self.db.session.commit

        def commit_observado():
            commits.append(("commit", self.legado.exists()))
            return original_commit()
        with patch.object(storage.os, "remove", side_effect=observar), \
                patch.object(self.db.session, "commit", side_effect=commit_observado):
            ok, _ = _excluir_analise(self._analise())
        self.assertTrue(ok)
        self.assertEqual(commits, [("commit", True)], "o arquivo ainda existia no momento do COMMIT")
        alvos = [caminho for _, caminho in removidos]
        self.assertIn(str(self.legado), alvos)
        self.assertNotIn(str(self.fora), alvos)
        for alvo in alvos:  # toda remoção fica confinada à pasta de uploads
            self.assertTrue(Path(alvo).resolve().is_relative_to(self.uploads.resolve()), alvo)
        self.assertFalse(self.legado.exists())
        self.assertTrue(self.fora.exists(), "arquivo fora de UPLOAD_FOLDER nunca é apagado")
        self.assertEqual(self._uploads(), [])
        self.assertIsNone(self._analise())

    def test_database_failure_keeps_rows_and_files_intact(self):
        from blueprints.admin import _excluir_analise
        with patch.object(self.db.session, "commit", side_effect=SQLAlchemyError("PRIVATE_DELETE_SENTINEL")):
            ok, mensagem = _excluir_analise(self._analise())
        self.assertFalse(ok)
        self.assertNotIn("PRIVATE_DELETE_SENTINEL", mensagem)
        self.assertTrue(self.legado.exists())
        self.assertTrue(self.fora.exists())
        self.assertEqual(len(self._uploads()), 2)
        self.assertIsNotNone(self._analise())
        self.assertEqual(pos_commit.pendentes(self.db.session), [], "rollback descarta o agendamento")

    def test_company_hard_delete_is_atomic_with_its_legacy_files(self):
        from models import Empresa
        empresa = self.db.session.get(Empresa, self.empresa_id)
        empresa.deletado_em = datetime.now(timezone.utc)  # já na lixeira (duplo passo)
        self.db.session.commit()
        self.login("admin-test@example.invalid")
        caminho = f"/admin/empresa/excluir-permanente/{self.empresa_id}"
        token = self.csrf_token("/admin/lixeira")
        with patch.object(self.db.session, "commit", side_effect=SQLAlchemyError("PRIVATE_HARD_DELETE")):
            response = self.client.post(caminho, data={"csrf_token": token})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.legado.exists())
        self.assertEqual(len(self._uploads()), 2)
        self.assertIsNotNone(self.db.session.get(Empresa, self.empresa_id))

        response = self.client.post(caminho, data={"csrf_token": self.csrf_token("/admin/lixeira")})
        self.assertEqual(response.status_code, 302)
        self.db.session.expire_all()
        self.assertIsNone(self.db.session.get(Empresa, self.empresa_id))
        self.assertFalse(self.legado.exists())
        self.assertTrue(self.fora.exists())

    def test_savepoint_rollback_discards_only_its_scheduled_removals(self):
        outro = self.uploads / "outro_legado.csv"
        outro.write_text("x\n", encoding="utf-8")
        self._uploads()  # abre a transação, como qualquer rota faz antes de remover
        storage.remover(str(self.legado))
        try:
            with self.db.session.begin_nested():
                storage.remover(str(outro))
                raise ValueError("synthetic savepoint rollback")
        except ValueError:
            pass
        self.assertEqual([item for _, item in pos_commit.pendentes(self.db.session)], [str(self.legado)])
        self.db.session.commit()
        self.assertFalse(self.legado.exists())
        self.assertTrue(outro.exists())

    def test_rollback_discards_scheduled_removals(self):
        self._uploads()  # transação aberta, como em qualquer rota
        storage.remover(str(self.legado))
        self.db.session.rollback()
        self.assertEqual(pos_commit.pendentes(self.db.session), [])
        self.db.session.commit()
        self.assertTrue(self.legado.exists())

    def test_removal_failure_is_logged_without_the_path_and_is_idempotent(self):
        self._uploads()
        storage.remover(str(self.legado))
        with patch.object(storage.os, "remove", side_effect=PermissionError("PRIVATE_PATH_SENTINEL")), \
                self.assertLogs(storage.logger, level="WARNING") as logs:
            self.db.session.commit()
        saida = "\n".join(logs.output)
        self.assertIn("PermissionError", saida)
        self.assertNotIn(str(self.legado), saida)
        self.assertNotIn("PRIVATE_PATH_SENTINEL", saida)
        self.assertTrue(self.legado.exists())
        # Já removido (ou inexistente): nenhum erro, nenhum aviso.
        self.legado.unlink()
        self._uploads()
        storage.remover(str(self.legado))
        storage.remover(str(self.uploads / "nunca_existiu.csv"))
        self.db.session.commit()

    def test_paths_outside_upload_folder_are_never_read_or_removed(self):
        subpasta = self.work_dir / "outra_pasta"
        subpasta.mkdir()
        (subpasta / "fora_da_pasta.csv").write_text("x\n", encoding="utf-8")
        for referencia in (str(self.fora), "../fora_da_pasta.csv", "../outra_pasta/fora_da_pasta.csv",
                           "..\\..\\fora_da_pasta.csv", "subdir/../../fora_da_pasta.csv",
                           str(subpasta / "fora_da_pasta.csv")):
            with self.subTest(referencia=referencia):
                resolvido = Path(storage.resolver(referencia)).resolve()
                self.assertTrue(resolvido.is_relative_to(self.uploads.resolve()), resolvido)
                self.assertNotEqual(resolvido, self.uploads.resolve())
                self._uploads()
                storage.remover(referencia)
                self.db.session.commit()
                self.assertTrue(self.fora.exists())
                self.assertTrue((subpasta / "fora_da_pasta.csv").exists())
        # A própria pasta de uploads (ou um diretório dentro dela) nunca é removida.
        (self.uploads / "pasta_interna").mkdir()
        for referencia in (str(self.uploads), str(self.uploads / "pasta_interna"), ""):
            with self.subTest(referencia=referencia):
                self._uploads()
                storage.remover(referencia)
                self.db.session.commit()
        self.assertTrue(self.uploads.exists())
        self.assertTrue((self.uploads / "pasta_interna").exists())

    def test_legacy_reference_inside_upload_folder_still_resolves_for_reading(self):
        self.assertEqual(Path(storage.resolver(str(self.legado))).resolve(), self.legado.resolve())
        self.assertEqual(Path(storage.resolver("analise_legado_vendas.csv")).resolve(), self.legado.resolve())
        obsoleto = "/pasta/antiga/que/nao/existe/analise_legado_vendas.csv"
        self.assertEqual(Path(storage.resolver(obsoleto)).resolve(), self.legado.resolve())

    def test_db_stored_file_row_is_deleted_in_the_same_transaction(self):
        from models import ArquivoArmazenado
        referencia = storage.salvar(b"conteudo", "analise_db_vendas.csv")
        self.db.session.commit()
        self.assertIsNotNone(self.db.session.get(ArquivoArmazenado, "analise_db_vendas.csv"))
        storage.remover(referencia)
        self.db.session.rollback()
        self.db.session.expire_all()
        self.assertIsNotNone(self.db.session.get(ArquivoArmazenado, "analise_db_vendas.csv"))
        storage.remover(referencia)
        self.db.session.commit()
        self.db.session.expire_all()
        self.assertIsNone(self.db.session.get(ArquivoArmazenado, "analise_db_vendas.csv"))

    def test_no_route_unlinks_files_before_commit(self):
        """Guarda estática: fora de storage.py ninguém chama os.remove/unlink."""
        raiz = Path(__file__).resolve().parents[1]
        ofensores = []
        for caminho in [raiz / "app.py", *sorted((raiz / "blueprints").glob("*.py"))]:
            for numero, linha in enumerate(caminho.read_text(encoding="utf-8").splitlines(), 1):
                if re.search(r"os\.remove\(|\.unlink\(|shutil\.rmtree\(", linha):
                    ofensores.append(f"{caminho.name}:{numero}")
        self.assertEqual(ofensores, [])
