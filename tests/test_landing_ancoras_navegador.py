"""Landing: cada âncora do menu leva ao início da seção, logo abaixo do cabeçalho fixo.

Mede posições reais (getBoundingClientRect) no Chromium, com Bootstrap e Plotly
íntegros, como na CI: menu no computador, no tablet, no celular e no celular
deitado, navegação de ida e volta, menu móvel, acesso direto e recarga com âncora,
clique com a página ainda carregando, histórico, teclado, redimensionamento, fonte
maior, sem JavaScript e com movimento reduzido.

Tolerância de 1 px: a posição de rolagem é arredondada para pixels inteiros e as
posições do layout são fracionárias, então o início da seção pode ficar até meio
pixel acima ou abaixo da borda do cabeçalho. Dois casos somam um segundo
arredondamento e usam 2 px: sem JavaScript (valem as alturas do cabeçalho escritas
na folha de estilos, em pixels inteiros arredondados para baixo) e depois de o
navegador compensar uma mudança de altura acima da seção (ancoragem de rolagem).
"""

import os
from pathlib import Path
import re
import threading
import time
import unittest
from unittest.mock import patch

from tests.deploy_support import DeployTestCase
from tests.test_contratos_navegador import _CDN, _copias_locais_da_cdn
from tests.test_nexobot_navegador import _CONECTAR_LOCAL

try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright
except ImportError:
    PlaywrightTimeoutError = sync_playwright = None

_RAIZ = Path(__file__).resolve().parents[1]
_BROWSER = os.environ.get("NEXO_TEST_BROWSER") == "1" and sync_playwright is not None
_BOOTSTRAP = _CDN + "bootstrap@5.3.3/dist/css/bootstrap.min.css"
_PLOTLY = _CDN + "plotly.js-dist-min@2.35.2/plotly.min.js"

_IDA = ("inicio", "como-funciona", "indicadores", "demonstracao", "planos")
_VOLTA = ("demonstracao", "indicadores", "como-funciona", "inicio")
_TELAS = {
    "computador": ((1024, 768), (1366, 768), (1440, 900), (1920, 1080)),
    "tablet": ((768, 1024), (820, 1180), (992, 800)),
    "celular": ((320, 568), (360, 740), (390, 844), (430, 932)),
    # Telas baixas: abrir o menu encolhe o vídeo da demonstração, que fica acima de Planos.
    "celular deitado": ((568, 320), (667, 375), (844, 390)),
}
_MENU_MOVEL_ATE = 992
_TOLERANCIA = 1.0
_TOLERANCIA_DUPLA = 2.0
_CONTORNO_DE_FOCO = 7  # outline de 3 px com outline-offset de 4 px (landing.css)

_MEDIR = """([id, tolerancia]) => {
    const header = document.querySelector('.nexo-header').getBoundingClientRect();
    const alvo = document.getElementById(id);
    const caixa = alvo.getBoundingClientRect();
    const titulo = alvo.querySelector('h1, h2').getBoundingClientRect();
    const etiqueta = alvo.querySelector('.section-tag');
    // Seção anterior: nada dela pode aparecer entre a borda do cabeçalho e o
    // início da seção escolhida.
    const anterior = alvo.previousElementSibling;
    const restos = [];
    if (anterior) {
        for (const el of [anterior, ...anterior.querySelectorAll('*')]) {
            const r = el.getBoundingClientRect();
            if (r.width > 0 && r.height > 0 && r.bottom > header.bottom + tolerancia && r.top < innerHeight) {
                restos.push((el.id ? '#' + el.id : el.tagName.toLowerCase()) + ' ' + (el.textContent || '').trim().slice(0, 40));
            }
        }
    }
    return {
        hash: location.hash, scrollY: scrollY, larguraDocumento: document.documentElement.scrollWidth,
        alturaJanela: innerHeight, headerTop: header.top, headerBottom: header.bottom, headerAltura: header.height,
        secaoTop: caixa.top, tituloTop: titulo.top, tituloBottom: titulo.bottom,
        etiquetaTop: etiqueta ? etiqueta.getBoundingClientRect().top : null,
        espacamentoInterno: parseFloat(getComputedStyle(alvo).paddingTop),
        restosAnteriores: restos,
    };
}"""

