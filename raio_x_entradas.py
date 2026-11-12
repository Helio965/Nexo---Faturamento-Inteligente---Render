"""Leitura de vendas exclusiva do Raio-X, isolada dos indicadores mensais.

Adaptada dos helpers do etl_processor da referência 91e5fb06. Contém somente
leitura limitada, normalização monetária, status de linhas e detecção de período.
Não calcula nem persiste KPIs, Curva ABC ou validação PDV e não é importada pelo
ETL financeiro legado. As estimativas do Raio-X usam este contrato específico;
os indicadores históricos continuam usando etl_processor.py do Render.
"""

import logging
import math
import numbers
import re
import unicodedata
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd

from etl_inputs import ETLInputError, read_raw, validate_input
from etl_limits import get_limits

logger = logging.getLogger(__name__)

class ETLValidationError(ETLInputError):
    """Mantém o tipo público anterior e a identificação segura de limites."""

    def __init__(self, mensagem, code="data"):
        super().__init__(code, mensagem)

def _strip_acentos(texto) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", str(texto))
        if not unicodedata.combining(c)
    )

def _norm_chave(valor) -> str:
    """
    Normalização AGRESSIVA para casar fragmentos do dicionário de aliases:
      - remove BOM/NBSP/quebras de linha;
      - tira acentos; vira minúsculas;
      - substitui pontuação por espaço; colapsa múltiplos espaços.
    Resultado é seguro para `fragmento in chave_normalizada`.
    """
    if valor is None:
        return ""
    s = str(valor).replace("﻿", "").replace("\xa0", " ")
    s = s.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    s = _strip_acentos(s).lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _normalizar_produto(valor) -> str:
    """Chave de agrupamento por produto (uppercase, sem acentos, sem pontuação)."""
    s = _strip_acentos(str(valor or "")).upper()
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

LIMITE_NOME_PRODUTO = 200

def _nome_exibivel(valor) -> str:
    """Nome de produto com teto de tamanho (proteção de armazenamento/layout) e
    sem NUL. Preserva o restante do conteúdo: os números financeiros e os nomes
    permanecem equivalentes ao motor original; a sanitização para uma linha é
    responsabilidade da camada de exibição (templates/PDF). Não é a chave de
    agrupamento (essa é _normalizar_produto)."""
    return str(valor or "").replace("\x00", "")[:LIMITE_NOME_PRODUTO]

_NAO_PRODUTOS = {
    "DESCONTO", "DESCONTOS", "ACRESCIMO", "ACRESCIMOS", "FRETE", "TROCO",
    "TAXA", "TAXAS", "JUROS", "TOTAL", "SUBTOTAL", "TOTAL GERAL",
    "ARREDONDAMENTO", "ENTRADA", "SANGRIA", "SUPRIMENTO",
}

def _parse_valor(bruto):
    """
    Aceita 'R$ 1.234,56', '1.234,56', '1234,56', '1,234.56', '1234.56',
    '(123,45)', ' - ', '', None — retorna float ou None se irrecuperável.

    Só para quantidades e estoque: aqui o ponto único é decimal, porque "1.500" numa
    coluna de quantidade costuma ser 1,5 kg. Dinheiro usa converter_valor_monetario.
    """
    if bruto is None:
        return None
    s = str(bruto).strip()
    # O apóstrofo da neutralização de fórmula (security_gatekeeper) não é sinal nem dígito:
    # sem tirá-lo, "'-2 un(s)" seria lido como +2 e a devolução viraria venda. O dinheiro já
    # o ignora (_limpar_monetario).
    if s.startswith("'"):
        s = s[1:].strip()
    if s.lower() in ("", "nan", "none", "-", "--"):
        return None

    s = s.replace("\xa0", "").replace(" ", "")
    s = re.sub(r"(?i)r\$", "", s)
    negativo = s.startswith("-") or s.startswith("(")
    s2 = re.sub(r"[^0-9.,]", "", s)
    if s2 == "":
        return None

    tem_virg = "," in s2
    tem_pto = "." in s2
    if tem_virg and tem_pto:
        # o separador mais à direita é o decimal
        if s2.rfind(",") > s2.rfind("."):
            s2 = s2.replace(".", "").replace(",", ".")
        else:
            s2 = s2.replace(",", "")
    elif tem_virg:
        # padrão BR: vírgula é decimal
        s2 = s2.replace(".", "").replace(",", ".")
    elif tem_pto and s2.count(".") > 1:
        # múltiplos pontos => separadores de milhar
        s2 = s2.replace(".", "")
    # único ponto = decimal => mantém

    try:
        val = float(s2)
    except ValueError:
        return None
    return -val if (negativo and val > 0) else val

