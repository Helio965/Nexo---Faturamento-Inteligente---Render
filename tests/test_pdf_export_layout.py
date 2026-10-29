"""Layout, paginação e gráfico de pizza do PDF da análise (ReportLab), com dados sintéticos.

Da raiz: python -B -m unittest tests.test_pdf_export_layout -v
Sem banco, rede ou credenciais. A geometria (limites, sobreposições, títulos
isolados, rodapé) é lida do PDF gerado com o pdftotext; sem ele, esses testes
são ignorados e os testes estruturais continuam valendo.
"""

import copy
from decimal import Decimal
from types import SimpleNamespace
import unittest

from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing
from reportlab.lib.colors import white
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, Table

import pdf_export
from tests import pdf_layout_support as apoio

LARGURA_UTIL = A4[0] - 2 * apoio.MARGEM


def _distribuicao_referencia():
    analise = apoio.analise_referencia()
    return pdf_export.calcular_distribuicao(analise.indicador.faturamento_total, analise.curva_abc[:5])


def _posicao(linhas, trecho):
    """Índice da primeira linha visual que contém o trecho (ValueError se nenhuma)."""
    for i, linha in enumerate(linhas):
        if trecho in linha:
            return i
    raise ValueError(f"{trecho!r} não está em nenhuma linha do documento")


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
        linhas = apoio.linhas_visuais(documento)
        esperadas = ("Curva ABC · Top 5 produtos (Princípio de Pareto)", "# Produto Classe Faturamento (R$) % acum.",
                     "1 Fax Térmico Panasonic A 3.200,00 74,2%", "2 Leitor Zip Drive Iomega B 760,00 91,9%",
                     "3 Mouse Bola Serial C 220,00 97,0%", "4 Pilha AA C 40,00 97,9%", "5 Diskette Maxell C 36,00 98,7%")
        posicoes = [_posicao(linhas, esperada) for esperada in esperadas]
        self.assertEqual(posicoes, sorted(posicoes))             # título, cabeçalho e linhas em ordem
        # Só os 5 primeiros na tabela (o 6º e o 7º entram em "Outros produtos").
        self.assertNotIn("Cabo Paralelo", apoio.texto(documento))

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
        linhas = apoio.linhas_visuais(apoio.gerar())
        posicoes = [_posicao(linhas, t) for t in (
            "Curva ABC · Top 5", "Classe A: até 80%", "Distribuição do faturamento por produto",
            "Participação dos principais produtos no faturamento do período.", "Faturamento (R$) Participação",
            "Outros produtos — 55,00 1,28%", "Síntese executiva")]
        self.assertEqual(posicoes, sorted(posicoes))

    def test_07_legenda_e_percentuais_no_documento(self):
        linhas = apoio.linhas_visuais(apoio.gerar())
        for esperado in ("Fax Térmico Panasonic A 3.200,00 74,23%", "Leitor Zip Drive Iomega B 760,00 17,63%",
                         "Mouse Bola Serial C 220,00 5,10%", "Pilha AA C 40,00 0,93%", "Diskette Maxell C 36,00 0,84%",
                         "Outros produtos — 55,00 1,28%", "Faturamento total 4.311,00 100,00%"):
            _posicao(linhas, esperado)
        conteudo = apoio.texto(apoio.gerar())
        self.assertIn("“Outros produtos” reúne o faturamento dos itens fora do Top 5.", conteudo)
        self.assertIn("Percentuais arredondados para duas casas decimais: a soma exibida pode diferir de 100% "
                      "por arredondamento.", conteudo)

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
                    paginas = apoio.paginas(apoio.gerar(analise, semaforos=cartoes))
                    for numero, pagina in enumerate(paginas, start=1):
                        with self.subTest(cartoes=n_cartoes, titulo_longo=titulo_longo, resumo=n_resumo,
                                          conclusao=n_conclusao, pagina=numero):
                            self.assertIsNone(apoio.titulo_isolado(pagina))
                            self.assertEqual(apoio.problemas_de_geometria(pagina), [])
                    with self.subTest(cartoes=n_cartoes, titulo_longo=titulo_longo, resumo=n_resumo,
                                      conclusao=n_conclusao):
                        self.assertEqual(apoio.lacunas_evitaveis(paginas), [])
                        self.assertEqual(apoio.grafico_partido(paginas), [])
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

    def test_18_horario_de_brasilia_no_rodape_e_na_frase_final(self):
        # Os casos de fuso (servidor em UTC, virada do dia, verão) estão em test_pdf_export_horario.py.
        from datetime import datetime, timezone
        documento = apoio.gerar(gerado_em=datetime(2026, 10, 30, 1, 15, tzinfo=timezone.utc))
        paginas = apoio.paginas(documento)
        for pagina in paginas:
            rodape = " ".join(l["texto"] for l in apoio.linhas_do_rodape(pagina))
            self.assertIn("Gerado em 29/10/2026 às 22:15 (horário de Brasília)", rodape)
        conteudo = apoio.texto(documento)
        self.assertIn("Documento gerado pelo portal NEXO em 29/10/2026 às 22:15 (horário de Brasília).", conteudo)
        self.assertNotIn("01:15", conteudo)

    def test_19_exportacoes_em_momentos_diferentes(self):
        from datetime import datetime, timezone
        primeira = apoio.texto(apoio.gerar(gerado_em=datetime(2026, 10, 29, 15, 2, tzinfo=timezone.utc)))
        segunda = apoio.texto(apoio.gerar(gerado_em=datetime(2026, 10, 29, 18, 47, tzinfo=timezone.utc)))
        self.assertIn("29/10/2026 às 12:02", primeira)
        self.assertIn("29/10/2026 às 15:47", segunda)
        # Só o carimbo muda: conteúdo, valores e período são os mesmos nas duas exportações.
        self.assertEqual(primeira.replace("12:02", "#"), segunda.replace("15:47", "#"))

    def test_inconsistencia_soma_maior_que_o_total_e_explicita(self):
        apoio.reativar_logger_do_gerador(self)
        analise = apoio.analise_referencia()
        analise.indicador.faturamento_total = Decimal("4000.00")
        with self.assertLogs("pdf_export", level="WARNING") as registro:
            conteudo = apoio.texto(apoio.gerar(analise))
        self.assertIn("Atenção: A soma dos produtos exibidos (R$ 4.256,00) é maior que o faturamento total "
                      "informado (R$ 4.000,00)", conteudo)
        self.assertIn("Soma dos produtos exibidos", conteudo)       # rótulo do total (em duas linhas)
        linhas = apoio.linhas_visuais(apoio.gerar(analise))
        self.assertFalse(any("Outros produtos —" in l for l in linhas))   # sem a linha "Outros" na legenda
        _posicao(linhas, "4.256,00 100,00%")
        # O log identifica a análise e o tipo de inconsistência, sem valores comerciais.
        self.assertEqual(len(registro.output), 1)
        self.assertIn("análise 5", registro.output[0])
        self.assertIn("soma_maior_que_total", registro.output[0])
        for valor in ("4256", "4.256", "4000", "4.000"):
            self.assertNotIn(valor, registro.output[0])

    def test_textos_gigantes_nao_impedem_a_exportacao(self):
        # Nomes e textos sem limite de tamanho no banco: o PDF sai sempre, sem nada fora do lugar.
        longo = ("Produto com descrição técnica muito detalhada vinda do ERP " * 200).strip()
        analise = apoio.analise_referencia(resumo="Texto do consultor. " * 1500, conclusao="Conclusão. " * 800)
        for p in analise.curva_abc:
            p.produto_nome = longo
        analise.curva_abc[1].produto_nome = "W" * 3000            # palavra única, sem espaço
        analise.empresa.nome_fantasia = "Empresa " * 1500
        analise.relatorio.titulo = "Título " * 400
        cartoes = apoio.semaforos_referencia()
        cartoes[1]["o_que_fazer"] = f"Criar ação de escoamento para “{longo}”."
        documento = apoio.gerar(analise, semaforos=cartoes)
        paginas = apoio.paginas(documento)
        self.assertGreater(len(paginas), 5)
        for numero, pagina in enumerate(paginas, start=1):
            with self.subTest(pagina=numero):
                self.assertEqual(apoio.problemas_de_geometria(pagina), [])
                self.assertIsNone(apoio.titulo_isolado(pagina))
                self.assertIsNone(apoio.pagina_sem_conteudo(pagina))
                rodape = " ".join(l["texto"] for l in apoio.linhas_do_rodape(pagina))
                self.assertIn(f"Página {numero} de {len(paginas)}", rodape)
                self.assertIn("Referência 06/2026", rodape)
        # Nada do texto do consultor é cortado (corpo das páginas, sem o rodapé no meio).
        corpo = " ".join(l["texto"] for p in paginas for l in sorted(apoio.linhas_do_corpo(p), key=lambda l: l["y0"]))
        self.assertEqual(corpo.count("Texto do consultor."), 1500)
        self.assertEqual(corpo.count("Conclusão."), 800)

    def test_rodape_mantem_a_referencia_com_razao_social_longa(self):
        analise = apoio.analise_referencia()
        analise.empresa.nome_fantasia = None
        analise.empresa.razao_social = ("COMÉRCIO DE MATERIAIS DE CONSTRUÇÃO E FERRAGENS IRMÃOS OLIVEIRA "
                                        "DA SILVA LTDA - EPP")
        for pagina in apoio.paginas(apoio.gerar(analise)):
            rodape = " ".join(l["texto"] for l in apoio.linhas_do_rodape(pagina))
            self.assertIn("NEXO · COMÉRCIO DE MATERIAIS", rodape)
            self.assertIn("· Referência 06/2026", rodape)
            self.assertIn("Gerado em 29/10/2026 às 12:02 (horário de Brasília)", rodape)
            self.assertEqual(apoio.problemas_de_geometria(pagina), [])

    def test_frase_final_e_titulos_nunca_ficam_sozinhos_numa_pagina(self):
        frase = "A recomendação considera o giro do estoque, o prazo dos fornecedores e o ritmo das vendas. "
        nome = "Produto com descricao muito longa "
        casos = []
        for n_resumo in (4, 8, 12):
            for n_conclusao in range(10, 26, 2):
                casos.append(apoio.analise_referencia(resumo=frase * n_resumo, conclusao=frase * n_conclusao))
        for tamanho in (262, 300, 320, 600, 2000):              # legenda com nomes longos
            analise = apoio.analise_referencia()
            for p in analise.curva_abc:
                p.produto_nome = (nome * 80)[:tamanho]
            casos.append(analise)
        for i, analise in enumerate(casos):
            paginas = apoio.paginas(apoio.gerar(analise))
            for numero, pagina in enumerate(paginas, start=1):
                with self.subTest(caso=i, pagina=numero):
                    self.assertIsNone(apoio.pagina_sem_conteudo(pagina))
                    self.assertIsNone(apoio.titulo_isolado(pagina))
                    self.assertEqual(apoio.problemas_de_geometria(pagina), [])
            with self.subTest(caso=i):
                self.assertEqual(apoio.lacunas_evitaveis(paginas), [])
                self.assertEqual(apoio.grafico_partido(paginas), [])

    def test_primeiro_paragrafo_longo_comeca_na_mesma_pagina(self):
        # Um resumo de um só bloco, longo: não deixa meia página em branco antes da devolutiva.
        frase = "O consultor recomenda revisar o mix, o giro do estoque e o prazo dos fornecedores antes de novas compras. "
        documento = apoio.gerar(apoio.analise_referencia(resumo=frase * 60))
        for pagina in apoio.paginas(documento):
            textos = [l["texto"] for l in apoio.linhas_do_corpo(pagina)]
            if any(t.startswith("Eles concentram") for t in textos):      # último cartão da síntese
                self.assertIn("Devolutiva do consultor", textos)
                self.assertIn("Resumo executivo", textos)
                break
        else:
            self.fail("último cartão da síntese não encontrado")
        # Todo o texto continua lá (corpo das páginas, sem o rodapé entre uma página e outra).
        corpo = " ".join(l["texto"] for p in apoio.paginas(documento)
                         for l in sorted(apoio.linhas_do_corpo(p), key=lambda l: l["y0"]))
        self.assertEqual(corpo.count("O consultor recomenda revisar o mix"), 60)

    def test_espaco_entre_secoes_some_no_topo_da_pagina(self):
        analise = apoio.analise_referencia()
        analise.relatorio.titulo = ("Análise executiva de faturamento, compras e estoque do mês de junho de 2026 com "
                                    "recomendações de reposição, escoamento de itens parados e proteção dos produtos "
                                    "estratégicos da Classe A")
        paginas = apoio.paginas(apoio.gerar(analise))
        self.assertGreaterEqual(len(paginas), 2)
        abertura = min(apoio.linhas_do_corpo(paginas[1]), key=lambda l: l["y0"])["texto"]
        self.assertTrue(any(abertura.startswith(t) for t in apoio.TITULOS_DE_SECAO), abertura)
        for pagina in paginas[1:]:
            primeira = min(apoio.linhas_do_corpo(pagina), key=lambda l: l["y0"])
            self.assertLess(primeira["y0"], apoio.TOPO + 2.5 * mm, primeira)

    def test_secao_sem_faturamento_positivo_explica_o_motivo(self):
        analise = apoio.analise_referencia()
        for p in analise.curva_abc:
            p.faturamento = -p.faturamento
        conteudo = apoio.texto(apoio.gerar(analise))
        self.assertIn("Distribuição do faturamento por produto", conteudo)
        self.assertIn("Atenção: Nenhum produto da tabela tem faturamento positivo", conteudo)

    def test_conclusao_curta_fica_na_pagina_do_resumo(self):
        # A conclusão típica tem um parágrafo (é o que ai_devolutiva pede à IA e o que o
        # texto determinístico produz): segue o resumo, sem ir sozinha para uma página nova.
        import ai_devolutiva
        contexto = {"referencia": "06/2026", "empresa": "Empresa Demonstração", "faturamento_total": Decimal("4311"),
                    "total_comprado": Decimal("5120"), "pressao_estoque": Decimal("809"), "abc_classe_a_qtd": 1,
                    "abc_classe_a_perc": 74.23, "abc_lider_nome": "Fax Térmico Panasonic", "abc_lider_perc": 74.23}
        deterministico = ai_devolutiva._gerar_fallback(contexto)
        frase = "Reduzir o ritmo de compras e priorizar o giro do estoque já adquirido no próximo ciclo. "
        casos = {"texto determinístico": (deterministico["resumo_executivo"], deterministico["conclusao_estrategica"]),
                 "uma frase": (None, frase), "quatro frases": (None, frase * 4), "nove frases": (None, frase * 9)}
        for rotulo, (resumo, conclusao) in casos.items():
            paginas = apoio.paginas(apoio.gerar(apoio.analise_referencia(resumo=resumo, conclusao=conclusao)))
            with self.subTest(caso=rotulo):
                self.assertEqual(len(paginas), 2)
                ultima = [l["texto"] for l in apoio.linhas_do_corpo(paginas[-1])]
                self.assertIn("Resumo executivo", ultima)
                self.assertIn("Conclusão estratégica", ultima)
                self.assertTrue(any(t.startswith(apoio.FECHAMENTO) for t in ultima))
                self.assertEqual(apoio.lacunas_evitaveis(paginas), [])

    def test_ultimo_bloco_nao_muda_de_pagina_com_espaco_sobrando(self):
        # A frase final entra no último bloco do documento sem forçar quebra de página,
        # seja ele um cartão, o gráfico ou a devolutiva sem texto.
        sem_devolutiva = apoio.analise_referencia()
        sem_devolutiva.relatorio = None
        so_grafico = apoio.analise_referencia()
        so_grafico.relatorio = None
        casos = (("sem devolutiva", sem_devolutiva, None, 2, "Eles concentram"),
                 ("sem devolutiva e sem cartões", so_grafico, [], 1, "Participação individual"),
                 ("devolutiva sem texto", apoio.analise_referencia(resumo="", conclusao=""), None, 2,
                  "Sem texto registrado pelo consultor."))
        for rotulo, analise, semaforos, esperadas, ultimo_bloco in casos:
            paginas = apoio.paginas(apoio.gerar(analise, semaforos=semaforos))
            with self.subTest(caso=rotulo):
                self.assertEqual(len(paginas), esperadas)
                self.assertEqual(apoio.lacunas_evitaveis(paginas), [])
                corpo = [l["texto"] for l in sorted(apoio.linhas_do_corpo(paginas[-1]), key=lambda l: l["y0"])]
                self.assertTrue(corpo[-1].startswith(apoio.FECHAMENTO), corpo)
                self.assertTrue(any(t.startswith(ultimo_bloco) for t in corpo), corpo)

    def _sem_titulo_isolado(self, documentos):
        for nome, analise, cartoes in documentos:
            paginas = apoio.paginas(apoio.gerar(analise, semaforos=cartoes))
            with self.subTest(caso=nome):
                for pagina in paginas:
                    self.assertIsNone(apoio.titulo_isolado(pagina))
                    self.assertIsNone(apoio.pagina_sem_conteudo(pagina))
                self.assertEqual(apoio.grafico_partido(paginas), [])
                self.assertEqual(apoio.lacunas_evitaveis(paginas), [])

    def test_titulos_da_devolutiva_nunca_isolados_em_qualquer_altura(self):
        # Varredura fina: o texto antes de cada título cresce aos poucos e leva o título
        # por todas as alturas da página, inclusive o pé.
        documentos = []
        for n in range(0, 140, 4):            # último cartão: "Devolutiva do consultor" e "Resumo executivo"
            cartoes = apoio.semaforos_referencia()
            cartoes[-1]["por_que"] += " Detalhe adicional do diagnóstico." * n
            documentos.append((f"cartão+{n}", apoio.analise_referencia(), cartoes))
        frase = "Giro do estoque e prazo dos fornecedores. "
        for n in range(1, 60, 2):             # resumo: "Conclusão estratégica"
            documentos.append((f"resumo×{n}", apoio.analise_referencia(resumo=frase * n), None))
        self._sem_titulo_isolado(documentos)

    def test_secoes_do_inicio_nunca_isoladas_no_pe_da_primeira_pagina(self):
        # O título do relatório cresce e empurra "Indicadores do período", "Curva ABC" e o
        # gráfico por todas as alturas da primeira página.
        documentos = []
        for n in range(1, 300, 4):
            analise = apoio.analise_referencia()
            analise.relatorio.titulo = ("Título " * n).strip()
            documentos.append((f"título×{n}", analise, None))
        self._sem_titulo_isolado(documentos)


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
        # Cabeçalho da Curva ABC preservado: fundo roxo NEXO e texto branco.
        self.assertIn(("BACKGROUND", (0, 0), (-1, 0), pdf_export.ROXO), abc._bkgrndcmds)
        self.assertEqual({c.color.hexval() for c in abc._cellStyles[0]}, {white.hexval()})

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
        apoio.reativar_logger_do_gerador(self)           # sem isto o assertNoLogs do fim não falharia nunca

        def top5():
            return apoio.analise_referencia().curva_abc[:5]

        maior = pdf_export.calcular_distribuicao(Decimal("4000"), top5())
        self.assertFalse(maior.base_e_faturamento_total)
        self.assertEqual(maior.base, Decimal("4256.00"))
        self.assertFalse(any(f.outros for f in maior.fatias))
        self.assertEqual(maior.inconsistencias, ("soma_maior_que_total",))
        sem_total = pdf_export.calcular_distribuicao(None, top5())
        self.assertEqual(sem_total.base, Decimal("4256.00"))
        self.assertEqual(sem_total.inconsistencias, ("total_ausente",))
        self.assertIn("não informado", sem_total.avisos[0])
        negativo_total = pdf_export.calcular_distribuicao(Decimal("-500"), top5())
        self.assertEqual(negativo_total.inconsistencias, ("total_nao_positivo",))
        self.assertIn("não é positivo (R$ -500,00)", negativo_total.avisos[0])
        # Produto da tabela sem valor válido: fora do gráfico, e o valor dele não vira "Outros".
        for invalido in (Decimal("-3"), None, Decimal("NaN"), "abc"):
            produtos = top5()
            produtos[4].faturamento = invalido
            d = pdf_export.calcular_distribuicao(Decimal("4311"), produtos)
            with self.subTest(invalido=invalido):
                self.assertEqual(len(d.fatias), 4)
                self.assertFalse(any(f.outros for f in d.fatias))
                self.assertFalse(d.base_e_faturamento_total)
                self.assertEqual(d.base, Decimal("4220.00"))
                self.assertIn("produto_sem_faturamento_positivo", d.inconsistencias)
                self.assertTrue(any("zero, negativo ou inválido" in a for a in d.avisos))
        nenhum = top5()
        for p in nenhum:
            p.faturamento = Decimal("-1")
        vazio = pdf_export.calcular_distribuicao(Decimal("4311"), nenhum)
        self.assertEqual(vazio.fatias, ())
        self.assertEqual(vazio.inconsistencias, ("sem_faturamento_positivo",))
        self.assertEqual(len(vazio.avisos), 1)
        self.assertIsNone(pdf_export.calcular_distribuicao(Decimal("10"), []))
        # Diferença menor que um centavo (invisível no documento) não é inconsistência nem "Outros".
        arredondado = pdf_export.calcular_distribuicao(Decimal("4256.004"), top5())
        self.assertFalse(any(f.outros for f in arredondado.fatias))
        self.assertTrue(arredondado.base_e_faturamento_total)
        # calcular_distribuicao é pura: o registro em log fica com gerar_pdf_analise.
        with self.assertNoLogs("pdf_export", level="WARNING"):
            pdf_export.calcular_distribuicao(Decimal("4000"), top5())

    def test_devolucoes_fora_da_tabela_sao_explicitadas(self):
        # Como o ETL grava: faturamento total = soma de todos os produtos (inclusive um com
        # devolução maior que a venda), Curva ABC = só os positivos, com 2 casas.
        produtos = apoio.analise_referencia().curva_abc[:5]
        for p in produtos:
            p.percentual_individual = (p.faturamento / Decimal("4311") * 100).quantize(Decimal("0.01"))
        d = pdf_export.calcular_distribuicao(Decimal("4281.00"), produtos)    # 4.311 − 30 de devolução
        self.assertTrue(d.base_e_faturamento_total)
        self.assertEqual(d.inconsistencias, ("base_abc_divergente",))
        self.assertIn("diferem do percentual individual da Curva ABC", d.avisos[0])
        self.assertEqual([f.faturamento for f in d.fatias if f.outros], [Decimal("25.00")])
        # Sem devolução, a participação calculada coincide com a gravada: nenhum aviso.
        self.assertEqual(pdf_export.calcular_distribuicao(Decimal("4311.00"), produtos).avisos, ())

    def test_legenda_tem_altura_limitada(self):
        produtos = apoio.analise_referencia().curva_abc[:5]
        for p in produtos:
            p.produto_nome = "Produto com descricao muito longa " * 60
        produtos[1].produto_nome = "W" * 2000
        distribuicao = pdf_export.calcular_distribuicao(Decimal("4311"), produtos)
        est = pdf_export._estilos()
        legenda = pdf_export._legenda_flowable(distribuicao, LARGURA_UTIL - 62 * mm, est)
        nome_largura = legenda._colWidths[1] - 7
        for linha in legenda._cellvalues[1:6]:
            altura = linha[1].wrap(nome_largura, 10_000)[1]
            self.assertLessEqual(altura, pdf_export.LINHAS_NOME_LEGENDA * est["leg"].leading + 0.5)
            self.assertTrue(linha[1].getPlainText().endswith("…"))
        secao = pdf_export._secao_distribuicao(distribuicao, LARGURA_UTIL, est)
        altura = sum(c.wrap(LARGURA_UTIL, 10_000)[1] + c.getSpaceAfter() for c in secao._content)
        self.assertLess(altura, pdf_export.ALTURA_UTIL)        # o bloco sempre cabe numa página

    def test_06_grafico_de_pizza_vetorial_com_os_mesmos_dados_da_tabela(self):
        # O gráfico e a legenda que o documento realmente desenha, não montados aqui.
        from unittest.mock import patch
        feitos = {}
        originais = {nome: getattr(pdf_export, nome) for nome in ("_grafico_pizza", "_legenda_flowable")}

        def registrar(nome):
            def chamar(distribuicao, *args, **kwargs):
                feitos[nome] = (distribuicao, originais[nome](distribuicao, *args, **kwargs))
                return feitos[nome][1]
            return chamar

        with patch.object(pdf_export, "_grafico_pizza", registrar("_grafico_pizza")), \
                patch.object(pdf_export, "_legenda_flowable", registrar("_legenda_flowable")):
            apoio.gerar()
        distribuicao, desenho = feitos["_grafico_pizza"]
        da_legenda, tabela = feitos["_legenda_flowable"]
        self.assertIs(da_legenda, distribuicao)
        produtos = apoio.analise_referencia().curva_abc[:5]
        self.assertEqual([f.nome for f in distribuicao.fatias],
                         [p.produto_nome for p in produtos] + ["Outros produtos"])   # ordem da tabela ABC
        self.assertIsInstance(desenho, Drawing)
        pizza = [c for c in desenho.contents if isinstance(c, Pie)]
        self.assertEqual(len(pizza), 1)
        pizza = pizza[0]
        self.assertIs(type(pizza), Pie)                          # 2D: Pie3d é subclasse de Pie e não serve
        self.assertEqual(pizza.data, [float(p.faturamento) for p in produtos] + [55.0])
        self.assertEqual(pizza.startAngle, 90)
        self.assertEqual(pizza.direction, "clockwise")
        # Percentual só dentro das fatias grandes; as pequenas ficam na legenda.
        self.assertEqual(pizza.labels, ["74,23%", "17,63%", "", "", "", ""])
        # Cores: rampa roxa na ordem da tabela, cinza em "Outros" e as mesmas amostras da legenda.
        cores = [pizza.slices[i].fillColor.hexval() for i in range(6)]
        self.assertEqual(cores, [c.hexval() for c in pdf_export.RAMPA_PIZZA] + [pdf_export.COR_OUTROS.hexval()])
        amostras = [linha[0][0] if isinstance(linha[0], tuple) else linha[0] for linha in tabela._cellvalues[1:7]]
        self.assertEqual([amostra.contents[0].fillColor.hexval() for amostra in amostras], cores)

    def test_paleta_do_grafico_na_identidade_nexo(self):
        import colorsys

        def hls(cor):
            return colorsys.rgb_to_hls(cor.red, cor.green, cor.blue)

        matiz_nexo = hls(pdf_export.ROXO)[0]
        luminosidades = []
        for cor in pdf_export.RAMPA_PIZZA:
            matiz, luz, saturacao = hls(cor)
            self.assertLess(abs(matiz - matiz_nexo) * 360, 15, cor.hexval())   # família do roxo NEXO
            self.assertGreater(saturacao, 0.4, cor.hexval())
            luminosidades.append(luz)
        self.assertEqual(luminosidades, sorted(set(luminosidades)))          # do mais escuro ao mais claro
        self.assertLess(hls(pdf_export.COR_OUTROS)[2], 0.25)                 # "Outros": cinza neutro

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
        # Sem letra miúda: nome (Paragraph) e classe, faturamento e participação (células de texto).
        for i in range(1, len(linhas)):
            self.assertGreaterEqual(linhas[i][1].style.fontSize, 8)
            for coluna in (2, 3, 4):
                self.assertGreaterEqual(legenda._cellStyles[i][coluna].fontsize, 8, (i, coluna))
        for coluna in (2, 3, 4):
            self.assertGreaterEqual(legenda._cellStyles[0][coluna].fontsize, 8)

    def test_11_titulo_da_sintese_sem_5w2h(self):
        textos = []

        class ParagrafoRegistrado(Paragraph):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                textos.append(self.getPlainText())

        from unittest.mock import patch
        with patch.object(pdf_export, "Paragraph", ParagrafoRegistrado):
            apoio.gerar()
        self.assertIn("Síntese executiva", textos)
        self.assertFalse(any("5W2H" in t for t in textos), [t for t in textos if "5W2H" in t])

    def test_notas_do_grafico_so_quando_se_aplicam(self):
        # A nota explica "Outros produtos" só quando a fatia existe, e o arredondamento só
        # quando os percentuais exibidos não somam 100,00% (sem ajustar os dados).
        est = pdf_export._estilos()

        def nota(distribuicao):
            secao = pdf_export._secao_distribuicao(distribuicao, LARGURA_UTIL, est)
            return next(c.getPlainText() for c in secao._content
                        if isinstance(c, Paragraph) and c.getPlainText().startswith("Participação individual ="))

        outros = "“Outros produtos” reúne o faturamento dos itens fora do Top 5."
        arredondamento = "Percentuais arredondados para duas casas decimais"
        referencia = nota(_distribuicao_referencia())                  # 74,23 + … + 1,28 = 100,01%
        self.assertIn(outros, referencia)
        self.assertIn(arredondamento, referencia)
        sem_outros = nota(pdf_export.calcular_distribuicao(Decimal("4256.00"), apoio.analise_referencia().curva_abc[:5]))
        self.assertNotIn("Outros produtos", sem_outros)
        self.assertIn(arredondamento, sem_outros)                      # 75,19 + … + 0,85 = 100,01%
        metades = apoio.curva_referencia((("Produto A", "50.00"), ("Produto B", "50.00")))
        exata = nota(pdf_export.calcular_distribuicao(Decimal("100.00"), metades))
        self.assertEqual(exata, "Participação individual = faturamento do produto ÷ faturamento total do período × 100.")

    def test_secao_do_grafico_nao_se_parte_e_titulo_viaja_com_o_grafico(self):
        secao = pdf_export._secao_distribuicao(_distribuicao_referencia(), LARGURA_UTIL, pdf_export._estilos())
        self.assertIsInstance(secao, KeepTogether)
        conteudo = secao._content
        self.assertEqual(conteudo[0].getPlainText(), "Distribuição do faturamento por produto")
        self.assertEqual(conteudo[1].getPlainText(), "Participação dos principais produtos no faturamento do período.")
        corpo = [c for c in conteudo if isinstance(c, Table)][0]
        grafico, legenda = corpo._cellvalues[0]
        self.assertIsInstance(grafico, Drawing)                  # gráfico à esquerda
        self.assertIsInstance(legenda, Table)                    # legenda à direita
        # O que o gráfico desenha fica dentro do próprio desenho e da coluna dele.
        x0, y0, x1, y1 = grafico.getBounds()
        self.assertGreaterEqual(min(x0, y0), 0)
        self.assertLessEqual(x1, min(grafico.width, corpo._colWidths[0]))
        self.assertLessEqual(y1, grafico.height)

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
        self.assertEqual(pdf_export._brl(Decimal("-864197532086.42")), "-864.197.532.086,42")
        self.assertEqual(pdf_export._pct(Decimal("74.2287")), "74,23%")
        self.assertEqual(pdf_export._pct(Decimal("91.858"), 1), "91,9%")

    def test_valores_iguais_aos_do_portal(self):
        """O PDF mostra os mesmos números que a página da análise para os mesmos dados
        gravados (mesma regra de arredondamento, inclusive nos empates)."""
        from pathlib import Path
        from jinja2 import Environment, FileSystemLoader
        raiz = Path(pdf_export.__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(raiz / "templates")))
        macros = env.get_template("_macros.html").module
        # Mesma expressão de templates/cliente/analise.html para "% acumulado".
        fonte = (raiz / "templates" / "cliente" / "analise.html").read_text(encoding="utf-8")
        expressao = "('%.1f'|format(p.percentual_acumulado|float))|replace('.', ',')"
        self.assertIn(expressao, fonte)
        percentual = env.from_string("{{ " + expressao + " }}%")
        for valor in (Decimal("12.4750000000"), Decimal("4311.125"), Decimal("0.005"), Decimal("1.005"),
                      Decimal("3200"), Decimal("987654321098.76"), Decimal("-30.555"), 1250.90, None):
            with self.subTest(valor=valor):
                self.assertEqual(pdf_export._brl(valor), str(macros.brl(valor)))
        for valor in (Decimal("91.85"), Decimal("91.8500000000"), Decimal("74.25"), Decimal("74.2287"),
                      Decimal("97.95"), Decimal("100")):
            with self.subTest(valor=valor):
                self.assertEqual(pdf_export._pct_gravado(valor),
                                 percentual.render(p=SimpleNamespace(percentual_acumulado=valor)))


if __name__ == "__main__":
    unittest.main()
