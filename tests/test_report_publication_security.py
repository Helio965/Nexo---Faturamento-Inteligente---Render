"""SEC-003: o cliente só vê a versão PUBLICADA; rascunho e IA não a alteram."""

import re
import unittest
from unittest.mock import patch

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import StaleDataError

from . import pdf_layout_support as apoio
from .deploy_support import DeployTestCase

PUBLICADO = "PUBLISHED-SENTINEL-ONE"
RASCUNHO = "DRAFT-SENTINEL-TWO"
GERADO_IA = "AI-GENERATED-SENTINEL-THREE"


class ReportPublicationSecurityTests(DeployTestCase):
    def setUp(self):
        super().setUp()
        from models import Analise, IndicadorAnalise
        self.fixtures()
        analise = self.db.session.get(Analise, self.analise_id)
        analise.status_analise = "EM_ANALISE"
        analise.indicador = IndicadorAnalise(faturamento_total=250, total_comprado=100,
                                             saldo_estimado_compras_vendas=150)
        self.db.session.commit()
        self.editor = f"/admin/analise/{self.analise_id}/relatorio"
        self.login("admin-test@example.invalid")
        self.cliente = self.app.test_client()
        response = self.cliente.post("/auth/login", data={
            "email": "cliente-test@example.invalid", "senha": self.password,
            "csrf_token": self._csrf_de(self.cliente, "/auth/login"),
        })
        self.assertEqual(response.status_code, 302)

    # ------------------------------------------------------------ helpers
    def _csrf_de(self, client, path):
        response = client.get(path)
        self.assertEqual(response.status_code, 200)
        match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', response.get_data(as_text=True))
        self.assertIsNotNone(match)
        return match.group(1)

    def _relatorio(self):
        from models import RelatorioAnalise
        self.db.session.expire_all()
        return self.db.session.scalar(select(RelatorioAnalise).where(
            RelatorioAnalise.id_analise == self.analise_id))

    def _versao(self):
        rel = self._relatorio()
        return rel.versao_rascunho if rel else 0

    def _post(self, acao, texto, *, versao=None, revisado=False, follow=False):
        data = {
            "csrf_token": self._csrf_de(self.client, self.editor), "acao": acao,
            "versao_rascunho": str(self._versao() if versao is None else versao),
            "titulo": f"Titulo {texto}", "resumo_executivo": f"Resumo {texto}",
            "conclusao_estrategica": f"Conclusao {texto}",
        }
        if revisado:
            data["revisao_confirmada"] = "1"
        response = self.client.post(self.editor, data=data, follow_redirects=follow)
        self.assertEqual(response.status_code, 200 if follow else 302)
        return response

    def _gerar_ia(self, fonte="ia"):
        gerado = {"resumo_executivo": f"Resumo {GERADO_IA}", "conclusao_estrategica": f"Conclusao {GERADO_IA}",
                  "fonte": fonte}
        with patch("ai_devolutiva.gerar_devolutiva_ia", return_value=gerado):
            response = self.client.post(self.editor, data={
                "csrf_token": self._csrf_de(self.client, self.editor), "acao": "gerar_ia",
                "versao_rascunho": str(self._versao()),
            })
        self.assertEqual(response.status_code, 302)

    def _pagina_cliente(self):
        return self.cliente.get(f"/cliente/analise/{self.analise_id}")

    def _texto_cliente(self):
        response = self._pagina_cliente()
        self.assertEqual(response.status_code, 200)
        return response.get_data(as_text=True)

    def _pdf_cliente(self):
        response = self.cliente.get(f"/cliente/analise/{self.analise_id}/pdf")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data.startswith(b"%PDF-"))
        if not apoio.pdftotext_disponivel():
            raise unittest.SkipTest("pdftotext indisponível: texto do PDF não verificável")
        return apoio.texto(response.data)

    def _notificacoes_cliente(self):
        from models import Notificacao
        return self.db.session.scalars(select(Notificacao).where(
            Notificacao.id_usuario == self.cliente_id)).all()

    def _editor_html(self):
        return self.client.get(self.editor).get_data(as_text=True)

    # ------------------------------------------------------------ cenários
    def test_unpublished_report_is_invisible_to_the_client(self):
        self._post("rascunho", RASCUNHO)
        self.assertEqual(self._pagina_cliente().status_code, 404)
        self.assertEqual(self.cliente.get(f"/cliente/analise/{self.analise_id}/pdf").status_code, 404)
        self.assertEqual(self._notificacoes_cliente(), [])

    def test_publication_freezes_the_text_and_later_draft_edits_do_not_reach_the_client(self):
        self._post("publicar", PUBLICADO)
        rel = self._relatorio()
        self.assertTrue(rel.publicado)
        self.assertTrue(rel.tem_copia_publicada)
        self.assertEqual(rel.conclusao_estrategica_publicada, f"Conclusao {PUBLICADO}")
        self.assertIn(PUBLICADO, self._texto_cliente())
        self.assertEqual(len(self._notificacoes_cliente()), 1)

        self._post("rascunho", RASCUNHO)
        rel = self._relatorio()
        self.assertEqual(rel.conclusao_estrategica, f"Conclusao {RASCUNHO}")
        self.assertEqual(rel.conclusao_estrategica_publicada, f"Conclusao {PUBLICADO}")
        self.assertTrue(rel.publicado)
        pagina = self._texto_cliente()
        self.assertIn(PUBLICADO, pagina)
        self.assertNotIn(RASCUNHO, pagina)
        pdf = self._pdf_cliente()
        self.assertIn(PUBLICADO, pdf)
        self.assertNotIn(RASCUNHO, pdf)
        dashboard = self.cliente.get("/cliente/dashboard").get_data(as_text=True)
        self.assertIn(f"Titulo {PUBLICADO}", dashboard)
        self.assertNotIn(RASCUNHO, dashboard)
        self.assertIn("Rascunho diferente do texto publicado", self._editor_html())
        self.assertEqual(len(self._notificacoes_cliente()), 1, "rascunho não notifica")

    def test_ai_generation_never_changes_the_published_text_until_reviewed_and_republished(self):
        self._post("publicar", PUBLICADO)
        self._gerar_ia()
        rel = self._relatorio()
        self.assertTrue(rel.gerado_por_ia)
        self.assertEqual(rel.conclusao_estrategica, f"Conclusao {GERADO_IA}")
        self.assertEqual(rel.conclusao_estrategica_publicada, f"Conclusao {PUBLICADO}")
        self.assertFalse(rel.gerado_por_ia_publicado)
        pagina = self._texto_cliente()
        self.assertIn(PUBLICADO, pagina)
        self.assertNotIn(GERADO_IA, pagina)
        self.assertNotIn("Gerado por IA", pagina)
        self.assertNotIn(GERADO_IA, self._pdf_cliente())

        # Publicar sem declarar a revisão humana é recusado.
        response = self._post("publicar", GERADO_IA, follow=True)
        self.assertIn("confirme a revisão humana", response.get_data(as_text=True))
        rel = self._relatorio()
        self.assertEqual(rel.conclusao_estrategica_publicada, f"Conclusao {PUBLICADO}")
        self.assertNotIn(GERADO_IA, self._texto_cliente())
        self.assertEqual(len(self._notificacoes_cliente()), 1)

        self._post("publicar", GERADO_IA, revisado=True)
        rel = self._relatorio()
        self.assertEqual(rel.conclusao_estrategica_publicada, f"Conclusao {GERADO_IA}")
        self.assertTrue(rel.gerado_por_ia_publicado)
        self.assertIn(GERADO_IA, self._texto_cliente())
        self.assertEqual(len(self._notificacoes_cliente()), 2)

    def test_legacy_published_report_without_copy_is_frozen_before_the_first_edit(self):
        from models import RelatorioAnalise
        self._post("publicar", PUBLICADO)
        # Estado anterior a esta versão: publicado, sem cópia (colunas nulas).
        self.db.session.execute(update(RelatorioAnalise).where(
            RelatorioAnalise.id_analise == self.analise_id,
        ).values(titulo_publicado=None, resumo_executivo_publicado=None,
                 conclusao_estrategica_publicada=None, gerado_por_ia_publicado=None))
        self.db.session.commit()
        rel = self._relatorio()
        self.assertFalse(rel.tem_copia_publicada)
        self.assertTrue(rel.publicada.legado)
        self.assertIn(PUBLICADO, self._texto_cliente())

        self._post("rascunho", RASCUNHO)
        rel = self._relatorio()
        self.assertTrue(rel.tem_copia_publicada)
        self.assertEqual(rel.conclusao_estrategica_publicada, f"Conclusao {PUBLICADO}")
        self.assertEqual(rel.conclusao_estrategica, f"Conclusao {RASCUNHO}")
        self.assertIn(PUBLICADO, self._texto_cliente())
        self.assertNotIn(RASCUNHO, self._texto_cliente())

        self._gerar_ia()
        self.assertEqual(self._relatorio().conclusao_estrategica_publicada, f"Conclusao {PUBLICADO}")
        self.assertIn(PUBLICADO, self._texto_cliente())

    def test_stale_form_version_cannot_overwrite_a_newer_draft(self):
        self._post("rascunho", "FIRST")
        versao_antiga = self._versao()
        self._post("rascunho", "SECOND")
        self.assertEqual(self._versao(), versao_antiga + 1)
        response = self._post("rascunho", "STALE", versao=versao_antiga, follow=True)
        self.assertIn("alterado em outra sessão", response.get_data(as_text=True))
        rel = self._relatorio()
        self.assertEqual(rel.conclusao_estrategica, "Conclusao SECOND")
        self.assertEqual(rel.versao_rascunho, versao_antiga + 1)
        for versao in ("", "abc", "-1", "999"):
            with self.subTest(versao=versao):
                self._post("rascunho", "STALE", versao=versao)
                self.assertEqual(self._relatorio().conclusao_estrategica, "Conclusao SECOND")
        # Publicar com a versão errada também não publica.
        self._post("publicar", "STALE", versao=versao_antiga)
        self.assertFalse(self._relatorio().publicado)
        self.assertEqual(self._pagina_cliente().status_code, 404)

    def test_concurrent_write_detected_at_commit_leaves_everything_unchanged(self):
        self._post("publicar", PUBLICADO)
        with patch.object(self.db.session, "commit", side_effect=StaleDataError("synthetic")):
            response = self._post("publicar", RASCUNHO, follow=True)
        self.assertIn("alterado em outra sessão", response.get_data(as_text=True))
        rel = self._relatorio()
        self.assertEqual(rel.conclusao_estrategica_publicada, f"Conclusao {PUBLICADO}")
        self.assertEqual(rel.conclusao_estrategica, f"Conclusao {PUBLICADO}")
        self.assertIn(PUBLICADO, self._texto_cliente())

    def test_database_failure_during_publication_publishes_nothing_and_notifies_nobody(self):
        self._post("rascunho", RASCUNHO)
        with patch.object(self.db.session, "commit", side_effect=SQLAlchemyError("PRIVATE_COMMIT_SENTINEL")):
            response = self._post("publicar", PUBLICADO, follow=True)
        corpo = response.get_data(as_text=True)
        self.assertIn("Não foi possível salvar o relatório", corpo)
        self.assertNotIn("PRIVATE_COMMIT_SENTINEL", corpo)
        rel = self._relatorio()
        self.assertFalse(rel.publicado)
        self.assertFalse(rel.tem_copia_publicada)
        self.assertEqual(rel.conclusao_estrategica, f"Conclusao {RASCUNHO}")
        self.assertEqual(self._notificacoes_cliente(), [])
        self.assertEqual(self._pagina_cliente().status_code, 404)
        from models import Analise
        self.db.session.expire_all()
        self.assertEqual(self.db.session.get(Analise, self.analise_id).status_analise, "EM_ANALISE")

    def test_unpublish_hides_the_report_and_republish_delivers_the_edited_text(self):
        self._post("publicar", PUBLICADO)
        self._post("rascunho", RASCUNHO)
        self._post("despublicar", RASCUNHO)
        rel = self._relatorio()
        self.assertFalse(rel.publicado)
        self.assertEqual(self._pagina_cliente().status_code, 404)
        self.assertEqual(self.cliente.get(f"/cliente/analise/{self.analise_id}/pdf").status_code, 404)
        self._post("publicar", RASCUNHO)
        self.assertEqual(self._relatorio().conclusao_estrategica_publicada, f"Conclusao {RASCUNHO}")
        self.assertIn(RASCUNHO, self._texto_cliente())
        self.assertNotIn(PUBLICADO, self._texto_cliente())

    def test_editor_carries_the_version_and_the_review_checkbox_only_for_ai_text(self):
        self._post("rascunho", RASCUNHO)
        html = self._editor_html()
        self.assertIn(f'name="versao_rascunho" value="{self._versao()}"', html)
        self.assertNotIn('name="revisao_confirmada"', html)
        self._gerar_ia()
        self.assertIn('name="revisao_confirmada"', self._editor_html())

    def test_published_copy_is_read_only_object_without_draft_fields(self):
        self._post("publicar", PUBLICADO)
        self._post("rascunho", RASCUNHO)
        publicada = self._relatorio().publicada
        self.assertFalse(publicada.legado)
        self.assertEqual(publicada.conclusao_estrategica, f"Conclusao {PUBLICADO}")
        self.assertFalse(hasattr(publicada, "pontos_positivos"))
        with self.assertRaises(AttributeError):
            publicada.conclusao_estrategica_publicada  # noqa: B018 — só a leitura publicada existe