def _converter_serie(serie: pd.Series) -> pd.Series:
    return pd.Series([_parse_valor(v) for v in serie], index=serie.index, dtype="float64")

_RE_MILHAR_PONTO = re.compile(r"[1-9][0-9]{0,2}(?:\.[0-9]{3})+")

_RE_MILHAR_VIRGULA = re.compile(r"[1-9][0-9]{0,2}(?:,[0-9]{3})+")

_RE_DECIMAL = re.compile(r"[0-9]+[.,]?[0-9]*|[.,][0-9]+")

_RE_CASAS_DECIMAIS = re.compile(r"[0-9]+")

_RE_CIENTIFICO = re.compile(r"[0-9]+(?:[.,][0-9]+)?[eE][+-]?[0-9]+")

_RE_PONTO_DECIMAL = re.compile(r"[0-9,]*\.[0-9]+")

_RE_VIRGULA_DECIMAL = re.compile(r"[0-9.]*,[0-9]+")

_RE_MOEDA = re.compile(r"r\$|us\$|brl|usd|\$", re.IGNORECASE)

_SINAIS_DE_MENOS = str.maketrans({"−": "-", "–": "-", "﹣": "-", "－": "-"})

_VALORES_EM_BRANCO = {"", "-", "--", "nan", "none", "null", "na", "n/a", "nd", "n/d"}

def _limpar_monetario(valor) -> str:
    """Tira espaços, caracteres invisíveis, aspas de texto do Excel e símbolo de moeda."""
    texto = str(valor).translate(_SINAIS_DE_MENOS)
    texto = "".join(c for c in texto if unicodedata.category(c)[0] not in "CZ")
    return _RE_MOEDA.sub("", texto.strip("'\""))

def _separar_sinal(corpo: str) -> tuple:
    """(negativo, corpo sem sinal): aceita "(10)", "-10" e "10-", formatos de PDV."""
    negativo = False
    if corpo.startswith("(") and corpo.endswith(")"):
        negativo, corpo = True, corpo[1:-1]
    if corpo.startswith("-"):
        negativo, corpo = True, corpo[1:]
    elif corpo.endswith("-"):
        negativo, corpo = True, corpo[:-1]
    return negativo, corpo.removeprefix("+")

def _normalizar_separadores(corpo: str, ponto_decimal: bool):
    """Texto aceito por float(), ou None se os separadores não formam um número."""
    if _RE_CIENTIFICO.fullmatch(corpo):
        return corpo.replace(",", ".")
    virgula, ponto = corpo.rfind(","), corpo.rfind(".")
    if virgula >= 0 and ponto >= 0:
        # O separador mais à direita é o decimal; o outro só pode agrupar milhares.
        decimal_br = virgula > ponto
        inteiro, _, casas = corpo.rpartition("," if decimal_br else ".")
        agrupado = _RE_MILHAR_PONTO if decimal_br else _RE_MILHAR_VIRGULA
        if not (agrupado.fullmatch(inteiro) and _RE_CASAS_DECIMAIS.fullmatch(casas)):
            return None
        return inteiro.replace("." if decimal_br else ",", "") + "." + casas
    if corpo.count(",") > 1:
        return corpo.replace(",", "") if _RE_MILHAR_VIRGULA.fullmatch(corpo) else None
    if corpo.count(".") > 1:
        return corpo.replace(".", "") if _RE_MILHAR_PONTO.fullmatch(corpo) else None
    if _RE_MILHAR_PONTO.fullmatch(corpo) and not ponto_decimal:
        return corpo.replace(".", "")
    return corpo.replace(",", ".") if _RE_DECIMAL.fullmatch(corpo) else None

