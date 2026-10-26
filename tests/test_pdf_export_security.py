"""Regressões NEXO-SEC-001: dados sintéticos, PDF em memória e I/O bloqueado.

Da raiz: PYTHONPATH=. python -B tests/test_pdf_export_security.py -v
Não instancia a factory, não acessa banco e não exige serviços ou credenciais.
pdftotext é opcional e usado somente para inspecionar bytes via stdin/stdout.
"""

import contextlib
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

import pdf_export


def _dados():
    empresa = SimpleNamespace(
        nome_fantasia="Tintas & Cores", razao_social="Construção São Paulo",
        cnpj="00.000.000/0001-00",
    )
    relatorio = SimpleNamespace(
        titulo="Análise de reposição", resumo_executivo="Ação recomendada: reposição gradual.",
        conclusao_estrategica="Não ampliar compras sem acompanhar a demanda.",
    )
    indicador = SimpleNamespace(
        faturamento_total=1250.90, total_comprado=1500,
        saldo_estimado_compras_vendas=249.10,
    )
    analise = SimpleNamespace(
        id_analise=17, mes_referencia=10, ano_referencia=2026,
        periodo_inicio=date(2026, 10, 1), periodo_fim=date(2026, 10, 31),
        empresa=empresa, relatorio=relatorio, indicador=indicador,
    )
    produtos = [SimpleNamespace(
        posicao_ranking=1, produto_nome="Tinta Construção", classe_abc="A",
        faturamento=1250.90, percentual_acumulado=80,
    )]
    semaforos = [{
        "nivel": "atencao", "titulo": "Pressão de estoque",
        "o_que_fazer": "Acompanhar a reposição.",
        "por_que": "As compras superam o faturamento do período.",
    }]
    return analise, semaforos, produtos


class _PDFChecks:
    @contextlib.contextmanager
    def _sem_recursos(self):
        """Intercepta os pontos realmente usados pelo parser/imagens ReportLab."""
        with contextlib.ExitStack() as stack:
            loaders = []
            for target in (
                "reportlab.platypus.paraparser.ImageReader",
                "reportlab.lib.utils.open_for_read",
                "reportlab.lib.utils.open_for_read_by_name",
                "urllib.request.urlopen",
                "socket.create_connection", "socket.socket.connect",
                "socket.socket.connect_ex",
            ):
                loaders.append(stack.enter_context(patch(
                    target, side_effect=AssertionError("Recurso externo/local proibido no PDF"),
                )))
            for method in ("linkURL", "linkRect"):
                loaders.append(stack.enter_context(patch.object(
                    Canvas, method, side_effect=AssertionError("Link ativo proibido nos dados"),
                )))
            yield
            for loader in loaders:
                loader.assert_not_called()

    def _gerar(self, dados):
        with self._sem_recursos():
            result = pdf_export.gerar_pdf_analise(*dados)
        self.assertIsInstance(result, bytes)
        self.assertTrue(result.startswith(b"%PDF-"))
        self.assertIn(b"%%EOF", result[-100:])
        return result

    def _texto(self, documento):
        executable = shutil.which("pdftotext")
        if executable is None:
            self.skipTest("pdftotext indisponível; geração e segurança possuem testes independentes")
        result = subprocess.run(
            [executable, "-enc", "UTF-8", "-", "-"], input=documento,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=15,
        )
        return " ".join(result.stdout.decode("utf-8").split())


