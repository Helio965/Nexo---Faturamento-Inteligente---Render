"""NexoBot Advanced — compreensão de linguagem (sem banco, sem rede).

Executar da raiz: python -m unittest tests.test_nexobot_linguagem -v
Verifica separadamente: normalização, classificação de intenções, recusa de
interpretações incertas, ausência de navegação indevida e contexto.
"""

import unittest

from nexobot.classificacao import classificar
from nexobot.contexto import Contexto
from nexobot.intencoes import Intencao
from nexobot.normalizacao import LIMITE_CARACTERES, normalizar
from tests import nexobot_corpus as corpus


def interpretar(mensagem, ultimo=None, oferta=None, **contexto):
    dados = dict(contexto)
    if oferta:
        dados["oferta"] = oferta
    return classificar(normalizar(mensagem), Contexto.da_requisicao(ultimo, dados or None))


class NormalizacaoTests(unittest.TestCase):
    def test_entradas_nao_textuais_viram_mensagem_vazia(self):
        for valor in (None, 123, 4.5, [], {}, ("a",), b"bytes", object()):
            with self.subTest(valor=type(valor).__name__):
                n = normalizar(valor)
                self.assertTrue(n.vazio)
                self.assertEqual(n.tokens, ())

    def test_acentos_caixa_espacos_e_pontuacao(self):
        n = normalizar("  ONDE   fica o   HISTÓRICO?!  ")
        self.assertEqual(n.canonico, "onde fica o historico ?")
        self.assertTrue(n.pergunta)

    def test_abreviacoes_de_chat(self):
        self.assertEqual(normalizar("vc pode me levar pro upload pfv").canonico,
                         "voce pode me levar para o upload por favor")
        self.assertEqual(normalizar("oq eh isso").canonico, "o que eh isso")

    def test_erros_de_digitacao_corrigidos_para_o_dominio(self):
        for digitado, esperado in (
            ("uplod", "upload"), ("dashbord", "dashboard"), ("chamdos", "chamados"),
            ("hsitorico", "historico"), ("istorico", "historico"), ("suprote", "suporte"),
            ("relatorrio", "relatorio"), ("guai", "guia"),
        ):
            with self.subTest(digitado=digitado):
                self.assertEqual(normalizar(digitado).canonico, esperado)

    def test_palavras_comuns_nao_sao_corrigidas_para_o_dominio(self):
        for palavra in ("obra", "papel", "expressao", "historias", "comprar", "consultar",
                        "ajudar", "porta", "vela", "investimentos"):
            with self.subTest(palavra=palavra):
                self.assertEqual(normalizar(palavra).canonico, palavra)

    def test_repeticoes_e_risadas(self):
        self.assertEqual(normalizar("oiiiii").canonico, "oi")
        self.assertEqual(normalizar("historicoooo").canonico, "historico")
        self.assertEqual(normalizar("isso").canonico, "isso")
        self.assertTrue(normalizar("kkkkkkk").so_simbolos)

    def test_emojis_e_simbolos(self):
        self.assertTrue(normalizar("😀😀😀").so_simbolos)
        self.assertTrue(normalizar("😀").tem_emoji)
        n = normalizar("😀 onde fica o upload? 🙏")
        self.assertFalse(n.so_simbolos)
        self.assertEqual(n.canonico, "onde fica o upload ?")

    def test_caracteres_invisiveis_e_unicode_incomum(self):
        n = normalizar("ab​ra o‮ his\x00tórico﻿")
        self.assertNotIn("​", n.bruto)
        self.assertNotIn("\x00", n.bruto)
        # Largura total (fullwidth) é normalizada por NFKC.
        self.assertEqual(normalizar("ＡＢＲＡ ｏ ｇｕｉａ").canonico, "abra o guia")

    def test_limite_defensivo_de_tamanho(self):
        n = normalizar("abra o guia " * 500)
        self.assertTrue(n.truncado)
        self.assertLessEqual(len(n.original), LIMITE_CARACTERES)

    def test_trechos_entre_aspas_sao_marcados(self):
        n = normalizar('Se eu disser "abra o histórico", funciona?')
        citados = [n.tokens[i] for i in sorted(n.citados)]
        self.assertEqual(citados, ["abra", "o", "historico"])
        # Aspas sem fechamento não comprovam citação.
        self.assertFalse(normalizar('abra "o histórico').citados)

    def test_verbo_e_nao_se_confunde_com_conjuncao(self):
        self.assertEqual(normalizar("O que é isso e aquilo").canonico, "o que eh isso e aquilo")


