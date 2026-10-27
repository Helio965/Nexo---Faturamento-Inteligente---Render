"""Regressão de overflow, cortes e sobreposições em navegador real (Chromium via Playwright).

O que só o navegador mostra, medido pelas posições reais dos elementos (não só por
scrollWidth > clientWidth): uma tabela pode rolar certinho e ainda ter uma coluna
encoberta por outra fixa, um KPI pode "caber" porque a fonte encolheu demais e um
botão flutuante pode estar em cima de um controle.

Cenários, nas larguras 320, 360, 390, 768, 1024, 1366, 1536 e 1920 px (e no zoom
de 150% sobre 1366 px), com dados fictícios propositalmente extensos (razão social
e e-mail longos, produtos com nomes compridos, faturamento de nove dígitos):

  1. página sem rolagem horizontal e sem elemento visível fora da tela;
  2. tabelas: nenhuma célula fica encoberta por célula fixa; em modo tabela,
     o contêiner que rola recebe foco (setas rolam) e todas as colunas são
     alcançáveis; em modo cartões, cada valor leva o rótulo da coluna; os botões
     de cada linha continuam presentes e clicáveis pelo teclado;
  3. KPIs: nunca estouram o cartão e a fonte não desce de 18px;
  4. NexoBot: o botão flutuante não cobre nenhum controle nem título, no topo e
     no fim da página, e some com a gaveta do menu aberta;
  5. sidebar: o ponto do item ativo não encosta no rótulo ("Base de Conhecimento");
  6. gráficos: rótulos sem reticências, sem corte e sem sobreposição, com
     alternativa textual (role="img" + aria-label);
  7. envio de relatórios: o campo de arquivo é alcançado pelo Tab, o foco fica
     visível na dropzone e enviar sem arquivo é barrado antes do POST;
  8. 404 dentro do portal: página do NEXO em português com link de volta
     (e JSON em /api/).

Rede: somente o servidor local; CDN respondida localmente (Bootstrap mínimo ou
cópias íntegras via NEXO_TEST_CDN_DIR, como em test_contratos_navegador). Plotly
não é carregado por padrão: as medições de gráfico só rodam quando a cópia local
existir (NEXO_TEST_CDN_DIR/plotly.min.js); caso contrário são puladas e o teste
registra a limitação. Habilitado por NEXO_TEST_BROWSER=1, como na CI.
"""

import os
import threading
import unittest
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from tests.contratos_support import ContratosCase
from tests.test_contratos_navegador import _BOOTSTRAP_MINIMO, _CDN, _copias_locais_da_cdn
from tests.test_nexobot_navegador import _CONECTAR_LOCAL

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # dependência opcional de desenvolvimento
    sync_playwright = None


_BROWSER = os.environ.get("NEXO_TEST_BROWSER") == "1" and sync_playwright is not None
_PLOTLY_URL = _CDN + "plotly.js-dist-min@2.35.2/plotly.min.js"

LARGURAS = ((320, 568), (360, 780), (390, 844), (768, 1024), (1024, 768), (1366, 768), (1536, 864), (1920, 1080))
ZOOM_150 = (911, 512, 1.5)  # 1366 px a 150%: viewport CSS menor, escala maior
NOME_LONGO = "Distribuidora Internacional de Materiais Elétricos, Hidráulicos e Ferragens do Vale do Paraíba Ltda"
FANTASIA_LONGA = "Distribuidora Internacional Vale do Paraíba (unidade matriz)"
EMAIL_LONGO = "financeiro.contabilidade.administrativo@distribuidora-internacional-materiais.example.invalid"
PRODUTOS_LONGOS = [
    "Kit presente premium de café especial torrado e moído com chocolate artesanal 70% cacau e caneca personalizada",
    "Caneca térmica inox 450 ml com tampa antivazamento e cabo emborrachado edição limitada",
    "Cesta de Natal grande com panetone artesanal, espumante e seleção de frutas secas importadas",
    "Café especial torra média 500 g lote único da fazenda experimental da serra",
    "Chá importado de folhas inteiras caixa com 20 sachês sortidos",
    "Biscoito amanteigado artesanal lata decorativa 400 g",
    "Geleia de frutas vermelhas sem açúcar 250 g",
    "Mel orgânico de flores silvestres 500 g",
    "Granola premium com castanhas 1 kg",
    "Água mineral com gás 500 ml",
]

def _linhas_necessarias(texto, por_linha):
    """Mesma quebra gulosa por palavras de NEXO.quebrarRotulo (templates/base.html)."""
    linhas, atual = [], ""
    for palavra in texto.split():
        if not atual:
            atual = palavra
        elif len(atual) + 1 + len(palavra) <= por_linha:
            atual += " " + palavra
        else:
            linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return len(linhas)


