"""Seleção e área de transferência reais no Chromium, com dados fictícios.

Usa a aplicação, CSP e fixtures SQLite temporárias da suíte de navegador. A CDN
é servida por cópias com SRI validado; nenhuma conta ou serviço externo é usado.
Ative com NEXO_TEST_BROWSER=1, como os demais testes de interface.
"""

import unittest

from tests import test_overflow_navegador as navegador


ADMIN = "admin-test@example.invalid"
CLIENTE = "cliente-test@example.invalid"
LARGURAS = (320, 360, 390, 430, 768, 1024, 1366, 1920)


@unittest.skipUnless(navegador._BROWSER, "Defina NEXO_TEST_BROWSER=1 e instale Playwright.")
class SelecaoNavegadorTests(navegador.NavegadorCase):
    def _arrastar(self, pagina, seletor):
        """Arrasta sobre uma linha real de texto, evitando espaços do contêiner."""
        alvo = pagina.locator(seletor).first
        alvo.evaluate("e => e.scrollIntoView({block:'center', behavior:'instant'})")
        pagina.evaluate("() => { document.activeElement.blur(); getSelection().removeAllRanges(); }")
        caixa = alvo.evaluate("""e => {
            const walker = document.createTreeWalker(e, NodeFilter.SHOW_TEXT);
            let node;
            while ((node = walker.nextNode())) {
                if (!node.textContent.trim()) continue;
                const range = document.createRange(); range.selectNodeContents(node);
                const rect = [...range.getClientRects()].find(r => r.width > 10 && r.height > 0);
                if (rect) return {x: rect.x, y: rect.y, w: rect.width, h: rect.height};
            }
            return null;
        }""")
        self.assertIsNotNone(caixa, seletor)
        inicio = caixa["x"] + 1
        fim = min(caixa["x"] + caixa["w"] - 1, inicio + 160)
        y = caixa["y"] + caixa["h"] / 2
        pagina.mouse.move(inicio, y)
        pagina.mouse.down()
        pagina.mouse.move(fim, y, steps=12)
        pagina.mouse.up()
        return pagina.evaluate("getSelection().toString()")

    def _sem_selecao(self, pagina, seletor):
        self.assertEqual(self._arrastar(pagina, seletor), "", seletor)

    def _clipboard(self, pagina):
        pagina.context.grant_permissions(["clipboard-read", "clipboard-write"], origin=self.base)

    def _colar(self, pagina, seletor, texto):
        self._clipboard(pagina)
        pagina.evaluate("texto => navigator.clipboard.writeText(texto)", texto)
        pagina.locator(seletor).click()
        pagina.keyboard.press("ControlOrMeta+A")
        pagina.keyboard.press("ControlOrMeta+V")
        self.assertEqual(pagina.locator(seletor).input_value(), texto, seletor)

    def _editar_clipboard(self, pagina, seletor, texto):
        """Seleciona parte, copia, recorta, cola e desfaz/refaz com teclas nativas."""
        self._colar(pagina, seletor, texto)
        alvo = pagina.locator(seletor)
        pagina.keyboard.press("Home")
        for _ in range(5):
            pagina.keyboard.press("Shift+ArrowRight")
        pagina.keyboard.press("ControlOrMeta+C")
        self.assertEqual(pagina.evaluate("navigator.clipboard.readText()"), texto[:5])
        pagina.keyboard.press("ControlOrMeta+X")
        self.assertEqual(alvo.input_value(), texto[5:])
        pagina.keyboard.press("ControlOrMeta+V")
        self.assertEqual(alvo.input_value(), texto)
        pagina.keyboard.press("ControlOrMeta+Z")
        self.assertEqual(alvo.input_value(), texto[5:])
        pagina.keyboard.press("ControlOrMeta+Shift+Z")
        self.assertEqual(alvo.input_value(), texto)

    def _esperar(self, pagina, expressao):
        # Evita a reavaliação com eval do wait_for_function, vedada pela CSP real.
        for _ in range(100):
            if pagina.evaluate(expressao):
                return
            pagina.wait_for_timeout(50)
        self.fail(expressao)

    def test_landing_arrasto_nas_oito_larguras_e_navegacao(self):
        pagina = self.abrir(1366, 900)
        self.ir(pagina, "/")
        # Controle positivo: o mesmo gesto precisa selecionar texto quando só
        # a folha nova é desativada. Evita passar por arrastar em espaço vazio.
        pagina.evaluate("document.querySelector('link[href*=\"nexo-selecao.css\"]').disabled = true")
        self.assertTrue(self._arrastar(pagina, "#hero-title"))
        pagina.evaluate("document.querySelector('link[href*=\"nexo-selecao.css\"]').disabled = false")
        for largura in LARGURAS:
            pagina.set_viewport_size({"width": largura, "height": 900})
            for seletor in ("#hero-title", ".hero .lead", "#problema .nexo-card h3", ".plan h3", "footer p"):
                with self.subTest(largura=largura, elemento=seletor):
                    self._sem_selecao(pagina, seletor)
            self.assertLessEqual(pagina.evaluate("document.documentElement.scrollWidth - innerWidth"), 1)
        pagina.set_viewport_size({"width": 1366, "height": 900})
        pagina.locator('.hero-cta a[href="#planos"]').click()
        self.assertEqual(pagina.evaluate("location.hash"), "#planos")
        pagina.locator('.header-actions a[href="/auth/login"]').click()
        self.assertTrue(pagina.url.endswith("/auth/login"))
        self.assertTrue(pagina.locator("#email").is_editable())

    def test_login_cola_email_senha_e_preserva_foco_teclado(self):
        pagina = self.abrir(1366, 900)
        self.ir(pagina, "/auth/login")
        self._sem_selecao(pagina, ".auth-title")
        self._sem_selecao(pagina, ".auth-sub")
        self._colar(pagina, "#email", CLIENTE)
        pagina.evaluate("navigator.clipboard.writeText('sentinela diferente do email')")
        pagina.keyboard.press("ControlOrMeta+A")
        pagina.keyboard.press("ControlOrMeta+C")
        self.assertEqual(pagina.evaluate("navigator.clipboard.readText()"), CLIENTE)
        pagina.keyboard.press("Tab")
        self.assertEqual(pagina.evaluate("document.activeElement.id"), "senha")
        self._colar(pagina, "#senha", self.password)
        pagina.keyboard.press("ControlOrMeta+A")
        self.assertEqual(pagina.locator("#senha").evaluate("e => e.selectionEnd - e.selectionStart"), len(self.password))
        with pagina.expect_navigation(wait_until="load"):
            pagina.locator('button[type="submit"]').click()
        self.assertIn("/cliente/dashboard", pagina.url)
        self.assertEqual(pagina.locator("#email").count(), 0)

    def test_admin_cnpj_busca_formulario_envio_e_readonly(self):
        pagina = self.abrir(1366, 900)
        self.entrar(pagina, ADMIN)
        self._sem_selecao(pagina, ".page-head h1")
        self.ir(pagina, "/admin/empresas")
        self._sem_selecao(pagina, "tbody .t-strong")
        self._editar_clipboard(pagina, "#buscaEmpresa", "Empresa fictícia")
        self.ir(pagina, "/admin/empresas/nova")
        # O formulário inteiro tinha user-select:text na política anterior.
        self._sem_selecao(pagina, ".relatorio-doc .field-hint" if pagina.locator(".relatorio-doc .field-hint").count()
                          else ".relatorio-doc .nexo-card-head p")
        self._colar(pagina, "#cnpj", "12345678000195")
        self._editar_clipboard(pagina, "#razao_social", "Empresa seleção fictícia")
        self._colar(pagina, "#email_contato", "contato-selecao@example.invalid")
        pagina.fill("#data_contratacao", "2026-03-02")
        pagina.locator("#id_segmento").select_option(index=1)
        pagina.locator("#id_plano_atual").select_option(index=1)
        self._colar(pagina, "#usuario_nome", "Responsável fictício")
        self._colar(pagina, "#usuario_email", "usuario-selecao@example.invalid")
        with pagina.expect_navigation(wait_until="load"):
            pagina.locator('.relatorio-doc button[type="submit"]').click()
        self.assertIn("cadastrada", pagina.locator("body").inner_text())
        self._sem_selecao(pagina, ".alert")
        from models import Empresa
        self.db.session.expire_all()
        empresa = self.db.session.scalar(self.db.select(Empresa).where(Empresa.cnpj == "12345678000195"))
        self.assertIsNotNone(empresa)
        self.assertEqual(empresa.razao_social, "Empresa seleção fictícia")
        self.ir(pagina, f"/admin/empresas/{empresa.id_empresa}/editar")
        self.assertTrue(pagina.locator("#cnpj").get_attribute("readonly") is not None)
        pagina.locator("#cnpj").click()
        pagina.keyboard.press("ControlOrMeta+A")
        pagina.keyboard.press("ControlOrMeta+C")
        self.assertEqual(pagina.evaluate("navigator.clipboard.readText()"), "12345678000195")

    def test_cliente_temas_larguras_suporte_nexobot_e_configuracoes(self):
        pagina = self.abrir(1366, 900)
        self.entrar(pagina, CLIENTE)
        for tema in ("dark", "light", "system"):
            pagina.evaluate("t => localStorage.setItem('theme', t)", tema)
            self.ir(pagina, "/cliente/dashboard")
            self.assertEqual(pagina.evaluate("localStorage.getItem('theme')"), tema)
            for largura in LARGURAS:
                pagina.set_viewport_size({"width": largura, "height": 900})
                with self.subTest(tema=tema, largura=largura):
                    self._sem_selecao(pagina, ".page-head h1")
                    self._sem_selecao(pagina, ".painel-kpi-valor, .kpi-value")
                    self.assertLessEqual(pagina.evaluate("document.documentElement.scrollWidth - innerWidth"), 1)
        pagina.set_viewport_size({"width": 1366, "height": 900})
        self.ir(pagina, f"/cliente/analise/{self.analise_id}")
        self._sem_selecao(pagina, ".rb-body")
        self.ir(pagina, "/cliente/tickets?novo=1")
        self._editar_clipboard(pagina, "textarea[name=mensagem]", "Mensagem fictícia para o suporte.")
        self._colar(pagina, "input[name=assunto]", "Dúvida fictícia")
        pagina.locator("#nexobotLauncher").click()
        self._editar_clipboard(pagina, "#nexobotInput", "Mensagem fictícia para o NexoBot.")
        self.assertTrue(pagina.locator("#nexobotEnviar").is_enabled())
        with pagina.expect_response(lambda r: "/api/suporte-bot" in r.url) as resposta_bot:
            pagina.locator("#nexobotEnviar").click()
        self.assertEqual(resposta_bot.value.status, 200)
        self.assertTrue(resposta_bot.value.json().get("resposta", "").strip())
        self._esperar(pagina, "document.querySelector('#nexobotForm').getAttribute('aria-busy') === 'false'")
        self.assertGreaterEqual(pagina.locator("#nexobotMsgs .nb-bot:not(.nb-typing)").count(), 2)
        self.assertEqual(pagina.locator("#nexobotMsgs .nb-erro").count(), 0)
        self.ir(pagina, "/cliente/configuracoes")
        self._editar_clipboard(pagina, "#nome", "Nome fictício para edição")
        self._colar(pagina, "#novo_email", "novo-selecao@example.invalid")
        self._colar(pagina, "#senha_atual_email", "SenhaFicticia!123456")

    def test_editores_semanticos_dinamicos_ilhas_e_menu_contexto(self):
        pagina = self.abrir(1366, 900)
        self.ir(pagina, "/auth/login")
        pagina.evaluate("""() => {
            const caixa = document.createElement('section');
            caixa.innerHTML = '<p id="apresentacao">Texto meramente informativo de teste</p>' +
              '<div id="rico" contenteditable="true"><span>Texto rico editável</span></div>' +
              '<div id="vazio" contenteditable=""><b>Editor com atributo vazio</b></div>' +
              '<div id="simples" contenteditable="plaintext-only">Editor de texto simples</div>' +
              '<div contenteditable="true"><p id="ilha" contenteditable="false">Ilha informativa protegida</p></div>' +
              '<div id="customizado" role="textbox" contenteditable="true"><span>Entrada personalizada</span></div>' +
              '<div id="papel" role="textbox"><span>Componente com papel de entrada</span></div>' +
              '<input id="dinamico" aria-label="Entrada dinâmica"><textarea id="dinamica"></textarea>';
            document.body.appendChild(caixa);
        }""")
        self._sem_selecao(pagina, "#apresentacao")
        self._sem_selecao(pagina, "#ilha")
        for seletor in ("#rico span", "#vazio b", "#simples", "#customizado span", "#papel span"):
            self.assertTrue(self._arrastar(pagina, seletor), seletor)
        for seletor in ("#dinamico", "#dinamica"):
            self._editar_clipboard(pagina, seletor, "Texto dinâmico fictício")
        self._clipboard(pagina)
        pagina.evaluate("() => { window.contextoCancelado = null; window.addEventListener('contextmenu', e => { "
                        "queueMicrotask(() => window.contextoCancelado = e.defaultPrevented); }); }")
        pagina.locator("#dinamico").click(button="right")
        self._esperar(pagina, "window.contextoCancelado !== null")
        self.assertIs(pagina.evaluate("window.contextoCancelado"), False)
        pagina.keyboard.press("Escape")

    def test_graficos_hover_legenda_zoom_e_arrasto_sem_selecao(self):
        pagina = self.abrir(1366, 900)
        self.entrar(pagina, CLIENTE)
        grafico = pagina.locator("#chartHistoricoCliente")
        self._esperar(pagina, "!!document.querySelector('#chartHistoricoCliente .scatterlayer .point')")
        ponto = grafico.locator(".scatterlayer .point").first
        ponto.evaluate("e => e.scrollIntoView({block:'center', behavior:'instant'})")
        caixa_ponto = ponto.bounding_box()
        # O Plotly recebe hover pela camada de interação sobre os pontos SVG.
        pagina.mouse.move(caixa_ponto["x"] + caixa_ponto["width"] / 2,
                          caixa_ponto["y"] + caixa_ponto["height"] / 2)
        self._esperar(pagina, "document.querySelector('#chartHistoricoCliente .hoverlayer').textContent.length > 0")
        self._sem_selecao(pagina, "#chartHistoricoCliente .xtick text")
        grafico.locator(".legendtoggle").first.click()
        self._esperar(pagina, "document.getElementById('chartHistoricoCliente').data[0].visible === 'legendonly'")
        grafico.locator(".legendtoggle").first.click()
        self._esperar(pagina, "document.getElementById('chartHistoricoCliente').data[0].visible === true")
        # Os gráficos atuais têm eixos travados por decisão anterior do produto.
        # Um gráfico de teste via NEXO.plot comprova o gesto de zoom onde habilitado.
        pagina.evaluate("""() => {
            const el = document.createElement('div'); el.id = 'graficoSelecaoTeste';
            document.querySelector('main').appendChild(el);
            NEXO.plot(el.id, [{x:[0,1,2,3], y:[0,2,1,3], mode:'lines+markers'}], {height:400});
            el.scrollIntoView({block:'center',behavior:'instant'});
        }""")
        self._esperar(pagina, "!!document.querySelector('#graficoSelecaoTeste .nsewdrag')")
        antes = pagina.evaluate("document.getElementById('graficoSelecaoTeste')._fullLayout.xaxis.range.slice()")
        caixa = pagina.locator("#graficoSelecaoTeste .nsewdrag").bounding_box()
        pagina.evaluate("getSelection().removeAllRanges()")
        pagina.mouse.move(caixa["x"] + caixa["width"] * .25, caixa["y"] + caixa["height"] * .25)
        pagina.mouse.down()
        pagina.mouse.move(caixa["x"] + caixa["width"] * .70, caixa["y"] + caixa["height"] * .70, steps=15)
        pagina.mouse.up()
        self._esperar(pagina, "document.getElementById('graficoSelecaoTeste').layout.xaxis.autorange === false")
        depois = pagina.evaluate("document.getElementById('graficoSelecaoTeste')._fullLayout.xaxis.range.slice()")
        self.assertLess(depois[1] - depois[0], antes[1] - antes[0])
        self.assertEqual(pagina.evaluate("getSelection().toString()"), "")

    def test_toque_simulado_preserva_login_e_edicao(self):
        contexto = self.navegador.new_context(viewport={"width": 390, "height": 844},
                                             is_mobile=True, has_touch=True, reduced_motion="reduce")
        self.addCleanup(contexto.close)
        pagina = contexto.new_page()
        pagina.on("pageerror", lambda erro: self.erros_js.append(str(erro)))
        pagina.route("**/*", self._rota)
        self.ir(pagina, "/auth/login")
        self.assertGreater(pagina.evaluate("navigator.maxTouchPoints"), 0)
        self.assertEqual(pagina.locator(".auth-title").evaluate("e => getComputedStyle(e).userSelect"), "none")
        pagina.locator("#email").tap()
        self._colar(pagina, "#email", CLIENTE)
        pagina.locator("#senha").tap()
        self._colar(pagina, "#senha", self.password)
        with pagina.expect_navigation(wait_until="load"):
            pagina.locator('button[type="submit"]').tap()
        self.assertIn("/cliente/dashboard", pagina.url)
