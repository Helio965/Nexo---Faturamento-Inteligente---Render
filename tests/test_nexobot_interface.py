"""NexoBot Advanced — verificações estáticas do widget (sem navegador).

Executar da raiz: python -m unittest tests.test_nexobot_interface -v
Os testes em navegador real ficam em tests/test_nexobot_navegador.py.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "static" / "js" / "nexobot.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "css" / "nexo.css").read_text(encoding="utf-8")
BASE = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
WIDGET = BASE[BASE.index("NexoBot — widget"):BASE.index("filename='js/nexobot.js'")]


class WidgetJavaScriptTests(unittest.TestCase):
    def test_nao_usa_apis_que_interpretam_html_ou_codigo(self):
        for proibido in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(",
                         "new Function", "setTimeout('", 'setTimeout("', "srcdoc"):
            with self.subTest(api=proibido):
                self.assertNotIn(proibido, JS)
        self.assertIn("createTextNode", JS)
        self.assertIn("textContent", JS)

    def test_acoes_validadas_contra_catalogo_e_mesma_origem(self):
        self.assertIn("var ACOES = { navegar: true, sugerir_navegacao: true };", JS)
        self.assertIn("destinos[destino] !== url", JS)
        self.assertIn("validada.origin === window.location.origin", JS)
        self.assertIn("url.charAt(1) === '/'", JS)  # rejeita //host

    def test_requisicao_segura(self):
        self.assertIn("credentials: 'same-origin'", JS)
        self.assertIn("'X-CSRFToken'", JS)
        self.assertIn("TEMPO_LIMITE_MS", JS)
        self.assertIn("requisicao.abort()", JS)
        self.assertRegex(JS, r"if \(!texto \|\| pendente \|\| redirecionando\) return;")

    def test_tratamento_de_sessao_expirada_e_falhas(self):
        self.assertIn("r.redirected || r.status === 401 || r.status === 403", JS)
        self.assertIn("Sua sessão expirou", JS)
        self.assertIn("erro.status === 429", JS)
        self.assertIn("input.value = texto", JS)  # restaura o texto para reenviar

    def test_contexto_guarda_somente_chaves_do_catalogo(self):
        self.assertIn("function guardarContexto", JS)
        self.assertIn("chaveValida", JS)
        self.assertNotIn("localStorage", JS)
        self.assertNotIn("sessionStorage", JS)
        self.assertNotIn("document.cookie", JS)

    def test_acessibilidade_por_teclado(self):
        self.assertIn("e.key === 'Escape'", JS)
        self.assertIn("launcher.focus()", JS)
        self.assertIn("aria-expanded", JS)
        self.assertIn("aria-busy", JS)


class WidgetTemplateTests(unittest.TestCase):
    def test_marcacao_acessivel(self):
        for trecho in ('aria-controls="nexobotPanel"', 'aria-expanded="false"', 'role="dialog"',
                       'aria-labelledby="nexobotTitulo"', 'role="log"', 'aria-live="polite"',
                       'for="nexobotInput"', 'aria-label="Enviar mensagem"', 'maxlength="1000"', "hidden"):
            with self.subTest(trecho=trecho):
                self.assertIn(trecho, WIDGET)

    def test_dados_injetados_escapados(self):
        self.assertIn("| tojson | forceescape", WIDGET)
        self.assertNotIn("|safe", WIDGET.replace(" ", ""))
        self.assertIn("url_for('api.suporte_bot')", WIDGET)

    def test_widget_somente_para_cliente(self):
        inicio = BASE.index("NexoBot — widget")
        anterior = BASE.rfind("{% if", 0, inicio)
        self.assertIn("current_user.is_cliente", BASE[anterior:inicio])


class WidgetCssTests(unittest.TestCase):
    def test_estados_e_responsividade(self):
        for trecho in (".nexobot-panel[hidden] { display: none; }", ".nb-navigation", ".nb-opcao",
                       ".nb-erro", "@media (max-width: 560px)", "@media (prefers-reduced-motion: reduce)",
                       ".nexobot-form input { font-size: 16px; }", ":focus-visible"):
            with self.subTest(trecho=trecho):
                self.assertIn(trecho, CSS)

    def test_animacao_leve(self):
        bloco = CSS[CSS.index("NEXOBOT — widget"):]
        bloco = bloco[:bloco.index("GUIA (CMS)")]
        self.assertEqual(len(re.findall(r"@keyframes", bloco)), 1)
        self.assertNotIn("filter: blur(", bloco.replace("backdrop-filter", ""))


if __name__ == "__main__":
    unittest.main()