_ALINHADA = """([id, tolerancia]) => {
    const header = document.querySelector('.nexo-header').getBoundingClientRect();
    const caixa = document.getElementById(id).getBoundingClientRect();
    return location.hash === '#' + id && Math.abs(caixa.top - header.bottom) <= tolerancia;
}"""

# A rolagem terminou quando a posição não muda por 12 quadros seguidos (~0,2 s).
_ROLAGEM_PARADA = """() => new Promise(resolve => {
    let ultima = scrollY, iguais = 0;
    const quadro = () => {
        if (scrollY === ultima) { if (++iguais >= 12) { resolve(scrollY); return; } }
        else { ultima = scrollY; iguais = 0; }
        requestAnimationFrame(quadro);
    };
    requestAnimationFrame(quadro);
})"""

_DOIS_QUADROS = "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"


def _sem_comentarios(texto):
    return re.sub(r"/\*.*?\*/|^\s*//[^\n]*$", "", texto, flags=re.S | re.M)


class LandingAnchorSingleMechanismTests(unittest.TestCase):
    """Sem navegador: uma única compensação vertical, ligada à altura do cabeçalho."""

    def test_css_has_no_vertical_scroll_padding_and_margins_follow_the_header(self):
        css = _sem_comentarios((_RAIZ / "static/css/landing.css").read_text(encoding="utf-8"))
        self.assertIsNone(re.search(r"scroll-padding(-top|-block(-start)?)?\s*:", css),
                          "scroll-padding vertical se somaria à margem de rolagem")
        regras = re.findall(r"([^{}]+)\{[^{}]*?scroll-margin-top\s*:\s*([^;}]+)", css)
        self.assertTrue(regras)
        for seletores, valor in regras:
            self.assertIn("var(--nexo-header-height)", valor)
            self.assertNotIn("header", seletores, "Controles do cabeçalho fixo não recebem margem de rolagem")
        self.assertRegex(css, r":root\s*\{[^}]*--nexo-header-height\s*:")

    def test_script_measures_the_header_when_the_menu_changes_and_when_it_resizes(self):
        js = _sem_comentarios((_RAIZ / "static/js/landing.js").read_text(encoding="utf-8"))
        menu = js.split("function setMenu(open)", 1)[1].split("function syncMenu()", 1)[0]
        self.assertIn("syncHeaderOffset();", menu)
        self.assertIn("setProperty('--nexo-header-height'", js)
        self.assertIn("new window.ResizeObserver(syncHeaderOffset)", js)


