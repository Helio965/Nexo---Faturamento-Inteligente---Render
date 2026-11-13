"""Cabeçalho renderizado: posição, proteção de pixels e controles em Chromium.

Reutiliza exclusivamente o servidor local e os bancos SQLite descartáveis de
NavegadorCase. CDN respondida com cópias locais de SRI conferido. Habilitar com
NEXO_TEST_BROWSER=1, NEXO_TEST_CHROMIUM e NEXO_TEST_CDN_DIR, como os demais testes.

A proteção visual é medida comparando a região inteira do cabeçalho, incluindo
cantos, contra duas cenas: conteúdo contrastante visível e o mesmo conteúdo
oculto (sem mudar o fluxo). O controle positivo, logo abaixo do cabeçalho,
precisa mudar de fato; assim a comparação não passa sem conteúdo atrás da barra.
"""

import base64
import io
import json
import math
from pathlib import Path
import unittest
from urllib.parse import urlsplit

from PIL import Image, ImageChops

from tests.test_overflow_navegador import NavegadorCase, _BROWSER


ADMIN = "admin-test@example.invalid"
CLIENTE = "cliente-test@example.invalid"
RESOLUCOES = ((320, 568), (360, 780), (390, 844), (430, 932),
              (768, 1024), (1024, 768), (1366, 768), (1920, 1080))
ROOT = Path(__file__).resolve().parents[1]

_GEOMETRIA = """() => {
    const h = document.querySelector('.topbar'), b = h.getBoundingClientRect();
    const rect = e => { const r = e.getBoundingClientRect();
        return {left:r.left, right:r.right, top:r.top, bottom:r.bottom, height:r.height}; };
    const controles = ['.topbar-title', '#navToggle', '#bellBtn', '.user-chip'].map(s => {
        const e = document.querySelector(s); return {seletor:s, visivel:getComputedStyle(e).display !== 'none', ...rect(e)};
    }).filter(e => e.visivel);
    return {left:b.left, right:b.right, top:b.top, bottom:b.bottom, height:b.height,
        raio:parseFloat(getComputedStyle(h).borderTopLeftRadius), controles,
        rolagemX:document.documentElement.scrollWidth > innerWidth + 1,
        scrollY:scrollY, altura:document.documentElement.scrollHeight};
}"""

# HTML de conteúdo comum, sem fixed/sticky/z-index: deve atravessar naturalmente
# a região protegida. Preenche toda a largura, inclusive quando .page tem max-width.
_INSERIR_CENA = """() => {
    const p = document.querySelector('.page'), area = document.querySelector('.main-area');
    const velho = document.getElementById('cenaTopbar'); if (velho) velho.remove();
    const cena = document.createElement('section'); cena.id = 'cenaTopbar';
    cena.style.cssText = 'position:relative;color:#000;background:#fff;overflow:hidden;'
        + 'width:' + area.clientWidth + 'px;margin-left:-' + getComputedStyle(p).paddingLeft;
    const linha = '<article style="background:#fff;color:#000;border:8px solid #000;padding:4px;">'
        + '<h2 style="font:900 24px/1.1 monospace;margin:0;color:#000;">FATURAMENTO 123456789 NEXO</h2>'
        + '<table style="width:100%;font:900 20px/1.1 monospace;color:#000;">'
        + '<tr><td style="background:#000;color:#fff;">R$ 987.654,32</td>'
        + '<td>CLIENTE 0123456789</td></tr></table>'
        + '<svg viewBox="0 0 600 40" width="100%" height="40" role="img" aria-label="Gráfico contrastante">'
        + '<rect width="600" height="40" fill="white"/>'
        + '<path d="M0 38L50 0L100 38L150 0L200 38L250 0L300 38L350 0L400 38L450 0L500 38L550 0L600 38" '
        + 'fill="none" stroke="black" stroke-width="12"/></svg></article>';
    cena.innerHTML = linha.repeat(24); p.prepend(cena);
}"""


def _imagem(pagina):
    return Image.open(io.BytesIO(pagina.screenshot(animations="disabled"))).convert("RGB")


def _maior_diferenca(a, b):
    return max(maximo for minimo, maximo in ImageChops.difference(a, b).getextrema())