_MEDIR = """() => {
    const vw = innerWidth, vh = innerHeight;
    const rect = el => { const b = el.getBoundingClientRect(); return {x0: b.left, y0: b.top, x1: b.right, y1: b.bottom, w: b.width, h: b.height}; };
    const inter = (a, b) => Math.max(0, Math.min(a.x1, b.x1) - Math.max(a.x0, b.x0)) * Math.max(0, Math.min(a.y1, b.y1) - Math.max(a.y0, b.y0));
    const desc = el => el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\\s+/).slice(0, 2).join('.') : '');
    const visivel = el => { const cs = getComputedStyle(el); return cs.display !== 'none' && cs.visibility !== 'hidden' && cs.opacity !== '0'; };
    const tabelas = [...document.querySelectorAll('.table-responsive-x')].map(caixa => {
        const cr = rect(caixa);
        const fixas = [...caixa.querySelectorAll('th, td')].filter(c => getComputedStyle(c).position === 'sticky');
        let encobertas = 0;
        for (const fixa of fixas) {
            const fr = rect(fixa);
            for (const outra of caixa.querySelectorAll('th, td')) {
                if (outra === fixa || getComputedStyle(outra).position === 'sticky') continue;
                const o = rect(outra);
                const vis = {x0: Math.max(o.x0, cr.x0), x1: Math.min(o.x1, cr.x1), y0: o.y0, y1: o.y1};
                if (vis.x1 > vis.x0 && inter(vis, fr) > 4 * (o.y1 - o.y0)) encobertas++;
            }
        }
        const cartoes = caixa.classList.contains('em-cartoes');
        const ths = [...caixa.querySelectorAll('thead th')];
        const ultimaColuna = ths.length ? rect(ths[ths.length - 1]) : null;
        const semRotulo = cartoes ? [...caixa.querySelectorAll('tbody tr:not([style*="none"]) td:not([colspan])')]
            .filter(td => td.textContent.trim() && !td.classList.contains('celula-acoes') && !td.getAttribute('data-label')).length : 0;
        const botoesForaDoCartao = cartoes ? [...caixa.querySelectorAll('tbody a, tbody button')].filter(b => { const r = rect(b); const tr = rect(b.closest('tr')); return r.w && (r.x1 > tr.x1 + 1 || r.x0 < tr.x0 - 1); }).length : 0;
        return {rola: caixa.scrollWidth > caixa.clientWidth + 1, cartoes, encobertas, fixas: fixas.length,
                focavel: caixa.tabIndex === 0, colunas: ths.length, semRotulo, botoesForaDoCartao,
                ultimaAlcancavel: !ultimaColuna || cartoes || (ultimaColuna.x1 - cr.x0) <= caixa.scrollWidth + 1,
                largura_caixa: cr.w, dentroDaTela: cr.x0 >= -1 && cr.x1 <= vw + 1};
    });
    const kpis = [...document.querySelectorAll('.kpi-value')].map(el => ({
        texto: el.textContent.replace(/\\s+/g, ' ').trim(), fonte: parseFloat(getComputedStyle(el).fontSize),
        estoura: el.scrollWidth > el.clientWidth + 1}));
    const launcher = document.getElementById('nexobotLauncher');
    let nexobot = null;
    if (launcher && visivel(launcher)) {
        const lr = rect(launcher);
        const sobre = [...document.querySelectorAll('a, button, input, select, textarea, h1, h2, h3, .kpi-value, .sc-title')]
            .filter(el => el !== launcher && !el.closest('#nexobot') && visivel(el))
            .map(el => ({el, b: rect(el)})).filter(o => o.b.w && o.b.h && inter(o.b, lr) > 0)
            .map(o => desc(o.el) + ' "' + o.el.textContent.replace(/\\s+/g, ' ').trim().slice(0, 30) + '"');
        nexobot = {sobre, dentroDaTela: lr.x1 <= vw + 1 && lr.y1 <= vh + 1};
    }
    const ativo = document.querySelector('.sidebar .nav-item.active');
    let sidebar = null;
    if (ativo) {
        const textos = [...ativo.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim());
        const rg = document.createRange(); rg.selectNodeContents(textos[textos.length - 1]);
        const tb = rg.getBoundingClientRect();
        const cs = getComputedStyle(ativo, '::after');
        const ar = rect(ativo);
        let folga = null;
        if (cs.content !== 'none' && parseFloat(cs.width) > 0 && cs.position === 'absolute') {
            folga = (ar.x1 - (parseFloat(cs.right) || 0) - parseFloat(cs.width)) - tb.right;
        }
        sidebar = {folga, fluxo: cs.position !== 'absolute', rotulo: ativo.textContent.trim(), texto_direita: tb.right, item_direita: ar.x1};
    }
    const fora = [];
    for (const el of document.querySelectorAll('main.page *')) {
        if (el.closest('script, style, template, svg')) continue;
        if (!visivel(el)) continue;
        const b = el.getBoundingClientRect(); if (!b.width || !b.height) continue;
        let clip = false;
        for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) { if (getComputedStyle(p).overflowX !== 'visible') { clip = true; break; } }
        if (!clip && (b.left < -1 || b.right > vw + 1)) fora.push(desc(el));
    }
    const graficos = [...document.querySelectorAll('.chart-box')].map(c => {
        const cr = rect(c);
        const ticks = [...c.querySelectorAll('.xtick text, .ytick text')].map(t => ({texto: t.textContent, b: rect(t)}));
        const cortados = ticks.filter(t => t.b.x0 < cr.x0 - 1 || t.b.x1 > cr.x1 + 1 || t.b.y1 > cr.y1 + 1).map(t => t.texto);
        const xt = ticks.filter(t => t.texto).sort((a, b) => a.b.x0 - b.b.x0);
        let sobrepostos = 0;
        for (let i = 1; i < xt.length; i++) if (xt[i].b.x0 < xt[i - 1].b.x1 - 1 && Math.abs(xt[i].b.y0 - xt[i - 1].b.y0) < 2 && Math.abs(xt[i].b.x0 - xt[i-1].b.x0) > 0) sobrepostos++;
        return {id: c.id, w: Math.round(cr.w), desenhado: !!c.querySelector('.main-svg'), truncados: ticks.filter(t => /…$/.test(t.texto)).length,
                cortados: cortados.slice(0, 5), sobrepostos, papel: c.getAttribute('role'), rotulo: (c.getAttribute('aria-label') || '').length};
    });
    return {rolagem_x: document.documentElement.scrollWidth > vw + 1, tabelas, kpis, nexobot, sidebar, fora: fora.slice(0, 10), graficos};
}"""


