"""Detalhamento por produto (operação calculate_detailed, revisão 5a9c3e7d1b42).

Garante que a ampliação NÃO altera o motor financeiro (o resultado é idêntico ao da
operação calculate nos 22 cenários históricos de SEC-005) e que o detalhamento é
exato, limitado e honesto: universo completo da Curva ABC, movimentação só com
unidades e correspondência confiáveis, tetos de linhas/saída declarados, contrato
do worker validado campo a campo, persistência idempotente e migração reversível.
Todos os relatórios são sintéticos.
"""

import contextlib
from datetime import date
from decimal import Decimal
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from sqlalchemy import func, inspect, select, text

import etl_processor
from etl_limits import ETLLimits, using_limits
from etl_runtime import run_calculation, run_calculation_detailed, validar_detalhamento
from tests.deploy_support import ROOT, DeployTestCase
from tests.etl_equivalence_support import fixture_pairs, plain, write_csv, write_xlsx

LIMITES = ETLLimits()


def _detalhar(vendas, compras, orcamento=None):
    with using_limits(LIMITES):
        bruto = etl_processor.calcular_com_detalhamento_local(
            str(vendas), str(compras), orcamento_bytes=orcamento or LIMITES.max_output_bytes)
    return bruto


def _linhas(detalhamento):
    colunas = detalhamento["colunas"]
    return [dict(zip(colunas, linha)) for linha in detalhamento["produtos"]]


