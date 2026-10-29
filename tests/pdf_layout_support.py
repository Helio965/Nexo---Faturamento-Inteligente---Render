"""Apoio aos testes de layout e horário do PDF (sem banco, sem rede, dados sintéticos).

Os números da análise de referência reproduzem os valores informados pelo
proprietário para o documento "analise_nexo_202606_5" (faturamento total
R$ 4.311,00; Top 5 = R$ 4.256,00; outros R$ 55,00). Empresa, CNPJ, compras e
textos são fictícios. A geometria é lida com o pdftotext (poppler) por
stdin/stdout; sem ele, os testes que dependem de geometria são ignorados.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import html
import logging
import re
import shutil
import subprocess
from types import SimpleNamespace

from reportlab.lib.units import mm

import pdf_export

INSTANTE_UTC = datetime(2026, 10, 29, 15, 2, tzinfo=timezone.utc)   # 12:02 em Brasília
ITENS = (
    ("Fax Térmico Panasonic", "3200.00"), ("Leitor Zip Drive Iomega", "760.00"),
    ("Mouse Bola Serial", "220.00"), ("Pilha AA", "40.00"), ("Diskette Maxell", "36.00"),
    ("Cabo Paralelo 1,8 m", "30.00"), ("Fita VHS T-120", "25.00"),
)
TITULOS = ("Indicadores do período", "Curva ABC", "Distribuição do faturamento por produto",
           "Síntese executiva", "Devolutiva do consultor", "Resumo executivo", "Conclusão estratégica")
SUBTITULO_GRAFICO = "Participação dos principais produtos no faturamento do período."
FECHAMENTO = "Documento gerado pelo portal NEXO em"
MARGEM = 18 * mm
TOPO = 15 * mm
INICIO_RODAPE = 17 * mm          # régua do rodapé, medida a partir da base da página


def curva_referencia(itens=ITENS):
    total = sum(Decimal(v) for _, v in itens)
    acumulado = Decimal(0)
    produtos = []
    for posicao, (nome, valor) in enumerate(itens, start=1):
        valor = Decimal(valor)
        acumulado += valor
        percentual = acumulado / total * 100
        classe = "A" if posicao == 1 or percentual <= 80 else ("B" if percentual <= 95 else "C")
        produtos.append(SimpleNamespace(
            posicao_ranking=posicao, produto_nome=nome, faturamento=valor,
            percentual_individual=(valor / total * 100).quantize(Decimal("0.0001")),
            percentual_acumulado=percentual.quantize(Decimal("0.0001")), classe_abc=classe,
        ))
    return produtos


def analise_referencia(resumo=None, conclusao=None):
    empresa = SimpleNamespace(nome_fantasia="Empresa Demonstração", razao_social="Empresa Demonstração Ltda",
                              cnpj="00.000.000/0001-00")
    relatorio = SimpleNamespace(
        titulo="Análise de faturamento — junho de 2026",
        resumo_executivo=resumo if resumo is not None else (
            "O faturamento de junho somou R$ 4.311,00, concentrado no Fax Térmico Panasonic.\n\n"
            "As compras superaram as vendas em cerca de 19%."),
        conclusao_estrategica=conclusao if conclusao is not None else (
            "Reduzir o ritmo de compras e priorizar o giro do estoque já adquirido.\n\n"
            "Proteger o abastecimento do Fax Térmico Panasonic.\nRevisar o mix em 30 dias."),
    )
    indicador = SimpleNamespace(
        faturamento_total=Decimal("4311.00"), total_comprado=Decimal("5120.00"),
        saldo_estimado_compras_vendas=Decimal("809.00"),
        produto_maior_saldo_parado_nome="Leitor Zip Drive Iomega", saldo_estimado_parado=Decimal("12"),
    )
    return SimpleNamespace(
        id_analise=5, mes_referencia=6, ano_referencia=2026,
        periodo_inicio=date(2026, 6, 1), periodo_fim=date(2026, 6, 30),
        empresa=empresa, relatorio=relatorio, indicador=indicador, curva_abc=curva_referencia(),
    )


def semaforos_referencia():
    return [
        {"nivel": "critico", "titulo": "Capital imobilizado em estoque",
         "o_que_fazer": "Reduzir o ritmo de compras e priorizar o giro do estoque já adquirido no próximo ciclo.",
         "por_que": "Você comprou cerca de 19% a mais do que vendeu (em R$)."},
        {"nivel": "atencao", "titulo": "Estoque parado concentrado",
         "o_que_fazer": "Criar ação de escoamento para “Leitor Zip Drive Iomega”.",
         "por_que": "Estimativa de 12 unidades compradas e ainda não vendidas."},
        {"nivel": "oportunidade", "titulo": "Produtos estratégicos (Classe A)",
         "o_que_fazer": "Blindar o abastecimento e a precificação dos 1 produto(s) Classe A.",
         "por_que": "Eles concentram ~74% do faturamento (Princípio de Pareto)."},
    ]


def gerar(analise=None, semaforos=None, produtos=None, gerado_em=INSTANTE_UTC):
    analise = analise or analise_referencia()
    semaforos = semaforos_referencia() if semaforos is None else semaforos
    produtos = analise.curva_abc if produtos is None else produtos
    return pdf_export.gerar_pdf_analise(analise, semaforos, produtos, gerado_em=gerado_em)


def reativar_logger_do_gerador(caso):
    """As migrations de teste chamam fileConfig() do Alembic, que desativa os loggers
    já criados; reativa o do gerador durante o teste e restaura o estado ao fim."""
    logger = logging.getLogger(pdf_export.__name__)
    caso.addCleanup(setattr, logger, "disabled", logger.disabled)
    logger.disabled = False


def pdftotext_disponivel():
    return shutil.which("pdftotext") is not None


def texto(documento):
    saida = subprocess.run([shutil.which("pdftotext"), "-enc", "UTF-8", "-", "-"], input=documento,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=30)
    return " ".join(saida.stdout.decode("utf-8").split())


_ATRIBUTOS = re.compile(r'(xMin|yMin|xMax|yMax|width|height)="(-?[\d.]+)"')   # texto fora da página tem y < 0


def _attrs(trecho):
    return {k: float(v) for k, v in _ATRIBUTOS.findall(trecho)}


def paginas(documento):
    """Lista de páginas: {'largura', 'altura', 'linhas': [{'texto', 'x0', 'y0', 'x1', 'y1', 'palavras'}]}.
    Coordenadas do pdftotext: origem no canto superior esquerdo, y crescendo para baixo."""
    saida = subprocess.run([shutil.which("pdftotext"), "-bbox-layout", "-enc", "UTF-8", "-", "-"],
                           input=documento, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           check=True, timeout=30).stdout.decode("utf-8")
    resultado = []
    for cabeca, corpo in re.findall(r"<page ([^>]*)>(.*?)</page>", saida, flags=re.S):
        dims = _attrs(cabeca)
        linhas = []
        for cab_linha, corpo_linha in re.findall(r"<line ([^>]*)>(.*?)</line>", corpo, flags=re.S):
            palavras = [dict(_attrs(a), texto=html.unescape(t))
                        for a, t in re.findall(r"<word ([^>]*)>(.*?)</word>", corpo_linha, flags=re.S)]
            caixa = _attrs(cab_linha)
            linhas.append({"texto": " ".join(p["texto"] for p in palavras), "x0": caixa["xMin"],
                           "y0": caixa["yMin"], "x1": caixa["xMax"], "y1": caixa["yMax"], "palavras": palavras})
        resultado.append({"largura": dims["width"], "altura": dims["height"], "linhas": linhas})
    return resultado


def linhas_do_corpo(pagina):
    limite = pagina["altura"] - INICIO_RODAPE
    return [l for l in pagina["linhas"] if l["y1"] <= limite]


def linhas_do_rodape(pagina):
    limite = pagina["altura"] - INICIO_RODAPE
    return [l for l in pagina["linhas"] if l["y0"] >= limite]


def problemas_de_geometria(pagina):
    """Palavras fora da página/margens e linhas de texto sobrepostas (lista vazia = ok)."""
    problemas = []
    largura, altura = pagina["largura"], pagina["altura"]
    for linha in pagina["linhas"]:
        for p in linha["palavras"]:
            if p["xMin"] < MARGEM - 1 or p["xMax"] > largura - MARGEM + 1:
                problemas.append(("fora_das_margens_laterais", p["texto"], round(p["xMin"], 1), round(p["xMax"], 1)))
            if p["yMin"] < TOPO - 1 or p["yMax"] > altura - 5 * mm:
                problemas.append(("fora_da_area_vertical", p["texto"], round(p["yMin"], 1), round(p["yMax"], 1)))
    todas = [p for l in pagina["linhas"] for p in l["palavras"]]
    for i in range(len(todas)):
        a = todas[i]
        for b in todas[i + 1:]:
            dx = min(a["xMax"], b["xMax"]) - max(a["xMin"], b["xMin"])
            dy = min(a["yMax"], b["yMax"]) - max(a["yMin"], b["yMin"])
            if dx > 0.8 and dy > 1.5:
                problemas.append(("sobreposicao", a["texto"], b["texto"]))
    return problemas


def titulo_isolado(pagina):
    """Título que termina o corpo da página (o conteúdo dele ficou na seguinte)."""
    corpo = linhas_do_corpo(pagina)
    if not corpo:
        return None
    ultima = max(corpo, key=lambda l: l["y1"])
    return ultima["texto"] if any(ultima["texto"].startswith(t) for t in TITULOS) else None


def pagina_sem_conteudo(pagina):
    """Página cujo corpo só tem títulos, o subtítulo do gráfico e/ou a frase final
    (o conteúdo foi para outra página): devolve esses textos; None se a página é normal."""
    corpo = [l["texto"] for l in linhas_do_corpo(pagina)]
    def vazia(texto):
        return (any(texto.startswith(t) for t in TITULOS) or texto == SUBTITULO_GRAFICO
                or texto.startswith(FECHAMENTO))
    return corpo if corpo and all(vazia(t) for t in corpo) else None
