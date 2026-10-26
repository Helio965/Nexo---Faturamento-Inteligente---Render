"""Gestão contratual: aritmética de prazos e coberturas, sem banco e sem esperas.

Relógio sempre explícito ou injetado (NEXO_RELOGIO). Cobre meses com tamanhos
diferentes, virada de ano, anos bissextos, fusos e o instante exato do limite.
"""

import unittest
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from flask import Flask

import contract_policy as politica
from contract_policy import (
    PoliticaPrazos, calcular_limite_exportacao_pdf, calcular_limite_suspensao, periodo_analise,
    periodo_coberto, somar_dias_corridos, somar_meses_calendario, unir_intervalos, utc,
)

SP = ZoneInfo("America/Sao_Paulo")
NY = ZoneInfo("America/New_York")
UTC = timezone.utc


def local(*partes, fuso=SP):
    return datetime(*partes, tzinfo=fuso)


class MesesDeCalendarioTests(unittest.TestCase):
    def test_mesmo_dia_e_hora_locais(self):
        inicio = local(2026, 10, 15, 14, 30)
        self.assertEqual(somar_meses_calendario(inicio, 3, SP), local(2027, 1, 15, 14, 30))

    def test_fim_de_mes_usa_ultimo_dia_do_mes_curto(self):
        self.assertEqual(somar_meses_calendario(local(2027, 1, 31, 9), 1, SP), local(2027, 2, 28, 9))
        self.assertEqual(somar_meses_calendario(local(2026, 3, 31, 9), 3, SP), local(2026, 6, 30, 9))
        self.assertEqual(somar_meses_calendario(local(2026, 8, 31, 9), 3, SP), local(2026, 11, 30, 9))

    def test_31_de_janeiro_em_ano_bissexto_chega_a_29_de_fevereiro(self):
        self.assertEqual(somar_meses_calendario(local(2028, 1, 31, 9), 1, SP), local(2028, 2, 29, 9))
        self.assertEqual(somar_meses_calendario(local(2028, 1, 31, 9), 2, SP), local(2028, 3, 31, 9))

    def test_ano_bissexto(self):
        self.assertEqual(somar_meses_calendario(local(2027, 11, 30, 8), 3, SP), local(2028, 2, 29, 8))
        self.assertEqual(somar_meses_calendario(local(2028, 2, 29, 8), 3, SP), local(2028, 5, 29, 8))
        self.assertEqual(somar_meses_calendario(local(2028, 2, 29, 8), 12, SP), local(2029, 2, 28, 8))

    def test_virada_de_ano(self):
        self.assertEqual(somar_meses_calendario(local(2026, 12, 15, 10), 3, SP), local(2027, 3, 15, 10))
        self.assertEqual(somar_meses_calendario(local(2026, 11, 1, 0), 2, SP), local(2027, 1, 1, 0))

    def test_tres_meses_nao_sao_noventa_dias(self):
        inicio = local(2026, 3, 1, 12)
        limite = calcular_limite_suspensao(inicio, None, PoliticaPrazos(3, 14, SP))
        self.assertEqual(limite, local(2026, 6, 1, 12))
        self.assertEqual((limite - inicio).days, 92)
        self.assertNotEqual(limite, inicio + timedelta(days=90))

    def test_contagem_no_fuso_da_politica_e_nao_em_utc(self):
        # 31/01 23:30 em São Paulo já é 01/02 em UTC: o mês somado é o local.
        inicio = local(2026, 1, 31, 23, 30)
        self.assertEqual(inicio.astimezone(UTC).day, 1)
        limite = somar_meses_calendario(inicio, 1, SP)
        self.assertEqual(limite, local(2026, 2, 28, 23, 30))
        self.assertEqual(limite.tzinfo, UTC)

    def test_horario_de_verao_preserva_hora_local(self):
        # Nova York muda para horário de verão em 08/03/2026.
        inicio = local(2026, 2, 8, 10, fuso=NY)
        limite = somar_meses_calendario(inicio, 1, NY)
        self.assertEqual(limite.astimezone(NY).hour, 10)
        self.assertEqual(limite, datetime(2026, 3, 8, 14, tzinfo=UTC))  # 10h EDT

    def test_horario_local_inexistente_nao_recua_o_limite(self):
        inicio = local(2026, 2, 8, 2, 30, fuso=NY)  # 08/03 02:30 não existe em NY
        limite = somar_meses_calendario(inicio, 1, NY)
        self.assertGreaterEqual(limite, datetime(2026, 3, 8, 7, 0, tzinfo=UTC))

    def test_meses_fora_do_intervalo_falham(self):
        with self.assertRaises(ValueError):
            calcular_limite_suspensao(local(2026, 1, 1), 0, PoliticaPrazos(3, 14, SP))
        with self.assertRaises(ValueError):
            calcular_limite_suspensao(local(2026, 1, 1), True, PoliticaPrazos(3, 14, SP))