def _interpretar_monetario(valor, ponto_decimal: bool = False):
    """Float finito, ou None quando o valor é nulo ou inválido."""
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, (numbers.Real, Decimal)):
        numero = float(valor)
        return numero if math.isfinite(numero) else None
    negativo, corpo = _separar_sinal(_limpar_monetario(valor))
    texto = _normalizar_separadores(corpo, ponto_decimal)
    if texto is None:
        return None
    numero = float(texto)
    if not math.isfinite(numero):
        return None
    return -numero if (negativo and numero) else numero

def _coluna_usa_ponto_decimal(corpos: list) -> bool:
    """A coluna tem valor com ponto que não pode ser milhar ("12.50", "1,234.56") e
    nenhum com vírgula decimal ("1.234,50"): nela, "12.500" é 12,5, e não 12.500,00."""
    com_ponto = com_virgula = False
    for corpo in corpos:
        if _RE_VIRGULA_DECIMAL.fullmatch(corpo):
            com_virgula = True
        elif _RE_PONTO_DECIMAL.fullmatch(corpo) and not _RE_MILHAR_PONTO.fullmatch(corpo):
            com_ponto = True
    return com_ponto and not com_virgula

def _converter_serie_monetaria(serie: pd.Series, qualidade: Counter) -> pd.Series:
    """Converte uma coluna em dinheiro e anota em `qualidade` o que pede revisão humana."""
    corpos = [_separar_sinal(_limpar_monetario(v))[1] for v in serie]
    ponto_decimal = _coluna_usa_ponto_decimal(corpos)
    valores = []
    for bruto, corpo in zip(serie, corpos):
        numero = _interpretar_monetario(bruto, ponto_decimal)
        if numero is None:
            if corpo.lower() not in _VALORES_EM_BRANCO:
                qualidade["invalidos"] += 1
            numero = 0.0
        elif corpo.count(".") == 1 and _RE_MILHAR_PONTO.fullmatch(corpo):
            qualidade["lidos_como_decimal" if ponto_decimal else "lidos_como_milhar"] += 1
        valores.append(numero)
    return pd.Series(valores, index=serie.index, dtype="float64")

def _ler_bruto(caminho_arquivo: str) -> pd.DataFrame:
    """Leitura limitada exclusiva do diagnóstico, preservando números reais do XLSX.

    O leitor legado usa dtype=str: o número 12.125 e o texto "12.125" ficam
    iguais. No Raio-X somente, recuperamos o tipo original das células ambíguas
    para não transformar R$ 12,125 em R$ 12.125,00. O texto continua seguindo as
    regras monetárias pt-BR. Nenhum leitor ou indicador legado é modificado.
    """
    try:
        limites = get_limits()
        bruto = read_raw(caminho_arquivo, limites)
        if Path(caminho_arquivo).suffix.lower() == ".xlsx":
            candidatos = [(linha, coluna) for coluna in range(bruto.shape[1])
                          for linha, valor in enumerate(bruto.iloc[:, coluna].tolist())
                          if isinstance(valor, str) and _RE_MILHAR_PONTO.fullmatch(valor)]
            if candidatos:
                bruto = bruto.astype(object)
                # A seleção da aba e os orçamentos vêm do validador limitado.
                metadados = validate_input(caminho_arquivo, "xlsx", limites)
                tipado = pd.read_excel(caminho_arquivo, dtype=object, header=None,
                                       engine="openpyxl", sheet_name=metadados["selected_sheet"])
                tipado = tipado.dropna(axis=0, how="all").dropna(axis=1, how="all").reset_index(drop=True)
                if tipado.shape != bruto.shape:
                    raise ETLInputError("invalid", "Não foi possível conferir os números do arquivo.")
                for linha, coluna in candidatos:
                    valor = tipado.iat[linha, coluna]
                    if isinstance(valor, numbers.Real) and not isinstance(valor, bool):
                        bruto.iat[linha, coluna] = valor
        return bruto
    except ETLInputError as erro:
        raise ETLValidationError(erro.safe_message, erro.code) from None

