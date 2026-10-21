"""NexoBot Advanced — desempenho medido (latência e memória).

Executar da raiz: python -m unittest tests.test_nexobot_desempenho -v
Os limites são folgados para não depender da máquina de CI; os valores
medidos são impressos para registro (ver Docs/NEXOBOT_ADVANCED.md).
"""

import random
import statistics
import time
import tracemalloc
import unittest

from nexobot.classificacao import classificar
from nexobot.contexto import Contexto
from nexobot.normalizacao import corrigir_palavra, normalizar
from nexobot.similaridade import radical
from tests import nexobot_corpus as corpus
from tests.test_nexobot_api import NexoBotApiBase
from tests.test_nexobot_robustez import texto_aleatorio


def frases():
    return ([m for m, _, _ in corpus.NAVEGAR] + [m for m, _, _ in corpus.SUGERIR]
            + [m for casos in corpus.NAO_NAVEGAR.values() for m, _ in casos]
            + [m for m, _ in corpus.PERGUNTAS_FUNCIONAIS])


def percentis(amostras_ms):
    ordenadas = sorted(amostras_ms)
    p95 = ordenadas[int(len(ordenadas) * 0.95) - 1]
    return statistics.median(ordenadas), p95, ordenadas[-1]


class InterpretadorDesempenhoTests(unittest.TestCase):
    def test_latencia_da_classificacao_local(self):
        mensagens = frases()
        for m in mensagens:  # aquece caches de correção
            classificar(normalizar(m), Contexto())
        amostras = []
        for _ in range(5):
            for m in mensagens:
                inicio = time.perf_counter()
                classificar(normalizar(m), Contexto.da_requisicao("upload"))
                amostras.append((time.perf_counter() - inicio) * 1000)
        p50, p95, maximo = percentis(amostras)
        print(f"\n[desempenho] classificação local: n={len(amostras)} p50={p50:.2f}ms p95={p95:.2f}ms max={maximo:.2f}ms")
        self.assertLess(p95, 30.0)

    def test_pior_caso_mensagem_longa(self):
        mensagem = ("me leve para a página de controle de estoque físico, por favor, " * 30)[:1000]
        inicio = time.perf_counter()
        for _ in range(20):
            classificar(normalizar(mensagem), Contexto())
        media = (time.perf_counter() - inicio) / 20 * 1000
        print(f"\n[desempenho] mensagem de 1000 caracteres: média={media:.2f}ms")
        self.assertLess(media, 200.0)

    def test_memoria_limitada_com_entradas_unicas(self):
        rnd = random.Random(7)
        tracemalloc.start()
        try:
            for _ in range(300):
                classificar(normalizar(texto_aleatorio(rnd)), Contexto())
            antes, _ = tracemalloc.get_traced_memory()
            for _ in range(3000):
                classificar(normalizar(texto_aleatorio(rnd)), Contexto())
            depois, pico = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        crescimento = (depois - antes) / 1024 / 1024
        print(f"\n[desempenho] memória após 3000 mensagens únicas: crescimento={crescimento:.2f}MB pico={pico/1024/1024:.2f}MB")
        # Caches LRU têm tamanho máximo: o crescimento não acompanha o volume de mensagens.
        self.assertLess(crescimento, 16.0)
        self.assertIsNotNone(corrigir_palavra.cache_info().maxsize)
        self.assertIsNotNone(radical.cache_info().maxsize)


class RespostaCompletaDesempenhoTests(NexoBotApiBase):
    def test_latencia_do_servico_com_guia_em_cache(self):
        from nexobot import responder
        mensagens = frases()
        with self.app.test_request_context():
            responder("oi")
            amostras = []
            for m in mensagens * 3:
                inicio = time.perf_counter()
                responder(m, contexto={"ultimo_destino": "upload"})
                amostras.append((time.perf_counter() - inicio) * 1000)
        p50, p95, maximo = percentis(amostras)
        print(f"\n[desempenho] resposta completa (Guia em cache): n={len(amostras)} "
              f"p50={p50:.2f}ms p95={p95:.2f}ms max={maximo:.2f}ms")
        self.assertLess(p95, 80.0)

    def test_latencia_http_ponta_a_ponta(self):
        amostras = []
        for m in frases()[:60]:
            inicio = time.perf_counter()
            self.assertEqual(self.post(m).status_code, 200)
            amostras.append((time.perf_counter() - inicio) * 1000)
        p50, p95, maximo = percentis(amostras)
        print(f"\n[desempenho] HTTP (cliente de teste Flask, SQLite): n={len(amostras)} "
              f"p50={p50:.2f}ms p95={p95:.2f}ms max={maximo:.2f}ms")
        self.assertLess(p95, 250.0)

    def test_reconstrucao_do_indice(self):
        from nexobot import conhecimento
        with self.app.test_request_context():
            inicio = time.perf_counter()
            for _ in range(10):
                conhecimento.invalidar()
                conhecimento.obter_base()
            media = (time.perf_counter() - inicio) / 10 * 1000
        print(f"\n[desempenho] reconstrução do índice (Guia do seed + fatos): média={media:.2f}ms")
        self.assertLess(media, 200.0)


if __name__ == "__main__":
    unittest.main()
