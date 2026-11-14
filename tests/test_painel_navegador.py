"""Visão Geral com o detalhamento completo, no navegador (Playwright/Chromium).

Reaproveita NavegadorCase (dados extensos, CDN íntegra servida localmente, medição de
cortes e overflow) e acrescenta à análise mais recente o detalhamento por produto que o
ETL gravaria: ranking completo (os 10 nomes longos no topo + 40 produtos), movimentação
com situações variadas e o resumo do universo. Verifica as oito larguras pedidas
(320 a 1920 px), os três temas, a consulta paginada e os filtros, sem erros de console.

Capturas para a documentação (opcional): NEXO_PAINEL_CAPTURAS=/pasta/destino.
"""

import os
from decimal import Decimal
from pathlib import Path

from tests.test_overflow_navegador import NavegadorCase, PRODUTOS_LONGOS

LARGURAS_PAINEL = ((320, 568), (360, 780), (390, 844), (430, 932), (768, 1024), (1024, 768), (1366, 768),
                   (1920, 1080))
GRAFICOS = ("chartCliente", "chartAbcCliente", "chartDistribuicaoClasses", "chartEvolucaoFaturamento",
            "chartHistoricoCliente")


class PainelNavegadorTests(NavegadorCase):
    def setUp(self):
        super().setUp()
        self.detalhar_analise_recente()

    def detalhar_analise_recente(self):
        from etl_processor import _normalizar_produto, chave_produto
        from models import IndicadorComplementarAnalise, ProdutoCurvaABC, ProdutoDesempenhoAnalise
        s = self.db.session
        topo = s.scalars(self.db.select(ProdutoCurvaABC).where(ProdutoCurvaABC.id_analise == self.analise_id)
                         .order_by(ProdutoCurvaABC.posicao_ranking)).all()
        extras = [(f"Produto complementar fictício {i:02d}", Decimal(1000 - i * 10)) for i in range(40)]
        total = sum((p.faturamento for p in topo), Decimal(0)) + sum((v for _, v in extras), Decimal(0))
        acumulado = Decimal(0)
        linhas = []
        for posicao, (nome, valor) in enumerate([(p.produto_nome, p.faturamento) for p in topo] + extras, start=1):
            individual = valor / total * 100
            acumulado += individual
            classe = "A" if acumulado <= 80 or posicao == 1 else ("B" if acumulado <= 95 else "C")
            linhas.append(dict(produto_chave=chave_produto(_normalizar_produto(nome)), produto_nome=nome,
                               posicao_ranking=posicao, classe_abc=classe, faturamento=valor,
                               quantidade_vendida=Decimal(100), percentual_individual=round(individual, 2),
                               percentual_acumulado=round(min(acumulado, Decimal(100)), 2)))
        movimentos = [(0, "300", "100", "COMPARAVEL"), (1, "150", "120", "COMPARAVEL"), (12, "80", "80", "COMPARAVEL"),
                      (3, "40", None, "UNIDADE_DIVERGENTE")]
        for ordem, (indice, comprada, vendida, situacao) in enumerate(movimentos, start=1):
            linha = linhas[indice]
            linha.update(quantidade_comprada=Decimal(comprada), posicao_movimentacao=ordem,
                         situacao_movimentacao=situacao, unidade_compra="CX" if situacao != "COMPARAVEL" else "UN",
                         unidade_venda="UN",
                         diferenca_quantidade=(Decimal(comprada) - Decimal(vendida)) if vendida else None)
        semvenda = dict(produto_chave=chave_produto("ITEM SEM VENDA FICTICIO"), produto_nome="Item sem venda fictício",
                        quantidade_comprada=Decimal(25), posicao_movimentacao=len(movimentos) + 1,
                        situacao_movimentacao="SEM_VENDA_CORRESPONDENTE", unidade_compra="UN")
        contagem = {c: sum(1 for l in linhas if l["classe_abc"] == c) for c in "ABC"}
        soma = {c: sum((l["faturamento"] for l in linhas if l["classe_abc"] == c), Decimal(0)) for c in "ABC"}
        s.add(IndicadorComplementarAnalise(
            id_analise=self.analise_id, versao_metodologia=1, versao_processamento=1,
            abc_total_produtos=len(linhas), abc_faturamento_total=total,
            abc_produtos_a=contagem["A"], abc_produtos_b=contagem["B"], abc_produtos_c=contagem["C"],
            abc_faturamento_a=soma["A"], abc_faturamento_b=soma["B"], abc_faturamento_c=soma["C"],
            produtos_vendas=len(linhas), produtos_compras=len(movimentos) + 1, compras_por_produto=True,
            unidade_vendas_informada=True, unidade_compras_informada=True, produtos_registrados=len(linhas) + 1,
            ranking_registrado=len(linhas), movimentacao_total=len(movimentos) + 1,
            movimentacao_registrada=len(movimentos) + 1, registro_limitado=False))
        for linha in linhas + [semvenda]:
            s.add(ProdutoDesempenhoAnalise(id_analise=self.analise_id, **linha))
        s.commit()

    def _desenhados(self, pagina):
        return pagina.evaluate("ids => ids.filter(id => { const el = document.getElementById(id); "
                               "return el && el.querySelector('.main-svg') && el.getAttribute('role') === 'img'; })",
                               list(GRAFICOS))

    def test_painel_completo_sem_cortes_nas_oito_larguras(self):
        for largura, altura in LARGURAS_PAINEL:
            pagina = self.abrir(largura, altura)
            self.entrar(pagina, "cliente-test@example.invalid")
            self.ir(pagina, "/cliente/dashboard")
            pagina.wait_for_timeout(250)
            self.assertEqual(sorted(self._desenhados(pagina)), sorted(GRAFICOS), f"gráficos @ {largura}px")
            self.assert_layout(pagina, largura, f"painel @ {largura}px")
            self.assert_fim_da_pagina(pagina, f"painel @ {largura}px")
            rolagem = pagina.evaluate("document.documentElement.scrollHeight > innerHeight")
            self.assertTrue(rolagem, "a Visão Geral continua vertical e rolável")
            pagina.context.close()

    def test_consulta_paginada_filtros_e_busca(self):
        # `expect` reavalia o DOM até o tempo-limite: sem esperas fixas que, com a máquina
        # carregada, leriam a tabela antes de a resposta ser aplicada.
        from playwright.sync_api import expect
        pagina = self.abrir(1366, 900)
        self.entrar(pagina, "cliente-test@example.invalid")
        self.ir(pagina, "/cliente/dashboard")
        ranking = pagina.locator('.painel-consulta[data-consulta="ranking"]')
        status = ranking.locator("[data-status]")
        nomes = ranking.locator("tbody tr td:nth-child(2)")
        self.assertEqual(ranking.locator("tbody tr").count(), 25)
        ranking.locator('[data-pagina="proxima"]').click()
        expect(status).to_contain_text("Página 2 de 2")
        expect(ranking.locator("tbody tr").first.locator("td").first).to_have_text("26º")
        ranking.locator('.painel-filtro[data-classe="C"]').click()
        expect(status).to_contain_text("Página 1 de ")  # filtro novo volta à primeira página
        classes = ranking.locator("tbody tr td:nth-child(3)").all_inner_texts()
        self.assertTrue(classes and all(c.strip() == "C" for c in classes))
        # Classe C + busca: exatamente o item procurado (lista vazia não passa).
        ranking.locator("[data-busca]").fill("Granola")
        expect(nomes).to_have_text(["Granola premium com castanhas 1 kg"])
        expect(status).to_contain_text("1 produto(s)")
        # Sem diferenciar acentos nem maiúsculas: espera a resposta deste termo (não a
        # tabela da busca anterior). A busca é por trecho contínuo do nome.
        with pagina.expect_response(lambda r: "busca=agua+MINERAL" in r.url):
            ranking.locator("[data-busca]").fill("agua MINERAL")
        expect(nomes).to_have_text(["Água mineral com gás 500 ml"])
        expect(status).to_contain_text("1 produto(s)")
        ranking.locator("[data-busca]").fill("produto inexistente xyz")
        expect(ranking.locator("tbody td[colspan]")).to_have_text("Nenhum produto encontrado com esses filtros.")
        mov = pagina.locator('.painel-consulta[data-consulta="movimentacao"]')
        self.assertEqual(mov.locator("tbody tr").count(), 2)  # compras acima das vendas
        mov.locator('.painel-filtro[data-filtro="unidades"]').click()
        expect(mov.locator("tbody")).to_contain_text("Unidades diferentes")
        expect(mov.locator('.painel-filtro[aria-pressed="true"]')).to_have_text("Unidade diferente ou ausente")
        mov.locator('.painel-filtro[data-filtro="todas"]').click()
        expect(mov.locator("[data-status]")).to_contain_text("5 produto(s)")

    def test_acoes_seguidas_antes_da_resposta_se_compoem(self):
        from playwright.sync_api import expect
        pagina = self.abrir(1366, 900)
        self.entrar(pagina, "cliente-test@example.invalid")
        self.ir(pagina, "/cliente/dashboard")
        ranking = pagina.locator('.painel-consulta[data-consulta="ranking"]')
        # Dois cliques no mesmo instante, antes de qualquer resposta: Classe C e Próxima.
        pagina.evaluate("""() => {
            const caixa = document.querySelector('.painel-consulta[data-consulta="ranking"]');
            caixa.querySelector('.painel-filtro[data-classe="C"]').click();
            caixa.querySelector('[data-pagina="proxima"]').click();
        }""")
        expect(ranking.locator("[data-status]")).to_contain_text("Página 2 de 2")
        expect(ranking.locator('.painel-filtro[aria-pressed="true"]')).to_have_text("Classe C")
        classes = ranking.locator("tbody tr td:nth-child(3)").all_inner_texts()
        self.assertTrue(classes and all(c.strip() == "C" for c in classes), classes)

    def test_graficos_e_estados_visuais(self):
        pagina = self.abrir(1366, 900)
        self.entrar(pagina, "cliente-test@example.invalid")
        self.ir(pagina, "/cliente/dashboard")
        pagina.wait_for_function("() => { const el = document.getElementById('chartEvolucaoFaturamento');"
                                 " return el && el.data && el.layout; }")
        grafico = pagina.evaluate("""() => {
            const el = document.getElementById('chartEvolucaoFaturamento');
            const pontos = dashboardData.historico.pontos;
            const esperado = pontos.map(p => (Date.parse(p.fim) - Date.parse(p.inicio) + 864e5) * 0.8);
            const atual = (el.layout.annotations || []).filter(a => String(a.text).includes('Atual'));
            return { larguras: Array.from(el.data[0].width), esperado: esperado, atual: atual.length,
                     x: atual.length ? atual[0].x : null,
                     xAtual: (pontos.find(p => p.atual) || {}).meio };
        }""")
        # Cada barra tem a largura do próprio período (lacunas ficam visíveis) e o
        # período desta análise é marcado em texto.
        self.assertEqual(grafico["larguras"], grafico["esperado"])
        self.assertEqual(grafico["atual"], 1)
        self.assertEqual(grafico["x"], grafico["xAtual"])
        borda = pagina.evaluate("getComputedStyle(document.querySelector("
                                "'.painel-consulta .painel-filtro[aria-pressed=\"true\"]')).borderTopWidth")
        self.assertEqual(borda, "2px")
        self.assertIn("% acumulado na linha (no celular, junto ao nome do produto)",
                      pagina.locator("#curva-abc").inner_text())

    def test_consulta_no_celular_rotulos_erros_e_pagina_sem_salto(self):
        from playwright.sync_api import expect
        pagina = self.abrir(390, 844)
        self.entrar(pagina, "cliente-test@example.invalid")
        self.ir(pagina, "/cliente/dashboard")
        ranking = pagina.locator('.painel-consulta[data-consulta="ranking"]')
        status = ranking.locator("[data-status]")
        # Falha transitória (limite de consultas, HTML 429): mensagem própria e nenhuma
        # página pulada na nova tentativa.
        pagina.route("**/produtos?*pagina=2*", lambda rota: rota.fulfill(
            status=429, content_type="text/html", body="<html><body>Muitas requisições</body></html>"))
        ranking.locator('[data-pagina="proxima"]').click()
        expect(status).to_contain_text("Muitas consultas em sequência")
        pagina.unroute("**/produtos?*pagina=2*")
        with pagina.expect_response(lambda r: "/produtos?" in r.url) as resposta:
            ranking.locator('[data-pagina="proxima"]').click()
        self.assertIn("pagina=2", resposta.value.url)
        expect(status).to_contain_text("Página 2 de 2")
        # Linhas trazidas pela consulta mantêm o nome da coluna no modo cartão do celular.
        primeira = ranking.locator("tbody tr").first
        expect(primeira.locator("td").first).to_have_text("26º")
        self.assertEqual(primeira.get_attribute("role"), "row")
        rotulos = primeira.locator("td").evaluate_all("tds => tds.map(td => td.getAttribute('data-label'))")
        self.assertEqual(rotulos, ["#", "Produto", "Classe", "Faturamento", "% individual", "% acumulado",
                                   "Qtde vendida"])
        # Análise despublicada no meio da consulta (404): não é sessão expirada.
        pagina.route("**/produtos?*", lambda rota: rota.fulfill(status=404, content_type="text/html", body="<html></html>"))
        ranking.locator('.painel-filtro[data-classe="B"]').click()
        expect(status).to_contain_text("não está mais disponível")
        # A falha não troca o filtro marcado nem a tabela exibida (estado coerente).
        expect(ranking.locator('.painel-filtro[aria-pressed="true"]')).to_have_text("Todas")
        expect(ranking.locator("tbody tr").first.locator("td").first).to_have_text("26º")
        pagina.context.close()
        # Só os dois erros HTTP simulados acima podem constar no console.
        simulados = [e for e in self.erros_js if "status of 429" in e or "status of 404" in e]
        self.assertEqual(len(simulados), 2, self.erros_js)
        self.erros_js = [e for e in self.erros_js if e not in simulados]

    def test_temas_claro_escuro_e_sistema(self):
        for tema, esquema in (("dark", "dark"), ("light", "light"), ("system", "light"), ("system", "dark")):
            pagina = self.abrir(1366, 900)
            pagina.emulate_media(color_scheme=esquema)
            self.entrar(pagina, "cliente-test@example.invalid")
            pagina.evaluate("t => localStorage.setItem('theme', t)", tema)
            self.ir(pagina, "/cliente/dashboard")
            esperado = esquema if tema == "system" else tema
            self.assertEqual(pagina.evaluate("document.documentElement.getAttribute('data-theme')"), esperado)
            self.assertEqual(pagina.evaluate("NEXO.tema"), esperado)
            self.assertEqual(sorted(self._desenhados(pagina)), sorted(GRAFICOS), f"tema {tema}/{esquema}")
            # Texto do painel legível sobre a superfície (sem branco no claro nem preto no escuro).
            cor = pagina.evaluate("getComputedStyle(document.querySelector('.resumo-destaques li')).color")
            self.assertNotEqual(cor, "rgb(255, 255, 255)" if esperado == "light" else "rgb(0, 0, 0)")
            pagina.context.close()

    def test_capturas_para_documentacao(self):
        destino = os.environ.get("NEXO_PAINEL_CAPTURAS")
        if not destino:
            self.skipTest("Capturas só quando NEXO_PAINEL_CAPTURAS indica a pasta de destino.")
        pasta = Path(destino)
        pasta.mkdir(parents=True, exist_ok=True)
        secoes = ("indicadores", "resumo-executivo", "insights", "curva-abc", "movimentacao", "compras-vendas",
                  "evolucao-faturamento", "evolucao-compras-vendas", "recomendacoes", "historico-devolutiva")
        for tema in ("dark", "light"):
            for largura, altura in ((1366, 900), (390, 844)):
                pagina = self.abrir(largura, altura)
                self.entrar(pagina, "cliente-test@example.invalid")
                pagina.evaluate("t => localStorage.setItem('theme', t)", tema)
                self.ir(pagina, "/cliente/dashboard")
                pagina.wait_for_timeout(400)
                pagina.screenshot(path=str(pasta / f"painel_{tema}_{largura}_topo.jpg"), type="jpeg", quality=82)
                # Por seção (capturas de página inteira passam do limite de textura do Chromium).
                # Cabeçalho fixo e botão do NexoBot ficam ocultos só nessas capturas: na captura
                # por elemento eles seriam pintados por cima do conteúdo da seção.
                pagina.evaluate("() => ['header.topbar', '#nexobot'].forEach(s => {"
                                " const el = document.querySelector(s); if (el) el.style.visibility = 'hidden'; })")
                for numero, secao in enumerate(secoes, start=1):
                    pagina.locator(f"#{secao}").screenshot(
                        path=str(pasta / f"painel_{tema}_{largura}_{numero:02d}_{secao}.jpg"), type="jpeg", quality=82)
                pagina.context.close()
        self.assertTrue(any(pasta.iterdir()))
        self.assertEqual(len(PRODUTOS_LONGOS), 10)
