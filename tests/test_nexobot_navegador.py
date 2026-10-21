"""NexoBot Advanced — interface em navegador real (Chromium via Playwright).

Opcional: Playwright NÃO faz parte de requirements.txt. Para executar:
    pip install playwright==1.56.0        # somente no ambiente de teste
    python -m playwright install chromium # ou NEXO_TEST_CHROMIUM=/caminho/do/chrome
    NEXO_TEST_BROWSER=1 python -m unittest tests.test_nexobot_navegador -v

Sobe a aplicação real num servidor local isolado (SQLite temporário,
migrações reais) e bloqueia qualquer requisição a outro host (CDNs).
"""

import os
import re
import socket
import threading
import unittest
from unittest.mock import patch

from tests.deploy_support import DeployTestCase

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # dependência opcional de desenvolvimento
    sync_playwright = None

HABILITADO = os.environ.get("NEXO_TEST_BROWSER") == "1" and sync_playwright is not None


@unittest.skipUnless(HABILITADO, "Defina NEXO_TEST_BROWSER=1 e instale o Playwright para os testes de navegador.")
class NavegadorTests(DeployTestCase):
    def setUp(self):
        super().setUp()
        from werkzeug.serving import make_server
        from models import GuiaTopico
        import seed_guia
        self.fixtures()
        for topico in seed_guia.TOPICOS:
            self.db.session.add(GuiaTopico(**topico))
        self.db.session.add(GuiaTopico(
            categoria="Teste", pergunta="Como funciona o xilofluxo?",
            resposta='<img src=x onerror="window.__xss=1"> <script>window.__xss=2</script> **negrito**'))
        self.db.session.commit()
        # A rede de teste bloqueia conexões; o servidor local precisa delas (só 127.0.0.1).
        for alvo in ("socket.socket.connect", "socket.socket.connect_ex", "socket.create_connection"):
            self.stack.enter_context(patch(alvo, _CONECTAR_LOCAL[alvo]))
        self.servidor = make_server("127.0.0.1", 0, self.app, threaded=True)
        self.base = f"http://127.0.0.1:{self.servidor.server_port}"
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()
        self.addCleanup(self.servidor.shutdown)
        self.pw = sync_playwright().start()
        self.addCleanup(self.pw.stop)
        executavel = os.environ.get("NEXO_TEST_CHROMIUM") or None
        self.navegador = self.pw.chromium.launch(executable_path=executavel)
        self.addCleanup(self.navegador.close)
        self.erros_js = []

    def nova_pagina(self, largura=1440, altura=900):
        contexto = self.navegador.new_context(viewport={"width": largura, "height": altura})
        self.addCleanup(contexto.close)
        pagina = contexto.new_page()
        pagina.on("pageerror", lambda erro: self.erros_js.append(str(erro)))
        # Somente o servidor local e o CSS versionado do Bootstrap usado pelo layout;
        # scripts externos (Plotly, Socket.IO) são bloqueados: o widget não depende deles.
        permitidos = (self.base, *_CSS_LAYOUT)
        pagina.route("**/*", lambda rota: rota.continue_() if rota.request.url.startswith(permitidos)
                     and (rota.request.url.startswith(self.base) or rota.request.resource_type in ("stylesheet", "font"))
                     else rota.abort())
        pagina.goto(self.base + "/auth/login")
        pagina.fill("input[name=email]", "cliente-test@example.invalid")
        pagina.fill("input[name=senha]", self.password)
        pagina.click("button[type=submit]")
        pagina.wait_for_url(re.compile(r".*/cliente/dashboard$"))
        return pagina

    def abrir_widget(self, pagina):
        pagina.click("#nexobotLauncher")
        pagina.wait_for_selector("#nexobotPanel:not([hidden])")

    def enviar(self, pagina, texto):
        total = pagina.locator(".nb-msg.nb-bot:not(.nb-typing)").count()
        pagina.fill("#nexobotInput", texto)
        pagina.press("#nexobotInput", "Enter")
        pagina.wait_for_function(
            "n => document.querySelectorAll('.nb-msg.nb-bot:not(.nb-typing)').length > n", arg=total)
        return pagina.locator(".nb-msg.nb-bot:not(.nb-typing)").last

    def tearDown(self):
        self.assertEqual(self.erros_js, [], "Exceções JavaScript na página")

    # -- cenários ----------------------------------------------------------
    def test_pergunta_oferece_botao_e_clique_navega(self):
        pagina = self.nova_pagina()
        self.abrir_widget(pagina)
        self.assertEqual(pagina.evaluate("document.activeElement.id"), "nexobotInput")
        bolha = self.enviar(pagina, "Onde fica o histórico?")
        self.assertIn("/cliente/dashboard", pagina.url)
        botao = bolha.locator("button.nb-navigation")
        self.assertEqual(botao.inner_text(), "Ir para Histórico de Análises")
        with pagina.expect_navigation():
            botao.click()
        self.assertTrue(pagina.url.endswith("/cliente/historico"))

    def test_comando_direto_fecha_painel_e_navega(self):
        pagina = self.nova_pagina()
        self.abrir_widget(pagina)
        pagina.fill("#nexobotInput", "Me leve para o upload")
        with pagina.expect_navigation():
            pagina.press("#nexobotInput", "Enter")
        self.assertTrue(pagina.url.endswith("/cliente/upload"))

    def test_contexto_e_pagina_atual(self):
        pagina = self.nova_pagina()
        self.abrir_widget(pagina)
        self.enviar(pagina, "Onde fica o guia?")
        pagina.fill("#nexobotInput", "me leva pra lá")
        with pagina.expect_navigation():
            pagina.press("#nexobotInput", "Enter")
        self.assertTrue(pagina.url.endswith("/cliente/guia"))
        self.abrir_widget(pagina)
        bolha = self.enviar(pagina, "Abra o guia")
        self.assertIn("Você já está em Guia", bolha.inner_text())
        self.assertTrue(pagina.url.endswith("/cliente/guia"))

    def test_esclarecimento_com_botoes_de_opcao(self):
        pagina = self.nova_pagina()
        self.abrir_widget(pagina)
        bolha = self.enviar(pagina, "Abra o histórico ou o upload")
        botoes = bolha.locator("button.nb-opcao")
        self.assertEqual(botoes.count(), 2)
        with pagina.expect_navigation():
            botoes.nth(1).click()
        self.assertTrue(pagina.url.endswith("/cliente/upload"))

    def test_conteudo_do_guia_e_renderizado_como_texto(self):
        pagina = self.nova_pagina()
        self.abrir_widget(pagina)
        bolha = self.enviar(pagina, "Como funciona o xilofluxo?")
        self.assertIn("<img src=x", bolha.inner_text())
        self.assertEqual(bolha.locator("img, script").count(), 0)
        self.assertEqual(bolha.locator("strong").first.inner_text(), "Como funciona o xilofluxo?")
        self.assertIsNone(pagina.evaluate("window.__xss || null"))

    def test_envio_duplo_e_bloqueado(self):
        pagina = self.nova_pagina()
        chamadas = []
        pagina.on("request", lambda r: chamadas.append(r.url) if r.url.endswith("/api/suporte-bot") else None)
        self.abrir_widget(pagina)
        pagina.fill("#nexobotInput", "Oi")
        pagina.evaluate("""() => { const f = document.getElementById('nexobotForm');
            f.requestSubmit(); f.requestSubmit(); f.requestSubmit(); }""")
        pagina.wait_for_function("document.querySelectorAll('.nb-msg.nb-bot:not(.nb-typing)').length >= 2")
        pagina.wait_for_function("!document.getElementById('nexobotEnviar').disabled")
        self.assertEqual(len(chamadas), 1)
        self.assertEqual(pagina.locator(".nb-msg.nb-user").count(), 1)

    def test_falha_da_api_restaura_o_texto(self):
        pagina = self.nova_pagina()
        pagina.route("**/api/suporte-bot", lambda rota: rota.fulfill(status=500, body="erro", content_type="text/html"))
        self.abrir_widget(pagina)
        bolha = self.enviar(pagina, "Onde fica o upload?")
        self.assertIn("Não consegui responder agora", bolha.inner_text())
        self.assertEqual(pagina.input_value("#nexobotInput"), "Onde fica o upload?")

    def test_acao_maliciosa_da_api_e_ignorada(self):
        pagina = self.nova_pagina()
        corpo = '{"resposta": "", "fonte": "local", "acao": "navegar", "destino": "upload", "url": "https://evil.example/"}'
        pagina.route("**/api/suporte-bot", lambda rota: rota.fulfill(status=200, body=corpo,
                                                                      content_type="application/json"))
        self.abrir_widget(pagina)
        bolha = self.enviar(pagina, "abra o upload")
        self.assertIn("Não consegui responder agora", bolha.inner_text())
        self.assertIn("/cliente/dashboard", pagina.url)

    def test_sessao_expirada(self):
        pagina = self.nova_pagina()
        self.abrir_widget(pagina)
        pagina.context.clear_cookies()
        bolha = self.enviar(pagina, "Onde fica o upload?")
        self.assertIn("Sua sessão expirou", bolha.inner_text())

    def test_teclado_escape_e_foco(self):
        pagina = self.nova_pagina()
        pagina.focus("#nexobotLauncher")
        pagina.keyboard.press("Enter")
        pagina.wait_for_selector("#nexobotPanel:not([hidden])")
        self.assertEqual(pagina.get_attribute("#nexobotLauncher", "aria-expanded"), "true")
        pagina.keyboard.press("Escape")
        pagina.wait_for_selector("#nexobotPanel", state="hidden")
        self.assertEqual(pagina.evaluate("document.activeElement.id"), "nexobotLauncher")

    def test_layout_mobile(self):
        pagina = self.nova_pagina(390, 844)
        largura_antes = pagina.evaluate("document.documentElement.scrollWidth")
        self.abrir_widget(pagina)
        for seletor in ("#nexobotPanel", "#nexobotLauncher", "#nexobotInput", "#nexobotEnviar"):
            caixa = pagina.locator(seletor).bounding_box()
            self.assertGreaterEqual(caixa["x"], 0, seletor)
            self.assertLessEqual(caixa["x"] + caixa["width"], 390, seletor)
            self.assertGreaterEqual(caixa["y"], 0, seletor)
            self.assertLessEqual(caixa["y"] + caixa["height"], 844, seletor)
        self.assertEqual(pagina.evaluate("getComputedStyle(document.getElementById('nexobotInput')).fontSize"), "16px")
        # O widget não cria rolagem horizontal (a largura da página não muda ao abri-lo).
        self.assertEqual(pagina.evaluate("document.documentElement.scrollWidth"), largura_antes)
        bolha = self.enviar(pagina, "Onde fica o histórico?")
        self.assertTrue(bolha.locator("button.nb-navigation").is_visible())


_CSS_LAYOUT = ("https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/",
               "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/")

_ORIGINAIS = {"socket.socket.connect": socket.socket.connect,
              "socket.socket.connect_ex": socket.socket.connect_ex,
              "socket.create_connection": socket.create_connection}


def _somente_local(original):
    def conectar(*args, **kwargs):
        destino = args[1] if len(args) > 1 and not isinstance(args[0], tuple) else args[0]
        host = destino[0] if isinstance(destino, tuple) else str(destino)
        if host not in ("127.0.0.1", "localhost", "::1"):
            raise AssertionError(f"Rede externa proibida no teste: {host}")
        return original(*args, **kwargs)
    return conectar


_CONECTAR_LOCAL = {alvo: _somente_local(original) for alvo, original in _ORIGINAIS.items()}


if __name__ == "__main__":
    unittest.main()