class PDFExportSecurityTests(_PDFChecks, unittest.TestCase):
    def test_interceptacao_alcanca_o_loader_real_do_parser(self):
        # Controle positivo: sem escape, o Paragraph original tentaria carregar img.
        with patch("reportlab.platypus.paraparser.ImageReader",
                   side_effect=RuntimeError("sentinela-loader")) as loader:
            with self.assertRaisesRegex(Exception, "sentinela-loader"):
                Paragraph('<img src="https://pdf.invalid/p.png"/>', pdf_export._estilos()["p"])
        loader.assert_called_once_with("https://pdf.invalid/p.png")

    def test_produto_com_img_permanece_literal_sem_carregador(self):
        dados = _dados()
        payload = '<img src="https://pdf.invalid/p.png"/>'
        dados[2][0].produto_nome = payload
        self._gerar(dados)
        with self._sem_recursos():
            table = pdf_export._abc_flowable(dados[2], 440, pdf_export._estilos())
        self.assertEqual(table._cellvalues[1][1].getPlainText(), payload)

    def test_todos_campos_comerciais_impedem_img_externa(self):
        payload = '<img src="https://pdf.invalid/p.png"/>'
        fields = (
            "produto", "classe", "fantasia", "razao", "cnpj", "titulo",
            "resumo", "conclusao", "semaforo_titulo", "acao", "justificativa", "nivel",
        )
        for field in fields:
            with self.subTest(field=field):
                dados = _dados()
                analise, semaforos, produtos = dados
                if field in ("produto", "classe"):
                    setattr(produtos[0], "produto_nome" if field == "produto" else "classe_abc", payload)
                elif field in ("fantasia", "razao", "cnpj"):
                    if field == "razao":
                        analise.empresa.nome_fantasia = None
                    setattr(analise.empresa, {
                        "fantasia": "nome_fantasia", "razao": "razao_social", "cnpj": "cnpj",
                    }[field], payload)
                elif field in ("titulo", "resumo", "conclusao"):
                    setattr(analise.relatorio, {
                        "titulo": "titulo", "resumo": "resumo_executivo", "conclusao": "conclusao_estrategica",
                    }[field], payload)
                else:
                    semaforos[0][{
                        "semaforo_titulo": "titulo", "acao": "o_que_fazer",
                        "justificativa": "por_que", "nivel": "nivel",
                    }[field]] = payload
                original = pdf_export.Paragraph
                textos = []

                def paragraph(*args, **kwargs):
                    result = original(*args, **kwargs)
                    textos.append(result.getPlainText())
                    return result

                with patch.object(pdf_export, "Paragraph", side_effect=paragraph):
                    self._gerar(dados)
                if field == "classe":
                    # Células str da Table usam canvas literal, sem parser XML.
                    table = pdf_export._abc_flowable(produtos, 440, pdf_export._estilos())
                    self.assertEqual(table._cellvalues[1][2], payload)
                else:
                    esperado = payload.upper() if field == "nivel" else payload
                    self.assertTrue(any(esperado in texto for texto in textos), textos)

    def test_caminho_local_sintetico_nao_e_lido_por_marcacao(self):
        # O arquivo só existe nesta área descartável; nenhum arquivo real é usado.
        with tempfile.TemporaryDirectory(prefix="nexo-pdf-security-") as directory:
            local = Path(directory) / "synthetic.txt"
            local.write_text("CONTEUDO_SINTETICO_NAO_DEVE_ENTRAR_NO_PDF", encoding="utf-8")
            dados = _dados()
            dados[2][0].produto_nome = f'<img src="{local}"/>'
            self._gerar(dados)
            dados[0].relatorio.conclusao_estrategica = f'<img src="{local.as_uri()}"/>'
            self._gerar(dados)

    def test_links_permanecem_texto_sem_anotacoes_ativas(self):
        for payload in (
            '<a href="https://pdf.invalid/">Abrir relatório</a>',
            '<link href="https://pdf.invalid/">Abrir relatório</link>',
        ):
            with self.subTest(payload=payload):
                dados = _dados()
                dados[0].relatorio.resumo_executivo = payload
                dados[2][0].produto_nome = payload
                documento = self._gerar(dados)
                self.assertNotIn(b"/Subtype /Link", documento)
                with self._sem_recursos():
                    table = pdf_export._abc_flowable(dados[2], 440, pdf_export._estilos())
                self.assertEqual(table._cellvalues[1][1].getPlainText(), payload)

    def test_caracteres_especiais_e_entidades_sao_preservados_uma_vez(self):
        for texto in (
            "Tintas & Cores", "Produto <Premium>", "Linha > Industrial", "A & B < C",
            "Literal &amp; e &lt;img&gt;", '<b>Nome literal</b>',
            '&#60;img src="https://pdf.invalid/x"/&#62;',
            '&#x3c;img src="https://pdf.invalid/x"/&#x3e;',
            '<img src="x"', "Ação Construção Reposição Não São Paulo",
        ):
            with self.subTest(texto=texto):
                dados = _dados()
                dados[2][0].produto_nome = texto
                self._gerar(dados)
                with self._sem_recursos():
                    table = pdf_export._abc_flowable(dados[2], 440, pdf_export._estilos())
                self.assertEqual(table._cellvalues[1][1].getPlainText(), texto)

    def test_semaforos_preservam_texto_literal_e_formatacao_fixa(self):
        card = {
            "nivel": "atencao", "titulo": "Ação <b>não confiável</b> & reposição",
            "o_que_fazer": "A & B < C", "por_que": "Produto <Premium>",
        }
        with self._sem_recursos():
            table = pdf_export._semaforo_flowable(card, 440, pdf_export._estilos())
        internal = table._cellvalues[0][0]
        title = internal._cellvalues[0][0]
        self.assertEqual(title.getPlainText(), card["titulo"] + " · ATENÇÃO")
        self.assertEqual(internal._cellvalues[2][0].getPlainText(), card["o_que_fazer"])
        self.assertEqual(internal._cellvalues[4][0].getPlainText(), card["por_que"])
        self.assertTrue(any(f.fontName == "Helvetica-Bold" for f in title.frags))
        self.assertTrue(any(f.fontSize == 7 for f in title.frags))

    def test_nivel_desconhecido_nao_injeta_marcacao(self):
        payload = '<img src="https://pdf.invalid/p.png"/>'
        dados = _dados()
        dados[1][0]["nivel"] = payload
        self._gerar(dados)
        with self._sem_recursos():
            table = pdf_export._semaforo_flowable(dados[1][0], 440, pdf_export._estilos())
        titulo = table._cellvalues[0][0]._cellvalues[0][0].getPlainText()
        self.assertIn(payload.upper(), titulo)

    def test_pdf_completo_preserva_a4_componentes_e_valores(self):
        dados = _dados()
        documento = self._gerar(dados)
        media_box = re.search(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", documento)
        self.assertIsNotNone(media_box)
        self.assertAlmostEqual(float(media_box[1]), A4[0], places=3)
        self.assertAlmostEqual(float(media_box[2]), A4[1], places=3)
        texto = self._texto(documento)
        for esperado in (
            "NEXO", "Faturamento Inteligente", "Análise Executiva", "Referência 10/2026",
            "Indicadores do período", "FATURAMENTO TOTAL", "TOTAL COMPRADO", "PRESSÃO DE ESTOQUE",
            "R$ 1.250,90", "R$ 1.500,00", "R$ 249,10", "Curva ABC", "Tinta Construção",
            "Síntese executiva (5W2H)", "O QUE FAZER", "POR QUE FAZER", "ATENÇÃO",
            "Devolutiva do consultor", "Resumo executivo.", "Conclusão estratégica.",
            "Documento gerado pelo portal NEXO", "Página 1", "Não representa lucro, margem ou CMV.",
            "Tintas & Cores", "Análise de reposição",
        ):
            with self.subTest(esperado=esperado):
                self.assertIn(esperado, texto)

    def test_opcionais_ausentes_e_listas_vazias(self):
        dados = _dados()
        dados[0].relatorio = None
        dados[0].indicador = None
        dados[0].empresa.nome_fantasia = None
        documento = self._gerar((dados[0], [], []))
        texto = self._texto(documento)
        self.assertIn("Análise publicada", texto)
        self.assertIn("Construção São Paulo", texto)

    def test_resumo_nulo_e_textos_vazios_nao_quebram_documento(self):
        dados = _dados()
        dados[0].relatorio.resumo_executivo = None
        dados[0].relatorio.conclusao_estrategica = ""
        dados[2][0].produto_nome = ""
        dados[1][0]["o_que_fazer"] = ""
        dados[1][0]["por_que"] = ""
        self._gerar(dados)

    def test_textos_longos_e_unicode_usual(self):
        dados = _dados()
        dados[2][0].produto_nome = "Tinta São Paulo – Construção & Reposição " * 7
        dados[1][0]["o_que_fazer"] = "Ação de reposição: não ampliar compras sem demanda. " * 10
        dados[0].relatorio.conclusao_estrategica = "Ação Construção Reposição Não São Paulo – € " * 10
        texto = self._texto(self._gerar(dados))
        for esperado in ("Tinta São Paulo", "Construção & Reposição", "Ação Construção Reposição Não São Paulo"):
            self.assertIn(esperado, texto)

    def test_renderizacao_nao_modifica_os_dados_de_entrada(self):
        import copy
        dados = _dados()
        dados[0].relatorio.resumo_executivo = "A & B < C"
        dados[2][0].produto_nome = '<b>Produto & família</b>'
        antes = copy.deepcopy(dados)
        self._gerar(dados)
        self.assertEqual(dados, antes)


class PDFPortalContractTests(_PDFChecks, unittest.TestCase):
    """Blueprint real, autenticação Flask-Login e banco inteiramente simulado."""

    def setUp(self):
        from flask import Flask
        from flask_login import LoginManager
        from blueprints import cliente

        self.cliente_module = cliente
        self.analise, self.semaforos, produtos = _dados()
        self.analise.id_empresa = 42
        self.analise.status_analise = "CONCLUIDO"
        self.analise.curva_abc = produtos
        self.analise.relatorio.publicado = True
        self.analise.indicador.periodo_base_inicio = self.analise.indicador.periodo_base_fim = None
        self.usuario = SimpleNamespace(
            is_authenticated=True, is_active=True, is_anonymous=False, is_cliente=True,
            empresa=SimpleNamespace(id_empresa=42),
        )
        self.app = Flask(__name__)
        self.app.config.update(
            SECRET_KEY="isolated-pdf-portal-test-key", TESTING=True,
            DEBUG=False, PROPAGATE_EXCEPTIONS=False,
        )
        manager = LoginManager(self.app)
        manager.user_loader(lambda identifier: self.usuario if identifier == "1" else None)
        self.app.register_blueprint(cliente.cliente_bp, url_prefix="/cliente")
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session["_user_id"] = "1"
            session["_fresh"] = True
        self.path = "/cliente/analise/17/pdf"
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.db_get = MagicMock(return_value=self.analise)
        self.stack.enter_context(patch.object(
            cliente, "db", SimpleNamespace(session=SimpleNamespace(get=self.db_get)),
        ))
        self.stack.enter_context(patch.object(cliente, "gerar_semaforos", return_value=self.semaforos))
        # Política contratual simulada: regime legado, empresa ATIVA (sem banco).
        import contract_policy
        self.situacao = contract_policy.SituacaoContratual(
            id_empresa=42, regime=contract_policy.REGIME_LEGADO, estado=contract_policy.ESTADO_ATIVA,
            status_conta="ATIVA", instante=datetime(2026, 10, 26, 12, tzinfo=timezone.utc),
        )
        self.stack.enter_context(patch.object(
            cliente, "obter_situacao_contratual", side_effect=lambda empresa: self.situacao,
        ))

    def test_cliente_autorizado_recebe_pdf_e_nome_de_download(self):
        with self._sem_recursos():
            response = self.client.get(self.path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertEqual(response.headers["Content-Disposition"],
                         'attachment; filename="analise_nexo_202610_17.pdf"')
        self.assertTrue(response.data.startswith(b"%PDF-"))
        self.assertEqual(self.analise.indicador.faturamento_total, 1250.90)

    def test_anonimo_nao_recebe_pdf(self):
        with patch.object(self.cliente_module, "gerar_pdf_analise") as render:
            response = self.app.test_client().get(self.path)
        self.assertEqual(response.status_code, 401)
        render.assert_not_called()
        self.db_get.assert_not_called()

    def test_admin_nao_recebe_pdf_pela_rota_cliente(self):
        self.usuario.is_cliente = False
        with patch.object(self.cliente_module, "gerar_pdf_analise") as render:
            response = self.client.get(self.path)
        self.assertEqual(response.status_code, 403)
        render.assert_not_called()
        self.db_get.assert_not_called()

    def test_outra_empresa_analise_ausente_e_nao_publicada_sao_negadas(self):
        for condition in ("outra_empresa", "ausente", "estado", "sem_relatorio", "nao_publicado"):
            with self.subTest(condition=condition):
                self.analise.id_empresa = 42
                self.analise.status_analise = "CONCLUIDO"
                self.analise.relatorio = _dados()[0].relatorio
                self.analise.relatorio.publicado = True
                self.db_get.return_value = self.analise
                if condition == "outra_empresa":
                    self.analise.id_empresa = 99
                elif condition == "ausente":
                    self.db_get.return_value = None
                elif condition == "estado":
                    self.analise.status_analise = "EM_ANALISE"
                elif condition == "sem_relatorio":
                    self.analise.relatorio = None
                else:
                    self.analise.relatorio.publicado = False
                with patch.object(self.cliente_module, "gerar_pdf_analise") as render:
                    response = self.client.get(self.path)
                self.assertEqual(response.status_code, 404)
                render.assert_not_called()

    def test_prazo_de_exportacao_encerrado_bloqueia_antes_de_gerar(self):
        import contract_policy
        instante = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)
        self.situacao = contract_policy.SituacaoContratual(
            id_empresa=42, regime=contract_policy.REGIME_CONTRATUAL, estado=contract_policy.ESTADO_SUSPENSA,
            status_conta="SUSPENSA", instante=instante, suspensao_limite=instante + timedelta(days=60),
            pdf_limite=instante, intervalos_pagos=((date(2026, 10, 1), date(2026, 10, 31)),),
        )
        with patch.object(self.cliente_module, "gerar_pdf_analise") as render, \
                patch.object(self.cliente_module, "render_template", return_value="restrito"):
            response = self.client.get(self.path)
        self.assertEqual(response.status_code, 403)
        self.assertNotEqual(response.mimetype, "application/pdf")
        render.assert_not_called()

    def test_periodo_nao_pago_bloqueia_antes_de_gerar(self):
        import contract_policy
        instante = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)
        self.situacao = contract_policy.SituacaoContratual(
            id_empresa=42, regime=contract_policy.REGIME_CONTRATUAL, estado=contract_policy.ESTADO_ATIVA,
            status_conta="ATIVA", instante=instante, intervalos_pagos=(),
        )
        with patch.object(self.cliente_module, "gerar_pdf_analise") as render, \
                patch.object(self.cliente_module, "render_template", return_value="restrito"):
            response = self.client.get(self.path)
        self.assertEqual(response.status_code, 403)
        render.assert_not_called()

    def test_erro_de_geracao_nao_expoe_detalhes_na_resposta(self):
        with patch.object(self.cliente_module, "gerar_pdf_analise",
                          side_effect=RuntimeError("INTERNAL_SYNTHETIC_SENTINEL")), \
                patch.object(self.app.logger, "error"):
            response = self.client.get(self.path)
        self.assertEqual(response.status_code, 500)
        self.assertNotIn(b"INTERNAL_SYNTHETIC_SENTINEL", response.data)
        self.assertNotIn(b"Traceback", response.data)


if __name__ == "__main__":
    unittest.main()