@unittest.skipUnless(_BROWSER, "Defina NEXO_TEST_BROWSER=1 e instale Playwright para validar a landing em navegador.")
class LandingAnchorAlignmentBrowserTests(DeployTestCase):
    def setUp(self):
        super().setUp()
        self.cdn_local = _copias_locais_da_cdn()
        if not all(url in self.cdn_local for url in (_BOOTSTRAP, _PLOTLY)):
            self.skipTest("Bootstrap 5.3.3 e Plotly 2.35.2 íntegros necessários para medir o layout (NEXO_TEST_CDN_DIR)")
        from werkzeug.serving import make_server
        for target, original in _CONECTAR_LOCAL.items():
            self.stack.enter_context(patch(target, original))
        self.server = make_server("127.0.0.1", 0, self.app, threaded=True)
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self._stop_server)
        self.pw = sync_playwright().start()
        self.addCleanup(self.pw.stop)
        self.browser = self.pw.chromium.launch(executable_path=os.environ.get("NEXO_TEST_CHROMIUM") or None)
        self.addCleanup(self.browser.close)
        self.errors = []

    def _stop_server(self):
        self.server.shutdown()
        self.server.server_close()

    def tearDown(self):
        self.assertEqual(self.errors, [], "Exceções JavaScript na landing")

    def page(self, largura, altura, *, javascript=True, movimento="no-preference", caminho="/",
             landing=True, reter_plotly=None, css_extra=None):
        context = self.browser.new_context(viewport={"width": largura, "height": altura},
                                           java_script_enabled=javascript, reduced_motion=movimento)
        self.addCleanup(context.close)
        page = context.new_page()
        page.on("pageerror", lambda error: self.errors.append(str(error)))
        base, cdn = self.base, self.cdn_local

        def route(rota):
            url = rota.request.url
            if css_extra and url.startswith(base) and url.endswith("/static/css/landing.css"):
                resposta = rota.fetch()  # simula uma preferência do navegador (ex.: fonte maior)
                rota.fulfill(response=resposta, body=resposta.text() + "\n" + css_extra)
            elif url.startswith(base):
                rota.continue_()
            elif url == _PLOTLY and reter_plotly is not None:
                reter_plotly.append(rota)  # o teste responde depois: página ainda carregando
            elif url in cdn:  # somente cópias com o hash SRI oficial conferido
                arquivo, tipo = cdn[url]
                rota.fulfill(status=200, path=arquivo, content_type=tipo)
            else:
                rota.abort()
        page.route("**/*", route)
        page.goto(self.base + caminho, wait_until="load" if reter_plotly is None else "domcontentloaded")
        if javascript and landing and reter_plotly is None:
            self.esperar_pagina_completa(page)
        return page

    def esperar_pagina_completa(self, page):
        # Carregamento concluído, gráficos desenhados e fontes prontas: depois disso a altura
        # do conteúdo não muda.
        page.wait_for_function("() => document.querySelectorAll('[data-chart-ready=true]').length === 3")
        page.wait_for_function("() => document.readyState === 'complete'")
        page.evaluate("() => document.fonts.ready.then(() => true)")
        page.evaluate(_DOIS_QUADROS)
        self.esperar_rolagem(page)

    def esperar_rolagem(self, page, javascript=True):
        if javascript:
            return page.evaluate(_ROLAGEM_PARADA)
        anterior, iguais = None, 0  # sem JavaScript a página não agenda quadros: leitura de fora
        prazo = time.monotonic() + 10
        while time.monotonic() < prazo:
            atual = page.evaluate("scrollY")
            iguais = iguais + 1 if atual == anterior else 0
            if iguais >= 6:
                return atual
            anterior = atual
            page.wait_for_timeout(50)
        self.fail("A rolagem não terminou em 10 s")

    def esperar_secao(self, page, secao, tolerancia=_TOLERANCIA):
        """Espera a seção chegar à borda do cabeçalho e a rolagem parar; devolve a medição."""
        try:
            page.wait_for_function(_ALINHADA, arg=[secao, tolerancia], timeout=8000)
        except PlaywrightTimeoutError:
            pass  # a medição abaixo mostra onde a página parou
        self.esperar_rolagem(page)
        return self.medir(page, secao, tolerancia)

    def medir(self, page, secao, tolerancia=_TOLERANCIA):
        return page.evaluate(_MEDIR, [secao, tolerancia])

    def ir_pelo_menu(self, page, largura, secao):
        menu = page.locator("#landing-navigation")
        botao = page.locator("#landing-menu-toggle")
        movel = largura <= _MENU_MOVEL_ATE
        if movel:
            botao.click()
            self.assertEqual(botao.get_attribute("aria-expanded"), "true")
            self.assertTrue(menu.is_visible())
        menu.locator(f'a[href="#{secao}"]').click()
        if movel:
            self.assertEqual(botao.get_attribute("aria-expanded"), "false")
            self.assertFalse(menu.is_visible())
        return self.esperar_secao(page, secao)

    def assert_alinhada(self, medida, secao, tolerancia=_TOLERANCIA):
        contexto = f"#{secao}: {medida}"
        self.assertEqual(medida["hash"], "#" + secao, contexto)
        self.assertAlmostEqual(medida["headerTop"], 0, delta=0.5, msg="Cabeçalho deixou de ficar fixo no topo")
        distancia = medida["secaoTop"] - medida["headerBottom"]
        self.assertLessEqual(distancia, tolerancia, "Seção começa abaixo da borda do cabeçalho: " + contexto)
        self.assertGreaterEqual(distancia, -tolerancia, "Seção começa sob o cabeçalho: " + contexto)
        self.assertEqual(medida["restosAnteriores"], [], "Conteúdo anterior visível acima da seção: " + contexto)
        self.assertGreaterEqual(medida["tituloTop"], medida["headerBottom"], "Título encoberto: " + contexto)
        self.assertLess(medida["tituloTop"], medida["alturaJanela"], "Título fora da tela: " + contexto)
        # O título aparece inteiro sempre que cabe abaixo do cabeçalho. Numa janela mais baixa
        # que o próprio título (celular deitado de 320 px de altura), o começo dele fica visível.
        if medida["tituloBottom"] - medida["secaoTop"] <= medida["alturaJanela"] - medida["headerBottom"]:
            self.assertLessEqual(medida["tituloBottom"], medida["alturaJanela"], "Título cortado: " + contexto)
        if medida["etiquetaTop"] is not None:
            # Entre a borda do cabeçalho e o primeiro conteúdo, só o espaçamento interno da
            # própria seção (80 px no computador, 64 px no celular). A etiqueta é um elemento
            # em linha: o alinhamento pela linha de base do texto a desce até 2 px.
            deslocamento = medida["etiquetaTop"] - medida["secaoTop"] - medida["espacamentoInterno"]
            self.assertTrue(-0.5 <= deslocamento <= 2, "Área vazia além do espaçamento da seção: " + contexto)
        if secao == "inicio":
            self.assertLessEqual(medida["scrollY"], 1, "Início deve levar ao topo da página")

    def test_menu_alinha_cada_secao_na_ida_e_na_volta_em_todas_as_telas(self):
        for tipo, telas in _TELAS.items():
            for largura, altura in telas:
                with self.subTest(tela=tipo, largura=largura, altura=altura):
                    page = self.page(largura, altura)
                    for secao in _IDA + _VOLTA:
                        medida = self.ir_pelo_menu(page, largura, secao)
                        self.assert_alinhada(medida, secao)
                        self.assertLessEqual(medida["larguraDocumento"], largura + 1, "Rolagem horizontal")
                    page.context.close()

    def test_menu_movel_fecha_e_a_secao_nao_se_desloca_depois(self):
        # Demonstração fica acima do vídeo e Planos abaixo dele (o vídeo muda de altura
        # com o menu aberto nas telas baixas).
        for largura, altura, secao in ((320, 568, "demonstracao"), (390, 844, "planos"),
                                       (768, 1024, "demonstracao"), (844, 390, "planos")):
            with self.subTest(largura=largura, altura=altura):
                page = self.page(largura, altura)
                fechado = page.locator(".nexo-header").bounding_box()["height"]
                page.locator("#landing-menu-toggle").click()
                aberto = page.locator(".nexo-header").bounding_box()["height"]
                self.assertGreater(aberto, fechado + 40, "O menu aberto ocupa o cabeçalho")
                page.locator(f'#landing-navigation a[href="#{secao}"]').click()
                self.assertEqual(page.locator("#landing-menu-toggle").get_attribute("aria-expanded"), "false")
                self.assertFalse(page.locator("#landing-navigation").is_visible())
                medida = self.esperar_secao(page, secao)
                self.assert_alinhada(medida, secao)
                self.assertAlmostEqual(medida["headerAltura"], fechado, delta=0.01)
                # Nenhum deslocamento posterior; o usuário continua rolando livremente.
                page.wait_for_timeout(500)
                self.assertEqual(self.esperar_rolagem(page), medida["scrollY"])
                page.mouse.move(largura / 2, altura / 2)
                page.mouse.wheel(0, -300)
                page.wait_for_function(f"() => scrollY < {medida['scrollY']} - 200")
                depois = self.esperar_rolagem(page)
                page.wait_for_timeout(500)
                self.assertEqual(self.esperar_rolagem(page), depois, "A página voltou sozinha para a âncora")
                self.assertTrue(page.locator(".header-actions a").is_visible())
                self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), largura + 1)
                # Link fora do cabeçalho clicado com o menu aberto: o menu fecha e a seção alinha.
                self.ir_pelo_menu(page, largura, "inicio")
                page.locator("#landing-menu-toggle").click()
                page.get_by_role("link", name="Conheça os planos").click()
                self.assertEqual(page.locator("#landing-menu-toggle").get_attribute("aria-expanded"), "false")
                self.assert_alinhada(self.esperar_secao(page, "planos"), "planos")
                page.context.close()

    def test_acesso_direto_e_recarga_com_ancora_alinham_apos_o_carregamento(self):
        for largura, altura in ((1366, 768), (820, 1180), (390, 844), (320, 568)):
            for secao in ("como-funciona", "indicadores", "demonstracao", "planos"):
                with self.subTest(largura=largura, secao=secao):
                    page = self.page(largura, altura, caminho="/#" + secao)
                    self.assert_alinhada(self.medir(page, secao), secao)
                    if secao in ("indicadores", "planos"):
                        page.reload(wait_until="load")
                        self.esperar_pagina_completa(page)
                        self.assert_alinhada(self.medir(page, secao), secao)
                    page.context.close()
        # Link de outra página para uma âncora da landing.
        page = self.page(390, 844, caminho="/como-aderir", landing=False)
        page.get_by_role("link", name="Conhecer os planos").click()
        page.wait_for_load_state("load")
        self.esperar_pagina_completa(page)
        self.assert_alinhada(self.medir(page, "planos"), "planos")

    def test_clique_com_a_pagina_ainda_carregando_alinha_e_continua_alinhado(self):
        for largura, altura in ((1366, 768), (390, 844)):
            with self.subTest(largura=largura):
                retidas = []
                page = self.page(largura, altura, reter_plotly=retidas)
                page.wait_for_function("() => document.documentElement.classList.contains('landing-enhanced')")
                self.assertEqual(len(retidas), 1)
                # Até o fim do carregamento a rolagem é imediata: o destino não fica para trás
                # quando os gráficos chegam e mudam a altura do conteúdo acima da seção.
                self.assertEqual(page.evaluate("getComputedStyle(document.documentElement).scrollBehavior"), "auto")
                self.assert_alinhada(self.ir_pelo_menu(page, largura, "planos"), "planos")
                antes = page.evaluate("document.documentElement.scrollHeight")
                arquivo, tipo = self.cdn_local[_PLOTLY]
                retidas[0].fulfill(status=200, path=arquivo, content_type=tipo)
                self.esperar_pagina_completa(page)
                self.assertLess(page.evaluate("document.documentElement.scrollHeight"), antes,
                                "Os gráficos prontos escondem as notas acima da seção")
                self.assert_alinhada(self.medir(page, "planos", _TOLERANCIA_DUPLA), "planos", _TOLERANCIA_DUPLA)
                self.assertEqual(page.evaluate("getComputedStyle(document.documentElement).scrollBehavior"), "smooth")
                page.context.close()

    def test_voltar_avancar_e_clique_repetido_preservam_o_historico(self):
        for largura, altura in ((1366, 768), (390, 844)):
            with self.subTest(largura=largura):
                page = self.page(largura, altura)
                page.get_by_role("link", name="Veja o NEXO em ação").click()
                self.assert_alinhada(self.esperar_secao(page, "demonstracao"), "demonstracao")
                for secao in ("como-funciona", "planos"):
                    self.assert_alinhada(self.ir_pelo_menu(page, largura, secao), secao)
                entradas = page.evaluate("history.length")
                self.assert_alinhada(self.ir_pelo_menu(page, largura, "planos"), "planos")
                self.assertEqual(page.evaluate("history.length"), entradas, "Clique repetido criou outra entrada")
                for secao in ("como-funciona", "demonstracao"):
                    page.go_back()
                    self.assert_alinhada(self.esperar_secao(page, secao), secao)
                page.go_back()
                page.wait_for_function("() => location.hash === '' && scrollY === 0")
                for secao in ("demonstracao", "como-funciona", "planos"):
                    page.go_forward()
                    self.assert_alinhada(self.esperar_secao(page, secao), secao)
                page.context.close()

    def test_teclado_e_links_internos_usam_o_mesmo_alinhamento(self):
        for largura, altura in ((1366, 768), (390, 844)):
            with self.subTest(largura=largura):
                page = self.page(largura, altura)
                page.keyboard.press("Tab")
                self.assertEqual(page.evaluate("document.activeElement.getAttribute('href')"), "#conteudo")
                page.keyboard.press("Enter")
                self.assertEqual(self.esperar_rolagem(page), 0)
                self.assertEqual(page.evaluate("document.activeElement.id"), "conteudo")
                if largura <= _MENU_MOVEL_ATE:
                    page.locator("#landing-menu-toggle").focus()
                    page.keyboard.press("Enter")
                page.locator('#landing-navigation a[href="#indicadores"]').focus()
                page.keyboard.press("Enter")
                self.assert_alinhada(self.esperar_secao(page, "indicadores"), "indicadores")
                for nome, secao in (("Conheça os planos", "planos"), ("Veja o NEXO em ação", "demonstracao")):
                    self.ir_pelo_menu(page, largura, "inicio")
                    page.get_by_role("link", name=nome).click()
                    self.assert_alinhada(self.esperar_secao(page, secao), secao)
                rodape = page.locator(".nexo-footer")
                rodape.locator('.footer-col a[href="#como-funciona"]').click()
                self.assert_alinhada(self.esperar_secao(page, "como-funciona"), "como-funciona")
                rodape.get_by_role("link", name="Voltar ao início").click()
                self.assert_alinhada(self.esperar_secao(page, "inicio"), "inicio")
                page.context.close()

    def test_foco_do_teclado_nao_fica_sob_o_cabecalho_nem_rola_a_pagina_a_toa(self):
        for largura, altura in ((1366, 768), (390, 844)):
            with self.subTest(largura=largura):
                page = self.page(largura, altura, movimento="reduce")
                # Controle inteiro dentro da janela, mas coberto pelo cabeçalho (10 a 54 px do topo).
                resumo = page.locator("#como-funciona details.chart-summary summary")
                topo = resumo.evaluate("el => el.getBoundingClientRect().top + scrollY")
                page.evaluate(f"window.scrollTo({{top: {topo} - 10, behavior: 'instant'}})")
                borda = page.evaluate("document.querySelector('.nexo-header').getBoundingClientRect().bottom")
                coberto = resumo.bounding_box()
                self.assertGreaterEqual(coberto["y"], 0)
                self.assertLess(coberto["y"] + coberto["height"], borda, "O cenário exige o controle sob o cabeçalho")
                page.evaluate("""() => {
                    const resumo = document.querySelector('#como-funciona details.chart-summary summary');
                    const focaveis = [...document.querySelectorAll('a[href], button:not([disabled]), summary')]
                        .filter(el => el.offsetParent !== null);
                    focaveis[focaveis.indexOf(resumo) + 1].focus({preventScroll: true});
                }""")
                page.keyboard.press("Shift+Tab")
                self.esperar_rolagem(page)
                self.assertEqual(page.evaluate("document.activeElement.textContent.trim()"),
                                 "Consultar os valores do gráfico")
                visivel = resumo.bounding_box()
                self.assertGreaterEqual(visivel["y"] - _CONTORNO_DE_FOCO, borda - 0.5,
                                        "Contorno de foco encoberto pelo cabeçalho")
                self.assertLessEqual(visivel["y"], borda + _CONTORNO_DE_FOCO + 2, "Foco rolou além do necessário")
                # Foco num controle do próprio cabeçalho não rola a página.
                page.evaluate("window.scrollTo({top: 3000, behavior: 'instant'})")
                page.locator(".header-actions a").focus()
                self.assertEqual(self.esperar_rolagem(page), 3000)
                page.context.close()

    def test_redimensionamento_e_fonte_maior_atualizam_a_compensacao(self):
        page = self.page(1366, 768)
        self.assert_alinhada(self.ir_pelo_menu(page, 1366, "planos"), "planos")
        for (largura, altura), secao in (((390, 844), "indicadores"), ((820, 1180), "como-funciona"),
                                         ((1920, 1080), "demonstracao"), ((320, 568), "planos")):
            with self.subTest(largura=largura):
                page.set_viewport_size({"width": largura, "height": altura})
                page.evaluate(_DOIS_QUADROS)
                self.assert_alinhada(self.ir_pelo_menu(page, largura, secao), secao)
        # A altura do cabeçalho muda sem a janela mudar (fonte padrão maior no navegador).
        for largura, altura in ((1366, 768), (390, 844)):
            with self.subTest(fonte_maior=largura):
                page.set_viewport_size({"width": largura, "height": altura})
                page.evaluate("document.documentElement.style.fontSize = ''")
                page.evaluate(_DOIS_QUADROS)
                normal = page.locator(".nexo-header").bounding_box()["height"]
                page.evaluate("document.documentElement.style.fontSize = '20px'")
                page.evaluate(_DOIS_QUADROS)
                self.assertGreater(page.locator(".nexo-header").bounding_box()["height"], normal + 4)
                for secao in ("como-funciona", "planos"):
                    self.assert_alinhada(self.ir_pelo_menu(page, largura, secao), secao)

    def test_sem_javascript_as_ancoras_usam_a_altura_da_folha(self):
        # A reserva da folha acompanha a fonte padrão do navegador (20 px = configuração "Grande").
        casos = [(largura, altura, None) for largura, altura in
                 ((1366, 768), (1024, 768), (820, 1180), (390, 844), (320, 568))]
        casos += [(1366, 768, "html { font-size: 20px; }"), (820, 1180, "html { font-size: 20px; }"),
                  (390, 844, "html { font-size: 20px; }")]
        for largura, altura, css_extra in casos:
            with self.subTest(largura=largura, fonte_maior=bool(css_extra)):
                page = self.page(largura, altura, javascript=False, css_extra=css_extra)
                self.assertTrue(page.locator("#landing-navigation").is_visible())
                for secao in _IDA[1:] + ("inicio",):
                    page.locator(f'#landing-navigation a[href="#{secao}"]').click()
                    self.esperar_rolagem(page, javascript=False)
                    self.assert_alinhada(self.medir(page, secao, _TOLERANCIA_DUPLA), secao, _TOLERANCIA_DUPLA)
                page.context.close()

    def test_rolagem_suave_e_movimento_reduzido(self):
        page = self.page(1366, 768)
        self.assertEqual(page.evaluate("getComputedStyle(document.documentElement).scrollBehavior"), "smooth")
        page.locator('#landing-navigation a[href="#planos"]').click()
        # Com animação, a página passa por posições intermediárias antes de chegar.
        page.wait_for_function("() => scrollY > 0")
        durante = page.evaluate("scrollY")
        medida = self.esperar_secao(page, "planos")
        self.assertLess(durante, medida["scrollY"], "Sem animação de rolagem suave")
        self.assert_alinhada(medida, "planos")
        page.context.close()

        page = self.page(1366, 768, movimento="reduce")
        self.assertEqual(page.evaluate("getComputedStyle(document.documentElement).scrollBehavior"), "auto")
        page.locator('#landing-navigation a[href="#planos"]').click()
        self.assert_alinhada(self.medir(page, "planos"), "planos")


if __name__ == "__main__":
    unittest.main()