class DiasCorridosTests(unittest.TestCase):
    def setUp(self):
        self.politica = PoliticaPrazos(3, 14, SP)
        self.inicio = local(2026, 10, 26, 15, 45)

    def test_quatorze_dias_corridos(self):
        limite_suspensao = calcular_limite_suspensao(self.inicio, None, self.politica)
        limite_pdf = calcular_limite_exportacao_pdf(self.inicio, limite_suspensao, self.politica)
        self.assertEqual(limite_pdf, local(2026, 11, 9, 15, 45))

    def test_quatorze_dias_atravessando_fim_de_ano_e_bissexto(self):
        self.assertEqual(somar_dias_corridos(local(2026, 12, 25, 8), 14, SP), local(2027, 1, 8, 8))
        self.assertEqual(somar_dias_corridos(local(2028, 2, 20, 8), 14, SP), local(2028, 3, 5, 8))

    def test_prazo_de_pdf_nunca_ultrapassa_a_suspensao(self):
        curta = PoliticaPrazos(1, 45, SP)
        limite = calcular_limite_suspensao(self.inicio, None, curta)
        self.assertEqual(calcular_limite_exportacao_pdf(self.inicio, limite, curta), limite)


class LimiteExatoTests(unittest.TestCase):
    """Prazo encerrado ao ATINGIR o instante-limite (limite exclusivo)."""

    def _situacao(self, instante, limite, pdf):
        return politica.SituacaoContratual(
            id_empresa=1, regime=politica.REGIME_CONTRATUAL, estado=politica.ESTADO_SUSPENSA,
            status_conta="SUSPENSA", instante=instante, suspensao_limite=limite, pdf_limite=pdf,
        )

    def test_pdf_antes_no_instante_e_depois(self):
        limite = local(2027, 1, 26, 15, 45)
        pdf = local(2026, 11, 9, 15, 45)
        um = timedelta(microseconds=1)
        self.assertTrue(self._situacao(pdf - um, limite, pdf).exportacao_pdf_aberta)
        self.assertFalse(self._situacao(pdf, limite, pdf).exportacao_pdf_aberta)
        self.assertFalse(self._situacao(pdf + timedelta(days=1), limite, pdf).exportacao_pdf_aberta)


