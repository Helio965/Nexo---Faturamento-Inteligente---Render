"""Visão Geral do cliente (inteligência comercial): rota, endpoint de consulta e segurança.

SQLite com as migrações reais (ContratosCase). Empresas, produtos e valores são fictícios.
Cobre: estados vazios, ordem vertical das seções, contrato do JSON do painel, só
devolutivas publicadas, análises legadas (top-20) x detalhamento completo, consulta
paginada (filtros, busca, limites), isolamento entre empresas, cobertura contratual,
cabeçalhos, GET sem efeito colateral e escape de nomes vindos da planilha.
"""

from datetime import date, datetime
from decimal import Decimal
import json
import re
from unittest.mock import patch

from sqlalchemy import event, func, insert, select, text as sa_text

from tests.contratos_support import ContratosCase, TEXTO_PRIVADO

SECOES = ("indicadores", "resumo-executivo", "insights", "curva-abc", "movimentacao", "compras-vendas",
          "evolucao-faturamento", "evolucao-compras-vendas", "recomendacoes", "historico-devolutiva")


def _dados(corpo):
    achado = re.search(r"const dashboardData = (.+?);\n", corpo)
    return None if achado is None else json.loads(achado.group(1))


class _PainelCase(ContratosCase):
    def entrar(self):
        self.login()
        return self.client

    def publicar_com(self, id_analise, inicio, fim, fat, compras, concluida_em, produtos=(), tipo="MENSAL",
                     quinzena=None, base=None, mais_vendido=None):
        from models import Analise, ProdutoCurvaABC
        analise = self.publicar(id_analise, inicio, fim, base=base, texto="Resumo publicado fictício")
        analise.tipo_analise, analise.quinzena_referencia = tipo, quinzena
        ind = analise.indicador
        ind.faturamento_total, ind.total_comprado = Decimal(fat), Decimal(compras)
        ind.saldo_estimado_compras_vendas = Decimal(compras) - Decimal(fat)
        if mais_vendido:
            ind.produto_mais_vendido_nome, ind.produto_mais_vendido_quantidade = mais_vendido
        total = sum(Decimal(v) for _, v, _ in produtos) or Decimal(1)
        acumulado = Decimal(0)
        linhas = []
        for posicao, (nome, valor, classe) in enumerate(produtos, start=1):
            individual = Decimal(valor) / total * 100
            acumulado += individual
            linhas.append(ProdutoCurvaABC(posicao_ranking=posicao, produto_nome=nome, faturamento=Decimal(valor),
                                          quantidade=Decimal(10), percentual_individual=round(individual, 2),
                                          percentual_acumulado=round(min(acumulado, Decimal(100)), 2), classe_abc=classe))
        analise.curva_abc = linhas[:20]
        analise.data_conclusao = concluida_em
        self.db.session.commit()
        return self.db.session.get(Analise, analise.id_analise)

    def detalhar(self, analise, produtos, movimentos=(), compras_por_produto=True, limitado=None):
        """Grava o detalhamento como o ETL gravaria: produtos = [(nome, faturamento, classe)],
        movimentos = [(nome, comprada, vendida, situacao)]."""
        from etl_processor import _normalizar_produto, chave_produto
        from models import IndicadorComplementarAnalise, ProdutoDesempenhoAnalise
        total = sum(Decimal(v) for _, v, _ in produtos)
        contagem = {c: sum(1 for _, _, k in produtos if k == c) for c in "ABC"}
        soma = {c: sum((Decimal(v) for _, v, k in produtos if k == c), Decimal(0)) for c in "ABC"}
        registrados = limitado or len(produtos)
        linhas, acumulado = {}, Decimal(0)
        for posicao, (nome, valor, classe) in enumerate(produtos[:registrados], start=1):
            individual = Decimal(valor) / total * 100
            acumulado += individual
            linhas[nome] = dict(produto_chave=chave_produto(_normalizar_produto(nome)), produto_nome=nome,
                                posicao_ranking=posicao, classe_abc=classe, faturamento=Decimal(valor),
                                quantidade_vendida=Decimal(10), percentual_individual=round(individual, 2),
                                percentual_acumulado=round(min(acumulado, Decimal(100)), 2))
        for ordem, (nome, comprada, vendida, situacao) in enumerate(movimentos, start=1):
            linha = linhas.setdefault(nome, dict(produto_chave=chave_produto(_normalizar_produto(nome)),
                                                 produto_nome=nome))
            linha.update(quantidade_comprada=Decimal(comprada), posicao_movimentacao=ordem,
                         quantidade_vendida=None if vendida is None else Decimal(vendida),
                         situacao_movimentacao=situacao,
                         diferenca_quantidade=(Decimal(comprada) - Decimal(vendida)) if situacao == "COMPARAVEL" else None)
        self.db.session.add(IndicadorComplementarAnalise(
            id_analise=analise.id_analise, versao_metodologia=1,
            versao_processamento=analise.indicador.versao_processamento, abc_total_produtos=len(produtos),
            abc_faturamento_total=total, abc_produtos_a=contagem["A"], abc_produtos_b=contagem["B"],
            abc_produtos_c=contagem["C"], abc_faturamento_a=soma["A"], abc_faturamento_b=soma["B"],
            abc_faturamento_c=soma["C"], produtos_vendas=len(produtos),
            produtos_compras=len(movimentos) if compras_por_produto else None,
            compras_por_produto=compras_por_produto, unidade_vendas_informada=True, unidade_compras_informada=True,
            produtos_registrados=len(linhas), ranking_registrado=registrados, movimentacao_total=len(movimentos),
            movimentacao_registrada=len(movimentos), registro_limitado=registrados < len(produtos)))
        for linha in linhas.values():
            self.db.session.add(ProdutoDesempenhoAnalise(id_analise=analise.id_analise, **linha))
        self.db.session.commit()

    def catalogo(self, n):
        produtos = []
        for i in range(n):
            classe = "A" if i < n * 0.2 else ("B" if i < n * 0.5 else "C")
            produtos.append((f"Produto fictício {i + 1:03d}", str(1000 - i * (900 // max(n, 1))), classe))
        return produtos


class EstadosETextoTests(_PainelCase):
    def test_sem_analise_publicada(self):
        corpo = self.entrar().get("/cliente/dashboard").get_data(as_text=True)
        self.assertIn("Sua primeira análise está em preparação.", corpo)
        self.assertIsNone(_dados(corpo))
        self.assertNotIn('id="indicadores"', corpo)

    def test_secoes_em_ordem_vertical_e_contrato_do_json(self):
        jan = self.publicar_com(self.analise_id, date(2026, 1, 1), date(2026, 1, 31), "18000", "15000",
                                datetime(2026, 2, 5, 12), produtos=[("Café fictício", "12000", "A"),
                                                                    ("Leite fictício", "6000", "B")])
        fev = self.publicar_com(self.nova_analise(date(2026, 2, 1), date(2026, 2, 28)).id_analise,
                                date(2026, 2, 1), date(2026, 2, 28), "20000", "24000", datetime(2026, 3, 1, 12),
                                produtos=[("Café fictício", "15000", "A"), ("Leite fictício", "5000", "B")])
        resposta = self.entrar().get("/cliente/dashboard")
        self.assertEqual(resposta.status_code, 200)
        corpo = resposta.get_data(as_text=True)
        posicoes = [corpo.index(f'id="{secao}"') for secao in SECOES]
        self.assertEqual(posicoes, sorted(posicoes))
        dados = _dados(corpo)
        self.assertEqual(dados["comparativo"]["values"], [24000.0, 20000.0])
        self.assertEqual(dados["pressao_estoque"], 4000.0)
        self.assertEqual(dados["curva_abc"]["labels"], ["Café fictício", "Leite fictício"])
        self.assertEqual(dados["historico"]["labels"], ["01/2026", "02/2026"])
        self.assertEqual(dados["historico"]["vendas"], [18000.0, 20000.0])
        self.assertEqual(dados["historico"]["compras"], [15000.0, 24000.0])
        # IDs dos gráficos usados pelos testes de navegador continuam presentes.
        for alvo in ('id="chartCliente"', 'id="chartAbcCliente"', 'id="chartEvolucaoFaturamento"',
                     'id="chartHistoricoCliente"'):
            self.assertIn(alvo, corpo)
        texto = re.sub(r"<[^>]+>", " ", corpo)
        self.assertIn("+11,1%", texto)  # 18.000 -> 20.000
        self.assertIn("Compras acima das vendas", texto)
        self.assertIn("Relatório estratégico", corpo)
        self.assertEqual(corpo.count("Relatório Estratégico"), 0)
        self.assertIn(f'/cliente/analise/{jan.id_analise}"', corpo)
        self.assertIn(f"#{fev.id_analise}", corpo)

    def test_concluida_sem_publicacao_nunca_expoe_rascunho(self):
        from models import Analise
        self.publicar_com(self.analise_id, date(2026, 1, 1), date(2026, 1, 31), "18000", "15000",
                          datetime(2026, 2, 5, 12), produtos=[("Café fictício", "18000", "A")])
        analise = self.db.session.get(Analise, self.analise_id)
        analise.relatorio.publicado = False
        analise.relatorio.conclusao_estrategica = TEXTO_PRIVADO
        self.db.session.commit()
        client = self.entrar()
        corpo = client.get("/cliente/dashboard").get_data(as_text=True)
        self.assertNotIn(TEXTO_PRIVADO, corpo)
        self.assertNotIn("18.000,00", corpo)
        self.assertIn("Sua primeira análise está em preparação.", corpo)
        self.assertEqual(client.get(f"/cliente/analise/{self.analise_id}/produtos").status_code, 404)

    def test_nomes_da_planilha_sao_escapados(self):
        nome = "<script>alert(1)</script> Café"
        self.publicar_com(self.analise_id, date(2026, 1, 1), date(2026, 1, 31), "100", "50",
                          datetime(2026, 2, 5, 12), produtos=[(nome, "100", "A")], mais_vendido=(nome, Decimal(3)))
        client = self.entrar()
        corpo = client.get("/cliente/dashboard").get_data(as_text=True)
        self.assertNotIn("<script>alert(1)", corpo)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt; Café", corpo)
        resposta = client.get(f"/cliente/analise/{self.analise_id}/produtos?visao=ranking")
        self.assertEqual(resposta.json["itens"][0]["nome"], nome)  # JSON: texto puro, montado com textContent

    def test_lider_e_mais_vendido_coincidentes(self):
        self.publicar_com(self.analise_id, date(2026, 1, 1), date(2026, 1, 31), "1000", "900",
                          datetime(2026, 2, 5, 12), produtos=[("Café fictício", "700", "A"), ("Pão fictício", "300", "B")],
                          mais_vendido=("Café fictício", Decimal(50)))
        corpo = self.entrar().get("/cliente/dashboard").get_data(as_text=True)
        self.assertIn("Também é o produto mais vendido em quantidade.", corpo)
        self.assertIn("Lidera os dois rankings", corpo)


class RevisaoPainelTests(_PainelCase):
    """Cenários da revisão independente, de ponta a ponta na rota (dados fictícios)."""

    def test_compras_acima_alem_das_primeiras_linhas_e_classe_a_conferida(self):
        produtos = self.catalogo(30)
        analise = self.publicar_com(self.analise_id, date(2026, 1, 1), date(2026, 1, 31), "50000", "50500",
                                    datetime(2026, 2, 5, 12), produtos=produtos)
        # As dez maiores diferenças têm saída de 95% (alinhadas); o líder da Classe A,
        # na 11ª linha da movimentação, comprou 40 e vendeu 10.
        movimentos = [(f"Produto fictício {i:03d}", "1000", "950", "COMPARAVEL") for i in range(11, 21)]
        movimentos.append(("Produto fictício 001", "40", "10", "COMPARAVEL"))
        self.detalhar(analise, produtos, movimentos=movimentos)
        corpo = self.entrar().get("/cliente/dashboard").get_data(as_text=True)
        texto = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", corpo))
        self.assertIn("Produtos com compras superiores às vendas", texto)
        self.assertIn("“Produto fictício 001” (+30)", texto)
        # A recomendação da Classe A diz quem fica fora e por quê (mesmo critério de 90%).
        self.assertIn("Os produtos de maior faturamento são “Produto fictício 002” e “Produto fictício 003”. "
                      "“Produto fictício 001” fica fora desta ação: vendeu menos de 90% do volume comprado", texto)
        # Compras 1% acima do faturamento: equilíbrio pelos limiares de ±5%, como os insights.
        self.assertIn('<span class="painel-sinal is-equilibrio">Equilíbrio</span>', corpo)
        self.assertIn("Compras e vendas equilibradas", texto)
        self.assertIn("dentro da faixa de equilíbrio usada pelo NEXO", texto)

    def test_registro_parcial_da_movimentacao_declarado_na_secao(self):
        produtos = self.catalogo(12)
        analise = self.publicar_com(self.analise_id, date(2026, 1, 1), date(2026, 1, 31), "10000", "9000",
                                    datetime(2026, 2, 5, 12), produtos=produtos)
        self.detalhar(analise, produtos, movimentos=[("Produto fictício 001", "30", "10", "COMPARAVEL")])
        from models import IndicadorComplementarAnalise
        complemento = self.db.session.execute(select(IndicadorComplementarAnalise)).scalar_one()
        complemento.movimentacao_total = 9
        self.db.session.commit()
        texto = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", self.entrar().get("/cliente/dashboard").get_data(as_text=True)))
        self.assertIn("1 produto(s) comparáveis entre os 1 registrados de 9 comprados", texto)
        self.assertIn("registrada para 1 de 9 produtos comprados", texto)

    def test_periodos_com_duracoes_diferentes_declarados_no_indicador(self):
        self.publicar_com(self.analise_id, date(2026, 2, 1), date(2026, 2, 28), "28000", "20000",
                          datetime(2026, 3, 5, 12))
        atual = self.nova_analise(date(2026, 3, 1), date(2026, 3, 31))
        self.publicar_com(atual.id_analise, date(2026, 3, 1), date(2026, 3, 31), "31000", "22000",
                          datetime(2026, 4, 5, 12))
        texto = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", self.entrar().get("/cliente/dashboard").get_data(as_text=True)))
        self.assertIn("+10,7% vs. 02/2026", texto)
        # Declarado nos dois cartões com variação (faturamento e total comprado).
        self.assertEqual(texto.count("Períodos com durações diferentes: 31 dias neste e 28 em 02/2026."), 2)
        self.assertIn("Como os períodos têm 31 e 28 dias, a média diária ficou estável.", texto)
        self.assertNotIn("Faturamento em alta", texto)

    def test_estimativa_legada_rotulada_sem_presumir_unidade(self):
        analise = self.publicar_com(self.analise_id, date(2026, 1, 1), date(2026, 1, 31), "1000", "900",
                                    datetime(2026, 2, 5, 12), produtos=[("Café fictício", "700", "A")])
        analise.indicador.produto_maior_saldo_parado_nome = "Café fictício"
        analise.indicador.saldo_estimado_parado = Decimal(12)
        self.db.session.commit()
        texto = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", self.entrar().get("/cliente/dashboard").get_data(as_text=True)))
        self.assertIn("Estimativa +12", texto)
        self.assertIn("sem conferência de correspondência entre os relatórios nem de unidade de medida", texto)
        self.assertNotIn("+12 un.", texto)


class CurvaABCLegadoECompletoTests(_PainelCase):
    def test_legado_com_20_linhas_declara_limitacao_sem_estimar(self):
        self.publicar_com(self.analise_id, date(2026, 1, 1), date(2026, 1, 31), "100000", "80000",
                          datetime(2026, 2, 5, 12), produtos=self.catalogo(20))
        corpo = self.entrar().get("/cliente/dashboard").get_data(as_text=True)
        self.assertIn("armazenou só os 20 primeiros produtos do ranking", corpo)
        self.assertIsNone(_dados(corpo)["distribuicao"])
        self.assertNotIn('id="chartDistribuicaoClasses"', corpo)
        # Sem afirmar a causa (processamento anterior ou detalhamento não gravado).
        self.assertIn("Esta análise não tem o detalhamento por produto armazenado", corpo)

    def test_legado_completo_com_menos_de_20_linhas(self):
        self.publicar_com(self.analise_id, date(2026, 1, 1), date(2026, 1, 31), "1000", "800",
                          datetime(2026, 2, 5, 12),
                          produtos=[("A1", "700", "A"), ("B1", "200", "B"), ("C1", "100", "C")])
        dados = _dados(self.entrar().get("/cliente/dashboard").get_data(as_text=True))
        self.assertEqual(dados["distribuicao"]["percentuais"], [70.0, 20.0, 10.0])
        self.assertEqual(dados["distribuicao"]["produtos"], [1, 1, 1])

    def test_detalhamento_completo_universo_e_movimentacao(self):
        produtos = self.catalogo(60)
        analise = self.publicar_com(self.analise_id, date(2026, 1, 1), date(2026, 1, 31), "50000", "56000",
                                    datetime(2026, 2, 5, 12), produtos=produtos)
        self.detalhar(analise, produtos, movimentos=[
            ("Produto fictício 001", "300", "100", "COMPARAVEL"),
            ("Produto fictício 010", "50", "45", "COMPARAVEL"),
            ("Produto sem venda", "40", None, "SEM_VENDA_CORRESPONDENTE"),
        ])
        corpo = self.entrar().get("/cliente/dashboard").get_data(as_text=True)
        dados = _dados(corpo)
        self.assertEqual(dados["distribuicao"]["produtos"], [12, 18, 30])
        self.assertAlmostEqual(sum(dados["distribuicao"]["percentuais"]), 100.0, places=6)
        self.assertEqual(dados["distribuicao"]["total_produtos"], 60)
        self.assertEqual(len(dados["curva_abc"]["labels"]), 10)  # Pareto: 10 primeiros, como a página da análise
        self.assertIn('id="chartDistribuicaoClasses"', corpo)
        texto = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", corpo))
        self.assertIn("Maior diferença: unidades compradas − vendidas", texto)
        # Sem unidade informada nos relatórios, nenhuma unidade é presumida.
        self.assertIn("Produto fictício 001 Comprado 300 Vendido 100 Diferença +200 Diferença entre quantidades", texto)
        self.assertIn("Saída abaixo da metade do volume comprado no período.", texto)
        self.assertIn("produto(s) comprado(s) não têm venda correspondente", texto)
        self.assertIn("Produtos com compras superiores às vendas", texto)
        self.assertIn("Todos os 60 produtos com venda", texto)

    def test_detalhamento_limitado_e_declarado(self):
        produtos = self.catalogo(40)
        analise = self.publicar_com(self.analise_id, date(2026, 1, 1), date(2026, 1, 31), "50000", "40000",
                                    datetime(2026, 2, 5, 12), produtos=produtos)
        self.detalhar(analise, produtos, limitado=25)
        client = self.entrar()
        corpo = client.get("/cliente/dashboard").get_data(as_text=True)
        self.assertIn("Os 25 primeiros de 40 produtos", corpo)
        pagina = client.get(f"/cliente/analise/{self.analise_id}/produtos?visao=ranking&pagina=2").json
        self.assertEqual((pagina["total"], pagina["paginas"], pagina["completo"]), (25, 1, False))

    def test_sem_tabelas_do_detalhamento_a_pagina_segue_no_legado(self):
        produtos = [("A1", "1000", "A")]
        analise = self.publicar_com(self.analise_id, date(2026, 1, 1), date(2026, 1, 31), "1000", "800",
                                    datetime(2026, 2, 5, 12), produtos=produtos)
        self.detalhar(analise, produtos, movimentos=[("A1", "30", "10", "COMPARAVEL")])
        id_analise = analise.id_analise
        client = self.entrar()
        url = f"/cliente/analise/{id_analise}/produtos?visao=movimentacao"
        self.assertIn("Compras x vendas por produto", client.get("/cliente/dashboard").get_data(as_text=True))
        self.assertFalse(client.get(url).json.get("indisponivel"))
        # Verificação de esquema dizendo "ausente": nada do detalhamento é lido.
        with patch("detalhamento_produtos.esquema_detalhamento_disponivel", return_value=False):
            corpo = client.get("/cliente/dashboard").get_data(as_text=True)
            self.assertTrue(client.get(url).json["indisponivel"])
        self.assertIn("Esta análise não tem o detalhamento por produto armazenado", corpo)
        self.assertIn("Ranking armazenado nesta análise", corpo)
        # Antes da migração de verdade (expand -> migrate -> deploy): tabelas ausentes.
        import detalhamento_produtos
        from flask_migrate import downgrade, upgrade
        self.db.session.execute(sa_text("DELETE FROM produto_desempenho_analise"))
        self.db.session.execute(sa_text("DELETE FROM indicador_complementar_analise"))
        self.db.session.commit()
        self._migrar(downgrade, "f4c2a8e1d9b6")
        detalhamento_produtos.esquecer_esquema_detalhamento()
        resposta = client.get("/cliente/dashboard")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("Esta análise não tem o detalhamento por produto armazenado", resposta.get_data(as_text=True))
        self.assertEqual(client.get(f"/cliente/analise/{id_analise}/produtos?visao=ranking").json["total"], 1)
        self.assertTrue(client.get(url).json["indisponivel"])
        self._migrar(upgrade, "head")
        detalhamento_produtos.esquecer_esquema_detalhamento()

    def _migrar(self, funcao, revisao):
        import contextlib
        import io
        from tests.deploy_support import ROOT
        self.db.session.remove()
        with patch("logging.config.fileConfig"), contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            funcao(directory=str(ROOT / "migrations"), revision=revisao)


class ConsultaPaginadaTests(_PainelCase):
    def setUp(self):
        super().setUp()
        self.produtos = self.catalogo(60) + [("Item 50% _raro_", "1", "C")]
        self.analise = self.publicar_com(self.analise_id, date(2026, 1, 1), date(2026, 1, 31), "50000", "40000",
                                         datetime(2026, 2, 5, 12), produtos=self.produtos)
        self.detalhar(self.analise, self.produtos, movimentos=[
            (f"Produto fictício {i:03d}", "30", "10", "COMPARAVEL") for i in range(1, 31)])
        self.cli = self.entrar()
        self.url = f"/cliente/analise/{self.analise_id}/produtos"

    def test_paginas_limites_e_cabecalhos(self):
        primeira = self.cli.get(self.url + "?visao=ranking")
        self.assertEqual(primeira.status_code, 200)
        self.assertEqual(primeira.headers["Cache-Control"], "no-store")
        self.assertEqual(primeira.headers["X-Content-Type-Options"], "nosniff")
        dados = primeira.json
        self.assertEqual((dados["total"], dados["paginas"], len(dados["itens"])), (61, 3, 25))
        self.assertEqual(dados["itens"][0]["posicao"], 1)
        self.assertTrue(dados["itens"][0]["faturamento"].startswith("R$ "))
        ultima = self.cli.get(self.url + "?visao=ranking&pagina=999").json
        self.assertEqual((ultima["pagina"], len(ultima["itens"])), (3, 11))
        self.assertEqual(self.cli.get(self.url + "?visao=ranking&pagina=-4").json["pagina"], 1)
        self.assertEqual(self.cli.get(self.url + "?visao=ranking&pagina=abc").json["pagina"], 1)

    def test_filtros_e_busca_literal(self):
        classe_b = self.cli.get(self.url + "?visao=ranking&classe=B").json
        self.assertTrue(classe_b["itens"] and all(i["classe"] == "B" for i in classe_b["itens"]))
        invalida = self.cli.get(self.url + "?visao=ranking&classe=Z").json
        self.assertEqual(invalida["total"], 61)
        literal = self.cli.get(self.url + "?visao=ranking&busca=50%25 _raro_").json
        self.assertEqual([i["nome"] for i in literal["itens"]], ["Item 50% _raro_"])
        # "%" e "_" nunca viram curinga: a busca usa o nome normalizado (só letras,
        # números e espaços), como a consulta legada.
        so_pontuacao = self.cli.get(self.url + "?visao=ranking&busca=%25").json
        self.assertEqual(so_pontuacao["total"], 61)  # equivale a não buscar
        self.assertEqual(self.cli.get(self.url + "?visao=ranking&busca=1_0").json["total"], 0)
        self.assertEqual(self.cli.get(self.url + "?visao=ranking&busca=%25raro%25").json["total"], 1)
        # Acentos, maiúsculas e pontuação não impedem o encontro.
        self.assertEqual(self.cli.get(self.url + "?visao=ranking&busca=ficticio").json["total"], 60)
        self.assertEqual(self.cli.get(self.url + "?visao=ranking&busca=FICT%C3%8DCIO 007").json["total"], 1)
        longa = self.cli.get(self.url + "?visao=ranking&busca=" + "x" * 500)
        self.assertEqual(longa.status_code, 200)

    def test_movimentacao_filtros(self):
        acima = self.cli.get(self.url + "?visao=movimentacao&filtro=acima").json
        self.assertEqual((acima["total"], acima["paginas"]), (30, 2))
        self.assertEqual((acima["itens"][0]["unidade_compra"], acima["itens"][0]["unidade_venda"]), (None, None))
        self.assertEqual(acima["itens"][0]["diferenca"], "+20")
        sem = self.cli.get(self.url + "?visao=movimentacao&filtro=sem_correspondencia").json
        self.assertEqual(sem["total"], 0)
        padrao = self.cli.get(self.url + "?visao=movimentacao&filtro=xyz").json
        self.assertEqual(padrao["filtro"], "acima")

    def test_compras_acima_usam_o_mesmo_criterio_das_recomendacoes(self):
        from models import ProdutoDesempenhoAnalise
        # Saída de 95% (comprou 30, vendeu 28,5): diferença positiva, mas alinhada.
        linha = self.db.session.execute(select(ProdutoDesempenhoAnalise).where(
            ProdutoDesempenhoAnalise.produto_nome == "Produto fictício 001")).scalar_one()
        linha.quantidade_vendida, linha.diferenca_quantidade = Decimal("28.5"), Decimal("1.5")
        self.db.session.commit()
        acima = self.cli.get(self.url + "?visao=movimentacao&filtro=acima&busca=001").json
        self.assertEqual(acima["total"], 0)
        comparaveis = self.cli.get(self.url + "?visao=movimentacao&filtro=comparaveis&busca=001").json
        self.assertEqual(comparaveis["itens"][0]["interpretacao"], "Compras alinhadas às vendas do período.")
        self.assertEqual(self.cli.get(self.url + "?visao=movimentacao&filtro=acima").json["total"], 29)

    def test_get_nao_altera_estado(self):
        from models import IndicadorComplementarAnalise, ProdutoDesempenhoAnalise
        antes = [self.db.session.scalar(select(func.count()).select_from(m))
                 for m in (ProdutoDesempenhoAnalise, IndicadorComplementarAnalise)]
        for consulta in ("?visao=ranking&pagina=2", "?visao=movimentacao", "?visao=ranking&busca=Café"):
            self.assertEqual(self.cli.get(self.url + consulta).status_code, 200)
        self.db.session.expire_all()
        depois = [self.db.session.scalar(select(func.count()).select_from(m))
                  for m in (ProdutoDesempenhoAnalise, IndicadorComplementarAnalise)]
        self.assertEqual(antes, depois)


class IsolamentoEPermissoesTests(_PainelCase):
    def test_outra_empresa_rascunho_e_inexistente_dao_404(self):
        from models import Analise
        self.publicar_com(self.outra_analise_id, date(2026, 1, 1), date(2026, 1, 31), "999", "1",
                          datetime(2026, 2, 5, 12), produtos=[("Produto da outra empresa", "999", "A")])
        self.publicar_com(self.analise_id, date(2026, 1, 1), date(2026, 1, 31), "100", "90",
                          datetime(2026, 2, 5, 12), produtos=[("Produto próprio", "100", "A")])
        client = self.entrar()
        self.assertEqual(client.get(f"/cliente/analise/{self.outra_analise_id}/produtos").status_code, 404)
        self.assertEqual(client.get("/cliente/analise/999999/produtos").status_code, 404)
        corpo = client.get("/cliente/dashboard").get_data(as_text=True)
        self.assertNotIn("Produto da outra empresa", corpo)
        aberta = self.nova_analise(date(2026, 3, 1), date(2026, 3, 31), status="EM_ANALISE")
        self.assertEqual(client.get(f"/cliente/analise/{aberta.id_analise}/produtos").status_code, 404)
        self.assertIsNotNone(self.db.session.get(Analise, aberta.id_analise))

    def test_sem_login_e_admin_nao_acessam(self):
        self.publicar_com(self.analise_id, date(2026, 1, 1), date(2026, 1, 31), "100", "90",
                          datetime(2026, 2, 5, 12), produtos=[("Produto próprio", "100", "A")])
        anonimo = self.client.get(f"/cliente/analise/{self.analise_id}/produtos")
        self.assertEqual(anonimo.status_code, 302)
        self.assertIn("/auth/login", anonimo.headers["Location"])
        self.login(email="admin-test@example.invalid")
        self.assertEqual(self.client.get(f"/cliente/analise/{self.analise_id}/produtos").status_code, 403)

    def test_periodo_nao_pago_fica_fora_do_painel_e_da_consulta(self):
        self.contratar()
        jan = self.publicar_com(self.analise_id, date(2026, 1, 1), date(2026, 1, 31), "27350", "19900",
                                datetime(2026, 2, 5, 12), produtos=[("Produto liberado", "27350", "A")])
        fev = self.publicar_com(self.nova_analise(date(2026, 2, 1), date(2026, 2, 28)).id_analise,
                                date(2026, 2, 1), date(2026, 2, 28), "18500", "14200", datetime(2026, 3, 1, 12),
                                produtos=[("Produto sigiloso", "18500", "A")])
        self.detalhar(fev, [("Produto sigiloso", "18500", "A")])
        self.pagar(date(2026, 1, 1), date(2026, 1, 31))
        self.ativar_regras()
        client = self.entrar()
        self.assertEqual(client.get(f"/cliente/analise/{fev.id_analise}/produtos").status_code, 403)
        corpo = client.get("/cliente/dashboard").get_data(as_text=True)
        for marca in ("Produto sigiloso", "18.500", "14.200"):
            self.assertNotIn(marca, corpo)
        self.assertIn(f'/cliente/analise/{jan.id_analise}"', corpo)
        dados = _dados(corpo)
        self.assertIsNone(dados["historico"])  # um único período pago: sem série


class TotaisResumoEValoresAusentesTests(_PainelCase):
    def test_totais_por_situacao_de_todos_os_comprados_com_registro_parcial(self):
        produtos = self.catalogo(12)
        analise = self.publicar_com(self.analise_id, date(2026, 1, 1), date(2026, 1, 31), "10000", "9000",
                                    datetime(2026, 2, 5, 12), produtos=produtos)
        self.detalhar(analise, produtos, movimentos=[("Produto fictício 001", "30", "10", "COMPARAVEL")])
        from models import IndicadorComplementarAnalise
        complemento = self.db.session.execute(select(IndicadorComplementarAnalise)).scalar_one()
        # 9 comprados no relatório; só 1 registrado (teto); totais gravados pelo ETL.
        complemento.movimentacao_total = 9
        (complemento.movimentacao_comparaveis, complemento.movimentacao_sem_venda,
         complemento.movimentacao_unidade_divergente, complemento.movimentacao_unidade_ambigua,
         complemento.movimentacao_quantidade_invalida) = (5, 2, 1, 0, 1)
        self.db.session.commit()
        texto = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", self.entrar().get("/cliente/dashboard").get_data(as_text=True)))
        self.assertIn("5 produto(s) comparáveis de 9 comprados · a consulta mostra os 1 registrados", texto)
        self.assertIn("os totais por situação consideram todos os produtos", texto)
        self.assertIn("2 produto(s) comprado(s) não têm venda correspondente", texto)
        self.assertIn("1 produto(s) com unidade diferente, ausente ou registrada de mais de uma forma", texto)
        self.assertIn("1 produto(s) com quantidade inválida", texto)

    def test_resumo_executivo_mostra_a_copia_publicada_e_nunca_o_rascunho(self):
        analise = self.publicar_com(self.analise_id, date(2026, 1, 1), date(2026, 1, 31), "10000", "9000",
                                    datetime(2026, 2, 5, 12), produtos=[("Café fictício", "6000", "A")])
        relatorio = analise.relatorio
        relatorio.resumo_executivo_publicado = "Resumo executivo publicado fictício"
        relatorio.conclusao_estrategica_publicada = "Conclusão estratégica publicada fictícia"
        relatorio.titulo_publicado = relatorio.titulo
        relatorio.resumo_executivo = "Rascunho em edição que não foi publicado"
        self.db.session.commit()
        corpo = self.entrar().get("/cliente/dashboard").get_data(as_text=True)
        secao = re.search(r'<section id="resumo-executivo".*?</section>', corpo, re.S).group(0)
        self.assertIn("Resumo executivo publicado fictício", secao)
        self.assertIn('class="resumo-destaques"', secao)
        self.assertNotIn("Rascunho em edição que não foi publicado", corpo)

    def test_valores_ausentes_do_indicador_nao_viram_equilibrio_nem_zero(self):
        analise = self.publicar_com(self.analise_id, date(2026, 1, 1), date(2026, 1, 31), "10000", "9000",
                                    datetime(2026, 2, 5, 12), produtos=[("Café fictício", "6000", "A")])
        analise.indicador.total_comprado = None
        analise.indicador.saldo_estimado_compras_vendas = None
        self.db.session.commit()
        corpo = self.entrar().get("/cliente/dashboard").get_data(as_text=True)
        texto = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", corpo))
        self.assertNotIn('<span class="painel-sinal is-equilibrio">Equilíbrio</span>', corpo)
        # No próprio cartão da diferença (o de movimentação também diz "Não calculado").
        self.assertIn('<span class="painel-sinal is-equilibrio">Não calculado</span>', corpo)
        self.assertIn("Não informado nesta análise", texto)
        self.assertIn("a diferença entre compras e vendas não foi calculada", texto)
        self.assertNotIn("tiveram o mesmo valor", texto)
        self.assertIsNone(_dados(corpo)["comparativo"])
        self.assertNotIn('id="chartCliente"', corpo)


class ConsultasLimitadasTests(_PainelCase):
    def test_painel_e_consulta_nao_carregam_o_catalogo_inteiro(self):
        from models import IndicadorComplementarAnalise, ProdutoDesempenhoAnalise
        analise = self.publicar_com(self.analise_id, date(2026, 1, 1), date(2026, 1, 31), "3000000", "2900000",
                                    datetime(2026, 2, 5, 12))
        n = 3000
        linhas, acumulado, contagem, soma = [], Decimal(0), {"A": 0, "B": 0, "C": 0}, {"A": 0, "B": 0, "C": 0}
        total = sum(Decimal(3000 - i) for i in range(n))
        for i in range(n):
            valor = Decimal(3000 - i)
            acumulado += valor / total * 100
            classe = "A" if acumulado <= 80 or i == 0 else ("B" if acumulado <= 95 else "C")
            contagem[classe] += 1
            soma[classe] += valor
            linhas.append(dict(id_analise=analise.id_analise, produto_chave=f"{i:016x}",
                               produto_nome=f"Produto fictício em escala {i:04d}", posicao_ranking=i + 1,
                               classe_abc=classe, faturamento=valor, quantidade_vendida=Decimal(100),
                               percentual_individual=round(valor / total * 100, 2),
                               percentual_acumulado=round(min(acumulado, Decimal(100)), 2),
                               quantidade_comprada=Decimal(100 + n - i), situacao_movimentacao="COMPARAVEL",
                               diferenca_quantidade=Decimal(n - i), posicao_movimentacao=i + 1))
        self.db.session.add(IndicadorComplementarAnalise(
            id_analise=analise.id_analise, versao_metodologia=1,
            versao_processamento=analise.indicador.versao_processamento, abc_total_produtos=n,
            abc_faturamento_total=total, abc_produtos_a=contagem["A"], abc_produtos_b=contagem["B"],
            abc_produtos_c=contagem["C"], abc_faturamento_a=soma["A"], abc_faturamento_b=soma["B"],
            abc_faturamento_c=soma["C"], produtos_vendas=n, produtos_compras=n, compras_por_produto=True,
            unidade_vendas_informada=True, unidade_compras_informada=True, produtos_registrados=n,
            ranking_registrado=n, movimentacao_total=n, movimentacao_registrada=n, movimentacao_comparaveis=n,
            movimentacao_sem_venda=0, movimentacao_unidade_divergente=0, movimentacao_unidade_ambigua=0,
            movimentacao_quantidade_invalida=0, registro_limitado=False))
        self.db.session.execute(insert(ProdutoDesempenhoAnalise), linhas)
        self.db.session.commit()
        client = self.entrar()
        client.get("/cliente/dashboard")  # aquecimento (caches de esquema)
        carregadas, consultas = [], []
        contar_linha = lambda *_args: carregadas.append(1)
        contar_consulta = lambda *_args: consultas.append(1)
        event.listen(ProdutoDesempenhoAnalise, "load", contar_linha)
        event.listen(self.db.engine, "before_cursor_execute", contar_consulta)
        try:
            self.assertEqual(client.get("/cliente/dashboard").status_code, 200)
            painel = (len(carregadas), len(consultas))
            carregadas.clear(), consultas.clear()
            resposta = client.get(f"/cliente/analise/{analise.id_analise}/produtos?visao=movimentacao&filtro=todas&pagina=40")
            endpoint = (len(carregadas), len(consultas))
        finally:
            event.remove(ProdutoDesempenhoAnalise, "load", contar_linha)
            event.remove(self.db.engine, "before_cursor_execute", contar_consulta)
        self.assertEqual(resposta.json["total"], n)
        self.assertEqual(len(resposta.json["itens"]), 25)
        # Topo (20) + destaques por classe (9) + movimentação (10 + 10) + mais vendido (1)
        # + primeira página das duas consultas (25 + 25): nunca o catálogo de 3.000 linhas.
        self.assertLessEqual(painel[0], 100, painel)
        self.assertLessEqual(painel[1], 40, painel)
        self.assertEqual(endpoint[0], 25, endpoint)
        self.assertLessEqual(endpoint[1], 15, endpoint)


class CoberturaDasComprasTests(_PainelCase):
    def test_compras_por_produto_exigem_cobertura_do_periodo_de_compras(self):
        self.contratar()
        produtos = [("Produto de março", "5000", "A")]
        mar = self.publicar_com(self.analise_id, date(2026, 3, 1), date(2026, 3, 31), "5000", "4000",
                                datetime(2026, 4, 5, 12), produtos=produtos)
        self.detalhar(mar, produtos, movimentos=[("Produto de março", "90", "30", "COMPARAVEL"),
                                                 ("Compra só de janeiro", "70", None, "SEM_VENDA_CORRESPONDENTE")])
        from models import IndicadorComplementarAnalise
        complemento = self.db.session.execute(select(IndicadorComplementarAnalise)).scalar_one()
        # Vendas de março (período pago); o relatório de compras cobre o trimestre.
        complemento.periodo_vendas_inicio, complemento.periodo_vendas_fim = date(2026, 3, 1), date(2026, 3, 31)
        complemento.periodo_compras_inicio, complemento.periodo_compras_fim = date(2026, 1, 1), date(2026, 3, 31)
        self.db.session.commit()
        self.pagar(date(2026, 3, 1), date(2026, 3, 31))
        self.ativar_regras()
        client = self.entrar()
        url = f"/cliente/analise/{mar.id_analise}/produtos?visao=movimentacao&filtro=todas"
        corpo = client.get("/cliente/dashboard").get_data(as_text=True)
        texto = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", corpo))
        # Nenhuma quantidade comprada aparece (cartão de maior diferença bloqueado).
        self.assertNotIn("Comprado 90", texto)
        self.assertNotIn("não têm venda correspondente", texto)
        self.assertIn("Não exibido", texto)
        self.assertIn("abrange período fora da cobertura contratada", corpo)
        self.assertNotIn("Produtos com compras superiores às vendas", corpo)
        self.assertIn("Produto de março", corpo)  # o ranking de vendas (período pago) segue
        bloqueada = client.get(url).json
        self.assertTrue(bloqueada["indisponivel"])
        self.assertEqual(bloqueada["itens"], [])
        # Com o trimestre coberto, as compras por produto voltam a ser exibidas.
        self.pagar(date(2026, 1, 1), date(2026, 2, 28))
        liberada = client.get(url).json
        self.assertEqual(liberada["total"], 2)
        corpo = client.get("/cliente/dashboard").get_data(as_text=True)
        texto = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", corpo))
        self.assertNotIn("fora da cobertura contratada", corpo)
        self.assertIn("Compras x vendas por produto", corpo)
        self.assertIn("Comprado 90", texto)  # controle positivo do bloqueio acima
        self.assertIn("1 produto(s) comprado(s) não têm venda correspondente", corpo)


class HistoricoTests(_PainelCase):
    def test_quinzenal_mensal_sobreposicao_e_lacuna(self):
        from models import Analise
        m1 = self.publicar_com(self.analise_id, date(2026, 1, 1), date(2026, 1, 31), "1000", "900",
                               datetime(2026, 2, 2, 12))
        q = self.nova_analise(date(2026, 2, 1), date(2026, 2, 15))
        self.publicar_com(q.id_analise, date(2026, 2, 1), date(2026, 2, 15), "500", "400",
                          datetime(2026, 2, 20, 12), tipo="QUINZENAL", quinzena=1)
        duplicada = self.publicar_com(self.nova_analise(date(2026, 3, 1), date(2026, 3, 31)).id_analise,
                                      date(2026, 3, 1), date(2026, 3, 31), "1500", "1200", datetime(2026, 4, 2, 12))
        corrigida = self.publicar_com(self.nova_analise(date(2026, 3, 1), date(2026, 3, 31)).id_analise,
                                      date(2026, 3, 1), date(2026, 3, 31), "1600", "1250", datetime(2026, 4, 9, 12))
        dados = _dados(self.entrar().get("/cliente/dashboard").get_data(as_text=True))
        # A atual é março (corrigida, a mais recente); fevereiro é quinzenal e fica fora; o março
        # duplicado sai por sobreposição; janeiro -> março marca a lacuna de fevereiro.
        self.assertEqual(dados["historico"]["labels"], ["01/2026", "03/2026"])
        self.assertEqual(dados["historico"]["vendas"], [1000.0, 1600.0])
        self.assertTrue(dados["historico"]["pontos"][1]["lacuna_antes"])
        self.assertEqual([p["id"] for p in dados["historico"]["pontos"]], [m1.id_analise, corrigida.id_analise])
        self.assertIsNotNone(self.db.session.get(Analise, duplicada.id_analise))