@unittest.skipUnless(_BROWSER, "Defina NEXO_TEST_BROWSER=1 e instale o Playwright.")
class TopbarNavegadorTests(NavegadorCase):
    def _sessao(self, email=ADMIN, tema="dark", largura=1366, altura=768, sem_filtro=False):
        pagina = self.abrir(largura, altura)
        if sem_filtro:
            # Simula um motor sem a propriedade. A expressão @supports original
            # torna-se falsa; não se injeta uma superfície artificial de fallback.
            def css_sem_filtro(rota):
                nome = Path(urlsplit(rota.request.url).path).name
                folha = (ROOT / "static" / "css" / nome).read_text(encoding="utf-8")
                folha = folha.replace("backdrop-filter", "nexo-test-unsupported-filter")
                rota.fulfill(status=200, content_type="text/css", body=folha)
            pagina.route("**/static/css/nexo*.css*", css_sem_filtro)
        self.entrar(pagina, email)
        pagina.evaluate("t => localStorage.setItem('theme', t)", tema)
        self.ir(pagina, "/admin/dashboard" if email == ADMIN else "/cliente/dashboard")
        self.assertEqual(pagina.locator("html").get_attribute("data-theme"), tema)
        return pagina

    def _rolar(self, pagina, y):
        pagina.evaluate("y => { document.documentElement.style.scrollBehavior='auto'; window.scrollTo(0,y); }", y)
        pagina.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
        return pagina.evaluate(_GEOMETRIA)

    def _redimensionar(self, pagina, largura, altura):
        pagina.set_viewport_size({"width": largura, "height": altura})
        # O shell reavalia KPIs/tabelas em 120 ms e gráficos em 150 ms.
        # Medir antes disso confunde o layout anterior com overflow permanente.
        pagina.wait_for_timeout(250)

    def _assert_geometria(self, medida, largura):
        self.assertAlmostEqual(medida["top"], 0, delta=0.5, msg=medida)
        self.assertAlmostEqual(medida["left"], 292 if largura >= 992 else 10, delta=0.5, msg=medida)
        self.assertAlmostEqual(medida["right"], largura - (14 if largura >= 992 else 10), delta=0.5, msg=medida)
        self.assertAlmostEqual(medida["height"], 68 if largura >= 992 else 60, delta=0.5, msg=medida)
        self.assertEqual(medida["raio"], 22 if largura >= 992 else 18, medida)
        self.assertFalse(medida["rolagemX"], medida)
        for c in medida["controles"]:
            self.assertGreaterEqual(c["left"], medida["left"], c)
            self.assertLessEqual(c["right"], medida["right"], c)
            self.assertGreaterEqual(c["top"], medida["top"], c)
            self.assertLessEqual(c["bottom"], medida["bottom"], c)
            self.assertAlmostEqual((c["top"] + c["bottom"]) / 2,
                                   (medida["top"] + medida["bottom"]) / 2, delta=1, msg=c)
        controles = sorted(medida["controles"], key=lambda c: c["left"])
        for a, b in zip(controles, controles[1:]):
            self.assertLessEqual(a["right"], b["left"] + 0.5,
                            f"controles se sobrepõem: {a}, {b}")

    def _assert_pixels_protegidos(self, pagina):
        medida = pagina.evaluate(_GEOMETRIA)
        cena = pagina.locator("#cenaTopbar").bounding_box()
        self.assertLess(cena["y"], 0, "o conteúdo contrastante precisa atravessar o topo")
        self.assertGreater(cena["y"] + cena["height"], medida["bottom"])
        caixa = (math.ceil(medida["left"]), 0, math.floor(medida["right"]), math.floor(medida["bottom"]))
        visivel = _imagem(pagina)
        pagina.evaluate("document.querySelector('.page').style.visibility = 'hidden'")
        oculto = _imagem(pagina)
        pagina.evaluate("document.querySelector('.page').style.removeProperty('visibility')")
        # Inclui topo, dois cantos, centro, título, sino e borda inferior.
        diferenca = _maior_diferenca(visivel.crop(caixa), oculto.crop(caixa))
        if diferenca > 3:
            # Evidência das capturas já realizadas: não muda o ensaio ou seu limite.
            imagens = {}
            for nome, imagem in (("visivel", visivel.crop(caixa)),
                                  ("oculto", oculto.crop(caixa)),
                                  ("diferenca", ImageChops.difference(visivel, oculto).crop(caixa))):
                arquivo = io.BytesIO()
                imagem.save(arquivo, format="PNG")
                imagens[nome] = base64.b64encode(arquivo.getvalue()).decode("ascii")
            print("TOPBAR_DIAGNOSTICO=" + json.dumps({
                "geometria": medida, "caixa": caixa, "maximo": diferenca,
                "bbox": ImageChops.difference(visivel, oculto).crop(caixa).getbbox(),
                "imagens_png_base64": imagens,
            }), flush=True)
        self.assertLessEqual(diferenca, 3, f"conteúdo alterou pixels protegidos em até {diferenca}/255")
        controle = (caixa[0], caixa[3] + 24, caixa[2], caixa[3] + 90)
        self.assertGreater(_maior_diferenca(visivel.crop(controle), oculto.crop(controle)), 100,
                           "o cenário precisa ter conteúdo contrastante exposto abaixo do cabeçalho")

    def test_posicao_estavel_e_margens_preservadas_em_oito_larguras(self):
        for email in (ADMIN, CLIENTE):
            for tema in ("dark", "light"):
                pagina = self._sessao(email, tema)
                for largura, altura in RESOLUCOES:
                    with self.subTest(email=email, tema=tema, largura=largura):
                        self._redimensionar(pagina, largura, altura)
                        pagina.evaluate(_INSERIR_CENA)
                        inicial = self._rolar(pagina, 0)
                        self._assert_geometria(inicial, largura)
                        for y in (1, 8, 48, 160, 600, 1200, 520, 24, 2, 0):
                            medida = self._rolar(pagina, y)
                            self._assert_geometria(medida, largura)
                            self.assertAlmostEqual(medida["top"], inicial["top"], delta=0.5)
                            self.assertAlmostEqual(medida["scrollY"], y, delta=1,
                                                   msg="o documento precisa continuar rolando normalmente")
                pagina.context.close()

    def test_conteudo_nao_altera_pixels_do_topo_cantos_e_corpo(self):
        for tema in ("dark", "light"):
            pagina = self._sessao(ADMIN, tema)
            for largura, altura in RESOLUCOES:
                self._redimensionar(pagina, largura, altura)
                pagina.evaluate(_INSERIR_CENA)
                for y in (240, 617):
                    with self.subTest(tema=tema, largura=largura, scroll=y):
                        self._rolar(pagina, y)
                        self._assert_pixels_protegidos(pagina)
            pagina.context.close()

    def test_fallback_sem_backdrop_filter_e_transparencia_reduzida(self):
        for sem_filtro in (True, False):
            for tema in ("dark", "light"):
                pagina = self._sessao(ADMIN, tema, sem_filtro=sem_filtro)
                if not sem_filtro:
                    cdp = pagina.context.new_cdp_session(pagina)
                    cdp.send("Emulation.setEmulatedMedia", {"features":[
                        {"name":"prefers-reduced-motion", "value":"reduce"},
                        {"name":"prefers-reduced-transparency", "value":"reduce"}]})
                    self.assertTrue(pagina.evaluate("matchMedia('(prefers-reduced-transparency: reduce)').matches"))
                for largura, altura in ((320, 568), (1366, 768)):
                    with self.subTest(sem_filtro=sem_filtro, tema=tema, largura=largura):
                        self._redimensionar(pagina, largura, altura)
                        pagina.evaluate(_INSERIR_CENA)
                        self._assert_geometria(self._rolar(pagina, 617), largura)
                        self.assertEqual(pagina.evaluate("getComputedStyle(document.querySelector('.topbar'),'::before').backdropFilter"), "none")
                        fundo = pagina.evaluate("""() => { const c = getComputedStyle(document.querySelector('.topbar'),'::before');
                            return {cor:c.backgroundColor, imagem:c.backgroundImage}; }""")
                        if fundo["imagem"] == "none":
                            self.assertRegex(fundo["cor"], r"^rgb\(", "fallback precisa ter superfície opaca")
                        else:
                            self.assertIn("rgb(", fundo["imagem"])
                            self.assertNotIn("rgba(", fundo["imagem"], "as cores do degradê de fallback precisam ser opacas")
                        self._assert_pixels_protegidos(pagina)
                        pagina.click("#bellBtn")
                        pagina.wait_for_selector(".bell-menu.show")
                        pagina.keyboard.press("Escape")
                pagina.context.close()

    def test_paginas_admin_cliente_zoom_e_orientacao(self):
        paginas = ((ADMIN, ("/admin/dashboard", "/admin/empresas", "/admin/contratos", "/admin/analises",
                            "/admin/tickets", "/admin/configuracoes")),
                   (CLIENTE, ("/cliente/dashboard", "/cliente/historico", "/cliente/tickets", "/cliente/configuracoes")))
        for email, caminhos in paginas:
            for tema in ("dark", "light"):
                pagina = self._sessao(email, tema, largura=390, altura=844)
                for caminho in caminhos:
                    with self.subTest(caminho=caminho, tema=tema):
                        self.ir(pagina, caminho)
                        self._assert_geometria(self._rolar(pagina, 0), 390)
                        pagina.evaluate(_INSERIR_CENA)
                        self._assert_geometria(self._rolar(pagina, 620), 390)
                # Troca retrato/paisagem e altura dinâmica da viewport no mesmo documento.
                for largura, altura in ((844, 390), (390, 660), (390, 844)):
                    self._redimensionar(pagina, largura, altura)
                    pagina.evaluate(_INSERIR_CENA)
                    self._assert_geometria(self._rolar(pagina, 620), largura)
                pagina.context.close()
        # Como a suíte existente: 1366 px a 150% = ~911 CSS px com escala 1.5.
        pagina = self.abrir(911, 512, escala=1.5)
        self.entrar(pagina, ADMIN)
        pagina.evaluate(_INSERIR_CENA)
        self._assert_geometria(self._rolar(pagina, 620), 911)

    def test_sino_sidebar_modal_e_nexobot_continuam_clicaveis(self):
        from models import Notificacao
        for email, prefixo in ((ADMIN, "/admin"), (CLIENTE, "/cliente")):
            for tema in ("dark", "light"):
                self.db.session.add(Notificacao(
                    id_usuario=self.admin_id if email == ADMIN else self.cliente_id,
                    texto="Notificação de teste do cabeçalho", link_destino=prefixo + "/configuracoes"))
                self.db.session.commit()
                pagina = self._sessao(email, tema, largura=390, altura=844)
                pagina.evaluate(_INSERIR_CENA)
                self._rolar(pagina, 617)
                self.assertEqual(pagina.locator("#bellBadge").get_attribute("data-count"), "1")
                pagina.click("#bellBtn")
                menu = pagina.locator(".bell-menu.show")
                menu.wait_for(state="visible")
                sino = pagina.locator("#bellBtn").bounding_box()
                self.assertGreaterEqual(menu.bounding_box()["y"], sino["y"] + sino["height"])
                with pagina.expect_navigation(wait_until="load"):
                    pagina.locator(".bell-item.is-unread").click()
                self.assertTrue(pagina.url.endswith(prefixo + "/configuracoes"))
                self.assertEqual(pagina.locator("#bellBadge").get_attribute("data-count"), "0")
                pagina.click("#navToggle")
                pagina.wait_for_selector(".app-shell.nav-open")
                self.assertTrue(pagina.locator("#sidebar").is_visible())
                self.assertEqual(pagina.locator("#navToggle").get_attribute("aria-expanded"), "true")
                self.assertFalse(pagina.locator("#nexobotLauncher").is_visible())
                pagina.locator(".sidebar-close").click()
                pagina.wait_for_selector(".app-shell:not(.nav-open)")
                pagina.click("#navToggle")
                pagina.locator("#sidebarOverlay").click(position={"x":380, "y":200})
                pagina.wait_for_selector(".app-shell:not(.nav-open)")
                if email == CLIENTE:
                    pagina.click("#nexobotLauncher")
                    pagina.wait_for_selector("#nexobot.is-open", state="attached")
                    pagina.locator("#nexobotPanel").wait_for(state="visible")
                    pagina.click("#nexobotClose")
                else:
                    self.assertEqual(pagina.locator("#nexobotLauncher").count(), 0)
                if email == ADMIN:
                    self.ir(pagina, "/admin/empresas")
                    pagina.locator('[data-bs-target="#confirmDeleteEmpresaModal"]').first.click()
                    pagina.wait_for_selector("#confirmDeleteEmpresaModal.show")
                    pagina.locator('#confirmDeleteEmpresaModal [data-bs-dismiss="modal"]').first.click()
                    pagina.wait_for_selector("#confirmDeleteEmpresaModal.show", state="hidden")
                pagina.context.close()
