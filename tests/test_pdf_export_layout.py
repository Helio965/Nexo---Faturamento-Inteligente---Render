"""Layout, paginação e gráfico de pizza do PDF da análise (ReportLab), com dados sintéticos.

Da raiz: python -B -m unittest tests.test_pdf_export_layout -v
Sem banco, rede ou credenciais. A geometria (limites, sobreposições, títulos
isolados, rodapé) é lida do PDF gerado com o pdftotext; sem ele, esses testes
são ignorados e os testes estruturais continuam valendo.
"""

import copy
from decimal import Decimal
import unittest

from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, Table

import pdf_export
from tests import pdf_layout_support as apoio

LARGURA_UTIL = A4[0] - 2 * apoio.MARGEM


def _distribuicao_referencia():
    analise = apoio.analise_referencia()
    return pdf_export.calcular_distribuicao(analise.indicador.faturamento_total, analise.curva_abc[:5])


@unittest.skipUnless(apoio.pdftotext_disponivel(), "pdftotext indisponível: geometria não verificável")
class PDFLayoutGeometriaTests(unittest.TestCase):
    def test_01_cabecalho_completo_dentro_da_pagina(self):
        pagina = apoio.paginas(apoio.gerar())[0]
        textos = [l["texto"] for l in pagina["linhas"]]
        for esperado in ("NEXO", "Faturamento Inteligente", "Análise Executiva", "Referência 06/2026"):
            self.assertIn(esperado, textos)
        for linha in pagina["linhas"]:
            if linha["texto"] in ("NEXO", "Faturamento Inteligente", "Análise Executiva", "Referência 06/2026"):
                # Antes da correção a faixa media 0 × 0 e era desenhada acima da página (y < 0).
                self.assertGreaterEqual(linha["y0"], apoio.TOPO, linha)
                self.assertLessEqual(linha["y1"], apoio.TOPO + 22 * mm, linha)
        self.assertEqual(apoio.problemas_de_geometria(pagina), [])

    def test_02_indicadores_financeiros(self):
        pagina = apoio.paginas(apoio.gerar())[0]
        textos = [l["texto"] for l in pagina["linhas"]]
        for esperado in ("FATURAMENTO TOTAL", "TOTAL COMPRADO", "PRESSÃO DE ESTOQUE",
                         "R$ 4.311,00", "R$ 5.120,00", "R$ 809,00"):
            self.assertIn(esperado, textos)

    def test_03_valores_grandes_cabem_inteiros_nas_celulas(self):
        analise = apoio.analise_referencia()
        analise.indicador.faturamento_total = Decimal("987654321098.76")
        analise.indicador.total_comprado = Decimal("123456789012.34")
        analise.indicador.saldo_estimado_compras_vendas = Decimal("-864197532086.42")
        for p in analise.curva_abc:
            p.faturamento = p.faturamento * 229101000
        documento = apoio.gerar(analise)
        pagina = apoio.paginas(documento)[0]
        valores = {"R$ 987.654.321.098,76": None, "R$ 123.456.789.012,34": None, "R$ -864.197.532.086,42": None}
        for linha in pagina["linhas"]:
            if linha["texto"] in valores:
                valores[linha["texto"]] = linha
        self.assertTrue(all(valores.values()), valores)        # cada valor numa linha só, inteiro
        caixas = sorted(valores.values(), key=lambda l: l["x0"])
        coluna = LARGURA_UTIL / 3
        for i, linha in enumerate(caixas):
            self.assertGreaterEqual(linha["x0"], apoio.MARGEM + i * coluna, linha)
            self.assertLessEqual(linha["x1"], apoio.MARGEM + (i + 1) * coluna, linha)
        for p in apoio.paginas(documento):
            self.assertEqual(apoio.problemas_de_geometria(p), [])

    def test_04_curva_abc_preservada(self):
        documento = apoio.gerar()
        conteudo = apoio.texto(documento)
        for esperado in ("Curva ABC · Top 5 produtos (Princípio de Pareto)", "# Produto Classe Faturamento (R$) % acum.",
                         "1 Fax Térmico Panasonic A 3.200,00 74,2%", "2 Leitor Zip Drive Iomega B 760,00 91,9%",
                         "3 Mouse Bola Serial C 220,00 97,0%", "4 Pilha AA C 40,00 97,9%", "5 Diskette Maxell C 36,00 98,7%"):
            self.assertIn(esperado, conteudo)
        # Só os 5 primeiros na tabela (o 6º e o 7º entram em "Outros produtos").
        self.assertNotIn("Cabo Paralelo", conteudo)

    def test_05_nomes_longos_quebram_sem_invadir_a_coluna_da_classe(self):
        analise = apoio.analise_referencia()
        analise.curva_abc[0].produto_nome = ("Fax Térmico Panasonic KX-FT987 com bobina de papel térmico 216 mm × 30 m, "
                                             "cortador automático e secretária eletrônica digital — edição especial")
        analise.curva_abc[1].produto_nome = "LEITORZIPDRIVEIOMEGA100MBPARALELOEXTERNOSEMESPACOS" * 2
        documento = apoio.gerar(analise)
        # Coluna "Produto" da tabela (entre "#" e "Classe") e da legenda (entre a amostra e "Classe").
        fim_tabela = apoio.MARGEM + 10 * mm + (LARGURA_UTIL - 84 * mm)
        inicio_legenda = apoio.MARGEM + 62 * mm + 7 * mm
        fim_legenda = inicio_legenda + (LARGURA_UTIL - 62 * mm) - 70 * mm
        verificadas = {"tabela": 0, "legenda": 0}
        for pagina in apoio.paginas(documento):
            self.assertEqual(apoio.problemas_de_geometria(pagina), [])
            linhas = sorted(pagina["linhas"], key=lambda l: l["y0"])
            textos = [l["texto"] for l in linhas]
            regioes = []
            # Cada célula é uma linha no pdftotext: os cabeçalhos são localizados pelo texto exato.
            if "% acum." in textos:
                y0 = next(l["y1"] for l in linhas if l["texto"] == "% acum.")
                y1 = next(l["y0"] for l in linhas if l["texto"].startswith("Classe A: até 80%"))
                regioes.append(("tabela", y0, y1, apoio.MARGEM + 10 * mm, fim_tabela))
            if "Participação" in textos:
                y0 = next(l["y1"] for l in linhas if l["texto"] == "Participação")
                y1 = next(l["y0"] for l in linhas if l["texto"].startswith("Faturamento total"))
                regioes.append(("legenda", y0, y1, inicio_legenda, fim_legenda))
            for nome, y0, y1, x0, x1 in regioes:
                for linha in linhas:
                    for palavra in linha["palavras"]:
                        if y0 <= palavra["yMin"] < y1 and x0 - 1 <= palavra["xMin"] < x1:
                            self.assertLessEqual(palavra["xMax"], x1 + 0.5, (nome, palavra))
                            verificadas[nome] += 1
        self.assertGreater(verificadas["tabela"], 10)
        self.assertGreater(verificadas["legenda"], 10)

    def test_06_grafico_abaixo_da_tabela_e_antes_da_sintese(self):
        conteudo = apoio.texto(apoio.gerar())
        posicoes = [conteudo.index(t) for t in (
            "Curva ABC · Top 5", "Classe A: até 80%", "Distribuição do faturamento por produto",
            "Participação dos principais produtos no faturamento do período.", "Faturamento (R$) Participação",
            "Outros produtos — 55,00 1,28%", "Síntese executiva")]
        self.assertEqual(posicoes, sorted(posicoes))

    def test_07_legenda_e_percentuais_no_documento(self):
        conteudo = apoio.texto(apoio.gerar())
        for esperado in ("Fax Térmico Panasonic A 3.200,00 74,23%", "Leitor Zip Drive Iomega B 760,00 17,63%",
                         "Mouse Bola Serial C 220,00 5,10%", "Pilha AA C 40,00 0,93%", "Diskette Maxell C 36,00 0,84%",
                         "Outros produtos — 55,00 1,28%", "4.311,00 100,00%", "Faturamento total"):
            self.assertIn(esperado, conteudo)

    def test_10_sintese_executiva_sem_5w2h_e_com_todos_os_cartoes(self):
        conteudo = apoio.texto(apoio.gerar())
        self.assertIn("Síntese executiva", conteudo)
        self.assertNotIn("5W2H", conteudo)
        for card in apoio.semaforos_referencia():
            for campo in ("titulo", "o_que_fazer", "por_que"):
                self.assertIn(" ".join(card[campo].split()), conteudo)
        self.assertEqual(conteudo.count("O QUE FAZER"), 3)
        self.assertEqual(conteudo.count("POR QUE FAZER"), 3)
        for rotulo in ("CRÍTICO", "ATENÇÃO", "OPORTUNIDADE"):
            self.assertIn(rotulo, conteudo)

    def test_12_devolutiva_titulos_juntos_dos_textos_e_estrutura_preservada(self):
        documento = apoio.gerar()
        conteudo = apoio.texto(documento)
        ordem = [conteudo.index(t) for t in (
            "Devolutiva do consultor", "Resumo executivo", "O faturamento de junho somou R$ 4.311,00",
            "As compras superaram", "Conclusão estratégica", "Reduzir o ritmo de compras e priorizar o giro do estoque já adquirido.",
            "Proteger o abastecimento", "Revisar o mix em 30 dias.")]
        self.assertEqual(ordem, sorted(ordem))
        linhas = [l["texto"] for p in apoio.paginas(documento) for l in p["linhas"]]
        # Linha em branco = novo parágrafo; quebra simples = nova linha (como na página web).
        self.assertIn("Proteger o abastecimento do Fax Térmico Panasonic.", linhas)
        self.assertIn("Revisar o mix em 30 dias.", linhas)
        for pagina in apoio.paginas(documento):
            textos = [l["texto"] for l in sorted(apoio.linhas_do_corpo(pagina), key=lambda l: l["y0"])]
            for titulo in ("Devolutiva do consultor", "Resumo executivo", "Conclusão estratégica"):
                if titulo in textos:
                    self.assertLess(textos.index(titulo), len(textos) - 1, f"{titulo} sem texto na mesma página")

    def test_13_rodape_em_todas_as_paginas(self):
        frase = "Recomendamos acompanhar o giro do estoque e o prazo dos fornecedores antes de novas compras. "
        documento = apoio.gerar(apoio.analise_referencia(resumo=(frase * 12 + "\n\n") * 4, conclusao=(frase * 14 + "\n\n") * 5))
        paginas = apoio.paginas(documento)
        self.assertGreaterEqual(len(paginas), 3)
        for numero, pagina in enumerate(paginas, start=1):
            rodape = " ".join(l["texto"] for l in sorted(apoio.linhas_do_rodape(pagina), key=lambda l: (l["y0"], l["x0"])))
            with self.subTest(pagina=numero):
                self.assertIn(f"Página {numero} de {len(paginas)}", rodape)
                self.assertIn("Não representa lucro, margem ou CMV.", rodape)
                self.assertIn("Gerado em 29/10/2026 às 12:02 (horário de Brasília)", rodape)
                self.assertIn("NEXO · Empresa Demonstração · Referência 06/2026", rodape)
                self.assertEqual(apoio.problemas_de_geometria(pagina), [])

    def test_14_paginacao_sem_titulo_isolado_em_varias_combinacoes(self):
        frase = "A recomendação considera o giro do estoque, o prazo dos fornecedores e o ritmo das vendas. "
        longo = {"nivel": "atencao", "titulo": "Revisar o mix de produtos de baixa saída",
                 "o_que_fazer": "Reavaliar a reposição dos itens de Classe C e negociar troca com fornecedores. " * 3,
                 "por_que": "Itens de baixa saída concentram capital sem retorno proporcional no faturamento. " * 3}
        base = apoio.semaforos_referencia()
        casos = 0
        for n_cartoes in (1, 3, 5):
            for titulo_longo in (False, True):
                for n_resumo, n_conclusao in ((1, 1), (3, 6), (6, 9)):
                    analise = apoio.analise_referencia(resumo=frase * n_resumo * 2, conclusao=frase * n_conclusao * 2)
                    if titulo_longo:
                        analise.relatorio.titulo = "Análise consolidada com recomendações de reposição e escoamento — " * 3
                    cartoes = (base + [longo] * 3)[:n_cartoes]
                    documento = apoio.gerar(analise, semaforos=cartoes)
                    for numero, pagina in enumerate(apoio.paginas(documento), start=1):
                        with self.subTest(cartoes=n_cartoes, titulo_longo=titulo_longo, resumo=n_resumo,
                                          conclusao=n_conclusao, pagina=numero):
                            self.assertIsNone(apoio.titulo_isolado(pagina))
                            self.assertEqual(apoio.problemas_de_geometria(pagina), [])
                    casos += 1
        self.assertEqual(casos, 18)

    def test_15_documento_longo_preserva_todo_o_texto_em_ordem(self):
        paragrafos = [f"Parágrafo {i:02d}: orientação número {i} sobre reposição, giro e prazo dos fornecedores. " * 6
                      for i in range(1, 25)]
        documento = apoio.gerar(apoio.analise_referencia(resumo="\n\n".join(paragrafos[:8]),
                                                         conclusao="\n\n".join(paragrafos[8:])))
        paginas = apoio.paginas(documento)
        self.assertGreaterEqual(len(paginas), 4)
        conteudo = apoio.texto(documento)
        posicoes = [conteudo.index(f"Parágrafo {i:02d}:") for i in range(1, 25)]
        self.assertEqual(posicoes, sorted(posicoes))
        for i in range(1, 25):
            self.assertEqual(conteudo.count(f"Parágrafo {i:02d}:"), 6)
        for pagina in paginas:
            self.assertIsNone(apoio.titulo_isolado(pagina))
            self.assertEqual(apoio.problemas_de_geometria(pagina), [])

    def test_16_caracteres_especiais_preservados(self):
        analise = apoio.analise_referencia(
            resumo="Tintas & Cores <Premium> — “aspas” ‘simples’ € ™ ½ ç ã é ü Ñ ø\nSegunda linha com > e < e &amp; literal")
        analise.curva_abc[2].produto_nome = 'Produto <b>negrito literal</b> & “especial”'
        conteudo = apoio.texto(apoio.gerar(analise))
        for esperado in ("Tintas & Cores <Premium> — “aspas” ‘simples’ € ™ ½ ç ã é ü Ñ ø",
                         "Segunda linha com > e < e &amp; literal", 'Produto <b>negrito literal</b> & “especial”'):
            self.assertIn(esperado, conteudo)

    def test_17_data_de_geracao_no_fim_do_documento(self):
        conteudo = apoio.texto(apoio.gerar())
        self.assertIn("Documento gerado pelo portal NEXO em 29/10/2026 às 12:02 (horário de Brasília).", conteudo)

    def test_inconsistencia_soma_maior_que_o_total_e_explicita(self):
        apoio.reativar_logger_do_gerador(self)
        analise = apoio.analise_referencia()
        analise.indicador.faturamento_total = Decimal("4000.00")
        with self.assertLogs("pdf_export", level="WARNING"):
            conteudo = apoio.texto(apoio.gerar(analise))
        self.assertIn("Atenção: A soma dos produtos exibidos (R$ 4.256,00) é maior que o faturamento total "
                      "informado (R$ 4.000,00)", conteudo)
        self.assertNotIn("Outros produtos —", conteudo)          # sem a linha "Outros" na legenda
        self.assertIn("4.256,00 100,00%", conteudo)
        self.assertIn("Soma dos produtos exibidos", conteudo)


