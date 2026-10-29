"""
NEXO - Faturamento Inteligente | Exportação da Análise Executiva em PDF
======================================================================
Gera, com ReportLab (platypus), o PDF da análise publicada: cabeçalho da marca,
indicadores, Curva ABC (Top 5) com o gráfico de pizza da distribuição do
faturamento, síntese executiva em semáforos (5W2H) e a devolutiva do consultor.

Layout claro (fundo branco) — apropriado para impressão/anexo — com os acentos
de cor da identidade NEXO (roxo) e o mesmo código de cores da app para as
classes ABC e os semáforos. Mantém a regra: sem lucro/margem/CMV.

Paginação: o conteúdo ocupa exatamente a área entre as margens (quadro sem
recuo interno); nenhum título fica sozinho no fim de uma página — cada título
viaja com o primeiro bloco do seu conteúdo —, blocos curtos (indicadores,
tabela, gráfico com legenda, cada cartão) não se partem e os textos longos da
devolutiva quebram entre páginas normalmente. O rodapé de todas as páginas traz
"Página X de Y".

Função pública:
    gerar_pdf_analise(analise, semaforos, abc_top) -> bytes
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO
import logging
import re
from xml.sax.saxutils import escape

from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Circle, Drawing, Rect
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

log = logging.getLogger(__name__)

# ---- Paleta NEXO ----
ROXO = HexColor("#7c3aed")
ROXO2 = HexColor("#a855f7")
LAVANDA = HexColor("#ede9fb")
TINTA = HexColor("#1f2330")
CINZA = HexColor("#6a7088")
LINHA = HexColor("#e6e8ef")
CONTORNO = HexColor("#c3c6d4")
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

# Gráfico de pizza: rampa ordinal no matiz do roxo NEXO (mais escuro = maior
# participação; as fatias vêm em ordem de faturamento). Validada com o
# verificador de paletas: L monotônico, ΔL >= 0,06 entre vizinhos (cores
# distinguíveis também por daltônicos e na impressão em tons de cinza), um só
# matiz e contraste >= 2:1 no extremo claro. "Outros produtos" usa um cinza
# neutro claro (ΔE >= 16 contra todos os passos), com o contorno do círculo.
RAMPA_PIZZA = tuple(HexColor(c) for c in ("#5a06bb", "#7040ce", "#8765e0", "#9d83ee", "#b4a1fc"))
COR_OUTROS = HexColor("#d5d8e2")
TOP_N_PDF = 5                      # a tabela e o gráfico mostram os mesmos produtos
LIMITE_ROTULO_NA_FATIA = Decimal("12")   # % mínima para escrever o percentual dentro da fatia
TOLERANCIA_CENTAVOS = Decimal("0.005")   # diferenças abaixo de meio centavo são arredondamento

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


def _pct(valor, casas: int = 2) -> str:
    """74.22871 -> '74,23%' (vírgula decimal, arredondamento meio para cima)."""
    numero = _decimal(valor) or Decimal(0)
    quantum = Decimal(1).scaleb(-casas)
    return f"{numero.quantize(quantum, ROUND_HALF_UP):.{casas}f}".replace(".", ",") + "%"


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


def _luminancia(cor) -> float:
    def canal(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * canal(cor.red) + 0.7152 * canal(cor.green) + 0.0722 * canal(cor.blue)


def _tinta_sobre(fundo):
    """Branco ou tinta escura, o que tiver mais contraste sobre o fundo."""
    lum = _luminancia(fundo)
    contraste_branco = 1.05 / (lum + 0.05)
    contraste_tinta = (lum + 0.05) / (_luminancia(TINTA) + 0.05)
    return white if contraste_branco >= contraste_tinta else TINTA


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
        "sub": ParagraphStyle("sub", parent=base, fontSize=8.5, leading=11.5, textColor=CINZA, spaceAfter=0),
        "p": ParagraphStyle("p", parent=base, fontSize=9.5, leading=14, textColor=TINTA, spaceAfter=5,
                            allowWidows=0),
        "small": ParagraphStyle("small", parent=base, fontSize=8, leading=11, textColor=CINZA),
        "aviso": ParagraphStyle("aviso", parent=base, fontSize=8, leading=11, textColor=TINTA),
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
        "leg": ParagraphStyle("leg", parent=base, fontSize=8.5, leading=10.5, textColor=TINTA),
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


@dataclass(frozen=True)
class Fatia:
    nome: str
    classe: str | None
    faturamento: Decimal
    percentual: Decimal          # sobre a base, sem arredondar
    cor: object
    outros: bool = False


@dataclass(frozen=True)
class Distribuicao:
    fatias: tuple
    base: Decimal                # denominador das participações
    base_e_faturamento_total: bool
    avisos: tuple


def calcular_distribuicao(faturamento_total, produtos) -> Distribuicao | None:
    """Participação individual de cada produto exibido na tabela Curva ABC.

    participação = faturamento do produto ÷ faturamento total do período × 100;
    "Outros produtos" = faturamento total − soma dos produtos exibidos (quando
    positivo). Os dados não são ajustados para a soma dos percentuais
    arredondados dar 100%. Inconsistências viram aviso explícito no PDF:
      - soma dos produtos maior que o faturamento total: a base passa a ser a
        soma dos produtos e não há fatia "Outros";
      - faturamento total ausente ou não positivo: idem;
      - produto com faturamento zero ou negativo: fica fora do gráfico.
    Devolve None quando não há faturamento positivo para distribuir.
    """
    avisos = []
    exibidos = []
    ignorados = 0
    for p in produtos[:TOP_N_PDF]:
        valor = _decimal(p.faturamento)
        if valor is None or valor <= 0:
            ignorados += 1
            continue
        exibidos.append((p, valor))
    soma = sum((valor for _, valor in exibidos), Decimal(0))
    if soma <= 0:
        return None
    total = _decimal(faturamento_total)
    if total is None or total <= 0:
        base, usa_total = soma, False
        avisos.append("Faturamento total do período indisponível: as participações foram "
                      "calculadas sobre a soma dos produtos exibidos.")
    elif soma - total > TOLERANCIA_CENTAVOS:
        base, usa_total = soma, False
        avisos.append(f"A soma dos produtos exibidos (R$ {_brl(soma)}) é maior que o faturamento total "
                      f"informado (R$ {_brl(total)}); as participações foram calculadas sobre a soma "
                      "dos produtos, sem a fatia Outros produtos.")
        log.warning("PDF: soma da Curva ABC exibida (%s) maior que o faturamento total (%s).", soma, total)
    else:
        base, usa_total = total, True
    if ignorados:
        avisos.append(f"{ignorados} produto(s) da tabela com faturamento zero ou negativo não entram no gráfico.")
    fatias = [
        Fatia(nome=str(p.produto_nome or ""), classe=p.classe_abc, faturamento=valor,
              percentual=valor / base * 100, cor=RAMPA_PIZZA[min(i, len(RAMPA_PIZZA) - 1)])
        for i, (p, valor) in enumerate(exibidos)
    ]
    if usa_total:
        restante = total - soma
        if restante > TOLERANCIA_CENTAVOS:
            fatias.append(Fatia(nome="Outros produtos", classe=None, faturamento=restante,
                                percentual=restante / base * 100, cor=COR_OUTROS, outros=True))
    return Distribuicao(fatias=tuple(fatias), base=base, base_e_faturamento_total=usa_total,
                        avisos=tuple(avisos))


def _grafico_pizza(distribuicao, diametro):
    """Pizza vetorial 2D (ReportLab Graphics): fatias proporcionais, separadas
    por um filete branco, começando às 12 h no sentido horário. Só as fatias
    grandes recebem o percentual dentro; as demais ficam na legenda."""
    folga = 2 * mm
    lado = diametro + 2 * folga
    desenho = Drawing(lado, lado)
    pizza = Pie()
    pizza.x = pizza.y = folga
    pizza.width = pizza.height = diametro
    pizza.data = [float(f.faturamento) for f in distribuicao.fatias]
    pizza.startAngle = 90
    pizza.direction = "clockwise"
    pizza.sideLabels = 0
    pizza.simpleLabels = 1
    pizza.labels = [_pct(f.percentual) if f.percentual >= LIMITE_ROTULO_NA_FATIA else ""
                    for f in distribuicao.fatias]
    pizza.slices.strokeColor = white
    pizza.slices.strokeWidth = 1.2
    pizza.slices.labelRadius = 0.62
    pizza.slices.fontName = "Helvetica-Bold"
    pizza.slices.fontSize = 8.5
    for i, fatia in enumerate(distribuicao.fatias):
        pizza.slices[i].fillColor = fatia.cor
        pizza.slices[i].fontColor = _tinta_sobre(fatia.cor)
    desenho.add(pizza)
    # Contorno fino do círculo: mantém visível a borda de fatias claras sobre o papel branco.
    desenho.add(Circle(folga + diametro / 2, folga + diametro / 2, diametro / 2,
                       fillColor=None, strokeColor=CONTORNO, strokeWidth=0.6))
    return desenho


def _amostra(cor):
    lado = 3.6 * mm
    desenho = Drawing(lado, lado)
    desenho.add(Rect(0, 0, lado, lado, rx=1.2, ry=1.2, fillColor=cor,
                     strokeColor=CONTORNO if cor == COR_OUTROS else None, strokeWidth=0.5))
    return desenho


def _legenda_flowable(distribuicao, largura, est):
    larguras = [7 * mm, largura - 70 * mm, 14 * mm, 28 * mm, 21 * mm]
    cab = ParagraphStyle("legh", parent=est["leg"], fontName="Helvetica-Bold", fontSize=8, leading=10)
    linhas = [["", Paragraph("Produto", cab), "Classe", "Faturamento (R$)", "Participação"]]
    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), FUNDO_SUAVE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("TEXTCOLOR", (0, 0), (-1, -1), TINTA),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("ALIGN", (3, 0), (4, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINHA),
        ("FONTNAME", (4, 1), (4, -1), "Helvetica-Bold"),
    ]
    for i, fatia in enumerate(distribuicao.fatias, start=1):
        nome = Paragraph(_texto_pdf(fatia.nome), est["leg"])
        if fatia.outros:
            classe = "—"
        else:
            classe = fatia.classe
            estilo.append(("TEXTCOLOR", (2, i), (2, i), CLASSE_COR.get(fatia.classe, CINZA)))
            estilo.append(("FONTNAME", (2, i), (2, i), "Helvetica-Bold"))
        linhas.append([_amostra(fatia.cor), nome, classe, _brl(fatia.faturamento), _pct(fatia.percentual)])
    rotulo_total = "Faturamento total" if distribuicao.base_e_faturamento_total else "Soma dos produtos exibidos"
    linhas.append(["", Paragraph(f"<b>{rotulo_total}</b>", est["leg"]), "", _brl(distribuicao.base), "100,00%"])
    estilo += [
        ("FONTNAME", (3, -1), (4, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, -1), (-1, -1), 0.6, CONTORNO),
    ]
    t = Table(linhas, colWidths=larguras)
    t.setStyle(TableStyle(estilo))
    return t


def _secao_distribuicao(distribuicao, largura, est):
    """Título, subtítulo, gráfico (à esquerda) + legenda (à direita) e nota, num
    bloco que não se parte: se não couber depois da tabela, vai inteiro para a
    página seguinte."""
    largura_grafico = 62 * mm
    grafico = _grafico_pizza(distribuicao, diametro=54 * mm)
    legenda = _legenda_flowable(distribuicao, largura - largura_grafico, est)
    corpo = Table([[grafico, legenda]], colWidths=[largura_grafico, largura - largura_grafico])
    corpo.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    nota = ("Participação individual = faturamento do produto ÷ faturamento total do período × 100."
            if distribuicao.base_e_faturamento_total else
            "Participação individual = faturamento do produto ÷ soma dos produtos exibidos × 100.")
    if any(f.outros for f in distribuicao.fatias):
        nota += f" “Outros produtos” reúne o faturamento dos itens fora do Top {TOP_N_PDF}."
    soma_arredondada = sum((Decimal(_pct(f.percentual)[:-1].replace(",", ".")) for f in distribuicao.fatias),
                           Decimal(0))
    if soma_arredondada != Decimal("100.00"):
        nota += (" Percentuais arredondados para duas casas decimais: a soma exibida pode diferir "
                 "de 100% por arredondamento.")
    bloco = [
        Paragraph("Distribuição do faturamento por produto", est["h2"]),
        Paragraph("Participação dos principais produtos no faturamento do período.", est["sub"]),
        Spacer(1, 3 * mm),
        corpo,
        Spacer(1, 2.5 * mm),
        Paragraph(_texto_pdf(nota), est["small"]),
    ]
    for aviso in distribuicao.avisos:
        bloco += [Spacer(1, 1.5 * mm), Paragraph(f"<b>Atenção:</b> {_texto_pdf(aviso)}", est["aviso"])]
    return KeepTogether(bloco)


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

    # Curva ABC: título, tabela e explicação juntos; depois, o gráfico de pizza.
    if produtos:
        elems.append(KeepTogether([
            Paragraph(f"Curva ABC · Top {len(produtos)} produtos (Princípio de Pareto)", est["h2"]),
            _abc_flowable(produtos, largura, est),
            Spacer(1, 2 * mm),
            Paragraph("Classe A: até 80% do faturamento acumulado (estratégicos) · "
                      "B: 80–95% (táticos) · C: ~5% restantes (operacionais).", est["small"]),
        ]))
        elems.append(Spacer(1, 7 * mm))
        distribuicao = calcular_distribuicao(ind.faturamento_total if ind else None, produtos)
        if distribuicao is not None:
            elems.append(_secao_distribuicao(distribuicao, largura, est))
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