@unittest.skipUnless(_BROWSER, "Defina NEXO_TEST_BROWSER=1 e instale o Playwright para os testes de navegador.")
class OverflowNavegadorTests(ContratosCase):
    def setUp(self):
        super().setUp()
        self.dados_extensos()
        from werkzeug.serving import make_server
        for alvo, original in _CONECTAR_LOCAL.items():
            self.stack.enter_context(patch(alvo, original))
        self.servidor = make_server("127.0.0.1", 0, self.app, threaded=True)
        self.base = f"http://127.0.0.1:{self.servidor.server_port}"
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()
        self.addCleanup(self._parar_servidor)
        self.pw = sync_playwright().start()
        self.addCleanup(self.pw.stop)
        self.navegador = self.pw.chromium.launch(executable_path=os.environ.get("NEXO_TEST_CHROMIUM") or None)
        self.addCleanup(self.navegador.close)
        self.cdn_local = _copias_locais_da_cdn()
        pasta = os.environ.get("NEXO_TEST_CDN_DIR")
        plotly = Path(pasta) / "plotly.min.js" if pasta else None
        self.plotly_local = str(plotly) if plotly and plotly.is_file() else None
        self.erros_js = []

    def _parar_servidor(self):
        self.servidor.shutdown()
        self.servidor.server_close()

    def tearDown(self):
        self.assertEqual(self.erros_js, [], "Erros de JavaScript no console")

    # ------------------------------------------------------------ dados
    def dados_extensos(self):
        """Nomes, e-mails e produtos longos; faturamento de nove dígitos; uma empresa
        na lixeira; dois chamados; duas análises publicadas (histórico com 2 pontos)."""
        from models import Analise, ChamadoSuporte, Empresa, MensagemSuporte, Plano, ProdutoCurvaABC, Segmento
        s = self.db.session
        plano = s.scalar(self.db.select(Plano))
        segmento = Segmento(nome_segmento="MATERIAIS_DE_CONSTRUCAO_E_ACABAMENTOS")
        s.add(segmento)
        s.flush()
        longa = Empresa(id_segmento=segmento.id_segmento, id_plano_atual=plano.id_plano, cnpj="99000000000199",
                        razao_social=NOME_LONGO, nome_fantasia=FANTASIA_LONGA, email_contato=EMAIL_LONGO,
                        data_contratacao=date(2026, 1, 1))
        lixo = Empresa(id_segmento=segmento.id_segmento, id_plano_atual=plano.id_plano, cnpj="99000000000198",
                       razao_social="Empresa fictícia removida com razão social bastante extensa para testes Ltda ME",
                       nome_fantasia="Removida Demo", email_contato="removida@example.invalid",
                       data_contratacao=date(2026, 1, 1), deletado_em=datetime(2026, 2, 20, 15, 30))
        s.add_all([longa, lixo])
        s.flush()
        self.contratar(empresa_id=longa.id_empresa)
        # Referência sem espaços (140 caracteres): no modo cartões ela precisa quebrar
        # dentro do cartão, não vazar dele.
        self.pagar(date(2026, 1, 1), date(2026, 1, 31), empresa_id=longa.id_empresa,
                   referencia="Comprovante-fictício-" + "X" * 120)
        # Análise do cliente: indicadores grandes, devolutiva e Curva ABC com nomes longos.
        self.publicar(self.analise_id, inicio=date(2026, 1, 1), fim=date(2026, 1, 31))
        anterior = self.nova_analise(date(2025, 12, 1), date(2025, 12, 31))
        self.publicar(anterior.id_analise, inicio=date(2025, 12, 1), fim=date(2025, 12, 31))
        analise = s.get(Analise, self.analise_id)
        ind = analise.indicador
        ind.faturamento_total = Decimal("123456789.12")
        ind.total_comprado = Decimal("98765432.10")
        ind.saldo_estimado_compras_vendas = Decimal("-24691357.02")
        ind.produto_mais_vendido_nome = PRODUTOS_LONGOS[0]
        ind.produto_mais_vendido_quantidade = Decimal("1234567")
        ind.produto_maior_faturamento_nome = PRODUTOS_LONGOS[1]
        ind.produto_maior_faturamento_valor = Decimal("12345678.90")
        ind.produto_maior_saldo_parado_nome = PRODUTOS_LONGOS[2]
        total = Decimal("123456789.12")
        acumulado = Decimal("0")
        for pos, nome in enumerate(PRODUTOS_LONGOS, 1):
            fat = (total * Decimal(11 - pos) / Decimal(55)).quantize(Decimal("0.01"))
            perc = (fat / total * 100).quantize(Decimal("0.01"))
            acumulado += perc
            s.add(ProdutoCurvaABC(id_analise=analise.id_analise, posicao_ranking=pos, produto_nome=nome,
                                  quantidade=Decimal(1000 * (11 - pos)), faturamento=fat,
                                  percentual_individual=perc, percentual_acumulado=min(acumulado, Decimal("100")),
                                  classe_abc="A" if acumulado <= 80 else ("B" if acumulado <= 95 else "C")))
        # Período em aberto: a página "Enviar relatórios" mostra as dropzones.
        self.nova_analise(date(2026, 2, 1), date(2026, 2, 28))
        for i, (assunto, status) in enumerate([
                ("Erro ao enviar planilha de compras em formato XLSX com várias abas e colunas mescladas", "ABERTO"),
                ("Dúvida sobre o indicador de pressão de estoque do último período", "RESOLVIDO")]):
            chamado = ChamadoSuporte(id_empresa=self.empresa_id, id_usuario_cliente=self.cliente_id, assunto=assunto,
                                     categoria="ERRO_INTEGRACAO" if i == 0 else "DUVIDA_TECNICA", status_chamado=status,
                                     prioridade="MEDIA", data_abertura=datetime(2026, 2, 10 + i, 14, 20),
                                     data_atualizacao=datetime(2026, 2, 11 + i, 9, 5))
            s.add(chamado)
            s.flush()
            s.add(MensagemSuporte(id_chamado=chamado.id_chamado, id_usuario_remetente=self.cliente_id,
                                  mensagem="Mensagem fictícia.", data_envio=datetime(2026, 2, 10 + i, 14, 20)))
        s.commit()
        self.empresa_longa_id = longa.id_empresa

    # ------------------------------------------------------------ navegador
    def _rota(self, rota):
        requisicao = rota.request
        url = requisicao.url
        if url.startswith(self.base + "/"):
            rota.continue_()
        elif url in self.cdn_local:
            caminho, tipo = self.cdn_local[url]
            rota.fulfill(status=200, path=caminho, content_type=tipo)
        elif url == _PLOTLY_URL and self.plotly_local:
            rota.fulfill(status=200, path=self.plotly_local, content_type="application/javascript")
        elif url == _CDN + "bootstrap@5.3.3/dist/css/bootstrap.min.css":
            rota.fulfill(status=200, content_type="text/css", body=_BOOTSTRAP_MINIMO)
        elif requisicao.resource_type == "stylesheet":
            rota.fulfill(status=200, content_type="text/css", body="")
        elif requisicao.resource_type == "script":
            rota.fulfill(status=200, content_type="application/javascript", body="")
        else:
            rota.abort()

    def abrir(self, largura, altura, escala=1):
        contexto = self.navegador.new_context(viewport={"width": largura, "height": altura}, device_scale_factor=escala,
                                              reduced_motion="reduce", locale="pt-BR", timezone_id="America/Sao_Paulo")
        self.addCleanup(contexto.close)
        pagina = contexto.new_page()
        pagina.on("pageerror", lambda erro: self.erros_js.append(f"{largura}px: {erro}"))
        pagina.on("console", lambda msg: self.erros_js.append(f"{largura}px console: {msg.text}")
                  if msg.type == "error" and "404 (NOT FOUND)" not in msg.text else None)
        pagina.route("**/*", self._rota)
        return pagina

    def entrar(self, pagina, email):
        pagina.goto(self.base + "/auth/login", wait_until="load")
        pagina.fill("#email", email)
        pagina.fill("#senha", self.password)
        with pagina.expect_navigation(wait_until="load"):
            pagina.click("button[type=submit]")

    def ir(self, pagina, caminho, status=200):
        resposta = pagina.goto(self.base + caminho, wait_until="load")
        self.assertEqual(resposta.status, status, caminho)
        pagina.wait_for_timeout(150)  # o ajuste de layout do shell roda após as fontes
        return resposta

    def medir(self, pagina):
        return pagina.evaluate(_MEDIR)

    # ------------------------------------------------------------ asserções
    def assert_layout(self, pagina, largura, contexto):
        m = self.medir(pagina)
        self.assertFalse(m["rolagem_x"], f"{contexto}: a página rola na horizontal")
        self.assertEqual(m["fora"], [], f"{contexto}: elementos fora da tela")
        for t in m["tabelas"]:
            self.assertEqual(t["encobertas"], 0, f"{contexto}: célula encoberta por célula fixa ({t})")
            self.assertEqual(t["fixas"], 0, f"{contexto}: ainda há célula fixa ({t})")
            self.assertTrue(t["dentroDaTela"], f"{contexto}: tabela fora da tela ({t})")
            if t["rola"] and not t["cartoes"]:
                self.assertTrue(t["focavel"], f"{contexto}: tabela que rola sem foco pelo teclado ({t})")
                self.assertTrue(t["ultimaAlcancavel"], f"{contexto}: última coluna inalcançável ({t})")
            if t["cartoes"]:
                self.assertEqual(t["semRotulo"], 0, f"{contexto}: valor sem rótulo nos cartões ({t})")
                self.assertEqual(t["botoesForaDoCartao"], 0, f"{contexto}: botão fora do cartão ({t})")
        for k in m["kpis"]:
            self.assertFalse(k["estoura"], f"{contexto}: KPI estourando ({k})")
            self.assertGreaterEqual(k["fonte"], 18, f"{contexto}: KPI ilegível ({k})")
        if m["nexobot"]:
            self.assertTrue(m["nexobot"]["dentroDaTela"], f"{contexto}: NexoBot fora da tela")
        if m["sidebar"] and m["sidebar"]["folga"] is not None:
            self.assertGreaterEqual(m["sidebar"]["folga"], 6, f"{contexto}: indicador da sidebar no rótulo ({m['sidebar']})")
        # Nomes de produto cabem em até 3 linhas (de ~18 caracteres no celular, ~26 no
        # computador, quebradas nas palavras como faz NEXO.quebrarRotulo); só os que
        # precisariam de mais linhas podem terminar em reticências, e o nome completo
        # fica na tooltip, na descrição acessível e na tabela ABC.
        for g in m["graficos"]:
            if not g["desenhado"]:
                continue
            # O gráfico decide o modo pela própria largura (< 560 px = estreito), não pela do viewport.
            por_linha = 18 if g["w"] < 560 else 26
            truncaveis = sum(1 for nome in PRODUTOS_LONGOS if _linhas_necessarias(nome, por_linha) > 3)
            permitidos = truncaveis if "Abc" in g["id"] else 0
            self.assertLessEqual(g["truncados"], permitidos, f"{contexto}: rótulo truncado em {g['id']}")
            self.assertEqual(g["cortados"], [], f"{contexto}: rótulo cortado em {g['id']}")
            self.assertEqual(g["sobrepostos"], 0, f"{contexto}: rótulos sobrepostos em {g['id']}")
            self.assertEqual(g["papel"], "img", f"{contexto}: gráfico sem alternativa textual ({g['id']})")
            self.assertGreater(g["rotulo"], 20, f"{contexto}: descrição vazia em {g['id']}")
        return m

    def assert_fim_da_pagina(self, pagina, contexto):
        """No fim da página o NexoBot não cobre nada (há espaço reservado); no meio da
        página o que fica sob o botão sai de baixo dele com a rolagem, como em qualquer
        botão flutuante, então a medição do topo só vale para páginas que não rolam."""
        rola = pagina.evaluate("document.documentElement.scrollHeight > innerHeight + 1")
        if not rola:
            m = self.medir(pagina)
            if m["nexobot"]:
                self.assertEqual(m["nexobot"]["sobre"], [], f"{contexto} (página sem rolagem): NexoBot sobre controle/título")
        pagina.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
        pagina.wait_for_timeout(100)
        m = self.medir(pagina)
        if m["nexobot"]:
            self.assertEqual(m["nexobot"]["sobre"], [], f"{contexto} (fim da página): NexoBot sobre controle/título")
        pagina.evaluate("window.scrollTo(0, 0)")

    # ------------------------------------------------------------ cenários
    def paginas_admin(self):
        return ["/admin/dashboard", "/admin/empresas", "/admin/analises", "/admin/lixeira", "/admin/contratos",
                "/admin/tickets", "/admin/guia", f"/admin/empresas/{self.empresa_longa_id}/detalhes"]

    def paginas_cliente(self):
        return ["/cliente/dashboard", f"/cliente/analise/{self.analise_id}", "/cliente/historico", "/cliente/upload",
                "/cliente/tickets", "/cliente/guia"]

    def test_admin_sem_cortes_em_todas_as_larguras(self):
        for largura, altura in LARGURAS:
            pagina = self.abrir(largura, altura)
            self.entrar(pagina, "admin-test@example.invalid")
            for caminho in self.paginas_admin():
                self.ir(pagina, caminho)
                self.assert_layout(pagina, largura, f"{caminho} @ {largura}px")
            pagina.context.close()

    def test_cliente_sem_cortes_em_todas_as_larguras(self):
        for largura, altura in LARGURAS:
            pagina = self.abrir(largura, altura)
            self.entrar(pagina, "cliente-test@example.invalid")
            for caminho in self.paginas_cliente():
                self.ir(pagina, caminho)
                self.assert_layout(pagina, largura, f"{caminho} @ {largura}px")
                self.assert_fim_da_pagina(pagina, f"{caminho} @ {largura}px")
            pagina.context.close()

    def test_zoom_150_por_cento(self):
        largura, altura, escala = ZOOM_150
        pagina = self.abrir(largura, altura, escala)
        self.entrar(pagina, "admin-test@example.invalid")
        for caminho in ("/admin/analises", "/admin/lixeira", "/admin/empresas"):
            self.ir(pagina, caminho)
            self.assert_layout(pagina, largura, f"{caminho} @ zoom 150%")

    def test_tabela_de_analises_mostra_todas_as_colunas(self):
        """A 1366 px (notebook) e 1920 px: as nove colunas de Análises existem, nenhuma
        fica encoberta e, se a tabela rolar, a última coluna chega à vista pelo teclado."""
        for largura, altura in ((1366, 768), (1920, 1080)):
            pagina = self.abrir(largura, altura)
            self.entrar(pagina, "admin-test@example.invalid")
            self.ir(pagina, "/admin/analises")
            m = self.assert_layout(pagina, largura, f"/admin/analises @ {largura}px")
            tabela = m["tabelas"][0]
            self.assertEqual(tabela["colunas"], 9, tabela)
            rotulos = pagina.locator("#tabelaAnalises thead th").all_text_contents()
            self.assertEqual([r.strip() for r in rotulos],
                             ["Empresa", "Período", "Tipo", "Quinzena", "Status", "Uploads", "Criação", "Publicado", "Ações"])
            if tabela["rola"] and not tabela["cartoes"]:
                caixa = pagina.locator(".table-responsive-x").first
                caixa.focus()
                for _ in range(40):
                    pagina.keyboard.press("ArrowRight")
                visivel = pagina.evaluate("""() => { const c = document.querySelector('.table-responsive-x');
                    const th = c.querySelector('thead th:last-child').getBoundingClientRect(); const cr = c.getBoundingClientRect();
                    return th.right <= cr.right + 1 && th.left >= cr.left - 1; }""")
                self.assertTrue(visivel, "a coluna Ações não chegou à vista com as setas")
            # O botão "Abrir" da primeira linha é alcançado pelo Tab e abre a análise.
            pagina.locator("#tabelaAnalises tbody tr").first.locator("a.btn-ghost").first.focus()
            self.assertEqual(pagina.evaluate("document.activeElement.textContent.trim()"), "Abrir")
            pagina.context.close()

    def test_lixeira_data_de_remocao_legivel_e_acoes_separadas(self):
        for largura, altura in ((1366, 768), (390, 844)):
            pagina = self.abrir(largura, altura)
            self.entrar(pagina, "admin-test@example.invalid")
            self.ir(pagina, "/admin/lixeira")
            self.assert_layout(pagina, largura, f"/admin/lixeira @ {largura}px")
            celula = pagina.locator(".nexo-table tbody tr").first.locator("td").nth(5)
            self.assertIn("20/02/2026 15:30", celula.text_content())
            caixa = celula.evaluate("td => { const r = td.getBoundingClientRect(); const c = td.closest('.table-responsive-x').getBoundingClientRect(); return [r.left, r.right, c.left, c.right, c.scrollWidth]; }")
            # A data cabe por inteiro na área visível ou é alcançável pela rolagem (nunca encoberta).
            self.assertGreaterEqual(caixa[1] - caixa[0], 100, caixa)
            botoes = pagina.locator(".nexo-table tbody tr").first.locator(".acoes button")
            self.assertEqual(botoes.count(), 2)
            r1, r2 = (botoes.nth(i).evaluate("b => { const r = b.getBoundingClientRect(); return [r.left, r.right, r.top, r.bottom]; }") for i in (0, 1))
            separados = r1[1] + 4 <= r2[0] or r2[1] + 4 <= r1[0] or r1[3] + 4 <= r2[2] or r2[3] + 4 <= r1[2]
            self.assertTrue(separados, (r1, r2))
            botoes.nth(1).click()
            pagina.wait_for_selector("#confirmPurgeModal.show")
            self.assertIn("Removida Demo", pagina.locator("#confirmPurgeNome").text_content())
            pagina.keyboard.press("Escape")
            pagina.wait_for_selector("#confirmPurgeModal", state="hidden")
            pagina.context.close()

    def test_empresas_filtro_por_empresa_vindo_da_lista(self):
        pagina = self.abrir(1440, 900)
        self.entrar(pagina, "admin-test@example.invalid")
        self.ir(pagina, f"/admin/analises?empresa={self.empresa_id}")
        self.assertEqual(pagina.locator("#filtroEmpresa").input_value(), str(self.empresa_id))
        visiveis = pagina.evaluate("[...document.querySelectorAll('#tabelaAnalises tbody tr[data-empresa]')].filter(r => r.style.display !== 'none').map(r => r.dataset.empresa)")
        self.assertTrue(visiveis and all(v == str(self.empresa_id) for v in visiveis), visiveis)
        self.ir(pagina, "/admin/empresas")
        href = pagina.locator("#tabelaEmpresas tbody tr").first.locator("a", has_text="Análises").get_attribute("href")
        self.assertIn("/admin/analises?empresa=", href)
        # Busca: filtra pelos dados, não pelos rótulos dos botões; "Limpar busca" volta ao normal.
        pagina.fill("#buscaEmpresa", "análises")
        self.assertTrue(pagina.locator("#semResultados").is_visible())
        pagina.click("#limparBusca")
        self.assertFalse(pagina.locator("#semResultados").is_visible())
        self.assertEqual(pagina.locator("#buscaEmpresa").input_value(), "")

    def test_sidebar_item_longo_nao_encosta_no_indicador(self):
        pagina = self.abrir(1440, 900)
        self.entrar(pagina, "admin-test@example.invalid")
        self.ir(pagina, "/admin/guia")
        m = self.medir(pagina)
        self.assertEqual(m["sidebar"]["rotulo"], "Base de Conhecimento", m["sidebar"])
        self.assertTrue(m["sidebar"]["fluxo"], "o indicador deve ser um item do flex, não absoluto")
        self.assertLessEqual(m["sidebar"]["texto_direita"] + 6 + 12, m["sidebar"]["item_direita"] + 1, m["sidebar"])

    def test_upload_acessivel_pelo_teclado_e_sem_envio_vazio(self):
        pagina = self.abrir(1366, 768)
        self.entrar(pagina, "cliente-test@example.invalid")
        self.ir(pagina, "/cliente/upload")
        campos = pagina.locator("input[type=file][data-dz-input]")
        self.assertGreaterEqual(campos.count(), 2)
        # Tab a partir do início do conteúdo chega ao campo de arquivo em poucas paradas.
        pagina.focus("#conteudo")
        alcancou = False
        for _ in range(12):
            pagina.keyboard.press("Tab")
            if pagina.evaluate("document.activeElement.matches('input[type=file][data-dz-input]')"):
                alcancou = True
                break
        self.assertTrue(alcancou, "o campo de arquivo não entrou na ordem de Tab")
        foco_visivel = pagina.evaluate("""() => { const dz = document.activeElement.closest('.dropzone');
            const cs = getComputedStyle(dz); return cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) >= 2; }""")
        self.assertTrue(foco_visivel, "o foco no campo de arquivo não aparece na dropzone")

    def test_upload_sem_arquivo_nao_faz_post(self):
        pagina = self.abrir(1366, 768)
        self.entrar(pagina, "cliente-test@example.invalid")
        self.ir(pagina, "/cliente/upload")
        posts = []
        pagina.on("request", lambda r: posts.append(r.url) if r.method == "POST" else None)
        pagina.locator("form:has(input[type=file]) button[type=submit]").first.click()
        pagina.wait_for_timeout(300)
        self.assertEqual(posts, [])
        erro = pagina.locator(".dropzone.is-erro .dz-erro").first
        self.assertTrue(erro.is_visible())
        self.assertIn("Selecione um arquivo", erro.text_content())
        # Arquivo inválido é recusado antes do envio; arquivo válido aparece como selecionado.
        campo = pagina.locator("input[type=file][data-dz-input]").first
        campo.set_input_files({"name": "relatorio.pdf", "mimeType": "application/pdf", "buffer": b"%PDF-1.4"})
        self.assertIn("Formato não aceito", pagina.locator(".dropzone .dz-erro").first.text_content())
        campo.set_input_files({"name": "vendas-janeiro.csv", "mimeType": "text/csv", "buffer": b"produto;qtd\n"})
        self.assertIn("vendas-janeiro.csv", pagina.locator(".dropzone .dz-title").first.text_content())
        self.assertIn("Selecionado para envio", pagina.locator(".dropzone .dz-estado").first.text_content())

    def test_pagina_nao_encontrada_dentro_do_portal(self):
        pagina = self.abrir(1366, 768)
        self.entrar(pagina, "cliente-test@example.invalid")
        resposta = pagina.goto(self.base + "/cliente/analise/999999", wait_until="load")
        self.assertEqual(resposta.status, 404)
        self.assertEqual(pagina.locator("html").get_attribute("lang"), "pt-BR")
        self.assertIn("Página não encontrada", pagina.locator("h1").text_content())
        self.assertTrue(pagina.locator("a", has_text="Voltar ao painel").is_visible())
        self.assertNotIn("Not Found", pagina.content())
        self.erros_js = [e for e in self.erros_js if "404" not in e]

    def test_paginas_publicas_sem_rolagem_horizontal(self):
        """Landing, login e "Como aderir": só regressão de layout (sem reformulação)."""
        for largura, altura in ((320, 568), (390, 844), (1366, 768)):
            pagina = self.abrir(largura, altura)
            for caminho in ("/", "/auth/login", "/como-aderir"):
                self.ir(pagina, caminho)
                pagina.wait_for_timeout(300)
                medida = pagina.evaluate("""() => ({rola: document.documentElement.scrollWidth > innerWidth + 1,
                    fora: [...document.querySelectorAll('a, button, input, h1, h2')].filter(el => {
                        const b = el.getBoundingClientRect(); const cs = getComputedStyle(el);
                        return b.width && cs.visibility !== 'hidden' && (b.left < -1 || b.right > innerWidth + 1); }).length})""")
                self.assertFalse(medida["rola"], f"{caminho} @ {largura}px rola na horizontal")
                self.assertEqual(medida["fora"], 0, f"{caminho} @ {largura}px: controle fora da tela")
            pagina.context.close()

    def test_nexobot_some_com_a_gaveta_aberta(self):
        pagina = self.abrir(390, 844)
        self.entrar(pagina, "cliente-test@example.invalid")
        self.ir(pagina, "/cliente/dashboard")
        pagina.click("#navToggle")
        pagina.wait_for_timeout(400)
        escondido = pagina.evaluate("getComputedStyle(document.getElementById('nexobotLauncher')).visibility === 'hidden'")
        self.assertTrue(escondido, "o NexoBot deve sumir com a gaveta aberta")
        self.assertTrue(pagina.locator(".sidebar .nav-logout").is_visible())
        pagina.keyboard.press("Escape")
        pagina.wait_for_timeout(400)
        self.assertFalse(pagina.evaluate("getComputedStyle(document.getElementById('nexobotLauncher')).visibility === 'hidden'"))


