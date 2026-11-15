"""Extensão editorial do Guia em SQLite descartável, com migrações reais."""

import contextlib
import io

from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from tests.deploy_support import ROOT, DeployTestCase


REVISAO = "c3e08eb3863a"
ANTERIOR = "5a9c3e7d1b42"
TABELAS = {"guia_edicao", "guia_midia"}


class GuiaSchemaTests(DeployTestCase):
    def _topico(self):
        from models import GuiaTopico
        topico = GuiaTopico(categoria="Upload", pergunta="Como enviar arquivos?",
                            resposta="Selecione os relatórios e confirme.", ativo=True,
                            imagem_url="db:guia/imagem-legitima.png")
        self.db.session.add(topico)
        self.db.session.commit()
        return topico

    def _migrar(self, comando, revisao):
        import flask_migrate
        self.db.session.remove()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            getattr(flask_migrate, comando)(directory=str(ROOT / "migrations"), revision=revisao)

    def test_esquema_reflete_modelos_sem_modificar_guia_legado(self):
        from alembic.autogenerate import compare_metadata
        from alembic.migration import MigrationContext
        inspetor = inspect(self.db.engine)
        self.assertEqual(self.db.session.scalar(text("SELECT version_num FROM alembic_version")), REVISAO)
        self.assertEqual({c["name"] for c in inspetor.get_columns("guia_topico")}, {
            "id", "categoria", "pergunta", "resposta", "imagem_url", "ativo", "data_criacao", "data_atualizacao",
        })
        self.assertEqual({c["name"] for c in inspetor.get_columns("guia_edicao")}, {
            "id_topico", "descricao", "ordem", "blocos", "historico", "publicado_em", "excluido_em", "versao",
        })
        self.assertEqual({c["name"] for c in inspetor.get_columns("guia_midia")}, {
            "id", "id_topico", "referencia", "tipo", "legenda", "alt", "data_criacao",
        })
        for tabela in TABELAS:
            [fk] = inspetor.get_foreign_keys(tabela)
            self.assertEqual((fk["referred_table"], fk["referred_columns"], fk["options"].get("ondelete")),
                             ("guia_topico", ["id"], "CASCADE"))
        indices = {i["name"] for tabela in TABELAS for i in inspetor.get_indexes(tabela)}
        self.assertEqual(indices, {"ix_guia_edicao_ordem", "ix_guia_midia_topico", "ix_guia_midia_referencia"})
        with self.db.engine.connect() as conexao:
            contexto = MigrationContext.configure(conexao, opts={"compare_type": True})
            diferencas = [d for d in compare_metadata(contexto, self.db.metadata)
                         if any(tabela in str(d) for tabela in TABELAS)]
        self.assertEqual(diferencas, [])

    def test_defaults_json_e_restricoes_valem_para_escrita_no_banco(self):
        from models import GuiaEdicao, GuiaMidia
        topico = self._topico()
        self.db.session.execute(text("INSERT INTO guia_edicao (id_topico) VALUES (:id)"), {"id": topico.id})
        self.db.session.commit()
        edicao = self.db.session.get(GuiaEdicao, topico.id)
        self.assertEqual((edicao.descricao, edicao.ordem, edicao.blocos, edicao.historico, edicao.versao),
                         ("", 0, [], [], 1))
        for campo, valor in (("ordem", -1), ("ordem", 10000), ("versao", 0)):
            with self.subTest(campo=campo, valor=valor):
                with self.assertRaises(IntegrityError):
                    self.db.session.execute(text(f"UPDATE guia_edicao SET {campo} = :v"), {"v": valor})
                self.db.session.rollback()
        for dados in ({"tipo": "html", "referencia": "db:guia/a.html"},
                      {"tipo": "imagem", "referencia": ""},
                      {"tipo": "video", "referencia": "db:guia/a.mp4", "id_topico": 99999}):
            with self.subTest(dados=dados):
                with self.assertRaises(IntegrityError):
                    self.db.session.add(GuiaMidia(id_topico=dados.get("id_topico", topico.id),
                                                 tipo=dados["tipo"], referencia=dados["referencia"]))
                    self.db.session.commit()
                self.db.session.rollback()

    def test_versao_impede_perda_de_edicao_concorrente(self):
        from models import GuiaEdicao
        topico = self._topico()
        self.db.session.add(GuiaEdicao(id_topico=topico.id))
        self.db.session.commit()
        with Session(self.db.engine) as primeira, Session(self.db.engine) as segunda:
            a, b = primeira.get(GuiaEdicao, topico.id), segunda.get(GuiaEdicao, topico.id)
            a.descricao = "Edição preservada"
            primeira.commit()
            b.descricao = "Formulário antigo"
            with self.assertRaises(StaleDataError):
                segunda.commit()
            segunda.rollback()
        self.db.session.expire_all()
        atual = self.db.session.get(GuiaEdicao, topico.id)
        self.assertEqual((atual.descricao, atual.versao), ("Edição preservada", 2))

    def test_migracao_aditiva_e_reversao_vazia_preservam_topico_e_imagem(self):
        topico = self._topico()
        id_topico = topico.id
        antes = self.db.session.execute(text("SELECT * FROM guia_topico WHERE id = :id"), {"id": id_topico}).one()
        self._migrar("downgrade", ANTERIOR)
        self.assertFalse(TABELAS & set(inspect(self.db.engine).get_table_names()))
        self._migrar("upgrade", REVISAO)
        depois = self.db.session.execute(text("SELECT * FROM guia_topico WHERE id = :id"), {"id": id_topico}).one()
        self.assertEqual(tuple(depois), tuple(antes))

    def test_reversao_recusa_descartar_metadados_ou_midias(self):
        from models import GuiaEdicao, GuiaMidia
        topico = self._topico()
        id_topico = topico.id
        self.db.session.add(GuiaEdicao(id_topico=id_topico, blocos=[{"tipo": "texto", "html": "<p>Passo 1</p>"}]))
        self.db.session.commit()
        with self.assertRaises(SystemExit) as recusa:
            self._migrar("downgrade", ANTERIOR)
        self.assertEqual(recusa.exception.code, 1)
        self.assertEqual(self.db.session.scalar(text("SELECT count(*) FROM guia_edicao")), 1)
        self.db.session.execute(text("DELETE FROM guia_edicao"))
        self.db.session.add(GuiaMidia(id_topico=id_topico, referencia="db:guia/a.png", tipo="imagem"))
        self.db.session.commit()
        with self.assertRaises(SystemExit) as recusa:
            self._migrar("downgrade", ANTERIOR)
        self.assertEqual(recusa.exception.code, 1)
        self.assertEqual(self.db.session.scalar(text("SELECT count(*) FROM guia_midia")), 1)

    def test_cascata_no_banco_segue_apenas_o_topico_removido(self):
        from models import ArquivoArmazenado, GuiaEdicao, GuiaMidia, GuiaTopico
        primeiro, segundo = self._topico(), self._topico()
        ids = (primeiro.id, segundo.id)
        self.db.session.add(ArquivoArmazenado(chave="guia/compartilhada.png", conteudo=b"ficticio", tamanho=8))
        for id_topico in ids:
            self.db.session.add(GuiaEdicao(id_topico=id_topico))
            self.db.session.add(GuiaMidia(id_topico=id_topico, referencia="db:guia/compartilhada.png", tipo="imagem"))
        self.db.session.commit()
        self.db.session.execute(text("DELETE FROM guia_topico WHERE id = :id"), {"id": ids[0]})
        self.db.session.commit()
        self.assertEqual(self.db.session.scalars(select(GuiaEdicao.id_topico)).all(), [ids[1]])
        self.assertEqual(self.db.session.scalars(select(GuiaMidia.id_topico)).all(), [ids[1]])
        self.assertIsNotNone(self.db.session.get(GuiaTopico, ids[1]))
        self.assertIsNotNone(self.db.session.get(ArquivoArmazenado, "guia/compartilhada.png"))