class ClassificacaoCorpusTests(unittest.TestCase):
    def test_ordens_inequivocas_navegam(self):
        for mensagem, ultimo, destino in corpus.NAVEGAR:
            with self.subTest(mensagem=mensagem, contexto=ultimo):
                i = interpretar(mensagem, ultimo, oferta=ultimo)
                self.assertEqual(i.intencao, Intencao.NAVEGAR, i.motivo)
                self.assertEqual(i.destino, destino)

    def test_perguntas_e_desejos_sugerem_sem_navegar(self):
        for mensagem, ultimo, destino in corpus.SUGERIR:
            with self.subTest(mensagem=mensagem, contexto=ultimo):
                i = interpretar(mensagem, ultimo)
                self.assertNotEqual(i.intencao, Intencao.NAVEGAR)
                self.assertEqual(i.destino, destino)

    def test_intencoes_sem_navegacao(self):
        for intencao, casos in corpus.NAO_NAVEGAR.items():
            for mensagem, ultimo in casos:
                with self.subTest(intencao=intencao, mensagem=mensagem, contexto=ultimo):
                    i = interpretar(mensagem, ultimo, oferta=ultimo)
                    self.assertEqual(i.intencao.value, intencao, i.motivo)

    def test_confianca_entre_zero_e_um(self):
        todas = ([m for m, _, _ in corpus.NAVEGAR] + [m for m, _, _ in corpus.SUGERIR]
                 + [m for casos in corpus.NAO_NAVEGAR.values() for m, _ in casos])
        for mensagem in todas:
            with self.subTest(mensagem=mensagem):
                self.assertTrue(0.0 <= interpretar(mensagem).confianca <= 1.0)


class RegrasObrigatoriasTests(unittest.TestCase):
    """As dez regras de navegação do pedido, uma a uma."""

    def test_regra_1_comando_explicito(self):
        i = interpretar("Abra meu histórico.")
        self.assertEqual((i.intencao, i.destino), (Intencao.NAVEGAR, "historico"))

    def test_regra_2_pergunta_informativa_nao_redireciona(self):
        i = interpretar("Onde fica meu histórico?")
        self.assertEqual((i.intencao, i.destino), (Intencao.ORIENTACAO_NAVEGACAO, "historico"))

    def test_regra_3_contexto_somente_se_valido(self):
        self.assertEqual(interpretar("Me leve para aquela página.", "guia").destino, "guia")
        self.assertEqual(interpretar("Me leve para aquela página.").intencao, Intencao.AMBIGUIDADE)
        for invalido in ("admin", "/cliente/upload", "https://example.com", "javascript:alert(1)", 123, ["upload"]):
            with self.subTest(contexto=invalido):
                i = interpretar("Me leve para aquela página.", invalido)
                self.assertNotEqual(i.intencao, Intencao.NAVEGAR)

    def test_regra_4_negacao_nunca_redireciona(self):
        for mensagem in ("Não quero abrir o dashboard.", "não me leva pra lá", "Jamais abra o upload"):
            with self.subTest(mensagem=mensagem):
                self.assertEqual(interpretar(mensagem, "dashboard").intencao, Intencao.COMANDO_NEGADO)

    def test_regra_5_comando_citado_e_pergunta_sobre_o_sistema(self):
        i = interpretar("Se eu escrever abra o dashboard, o sistema vai funcionar?")
        self.assertEqual(i.intencao, Intencao.SOBRE_O_BOT)

    def test_regra_6_multiplos_destinos_pedem_esclarecimento(self):
        i = interpretar("Abra o histórico ou o dashboard.")
        self.assertEqual(i.intencao, Intencao.AMBIGUIDADE)
        self.assertEqual(set(i.opcoes), {"historico", "dashboard"})
        self.assertEqual(i.modo_opcoes, "navegar")

    def test_regra_7_operacao_nao_permitida_nao_e_ignorada(self):
        i = interpretar("Apague meus relatórios e abra o dashboard.")
        self.assertEqual(i.intencao, Intencao.OPERACAO_NAO_PERMITIDA)
        self.assertTrue(i.operacoes)
        self.assertEqual(i.destino, "dashboard")  # vira botão, nunca navegação

    def test_regra_8_pagina_inexistente(self):
        self.assertEqual(interpretar("Abra a página de investimentos.").intencao, Intencao.PAGINA_INEXISTENTE)

    def test_regra_9_pagina_atual(self):
        i = interpretar("Abra o histórico", pagina_atual="historico")
        self.assertEqual((i.intencao, i.destino), (Intencao.PAGINA_ATUAL, "historico"))

    def test_regra_10_links_esquemas_e_caminhos_administrativos(self):
        for mensagem in ("Abra https://evil.example", "abra javascript:alert(1)", "abra //evil.com",
                         "abra /admin/empresas", "abra data:text/html,<b>x</b>", "abra file:///etc/passwd",
                         "abra vbscript:msgbox", "abra www.exemplo.com.br", "me leva pro painel de administração"):
            with self.subTest(mensagem=mensagem):
                i = interpretar(mensagem, "upload", oferta="upload")
                self.assertIn(i.intencao, (Intencao.ACESSO_RESTRITO, Intencao.ENTRADA_SUSPEITA))
                self.assertIsNone(i.destino)


