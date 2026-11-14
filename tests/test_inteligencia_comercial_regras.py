"""Regras da Visão Geral (inteligencia_comercial.py): cálculos, histórico, Curva ABC,
movimentação, insights, recomendações e resumo — sem banco e sem Flask.

Os objetos são SimpleNamespace com os mesmos atributos das linhas ORM; os valores são
sintéticos. Cada regra é testada pela condição verificável que a ativa (`rastreio`)."""

from datetime import date, datetime
from decimal import Decimal as D
from types import SimpleNamespace as NS
import unittest

import inteligencia_comercial as ic


def indicador(fat="10000", compras="9000", saldo=None, inicio=None, fim=None, parado_nome=None, parado=None):
    fat_d, compras_d = (D(fat) if fat is not None else None), (D(compras) if compras is not None else None)
    if saldo is None and fat_d is not None and compras_d is not None:
        saldo = compras_d - fat_d
    return NS(faturamento_total=fat_d, total_comprado=compras_d, saldo_estimado_compras_vendas=saldo,
              periodo_base_inicio=inicio, periodo_base_fim=fim, produto_maior_saldo_parado_nome=parado_nome,
              saldo_estimado_parado=parado, produto_mais_vendido_nome=None, produto_mais_vendido_quantidade=None)


def analise(id_, inicio, fim, tipo="MENSAL", quinzena=None, fat="10000", compras="9000", conclusao=None,
            ind=True, base=None):
    return NS(id_analise=id_, periodo_inicio=inicio, periodo_fim=fim, tipo_analise=tipo,
              quinzena_referencia=quinzena, mes_referencia=inicio.month, ano_referencia=inicio.year,
              data_conclusao=conclusao or datetime(2026, 1, 1) ,
              indicador=indicador(fat, compras, inicio=base[0] if base else None,
                                  fim=base[1] if base else None) if ind else None)


def complemento(**campos):
    base = dict(abc_total_produtos=10, abc_faturamento_total=D("1000"), abc_produtos_a=2, abc_produtos_b=3,
                abc_produtos_c=5, abc_faturamento_a=D("800"), abc_faturamento_b=D("150"), abc_faturamento_c=D("50"),
                produtos_registrados=10, registro_limitado=False, compras_por_produto=True,
                unidade_vendas_informada=True, unidade_compras_informada=True, ranking_registrado=10,
                movimentacao_total=4, movimentacao_registrada=4, periodos_divergentes=False)
    base.update(campos)
    return NS(**base)


class FormatacaoTests(unittest.TestCase):
    def test_moeda_quantidade_percentual_pt_br(self):
        self.assertEqual(ic.fmt_moeda(D("1234567.891")), "R$ 1.234.567,89")
        self.assertEqual(ic.fmt_moeda(D("-0.5")), "-R$ 0,50")
        self.assertEqual(ic.fmt_moeda(D("10"), sinal=True), "+R$ 10,00")
        self.assertEqual(ic.fmt_moeda(None), "—")
        self.assertEqual(ic.fmt_quantidade(D("1234")), "1.234")
        self.assertEqual(ic.fmt_quantidade(D("12.5")), "12,5")
        self.assertEqual(ic.fmt_quantidade_sinal(D("-5")), "-5")
        self.assertEqual(ic.fmt_quantidade_sinal(D("20")), "+20")
        self.assertEqual(ic.fmt_percentual(D("12.345")), "12,3%")
        self.assertEqual(ic.fmt_percentual(D("-3.05"), sinal=True), "-3,1%")

    def test_decimal_sem_ruido_de_float_e_meio_para_cima(self):
        self.assertEqual(ic.moeda(0.1 + 0.2), D("0.30"))
        self.assertEqual(ic.moeda(D("2.675")), D("2.68"))  # float(2.675) arredondaria para 2.67
        self.assertIsNone(ic.dec(float("nan")))
        self.assertIsNone(ic.dec(True))
        self.assertIsNone(ic.percentual(1, 0))

    def test_percentuais_de_exibicao_somam_100(self):
        self.assertEqual(sum(ic.percentuais_somando_100([D("79.94"), D("15.06"), D("5.0")])), D("100.0"))
        self.assertEqual(ic.percentuais_somando_100([1, 1, 1]), [D("33.4"), D("33.3"), D("33.3")])
        self.assertEqual(ic.percentuais_somando_100([0, 0, 0]), [D("0"), D("0"), D("0")])
        self.assertEqual(ic.percentuais_somando_100([D("100"), D("0"), D("0")]), [D("100.0"), D("0.0"), D("0.0")])