ALIAS_VENDAS = {
    # codigo PRECISA vir antes de produto: assim a coluna "id_produto" (ex.: P001)
    # é reivindicada como código e NÃO rouba o canônico 'produto' do nome real
    # ("descricao_produto"/"nome_produto"). A ordem do dicionário é a inteligência.
    "codigo":      ["id produto", "id do produto", "codigo produto", "codigo",
                    "cod produto", "cod barras", "ean", "sku", "ref", "cod "],
    "produto":     ["nome do produto", "descricao do produto", "descricao produto",
                    "nome produto", "produto", "mercadoria", "descricao do item", "descricao"],
    # estoque ANTES de quantidade — "Qtde Estoque" não pode cair em qtd
    "estoque":     ["estoque atual", "saldo estoque", "saldo atual", "estoque"],
    # custo ANTES de venda — só por consistência
    "valor_custo": ["total custo", "vr custo", "vlr custo", "valor custo",
                    "custo total", "custo"],
    # 'faturamento' é o TOTAL por linha (qtd x preço) → é o valor de venda real.
    # Mantemos 'preco/preco_unitario' FORA daqui de propósito: somar preço
    # unitário inflaria o faturamento. Casamos o total, nunca o unitário.
    "valor_venda": ["faturamento", "arrecadado", "total venda", "total vendas",
                    "vr venda", "vlr venda", "valor total venda", "total liquido",
                    "valor venda", "vr total", "valor total"],
    # preço UNITÁRIO (vem DEPOIS de valor_venda: o total explícito sempre vence).
    # Só é usado para DERIVAR o total (qtd x unitário) quando não há coluna de total.
    "preco_unitario": ["preco unitario", "preco unit", "valor unitario", "vlr unitario",
                       "preco venda", "preco"],
    "quantidade":  ["qtde vend", "qtde vendida", "quantidade vendida", "qtd vendida",
                    "qtde total", "qtd vend", "qtde", "quantidade", "qtd"],
    # 'lucro' é DETECTADO defensivamente (reservar a coluna) e DESCARTADO
    # no cálculo. NEXO/PI2 NÃO usa lucro/CMV como KPI — terminologia oficial.
    "lucro":       ["lucro"],
}

def _mapear_cabecalho(linha_norm: list, aliases: dict) -> dict:
    """
    Para cada COLUNA da linha (já normalizada), encontra o 1º canônico cujo
    fragmento aparece como substring. Cada canônico é claimed no máximo 1x
    (1ª coluna vence — proteção contra duplicatas no relatório).
    """
    mapa: dict = {}
    for idx, chave in enumerate(linha_norm):
        if not chave:
            continue
        for canonico, fragmentos in aliases.items():
            if canonico in mapa:
                continue
            for frag in fragmentos:
                if frag in chave:
                    mapa[canonico] = idx
                    break
            if canonico in mapa and mapa[canonico] == idx:
                break
    return mapa