class _Arquivos(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory(prefix="nexo-detalhe-")
        self.addCleanup(self.pasta.cleanup)
        self.dir = Path(self.pasta.name)

    def csv(self, nome, linhas):
        return write_csv(self.dir / nome, linhas)


class EquivalenciaFinanceiraTests(_Arquivos):
    """O modo detalhado devolve exatamente o mesmo ResultadoETL do modo padrão."""

    def test_22_cenarios_historicos_identicos_no_processo(self):
        pares = fixture_pairs(self.dir)
        self.assertEqual(len(pares), 22)
        for caso, (vendas, compras) in pares.items():
            with self.subTest(caso=caso), using_limits(LIMITES):
                original = etl_processor._calcular_kpis_local(str(vendas), str(compras))
                detalhado, bases = etl_processor._calcular_kpis_e_bases(str(vendas), str(compras), detalhado=True)
                self.assertEqual(plain(detalhado._asdict()), plain(original._asdict()))
                self.assertIsNotNone(bases)
                detalhe = etl_processor._montar_detalhamento(bases, LIMITES.max_output_bytes)
                validar_detalhamento(json.loads(json.dumps(detalhe, default=str)))

    def test_worker_isolado_mesmo_resultado_e_detalhamento_valido(self):
        pares = fixture_pairs(self.dir)
        for caso in ("c4_equilibrio_abc", "c1_hemorragia_nf", "purchase_period_fallback"):
            with self.subTest(caso=caso):
                vendas, compras = map(str, pares[caso])
                original = run_calculation(vendas, compras, LIMITES)
                resultado, detalhe = run_calculation_detailed(vendas, compras, LIMITES)
                self.assertEqual(plain(resultado._asdict()), plain(original._asdict()))
                self.assertIsNotNone(detalhe)
                self.assertEqual(detalhe["resumo"]["abc_total_produtos"],
                                 sum(c["qtd_produtos"] for c in original.kpis["curva_abc"]["resumo"]))

    def test_resumo_do_universo_igual_ao_resumo_do_motor(self):
        for caso, (vendas, compras) in fixture_pairs(self.dir).items():
            with self.subTest(caso=caso):
                bruto = _detalhar(vendas, compras)
                resumo_motor = {c["classe"]: c for c in bruto["resultado"]["kpis"]["curva_abc"]["resumo"]}
                resumo = bruto["detalhamento"]["resumo"]
                for letra in "abc":
                    if resumo_motor:
                        self.assertEqual(resumo[f"abc_produtos_{letra}"], resumo_motor[letra.upper()]["qtd_produtos"])
                        self.assertAlmostEqual(resumo[f"abc_faturamento_{letra}"],
                                               resumo_motor[letra.upper()]["faturamento"], places=2)


class UnidadesEMovimentacaoTests(_Arquivos):
    def test_unidades_reconhecidas_divergentes_e_ambiguas(self):
        vendas = self.csv("v.csv", [["Produto", "Un", "Quantidade", "Valor total"],
                                    ["Café", "UN", "100", "2000,00"], ["Leite", "LT", "80", "400,00"],
                                    ["Arroz", "UN", "10", "300,00"], ["Feijão", "CX", "5", "150,00"]])
        compras = self.csv("c.csv", [["Produto", "Unidade", "Qtde Comprada", "Total Custo"],
                                     ["Café", "Un.", "120", "1500,00"], ["Leite", "UN", "90", "300,00"],
                                     ["Arroz", "UN", "5", "100,00"], ["Arroz", "CX", "1", "100,00"],
                                     ["Feijão", "caixa", "5", "100,00"], ["Macarrão", "UN", "40", "120,00"]])
        bruto = _detalhar(vendas, compras)
        linhas = {l["nome"]: l for l in _linhas(bruto["detalhamento"])}
        self.assertEqual(linhas["Café"]["situacao"], "C")
        self.assertEqual(linhas["Café"]["diferenca"], 20.0)
        self.assertEqual(linhas["Leite"]["unidade_venda"], "L")
        self.assertEqual(linhas["Leite"]["situacao"], "D")
        self.assertIsNone(linhas["Leite"]["diferenca"])
        self.assertEqual(linhas["Arroz"]["situacao"], "M")
        self.assertEqual((linhas["Feijão"]["situacao"], linhas["Feijão"]["diferenca"]), ("C", 0.0))
        self.assertEqual(linhas["Macarrão"]["situacao"], "S")
        self.assertIsNone(linhas["Macarrão"]["posicao"])
        resumo = bruto["detalhamento"]["resumo"]
        self.assertTrue(resumo["unidade_vendas_informada"] and resumo["unidade_compras_informada"])

    def test_unidade_ausente_em_relatorio_com_coluna_nao_vira_comparacao(self):
        # A coluna de unidade das vendas foi aceita, mas "Leite" está sem unidade nela:
        # caixas compradas não podem ser comparadas com unidades de tamanho desconhecido.
        vendas = self.csv("v.csv", [["Produto", "Un", "Quantidade", "Valor total"],
                                    ["Café", "UN", "100", "2000,00"], ["Arroz", "UN", "10", "300,00"],
                                    ["Feijão", "UN", "7", "70,00"], ["Leite", "", "100", "400,00"]])
        compras = self.csv("c.csv", [["Produto", "Unidade", "Qtde Comprada", "Total Custo"],
                                     ["Café", "UN", "120", "1500,00"], ["Leite", "CX", "10", "300,00"],
                                     ["Arroz", "UN", "8", "100,00"], ["Sabão", "UN", "4", "20,00"]])
        bruto = _detalhar(vendas, compras)
        linhas = {l["nome"]: l for l in _linhas(bruto["detalhamento"])}
        self.assertEqual((linhas["Leite"]["situacao"], linhas["Leite"]["diferenca"]), ("M", None))
        self.assertEqual(linhas["Café"]["situacao"], "C")
        resumo = bruto["detalhamento"]["resumo"]
        self.assertEqual((resumo["movimentacao_comparaveis"], resumo["movimentacao_sem_venda"],
                          resumo["movimentacao_unidade_ambigua"]), (2, 1, 1))
        self.assertEqual(resumo["movimentacao_comparaveis"] + resumo["movimentacao_sem_venda"]
                         + resumo["movimentacao_unidade_divergente"] + resumo["movimentacao_unidade_ambigua"]
                         + resumo["movimentacao_quantidade_invalida"], resumo["movimentacao_total"])

    def test_linha_de_compra_sem_produto_fica_fora_do_detalhamento(self):
        vendas = self.csv("v.csv", [["Produto", "Quantidade", "Valor total"], ["Café", "10", "100,00"]])
        compras = write_xlsx(self.dir / "c.xlsx", [("Compras", [
            ["Fornecedor", "Produto", "Qtde Comprada", "Total Custo"],
            ["Distribuidora fictícia", "Café", 12, 90],
            ["Transportadora fictícia", None, 1, 35]])])
        bruto = _detalhar(vendas, compras)
        nomes = [l["nome"] for l in _linhas(bruto["detalhamento"])]
        self.assertNotIn("nan", [n.lower() for n in nomes])
        self.assertEqual(bruto["detalhamento"]["resumo"]["produtos_compras"], 1)
        self.assertEqual(bruto["detalhamento"]["resumo"]["movimentacao_total"], 1)

    def test_unidade_em_so_parte_das_linhas_nao_vira_comparacao(self):
        # 40 das 100 unidades vendidas de Leite estão sem unidade: não há comparação
        # validada (situação M), nem nas vendas nem nas compras.
        vendas = self.csv("v.csv", [["Produto", "Un", "Quantidade", "Valor total"],
                                    ["Leite", "UN", "60", "240,00"], ["Leite", "", "40", "160,00"],
                                    ["Café", "UN", "10", "100,00"], ["Arroz", "UN", "100", "500,00"]])
        compras = self.csv("c.csv", [["Produto", "Unidade", "Qtde Comprada", "Total Custo"],
                                     ["Leite", "UN", "120", "300,00"], ["Café", "UN", "12", "90,00"],
                                     ["Arroz", "UN", "100", "300,00"], ["Arroz", "", "24", "70,00"]])
        linhas = {l["nome"]: l for l in _linhas(_detalhar(vendas, compras)["detalhamento"])}
        self.assertEqual((linhas["Leite"]["situacao"], linhas["Leite"]["diferenca"]), ("M", None))
        self.assertEqual((linhas["Arroz"]["situacao"], linhas["Arroz"]["diferenca"]), ("M", None))
        self.assertEqual(linhas["Café"]["situacao"], "C")

    def test_frete_taxas_e_juros_nao_viram_produto_comprado(self):
        vendas = self.csv("v.csv", [["Produto", "Quantidade", "Valor total"], ["Café", "10", "100,00"]])
        compras = self.csv("c.csv", [["Fornecedor", "Produto", "Qtde Comprada", "Total Custo"],
                                     ["Distribuidora fictícia", "Café", "12", "90,00"],
                                     ["Transportadora fictícia", "Frete", "1", "35,00"],
                                     ["Banco fictício", "Juros", "1", "4,00"]])
        bruto = _detalhar(vendas, compras)
        self.assertEqual([l["nome"] for l in _linhas(bruto["detalhamento"])], ["Café"])
        resumo = bruto["detalhamento"]["resumo"]
        self.assertEqual((resumo["produtos_compras"], resumo["movimentacao_sem_venda"]), (1, 0))

    def test_coluna_unidade_com_nomes_de_loja_e_ignorada(self):
        vendas = self.csv("v.csv", [["Produto", "Unidade", "Quantidade", "Valor total"],
                                    ["Café", "Matriz Centro", "10", "100,00"], ["Leite", "Loja 02", "5", "50,00"]])
        compras = self.csv("c.csv", [["Produto", "Qtde Comprada", "Total Custo"],
                                     ["Café", "10", "80,00"], ["Leite", "9", "40,00"]])
        bruto = _detalhar(vendas, compras)
        self.assertFalse(bruto["detalhamento"]["resumo"]["unidade_vendas_informada"])
        self.assertTrue(all(l["situacao"] == "C" for l in _linhas(bruto["detalhamento"])))

    def test_unidade_com_fator_nao_se_confunde(self):
        self.assertEqual(etl_processor._normalizar_unidade("cx12"), "CX12")
        self.assertEqual(etl_processor._normalizar_unidade("Caixa"), "CX")
        self.assertEqual(etl_processor._normalizar_unidade(" Un. "), "UN")
        self.assertIsNone(etl_processor._normalizar_unidade(""))
        self.assertFalse(etl_processor._unidade_reconhecida("MATRIZ"))

    def test_compras_em_nivel_de_nota_sem_movimentacao(self):
        vendas = self.csv("v.csv", [["Produto", "Quantidade", "Valor total"], ["Café", "10", "100,00"]])
        compras = self.csv("c.csv", [["Fornecedor", "Valor NF"], ["Distribuidora fictícia", "500,00"]])
        bruto = _detalhar(vendas, compras)
        resumo = bruto["detalhamento"]["resumo"]
        self.assertFalse(resumo["compras_por_produto"])
        self.assertIsNone(resumo["produtos_compras"])
        self.assertTrue(all(l["situacao"] is None for l in _linhas(bruto["detalhamento"])))

    def test_quantidade_invalida_e_ordem_da_movimentacao(self):
        vendas = self.csv("v.csv", [["Produto", "Quantidade", "Valor total"], ["A", "10", "100,00"],
                                    ["B", "-3", "-30,00"], ["C", "1", "10,00"]])
        compras = self.csv("c.csv", [["Produto", "Qtde Comprada", "Total Custo"], ["A", "40", "100,00"],
                                     ["B", "5", "10,00"], ["C", "3", "10,00"]])
        linhas = _linhas(_detalhar(vendas, compras)["detalhamento"])
        por_nome = {l["nome"]: l for l in linhas}
        self.assertEqual(por_nome["B"]["situacao"], "Q")
        self.assertIsNone(por_nome["B"]["posicao"])  # faturamento <= 0 não entra na Curva ABC
        ordem = sorted((l for l in linhas if l["posicao_movimentacao"]), key=lambda l: l["posicao_movimentacao"])
        self.assertEqual([l["nome"] for l in ordem], ["A", "C", "B"])


class EscalaETetosTests(_Arquivos):
    def _muitos(self, quantidade, compras=True):
        vendas = [["Produto", "Quantidade", "Valor total"]] + [
            [f"Produto sintético {i:05d}", "1", f"{(quantidade - i) * 3 + 1},00"] for i in range(quantidade)]
        arquivo_c = [["Produto", "Qtde Comprada", "Total Custo"]] + [
            [f"Produto sintético {i:05d}", "2", "1,00"] for i in range(0, quantidade, 2)]
        return self.csv("v.csv", vendas), self.csv("c.csv", arquivo_c if compras else
                                                    [["Fornecedor", "Valor NF"], ["F", "10,00"]])

    def test_milhares_de_produtos_completos_e_agregados_exatos(self):
        vendas, compras = self._muitos(3000)
        resultado, detalhe = run_calculation_detailed(str(vendas), str(compras), LIMITES)
        self.assertEqual(len(resultado.kpis["curva_abc"]["produtos"]), 20)  # contrato top-20 intacto
        resumo = detalhe["resumo"]
        self.assertEqual(resumo["abc_total_produtos"], 3000)
        self.assertEqual(resumo["ranking_registrado"], 3000)
        self.assertFalse(resumo["registro_limitado"])
        soma = sum(resumo[f"abc_faturamento_{c}"] for c in "abc")
        self.assertAlmostEqual(float(soma), float(resumo["abc_faturamento_total"]), places=1)
        motor = {c["classe"]: c["qtd_produtos"] for c in resultado.kpis["curva_abc"]["resumo"]}
        self.assertEqual((resumo["abc_produtos_a"], resumo["abc_produtos_b"], resumo["abc_produtos_c"]),
                         (motor["A"], motor["B"], motor["C"]))
        posicoes = sorted(p["posicao_ranking"] for p in detalhe["produtos"] if p["posicao_ranking"])
        self.assertEqual(posicoes, list(range(1, 3001)))

    def test_teto_de_linhas_declara_registro_limitado_com_prefixos_continuos(self):
        vendas, compras = self._muitos(40)
        with patch.object(etl_processor, "LIMITE_PRODUTOS_DETALHADOS", 7):
            detalhe = _detalhar(vendas, compras)["detalhamento"]
        resumo = detalhe["resumo"]
        self.assertTrue(resumo["registro_limitado"])
        self.assertEqual(len(detalhe["produtos"]), 7)
        linhas = _linhas(detalhe)
        posicoes = sorted(l["posicao"] for l in linhas if l["posicao"])
        self.assertEqual(posicoes[:resumo["ranking_registrado"]], list(range(1, resumo["ranking_registrado"] + 1)))
        self.assertLess(resumo["ranking_registrado"], 40)
        self.assertEqual(resumo["abc_total_produtos"], 40)  # o universo continua exato
        validar_detalhamento(json.loads(json.dumps(detalhe, default=str)))

    def test_orcamento_de_saida_corta_sem_derrubar_o_resultado(self):
        vendas, compras = self._muitos(200)
        bruto = _detalhar(vendas, compras, orcamento=RESERVA + 20000)
        self.assertIsNotNone(bruto["detalhamento"])
        self.assertTrue(bruto["detalhamento"]["resumo"]["registro_limitado"])
        self.assertLess(len(json.dumps(bruto["detalhamento"]["produtos"])), 20000)
        sem_espaco = _detalhar(vendas, compras, orcamento=1000)
        self.assertIsNone(sem_espaco["detalhamento"])
        self.assertEqual(sem_espaco["detalhamento_erro"], "orcamento")
        self.assertTrue(sem_espaco["resultado"]["sucesso"])

    def test_falha_no_detalhamento_nao_afeta_o_resultado(self):
        vendas, compras = self._muitos(5)
        with patch.object(etl_processor, "_montar_detalhamento", side_effect=RuntimeError("falha simulada")):
            bruto = _detalhar(vendas, compras)
        self.assertIsNone(bruto["detalhamento"])
        self.assertEqual(bruto["detalhamento_erro"], "detalhamento")
        self.assertTrue(bruto["resultado"]["sucesso"])

    def test_empates_tem_posicoes_unicas_e_classes_monotonicas(self):
        vendas = self.csv("v.csv", [["Produto", "Quantidade", "Valor total"]] +
                          [[f"Item {i}", "1", "10,00"] for i in range(12)])
        compras = self.csv("c.csv", [["Fornecedor", "Valor NF"], ["F", "10,00"]])
        linhas = sorted(_linhas(_detalhar(vendas, compras)["detalhamento"]), key=lambda l: l["posicao"])
        self.assertEqual([l["posicao"] for l in linhas], list(range(1, 13)))
        ordem = "ABC"
        classes = [ordem.index(l["classe"]) for l in linhas]
        self.assertEqual(classes, sorted(classes))


RESERVA = etl_processor.RESERVA_SAIDA_RESULTADO


class ContratoDoWorkerTests(_Arquivos):
    def _valido(self):
        vendas = self.csv("v.csv", [["Produto", "Quantidade", "Valor total"], ["A", "1", "10,00"]])
        compras = self.csv("c.csv", [["Produto", "Qtde Comprada", "Total Custo"], ["A", "2", "5,00"]])
        return json.loads(json.dumps(_detalhar(vendas, compras)["detalhamento"], default=str))

    def test_payload_valido_vira_linhas_do_modelo(self):
        convertido = validar_detalhamento(self._valido())
        self.assertEqual(convertido["produtos"][0]["situacao_movimentacao"], "COMPARAVEL")
        self.assertIsInstance(convertido["produtos"][0]["faturamento"], Decimal)
        self.assertIsInstance(convertido["resumo"]["periodo_vendas_inicio"], (date, type(None)))

    def test_payloads_adulterados_sao_recusados(self):
        casos = {
            "chave": lambda p: p["produtos"][0].__setitem__(0, "zz"),
            "situacao": lambda p: p["produtos"][0].__setitem__(11, "X"),
            "diferenca_sem_comparavel": lambda p: (p["produtos"][0].__setitem__(11, "S")),
            "classe_sem_posicao": lambda p: p["produtos"][0].__setitem__(2, None),
            "percentual_fora": lambda p: p["produtos"][0].__setitem__(6, 140.0),
            "nome_vazio": lambda p: p["produtos"][0].__setitem__(1, ""),
            "invariante": lambda p: p["resumo"].__setitem__("abc_produtos_a", 99),
            "colunas": lambda p: p["colunas"].reverse(),
            "nan": lambda p: p["produtos"][0].__setitem__(4, float("nan")),
            "chave_extra": lambda p: p["resumo"].__setitem__("extra", 1),
            "totais_situacao": lambda p: p["resumo"].__setitem__("movimentacao_comparaveis", 99),
            "total_situacao_ausente": lambda p: p["resumo"].pop("movimentacao_sem_venda"),
        }
        for nome, adulterar in casos.items():
            with self.subTest(caso=nome):
                payload = self._valido()
                adulterar(payload)
                with self.assertRaises(ValueError):
                    validar_detalhamento(payload)


class PersistenciaEMigracaoTests(DeployTestCase):
    """Banco SQLite com as migrações reais; os arquivos passam pelo worker isolado."""

    def setUp(self):
        super().setUp()
        self.fixtures()
        self.vendas = write_csv(self.work_dir / "v.csv", [
            ["Produto", "Un", "Quantidade", "Valor total"], ["Café", "UN", "100", "2000,00"],
            ["Leite", "UN", "80", "400,00"], ["Pão", "UN", "50", "100,00"]])
        self.compras = write_csv(self.work_dir / "c.csv", [
            ["Produto", "Unidade", "Qtde Comprada", "Total Custo"], ["Café", "UN", "130", "1500,00"],
            ["Leite", "UN", "60", "300,00"], ["Sabão", "UN", "10", "50,00"]])

    def _processar(self):
        resultado = etl_processor.processar_arquivos_analise(str(self.vendas), str(self.compras),
                                                             self.analise_id, self.db.session)
        self.db.session.commit()
        return resultado

    def _contar(self, modelo):
        return self.db.session.scalar(select(func.count()).select_from(modelo).where(
            modelo.id_analise == self.analise_id))

    def test_processamento_grava_detalhamento_e_reprocessamento_substitui(self):
        from models import IndicadorComplementarAnalise, ProdutoCurvaABC, ProdutoDesempenhoAnalise
        resultado = self._processar()
        self.assertTrue(resultado.sucesso, resultado.mensagem)
        self.assertEqual(resultado.mensagem, "Processamento concluído. KPIs consolidados + Curva ABC persistidos.")
        self.assertEqual(self._contar(IndicadorComplementarAnalise), 1)
        self.assertEqual(self._contar(ProdutoDesempenhoAnalise), 4)
        self.assertEqual(self._contar(ProdutoCurvaABC), 3)
        cafe = self.db.session.scalar(select(ProdutoDesempenhoAnalise).where(
            ProdutoDesempenhoAnalise.produto_nome == "Café"))
        self.assertEqual((cafe.situacao_movimentacao, cafe.diferenca_quantidade), ("COMPARAVEL", Decimal("30.0")))
        self.assertEqual(cafe.produto_busca, "CAFE")  # gravado na inserção em lote do ETL
        complemento = self.db.session.scalar(select(IndicadorComplementarAnalise))
        self.assertEqual((complemento.versao_processamento, complemento.movimentacao_comparaveis,
                          complemento.movimentacao_sem_venda), (1, 2, 1))
        self.assertTrue(self._processar().sucesso)
        self.assertEqual(self._contar(IndicadorComplementarAnalise), 1)
        self.assertEqual(self._contar(ProdutoDesempenhoAnalise), 4)

    def test_sem_tabelas_do_detalhamento_o_caminho_anterior_e_identico(self):
        from models import IndicadorAnalise, ProdutoDesempenhoAnalise
        with patch("detalhamento_produtos.esquema_detalhamento_disponivel", return_value=False), \
                patch.object(etl_processor, "calcular_kpis_detalhados_em_memoria",
                             side_effect=AssertionError("não deve detalhar")):
            resultado = self._processar()
        self.assertTrue(resultado.sucesso)
        self.assertEqual(self._contar(ProdutoDesempenhoAnalise), 0)
        indicador = self.db.session.scalar(select(IndicadorAnalise).where(IndicadorAnalise.id_analise == self.analise_id))
        self.assertEqual(indicador.faturamento_total, Decimal("2500.0"))

    def test_detalhamento_indisponivel_remove_linhas_antigas(self):
        from models import ProdutoDesempenhoAnalise
        self.assertTrue(self._processar().sucesso)
        original = etl_processor.calcular_kpis_detalhados_em_memoria
        with patch.object(etl_processor, "calcular_kpis_detalhados_em_memoria",
                          side_effect=lambda v, c: (original(v, c)[0], None)):
            self.assertTrue(self._processar().sucesso)
        self.assertEqual(self._contar(ProdutoDesempenhoAnalise), 0)

    def test_erro_de_banco_no_detalhamento_preserva_os_kpis(self):
        from sqlalchemy.exc import OperationalError
        from models import IndicadorAnalise, ProdutoCurvaABC, ProdutoDesempenhoAnalise
        with patch.object(etl_processor, "_inserir_detalhamento",
                          side_effect=OperationalError("x", {}, Exception("queda simulada"))):
            resultado = self._processar()
        self.assertTrue(resultado.sucesso)
        self.assertEqual(self._contar(IndicadorAnalise), 1)
        self.assertEqual(self._contar(ProdutoCurvaABC), 3)
        self.assertEqual(self._contar(ProdutoDesempenhoAnalise), 0)
        # Erro inesperado (não de banco) continua falhando fechado, sem gravação parcial.
        with patch.object(etl_processor, "_inserir_detalhamento", side_effect=RuntimeError("falha simulada")):
            self.assertFalse(self._processar().sucesso)

    def test_reprocessamento_com_falha_na_gravacao_nao_ressuscita_o_detalhamento_antigo(self):
        from sqlalchemy.exc import OperationalError
        from models import IndicadorAnalise, IndicadorComplementarAnalise, ProdutoDesempenhoAnalise
        self.assertTrue(self._processar().sucesso)
        self.assertEqual(self._contar(ProdutoDesempenhoAnalise), 4)
        with patch.object(etl_processor, "_inserir_detalhamento",
                          side_effect=OperationalError("x", {}, Exception("tempo esgotado simulado"))):
            self.assertTrue(self._processar().sucesso)
        # A exclusão do detalhamento anterior é confirmada à parte: a análise fica sem
        # detalhamento em vez de exibir o dos arquivos antigos ao lado dos KPIs novos.
        self.assertEqual(self._contar(ProdutoDesempenhoAnalise), 0)
        self.assertEqual(self._contar(IndicadorComplementarAnalise), 0)
        indicador = self.db.session.scalar(select(IndicadorAnalise).where(IndicadorAnalise.id_analise == self.analise_id))
        self.assertEqual(indicador.versao_processamento, 2)

    def test_detalhamento_de_outro_processamento_e_ignorado_pelo_portal(self):
        import detalhamento_produtos
        from models import Analise, ProdutoDesempenhoAnalise
        self.assertTrue(self._processar().sucesso)
        analise = self.db.session.get(Analise, self.analise_id)
        self.assertIsNotNone(detalhamento_produtos.complemento_vigente(analise))
        # Reprocessamento sem gravar o detalhamento (esquema dado como ausente, ex.:
        # versão anterior do sistema): as linhas antigas ficam, mas são ignoradas.
        with patch("detalhamento_produtos.esquema_detalhamento_disponivel", return_value=False):
            self.assertTrue(self._processar().sucesso)
        self.assertEqual(self._contar(ProdutoDesempenhoAnalise), 4)
        self.db.session.expire_all()
        analise = self.db.session.get(Analise, self.analise_id)
        self.assertEqual(analise.indicador.versao_processamento, 2)
        self.assertIsNone(detalhamento_produtos.complemento_vigente(analise))
        self.assertTrue(detalhamento_produtos.consultar_produtos(analise, "ranking")["legado"])

    def test_saida_estourada_cai_no_calculo_original(self):
        from models import IndicadorAnalise, ProdutoDesempenhoAnalise
        # Saída, tempo ou recursos do worker esgotados só na execução detalhada: o
        # cálculo original é refeito e o processamento conclui, sem detalhamento.
        for codigo in ("output", "timeout", "worker"):
            with self.subTest(codigo=codigo):
                with patch.object(etl_processor, "calcular_kpis_detalhados_em_memoria",
                                  side_effect=etl_processor.ETLValidationError("Falha simulada", codigo)):
                    resultado = self._processar()
                self.assertTrue(resultado.sucesso, resultado.mensagem)
                self.assertIsNotNone(self.db.session.scalar(select(IndicadorAnalise).where(
                    IndicadorAnalise.id_analise == self.analise_id)))
                self.assertEqual(self._contar(ProdutoDesempenhoAnalise), 0)
        # Erro do próprio arquivo falharia igual sem detalhamento: sobe, sem gravação.
        with patch.object(etl_processor, "calcular_kpis_detalhados_em_memoria",
                          side_effect=etl_processor.ETLValidationError("Arquivo inválido", "data")), \
                patch.object(etl_processor, "calcular_kpis_em_memoria",
                             side_effect=AssertionError("não deve refazer")):
            self.assertFalse(self._processar().sucesso)

    def test_excluir_a_analise_remove_o_detalhamento_em_cascata(self):
        from models import Analise, IndicadorComplementarAnalise, ProdutoDesempenhoAnalise
        self.assertTrue(self._processar().sucesso)
        self.db.session.delete(self.db.session.get(Analise, self.analise_id))
        self.db.session.commit()
        self.assertEqual(self._contar(IndicadorComplementarAnalise), 0)
        self.assertEqual(self._contar(ProdutoDesempenhoAnalise), 0)

    def _migrar(self, funcao, revisao):
        self.db.session.remove()
        with patch("logging.config.fileConfig"), contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            funcao(directory=str(ROOT / "migrations"), revision=revisao)

    def test_downgrade_recusa_dados_e_remove_estruturas_vazias(self):
        from flask_migrate import downgrade, upgrade
        self.assertTrue(self._processar().sucesso)
        with self.assertLogs("flask_migrate", "ERROR") as registro, self.assertRaises(SystemExit):
            self._migrar(downgrade, "f4c2a8e1d9b6")
        self.assertIn("Downgrade do detalhamento por produto recusado", registro.output[0])
        self.assertEqual(self.db.session.scalar(text("SELECT version_num FROM alembic_version")), "5a9c3e7d1b42")
        self.db.session.execute(text("DELETE FROM produto_desempenho_analise"))
        self.db.session.execute(text("DELETE FROM indicador_complementar_analise"))
        self.db.session.commit()
        self._migrar(downgrade, "f4c2a8e1d9b6")
        tabelas = set(inspect(self.db.engine).get_table_names())
        self.assertFalse({"indicador_complementar_analise", "produto_desempenho_analise"} & tabelas)
        # Sem as tabelas o processamento segue o caminho anterior, sem erro.
        import detalhamento_produtos
        detalhamento_produtos.esquecer_esquema_detalhamento()
        self.assertTrue(self._processar().sucesso)
        self._migrar(upgrade, "head")
        self.assertEqual(self.db.session.scalar(text("SELECT version_num FROM alembic_version")), "5a9c3e7d1b42")

    def test_old_head_new_head_preserva_dados_existentes(self):
        from flask_migrate import downgrade, upgrade
        self._migrar(downgrade, "f4c2a8e1d9b6")
        # Dados pré-existentes gravados por SQL cru na revisão anterior.
        self.db.session.execute(text(
            "INSERT INTO indicador_analise (id_analise, faturamento_total, total_comprado, "
            "saldo_estimado_compras_vendas, versao_processamento, data_geracao) "
            "VALUES (:a, 100, 80, -20, 1, CURRENT_TIMESTAMP)"), {"a": self.analise_id})
        self.db.session.execute(text(
            "INSERT INTO produto_curva_abc (id_analise, posicao_ranking, produto_nome, faturamento, "
            "percentual_individual, percentual_acumulado, classe_abc, data_geracao) "
            "VALUES (:a, 1, 'Produto antigo', 100, 100, 100, 'A', CURRENT_TIMESTAMP)"), {"a": self.analise_id})
        self.db.session.commit()
        antes = {t: self.db.session.scalar(text(f"SELECT count(*) FROM {t}"))
                 for t in ("analise", "indicador_analise", "produto_curva_abc", "empresa", "usuario")}
        self._migrar(upgrade, "head")
        depois = {t: self.db.session.scalar(text(f"SELECT count(*) FROM {t}")) for t in antes}
        self.assertEqual(antes, depois)
        self.assertEqual(self.db.session.scalar(text("SELECT count(*) FROM produto_desempenho_analise")), 0)
        self.assertEqual(self.db.session.scalar(text("SELECT count(*) FROM indicador_complementar_analise")), 0)


if __name__ == "__main__":
    unittest.main()