class PaginasDeErroTests(ContratosCase):
    """Sem navegador: as páginas de erro do portal e o JSON das chamadas /api/."""

    def _token(self, cliente, caminho="/auth/login"):
        import re
        pagina = cliente.get(caminho).get_data(as_text=True)
        return re.search(r'name="csrf_token" value="([^"]+)"', pagina).group(1)

    def _entrar(self, cliente, email):
        resposta = cliente.post("/auth/login", data={"csrf_token": self._token(cliente), "email": email, "senha": self.password})
        self.assertEqual(resposta.status_code, 302, resposta.get_data(as_text=True)[:300])

    def test_404_em_portugues_com_link_de_volta(self):
        cliente = self.app.test_client()
        self._entrar(cliente, "cliente-test@example.invalid")
        resposta = cliente.get("/cliente/analise/999999")
        self.assertEqual(resposta.status_code, 404)
        corpo = resposta.get_data(as_text=True)
        self.assertIn("Página não encontrada", corpo)
        self.assertIn('lang="pt-BR"', corpo)
        self.assertIn("Voltar ao painel", corpo)
        self.assertNotIn("Not Found", corpo)
        # Sem sessão: link para o início e para o login.
        anonimo = self.app.test_client().get("/pagina-que-nao-existe")
        self.assertEqual(anonimo.status_code, 404)
        self.assertIn("Entrar no portal", anonimo.get_data(as_text=True))

    def test_api_devolve_json(self):
        cliente = self.app.test_client()
        self._entrar(cliente, "cliente-test@example.invalid")
        resposta = cliente.get("/api/rota-inexistente")
        self.assertEqual(resposta.status_code, 404)
        self.assertEqual(resposta.get_json()["fonte"], "local")

    def test_email_volta_preenchido_apos_senha_errada(self):
        cliente = self.app.test_client()
        resposta = cliente.post("/auth/login", data={"csrf_token": self._token(cliente),
                                                     "email": "alguem@example.invalid", "senha": "errada"})
        corpo = resposta.get_data(as_text=True)
        self.assertIn('value="alguem@example.invalid"', corpo)
        self.assertIn("E-mail ou senha incorretos", corpo)
