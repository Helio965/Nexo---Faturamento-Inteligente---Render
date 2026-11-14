"""Detalhamento por produto da Visão Geral (revisão 5a9c3e7d1b42) em PostgreSQL privado.

Executar explicitamente (não há skip silencioso se os binários faltarem):
    NEXO_TEST_POSTGRES_BIN=/caminho/local/bin python -B -m unittest tests.postgresql_detalhamento_produtos -v

Cada caso recebe banco próprio em cluster privado, sem TCP, sem .env nem servidor
existente. Os relatórios de vendas e compras são sintéticos e passam pelo worker
isolado real do ETL. Cobre: migração aditiva sobre dados existentes, RLS e políticas
da Data API, paridade modelo/migração, gravação em Numeric, versão do processamento e
totais por situação, busca pelo nome normalizado, cascata ao excluir a análise, falha
do detalhamento sem perder os KPIs (nem ressuscitar o anterior), downgrade protegido e
o portal funcionando sem as tabelas (no PostgreSQL uma tabela ausente abortaria a
transação).
"""

import contextlib
from datetime import date, datetime
from decimal import Decimal
import io
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from flask import Flask
from sqlalchemy import func, inspect, select, text

from .deploy_support import ROOT
from .etl_equivalence_support import write_csv
from .postgresql_support import PrivatePostgreSQL
from extensions import db

SENHA = "Trilha serena 4821 norte"
TABELAS = ("indicador_complementar_analise", "produto_desempenho_analise")
REVISAO = "5a9c3e7d1b42"
ANTERIOR = "f4c2a8e1d9b6"


class PostgreSQLDetalhamentoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.postgresql = PrivatePostgreSQL()
        cls.addClassCleanup(cls.postgresql.close)

    def setUp(self):
        self.work = tempfile.TemporaryDirectory(prefix="nexo-pg-detalhe-")
        self.addCleanup(self.work.cleanup)
        self.root = Path(self.work.name)
        self.database = self.postgresql.create_database()
        self.addCleanup(self.postgresql.drop_database, self.database)
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        for alvo in ("socket.socket.connect", "socket.socket.connect_ex", "socket.create_connection"):
            self.stack.enter_context(patch(alvo, side_effect=AssertionError("Rede externa proibida")))
        with patch("dotenv.load_dotenv", return_value=False):
            import app as app_module
            from config import DevelopmentConfig
        uri = self.postgresql.url(self.database)
        valores = {
            "SECRET_KEY": "isolated-postgresql-detalhe-key",
            "SQLALCHEMY_DATABASE_URI": uri, "SQLALCHEMY_DIRECT_URI": uri,
            "SQLALCHEMY_ENGINE_OPTIONS": {"pool_pre_ping": True, "connect_args": {
                "connect_timeout": 5, "password": "", "passfile": str(self.postgresql.passfile),
                "options": "-c statement_timeout=30000 -c lock_timeout=10000",
            }},
            "UPLOAD_FOLDER": self.root / "uploads", "DEBUG": False, "SQLALCHEMY_ECHO": False, "TESTING": True,
            "MAIL_ATIVO": False, "MAIL_SUPPRESS_SEND": True, "MAIL_USERNAME": None, "MAIL_PASSWORD": None,
            "BREVO_API_KEY": None, "ANTHROPIC_API_KEY": None, "HF_API_TOKEN": None,
            "RATELIMIT_ENABLED": False, "PROXY_FIX_HOPS": 0,
        }
        with contextlib.ExitStack() as configuracao:
            for chave, valor in valores.items():
                configuracao.enter_context(patch.object(DevelopmentConfig, chave, valor, create=True))
            configuracao.enter_context(patch.object(
                app_module, "Flask", side_effect=lambda *a, **kw: Flask(*a, instance_path=str(self.root / "instance"),
                                                                       **kw)))
            self.app = app_module.create_app("development")
        self.vendas = write_csv(self.root / "vendas.csv", [
            ["Periodo de : 01/03/26 a 31/03/26"], ["Produto", "Un", "Quantidade", "Valor total"],
            ["Café torrado", "UN", "100", "2000,00"], ["Leite integral", "LT", "80", "400,00"],
            ["Pão de forma", "UN", "50", "150,00"], ["Item 50% _promo_", "UN", "3", "9,00"]])
        self.compras = write_csv(self.root / "compras.csv", [
            ["Periodo de : 01/03/26 a 31/03/26"], ["Produto", "Unidade", "Qtde Comprada", "Total Custo"],
            ["Café torrado", "UN", "160", "1500,00"], ["Leite integral", "UN", "60", "300,00"],
            ["Sabão em pó", "UN", "10", "50,00"]])
        with self.app.app_context():
            self.assertEqual(db.engine.url.host, str(self.postgresql.socket))
        self.addCleanup(self._encerrar)

    def _encerrar(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()

    def _migrar(self, comando, revisao="head"):
        import flask_migrate
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()), \
                patch("logging.config.fileConfig"):
            getattr(flask_migrate, comando)(directory=str(ROOT / "migrations"), revision=revisao)

    def _fixtures(self):
        from models import Analise, Empresa, Plano, RelatorioAnalise, Segmento, Usuario
        plano = Plano(nome_plano="BRONZE", valor_mensal=100, qtd_analises_mes=1, tipo_analise_permitida="MENSAL",
                      nivel_entrega_analise="BASICA", nivel_dashboard="RESUMIDO", nivel_atendimento="BAIXO")
        segmento = Segmento(nome_segmento="Segmento fictício")
        db.session.add_all([plano, segmento])
        db.session.flush()
        empresa = Empresa(id_segmento=segmento.id_segmento, id_plano_atual=plano.id_plano, cnpj="00000000000001",
                          razao_social="Empresa fictícia 1", email_contato="empresa1@example.invalid",
                          data_contratacao=date(2026, 1, 1))
        db.session.add(empresa)
        db.session.flush()
        admin = Usuario(nome="Admin Um", email="admin1@example.invalid", role="ADMIN", primeiro_acesso=False)
        cliente = Usuario(nome="Cliente Um", email="um@example.invalid", role="CLIENTE", primeiro_acesso=False,
                          id_empresa=empresa.id_empresa)
        for usuario in (admin, cliente):
            usuario.set_senha(SENHA)
        db.session.add_all([admin, cliente])
        db.session.flush()
        analise = Analise(id_empresa=empresa.id_empresa, id_plano_referencia=plano.id_plano,
                          id_usuario_admin_responsavel=admin.id_usuario, periodo_inicio=date(2026, 3, 1),
                          periodo_fim=date(2026, 3, 31), mes_referencia=3, ano_referencia=2026,
                          tipo_analise="MENSAL", status_analise="EM_ANALISE")
        db.session.add(analise)
        db.session.commit()
        self.id_analise = analise.id_analise
        return analise

    def _processar(self):
        import etl_processor
        resultado = etl_processor.processar_arquivos_analise(str(self.vendas), str(self.compras),
                                                             self.id_analise, db.session)
        db.session.commit()
        return resultado

    def _publicar(self):
        from models import Analise, RelatorioAnalise
        analise = db.session.get(Analise, self.id_analise)
        analise.status_analise, analise.data_conclusao = "CONCLUIDO", datetime(2026, 4, 2, 12)
        analise.relatorio = RelatorioAnalise(titulo="Análise fictícia", conclusao_estrategica="Conclusão fictícia",
                                             resumo_executivo="Resumo fictício", publicado=True,
                                             data_publicacao=datetime(2026, 4, 2, 12))
        analise.relatorio.congelar_publicacao()
        db.session.commit()

    def _entrar(self):
        cliente = self.app.test_client()
        pagina = cliente.get("/auth/login").get_data(as_text=True)
        csrf = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', pagina).group(1)
        resposta = cliente.post("/auth/login", data={"email": "um@example.invalid", "senha": SENHA,
                                                     "csrf_token": csrf})
        self.assertEqual(resposta.status_code, 302)
        return cliente

    def _contar(self, tabela):
        return db.session.scalar(text(f"SELECT count(*) FROM {tabela}"))

    def test_migracao_aditiva_sobre_dados_existentes_rls_e_politicas(self):
        from alembic.autogenerate import compare_metadata
        from alembic.migration import MigrationContext
        with self.app.app_context():
            self._migrar("upgrade", ANTERIOR)
            self._fixtures()
            # Papéis da Data API do Supabase, criados ANTES da revisão, e o que o Supabase faz
            # no schema public: tabela nova nasce acessível pela Data API. Sem o REVOKE da
            # migração, anon e authenticated ficariam com todos os privilégios.
            for comando in ('CREATE ROLE "anon" NOLOGIN', 'CREATE ROLE "authenticated" NOLOGIN',
                            'CREATE ROLE "service_role" NOLOGIN BYPASSRLS', 'CREATE ROLE "postgres" NOLOGIN',
                            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO anon, authenticated",
                            "GRANT USAGE ON SCHEMA public TO anon, authenticated"):
                db.session.execute(text(comando))
            db.session.commit()
            antes = {t: self._contar(t) for t in ("empresa", "usuario", "analise")}
            db.session.remove()
            self._migrar("upgrade", REVISAO)
            self.assertEqual({t: self._contar(t) for t in antes}, antes)
            for tabela in TABELAS:
                rls = db.session.execute(text(
                    "SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE oid = to_regclass(:t)"),
                    {"t": tabela}).one()
                self.assertEqual(tuple(rls), (True, False), tabela)
                # Definição completa: nome, tipo, papéis, USING e WITH CHECK.
                politicas = {tuple(linha) for linha in db.session.execute(text(
                    "SELECT policyname, permissive, array_to_string(ARRAY(SELECT unnest(roles) ORDER BY 1), ','), "
                    "qual, with_check FROM pg_policies WHERE tablename = :t"), {"t": tabela})}
                self.assertEqual(politicas, {
                    ("deny_api_access", "RESTRICTIVE", "anon,authenticated", "false", "false"),
                    ("acesso_servidor", "PERMISSIVE", "postgres,service_role", "true", "true"),
                }, tabela)
                for papel in ("anon", "authenticated"):
                    for privilegio in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE"):
                        self.assertFalse(db.session.scalar(text("SELECT has_table_privilege(:p, :t, :x)"),
                                                           {"p": papel, "t": tabela, "x": privilegio}),
                                         (papel, tabela, privilegio))
            self.assertEqual(self._contar("produto_desempenho_analise"), 0)
            db.session.rollback()
            with db.engine.connect() as conexao:
                contexto = MigrationContext.configure(conexao, opts={"compare_type": True})
                diferencas = [d for d in compare_metadata(contexto, db.metadata) if any(t in str(d) for t in TABELAS)]
            self.assertEqual(diferencas, [])

    def test_etl_grava_em_numeric_e_portal_busca_pelo_nome_normalizado(self):
        with self.app.app_context():
            self._migrar("upgrade")
            self._fixtures()
            resultado = self._processar()
            self.assertTrue(resultado.sucesso, resultado.mensagem)
            from models import IndicadorComplementarAnalise, ProdutoDesempenhoAnalise
            complemento = db.session.scalar(select(IndicadorComplementarAnalise))
            self.assertEqual(complemento.abc_total_produtos, 4)
            self.assertEqual(complemento.periodo_compras_inicio, date(2026, 3, 1))
            self.assertEqual(complemento.versao_processamento, 1)
            self.assertEqual(complemento.movimentacao_comparaveis + complemento.movimentacao_sem_venda
                             + complemento.movimentacao_unidade_divergente + complemento.movimentacao_unidade_ambigua
                             + complemento.movimentacao_quantidade_invalida, complemento.movimentacao_total)
            cafe = db.session.scalar(select(ProdutoDesempenhoAnalise).where(
                ProdutoDesempenhoAnalise.produto_nome == "Café torrado"))
            self.assertEqual((cafe.situacao_movimentacao, cafe.diferenca_quantidade), ("COMPARAVEL", Decimal("60.0")))
            leite = db.session.scalar(select(ProdutoDesempenhoAnalise).where(
                ProdutoDesempenhoAnalise.produto_nome == "Leite integral"))
            self.assertEqual(leite.situacao_movimentacao, "UNIDADE_DIVERGENTE")
            self.assertEqual(leite.produto_busca, "LEITE INTEGRAL")
            self._publicar()
        cliente = self._entrar()
        pagina = cliente.get("/cliente/dashboard")
        self.assertEqual(pagina.status_code, 200)
        self.assertIn("Café torrado", pagina.get_data(as_text=True))
        busca = cliente.get(f"/cliente/analise/{self.id_analise}/produtos?visao=ranking&busca=50%25 _promo_").json
        self.assertEqual([i["nome"] for i in busca["itens"]], ["Item 50% _promo_"])
        url = f"/cliente/analise/{self.id_analise}/produtos?visao=ranking"
        todos = cliente.get(url).json["total"]
        # "%" e "_" nunca funcionam como curinga: só pontuação equivale a não buscar.
        self.assertEqual(cliente.get(url + "&busca=%25").json["total"], todos)
        self.assertEqual(cliente.get(url + "&busca=1_0").json["total"], 0)
        # Sem acento, em maiúsculas ou com acento: o mesmo produto (como na consulta legada).
        for termo in ("cafe", "CAFE TORRADO", "caf%C3%A9"):
            self.assertEqual([i["nome"] for i in cliente.get(url + "&busca=" + termo).json["itens"]], ["Café torrado"])

    def test_falha_ao_gravar_detalhamento_preserva_kpis_e_exclusao_em_cascata(self):
        import etl_processor
        with self.app.app_context():
            self._migrar("upgrade")
            self._fixtures()
            # Erro inesperado (não de banco): o ETL falha fechado, sem gravação parcial.
            with patch.object(etl_processor, "_inserir_detalhamento", side_effect=RuntimeError("falha simulada")):
                self.assertFalse(self._processar().sucesso)
            self.assertEqual(self._contar("indicador_analise"), 0)
            # Falha de banco no detalhamento: o SAVEPOINT próprio isola e os KPIs ficam.
            from sqlalchemy.exc import OperationalError
            with patch.object(etl_processor, "_inserir_detalhamento",
                              side_effect=OperationalError("x", {}, Exception("queda simulada"))):
                resultado = self._processar()
            self.assertTrue(resultado.sucesso)
            self.assertEqual(self._contar("indicador_analise"), 1)
            self.assertEqual(self._contar("produto_desempenho_analise"), 0)
            self.assertTrue(self._processar().sucesso)
            self.assertGreater(self._contar("produto_desempenho_analise"), 0)
            # Reprocessamento cuja gravação falha: o detalhamento anterior não volta.
            with patch.object(etl_processor, "_inserir_detalhamento",
                              side_effect=OperationalError("x", {}, Exception("tempo esgotado simulado"))):
                self.assertTrue(self._processar().sucesso)
            self.assertEqual(self._contar("produto_desempenho_analise"), 0)
            self.assertEqual(self._contar("indicador_complementar_analise"), 0)
            self.assertTrue(self._processar().sucesso)
            self.assertGreater(self._contar("produto_desempenho_analise"), 0)
            from models import Analise
            db.session.delete(db.session.get(Analise, self.id_analise))
            db.session.commit()
            for tabela in TABELAS:
                self.assertEqual(self._contar(tabela), 0, tabela)

    def test_downgrade_protegido_e_portal_sem_as_tabelas(self):
        import detalhamento_produtos
        with self.app.app_context():
            self._migrar("upgrade")
            self._fixtures()
            self.assertTrue(self._processar().sucesso)
            db.session.remove()
            with self.assertRaises(SystemExit):
                self._migrar("downgrade", ANTERIOR)
            self.assertTrue(inspect(db.engine).has_table("produto_desempenho_analise"))
            db.session.execute(text("DELETE FROM produto_desempenho_analise"))
            db.session.execute(text("DELETE FROM indicador_complementar_analise"))
            db.session.commit()
            db.session.remove()
            self._migrar("downgrade", ANTERIOR)
            for tabela in TABELAS:
                self.assertFalse(inspect(db.engine).has_table(tabela), tabela)
            detalhamento_produtos._esquema_por_engine.clear()
            # Sem as tabelas: o ETL segue o caminho anterior e o portal não aborta transação.
            self.assertTrue(self._processar().sucesso)
            self._publicar()
        cliente = self._entrar()
        self.assertEqual(cliente.get("/cliente/dashboard").status_code, 200)
        consulta = cliente.get(f"/cliente/analise/{self.id_analise}/produtos?visao=ranking")
        self.assertEqual(consulta.status_code, 200)
        self.assertTrue(consulta.json["legado"])
        with self.app.app_context():
            db.session.remove()
            self._migrar("upgrade")
            self.assertTrue(inspect(db.engine).has_table("produto_desempenho_analise"))


if __name__ == "__main__":
    unittest.main()