def _detectar_cabecalho(df_bruto: pd.DataFrame, aliases: dict, valida_fn,
                        janela: int = 100):
    """
    Localiza a linha de cabeçalho na janela inicial:
      1) Cabeçalho de UMA linha — escolhe a que mapeia MAIS canônicos
         entre as que passam por `valida_fn` (cobertura mínima).
      2) Cabeçalho COMPOSTO (2 linhas adjacentes concatenadas) — fallback
         para PDVs que quebram títulos em duas linhas.
    Retorna (idx_cabecalho, mapa_canonico, linhas_cabecalho).

    Em caso de falha, levanta ETLValidationError com DIAGNÓSTICO acionável
    (quais colunas foram reconhecidas) — nunca fabrica colunas: um relatório
    sem as colunas essenciais não vira KPI inventado (integridade do dado).
    """
    limite = min(janela, len(df_bruto))
    melhor = None
    melhor_parcial: dict = {}   # melhor mapeamento visto, mesmo sem passar na validação

    # 1) cabeçalho de 1 linha
    for i in range(limite):
        linha = [_norm_chave(v) for v in df_bruto.iloc[i].tolist()]
        mapa = _mapear_cabecalho(linha, aliases)
        if len(mapa) > len(melhor_parcial):
            melhor_parcial = mapa
        if valida_fn(mapa) and (melhor is None or len(mapa) > len(melhor[1])):
            melhor = (i, mapa, 1)
    if melhor is not None:
        return melhor

    # 2) cabeçalho composto (2 linhas)
    for i in range(limite - 1):
        l1 = [_norm_chave(v) for v in df_bruto.iloc[i].tolist()]
        l2 = [_norm_chave(v) for v in df_bruto.iloc[i + 1].tolist()]
        # zip por menor comprimento — colunas extras ficam de fora
        comb = [(a + " " + b).strip() for a, b in zip(l1, l2)]
        mapa = _mapear_cabecalho(comb, aliases)
        if len(mapa) > len(melhor_parcial):
            melhor_parcial = mapa
        if valida_fn(mapa) and (melhor is None or len(mapa) > len(melhor[1])):
            melhor = (i, mapa, 2)
    if melhor is not None:
        return melhor

    reconhecidas = ", ".join(sorted(melhor_parcial.keys())) if melhor_parcial else "nenhuma"
    raise ETLValidationError(
        f"Não consegui identificar as colunas essenciais nas primeiras {limite} "
        f"linhas do relatório. Colunas reconhecidas: {reconhecidas}. "
        "Confirme que o arquivo é o relatório tabular do PDV — VENDAS precisa de "
        "produto, quantidade e valor; COMPRAS precisa de fornecedor e valor — e reenvie."
    )

_PADRAO_LIXO = re.compile(
    r"\b(?:total geral|totais|subtotal|movimenta|labsofti|software|"
    r"resumo|periodo|usuario|filtro|impresso|pagina)\b",
    re.IGNORECASE,
)

_CABECALHOS_REPETIDOS = {
    "codigo", "produto", "nome do produto", "descricao",
    "data", "data emissao", "data nf", "fornecedor",
    "valor nf", "vr total", "total nf",
}

def _construir_df_canonico(df_bruto: pd.DataFrame, idx_cab: int,
                           mapa: dict, linhas_cab: int) -> pd.DataFrame:
    """Recorta a partir da 1ª linha de dados e renomeia para nomes canônicos."""
    inicio = idx_cab + linhas_cab
    if inicio >= len(df_bruto):
        raise ETLValidationError("Cabeçalho localizado, mas sem linhas de dados após ele.")
    bloco = df_bruto.iloc[inicio:].reset_index(drop=True)
    out = pd.DataFrame(index=bloco.index)
    for nome_canonico, col_idx in mapa.items():
        if col_idx < bloco.shape[1]:
            out[nome_canonico] = bloco.iloc[:, col_idx].values
        else:
            out[nome_canonico] = pd.Series([None] * len(bloco))
    return out

def _filtrar_linhas_validas(df: pd.DataFrame, chave: str) -> pd.DataFrame:
    """
    Descarta linhas onde a coluna-chave está vazia, é rodapé/marca d'água, OU
    é um cabeçalho reimpresso (quebra de página típica do PDV).
    """
    if chave not in df.columns:
        raise ETLValidationError(f"Coluna-chave '{chave}' ausente após o mapeamento.")
    bruto = df[chave].map(lambda v: "" if v is None else str(v).strip())
    valido = bruto.map(lambda v: v.lower() not in ("", "nan", "none"))
    nao_rodape = ~bruto.str.contains(_PADRAO_LIXO, na=False)
    nao_cabec = ~bruto.map(_norm_chave).isin(_CABECALHOS_REPETIDOS)
    return df[valido & nao_rodape & nao_cabec].reset_index(drop=True)

_RE_COLUNA_SITUACAO = re.compile(
    r"\b(?:status|situacao|operacao|natureza|movimento|movimentacao)\b"
    r"|^tipo$|^tipo (?:de )?(?:venda|nota|documento|doc|registro|lancamento)\b"
)

