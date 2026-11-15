"""Guia editorial: migração, RLS e concorrência no PostgreSQL descartável.

Execução explícita: NEXO_TEST_POSTGRES_BIN=/diretorio/local/bin python -B -m unittest tests.postgresql_guia -v
O cluster usa socket Unix privado; não aceita URL, .env ou banco hospedado.
"""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from extensions import db, migrate
from tests.deploy_support import ROOT
from tests.postgresql_support import PrivatePostgreSQL


REVISAO = "c3e08eb3863a"
ANTERIOR = "5a9c3e7d1b42"
TABELAS = ("guia_edicao", "guia_midia")


class PostgreSQLGuiaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.postgresql = PrivatePostgreSQL()
        cls.addClassCleanup(cls.postgresql.close)

    def setUp(self):
        self.work = tempfile.TemporaryDirectory(prefix="nexo-pg-guia-")
        self.addCleanup(self.work.cleanup)
        self.database = self.postgresql.create_database()
        self.addCleanup(self.postgresql.drop_database, self.database)
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        for alvo in ("socket.socket.connect", "socket.socket.connect_ex", "socket.create_connection"):
            self.stack.enter_context(patch(alvo, side_effect=AssertionError("Rede externa proibida")))
        self.app = Flask(__name__, instance_path=str(Path(self.work.name) / "instance"))
        self.app.config.update(SQLALCHEMY_DATABASE_URI=self.postgresql.url(self.database),
                               SQLALCHEMY_ENGINE_OPTIONS={"connect_args": {
                                   "connect_timeout": 5, "password": "", "passfile": str(self.postgresql.passfile),
                                   "options": "-c statement_timeout=30000 -c lock_timeout=10000",
                               }})
        db.init_app(self.app)
        migrate.init_app(self.app, db)
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.addCleanup(self.ctx.pop)
        self.addCleanup(self._encerrar)
        self.assertEqual(db.engine.url.host, str(self.postgresql.socket))

    def _encerrar(self):
        db.session.remove()
        db.engine.dispose()

    def _migrar(self, comando, revisao=REVISAO):
        import flask_migrate
        db.session.remove()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()), \
                patch("logging.config.fileConfig"):
            getattr(flask_migrate, comando)(directory=str(ROOT / "migrations"), revision=revisao)

    def _topico(self):
        from models import GuiaTopico
        topico = GuiaTopico(categoria="Upload", pergunta="Como enviar arquivos?", resposta="Passo legítimo.",
                            ativo=True, imagem_url="db:guia/legitima.png")
        db.session.add(topico)
        db.session.commit()
        return topico.id

    def test_migracao_preserva_legado_e_bloqueia_data_api_inclusive_sequencia(self):
        from alembic.autogenerate import compare_metadata
        from alembic.migration import MigrationContext
        self._migrar("upgrade", ANTERIOR)
        id_topico = self._topico()
        antes = tuple(db.session.execute(text("SELECT * FROM guia_topico WHERE id = :id"), {"id": id_topico}).one())
        for comando in ('CREATE ROLE "anon" NOLOGIN', 'CREATE ROLE "authenticated" NOLOGIN',
                        'CREATE ROLE "service_role" NOLOGIN BYPASSRLS', 'CREATE ROLE "postgres" NOLOGIN',
                        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO PUBLIC, anon, authenticated",
                        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO PUBLIC, anon, authenticated",
                        "GRANT USAGE ON SCHEMA public TO anon, authenticated"):
            db.session.execute(text(comando))
        db.session.commit()
        self._migrar("upgrade")
        self.assertEqual(tuple(db.session.execute(text("SELECT * FROM guia_topico WHERE id = :id"),
                                                 {"id": id_topico}).one()), antes)
        for tabela in TABELAS:
            self.assertEqual(tuple(db.session.execute(text(
                "SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE oid = to_regclass(:t)"),
                {"t": tabela}).one()), (True, False))
            politicas = {tuple(r) for r in db.session.execute(text(
                "SELECT policyname, permissive, array_to_string(ARRAY(SELECT unnest(roles) ORDER BY 1), ','), "
                "qual, with_check FROM pg_policies WHERE tablename = :t"), {"t": tabela})}
            self.assertEqual(politicas, {
                ("deny_api_access", "RESTRICTIVE", "anon,authenticated", "false", "false"),
                ("acesso_servidor", "PERMISSIVE", "postgres,service_role", "true", "true"),
            })
            for papel in ("anon", "authenticated"):
                for privilegio in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE"):
                    self.assertFalse(db.session.scalar(text("SELECT has_table_privilege(:p,:t,:x)"),
                                                       {"p": papel, "t": tabela, "x": privilegio}))
        for papel in ("anon", "authenticated"):
            for privilegio in ("SELECT", "UPDATE", "USAGE"):
                self.assertFalse(db.session.scalar(text("SELECT has_sequence_privilege(:p,'guia_midia_id_seq',:x)"),
                                                   {"p": papel, "x": privilegio}))
        db.session.rollback()
        with db.engine.connect() as conexao:
            contexto = MigrationContext.configure(conexao, opts={"compare_type": True})
            diferencas = [d for d in compare_metadata(contexto, db.metadata) if any(t in str(d) for t in TABELAS)]
        self.assertEqual(diferencas, [])

    def test_json_persistente_versao_otimista_e_cascata_sem_apagar_blob(self):
        from models import ArquivoArmazenado, GuiaEdicao, GuiaMidia
        self._migrar("upgrade")
        id_topico = self._topico()
        db.session.add(GuiaEdicao(id_topico=id_topico, blocos=[{"tipo": "texto", "html": "<p>Passo 1</p>"}]))
        db.session.add(GuiaMidia(id_topico=id_topico, referencia="db:guia/compartilhada.png", tipo="imagem"))
        db.session.add(ArquivoArmazenado(chave="guia/compartilhada.png", conteudo=b"imagem", tamanho=6))
        db.session.commit()
        db.session.expire_all()
        self.assertEqual(db.session.get(GuiaEdicao, id_topico).blocos[0]["html"], "<p>Passo 1</p>")
        with Session(db.engine) as primeira, Session(db.engine) as segunda:
            a, b = primeira.get(GuiaEdicao, id_topico), segunda.get(GuiaEdicao, id_topico)
            a.descricao = "Primeira edição"
            primeira.commit()
            b.descricao = "Formulário antigo"
            with self.assertRaises(StaleDataError):
                segunda.commit()
            segunda.rollback()
        db.session.execute(text("DELETE FROM guia_topico WHERE id = :id"), {"id": id_topico})
        db.session.commit()
        self.assertEqual(db.session.scalars(select(GuiaEdicao)).all(), [])
        self.assertEqual(db.session.scalars(select(GuiaMidia)).all(), [])
        self.assertIsNotNone(db.session.get(ArquivoArmazenado, "guia/compartilhada.png"))

    def test_downgrade_recusa_dados_e_quando_vazio_preserva_topico(self):
        from models import GuiaEdicao, GuiaMidia
        self._migrar("upgrade")
        id_topico = self._topico()
        db.session.add(GuiaEdicao(id_topico=id_topico))
        db.session.commit()
        with self.assertRaises(SystemExit) as recusa:
            self._migrar("downgrade", ANTERIOR)
        self.assertEqual(recusa.exception.code, 1)
        self.assertEqual(db.session.scalar(text("SELECT count(*) FROM guia_edicao")), 1)
        db.session.execute(text("DELETE FROM guia_edicao"))
        db.session.add(GuiaMidia(id_topico=id_topico, referencia="db:guia/legitima.png", tipo="imagem"))
        db.session.commit()
        with self.assertRaises(SystemExit) as recusa:
            self._migrar("downgrade", ANTERIOR)
        self.assertEqual(recusa.exception.code, 1)
        db.session.execute(text("DELETE FROM guia_midia"))
        db.session.commit()
        self._migrar("downgrade", ANTERIOR)
        self.assertFalse(set(TABELAS) & set(inspect(db.engine).get_table_names()))
        self.assertEqual(db.session.scalar(text("SELECT count(*) FROM guia_topico WHERE id = :id"),
                                           {"id": id_topico}), 1)
        self._migrar("upgrade")
        self.assertTrue(set(TABELAS) <= set(inspect(db.engine).get_table_names()))

    def test_cms_quota_transacional_bytea_range_edicao_e_despublicacao(self):
        """Exercita o serviço e a trava de quota sem iniciar o portal autenticado."""
        from io import BytesIO
        import json
        from types import SimpleNamespace
        from PIL import Image
        from sqlalchemy import event, func
        from werkzeug.datastructures import FileStorage
        import guia_cms
        import guia_midias
        from models import ArquivoArmazenado, GuiaEdicao, GuiaMidia, GuiaTopico

        self._migrar("upgrade")
        self.app.add_url_rule("/midia/<path:chave>", "midia", lambda chave: "mídia privada")
        self.app.add_url_rule("/midia-legada/<path:nome>", "midia_legada_guia", lambda nome: "mídia privada")
        comandos = []
        engine = db.engine

        def registrar(conexao, cursor, comando, parametros, contexto, lote):
            if "pg_advisory_xact_lock" in comando or "substr(" in comando:
                comandos.append(comando)

        event.listen(engine, "before_cursor_execute", registrar)
        self.addCleanup(event.remove, engine, "before_cursor_execute", registrar)

        def png(cor):
            destino = BytesIO()
            Image.new("RGB", (18, 12), cor).save(destino, "PNG")
            return destino.getvalue()

        conteudo = png("purple")
        formulario = {
            "categoria": "Upload", "pergunta": "Tutorial PostgreSQL fictício",
            "descricao": "Orientação global de teste", "ordem": "4", "status": "publicado",
            "blocos_json": json.dumps([
                {"tipo": "texto", "html": "<h2>Primeiro passo</h2><p>Envie o relatório.</p>"},
                {"tipo": "midia", "id": "nova_captura", "legenda": "Captura fictícia", "alt": "Botão de envio"},
            ], ensure_ascii=False),
        }
        cliente = SimpleNamespace(is_authenticated=True, is_admin=False, is_cliente=True)
        with self.app.test_request_context("/admin/guia/novo"):
            topico = guia_cms.salvar(GuiaTopico(categoria="", pergunta="", resposta="", ativo=False), formulario, {
                "midia_nova_captura": FileStorage(stream=BytesIO(conteudo), filename="captura.png",
                                                  content_type="image/png"),
            })
            db.session.commit()
            id_topico = topico.id
            edicao = db.session.get(GuiaEdicao, id_topico)
            midia = db.session.scalar(select(GuiaMidia).where(GuiaMidia.id_topico == id_topico))
            chave, referencia = midia.referencia[3:], midia.referencia
            registro = db.session.get(ArquivoArmazenado, chave)
            self.assertEqual(bytes(registro.conteudo), conteudo)
            self.assertEqual((registro.content_type, registro.tamanho), ("image/png", len(conteudo)))
            self.assertEqual(edicao.blocos[1], {"tipo": "midia", "id": midia.id})
            self.assertEqual((edicao.ordem, midia.legenda, midia.alt), (4, "Captura fictícia", "Botão de envio"))
            self.assertTrue(topico.ativo)
            self.assertTrue(guia_cms.pode_servir_referencia(referencia, cliente))
            self.assertTrue(any("pg_advisory_xact_lock" in comando for comando in comandos))
            self.assertEqual(bytes(db.session.scalar(select(func.substr(ArquivoArmazenado.conteudo, 3, 8))
                .where(ArquivoArmazenado.chave == chave))), conteudo[2:10])
            versao = edicao.versao
            editar = dict(formulario, versao=str(versao), descricao="Descrição editada no PostgreSQL",
                          blocos_json=json.dumps([
                              {"tipo": "texto", "html": "<p>Segundo passo revisado.</p>"},
                              {"tipo": "midia", "id": midia.id, "legenda": "Legenda revisada", "alt": "Botão revisado"},
                          ], ensure_ascii=False))
            guia_cms.salvar(topico, editar, {})
            db.session.commit()
            db.session.expire_all()
            edicao = db.session.get(GuiaEdicao, id_topico)
            self.assertGreater(edicao.versao, versao)
            self.assertEqual((edicao.descricao, db.session.get(GuiaMidia, midia.id).legenda),
                             ("Descrição editada no PostgreSQL", "Legenda revisada"))
            self.assertEqual(db.session.get(GuiaTopico, id_topico).resposta, "Segundo passo revisado.")
            self.assertTrue(edicao.historico)
            with self.assertRaises(guia_cms.GuiaConflito):
                guia_cms.salvar(topico, editar, {})
            db.session.rollback()

            # O limite global é contado no BYTEA real e recusa antes de publicar
            # ou persistir a segunda mídia; rollback conserva a publicação anterior.
            with patch.object(guia_cms, "MAX_GUIA_BYTES", len(conteudo)):
                with self.assertRaisesRegex(guia_cms.GuiaErro, "quota"):
                    guia_cms.salvar(GuiaTopico(categoria="", pergunta="", resposta="", ativo=False), dict(formulario, pergunta="Não persistir"), {
                        "midia_nova_captura": FileStorage(stream=BytesIO(png("green")), filename="outra.png",
                                                          content_type="image/png"),
                    })
            db.session.rollback()
            for modelo in (GuiaTopico, GuiaMidia, ArquivoArmazenado):
                self.assertEqual(db.session.scalar(select(func.count()).select_from(modelo)), 1)
            self.assertTrue(db.session.get(GuiaTopico, id_topico).ativo)

        with self.app.test_request_context("/midia/" + chave, headers={"Range": "bytes=2-9"}):
            resposta = guia_midias.servir_midia(chave)
            self.assertEqual(resposta.status_code, 206)
            self.assertEqual(resposta.headers["Content-Range"], f"bytes 2-9/{len(conteudo)}")
            self.assertEqual(resposta.headers["Cache-Control"], "private, no-store")
            self.assertEqual(resposta.get_data(), conteudo[2:10])
            self.assertTrue(any("substr(" in comando for comando in comandos))

        with self.app.test_request_context("/admin/guia"):
            edicao = db.session.get(GuiaEdicao, id_topico)
            guia_cms.alterar_publicacao(db.session.get(GuiaTopico, id_topico), "despublicar", edicao.versao)
            db.session.commit()
            self.assertEqual(db.session.scalars(select(GuiaTopico).where(GuiaTopico.ativo.is_(True))).all(), [])
            self.assertFalse(guia_cms.pode_servir_referencia(referencia, cliente))
            self.assertEqual(bytes(db.session.get(ArquivoArmazenado, chave).conteudo), conteudo)
