"""Data e hora de geração do PDF no horário oficial de Brasília (America/Sao_Paulo).

Da raiz: python -B -m unittest tests.test_pdf_export_horario -v
Sem banco, rede ou credenciais. O relógio é simulado substituindo
pdf_export._agora_utc (o único ponto de leitura do relógio); o fuso do processo
é trocado com TZ + time.tzset() e restaurado ao fim de cada uso. A conversão
vem do banco de fusos IANA (zoneinfo): nenhuma regra manual de horário de verão.
"""

import ast
import contextlib
import copy
from datetime import date, datetime, timedelta, timezone
import importlib.util
import inspect
import os
import re
import time
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
import zoneinfo
from zoneinfo import ZoneInfo

import pdf_export
from tests import pdf_layout_support as apoio

UTC = timezone.utc
CARIMBO = re.compile(r"Gerado em (\d{2}/\d{2}/\d{4} às \d{2}:\d{2}) \(horário de Brasília\)")
FRASE_FINAL = re.compile(r"Documento gerado pelo portal NEXO em (\d{2}/\d{2}/\d{4} às \d{2}:\d{2}) "
                         r"\(horário de Brasília\)\.")
# Fusos de processo bem diferentes entre si (inclusive outros fusos do Brasil e extremos).
FUSOS_DO_PROCESSO = ("UTC", "America/Sao_Paulo", "America/Manaus", "America/Noronha", "America/New_York",
                     "Europe/Lisbon", "Asia/Tokyo", "Pacific/Kiritimati", "Etc/GMT+12")
COM_TZSET = hasattr(time, "tzset")
COM_PDFTOTEXT = apoio.pdftotext_disponivel()


@contextlib.contextmanager
def fuso_do_processo(nome):
    """Executa o bloco como se o servidor estivesse configurado em outro fuso."""
    anterior = os.environ.get("TZ")
    os.environ["TZ"] = nome
    time.tzset()
    try:
        yield
    finally:
        if anterior is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = anterior
        time.tzset()


def relogio(*instantes):
    """Relógio simulado: cada leitura devolve o próximo instante (UTC, com fuso)."""
    return patch.object(pdf_export, "_agora_utc", side_effect=list(instantes))


def carimbos(documento):
    """Carimbos do rodapé (um por página) e o da frase final do documento."""
    conteudo = apoio.texto(documento)
    return CARIMBO.findall(conteudo), FRASE_FINAL.findall(conteudo)