_RE_COLUNA_DE_OUTRO_ASSUNTO = re.compile(
    r"\b(?:pagamento|entrega|cliente|produto|estoque|financeiro|financeira|titulo|cadastro)\b"
)

_RE_LINHA_CANCELADA = re.compile(r"(?<![A-Z0-9])(?<!NAO )(?<!SEM )(?:CANC|ESTORN|INUTILIZ)")

_RE_LINHA_DEVOLUCAO = re.compile(r"(?<![A-Z0-9])(?<!NAO )(?<!SEM )(?:DEVOL|TROCA)")

def _situacao_das_linhas(df_bruto: pd.DataFrame, idx_cab: int, mapa: dict, linhas_cab: int):
    """Texto normalizado das colunas de status/operação de cada linha; None se não houver."""
    titulos = [[_norm_chave(v) for v in df_bruto.iloc[i].tolist()]
               for i in range(idx_cab, idx_cab + linhas_cab)]
    usadas = set(mapa.values())
    colunas = []
    for indice, partes in enumerate(zip(*titulos)):
        chave = " ".join(partes).strip()
        if (indice not in usadas and _RE_COLUNA_SITUACAO.search(chave)
                and not _RE_COLUNA_DE_OUTRO_ASSUNTO.search(chave)):
            colunas.append(indice)
    if not colunas:
        return None
    bloco = df_bruto.iloc[idx_cab + linhas_cab:, colunas]
    return [" ".join(_norm_chave(v).upper() for v in linha if not pd.isna(v))
            for linha in bloco.itertuples(index=False, name=None)]

def _aplicar_situacao_das_vendas(df: pd.DataFrame, nome: str) -> pd.DataFrame:
    """
    Descarta as linhas canceladas e transforma devoluções e trocas em dedução: valor e
    quantidade ficam negativos, tenham vindo positivos ou não na planilha. Assim, somar
    o faturamento já dá o Líquido Real (vendas válidas - devoluções/trocas), sem subtrair
    duas vezes. "DEVOLUCAO CANCELADA" não aconteceu: conta como cancelada.
    """
    canceladas = df["_situacao"].map(lambda s: bool(_RE_LINHA_CANCELADA.search(s))).astype(bool)
    devolucoes = df["_situacao"].map(lambda s: bool(_RE_LINHA_DEVOLUCAO.search(s))).astype(bool)
    valor_cancelado = float(df.loc[canceladas, "valor_venda"].abs().sum())
    linhas_canceladas = int(canceladas.sum())
    devolucoes = devolucoes[~canceladas].reset_index(drop=True)
    df = df[~canceladas].drop(columns="_situacao").reset_index(drop=True)
    if df.empty:
        raise ETLValidationError(
            f"Relatório de VENDAS '{nome}' sem vendas válidas: todas as linhas estão canceladas."
        )
    df["_devolucao"] = devolucoes
    df.loc[devolucoes, "valor_venda"] = -df.loc[devolucoes, "valor_venda"].abs()
    df.loc[devolucoes, "quantidade"] = -df.loc[devolucoes, "quantidade"].abs()
    df.attrs["situacao"] = {
        "linhas_canceladas": linhas_canceladas,
        "valor_cancelado": valor_cancelado,
        "linhas_devolucao": int(devolucoes.sum()),
        "valor_devolucoes": float(-df.loc[devolucoes, "valor_venda"].sum()),
    }
    return df

def _validar_vendas(mapa: dict) -> bool:
    # Precisa de produto + quantidade + um valor: total explícito (valor_venda)
    # OU preço unitário (o total da linha é derivado de qtd x unitário).
    if not ("produto" in mapa and "quantidade" in mapa):
        return False
    return ("valor_venda" in mapa) or ("preco_unitario" in mapa)

