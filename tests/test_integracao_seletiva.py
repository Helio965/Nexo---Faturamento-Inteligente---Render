"""Regressões dos pontos combinados, com fixtures e rede bloqueada."""

from datetime import datetime, timezone
import hashlib
import io
from unittest.mock import patch

from sqlalchemy import select

from tests.contratos_support import ContratosCase


class IntegracaoSeletivaTests(ContratosCase):
    def test_resposta_do_cliente_reabre_chamado_sem_data_de_fechamento(self):
        from models import ChamadoSuporte, MensagemSuporte
        chamado = ChamadoSuporte(
            id_empresa=self.empresa_id, id_usuario_cliente=self.cliente_id,
            assunto="Conversa fictícia", categoria="DUVIDA_TECNICA",
            status_chamado="RESOLVIDO", data_fechamento=datetime(2026, 2, 10, 15, tzinfo=timezone.utc),
        )
        self.db.session.add(chamado)
        self.db.session.commit()
        ident = chamado.id_chamado
        self.login()
        path = f"/cliente/tickets/{ident}"
        response = self.client.post(path, data={
            "mensagem": "Ainda preciso de ajuda.", "csrf_token": self.csrf_token(path),
        })
        self.assertEqual(response.status_code, 302)
        self.db.session.expire_all()
        chamado = self.db.session.get(ChamadoSuporte, ident)
        self.assertEqual(chamado.status_chamado, "EM_ATENDIMENTO")
        self.assertIsNone(chamado.data_fechamento)
        self.assertEqual(len(list(self.db.session.scalars(select(MensagemSuporte).where(
            MensagemSuporte.id_chamado == ident)))), 1)

    def test_publicacao_durante_preflight_impede_substituicao_do_upload(self):
        from models import UploadRelatorio
        self.login("admin-test@example.invalid")
        path = f"/admin/analise/{self.analise_id}/upload"
        csrf = self.csrf_token(path)
        conteudo = b"Produto;Quantidade;Valor total\nFicticio;1;10\n"

        def publicar_durante_validacao(*args):
            self.publicar(self.analise_id)
            return conteudo, hashlib.sha256(conteudo).hexdigest()

        with patch("blueprints.admin.ler_upload_validado", side_effect=publicar_durante_validacao), \
                patch("blueprints.admin.storage.salvar") as salvar:
            response = self.client.post(path, data={
                "tipo_relatorio": "VENDAS", "csrf_token": csrf,
                "arquivo": (io.BytesIO(conteudo), "vendas.csv"),
            }, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith(
            f"/admin/analise/{self.analise_id}/relatorio"))
        salvar.assert_not_called()
        self.assertEqual(list(self.db.session.scalars(select(UploadRelatorio))), [])
