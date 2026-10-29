"""
NEXO - Faturamento Inteligente | Exportação da Análise Executiva em PDF
======================================================================
Gera, com ReportLab (platypus), o PDF da análise publicada: cabeçalho da marca,
indicadores, Curva ABC (Top 5), síntese executiva em semáforos (5W2H) e a
devolutiva do consultor.

Layout claro (fundo branco) — apropriado para impressão/anexo — com os acentos
de cor da identidade NEXO (roxo) e o mesmo código de cores da app para as
classes ABC e os semáforos. Mantém a regra: sem lucro/margem/CMV.

Paginação: o conteúdo ocupa exatamente a área entre as margens (quadro sem
recuo interno); nenhum título fica sozinho no fim de uma página — cada título
viaja com o primeiro bloco do seu conteúdo —, blocos curtos (indicadores,
tabela, cada cartão) não se partem e os textos longos da
devolutiva quebram entre páginas normalmente. O rodapé de todas as páginas traz
"Página X de Y".

Função pública:
    gerar_pdf_analise(analise, semaforos, abc_top) -> bytes
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO
import re
from xml.sax.saxutils import escape

from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate, Flowable, Frame, KeepTogether, PageTemplate, Paragraph, Spacer,
    Table, TableStyle,
)

# ---- Paleta NEXO ----
ROXO = HexColor("#7c3aed")
ROXO2 = HexColor("#a855f7")
LAVANDA = HexColor("#ede9fb")
TINTA = HexColor("#1f2330")
CINZA = HexColor("#6a7088")
LINHA = HexColor("#e6e8ef")
FUNDO_SUAVE = HexColor("#f5f6fa")

CLASSE_COR = {"A": HexColor("#22c55e"), "B": HexColor("#f59e0b"), "C": HexColor("#9aa0b7")}
SEMAFORO_COR = {
    "critico": HexColor("#ef4444"),
    "atencao": HexColor("#f59e0b"),
    "oportunidade": HexColor("#22c55e"),
}
SEMAFORO_FUNDO = {
    "critico": HexColor("#fdecec"),
    "atencao": HexColor("#fdf4e3"),
    "oportunidade": HexColor("#e9f9ef"),
}
SEMAFORO_ROTULO = {"critico": "CRÍTICO", "atencao": "ATENÇÃO", "oportunidade": "OPORTUNIDADE"}

TOP_N_PDF = 5                      # a tabela mostra os 5 primeiros produtos da Curva ABC

# ---- Geometria da página (A4, pontos) ----
MARGEM_X = 18 * mm
MARGEM_TOPO = 15 * mm
MARGEM_BASE = 24 * mm        # área reservada ao rodapé (régua em 17 mm, textos em 12,5 e 8,5 mm)
AVISO_RODAPE = ("Sinalização gerencial estimada (faturamento e Curva ABC). Não representa "
                "lucro, margem ou CMV.")


# ---- Formatação ----
def _texto_pdf(valor) -> str:
    """Escapa um valor externo uma única vez, na entrada de um Paragraph.

    O parser do ReportLab aceita marcação que pode carregar imagens e criar
    links. Dados comerciais são texto literal; somente a marcação fixa deste
    módulo é confiável. Não usar este escape em strings desenhadas no canvas
    ou em células de Table que não sejam Paragraphs.
    """
    return escape("" if valor is None else str(valor))


def _decimal(valor) -> Decimal | None:
    """Decimal finito a partir de Decimal/float/int/str; None se ausente ou inválido."""
    if valor is None:
        return None
    try:
        numero = valor if isinstance(valor, Decimal) else Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return numero if numero.is_finite() else None


def _brl(valor) -> str:
    """12345.6 -> '12.345,60' (sem o símbolo), arredondando ao centavo (meio para cima)."""
    numero = _decimal(valor) or Decimal(0)
    texto = f"{numero.quantize(Decimal('0.01'), ROUND_HALF_UP):,.2f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def _num(valor) -> str:
    try:
        return f"{float(valor or 0):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "0"


def _tamanho_que_cabe(texto, fonte, tamanho, largura, minimo=8.0) -> float:
    """Maior corpo (até `tamanho`) em que `texto` cabe em `largura`."""
    while tamanho > minimo and stringWidth(texto, fonte, tamanho) > largura:
        tamanho -= 0.5
    return tamanho


def _encurtar(texto, fonte, tamanho, largura) -> str:
    """Corta com reticências para caber numa linha desenhada no canvas."""
    texto = " ".join(str(texto or "").split())
    if stringWidth(texto, fonte, tamanho) <= largura:
        return texto
    while texto and stringWidth(texto + "…", fonte, tamanho) > largura:
        texto = texto[:-1]
    return texto.rstrip() + "…"


# ---- Cabeçalho e rodapé ----
class _BarraTopo(Flowable):
    """Faixa roxa de cabeçalho com a marca NEXO.

    Declara o próprio tamanho em wrap(): sem isso o Flowable mede 0 × 0 e a
    faixa é desenhada acima do quadro, fora da página (o defeito do cabeçalho
    cortado). Todo o desenho fica dentro de 0 <= y <= ALTURA.
    """
    ALTURA = 22 * mm
    RECUO = 10 * mm

    def __init__(self, largura, titulo, subtitulo):
        super().__init__()
        self.largura = largura
        self.altura = self.ALTURA
        self.titulo = titulo
        self.subtitulo = subtitulo
        self.width, self.height = largura, self.ALTURA

    def wrap(self, availWidth, availHeight):
        self.width = min(self.largura, availWidth)
        self.height = self.altura
        return self.width, self.height

    def draw(self):
        c = self.canv
        largura, altura = self.width, self.height
        c.saveState()
        c.setFillColor(ROXO)
        c.roundRect(0, 0, largura, altura, 6, stroke=0, fill=1)
        # Marca à esquerda (empilhada) e identificação do documento à direita,
        # ambas centradas verticalmente na faixa.
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 20)
        c.drawString(self.RECUO, 11.2 * mm, "NEXO")
        c.setFillColor(LAVANDA)
        c.setFont("Helvetica", 8.5)
        c.drawString(self.RECUO, 6.0 * mm, "Faturamento Inteligente")
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 12)
        c.drawRightString(largura - self.RECUO, 12.0 * mm, self.titulo)
        c.setFillColor(LAVANDA)
        c.setFont("Helvetica", 8.5)
        c.drawRightString(largura - self.RECUO, 6.6 * mm, self.subtitulo)
        c.restoreState()


def _desenhar_rodape(canvas, pagina, total, identificacao):
    """Rodapé de todas as páginas: aviso, 'Página X de Y' e identificação."""
    x0, x1 = MARGEM_X, A4[0] - MARGEM_X
    canvas.saveState()
    canvas.setStrokeColor(LINHA)
    canvas.setLineWidth(0.5)
    canvas.line(x0, 17 * mm, x1, 17 * mm)
    numeracao = f"Página {pagina} de {total}"
    canvas.setFont("Helvetica-Bold", 7.5)
    canvas.setFillColor(TINTA)
    canvas.drawRightString(x1, 12.5 * mm, numeracao)
    espaco = x1 - x0 - stringWidth(numeracao, "Helvetica-Bold", 7.5) - 6 * mm
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(CINZA)
    canvas.drawString(x0, 12.5 * mm, _encurtar(AVISO_RODAPE, "Helvetica", 7.5, espaco))
    canvas.setFont("Helvetica", 7)
    canvas.drawString(x0, 8.5 * mm, _encurtar(identificacao, "Helvetica", 7, x1 - x0))
    canvas.restoreState()


def _canvas_com_rodape(identificacao):
    """Canvas que adia o rodapé até o fim do documento para conhecer o total de páginas."""
    class _CanvasNexo(Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._paginas_pendentes = []

        def showPage(self):
            self._paginas_pendentes.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._paginas_pendentes)
            for estado in self._paginas_pendentes:
                self.__dict__.update(estado)
                _desenhar_rodape(self, self._pageNumber, total, identificacao)
                super().showPage()
            super().save()

    return _CanvasNexo


# ---- Estilos ----
def _estilos():
    ss = getSampleStyleSheet()
    base = ss["Normal"]
    base.fontName = "Helvetica"
    base.textColor = TINTA
    estilos = {
        "titulo": ParagraphStyle("titulo", parent=base, fontName="Helvetica-Bold", fontSize=16,
                                 leading=20, textColor=TINTA, spaceAfter=4),
        "h2": ParagraphStyle("h2", parent=base, fontName="Helvetica-Bold",
                             fontSize=12.5, leading=15, textColor=ROXO, spaceBefore=0, spaceAfter=6),
        "h3": ParagraphStyle("h3", parent=base, fontName="Helvetica-Bold",
                             fontSize=10.5, leading=13, textColor=TINTA, spaceBefore=2, spaceAfter=3),
        "p": ParagraphStyle("p", parent=base, fontSize=9.5, leading=14, textColor=TINTA, spaceAfter=5,
                            allowWidows=0),
        "small": ParagraphStyle("small", parent=base, fontSize=8, leading=11, textColor=CINZA),
        "kpi_label": ParagraphStyle("kl", parent=base, fontSize=7.5, leading=9, textColor=CINZA),
        "kpi_value": ParagraphStyle("kv", parent=base, fontName="Helvetica-Bold",
                                    fontSize=13, leading=16, textColor=TINTA),
        "sc_title": ParagraphStyle("sct", parent=base, fontName="Helvetica-Bold",
                                   fontSize=10, textColor=TINTA),
        "sc_key": ParagraphStyle("sck", parent=base, fontName="Helvetica-Bold",
                                 fontSize=7, textColor=CINZA),
        "sc_val": ParagraphStyle("scv", parent=base, fontSize=8.5, leading=12, textColor=TINTA),
        "cell": ParagraphStyle("cell", parent=base, fontSize=9, leading=12),
        "cell_b": ParagraphStyle("cellb", parent=base, fontName="Helvetica-Bold", fontSize=9),
    }
    return estilos


def _paragrafos(texto, estilo):
    """Texto livre do consultor em Paragraphs, preservando a estrutura escrita
    (linha em branco = novo parágrafo; quebra simples = nova linha), como a
    página web faz com white-space: pre-line. Cada linha é escapada."""
    normalizado = str(texto or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    paragrafos = []
    for bloco in re.split(r"\n[ \t]*\n", normalizado):
        linhas = [linha.strip() for linha in bloco.split("\n") if linha.strip()]
        if linhas:
            paragrafos.append(Paragraph("<br/>".join(_texto_pdf(l) for l in linhas), estilo))
    return paragrafos


# ---- Blocos de conteúdo ----
def _kpis_flowable(ind, largura, est):
    rotulos = ("FATURAMENTO TOTAL", "TOTAL COMPRADO", "PRESSÃO DE ESTOQUE")
    valores = (ind.faturamento_total, ind.total_comprado, ind.saldo_estimado_compras_vendas)
    col = largura / 3.0
    recuo = 10
    base = est["kpi_value"]
    linha_valores = []
    for valor in valores:
        texto = f"R$ {_brl(valor)}"
        # Valores grandes reduzem o corpo para caber na célula (nunca saem dela).
        corpo = _tamanho_que_cabe(texto, base.fontName, base.fontSize, col - 2 * recuo)
        estilo = base if corpo == base.fontSize else ParagraphStyle(
            f"kv{corpo}", parent=base, fontSize=corpo, leading=corpo * 1.25)
        linha_valores.append(Paragraph(texto, estilo))
    dados = [[Paragraph(r, est["kpi_label"]) for r in rotulos], linha_valores]
    t = Table(dados, colWidths=[col, col, col])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), FUNDO_SUAVE),
        ("BOX", (0, 0), (-1, -1), 0.5, LINHA),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, LINHA),
        ("LEFTPADDING", (0, 0), (-1, -1), recuo), ("RIGHTPADDING", (0, 0), (-1, -1), recuo),
        ("TOPPADDING", (0, 0), (-1, 0), 9), ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
        ("TOPPADDING", (0, 1), (-1, 1), 3), ("BOTTOMPADDING", (0, 1), (-1, 1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def _abc_flowable(abc_top, largura, est):
    head = ["#", "Produto", "Classe", "Faturamento (R$)", "% acum."]
    larguras = [10 * mm, largura - 84 * mm, 18 * mm, 34 * mm, 22 * mm]
    linhas = [head]
    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), ROXO),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("ALIGN", (3, 0), (4, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINHA),
        ("BOX", (0, 0), (-1, -1), 0.5, LINHA),
    ]
    for i, p in enumerate(abc_top[:TOP_N_PDF], start=1):
        linhas.append([
            str(p.posicao_ranking),
            Paragraph(_texto_pdf(p.produto_nome), est["cell"]),
            p.classe_abc,
            _brl(p.faturamento),
            f"{float(p.percentual_acumulado or 0):.1f}%",
        ])
        # Cor da célula de classe + zebra
        cor = CLASSE_COR.get(p.classe_abc, CINZA)
        estilo.append(("TEXTCOLOR", (2, i), (2, i), cor))
        estilo.append(("FONTNAME", (2, i), (2, i), "Helvetica-Bold"))
        if i % 2 == 0:
            estilo.append(("BACKGROUND", (0, i), (-1, i), FUNDO_SUAVE))
    t = Table(linhas, colWidths=larguras, repeatRows=1)
    t.setStyle(TableStyle(estilo))
    return t


def _semaforo_flowable(card, largura, est):
    cor = SEMAFORO_COR.get(card["nivel"], CINZA)
    fundo = SEMAFORO_FUNDO.get(card["nivel"], FUNDO_SUAVE)
    rotulo = SEMAFORO_ROTULO.get(card["nivel"], card["nivel"].upper())
    interno = Table([
        [Paragraph(f'<b>{_texto_pdf(card["titulo"])}</b>  <font size="7" color="#6a7088">· {_texto_pdf(rotulo)}</font>', est["sc_title"])],
        [Paragraph("O QUE FAZER", est["sc_key"])],
        [Paragraph(_texto_pdf(card["o_que_fazer"]), est["sc_val"])],
        [Paragraph("POR QUE FAZER", est["sc_key"])],
        [Paragraph(_texto_pdf(card["por_que"]), est["sc_val"])],
    ], colWidths=[largura - 8 * mm])
    interno.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("TOPPADDING", (0, 1), (0, 1), 5),
    ]))
    wrap = Table([[interno]], colWidths=[largura])
    wrap.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), fundo),
        ("LINEBEFORE", (0, 0), (0, -1), 3, cor),
        ("BOX", (0, 0), (-1, -1), 0.4, LINHA),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return wrap


def _devolutiva(rel, est):
    """Título da seção, subtítulos e textos do consultor, sem títulos isolados:
    'Devolutiva do consultor' + 'Resumo executivo' + o 1º parágrafo andam
    juntos, assim como 'Conclusão estratégica' + o seu 1º parágrafo."""
    titulo = Paragraph("Devolutiva do consultor", est["h2"])
    secoes = []
    for subtitulo, texto in (("Resumo executivo", rel.resumo_executivo),
                             ("Conclusão estratégica", rel.conclusao_estrategica)):
        paragrafos = _paragrafos(texto, est["p"])
        if paragrafos:
            secoes.append((subtitulo, paragrafos))
    if not secoes:
        return [KeepTogether([titulo, Paragraph("Sem texto registrado pelo consultor.", est["small"])])]
    elems = []
    for i, (subtitulo, paragrafos) in enumerate(secoes):
        cabeca = ([titulo] if i == 0 else []) + [Paragraph(subtitulo, est["h3"]), paragrafos[0]]
        if i:
            elems.append(Spacer(1, 2 * mm))
        elems.append(KeepTogether(cabeca))
        elems.extend(paragrafos[1:])
    return elems


def gerar_pdf_analise(analise, semaforos, abc_top) -> bytes:
    """Monta o PDF da análise e devolve os bytes."""
    buf = BytesIO()
    doc = BaseDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGEM_X, rightMargin=MARGEM_X, topMargin=MARGEM_TOPO, bottomMargin=MARGEM_BASE,
        title=f"Analise NEXO #{analise.id_analise}", author="NEXO",
    )
    # Quadro sem recuo interno: a largura útil é exatamente a área entre as margens.
    quadro = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="conteudo",
                   leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="nexo", frames=[quadro])])
    largura = doc.width
    est = _estilos()
    emp = analise.empresa
    rel = analise.relatorio
    ind = analise.indicador
    produtos = list(abc_top or [])[:TOP_N_PDF]

    elems = []
    ref = f"{analise.mes_referencia:02d}/{analise.ano_referencia}"
    elems.append(_BarraTopo(largura, "Análise Executiva", f"Referência {ref}"))
    elems.append(Spacer(1, 7 * mm))

    titulo = rel.titulo if rel else "Análise publicada"
    elems.append(Paragraph(_texto_pdf(titulo), est["titulo"]))
    periodo = f"{analise.periodo_inicio.strftime('%d/%m/%Y')} – {analise.periodo_fim.strftime('%d/%m/%Y')}"
    nome_empresa = emp.nome_fantasia or emp.razao_social
    elems.append(Paragraph(
        f"{_texto_pdf(nome_empresa)} &nbsp;·&nbsp; CNPJ {_texto_pdf(emp.cnpj)} &nbsp;·&nbsp; Período {_texto_pdf(periodo)}",
        est["small"]))
    elems.append(Spacer(1, 7 * mm))

    # Indicadores
    if ind:
        elems.append(KeepTogether([Paragraph("Indicadores do período", est["h2"]),
                                   _kpis_flowable(ind, largura, est)]))
        elems.append(Spacer(1, 7 * mm))

    # Curva ABC: título, tabela e explicação juntos.
    if produtos:
        elems.append(KeepTogether([
            Paragraph(f"Curva ABC · Top {len(produtos)} produtos (Princípio de Pareto)", est["h2"]),
            _abc_flowable(produtos, largura, est),
            Spacer(1, 2 * mm),
            Paragraph("Classe A: até 80% do faturamento acumulado (estratégicos) · "
                      "B: 80–95% (táticos) · C: ~5% restantes (operacionais).", est["small"]),
        ]))
        elems.append(Spacer(1, 7 * mm))

    # Síntese executiva (semáforos): o título viaja com o primeiro cartão.
    if semaforos:
        cartoes = [_semaforo_flowable(card, largura, est) for card in semaforos]
        elems.append(KeepTogether([Paragraph("Síntese executiva (5W2H)", est["h2"]), cartoes[0]]))
        for cartao in cartoes[1:]:
            elems.append(Spacer(1, 3 * mm))
            elems.append(cartao)
        elems.append(Spacer(1, 7 * mm))

    # Devolutiva
    if rel:
        elems.extend(_devolutiva(rel, est))

    elems.append(Spacer(1, 6 * mm))
    elems.append(Paragraph(
        f"Documento gerado pelo portal NEXO em {datetime.now().strftime('%d/%m/%Y %H:%M')}.", est["small"]))

    identificacao = f"NEXO · {nome_empresa or ''} · Referência {ref}"
    doc.build(elems, canvasmaker=_canvas_com_rodape(identificacao))
    return buf.getvalue()