class SerieHistoricaTests(unittest.TestCase):
    def mensal(self, id_, mes, ano=2026, **kw):
        inicio = date(ano, mes, 1)
        fim = (date(ano + (mes == 12), mes % 12 + 1, 1) - date.resolution)
        return analise(id_, inicio, fim, conclusao=datetime(ano, mes, 28) if mes < 12 else datetime(ano, 12, 30), **kw)

    def test_nenhuma_e_uma_analise_nao_formam_serie(self):
        self.assertEqual(ic.montar_serie_historica([], None).pontos, [])
        unica = self.mensal(1, 1)
        serie = ic.montar_serie_historica([unica], unica)
        self.assertEqual(len(serie.pontos), 1)
        self.assertIsNone(serie.anterior)
        self.assertFalse(ic.interpretar_evolucao_faturamento(serie)["disponivel"])
        self.assertFalse(ic.interpretar_evolucao_compras_vendas(serie)["disponivel"])

    def test_duas_analises_em_ordem_cronologica_com_variacao(self):
        jan, fev = self.mensal(1, 1, fat="1000"), self.mensal(2, 2, fat="1100")
        serie = ic.montar_serie_historica([fev, jan], fev)
        self.assertEqual([p.rotulo for p in serie.pontos], ["01/2026", "02/2026"])
        self.assertEqual(serie.anterior.id_analise, 1)
        var = ic.variacao(serie.atual.faturamento, serie.anterior.faturamento)
        self.assertEqual(var["percentual"], D("10.0"))
        self.assertEqual(var["direcao"], "alta")

    def test_mensal_e_quinzenal_nao_se_misturam(self):
        jan = self.mensal(1, 1)
        q1 = analise(2, date(2026, 2, 1), date(2026, 2, 15), tipo="QUINZENAL", quinzena=1)
        fev = self.mensal(3, 2)
        serie = ic.montar_serie_historica([jan, q1, fev], fev)
        self.assertEqual([p.id_analise for p in serie.pontos], [1, 3])
        self.assertEqual(serie.excluidas["tipo_diferente"], 1)
        self.assertIn("outro tipo de período", ic.interpretar_evolucao_faturamento(serie)["texto"])

    def test_quinzenas_tem_rotulos_distintos(self):
        q1 = analise(1, date(2026, 3, 1), date(2026, 3, 15), tipo="QUINZENAL", quinzena=1)
        q2 = analise(2, date(2026, 3, 16), date(2026, 3, 31), tipo="QUINZENAL", quinzena=2)
        serie = ic.montar_serie_historica([q1, q2], q2)
        self.assertEqual([p.rotulo for p in serie.pontos], ["1ª quinz. 03/2026", "2ª quinz. 03/2026"])

    def test_periodo_sobreposto_nao_duplica_e_mantem_o_mais_recente(self):
        antiga = analise(1, date(2026, 3, 1), date(2026, 3, 31), conclusao=datetime(2026, 4, 2))
        corrigida = analise(2, date(2026, 3, 1), date(2026, 3, 31), conclusao=datetime(2026, 4, 9), fat="12000")
        abril = self.mensal(3, 4)
        serie = ic.montar_serie_historica([antiga, corrigida, abril], abril)
        self.assertEqual([p.id_analise for p in serie.pontos], [2, 3])
        self.assertEqual(serie.excluidas["sobreposta"], 1)

    def test_analise_atual_vence_sobreposicao(self):
        nova = analise(1, date(2026, 3, 1), date(2026, 3, 31), conclusao=datetime(2026, 4, 9))
        atual = analise(2, date(2026, 3, 2), date(2026, 3, 31), conclusao=datetime(2026, 4, 2))
        serie = ic.montar_serie_historica([nova, atual], atual)
        self.assertEqual([p.id_analise for p in serie.pontos], [2])
        self.assertTrue(serie.atual_comparavel)

    def test_periodo_atipico_do_arquivo_fica_fora_e_atual_nao_comparavel(self):
        fev = self.mensal(1, 2)
        # Declarada mensal, mas o relatório cobre um trimestre inteiro.
        trimestre = analise(2, date(2026, 3, 1), date(2026, 3, 31), base=(date(2026, 1, 1), date(2026, 3, 31)))
        serie = ic.montar_serie_historica([fev, trimestre], trimestre)
        self.assertFalse(serie.atual_comparavel)
        self.assertEqual(serie.excluidas["periodo_atipico"], 1)
        leitura = ic.interpretar_evolucao_faturamento(serie)
        self.assertFalse(leitura["disponivel"])
        self.assertIn("não foi comparado", leitura["texto"])

    def test_lacuna_marcada_sem_inventar_periodo(self):
        jan, mar = self.mensal(1, 1), self.mensal(2, 3)
        serie = ic.montar_serie_historica([jan, mar], mar)
        self.assertEqual(len(serie.pontos), 2)
        self.assertTrue(serie.pontos[1].lacuna_antes)
        self.assertIn("sem análise publicada", ic.interpretar_evolucao_faturamento(serie)["texto"])

    def test_periodo_sem_vendas_e_diferente_de_sem_informacao(self):
        jan, fev, mar = self.mensal(1, 1, fat="900"), self.mensal(2, 2, fat="0"), self.mensal(3, 3, fat="1200")
        serie = ic.montar_serie_historica([jan, fev, mar], mar)
        self.assertEqual([p.faturamento for p in serie.pontos], [D("900"), D("0"), D("1200")])
        self.assertFalse(any(p.lacuna_antes for p in serie.pontos))
        stats = ic.estatisticas_serie(serie.pontos, "faturamento")
        self.assertEqual(stats["periodos_sem_vendas"], 1)
        self.assertEqual(stats["tendencia"], "oscilante")
        self.assertEqual(stats["menor"]["rotulo"], "02/2026")

    def test_sem_base_percentual_quando_anterior_zero(self):
        var = ic.variacao(D("100"), D("0"))
        self.assertTrue(var["sem_base"])
        self.assertIsNone(var["percentual"])
        self.assertIsNone(ic.variacao(None, D("1")))

    def test_tendencia_crescente_e_decrescente(self):
        # Jan (31 dias), fev (28) e mar (31): a tendência usa a média diária.
        alta = [self.mensal(i, i, fat=str(dias * diaria)) for i, dias, diaria in ((1, 31, 100), (2, 28, 120), (3, 31, 140))]
        stats = ic.estatisticas_serie(ic.montar_serie_historica(alta, alta[-1]).pontos, "faturamento")
        self.assertEqual((stats["tendencia"], stats["por_dia"]), ("crescente", True))
        queda = [self.mensal(i, i, fat=str(dias * diaria)) for i, dias, diaria in ((1, 31, 140), (2, 28, 120), (3, 31, 100))]
        serie = ic.montar_serie_historica(queda, queda[-1])
        self.assertEqual(ic.estatisticas_serie(serie.pontos, "faturamento")["tendencia"], "decrescente")
        # Totais crescentes com média diária em queda (fevereiro forte): não é crescimento.
        enganosa = [self.mensal(i, i, fat=v) for i, v in ((1, "3100"), (2, "3360"), (3, "3410"))]
        self.assertEqual(ic.estatisticas_serie(ic.montar_serie_historica(enganosa, enganosa[-1]).pontos,
                                               "faturamento")["tendencia"], "oscilante")

    def test_janela_limitada_preserva_a_atual(self):
        mensais = [self.mensal(i + 1, (i % 12) + 1, ano=2024 + i // 12) for i in range(30)]
        serie = ic.montar_serie_historica(mensais, mensais[-1])
        self.assertEqual(len(serie.pontos), ic.LIMITE_PONTOS_SERIE)
        self.assertEqual(serie.omitidos, 6)
        self.assertTrue(serie.pontos[-1].atual)
        antiga = ic.montar_serie_historica(mensais, mensais[2])
        self.assertIn(mensais[2].id_analise, [p.id_analise for p in antiga.pontos])

    def test_compras_e_vendas_conta_periodos_sem_afirmar_estoque(self):
        jan, fev = self.mensal(1, 1, fat="1000", compras="1500"), self.mensal(2, 2, fat="1000", compras="800")
        leitura = ic.interpretar_evolucao_compras_vendas(ic.montar_serie_historica([jan, fev], fev))
        self.assertTrue(leitura["disponivel"])
        self.assertIn("Em 1 de 2 períodos comparáveis", leitura["texto"])
        self.assertIn("não representa lucro nem saldo de estoque físico", leitura["texto"])


class DistribuicaoABCTests(unittest.TestCase):
    def test_universo_completo_do_detalhamento(self):
        dist = ic.distribuicao_abc(complemento())
        self.assertTrue(dist.disponivel)
        self.assertEqual([c.percentual for c in dist.classes], [D("80.0"), D("15.0"), D("5.0")])
        self.assertEqual([c.produtos for c in dist.classes], [2, 3, 5])
        self.assertEqual(dist.classe("C").percentual_mix, D("50.0"))

    def test_legado_completo_com_menos_de_20_linhas(self):
        linhas = [ic.Produto(nome=f"P{i}", posicao=i, classe=c, faturamento=D(v))
                  for i, (c, v) in enumerate([("A", "700"), ("B", "200"), ("C", "100")], start=1)]
        dist = ic.distribuicao_abc(None, linhas)
        self.assertTrue(dist.disponivel)
        self.assertEqual(dist.fonte, "legado_completo")
        self.assertEqual([c.percentual for c in dist.classes], [D("70.0"), D("20.0"), D("10.0")])

    def test_legado_com_20_linhas_nao_calcula_participacao_so_com_o_topo(self):
        linhas = [ic.Produto(nome=f"P{i}", posicao=i, classe="A", faturamento=D("10")) for i in range(1, 21)]
        dist = ic.distribuicao_abc(None, linhas)
        self.assertFalse(dist.disponivel)
        self.assertEqual(dist.motivo, "ranking_parcial")
        cartoes = ic.cartoes_classes(dist, {"A": linhas[:3]})
        self.assertIsNone(cartoes[0]["percentual"])
        self.assertIn("não está disponível", cartoes[0]["leitura"])

    def test_sem_produtos(self):
        self.assertEqual(ic.distribuicao_abc(None, []).motivo, "sem_produtos")
        self.assertFalse(ic.distribuicao_abc(complemento(abc_total_produtos=0, abc_faturamento_total=D("0"),
                                                         abc_produtos_a=0, abc_produtos_b=0,
                                                         abc_produtos_c=0)).disponivel)

    def test_cartoes_especificos_por_classe(self):
        dist = ic.distribuicao_abc(complemento())
        destaques = {"A": [ic.Produto(nome="Café", percentual_individual=D("50"), faturamento=D("500"))],
                     "B": [ic.Produto(nome="Açúcar"), ic.Produto(nome="Leite")], "C": []}
        a, b, c = ic.cartoes_classes(dist, destaques)
        self.assertIn("80,0% do faturamento", a["leitura"])
        self.assertIn("“Açúcar” e “Leite”", b["recomendacao"])
        # Classe C: 5% do faturamento com 50% do mix -> revisão do mix.
        self.assertIn("Revise a reposição", c["recomendacao"])

    def test_classe_vazia(self):
        dist = ic.distribuicao_abc(complemento(abc_produtos_c=0, abc_produtos_b=8, abc_faturamento_c=D("0"),
                                               abc_faturamento_b=D("200")))
        cartao_c = ic.cartoes_classes(dist, {})[2]
        self.assertTrue(cartao_c["vazia"])
        self.assertIn("Nenhum produto ficou na Classe C", cartao_c["leitura"])


class MovimentacaoTests(unittest.TestCase):
    def produto(self, comprada, vendida, situacao="COMPARAVEL", **kw):
        dif = (D(str(comprada)) - D(str(vendida))) if situacao == "COMPARAVEL" else None
        return ic.Produto(nome=kw.pop("nome", "Item"), quantidade_comprada=D(str(comprada)),
                          quantidade_vendida=None if vendida is None else D(str(vendida)),
                          situacao=situacao, diferenca=dif, **kw)

    def test_faixas_de_saida_relativa(self):
        self.assertEqual(ic.interpretar_movimento(self.produto(100, 40))["nivel"], "atencao")
        self.assertIn("abaixo da metade", ic.interpretar_movimento(self.produto(100, 40))["interpretacao"])
        self.assertIn("Compras acima", ic.interpretar_movimento(self.produto(100, 80))["interpretacao"])
        self.assertIn("alinhadas", ic.interpretar_movimento(self.produto(100, 100))["interpretacao"])
        self.assertIn("Vendas acima", ic.interpretar_movimento(self.produto(100, 150))["interpretacao"])

    def test_situacoes_sem_numero_artificial(self):
        for situacao in ("SEM_VENDA_CORRESPONDENTE", "UNIDADE_DIVERGENTE", "UNIDADE_AMBIGUA", "QUANTIDADE_INVALIDA"):
            with self.subTest(situacao=situacao):
                linha = ic.linha_movimentacao(self.produto(10, None, situacao=situacao,
                                                           unidade_compra="CX", unidade_venda="UN"))
                self.assertIsNone(linha["diferenca"])
                self.assertEqual(linha["nivel"], "informativo")
        self.assertIn("CX na compra, UN na venda",
                      ic.interpretar_movimento(self.produto(1, 1, "UNIDADE_DIVERGENTE", unidade_compra="CX",
                                                            unidade_venda="UN"))["interpretacao"])

    def test_nunca_afirma_estoque_parado(self):
        for comprada, vendida in ((100, 0), (100, 30), (100, 95), (10, 50)):
            leitura = ic.interpretar_movimento(self.produto(comprada, vendida))
            texto = (leitura["interpretacao"] + " " + leitura["recomendacao"]).lower()
            self.assertNotIn("estoque parado", texto)
            self.assertNotIn("lucro", texto)

    def test_estados_da_secao(self):
        legado = ic.resumo_movimentacao(None, indicador(parado_nome="Café", parado=D("12")), [], {})
        self.assertFalse(legado["disponivel"])
        self.assertEqual(legado["legado"]["nome"], "Café")
        nf = ic.resumo_movimentacao(complemento(compras_por_produto=False), indicador(), [], {})
        self.assertEqual(nf["motivo"], "compras_sem_produto")
        mov = ic.resumo_movimentacao(complemento(unidade_compras_informada=False), indicador(),
                                     [self.produto(10, 4, nome="A"), self.produto(5, 5, nome="B")],
                                     {"COMPARAVEL": 2, "SEM_VENDA_CORRESPONDENTE": 1, "UNIDADE_DIVERGENTE": 1},
                                     periodos_divergentes=True)
        self.assertTrue(mov["disponivel"])
        self.assertEqual(mov["destaque"]["nome"], "A")
        ressalvas = " ".join(mov["ressalvas"])
        self.assertIn("não informam a unidade", ressalvas)
        self.assertIn("períodos diferentes", ressalvas)
        self.assertIn("não têm venda correspondente", ressalvas)
        self.assertIn("unidade diferente, ausente ou registrada de mais de uma forma", ressalvas)

    def test_sem_diferenca_positiva(self):
        mov = ic.resumo_movimentacao(complemento(), indicador(), [self.produto(5, 9)], {"COMPARAVEL": 1})
        self.assertIsNone(mov["destaque"])


class VariacaoProdutosTests(unittest.TestCase):
    def test_exige_variacao_e_impacto_relevantes(self):
        atuais = [ic.Produto(nome="Café", chave="a", faturamento=D("600")),
                  ic.Produto(nome="Pão", chave="b", faturamento=D("110")),
                  ic.Produto(nome="Novo", chave="c", faturamento=D("90"))]
        anteriores = {"a": D("400"), "b": D("100")}
        resultado = ic.variacoes_produtos(atuais, anteriores, False, D("1000"))
        self.assertEqual([r["produto"].nome for r in resultado], ["Café"])  # Pão +10%; Novo sem base
        self.assertEqual(resultado[0]["variacao"]["percentual"], D("50.0"))

    def test_sem_faturamento_total_nao_compara(self):
        self.assertEqual(ic.variacoes_produtos([ic.Produto(nome="X", chave="a", faturamento=D("1"))],
                                               {"a": D("2")}, True, D("0")), [])


class InsightsERecomendacoesTests(unittest.TestCase):
    def ctx(self, fat="10000", compras="9000", **kw):
        ind = indicador(fat, compras)
        return ic.ContextoPainel(analise=NS(id_analise=1), indicador=ind, **kw)

    def chaves(self, ctx):
        return [i["chave"] for i in ic.gerar_insights(ctx)]

    def test_compras_superiores_critico_e_atencao(self):
        critico = ic.gerar_insights(self.ctx(compras="12000"))[0]
        self.assertEqual((critico["chave"], critico["nivel"]), ("compras_superiores_vendas", "critico"))
        self.assertIn("20,0%", critico["o_que"])
        self.assertIn("não indica, sozinho, estoque físico parado", critico["por_que"])
        atencao = ic.gerar_insights(self.ctx(compras="10800"))[0]
        self.assertEqual(atencao["nivel"], "atencao")
        self.assertEqual(critico["rastreio"]["indicador"], "saldo_estimado_compras_vendas / faturamento_total")

    def test_vendas_superiores_e_equilibrio(self):
        self.assertEqual(self.chaves(self.ctx(compras="8000"))[0], "vendas_superiores_compras")
        self.assertEqual(self.chaves(self.ctx(compras="10200"))[0], "compras_vendas_equilibradas")

    def test_sem_indicador_ou_faturamento_nada_e_afirmado(self):
        self.assertEqual(ic.gerar_insights(ic.ContextoPainel(analise=NS(), indicador=None)), [])
        self.assertNotIn("compras_superiores_vendas", self.chaves(self.ctx(fat="0", compras="10")))
        self.assertEqual(ic.gerar_recomendacoes(ic.ContextoPainel(analise=NS(), indicador=None), []), [])

    def test_concentracao_em_um_produto(self):
        lider = ic.Produto(nome="Café", faturamento=D("4000"), percentual_individual=D("40"))
        self.assertIn("concentracao_produto", self.chaves(self.ctx(lider=lider)))
        menor = ic.Produto(nome="Café", faturamento=D("2000"), percentual_individual=D("20"))
        self.assertNotIn("concentracao_produto", self.chaves(self.ctx(lider=menor)))

    def _mov(self, linhas, **kw):
        return ic.resumo_movimentacao(complemento(), indicador(), linhas,
                                      {"COMPARAVEL": len(linhas)}, **kw)

    def test_baixa_saida_e_sem_contradicao_para_produto_classe_a(self):
        linha = ic.Produto(nome="Café", classe="A", quantidade_comprada=D("100"), quantidade_vendida=D("30"),
                           situacao="COMPARAVEL", diferenca=D("70"))
        ctx = self.ctx(movimentacao=self._mov([linha]),
                       destaques_classe={"A": [ic.Produto(nome="Café"), ic.Produto(nome="Leite")]},
                       distribuicao=ic.distribuicao_abc(complemento()))
        insights = ic.gerar_insights(ctx)
        baixa = next(i for i in insights if i["chave"] == "baixa_saida_relativa")
        self.assertIn("sem deixar faltar", baixa["o_que_fazer"])
        recs = ic.gerar_recomendacoes(ctx, insights)
        alvos = [r["alvo"] for r in recs]
        self.assertIn("Produtos com compras superiores às vendas", alvos)
        classe_a = next(r for r in recs if r["alvo"] == "Produtos estratégicos (Classe A)")
        # O mesmo produto não recebe "garantir abastecimento" e "reduzir compra": o
        # texto diz por que ele fica fora da ação da Classe A.
        self.assertIn("Os produtos de maior faturamento são “Leite”.", classe_a["situacao"])
        self.assertIn("“Café” fica fora desta ação: vendeu menos de 90% do volume comprado no período.",
                      classe_a["situacao"])

    def test_periodos_divergentes_desligam_recomendacao_por_produto(self):
        linha = ic.Produto(nome="Café", quantidade_comprada=D("100"), quantidade_vendida=D("30"),
                           situacao="COMPARAVEL", diferenca=D("70"))
        ctx = self.ctx(movimentacao=self._mov([linha], periodos_divergentes=True))
        self.assertNotIn("baixa_saida_relativa", self.chaves(ctx))

    def test_variacao_total_e_por_produto(self):
        jan = analise(1, date(2026, 1, 1), date(2026, 1, 31), fat="8000")
        fev = analise(2, date(2026, 2, 1), date(2026, 2, 28), fat="10000")
        serie = ic.montar_serie_historica([jan, fev], fev)
        queda = {"produto": ic.Produto(nome="Pão", faturamento=D("300")), "atual": D("300"), "anterior": D("600"),
                 "variacao": ic.variacao(D("300"), D("600")), "impacto": D("3.0")}
        ctx = ic.ContextoPainel(analise=fev, indicador=fev.indicador, serie=serie, variacoes_produto=[queda])
        chaves = self.chaves(ctx)
        self.assertIn("variacao_faturamento", chaves)
        self.assertIn("reducao_produto", chaves)
        recs = ic.gerar_recomendacoes(ctx, ic.gerar_insights(ctx))
        self.assertEqual(recs[0]["prioridade"], "Alta")
        self.assertIn("Pão", recs[0]["alvo"])

    def test_recomendacoes_so_com_dado_e_sem_duplicidade(self):
        # Só o indicador total: nenhuma recomendação de classe ou produto é inventada.
        ctx = self.ctx(compras="12000")
        recs = ic.gerar_recomendacoes(ctx, ic.gerar_insights(ctx))
        self.assertEqual([r["alvo"] for r in recs], ["Compras do próximo ciclo"])
        self.assertEqual(recs[0]["prioridade"], "Alta")
        equilibrado = self.ctx(compras="10000")
        self.assertEqual(ic.gerar_recomendacoes(equilibrado, ic.gerar_insights(equilibrado)), [])

    def test_recomendacoes_limitadas_e_priorizadas(self):
        linhas = [ic.Produto(nome=f"Item {i}", quantidade_comprada=D("100"), quantidade_vendida=D("20"),
                             situacao="COMPARAVEL", diferenca=D("80")) for i in range(5)]
        dist = ic.distribuicao_abc(complemento())
        ctx = self.ctx(compras="12000", movimentacao=self._mov(linhas), distribuicao=dist,
                       destaques_classe={"A": [ic.Produto(nome="Café")], "B": [ic.Produto(nome="Leite")], "C": []},
                       lider=ic.Produto(nome="Café", faturamento=D("5000"), percentual_individual=D("50")))
        recs = ic.gerar_recomendacoes(ctx, ic.gerar_insights(ctx))
        self.assertLessEqual(len(recs), 5)
        prioridades = [ic.PRIORIDADE_ORDEM[r["prioridade"]] for r in recs]
        self.assertEqual(prioridades, sorted(prioridades))
        self.assertEqual(len({r["alvo"] for r in recs}), len(recs))
        for rec in recs:
            self.assertTrue(rec["rastreio"])
            self.assertTrue(all(rec[campo] for campo in ("situacao", "justificativa", "acao", "objetivo")))

    def test_textos_sem_lucro_prejuizo_ou_promessa(self):
        dist = ic.distribuicao_abc(complemento())
        ctx = self.ctx(compras="12000", distribuicao=dist,
                       destaques_classe={"A": [ic.Produto(nome="Café")], "B": [ic.Produto(nome="Leite")]},
                       lider=ic.Produto(nome="Café", faturamento=D("5000"), percentual_individual=D("50")))
        insights = ic.gerar_insights(ctx)
        recs = ic.gerar_recomendacoes(ctx, insights)
        textos = " ".join(str(v) for item in insights + recs for k, v in item.items() if k != "rastreio").lower()
        for proibido in ("lucro", "prejuízo", "prejuizo", "margem", "rentab", "garantimos", "vai aumentar"):
            self.assertNotIn(proibido, textos)


class ResumoExecutivoTests(unittest.TestCase):
    def test_destaques_dinamicos_e_coincidencia_de_lider(self):
        ind = indicador("10000", "12000")
        lider = ic.Produto(nome="Café", faturamento=D("4000"), percentual_individual=D("40"))
        ctx = ic.ContextoPainel(analise=NS(), indicador=ind, lider=lider,
                                mais_vendido=ic.Produto(nome="Café", quantidade_vendida=D("80")))
        insights = ic.gerar_insights(ctx)
        frases = ic.gerar_resumo_executivo(ctx, insights, ic.gerar_recomendacoes(ctx, insights), "01/03 a 31/03")
        texto = " ".join(frases)
        self.assertIn("R$ 10.000,00", texto)
        self.assertIn("também liderou em quantidade vendida", texto)
        self.assertIn("As compras superaram as vendas em R$ 2.000,00", texto)

    def test_sem_classe_a_quando_distribuicao_indisponivel(self):
        ctx = ic.ContextoPainel(analise=NS(), indicador=indicador(), distribuicao=ic.distribuicao_abc(None, []))
        texto = " ".join(ic.gerar_resumo_executivo(ctx, [], [], "x"))
        self.assertNotIn("Classe A", texto)

    def test_sem_indicador(self):
        self.assertEqual(ic.gerar_resumo_executivo(ic.ContextoPainel(analise=NS(), indicador=None), [], [], "x"), [])


def _mensal(id_, mes, ano=2026, **kw):
    inicio = date(ano, mes, 1)
    fim = (date(ano + (mes == 12), mes % 12 + 1, 1) - date.resolution)
    return analise(id_, inicio, fim, conclusao=datetime(ano, mes, 28) if mes < 12 else datetime(ano, 12, 30), **kw)


class RevisaoDasRegrasTests(unittest.TestCase):
    """Cenários levantados na revisão independente das regras (dados fictícios)."""

    def test_sobreposicao_escolhe_por_prioridade_sem_derrubar_periodo_sem_conflito(self):
        janeiro = analise(1, date(2026, 1, 1), date(2026, 1, 31), conclusao=datetime(2026, 2, 5))
        cruzada = analise(2, date(2026, 1, 16), date(2026, 2, 14), conclusao=datetime(2026, 2, 20))
        fevereiro = analise(3, date(2026, 2, 1), date(2026, 2, 28), conclusao=datetime(2026, 3, 5))
        serie = ic.montar_serie_historica([janeiro, cruzada, fevereiro], fevereiro)
        # A atual vence a cruzada; janeiro não sobrepõe fevereiro e permanece.
        self.assertEqual([p.id_analise for p in serie.pontos], [1, 3])
        self.assertEqual(serie.anterior.id_analise, 1)
        self.assertEqual(serie.excluidas["sobreposta"], 1)

    def test_janela_mantem_o_periodo_anterior_e_nomeia_o_lado_omitido(self):
        mensais = [_mensal(i + 1, (i % 12) + 1, ano=2024 + i // 12) for i in range(30)]
        serie = ic.montar_serie_historica(mensais, mensais[6])
        self.assertEqual(serie.anterior.id_analise, mensais[5].id_analise)
        serie = ic.montar_serie_historica(mensais, mensais[5])
        self.assertEqual((serie.omitidos_antigos, serie.omitidos_recentes), (0, 6))
        texto = ic.interpretar_evolucao_faturamento(serie)["texto"]
        self.assertIn("6 período(s) mais recente(s)", texto)
        self.assertNotIn("mais antigo(s)", texto)

    def test_duracoes_diferentes_comparam_a_media_diaria(self):
        # R$ 1.000 por dia nos dois meses: o calendário não vira alta de vendas.
        fev = analise(1, date(2026, 2, 1), date(2026, 2, 28), fat="28000")
        mar = analise(2, date(2026, 3, 1), date(2026, 3, 31), fat="31000")
        serie = ic.montar_serie_historica([fev, mar], mar)
        ctx = ic.ContextoPainel(analise=mar, indicador=mar.indicador, serie=serie)
        comp = ctx.comparacao_faturamento
        self.assertEqual(comp["bruta"]["percentual"], D("10.7"))
        self.assertEqual(comp["relevante"]["percentual"], D("0.0"))
        self.assertNotIn("variacao_faturamento", [i["chave"] for i in ic.gerar_insights(ctx)])
        resumo = " ".join(ic.gerar_resumo_executivo(ctx, [], [], "01/03/2026 a 31/03/2026"))
        self.assertIn("alta de 10,7% em relação a 02/2026", resumo)
        self.assertIn("Como os períodos têm 31 e 28 dias, a média diária ficou estável.", resumo)
        self.assertIn("a média diária ficou estável", ic.interpretar_evolucao_faturamento(serie)["texto"])

    def test_quinzenas_de_13_e_15_dias_sem_queda_artificial(self):
        q1 = analise(1, date(2026, 2, 1), date(2026, 2, 15), tipo="QUINZENAL", quinzena=1, fat="15000")
        q2 = analise(2, date(2026, 2, 16), date(2026, 2, 28), tipo="QUINZENAL", quinzena=2, fat="13000")
        ctx = ic.ContextoPainel(analise=q2, indicador=q2.indicador, serie=ic.montar_serie_historica([q1, q2], q2))
        self.assertEqual(ctx.variacao_faturamento["percentual"], D("-13.3"))
        self.assertNotIn("variacao_faturamento", [i["chave"] for i in ic.gerar_insights(ctx)])
        # Queda real da média diária (R$ 1.000 -> R$ 800 por dia) continua apontada.
        q2_queda = analise(2, date(2026, 2, 16), date(2026, 2, 28), tipo="QUINZENAL", quinzena=2, fat="10400")
        ctx = ic.ContextoPainel(analise=q2_queda, indicador=q2_queda.indicador,
                                serie=ic.montar_serie_historica([q1, q2_queda], q2_queda))
        card = next(i for i in ic.gerar_insights(ctx) if i["chave"] == "variacao_faturamento")
        self.assertEqual(card["titulo"], "Faturamento em queda")
        self.assertIn("-30,7%", card["o_que"])
        self.assertIn("a média diária caiu 20,0%", card["o_que"])

    def test_variacao_por_produto_usa_a_media_diaria(self):
        estavel = [ic.Produto(nome="Café", chave="a", faturamento=D("3100"))]
        self.assertEqual(ic.variacoes_produtos(estavel, {"a": D("2800")}, True, D("10000"),
                                               dias_atual=31, dias_anterior=28), [])
        alta = [ic.Produto(nome="Café", chave="a", faturamento=D("3720"))]
        resultado = ic.variacoes_produtos(alta, {"a": D("2800")}, True, D("10000"), dias_atual=31, dias_anterior=28)
        self.assertEqual(resultado[0]["variacao"]["percentual"], D("20.0"))
        self.assertTrue(resultado[0]["por_dia"])
        self.assertEqual(resultado[0]["anterior"], D("2800.00"))

    def _mov(self, linhas, acima=None, **campos):
        contagem = {"COMPARAVEL": len(linhas)}
        return ic.resumo_movimentacao(complemento(**campos), indicador(), linhas, contagem, acima=acima)

    def _linha(self, nome, comprada, vendida, classe=None, unidade=None, chave=""):
        return ic.Produto(nome=nome, chave=chave or nome, classe=classe, quantidade_comprada=D(comprada),
                          quantidade_vendida=D(vendida), situacao="COMPARAVEL",
                          diferenca=D(comprada) - D(vendida), unidade_compra=unidade, unidade_venda=unidade)

    def test_classe_a_conferida_pela_propria_linha_de_movimentacao(self):
        refrigerantes = [self._linha(f"Refrigerante {i}", "1000", "700") for i in range(10)]
        whisky = self._linha("Whisky 12 anos", "120", "40", classe="A")
        vinho = self._linha("Vinho tinto", "50", "50", classe="A")
        ctx = ic.ContextoPainel(analise=NS(id_analise=1), indicador=indicador("10000", "9000"),
                                movimentacao=self._mov(refrigerantes, acima=refrigerantes),
                                destaques_classe={"A": [whisky, vinho]}, distribuicao=ic.distribuicao_abc(complemento()))
        recs = ic.gerar_recomendacoes(ctx, ic.gerar_insights(ctx))
        classe_a = next(r for r in recs if r["alvo"] == "Produtos estratégicos (Classe A)")
        self.assertIn("Os produtos de maior faturamento são “Vinho tinto”.", classe_a["situacao"])
        self.assertIn("“Whisky 12 anos” fica fora desta ação", classe_a["situacao"])

    def test_crescimento_com_compras_acima_nao_recebe_acoes_opostas(self):
        jan = analise(1, date(2026, 1, 1), date(2026, 1, 31), fat="9000")
        fev = analise(2, date(2026, 2, 1), date(2026, 2, 28), fat="10000")
        cerveja = self._linha("Cerveja lata", "1000", "450", chave="c")
        cerveja = ic.Produto(**{**cerveja.__dict__, "faturamento": D("2000")})
        crescimento = {"produto": cerveja, "atual": D("2000"), "anterior": D("1400"),
                       "variacao": ic.variacao(D("2000"), D("1400")), "impacto": D("6.0")}
        ctx = ic.ContextoPainel(analise=fev, indicador=fev.indicador, serie=ic.montar_serie_historica([jan, fev], fev),
                                movimentacao=self._mov([cerveja]), variacoes_produto=[crescimento])
        insights = ic.gerar_insights(ctx)
        card = next(i for i in insights if i["chave"] == "crescimento_produto")
        self.assertIn("dimensionar a próxima compra pelas vendas observadas", card["o_que_fazer"])
        textos = " ".join(i["o_que_fazer"] for i in insights)
        self.assertNotIn("Garantir a reposição de “Cerveja lata”", textos)
        recs = ic.gerar_recomendacoes(ctx, insights)
        self.assertNotIn("“Cerveja lata”", [r["alvo"] for r in recs])

    def test_concentracao_com_compras_acima_nao_pede_garantir_abastecimento(self):
        lider = self._linha("Café", "100", "30", classe="A")
        lider = ic.Produto(**{**lider.__dict__, "faturamento": D("4000"), "percentual_individual": D("40")})
        ctx = ic.ContextoPainel(analise=NS(id_analise=1), indicador=indicador(), lider=lider,
                                movimentacao=self._mov([lider]))
        card = next(i for i in ic.gerar_insights(ctx) if i["chave"] == "concentracao_produto")
        self.assertNotIn("Garantir o abastecimento", card["o_que_fazer"])
        self.assertIn("na medida das vendas observadas", card["o_que_fazer"])

    def test_registro_parcial_da_movimentacao_e_declarado(self):
        mov = self._mov([self._linha("A", "10", "4")], movimentacao_total=6000, movimentacao_registrada=3500)
        self.assertTrue(mov["parcial"])
        self.assertFalse(mov["contagem_completa"])
        self.assertIn("registrada para 3.500 de 6.000 produtos comprados", " ".join(mov["ressalvas"]))
        self.assertIn("as contagens, os filtros e a consulta abaixo consideram apenas os registrados",
                      " ".join(mov["ressalvas"]))
        self.assertFalse(self._mov([self._linha("A", "10", "4")])["parcial"])

    def test_totais_por_situacao_de_todos_os_comprados_prevalecem(self):
        # 6.000 comprados, 3.500 registrados (teto): os totais gravados pelo ETL valem
        # para as contagens e ressalvas; as linhas registradas, só para a consulta.
        mov = self._mov([self._linha("A", "10", "4")], movimentacao_total=6000, movimentacao_registrada=3500,
                        movimentacao_comparaveis=5200, movimentacao_sem_venda=650, movimentacao_unidade_divergente=90,
                        movimentacao_unidade_ambigua=40, movimentacao_quantidade_invalida=20)
        self.assertTrue(mov["contagem_completa"])
        self.assertEqual(mov["total_comparaveis"], 5200)
        self.assertEqual(mov["contagem"], {"COMPARAVEL": 5200, "SEM_VENDA_CORRESPONDENTE": 650,
                                           "UNIDADE_DIVERGENTE": 90, "UNIDADE_AMBIGUA": 40, "QUANTIDADE_INVALIDA": 20})
        ressalvas = " ".join(mov["ressalvas"])
        self.assertIn("os totais por situação consideram todos os produtos", ressalvas)
        self.assertIn("650 produto(s) comprado(s) não têm venda correspondente", ressalvas)
        self.assertIn("130 produto(s) com unidade diferente, ausente ou registrada de mais de uma forma", ressalvas)
        self.assertIn("20 produto(s) com quantidade inválida", ressalvas)

    def test_cinco_recomendacoes_no_maximo_mantendo_as_de_maior_prioridade(self):
        jan = analise(1, date(2026, 1, 1), date(2026, 1, 31), fat="9000")
        fev = analise(2, date(2026, 2, 1), date(2026, 2, 28), fat="10000")
        alta_p = ic.Produto(nome="Leite fictício", chave="l", faturamento=D("2000"))
        queda_p = ic.Produto(nome="Pão fictício", chave="p", faturamento=D("300"))
        variacoes = [
            {"produto": alta_p, "atual": D("2000"), "anterior": D("1200"), "variacao": ic.variacao(D("2000"), D("1200")),
             "impacto": D("8.0")},
            {"produto": queda_p, "atual": D("300"), "anterior": D("900"), "variacao": ic.variacao(D("300"), D("900")),
             "impacto": D("6.0")},
        ]
        comprado_acima = self._linha("Arroz fictício", "100", "20")
        ctx = ic.ContextoPainel(
            analise=fev, indicador=fev.indicador, serie=ic.montar_serie_historica([jan, fev], fev),
            movimentacao=self._mov([comprado_acima]), variacoes_produto=variacoes,
            distribuicao=ic.distribuicao_abc(complemento(abc_produtos_c=8, abc_produtos_a=1, abc_produtos_b=1,
                                                         abc_faturamento_c=D("50"))),
            destaques_classe={"A": [ic.Produto(nome="Café fictício")], "B": [ic.Produto(nome="Açúcar fictício")]})
        insights = ic.gerar_insights(ctx)
        self.assertIn("classe_c_participacao_reduzida", [i["chave"] for i in insights])
        recs = ic.gerar_recomendacoes(ctx, insights)
        alvos = [r["alvo"] for r in recs]
        # Seis candidatas: movimentação, queda, Classe A, Classe B, crescimento e Classe C.
        self.assertEqual(len(recs), 5)
        self.assertNotIn("Produtos complementares (Classe C)", alvos)  # a de prioridade Baixa sai
        self.assertIn("“Pão fictício”", alvos)
        self.assertEqual([r["prioridade"] for r in recs], sorted((r["prioridade"] for r in recs),
                                                                 key=ic.PRIORIDADE_ORDEM.get))

    def test_unidade_informada_nos_textos_e_nenhuma_presumida(self):
        picanha = self._linha("Picanha", "120.5", "40.25", unidade="KG")
        ctx = ic.ContextoPainel(analise=NS(id_analise=1), indicador=indicador(), movimentacao=self._mov([picanha]))
        insights = ic.gerar_insights(ctx)
        baixa = next(i for i in insights if i["chave"] == "baixa_saida_relativa")
        self.assertIn("quantidade comprada 120,5 KG e vendida 40,25 KG", baixa["o_que"])
        rec = ic.gerar_recomendacoes(ctx, insights)[0]
        self.assertIn("“Picanha” (+80,25 KG)", rec["situacao"])
        sem_unidade = self._linha("Arroz", "100", "30")
        ctx = ic.ContextoPainel(analise=NS(id_analise=1), indicador=indicador(), movimentacao=self._mov([sem_unidade]))
        rec = ic.gerar_recomendacoes(ctx, ic.gerar_insights(ctx))[0]
        self.assertIn("“Arroz” (+70)", rec["situacao"])
        self.assertNotIn("un.", rec["situacao"])
        self.assertEqual(ic.fmt_quantidade_unidade(D("3"), "*"), "3")

    def test_nivel_de_pressao_usa_os_limiares_dos_semaforos(self):
        self.assertEqual(ic.nivel_pressao(D("0.01")), "equilibrio")
        self.assertEqual(ic.nivel_pressao(D("-0.05")), "equilibrio")
        self.assertEqual(ic.nivel_pressao(D("0.06")), "pressao")
        self.assertEqual(ic.nivel_pressao(D("-0.06")), "giro")
        self.assertEqual(ic.nivel_pressao(None, D("10")), "pressao")
        self.assertEqual(ic.nivel_pressao(None, D("0")), "equilibrio")
        # Diferença desconhecida não é equilíbrio.
        self.assertEqual(ic.nivel_pressao(None, None), "indisponivel")

    def test_compras_e_vendas_explica_periodo_atual_atipico(self):
        fev = _mensal(1, 2)
        trimestre = analise(2, date(2026, 3, 1), date(2026, 3, 31), base=(date(2026, 1, 1), date(2026, 3, 31)))
        texto = ic.interpretar_evolucao_compras_vendas(ic.montar_serie_historica([fev, trimestre], trimestre))["texto"]
        self.assertIn("não foi comparado", texto)
        self.assertNotIn("a partir da segunda análise", texto)


class RevisaoDoDeltaTests(unittest.TestCase):
    """Casos da revisão das correções (dados fictícios)."""

    def _linha(self, nome, comprada, vendida, un_compra=None, un_venda=None, classe=None):
        return ic.Produto(nome=nome, chave=nome, classe=classe, quantidade_comprada=D(comprada),
                          quantidade_vendida=D(vendida), situacao="COMPARAVEL", diferenca=D(comprada) - D(vendida),
                          unidade_compra=un_compra, unidade_venda=un_venda)

    def test_unidade_de_um_relatorio_nao_rotula_a_quantidade_do_outro(self):
        # Vendas com coluna de unidade (KG); compras sem: a compra fica sem unidade e a
        # diferença também (só leva unidade comum aos dois relatórios).
        queijo = self._linha("Queijo", "100", "20", un_compra=None, un_venda="KG")
        linha = ic.linha_movimentacao(queijo)
        self.assertEqual((linha["unidade_compra"], linha["unidade_venda"], linha["unidade"]), (None, "KG", None))
        ctx = ic.ContextoPainel(analise=NS(id_analise=1), indicador=indicador(),
                                movimentacao=ic.resumo_movimentacao(complemento(unidade_compras_informada=False),
                                                                    indicador(), [queijo], {"COMPARAVEL": 1}))
        insights = ic.gerar_insights(ctx)
        baixa = next(i for i in insights if i["chave"] == "baixa_saida_relativa")
        self.assertIn("quantidade comprada 100 e vendida 20 KG", baixa["o_que"])
        rec = ic.gerar_recomendacoes(ctx, insights)[0]
        self.assertIn("“Queijo” (+80)", rec["situacao"])
        self.assertNotIn("+80 KG", rec["situacao"])
        igual = ic.linha_movimentacao(self._linha("Arroz", "10", "4", un_compra="KG", un_venda="KG"))
        self.assertEqual(igual["unidade"], "KG")

    def test_periodos_divergentes_deixam_as_acoes_por_produto_neutras(self):
        jan = analise(1, date(2026, 1, 1), date(2026, 1, 31), fat="9000")
        fev = analise(2, date(2026, 2, 1), date(2026, 2, 28), fat="10000")
        cerveja = self._linha("Cerveja", "1000", "300")
        cerveja = ic.Produto(**{**cerveja.__dict__, "faturamento": D("3500"), "percentual_individual": D("35")})
        crescimento = {"produto": cerveja, "atual": D("2000"), "anterior": D("1400"),
                       "variacao": ic.variacao(D("2000"), D("1400")), "impacto": D("6.0")}
        mov = ic.resumo_movimentacao(complemento(), indicador(), [cerveja], {"COMPARAVEL": 1}, periodos_divergentes=True)
        ctx = ic.ContextoPainel(analise=fev, indicador=fev.indicador, serie=ic.montar_serie_historica([jan, fev], fev),
                                lider=cerveja, movimentacao=mov, variacoes_produto=[crescimento])
        insights = ic.gerar_insights(ctx)
        textos = " ".join(i["o_que_fazer"] for i in insights) + " ".join(
            r["acao"] for r in ic.gerar_recomendacoes(ctx, insights))
        self.assertNotIn("Garantir a reposição de “Cerveja”", textos)
        self.assertNotIn("Garantir o abastecimento de “Cerveja”", textos)
        self.assertIn("Avaliar a reposição de “Cerveja” pelas vendas observadas", textos)

    def test_tendencia_com_duracoes_diferentes_usa_media_diaria(self):
        # Quinzenas de 15, 13 e 16 dias a R$ 1.000 por dia: totais sobem, ritmo estável.
        q = [analise(1, date(2026, 2, 1), date(2026, 2, 15), tipo="QUINZENAL", quinzena=1, fat="15000"),
             analise(2, date(2026, 2, 16), date(2026, 2, 28), tipo="QUINZENAL", quinzena=2, fat="13000"),
             analise(3, date(2026, 3, 16), date(2026, 3, 31), tipo="QUINZENAL", quinzena=2, fat="16000")]
        serie = ic.montar_serie_historica(q, q[-1])
        stats = ic.estatisticas_serie(serie.pontos, "faturamento")
        self.assertEqual((stats["tendencia"], stats["variacao_acumulada"]["percentual"]), ("estavel", D("0.0")))
        texto = ic.interpretar_evolucao_faturamento(serie)["texto"]
        self.assertIn("Pela média diária (os períodos têm durações diferentes), o faturamento ficou estável", texto)
        self.assertNotIn("cresceu ou se manteve", texto)

    def test_selo_e_insight_seguem_o_percentual_exibido(self):
        # 5,04% é exibido como 5,0%: dentro da faixa de equilíbrio, como diz a nota do cartão.
        ctx = ic.ContextoPainel(analise=NS(id_analise=1), indicador=indicador("10000", "10504"))
        self.assertEqual(ctx.razao_pressao, D("0.05"))
        self.assertEqual(ic.nivel_pressao(ctx.razao_pressao, ctx.diferenca), "equilibrio")
        self.assertEqual(ic.gerar_insights(ctx)[0]["chave"], "compras_vendas_equilibradas")
        ctx = ic.ContextoPainel(analise=NS(id_analise=1), indicador=indicador("10000", "10505"))
        self.assertEqual(ic.nivel_pressao(ctx.razao_pressao, ctx.diferenca), "pressao")  # exibido 5,1%


if __name__ == "__main__":
    unittest.main()