class InstanteDeGeracaoTests(unittest.TestCase):
    """Conversão do instante: não depende de pdftotext."""

    @unittest.skipUnless(COM_TZSET, "time.tzset indisponível nesta plataforma")
    def test_01_servidor_em_utc_15h02_utc_vira_12h02_em_brasilia(self):
        with fuso_do_processo("UTC"), relogio(datetime(2026, 10, 29, 15, 2, tzinfo=UTC)):
            instante = pdf_export.instante_de_geracao()
        self.assertEqual(instante.tzinfo.key, "America/Sao_Paulo")
        self.assertEqual(instante.utcoffset(), timedelta(hours=-3))
        self.assertEqual(instante.replace(tzinfo=None), datetime(2026, 10, 29, 12, 2))
        self.assertEqual(pdf_export.formatar_data_hora(instante), "29/10/2026 às 12:02")

    def test_02_virada_do_dia_30_10_01h15_utc_ainda_e_29_10_22h15(self):
        with relogio(datetime(2026, 10, 30, 1, 15, tzinfo=UTC)):
            instante = pdf_export.instante_de_geracao()
        self.assertEqual(instante.date(), date(2026, 10, 29))
        self.assertEqual(pdf_export.formatar_data_hora(instante), "29/10/2026 às 22:15")

    @unittest.skipUnless(COM_TZSET, "time.tzset indisponível nesta plataforma")
    def test_03_fuso_configurado_no_processo_nao_altera_o_horario(self):
        referencia = datetime(2026, 10, 29, 15, 2, tzinfo=UTC)
        for nome in FUSOS_DO_PROCESSO:
            with self.subTest(fuso_do_processo=nome), fuso_do_processo(nome):
                # O fuso do processo mudou de fato (senão o teste não provaria nada).
                esperado = referencia.astimezone(ZoneInfo(nome)).strftime("%z")
                self.assertEqual(time.strftime("%z", time.localtime(referencia.timestamp())), esperado)
                with relogio(referencia):
                    simulado = pdf_export.instante_de_geracao()
                self.assertEqual(pdf_export.formatar_data_hora(simulado), "29/10/2026 às 12:02")
                # Relógio real: o mesmo instante absoluto, sempre expresso em Brasília.
                antes = datetime.now(UTC)
                real = pdf_export.instante_de_geracao()
                depois = datetime.now(UTC)
                self.assertEqual(real.tzinfo.key, "America/Sao_Paulo")
                self.assertTrue(antes <= real <= depois, (antes, real, depois))

    @unittest.skipUnless(COM_TZSET, "time.tzset indisponível nesta plataforma")
    def test_geracao_nao_altera_o_fuso_do_processo(self):
        # Brasília vem do ZoneInfo: gerar o PDF não troca o fuso do servidor (nem o
        # que os próximos processos e o próximo tzset() herdariam).
        with fuso_do_processo("Asia/Tokyo"):
            antes = (os.environ.get("TZ"), time.tzname, time.timezone, time.altzone)
            apoio.gerar(gerado_em=None)                          # relógio real
            self.assertEqual((os.environ.get("TZ"), time.tzname, time.timezone, time.altzone), antes)

    def test_04_cada_exportacao_le_o_relogio_de_novo(self):
        instantes = (datetime(2026, 10, 29, 15, 2, tzinfo=UTC), datetime(2026, 10, 29, 15, 7, 30, tzinfo=UTC),
                     datetime(2026, 10, 29, 18, 59, 59, tzinfo=UTC))
        with relogio(*instantes) as leitura:
            textos = [pdf_export.formatar_data_hora(pdf_export.instante_de_geracao()) for _ in instantes]
        self.assertEqual(leitura.call_count, 3)
        self.assertEqual(textos, ["29/10/2026 às 12:02", "29/10/2026 às 12:07", "29/10/2026 às 15:59"])
        # Relógio real: nenhuma leitura é reaproveitada entre exportações.
        with patch.object(pdf_export, "_agora_utc", wraps=pdf_export._agora_utc) as leitura:
            apoio.gerar(gerado_em=None)
            apoio.gerar(gerado_em=None)
        self.assertEqual(leitura.call_count, 2)

    def test_07_datas_historicas_e_horario_de_verao_pelo_banco_de_fusos(self):
        # O Brasil teve horário de verão até fev/2019 (abolido em 2019). As regras vêm do
        # banco de fusos IANA; o código não contém nenhuma regra manual.
        casos = (
            (datetime(2019, 1, 15, 15, 0, tzinfo=UTC), "15/01/2019 às 13:00", -2),   # em pleno verão 2018/2019
            (datetime(2018, 11, 4, 2, 59, tzinfo=UTC), "03/11/2018 às 23:59", -3),   # último minuto sem verão
            (datetime(2018, 11, 4, 3, 0, tzinfo=UTC), "04/11/2018 às 01:00", -2),    # 00:00 saltou para 01:00
            (datetime(2019, 2, 17, 1, 59, tzinfo=UTC), "16/02/2019 às 23:59", -2),   # último minuto de verão
            (datetime(2019, 2, 17, 2, 0, tzinfo=UTC), "16/02/2019 às 23:00", -3),    # 23:00 repetido
            (datetime(2019, 11, 3, 3, 0, tzinfo=UTC), "03/11/2019 às 00:00", -3),    # verão abolido: sem salto
            (datetime(2019, 12, 15, 15, 0, tzinfo=UTC), "15/12/2019 às 12:00", -3),
            (datetime(2026, 1, 15, 15, 0, tzinfo=UTC), "15/01/2026 às 12:00", -3),
            (datetime(2026, 12, 15, 15, 0, tzinfo=UTC), "15/12/2026 às 12:00", -3),
        )
        for instante, esperado, horas in casos:
            with self.subTest(instante=instante.isoformat()):
                local = pdf_export.instante_de_geracao(instante)
                self.assertEqual(pdf_export.formatar_data_hora(local), esperado)
                self.assertEqual(local.utcoffset(), timedelta(hours=horas))
                # Mesmo instante absoluto (comparado em UTC: na hora repetida, a PEP 495 torna
                # desiguais as comparações diretas entre fusos diferentes).
                self.assertEqual(local.astimezone(UTC), instante)

    def test_codigo_sem_deslocamento_fixo_nem_relogio_ingenuo(self):
        """Sem subtração de horas, sem relógio local e sem fuso colado à mão (análise do código-fonte)."""
        arvore = ast.parse(inspect.getsource(pdf_export))
        chamadas = [n for n in ast.walk(arvore) if isinstance(n, ast.Call)]
        proibidas = {"utcnow", "localtime", "mktime", "timedelta", "tzset", "today", "fromtimestamp", "utcfromtimestamp"}
        violacoes = [ast.unparse(c) for c in chamadas
                     if ast.unparse(c.func).rsplit(".", 1)[-1] in proibidas
                     or "tzinfo" in {k.arg for k in c.keywords}]
        self.assertEqual(violacoes, [])
        # Nem mudança no fuso do processo: o gerador não toca em os.environ nem em os.putenv.
        self.assertEqual([ast.unparse(n) for n in ast.walk(arvore)
                          if isinstance(n, ast.Attribute) and n.attr in ("environ", "putenv")], [])
        # Uma única leitura do relógio, e com fuso explícito.
        self.assertEqual([ast.unparse(c) for c in chamadas if ast.unparse(c.func).endswith(".now")],
                         ["datetime.now(timezone.utc)"])
        textos = [n.value for n in ast.walk(arvore) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        for deslocamento in ("-03:00", "-0300", "UTC-3", "GMT-3", "UTC-03", "GMT-03"):
            self.assertFalse(any(deslocamento in t for t in textos), deslocamento)
        self.assertEqual(pdf_export.FUSO_HORARIO_OFICIAL, "America/Sao_Paulo")
        self.assertEqual(pdf_export.fuso_brasilia().key, "America/Sao_Paulo")

    def test_instante_sem_fuso_e_recusado_e_outros_fusos_sao_convertidos(self):
        with self.assertRaises(ValueError):
            pdf_export.instante_de_geracao(datetime(2026, 10, 29, 15, 2))
        with relogio(datetime(2026, 10, 29, 15, 2)):          # relógio que devolvesse hora ingênua
            with self.assertRaises(ValueError):
                pdf_export.instante_de_geracao()
        for instante in (datetime(2026, 10, 30, 0, 2, tzinfo=ZoneInfo("Asia/Tokyo")),
                         datetime(2026, 10, 29, 11, 2, tzinfo=ZoneInfo("America/Manaus")),
                         datetime(2026, 10, 29, 12, 2, tzinfo=timezone(timedelta(hours=-3)))):
            with self.subTest(instante=instante.isoformat()):
                self.assertEqual(pdf_export.formatar_data_hora(pdf_export.instante_de_geracao(instante)),
                                 "29/10/2026 às 12:02")

    def test_formato_com_zeros_a_esquerda(self):
        local = pdf_export.instante_de_geracao(datetime(2027, 1, 5, 12, 5, tzinfo=UTC))
        self.assertEqual(pdf_export.formatar_data_hora(local), "05/01/2027 às 09:05")

    def test_formatacao_independe_da_localidade_do_servidor(self):
        # Localidade ASCII sem modo UTF-8: o "às" não passa pelo strftime.
        import subprocess
        import sys
        from pathlib import Path
        codigo = ("import sys, datetime as d, pdf_export as p; "
                  "t = p.formatar_data_hora(p.instante_de_geracao(d.datetime(2026, 10, 29, 15, 2, tzinfo=d.timezone.utc))); "
                  "sys.stdout.buffer.write(t.encode('utf-8'))")
        ambiente = {"PATH": os.environ.get("PATH", ""), "LC_ALL": "C", "PYTHONUTF8": "0",
                    "PYTHONCOERCECLOCALE": "0", "PYTHONDONTWRITEBYTECODE": "1"}
        resultado = subprocess.run([sys.executable, "-B", "-c", codigo], cwd=Path(pdf_export.__file__).resolve().parent,
                                   env=ambiente, capture_output=True, timeout=60)
        self.assertEqual(resultado.returncode, 0, resultado.stderr.decode("utf-8", "replace"))
        self.assertEqual(resultado.stdout.decode("utf-8"), "29/10/2026 às 12:02")

    def test_metadados_do_arquivo_usam_o_mesmo_instante_do_carimbo(self):
        fusos = ("UTC", "Asia/Kolkata", "America/New_York") if COM_TZSET else ("UTC",)
        for nome in fusos:
            contexto = fuso_do_processo(nome) if COM_TZSET else contextlib.nullcontext()
            with self.subTest(fuso_do_processo=nome), contexto:
                documento = apoio.gerar(gerado_em=datetime(2026, 10, 29, 15, 2, tzinfo=UTC))
                self.assertEqual(re.findall(rb"/(?:CreationDate|ModDate) \(([^)]*)\)", documento),
                                 [b"D:20261029120200-03'00'"] * 2)
        verao = apoio.gerar(gerado_em=datetime(2019, 1, 15, 15, 0, tzinfo=UTC))
        self.assertIn(b"/CreationDate (D:20190115130000-02'00')", verao)

    def test_funciona_sem_a_base_de_fusos_do_sistema_operacional(self):
        """Sem /usr/share/zoneinfo, o zoneinfo usa o pacote tzdata (dependência declarada)."""
        self.assertIsNotNone(importlib.util.find_spec("tzdata"), "tzdata é dependência declarada em requirements.txt")
        chave = pdf_export.FUSO_HORARIO_OFICIAL

        def recarregar():
            ZoneInfo.clear_cache(only_keys=[chave])
            pdf_export.fuso_brasilia.cache_clear()

        self.addCleanup(recarregar)
        self.addCleanup(zoneinfo.reset_tzpath)
        zoneinfo.reset_tzpath(to=[])
        recarregar()
        self.assertEqual(zoneinfo.TZPATH, ())
        local = pdf_export.instante_de_geracao(datetime(2026, 10, 29, 15, 2, tzinfo=UTC))
        self.assertEqual(pdf_export.formatar_data_hora(local), "29/10/2026 às 12:02")
        verao = pdf_export.instante_de_geracao(datetime(2019, 1, 15, 15, 0, tzinfo=UTC))
        self.assertEqual(pdf_export.formatar_data_hora(verao), "15/01/2019 às 13:00")


@unittest.skipUnless(COM_PDFTOTEXT, "pdftotext indisponível: texto do PDF não verificável")
class HorarioNoDocumentoTests(unittest.TestCase):
    """O horário impresso no PDF (rodapé de todas as páginas e frase final)."""

    @unittest.skipUnless(COM_TZSET, "time.tzset indisponível nesta plataforma")
    def test_01_pdf_gerado_em_servidor_utc_mostra_12h02(self):
        with fuso_do_processo("UTC"), relogio(datetime(2026, 10, 29, 15, 2, tzinfo=UTC)):
            documento = apoio.gerar(gerado_em=None)
        rodapes, final = carimbos(documento)
        self.assertEqual(final, ["29/10/2026 às 12:02"])
        self.assertTrue(rodapes)
        self.assertEqual(set(rodapes), {"29/10/2026 às 12:02"})
        self.assertNotIn("15:02", apoio.texto(documento))

    def test_02_virada_do_dia_no_documento(self):
        with relogio(datetime(2026, 10, 30, 1, 15, tzinfo=UTC)):
            documento = apoio.gerar(gerado_em=None)
        rodapes, final = carimbos(documento)
        self.assertEqual(final, ["29/10/2026 às 22:15"])
        self.assertEqual(set(rodapes), {"29/10/2026 às 22:15"})
        self.assertNotIn("30/10/2026", apoio.texto(documento))

    @unittest.skipUnless(COM_TZSET, "time.tzset indisponível nesta plataforma")
    def test_03_mesmo_documento_em_qualquer_fuso_do_processo(self):
        referencia = datetime(2026, 10, 29, 15, 2, tzinfo=UTC)
        textos = {}
        for nome in FUSOS_DO_PROCESSO:
            with self.subTest(fuso_do_processo=nome), fuso_do_processo(nome), relogio(referencia):
                documento = apoio.gerar(gerado_em=None)
                rodapes, final = carimbos(documento)
                self.assertEqual(final, ["29/10/2026 às 12:02"])
                self.assertEqual(set(rodapes), {"29/10/2026 às 12:02"})
                textos[nome] = apoio.texto(documento)
        self.assertEqual(len(set(textos.values())), 1, "o texto do PDF mudou com o fuso do processo")

    def test_04_exportacoes_sucessivas_tem_cada_uma_o_seu_horario(self):
        instantes = (datetime(2026, 10, 29, 15, 2, tzinfo=UTC), datetime(2026, 10, 29, 15, 7, 30, tzinfo=UTC),
                     datetime(2026, 10, 30, 2, 59, tzinfo=UTC))
        with relogio(*instantes) as leitura:
            documentos = [apoio.gerar(gerado_em=None) for _ in instantes]
        self.assertEqual(leitura.call_count, len(instantes))
        self.assertEqual([carimbos(d)[1] for d in documentos],
                         [["29/10/2026 às 12:02"], ["29/10/2026 às 12:07"], ["29/10/2026 às 23:59"]])

    def test_05_periodo_financeiro_e_valores_nao_mudam_com_o_horario(self):
        analise = apoio.analise_referencia()
        antes = copy.deepcopy(analise)
        textos = []
        # 01/07 01:30 UTC ainda é 30/06 em Brasília (e já é 01/07 no Japão): o período analisado
        # é uma data do calendário e não é convertido de fuso.
        for instante, nome in ((datetime(2026, 7, 1, 1, 30, tzinfo=UTC), "Asia/Tokyo"),
                               (datetime(2026, 10, 29, 15, 2, tzinfo=UTC), "UTC")):
            contexto = fuso_do_processo(nome) if COM_TZSET else contextlib.nullcontext()
            with contexto, relogio(instante):
                conteudo = apoio.texto(apoio.gerar(analise, gerado_em=None))
            self.assertIn("Período 01/06/2026 – 30/06/2026", conteudo)
            self.assertIn("Referência 06/2026", conteudo)
            textos.append(conteudo)
        self.assertEqual(analise, antes)
        self.assertEqual((analise.periodo_inicio, analise.periodo_fim), (date(2026, 6, 1), date(2026, 6, 30)))
        self.assertIn("30/06/2026 às 22:30", textos[0])
        self.assertIn("29/10/2026 às 12:02", textos[1])
        # Fora o carimbo de geração, os dois documentos são idênticos (valores, período, textos).
        neutros = [t.replace("30/06/2026 às 22:30", "#").replace("29/10/2026 às 12:02", "#") for t in textos]
        self.assertEqual(neutros[0], neutros[1])

    def test_06_horario_em_todas_as_paginas_com_uma_unica_leitura(self):
        frase = "Recomendamos acompanhar o giro do estoque e o prazo dos fornecedores antes de novas compras. "
        analise = apoio.analise_referencia(resumo=(frase * 12 + "\n\n") * 4, conclusao=(frase * 14 + "\n\n") * 5)
        with relogio(datetime(2026, 10, 29, 15, 2, tzinfo=UTC)) as leitura:
            documento = apoio.gerar(analise, gerado_em=None)
        self.assertEqual(leitura.call_count, 1)
        paginas = apoio.paginas(documento)
        self.assertGreaterEqual(len(paginas), 3)
        for numero, pagina in enumerate(paginas, start=1):
            rodape = " ".join(l["texto"] for l in apoio.linhas_do_rodape(pagina))
            with self.subTest(pagina=numero):
                self.assertIn("Gerado em 29/10/2026 às 12:02 (horário de Brasília)", rodape)
        rodapes, final = carimbos(documento)
        self.assertEqual(len(rodapes), len(paginas))
        self.assertEqual(final, ["29/10/2026 às 12:02"])


class RotaDeExportacaoHorarioTests(unittest.TestCase):
    """Rota real do portal (Flask-Login), banco e política contratual simulados."""

    def setUp(self):
        from flask import Flask
        from flask_login import LoginManager
        from blueprints import cliente
        import contract_policy

        self.analise = apoio.analise_referencia()
        self.analise.id_empresa = 42
        self.analise.status_analise = "CONCLUIDO"
        self.analise.relatorio.publicado = True
        self.analise.indicador.periodo_base_inicio = self.analise.indicador.periodo_base_fim = None
        self.usuario = SimpleNamespace(is_authenticated=True, is_active=True, is_anonymous=False, is_cliente=True,
                                       empresa=SimpleNamespace(id_empresa=42))
        self.app = Flask(__name__)
        self.app.config.update(SECRET_KEY="isolated-pdf-time-test-key", TESTING=True, DEBUG=False,
                               PROPAGATE_EXCEPTIONS=False)
        manager = LoginManager(self.app)
        manager.user_loader(lambda identifier: self.usuario if identifier == "1" else None)
        self.app.register_blueprint(cliente.cliente_bp, url_prefix="/cliente")
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session["_user_id"] = "1"
            session["_fresh"] = True
        pilha = contextlib.ExitStack()
        self.addCleanup(pilha.close)
        pilha.enter_context(patch.object(cliente, "db", SimpleNamespace(
            session=SimpleNamespace(get=MagicMock(return_value=self.analise)))))
        pilha.enter_context(patch.object(cliente, "gerar_semaforos", return_value=apoio.semaforos_referencia()))
        situacao = contract_policy.SituacaoContratual(
            id_empresa=42, regime=contract_policy.REGIME_LEGADO, estado=contract_policy.ESTADO_ATIVA,
            status_conta="ATIVA", instante=datetime(2026, 10, 29, 15, tzinfo=UTC),
        )
        pilha.enter_context(patch.object(cliente, "obter_situacao_contratual", side_effect=lambda empresa: situacao))

    def test_duas_exportacoes_seguidas_geram_documentos_novos_sem_cache(self):
        # Relógio único da requisição (contract_policy.agora), injetado como nos testes contratuais.
        leitura = MagicMock(side_effect=[datetime(2026, 10, 29, 15, 2, tzinfo=UTC),
                                         datetime(2026, 10, 29, 15, 9, tzinfo=UTC)])
        self.app.config["NEXO_RELOGIO"] = leitura
        respostas = [self.client.get("/cliente/analise/5/pdf") for _ in range(2)]
        self.assertEqual(leitura.call_count, 2)                  # uma leitura por exportação
        for resposta in respostas:
            self.assertEqual(resposta.status_code, 200)
            self.assertEqual(resposta.mimetype, "application/pdf")
            self.assertEqual(resposta.headers["Cache-Control"], "no-store")
            self.assertEqual(resposta.headers["X-Content-Type-Options"], "nosniff")
            self.assertEqual(resposta.headers["Content-Disposition"],
                             'attachment; filename="analise_nexo_202606_5.pdf"')
            self.assertNotIn("ETag", resposta.headers)
            self.assertNotIn("Last-Modified", resposta.headers)
        self.assertNotEqual(respostas[0].data, respostas[1].data)
        self.assertEqual(self.analise.indicador.faturamento_total, apoio.analise_referencia().indicador.faturamento_total)
        if COM_PDFTOTEXT:
            self.assertEqual(carimbos(respostas[0].data)[1], ["29/10/2026 às 12:02"])
            self.assertEqual(carimbos(respostas[1].data)[1], ["29/10/2026 às 12:09"])


if __name__ == "__main__":
    unittest.main()
