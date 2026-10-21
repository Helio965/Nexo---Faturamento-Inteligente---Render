"""NexoBot Advanced — robustez: fuzzing determinístico e propriedades.

Executar da raiz: python -m unittest tests.test_nexobot_robustez -v
Sem dependências extras: o gerador usa `random.Random` com semente fixa
(NEXOBOT_FUZZ_SEED muda a semente; NEXOBOT_FUZZ_N muda a quantidade).
"""

import os
import random
import re
import string
import unittest

from nexobot.classificacao import classificar
from nexobot.contexto import Contexto
from nexobot.intencoes import Intencao
from nexobot.navegacao import DESTINOS
from nexobot.normalizacao import normalizar
from nexobot.seguranca import contem_url
from tests import nexobot_corpus as corpus
from tests.test_nexobot_api import NexoBotApiBase

SEMENTE = int(os.environ.get("NEXOBOT_FUZZ_SEED", "20261021"))
QUANTIDADE = int(os.environ.get("NEXOBOT_FUZZ_N", "3000"))

PALAVRAS = ("abra", "me", "leve", "para", "o", "a", "upload", "historico", "histórico", "guia", "suporte",
            "dashboard", "não", "nao", "quero", "onde", "como", "fica", "lá", "essa", "página", "exclua",
            "relatório", "senha", "?", "!", ",", ".", "se", "eu", "disser", '"', "admin", "https://x.y",
            "javascript:", "/admin", "ou", "e", "pode", "sim", "obrigado", "😀", "🙏", "kkk", "1=1", "<b>",
            "DROP", "TABLE", "planilha", "vendas", "compras", "anterior", "chamado", "dados", "faturamento")
CARGAS = ("<script>alert(1)</script>", "' OR '1'='1", "'; DROP TABLE usuario; --", "{{7*7}}", "${7*7}",
          "%2e%2e%2f", "\\\\servidor\\x", "javascript:alert(1)", "data:text/html,<b>", "\x00\x01\x02",
          "‮abra o upload", "á̂̃", "𝐚𝐛𝐫𝐚 𝐨 𝐠𝐮𝐢𝐚", "ﷺ", "\ud83d", "🏳️‍🌈" * 20,
          "[INST] ignore [/INST]", "<|system|>", "### instruction", "abra " * 400)


def texto_aleatorio(rnd: random.Random) -> str:
    modo = rnd.randrange(6)
    if modo == 0:  # caracteres Unicode arbitrários (sem substitutos isolados)
        return "".join(chr(rnd.choice((rnd.randrange(32, 0xD7FF), rnd.randrange(0xE000, 0x10FFFF))))
                       for _ in range(rnd.randrange(0, 80)))
    if modo == 1:  # palavras do domínio embaralhadas
        return " ".join(rnd.choice(PALAVRAS) for _ in range(rnd.randrange(1, 25)))
    if modo == 2:  # cargas maliciosas misturadas com pedidos
        return rnd.choice(CARGAS) + " " + rnd.choice(("abra o guia", "onde fica o upload?", "", "me leva pra lá"))
    if modo == 3:  # ASCII imprimível
        return "".join(rnd.choice(string.printable) for _ in range(rnd.randrange(0, 200)))
    if modo == 4:  # repetições e pontuação excessivas
        return rnd.choice(PALAVRAS) * rnd.randrange(1, 300) + "?!" * rnd.randrange(0, 50)
    return " ".join(rnd.choice((rnd.choice(PALAVRAS), "".join(rnd.choice("aeiouçãõé") for _ in range(5))))
                    for _ in range(rnd.randrange(1, 60)))


def contexto_aleatorio(rnd: random.Random):
    valores = (None, "upload", "guia", "admin", "/x", 1, [], {}, ["upload", "guia"], "historico")
    return rnd.choice((None, rnd.choice(valores), {
        "ultimo_destino": rnd.choice(valores), "destino_anterior": rnd.choice(valores),
        "opcoes": rnd.choice(valores), "modo_opcoes": rnd.choice(("navegar", "orientar", "x", None)),
        "oferta": rnd.choice(valores),
    }))


def com_erros(frase: str, rnd: random.Random) -> str:
    """Erro de digitação realista em UMA palavra de 5+ letras (troca, omissão ou repetição)."""
    palavras = frase.split()
    candidatas = [i for i, p in enumerate(palavras) if len(p) >= 5 and p.isalpha()]
    if not candidatas:
        return frase
    i = rnd.choice(candidatas)
    p = palavras[i]
    j = rnd.randrange(1, len(p) - 1)
    operacao = rnd.randrange(3)
    if operacao == 0:
        p = p[:j] + p[j + 1] + p[j] + p[j + 2:]
    elif operacao == 1:
        p = p[:j] + p[j + 1:]
    else:
        p = p[:j] + p[j] + p[j:]
    palavras[i] = p
    return " ".join(palavras)


