"""NexoBot Advanced 2.0 — verificações estáticas do widget (sem navegador).

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
BLOCO_CSS = CSS[CSS.index("NEXOBOT — widget"):CSS.index("GUIA (CMS)")]


class WidgetJavaScriptTests(unittest.TestCase):
    def test_nao_usa_apis_que_interpretam_html_ou_codigo(self):
        for proibido in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(",
                         "new Function", "setTimeout('", 'setTimeout("', "srcdoc"):
            with self.subTest(api=proibido):
                self.assertNotIn(proibido, JS)
        self.assertIn("createTextNode", JS)
        self.assertIn("textContent", JS)

    def test_blocos_estruturados_sao_validados_por_tipo(self):
        self.assertIn("var TIPOS_BLOCO = { cabecalho: true, texto: true, passos: true, secao: true, exemplo: true, aviso: true };", JS)
        self.assertIn("if (!bloco || typeof bloco !== 'object' || !TIPOS_BLOCO[bloco.tipo]) return null;", JS)
        self.assertIn("if (typeof item !== 'string') return;", JS)  # passos só aceitam texto

    def test_sugestoes_apenas_enviam_mensagens(self):
        trecho = JS[JS.index("function chips("):JS.index("/* ---------- catálogo e navegação")]
        self.assertIn("enviar(mensagem)", trecho)
        for proibido in ("location", "fetch(", "window.open", "href"):
            self.assertNotIn(proibido, trecho)
        self.assertIn("typeof s.mensagem === 'string'", trecho)

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
        self.assertRegex(JS, r"if \(!conteudo \|\| pendente \|\| redirecionando\) return;")

    def test_tratamento_de_sessao_expirada_e_falhas(self):
        self.assertIn("r.redirected || r.status === 401 || r.status === 403", JS)
        self.assertIn("Sua sessão expirou", JS)
        self.assertIn("erro.status === 429", JS)
        self.assertIn("input.value = conteudo", JS)  # restaura o texto para reenviar
        self.assertIn("rotulo: 'Tentar novamente'", JS)

    def test_contexto_guarda_somente_identificadores_conhecidos(self):
        self.assertIn("function guardarContexto", JS)
        self.assertIn("chaveValida", JS)
        self.assertIn("ASSUNTO_VALIDO.test(novo.assunto)", JS)
        self.assertIn("nivel >= 0 && nivel <= 4", JS)
        self.assertNotIn("localStorage", JS)
        self.assertNotIn("sessionStorage", JS)
        self.assertNotIn("document.cookie", JS)

    def test_campo_de_mensagem(self):
        self.assertIn("function ajustarAltura", JS)
        self.assertIn("ALTURA_MAXIMA_INPUT", JS)
        self.assertIn("e.key === 'Enter' && !e.shiftKey", JS)
        self.assertIn("enviarBtn.disabled = pendente || redirecionando || !input.value.trim();", JS)

    def test_teclado_virtual_e_acessibilidade(self):
        self.assertIn("window.visualViewport", JS)
        self.assertIn("e.key === 'Escape'", JS)
        self.assertIn("launcher.focus()", JS)
        self.assertIn("aria-expanded", JS)
        self.assertIn("aria-busy", JS)
        self.assertIn("prefers-reduced-motion", JS)

    def test_saudacao_local_coincide_com_a_do_servidor(self):
        from nexobot import respostas
        servidor = respostas.saudacao("oi")
        self.assertIn("Olá! Sou o NexoBot, seu assistente do NEXO.", JS)
        rotulos = re.findall(r"rotulo: '([^']+)', mensagem: '([^']+)'", JS)
        self.assertEqual([(r, m) for r, m in rotulos][:5],
                         [(s["rotulo"], s["mensagem"]) for s in servidor.sugestoes[:5]] + [
                             ("Preciso de ajuda", "Preciso de ajuda")][len(servidor.sugestoes[:5]) - 4:])


class WidgetTemplateTests(unittest.TestCase):
    def test_marcacao_acessivel(self):
        for trecho in ('aria-controls="nexobotPanel"', 'aria-expanded="false"', 'role="dialog"',
                       'aria-labelledby="nexobotTitulo"', 'aria-describedby="nexobotSubtitulo"', 'role="log"',
                       'aria-live="polite"', 'for="nexobotInput"', 'aria-label="Enviar mensagem"',
                       'maxlength="1000"', "hidden", "<textarea", 'enterkeyhint="send"'):
            with self.subTest(trecho=trecho):
                self.assertIn(trecho, WIDGET)

    def test_cabecalho_nao_promete_ia_externa(self):
        self.assertIn("Assistente do portal NEXO", WIDGET)
        self.assertIn("base de conhecimento do portal", WIDGET)
        for proibido in ("IA conectada", "inteligência artificial conectada", "GPT", "online"):
            self.assertNotIn(proibido, WIDGET)

    def test_dados_injetados_escapados(self):
        self.assertIn("| tojson | forceescape", WIDGET)
        self.assertNotIn("|safe", WIDGET.replace(" ", ""))
        self.assertIn("url_for('api.suporte_bot')", WIDGET)

    def test_widget_somente_para_cliente(self):
        inicio = BASE.index("NexoBot — widget")
        anterior = BASE.rfind("{% if", 0, inicio)
        self.assertIn("current_user.is_cliente", BASE[anterior:inicio])


class WidgetCssTests(unittest.TestCase):
    def test_mobile_first_e_estados(self):
        for trecho in (".nexobot-panel[hidden] { display: none; }", ".nb-navigation", ".nb-opcao", ".nb-chip",
                       ".nb-passos", ".nb-aviso", ".nb-exemplo", ".nb-secao", ".nb-cabecalho", ".nb-erro",
                       "@media (min-width: 640px)", "@media (max-height: 480px)",
                       "@media (prefers-reduced-motion: reduce)", "env(safe-area-inset-bottom",
                       "100dvh", ":focus-visible", "overflow-wrap: anywhere"):
            with self.subTest(trecho=trecho):
                self.assertIn(trecho, BLOCO_CSS)
        # Em tela pequena o painel é fixo e ocupa a tela; o launcher some quando aberto.
        self.assertIn(".nexobot.is-open .nexobot-launcher { display: none; }", BLOCO_CSS)
        self.assertRegex(BLOCO_CSS, r"\.nexobot-input \{[^}]*font: 16px")  # evita zoom automático no iOS

    def test_usa_tokens_do_design_system(self):
        for token in ("var(--grad)", "var(--primary-soft)", "var(--surface-2)", "var(--border)", "var(--text-muted)",
                      "var(--warning-bg)", "var(--font-sans)"):
            with self.subTest(token=token):
                self.assertIn(token, BLOCO_CSS)
        # Nenhuma paleta concorrente: cores fixas só nas variações já usadas pelo portal.
        for cor in re.findall(r"#[0-9a-fA-F]{6}\b", BLOCO_CSS):
            self.assertIn(cor.lower(), {"#ffffff", "#fff", "#d8c2fd", "#dcdee8", "#f1e9ff", "#fde7b0", "#c4a0fb",
                                        "#ece3fb", "#fbd07a"} | set(re.findall(r"#[0-9a-fA-F]{6}\b", CSS[:4000])))

    def test_sem_overflow_hidden_no_body(self):
        self.assertNotRegex(BLOCO_CSS, r"body\s*\{[^}]*overflow")

    def test_animacao_leve(self):
        self.assertEqual(len(re.findall(r"@keyframes", BLOCO_CSS)), 1)
        self.assertNotIn("filter: blur(", BLOCO_CSS.replace("backdrop-filter", ""))


if __name__ == "__main__":
    unittest.main()