def _vendas_do_bruto(bruto: pd.DataFrame, nome: str) -> pd.DataFrame:
    """carregar_vendas a partir da matriz já lida: o Raio-X lê cada arquivo uma vez só e
    tira dela também o período do cabeçalho (_extrair_periodo_base)."""
    if bruto.empty:
        raise ETLValidationError(f"O arquivo de vendas '{nome}' está totalmente vazio.")

    idx, mapa, linhas_cab = _detectar_cabecalho(bruto, ALIAS_VENDAS, _validar_vendas)
    # Título normalizado de cada coluna reconhecida. Os KPIs não o usam; o Raio-X precisa
    # saber se o custo é unitário e se o total da linha veio do preço unitário.
    cabecalhos = {canonico: " ".join(_norm_chave(bruto.iat[idx + k, coluna]) for k in range(linhas_cab)).strip()
                  for canonico, coluna in mapa.items()}
    df = _construir_df_canonico(bruto, idx, mapa, linhas_cab)
    situacao = _situacao_das_linhas(bruto, idx, mapa, linhas_cab)
    if situacao is not None:
        df["_situacao"] = situacao
    df = _filtrar_linhas_validas(df, "produto")

    # Conversões numéricas — NaN vira 0 (linha sem qtd/valor não impacta KPI)
    qualidade = Counter()
    df["quantidade"] = _converter_serie(df["quantidade"]).fillna(0.0)
    if "valor_venda" in df.columns:
        df["valor_venda"] = _converter_serie_monetaria(df["valor_venda"], qualidade)
    elif "preco_unitario" in df.columns:
        # Sem coluna de total: deriva o faturamento da linha (qtd x preço unitário).
        # Cálculo honesto a partir de colunas reais — não é dado inventado.
        df["valor_venda"] = _converter_serie_monetaria(df["preco_unitario"], qualidade) * df["quantidade"]
        logger.info("VENDAS '%s': faturamento derivado de quantidade x preço unitário.", nome)
    else:
        raise ETLValidationError(
            f"Relatório de VENDAS '{nome}' sem coluna de valor (nem total, nem preço unitário)."
        )
    if "valor_custo" in df.columns:
        df["valor_custo"] = _converter_serie_monetaria(df["valor_custo"], qualidade)
    if "estoque" in df.columns:
        df["estoque"] = _converter_serie(df["estoque"]).fillna(0.0)

    # 'lucro' é DETECTADO e DESCARTADO — terminologia NEXO proíbe usar.
    if "lucro" in df.columns:
        df = df.drop(columns=["lucro"])

    df["_prod_norm"] = df["produto"].map(_normalizar_produto)
    # Remove vazios e linhas que não são produto (descontos, frete, troco...),
    # que distorceriam o ranking de faturamento e a Curva ABC.
    df = df[(df["_prod_norm"] != "") & (~df["_prod_norm"].isin(_NAO_PRODUTOS))].reset_index(drop=True)
    if df.empty:
        raise ETLValidationError(
            f"Relatório de VENDAS '{nome}' sem nomes de produto válidos após a limpeza."
        )
    if "_situacao" in df.columns:
        df = _aplicar_situacao_das_vendas(df, nome)
    df.attrs["qualidade"] = dict(qualidade)
    df.attrs["cabecalhos"] = cabecalhos
    return df

_RE_DATA_BR = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{2,4})")

def _parse_data_br(grupos) -> "datetime.date | None":
    d, m, y = (int(x) for x in grupos)
    if y < 100:
        y += 2000  # ano de 2 dígitos: 26 -> 2026
    try:
        return datetime(y, m, d).date()
    except ValueError:
        return None

def _extrair_periodo_base(df_bruto: pd.DataFrame, janela: int = 30):
    """
    Varre as primeiras linhas procurando um cabeçalho de 'período' e extrai as
    duas datas (início, fim). Retorna (date, date) ou None se não encontrar.
    """
    limite = min(janela, len(df_bruto))
    for i in range(limite):
        for cell in df_bruto.iloc[i].tolist():
            if cell is None:
                continue
            txt = _strip_acentos(str(cell)).lower()
            if "periodo" not in txt:
                continue
            datas = [d for d in (_parse_data_br(g) for g in _RE_DATA_BR.findall(str(cell))) if d]
            if len(datas) >= 2:
                ini, fim = datas[0], datas[1]
                return (ini, fim) if ini <= fim else (fim, ini)
            if len(datas) == 1:
                return datas[0], datas[0]
    return None