class IntervalosPagosTests(unittest.TestCase):
    def test_consecutivos_se_unem_e_lacunas_nao(self):
        unidos = unir_intervalos([
            (date(2026, 2, 1), date(2026, 2, 28)), (date(2026, 1, 1), date(2026, 1, 31)),
            (date(2026, 3, 2), date(2026, 3, 31)),
        ])
        self.assertEqual(unidos, ((date(2026, 1, 1), date(2026, 2, 28)),
                                  (date(2026, 3, 2), date(2026, 3, 31))))

    def test_sobrepostos_e_invalidos(self):
        unidos = unir_intervalos([
            (date(2026, 1, 1), date(2026, 1, 20)), (date(2026, 1, 10), date(2026, 2, 5)),
            (date(2026, 5, 10), date(2026, 5, 1)), (None, date(2026, 6, 1)),
        ])
        self.assertEqual(unidos, ((date(2026, 1, 1), date(2026, 2, 5)),))

    def test_cobertura_total_parcial_e_lacuna(self):
        unidos = unir_intervalos([(date(2026, 1, 1), date(2026, 2, 28)),
                                  (date(2026, 3, 2), date(2026, 3, 31))])
        self.assertTrue(periodo_coberto(date(2026, 1, 1), date(2026, 1, 31), unidos))
        self.assertTrue(periodo_coberto(date(2026, 1, 15), date(2026, 2, 14), unidos))  # consecutivos
        self.assertFalse(periodo_coberto(date(2025, 12, 31), date(2026, 1, 31), unidos))  # início fora
        self.assertFalse(periodo_coberto(date(2026, 2, 15), date(2026, 3, 15), unidos))  # atravessa lacuna
        self.assertFalse(periodo_coberto(date(2026, 4, 1), date(2026, 4, 30), unidos))  # não pago
        self.assertFalse(periodo_coberto(None, date(2026, 1, 31), unidos))
        self.assertFalse(periodo_coberto(date(2026, 1, 31), date(2026, 1, 1), unidos))
        self.assertFalse(periodo_coberto(date(2026, 1, 1), date(2026, 1, 31), ()))

    def test_periodo_real_da_base_amplia_o_exigido(self):
        indicador = SimpleNamespace(periodo_base_inicio=date(2025, 12, 28), periodo_base_fim=date(2026, 2, 2))
        analise = SimpleNamespace(periodo_inicio=date(2026, 1, 1), periodo_fim=date(2026, 1, 31),
                                  indicador=indicador)
        self.assertEqual(periodo_analise(analise), (date(2025, 12, 28), date(2026, 2, 2)))
        analise.indicador = SimpleNamespace(periodo_base_inicio=date(2026, 1, 5), periodo_base_fim=None)
        self.assertEqual(periodo_analise(analise), (date(2026, 1, 1), date(2026, 1, 31)))


class RelogioEParametrosTests(unittest.TestCase):
    def test_instante_sem_fuso_e_recusado(self):
        with self.assertRaises(ValueError):
            utc(datetime(2026, 1, 1, 10))
        with self.assertRaises(ValueError):
            somar_meses_calendario(datetime(2026, 1, 1, 10), 1, SP)

    def test_relogio_injetado_e_fixo_na_requisicao(self):
        app = Flask(__name__)
        instantes = iter([datetime(2026, 5, 1, 12, tzinfo=UTC), datetime(2026, 5, 2, 12, tzinfo=UTC)])
        app.config["NEXO_RELOGIO"] = lambda: next(instantes)
        with app.test_request_context("/"):
            primeiro = politica.agora()
            self.assertEqual(politica.agora(), primeiro)  # mesmo instante na requisição
        with app.test_request_context("/"):
            self.assertEqual(politica.agora(), datetime(2026, 5, 2, 12, tzinfo=UTC))

    def test_relogio_injetado_sem_fuso_e_recusado(self):
        app = Flask(__name__)
        app.config["NEXO_RELOGIO"] = lambda: datetime(2026, 5, 1, 12)
        with app.app_context(), self.assertRaises(ValueError):
            politica.agora()

    def test_parametros_invalidos_falham_alto(self):
        for chave, valor in (("CONTRATO_SUSPENSAO_MESES", 0), ("CONTRATO_SUSPENSAO_MESES", "3"),
                             ("CONTRATO_EXPORTACAO_PDF_DIAS", 0), ("CONTRATO_SUSPENSAO_MESES", 13)):
            with self.subTest(chave=chave, valor=valor), self.assertRaises(ValueError):
                politica.politica_prazos({chave: valor})
        padrao = politica.politica_prazos({})
        self.assertEqual((padrao.meses_suspensao, padrao.dias_exportacao_pdf, padrao.fuso.key),
                         (3, 14, "America/Sao_Paulo"))

    def test_configuracao_do_projeto_usa_a_proposta_documentada(self):
        from config import Config
        self.assertEqual(Config.CONTRATO_SUSPENSAO_MESES, 3)
        self.assertEqual(Config.CONTRATO_EXPORTACAO_PDF_DIAS, 14)
        self.assertEqual(Config.CONTRATO_FUSO_HORARIO, "America/Sao_Paulo")


if __name__ == "__main__":
    unittest.main()