class ContextoTests(unittest.TestCase):
    def test_valida_somente_chaves_do_catalogo(self):
        c = Contexto.da_requisicao(None, {
            "ultimo_destino": "upload", "destino_anterior": "/admin", "opcoes": ["guia", "x", 3, "suporte"],
            "modo_opcoes": "executar", "oferta": "upload", "pagina_atual": "historico", "extra": "ignorado",
        })
        self.assertEqual(c.ultimo_destino, "upload")
        self.assertIsNone(c.destino_anterior)
        self.assertEqual(c.opcoes, ("guia", "suporte"))
        self.assertIsNone(c.modo_opcoes)
        self.assertEqual(c.oferta, "upload")
        self.assertEqual(c.pagina_atual, "historico")

    def test_tipos_inesperados_sao_descartados(self):
        for bruto in (None, "upload", 1, [], ["upload"], {"ultimo_destino": ["upload"]},
                      {"opcoes": "upload,guia"}, {"oferta": {"x": 1}}):
            with self.subTest(contexto=bruto):
                c = Contexto.da_requisicao(None, bruto)
                self.assertIsNone(c.ultimo_destino)
                self.assertEqual(c.opcoes, ())

    def test_oferta_so_vale_para_o_ultimo_destino(self):
        c = Contexto.da_requisicao(None, {"ultimo_destino": "upload", "oferta": "historico"})
        self.assertIsNone(c.oferta)

    def test_avanco_preserva_anterior_e_limpa_assunto_nao_relacionado(self):
        c = Contexto.da_requisicao("upload")
        novo = c.avancar("historico", oferecido=True)
        self.assertEqual(novo["ultimo_destino"], "historico")
        self.assertEqual(novo["destino_anterior"], "upload")
        self.assertEqual(novo["oferta"], "historico")
        self.assertEqual(c.avancar(), {"ultimo_destino": None, "destino_anterior": None,
                                       "opcoes": [], "modo_opcoes": None, "oferta": None})
        self.assertIsNone(c.manter()["oferta"])

    def test_confirmacao_exige_oferta_imediata(self):
        self.assertEqual(interpretar("sim", "upload", oferta="upload").intencao, Intencao.NAVEGAR)
        self.assertEqual(interpretar("sim", "upload").intencao, Intencao.CONFIRMACAO)
        self.assertEqual(interpretar("não, obrigado", "upload", oferta="upload").intencao, Intencao.RECUSA)

    def test_escolha_entre_opcoes(self):
        i = interpretar("o segundo", None, opcoes=["upload", "historico"], modo_opcoes="orientar")
        self.assertEqual((i.intencao, i.destino), (Intencao.ORIENTACAO_NAVEGACAO, "historico"))
        i = interpretar("o primeiro", None, opcoes=["historico", "dashboard"], modo_opcoes="navegar")
        self.assertEqual((i.intencao, i.destino), (Intencao.NAVEGAR, "historico"))
        i = interpretar("quero enviar um novo", None, opcoes=["upload", "historico"], modo_opcoes="orientar")
        self.assertEqual(i.destino, "upload")

    def test_referencia_a_anterior(self):
        i = interpretar("volta para a anterior", None, ultimo_destino="historico", destino_anterior="upload")
        self.assertEqual((i.intencao, i.destino), (Intencao.NAVEGAR, "upload"))
        self.assertEqual(interpretar("volta para a anterior").intencao, Intencao.AMBIGUIDADE)
        # "análises anteriores" é o Histórico, não uma referência à conversa.
        self.assertEqual(interpretar("abra as análises anteriores", "upload").destino, "historico")

    def test_destino_explicito_prevalece_sobre_contexto(self):
        self.assertEqual(interpretar("Quero ir para o histórico.", "upload").destino, "historico")

    def test_palavras_isoladas_nao_viram_comando(self):
        for mensagem in ("lá", "estoque", "ali", "essa", "página"):
            with self.subTest(mensagem=mensagem):
                self.assertNotEqual(interpretar(mensagem, "upload").intencao, Intencao.NAVEGAR)

    def test_assunto_nao_relacionado_nao_reaproveita_destino(self):
        for mensagem in ("O que aconteceu lá ontem?", "Eu estava naquela página ontem.",
                         "Me leve para lá estoque.", "Me leva para o local do bot."):
            with self.subTest(mensagem=mensagem):
                self.assertNotEqual(interpretar(mensagem, "upload", oferta="upload").intencao, Intencao.NAVEGAR)


if __name__ == "__main__":
    unittest.main()