class PDFLayoutEstruturaTests(unittest.TestCase):
    """Sem pdftotext: estrutura dos flowables e cálculo do gráfico."""

    def test_barra_topo_declara_o_proprio_tamanho(self):
        barra = pdf_export._BarraTopo(LARGURA_UTIL, "Análise Executiva", "Referência 06/2026")
        self.assertEqual(barra.wrap(LARGURA_UTIL, 500), (LARGURA_UTIL, 22 * mm))

    def test_tabela_abc_e_quadro_de_indicadores_ocupam_a_largura_util(self):
        est = pdf_export._estilos()
        analise = apoio.analise_referencia()
        abc = pdf_export._abc_flowable(analise.curva_abc, LARGURA_UTIL, est)
        kpis = pdf_export._kpis_flowable(analise.indicador, LARGURA_UTIL, est)
        self.assertAlmostEqual(sum(abc._colWidths), LARGURA_UTIL, places=3)
        self.assertAlmostEqual(sum(kpis._colWidths), LARGURA_UTIL, places=3)
        self.assertEqual(len(abc._cellvalues), 6)                # cabeçalho + Top 5
        self.assertEqual(abc._cellvalues[1][2], "A")             # classe como texto literal

    def test_08_percentuais_individuais_da_referencia(self):
        distribuicao = _distribuicao_referencia()
        self.assertTrue(distribuicao.base_e_faturamento_total)
        self.assertEqual(distribuicao.base, Decimal("4311.00"))
        self.assertEqual([pdf_export._pct(f.percentual) for f in distribuicao.fatias],
                         ["74,23%", "17,63%", "5,10%", "0,93%", "0,84%", "1,28%"])
        # Participação = faturamento ÷ faturamento total × 100, sem ajuste para somar 100.
        for fatia in distribuicao.fatias:
            self.assertEqual(fatia.percentual, fatia.faturamento / Decimal("4311.00") * 100)

    def test_09_outros_produtos_so_quando_ha_faturamento_fora_do_top5(self):
        distribuicao = _distribuicao_referencia()
        outros = [f for f in distribuicao.fatias if f.outros]
        self.assertEqual(len(outros), 1)
        self.assertEqual(outros[0].nome, "Outros produtos")
        self.assertEqual(outros[0].faturamento, Decimal("55.00"))
        sem_outros = pdf_export.calcular_distribuicao(Decimal("4256.00"), apoio.analise_referencia().curva_abc[:5])
        self.assertFalse(any(f.outros for f in sem_outros.fatias))
        self.assertLess(abs(sum(f.percentual for f in sem_outros.fatias) - 100), Decimal("1e-20"))

    def test_inconsistencias_tratadas_explicitamente(self):
        apoio.reativar_logger_do_gerador(self)
        produtos = apoio.analise_referencia().curva_abc[:5]
        with self.assertLogs("pdf_export", level="WARNING"):
            maior = pdf_export.calcular_distribuicao(Decimal("4000"), produtos)
        self.assertFalse(maior.base_e_faturamento_total)
        self.assertEqual(maior.base, Decimal("4256.00"))
        self.assertFalse(any(f.outros for f in maior.fatias))
        self.assertTrue(maior.avisos)
        sem_total = pdf_export.calcular_distribuicao(None, produtos)
        self.assertEqual(sem_total.base, Decimal("4256.00"))
        self.assertTrue(sem_total.avisos)
        produtos[4].faturamento = Decimal("-3")
        negativo = pdf_export.calcular_distribuicao(Decimal("4311"), produtos)
        self.assertEqual(len([f for f in negativo.fatias if not f.outros]), 4)
        self.assertTrue(any("zero ou negativo" in a for a in negativo.avisos))
        self.assertIsNone(pdf_export.calcular_distribuicao(Decimal("10"), []))
        # Meio centavo de diferença é arredondamento, não inconsistência nem "Outros".
        arredondado = pdf_export.calcular_distribuicao(Decimal("4256.004"), apoio.analise_referencia().curva_abc[:5])
        self.assertFalse(any(f.outros for f in arredondado.fatias))
        self.assertTrue(arredondado.base_e_faturamento_total)

    def test_06_grafico_de_pizza_vetorial_com_os_mesmos_dados_da_tabela(self):
        distribuicao = _distribuicao_referencia()
        desenho = pdf_export._grafico_pizza(distribuicao, 54 * mm)
        self.assertIsInstance(desenho, Drawing)
        pizza = [c for c in desenho.contents if isinstance(c, Pie)]
        self.assertEqual(len(pizza), 1)
        pizza = pizza[0]
        produtos = apoio.analise_referencia().curva_abc[:5]
        self.assertEqual(pizza.data, [float(p.faturamento) for p in produtos] + [55.0])
        self.assertEqual(pizza.startAngle, 90)
        self.assertEqual(pizza.direction, "clockwise")
        # Percentual só dentro das fatias grandes; as pequenas ficam na legenda.
        self.assertEqual(pizza.labels, ["74,23%", "17,63%", "", "", "", ""])
        self.assertEqual(len(set(str(pizza.slices[i].fillColor) for i in range(6))), 6)

    def test_fatia_unica_mostra_100_por_cento_no_centro(self):
        produto = apoio.curva_referencia((("Tinta Construção", "1250.90"),))
        distribuicao = pdf_export.calcular_distribuicao(Decimal("1250.90"), produto)
        pizza = [c for c in pdf_export._grafico_pizza(distribuicao, 54 * mm).contents if isinstance(c, Pie)][0]
        self.assertEqual(pizza.labels, ["100,00%"])
        self.assertEqual(pizza.slices[0].labelRadius, 0)

    def test_07_legenda_com_cor_nome_classe_faturamento_e_percentual(self):
        distribuicao = _distribuicao_referencia()
        legenda = pdf_export._legenda_flowable(distribuicao, LARGURA_UTIL - 62 * mm, pdf_export._estilos())
        linhas = legenda._cellvalues
        self.assertEqual(len(linhas), 1 + 6 + 1)                 # cabeçalho, 5 produtos + Outros, total
        for fatia, linha in zip(distribuicao.fatias, linhas[1:7]):
            amostra, nome, classe, faturamento, percentual = linha
            self.assertIsInstance(amostra, Drawing)
            self.assertEqual(str(amostra.contents[0].fillColor), str(fatia.cor))
            self.assertIsInstance(nome, Paragraph)
            self.assertEqual(nome.getPlainText(), fatia.nome)
            self.assertEqual(classe, "—" if fatia.outros else fatia.classe)
            self.assertEqual(faturamento, pdf_export._brl(fatia.faturamento))
            self.assertEqual(percentual, pdf_export._pct(fatia.percentual))
        self.assertEqual(linhas[-1][3:], ["4.311,00", "100,00%"])
        for i in range(1, 7):
            self.assertGreaterEqual(min(s.fontSize for s in (linhas[i][1].style,)), 8)

    def test_11_titulo_da_sintese_sem_5w2h(self):
        textos = []
        original = pdf_export.Paragraph

        def capturar(*args, **kwargs):
            paragrafo = original(*args, **kwargs)
            textos.append(paragrafo.getPlainText())
            return paragrafo

        from unittest.mock import patch
        with patch.object(pdf_export, "Paragraph", side_effect=capturar):
            apoio.gerar()
        self.assertIn("Síntese executiva", textos)
        self.assertFalse(any("5W2H" in t for t in textos), [t for t in textos if "5W2H" in t])

    def test_secao_do_grafico_nao_se_parte_e_titulo_viaja_com_o_grafico(self):
        secao = pdf_export._secao_distribuicao(_distribuicao_referencia(), LARGURA_UTIL, pdf_export._estilos())
        self.assertIsInstance(secao, KeepTogether)
        conteudo = secao._content
        self.assertEqual(conteudo[0].getPlainText(), "Distribuição do faturamento por produto")
        self.assertEqual(conteudo[1].getPlainText(), "Participação dos principais produtos no faturamento do período.")
        corpo = [c for c in conteudo if isinstance(c, Table)][0]
        self.assertIsInstance(corpo._cellvalues[0][0], Drawing)  # gráfico à esquerda
        self.assertIsInstance(corpo._cellvalues[0][1], Table)    # legenda à direita

    def test_20_integridade_dos_dados_de_entrada_e_dos_valores(self):
        analise = apoio.analise_referencia()
        semaforos = apoio.semaforos_referencia()
        antes = copy.deepcopy((analise, semaforos))
        documento = apoio.gerar(analise, semaforos=semaforos)
        self.assertEqual((analise, semaforos), antes)
        self.assertTrue(documento.startswith(b"%PDF-"))
        distribuicao = _distribuicao_referencia()
        self.assertEqual([f.faturamento for f in distribuicao.fatias if not f.outros],
                         [p.faturamento for p in analise.curva_abc[:5]])
        self.assertEqual(sum(f.faturamento for f in distribuicao.fatias), analise.indicador.faturamento_total)

    def test_formatacao_monetaria_e_percentual(self):
        self.assertEqual(pdf_export._brl(Decimal("4311")), "4.311,00")
        self.assertEqual(pdf_export._brl(1250.90), "1.250,90")
        self.assertEqual(pdf_export._brl(None), "0,00")
        self.assertEqual(pdf_export._brl(Decimal("1.005")), "1,01")      # meio centavo para cima
        self.assertEqual(pdf_export._pct(Decimal("74.2287")), "74,23%")
        self.assertEqual(pdf_export._pct(Decimal("91.858"), 1), "91,9%")


if __name__ == "__main__":
    unittest.main()