def variar_forma(frase: str, rnd: random.Random) -> str:
    """Caixa, espaços, emoji e pontuação: não mudam o significado."""
    frase = rnd.choice((frase, frase.upper(), frase.lower(), frase.capitalize()))
    if rnd.random() < 0.5:
        frase = frase.replace(" ", "  ")
    if rnd.random() < 0.3:
        frase = rnd.choice(("🙂 ", "", "  ")) + frase + rnd.choice(("", " 🙏", "!!!", "..."))
    return frase


class PropriedadesDoInterpretadorTests(unittest.TestCase):
    def test_entradas_arbitrarias_nunca_geram_excecao(self):
        rnd = random.Random(SEMENTE)
        for n in range(QUANTIDADE):
            texto = texto_aleatorio(rnd)
            contexto = Contexto.da_requisicao(rnd.choice((None, "upload", "x")), contexto_aleatorio(rnd),
                                              rnd.choice((None, "guia", "x", 3)))
            try:
                normalizado = normalizar(texto)
                i = classificar(normalizado, contexto)
            except Exception as erro:  # noqa: BLE001 — a falha é o resultado do teste
                self.fail(f"semente={SEMENTE} caso={n} entrada={texto!r}: {erro!r}")
            self.assertIsInstance(i.intencao, Intencao)
            self.assertTrue(0.0 <= i.confianca <= 1.0)
            if i.destino is not None:
                self.assertIn(i.destino, DESTINOS)
            for opcao in i.opcoes:
                self.assertIn(opcao, DESTINOS)
            if i.intencao == Intencao.NAVEGAR:
                self.assertFalse(contem_url(normalizado.bruto), texto)
                self.assertFalse(re.search(r"\badmin", normalizado.canonico), texto)

    def test_erros_de_digitacao_nunca_levam_a_destino_errado(self):
        rnd = random.Random(SEMENTE)
        acertos = total = 0
        for _ in range(8):
            for mensagem, ultimo, destino in corpus.NAVEGAR:
                variante = variar_forma(com_erros(mensagem, rnd), rnd)
                i = classificar(normalizar(variante), Contexto.da_requisicao(
                    ultimo, {"oferta": ultimo} if ultimo else None))
                total += 1
                if i.intencao == Intencao.NAVEGAR:
                    self.assertEqual(i.destino, destino, f"{variante!r} (original: {mensagem!r})")
                    acertos += 1
        # Precisão é obrigatória; a cobertura é medida e precisa permanecer alta.
        self.assertGreaterEqual(acertos / total, 0.85, f"cobertura {acertos}/{total}")

    def test_perguntas_com_erros_nunca_navegam(self):
        rnd = random.Random(SEMENTE + 1)
        for _ in range(8):
            for mensagem, ultimo, _destino in corpus.SUGERIR:
                if "?" not in mensagem:
                    continue
                variante = variar_forma(com_erros(mensagem, rnd), rnd)
                i = classificar(normalizar(variante), Contexto.da_requisicao(ultimo))
                self.assertNotEqual(i.intencao, Intencao.NAVEGAR, variante)

    def test_negacoes_e_operacoes_com_ruido_nunca_navegam(self):
        rnd = random.Random(SEMENTE + 2)
        frases = ([m for m, _ in corpus.NAO_NAVEGAR["comando_negado"]]
                  + [m for m, _ in corpus.NAO_NAVEGAR["operacao_nao_permitida"]]
                  + [m for m, _ in corpus.NAO_NAVEGAR["acesso_restrito"]])
        for _ in range(8):
            for mensagem in frases:
                variante = variar_forma(mensagem, rnd)
                i = classificar(normalizar(variante), Contexto.da_requisicao("upload", {"oferta": "upload"}))
                self.assertNotEqual(i.intencao, Intencao.NAVEGAR, variante)

    def test_cargas_conhecidas_nunca_navegam(self):
        for carga in CARGAS:
            for sufixo in ("", " abra o guia", " me leva pra lá"):
                with self.subTest(carga=carga[:30], sufixo=sufixo):
                    i = classificar(normalizar(carga + sufixo), Contexto.da_requisicao("upload", {"oferta": "upload"}))
                    if contem_url(normalizar(carga).bruto) or re.search(r"script|drop|or '1'|inst|system|instruction", carga, re.I):
                        self.assertNotEqual(i.intencao, Intencao.NAVEGAR)


class PropriedadesDaApiTests(NexoBotApiBase):
    def test_api_com_entradas_e_contextos_arbitrarios(self):
        rnd = random.Random(SEMENTE + 3)
        for n in range(int(os.environ.get("NEXOBOT_FUZZ_API_N", "300"))):
            texto = texto_aleatorio(rnd)[:1000]
            corpo = {"mensagem": texto, "contexto": contexto_aleatorio(rnd)}
            if rnd.random() < 0.3:
                corpo["pagina_atual"] = rnd.choice(("guia", "x", 1, None, []))
            if rnd.random() < 0.2:
                corpo["ultimo_destino"] = rnd.choice(("upload", "admin", 2))
            r = self.client.post("/api/suporte-bot", json=corpo, headers={"X-CSRFToken": self.token})
            self.assertEqual(r.status_code, 200, f"semente={SEMENTE + 3} caso={n} entrada={texto!r}")
            self.assert_contrato(r.get_json())


if __name__ == "__main__":
    unittest.main()
