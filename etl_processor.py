"""
NEXO - Faturamento Inteligente | Motor ETL UNIVERSAL (v3)
==========================================================
Processa relatórios de PDV (Vendas + Compras) com mapeamento DINÂMICO de
cabeçalhos: independe da posição das colunas, do nome exato, do tamanho da
janela temporal (15 dias, mês, trimestre, ano ou histórico inteiro) e
tolera sujeira (linhas decorativas, quebras de página, totalizações,
células e linhas em branco entre os registros).

Estratégia (4 camadas):
  1) Leitura crua: lê o arquivo SEM assumir cabeçalho (header=None,
     dtype=str), preservando a matriz como string para a varredura.
  2) Detecção de cabeçalho: varre as primeiras 60 linhas e procura a
     linha (ou 2 linhas adjacentes, no caso de cabeçalho composto) que
     MELHOR mapeia os aliases canônicos via substring normalizada.
  3) DataFrame canônico: a partir da 1ª linha de dados, monta um DF só
     com as colunas reconhecidas, renomeadas para nomes canônicos.
  4) Filtro de lixo: descarta linhas onde a coluna-chave é nula ou
     contém marcadores de rodapé/cabeçalho repetido (totais, "Movimenta",
     marca d'água "LabSofti" etc.).

Regras inegociáveis (MVP/PI2):
  - DataFrames vivem APENAS em memória; só os KPIs finais são persistidos.
  - O indicador de descasamento é "Indicador de Pressão de Estoque"
    (saldo estimado entre compras e vendas). NUNCA expor lucro, margem,
    CMV, prejuízo, rentabilidade ou estoque real como KPI.
  - 'Lucro' e 'Total Custo' do PDV são DETECTADOS para mapeamento
    defensivo (não confundem com outras colunas) e DESCARTADOS para fins
    de KPI. 'Total Custo' pode gerar APENAS o alerta "venda abaixo do
    custo informado pelo PDV" — observação do dado bruto, NÃO margem.
  - Falha de leitura/validação nunca é mascarada com dados falsos.
  - Status CONCLUIDO nunca é setado aqui — é decisão humana via admin.

Assinatura imutável:
  processar_arquivos_analise(caminho_vendas, caminho_compras,
                             id_analise, db_session) -> ResultadoETL
"""

import os
import re
import csv
import io
import logging
import unicodedata
from datetime import datetime, timezone
from collections import namedtuple

import pandas as pd
from sqlalchemy import select

from etl_inputs import ETLInputError, read_raw
from etl_limits import get_limits

logger = logging.getLogger(__name__)

ResultadoETL = namedtuple(
    "ResultadoETL", ["sucesso", "mensagem", "kpis", "telemetria", "alertas"]
)

# Quantos produtos do topo do ranking persistir/exibir na Curva ABC.
TOP_N_CURVA_ABC = 20

# Detalhamento por produto (operação "calculate_detailed" do worker isolado):
# ranking completo e movimentação compras x vendas, persistidos à parte em
# produto_desempenho_analise. NÃO altera o resultado financeiro (top-20, chaves e
# valores idênticos aos da operação "calculate"). Há teto de linhas por análise
# (volume no banco) e uma reserva do orçamento de saída do worker
# (max_output_bytes) para o resultado principal: o detalhamento nunca derruba o
# processamento, no máximo é registrado de forma parcial (e isso é declarado).
LIMITE_PRODUTOS_DETALHADOS = 5000
RESERVA_SAIDA_RESULTADO = 256 * 1024
VERSAO_DETALHAMENTO = 1
# Códigos compactos da situação de cada produto na comparação compras x vendas.
SITUACOES_DETALHAMENTO = {
    "C": "COMPARAVEL",
    "S": "SEM_VENDA_CORRESPONDENTE",
    "D": "UNIDADE_DIVERGENTE",
    "M": "UNIDADE_AMBIGUA",
    "Q": "QUANTIDADE_INVALIDA",
}
COLUNAS_DETALHAMENTO = (
    "chave", "nome", "posicao", "classe", "faturamento", "quantidade_vendida",
    "percentual_individual", "percentual_acumulado", "quantidade_comprada",
    "unidade_venda", "unidade_compra", "situacao", "diferenca", "posicao_movimentacao",
)

# Limiares do Princípio de Pareto (Curva ABC) sobre o faturamento ACUMULADO:
#   Classe A (Estratégicos): até 80%
#   Classe B (Táticos):      de 80% a 95%
#   Classe C (Operacionais): os ~5% restantes
ABC_LIMITE_A = 80.0
ABC_LIMITE_B = 95.0


class ETLValidationError(ETLInputError):
    """Mantém o tipo público anterior e a identificação segura de limites."""

    def __init__(self, mensagem, code="data"):
        super().__init__(code, mensagem)


# Encodings e separadores tentados em sequência para arquivos texto/CSV
ENCODINGS = ("utf-8-sig", "cp1252", "utf-8", "latin1")
SEPARADORES = (";", ",", "\t", "|")


# =====================================================================
# 1) Sanitização de strings
# =====================================================================
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


# Limite do nome EXIBÍVEL do produto: um valor vindo da planilha não deve
# estourar as colunas do banco, o layout do PDF nem os rótulos dos gráficos.
LIMITE_NOME_PRODUTO = 200


def _nome_exibivel(valor) -> str:
    """Nome de produto com teto de tamanho (proteção de armazenamento/layout) e
    sem NUL. Preserva o restante do conteúdo: os números financeiros e os nomes
    permanecem equivalentes ao motor original; a sanitização para uma linha é
    responsabilidade da camada de exibição (templates/PDF). Não é a chave de
    agrupamento (essa é _normalizar_produto)."""
    return str(valor or "").replace("\x00", "")[:LIMITE_NOME_PRODUTO]


# Linhas que NÃO são produto e contaminam rankings/Curva ABC quando o PDV as
# exporta como itens (ex.: "Descontos:" aparecendo como 50% do faturamento).
# Comparadas contra o nome JÁ normalizado por _normalizar_produto (uppercase,
# sem acento/pontuação). Match exato para não derrubar produtos reais.
_NAO_PRODUTOS = {
    "DESCONTO", "DESCONTOS", "ACRESCIMO", "ACRESCIMOS", "FRETE", "TROCO",
    "TAXA", "TAXAS", "JUROS", "TOTAL", "SUBTOTAL", "TOTAL GERAL",
    "ARREDONDAMENTO", "ENTRADA", "SANGRIA", "SUPRIMENTO",
}


# =====================================================================
# 2) Conversão numérica robusta (pt-BR e en-US)
# =====================================================================
def _parse_valor(bruto):
    """
    Aceita 'R$ 1.234,56', '1.234,56', '1234,56', '1,234.56', '1234.56',
    '(123,45)', ' - ', '', None — retorna float ou None se irrecuperável.
    """
    if bruto is None:
        return None
    s = str(bruto).strip()
    # Formula neutralization prefixes text with an apostrophe. Remove it before
    # detecting the sign so negative quantities and monetary amounts stay negative.
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


# =====================================================================
# 3) Leitura defensiva (.xlsx / .csv) sem assumir cabeçalho
# =====================================================================
def _trim_vazios(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove linhas e colunas COMPLETAMENTE vazias da matriz crua. Resolve dois
    tipos de "sujeira" comuns em exportações de PDV sem mascarar dado real:
      - linhas em branco decorativas no topo (empurram o cabeçalho para baixo);
      - colunas vazias à esquerda/entre dados (deslocamento de colunas).
    `how="all"` só descarta o que é integralmente nulo — nenhum dado é perdido.
    """
    if df is None or df.empty:
        return df
    limpo = df.dropna(axis=0, how="all").dropna(axis=1, how="all")
    return limpo.reset_index(drop=True) if not limpo.empty else df


def _ler_bruto(caminho_arquivo: str) -> pd.DataFrame:
    """Leitura limitada; conversões e seleção de aba preservam o contrato anterior."""
    try:
        return read_raw(caminho_arquivo, get_limits())
    except ETLInputError as erro:
        raise ETLValidationError(erro.safe_message, erro.code) from None


# =====================================================================
# 4) Dicionário de aliases — mapeamento DINÂMICO por substring
# =====================================================================
# IMPORTANTE: a ORDEM dos canônicos importa. Fragmentos mais ESPECÍFICOS
# devem vir ANTES de fragmentos mais GENÉRICOS, para evitar colisões
# (ex.: "Qtde Estoque" cair em quantidade, "Vr Total Produtos" cair em
# valor_nf). Todos os fragmentos estão escritos JÁ na forma normalizada
# (sem acento, minúsculas, sem pontuação, sem espaços extras).

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

ALIAS_COMPRAS = {
    # codigo no topo, mesmo motivo do dicionário de vendas (absorve "id_produto").
    "codigo":         ["id produto", "id do produto", "codigo produto", "codigo",
                       "cod produto", "cod barras"],
    "data":           ["data emissao", "data nf", "data entrada", "data compra", "data"],
    "fornecedor":     ["razao social fornecedor", "nome fornecedor", "fornecedor",
                       "razao social", "emitente"],
    # produtos_total ANTES de valor_nf — "Vr Total Produtos" é mais específico
    "produtos_total": ["total produtos", "vr total produtos", "vr produtos",
                       "total mercadorias", "valor produtos"],
    # valor da compra a nível de NF OU de item: 'total_compra' (C1) e
    # 'total_custo' (C4 item-level) são o total da linha — nunca o unitário.
    "valor_nf":       ["valor nf", "total compra", "total custo", "vr total", "total nf",
                       "total da nota", "valor total", "valor nota", "vr nf", "vr nota"],
    # custo UNITÁRIO (depois de valor_nf: o total explícito sempre vence). Usado
    # para DERIVAR o total (qtd x unitário) quando não há coluna de total.
    "custo_unitario": ["custo unitario", "custo unit", "vr unitario", "vlr unitario",
                       "preco unitario", "valor unitario"],
    # Colunas item-a-item (relatórios de compra por produto, não por NF):
    "produto":        ["nome do produto", "descricao do produto", "descricao produto",
                       "nome produto", "descricao", "mercadoria", "produto"],
    "qtde_comprada":  ["qtde comprada", "quantidade comprada", "qtd comprada",
                       "qtde compra", "qtd compra", "qtde"],
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


# =====================================================================
# 5) DataFrame canônico + limpeza de linhas-lixo
# =====================================================================
# Linhas-rodapé / marca d'água típicas de PDV (regex case-insensitive).
_PADRAO_LIXO = re.compile(
    r"\b(?:total geral|totais|subtotal|movimenta|labsofti|software|"
    r"resumo|periodo|usuario|filtro|impresso|pagina)\b",
    re.IGNORECASE,
)

# Strings que, se aparecerem como valor da coluna-chave, indicam que aquela
# linha é um cabeçalho REPETIDO (quebra de página do PDV) — devem ser puladas.
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


# =====================================================================
# 5b) Unidade de medida (opcional; usada só no detalhamento por produto)
# =====================================================================
# A comparação de unidades compradas x vendidas só é confiável quando as
# unidades são as mesmas. A coluna é reconhecida por cabeçalho EXATO (nunca por
# fragmento: "Vr Unitário" e "Fundo" não podem ser confundidos), fora das
# colunas já mapeadas, e só é aceita se os valores parecerem unidades de medida
# — uma coluna "Unidade" com nomes de loja/filial é ignorada.
_CABECALHOS_UNIDADE = frozenset({
    "un", "und", "unid", "unidade", "unidades", "um", "u m", "un med", "unid med",
    "unidade medida", "unidade de medida", "unid medida", "unid de medida", "un medida",
})
_SINONIMOS_UNIDADE = {
    "UN": "UN", "UND": "UN", "UNID": "UN", "UNIDADE": "UN", "UNIDADES": "UN", "U": "UN", "UNI": "UN",
    "PC": "PC", "PCS": "PC", "PECA": "PC", "PECAS": "PC",
    "CX": "CX", "CXA": "CX", "CAIXA": "CX", "CAIXAS": "CX",
    "PCT": "PCT", "PACOTE": "PCT", "PACOTES": "PCT",
    "KG": "KG", "KGS": "KG", "QUILO": "KG", "QUILOS": "KG", "KILO": "KG", "KILOS": "KG",
    "G": "G", "GR": "G", "GRS": "G", "GRAMA": "G", "GRAMAS": "G",
    "L": "L", "LT": "L", "LTS": "L", "LITRO": "L", "LITROS": "L", "ML": "ML",
    "M": "M", "MT": "M", "MTS": "M", "METRO": "M", "METROS": "M", "M2": "M2", "M3": "M3",
    "FD": "FD", "FARDO": "FD", "FARDOS": "FD", "DZ": "DZ", "DUZIA": "DZ",
    "SC": "SC", "SACO": "SC", "SACOS": "SC", "FR": "FR", "FRASCO": "FR", "GL": "GL", "GALAO": "GL",
    "LATA": "LATA", "BD": "BD", "BALDE": "BD", "BJ": "BJ", "BANDEJA": "BJ", "RL": "RL", "ROLO": "RL",
    "PAR": "PAR", "KIT": "KIT", "CJ": "CJ", "CONJUNTO": "CJ", "TB": "TB", "TUBO": "TB",
    "DP": "DP", "DISPLAY": "DP", "EMB": "EMB", "EMBALAGEM": "EMB",
}
# Embalagem com fator ("CX12", "FD6"): mesma família, mas fatores diferentes
# NÃO são a mesma unidade (CX12 ≠ CX6), então o código é mantido como está.
_RE_UNIDADE_FATOR = re.compile(r"^(" + "|".join(sorted(_SINONIMOS_UNIDADE, key=len, reverse=True)) + r")(\d{1,4})$")
_UNIDADE_MULTIPLA = "*"
_LIMIAR_COLUNA_UNIDADE = 0.8
_AMOSTRA_COLUNA_UNIDADE = 2000


def _normalizar_unidade(valor):
    """'Un.' -> 'UN'; 'Caixa' -> 'CX'; 'cx12' -> 'CX12'; vazio -> None."""
    if valor is None:
        return None
    texto = re.sub(r"[^A-Z0-9]", "", _strip_acentos(str(valor)).upper())
    if not texto or texto in ("NAN", "NONE"):
        return None
    if texto in _SINONIMOS_UNIDADE:
        return _SINONIMOS_UNIDADE[texto]
    fator = _RE_UNIDADE_FATOR.match(texto)
    if fator:
        return _SINONIMOS_UNIDADE[fator.group(1)] + fator.group(2)
    return texto[:12]


def _unidade_reconhecida(normalizada) -> bool:
    return bool(normalizada) and (normalizada in _SINONIMOS_UNIDADE.values()
                                  or bool(_RE_UNIDADE_FATOR.match(normalizada)))


def _detectar_coluna_unidade(df_bruto: pd.DataFrame, idx_cab: int, linhas_cab: int, mapa: dict):
    """Índice da coluna de unidade de medida, ou None. Não altera o mapa canônico."""
    usadas = set(mapa.values())
    cabecalho = [_norm_chave(v) for v in df_bruto.iloc[idx_cab].tolist()]
    if linhas_cab == 2 and idx_cab + 1 < len(df_bruto):
        segunda = [_norm_chave(v) for v in df_bruto.iloc[idx_cab + 1].tolist()]
        cabecalho = [(a + " " + b).strip() for a, b in zip(cabecalho, segunda)]
    dados = df_bruto.iloc[idx_cab + linhas_cab:]
    for coluna, texto in enumerate(cabecalho):
        if coluna in usadas or texto not in _CABECALHOS_UNIDADE or coluna >= dados.shape[1]:
            continue
        amostra = [u for u in (_normalizar_unidade(v) for v in
                               dados.iloc[:_AMOSTRA_COLUNA_UNIDADE, coluna].tolist()) if u]
        if amostra and sum(map(_unidade_reconhecida, amostra)) / len(amostra) >= _LIMIAR_COLUNA_UNIDADE:
            return coluna
    return None


# =====================================================================
# 6) Carregadores específicos (Vendas / Compras)
# =====================================================================
def _validar_vendas(mapa: dict) -> bool:
    # Precisa de produto + quantidade + um valor: total explícito (valor_venda)
    # OU preço unitário (o total da linha é derivado de qtd x unitário).
    if not ("produto" in mapa and "quantidade" in mapa):
        return False
    return ("valor_venda" in mapa) or ("preco_unitario" in mapa)


def _validar_compras(mapa: dict) -> bool:
    # Aceita relatório NF-level (chave = fornecedor) ou item-level (chave = produto).
    # Valor: total explícito (valor_nf/produtos_total) OU custo unitário + quantidade
    # (o total da linha é derivado de qtd_comprada x custo_unitario).
    tem_chave = ("fornecedor" in mapa) or ("produto" in mapa)
    tem_total = ("valor_nf" in mapa) or ("produtos_total" in mapa)
    tem_derivavel = ("custo_unitario" in mapa) and ("qtde_comprada" in mapa)
    return tem_chave and (tem_total or tem_derivavel)


def _anexar_detalhamento(df: pd.DataFrame, bruto: pd.DataFrame) -> pd.DataFrame:
    """Modo detalhado: unidade normalizada e período do cabeçalho lido da MESMA
    matriz já carregada (sem reler o arquivo). Não altera linhas nem valores."""
    if "_unidade" in df.columns:
        df["_unidade"] = df["_unidade"].map(_normalizar_unidade)
    df.attrs["periodo_arquivo"] = _extrair_periodo_base(bruto)
    return df


def carregar_vendas(caminho: str, detalhado: bool = False) -> pd.DataFrame:
    nome = os.path.basename(caminho)
    bruto = _ler_bruto(caminho)
    if bruto.empty:
        raise ETLValidationError(f"O arquivo de vendas '{nome}' está totalmente vazio.")

    idx, mapa, linhas_cab = _detectar_cabecalho(bruto, ALIAS_VENDAS, _validar_vendas)
    if detalhado:
        coluna_unidade = _detectar_coluna_unidade(bruto, idx, linhas_cab, mapa)
        if coluna_unidade is not None:
            mapa = {**mapa, "_unidade": coluna_unidade}
    df = _construir_df_canonico(bruto, idx, mapa, linhas_cab)
    df = _filtrar_linhas_validas(df, "produto")

    # Conversões numéricas — NaN vira 0 (linha sem qtd/valor não impacta KPI)
    df["quantidade"] = _converter_serie(df["quantidade"]).fillna(0.0)
    if "valor_venda" in df.columns:
        df["valor_venda"] = _converter_serie(df["valor_venda"]).fillna(0.0)
    elif "preco_unitario" in df.columns:
        # Sem coluna de total: deriva o faturamento da linha (qtd x preço unitário).
        # Cálculo honesto a partir de colunas reais — não é dado inventado.
        df["valor_venda"] = _converter_serie(df["preco_unitario"]).fillna(0.0) * df["quantidade"]
        logger.info("VENDAS '%s': faturamento derivado de quantidade x preço unitário.", nome)
    else:
        raise ETLValidationError(
            f"Relatório de VENDAS '{nome}' sem coluna de valor (nem total, nem preço unitário)."
        )
    if "valor_custo" in df.columns:
        df["valor_custo"] = _converter_serie(df["valor_custo"]).fillna(0.0)
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
    return _anexar_detalhamento(df, bruto) if detalhado else df


def carregar_compras(caminho: str, detalhado: bool = False):
    """
    Retorna (df_compras, coluna_valor_usada).
    `coluna_valor_usada` ∈ {"produtos_total", "valor_nf"} — produtos_total
    tem preferência (valor "puro" dos itens; valor_nf inclui frete/imposto).
    Com detalhado=True também traz a unidade de medida (se reconhecida) e o
    período do cabeçalho; linhas e valores são os mesmos do modo padrão.
    """
    nome = os.path.basename(caminho)
    bruto = _ler_bruto(caminho)
    if bruto.empty:
        raise ETLValidationError(f"O arquivo de compras '{nome}' está totalmente vazio.")

    idx, mapa, linhas_cab = _detectar_cabecalho(bruto, ALIAS_COMPRAS, _validar_compras)
    if detalhado:
        coluna_unidade = _detectar_coluna_unidade(bruto, idx, linhas_cab, mapa)
        if coluna_unidade is not None:
            mapa = {**mapa, "_unidade": coluna_unidade}
    df = _construir_df_canonico(bruto, idx, mapa, linhas_cab)
    # Chave de validade de linha: fornecedor (NF-level) ou, na ausência dele,
    # produto (item-level) — alinhado ao validador.
    chave_linha = "fornecedor" if "fornecedor" in df.columns else "produto"
    df = _filtrar_linhas_validas(df, chave_linha)

    if "produtos_total" in df.columns:
        coluna_valor = "produtos_total"
        df[coluna_valor] = _converter_serie(df[coluna_valor]).fillna(0.0)
    elif "valor_nf" in df.columns:
        coluna_valor = "valor_nf"
        df[coluna_valor] = _converter_serie(df[coluna_valor]).fillna(0.0)
    elif "custo_unitario" in df.columns and "qtde_comprada" in df.columns:
        # Sem coluna de total: deriva o total da linha (qtd x custo unitário).
        # Cálculo honesto a partir de colunas reais — não é dado inventado.
        qtd = _converter_serie(df["qtde_comprada"]).fillna(0.0)
        custo = _converter_serie(df["custo_unitario"]).fillna(0.0)
        coluna_valor = "valor_total_compra"
        df[coluna_valor] = qtd * custo
        logger.info("COMPRAS '%s': total derivado de quantidade x custo unitário.", nome)
    else:
        raise ETLValidationError(
            f"Relatório de COMPRAS '{nome}' sem coluna de valor reconhecida "
            "(total de NF/compra/custo, nem custo unitário + quantidade)."
        )
    df = df[df[coluna_valor] > 0].reset_index(drop=True)

    if "qtde_comprada" in df.columns:
        df["qtde_comprada"] = _converter_serie(df["qtde_comprada"]).fillna(0.0)
    if "produto" in df.columns:
        df["_prod_norm"] = df["produto"].map(_normalizar_produto)
    return (_anexar_detalhamento(df, bruto) if detalhado else df), coluna_valor


# =====================================================================
# 6a) Detecção do PERÍODO DA BASE (auditoria de origem dos dados)
# =====================================================================
# Relatórios de PDV trazem o período no cabeçalho textual (ex.:
# "Período de : 01/01/26 á 31/03/26"). Extraímos isso via pandas para exibir
# no dashboard COM QUE BASE/PERÍODO os dados foram gerados — sem digitar à mão.
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


def _detectar_periodo_arquivo(caminho: str):
    """Lê o cru do arquivo e tenta extrair o período do cabeçalho. Falha → None."""
    try:
        return _extrair_periodo_base(_ler_bruto(caminho))
    except ETLValidationError:
        return None


# =====================================================================
# 6b) Curva ABC (Princípio de Pareto) sobre o faturamento por produto
# =====================================================================
def _ranking_abc(grupo: pd.DataFrame):
    """
    Ranking Pareto do UNIVERSO COMPLETO de produtos elegíveis (faturamento > 0):
    devolve (base, total) com perc_ind, perc_acum e classe por produto, em ordem
    decrescente de faturamento, ou (None, 0.0) sem produto elegível. Fonte única
    da classificação: alimenta o top-N persistido em produto_curva_abc e o
    detalhamento completo (produto_desempenho_analise) com o mesmo critério.

    Regra Pareto: ordena por faturamento desc, acumula o percentual e classifica
    A (<=80%), B (<=95%), C (resto). O produto líder é sempre Classe A — garante
    que um único produto dominante não caia em C por ultrapassar o limiar sozinho.
    """
    base = grupo[grupo["fat"] > 0].sort_values("fat", ascending=False).reset_index(drop=True)
    total = float(base["fat"].sum())
    if base.empty or total <= 0:
        return None, 0.0

    # Percentual individual e ACUMULADO calculados VETORIALMENTE no pandas:
    # cumsum sobre o ranking decrescente de faturamento = curva de Pareto.
    base["perc_ind"] = base["fat"] / total * 100.0
    base["perc_acum"] = base["perc_ind"].cumsum().clip(upper=100.0)

    # Classificação A/B/C VETORIZADA (np.select) — evita iterrows() sobre todo o
    # universo de produtos (lento em catálogos grandes). O líder (posição 0) é
    # forçado a 'A' para um único produto dominante não cair em C sozinho.
    import numpy as np
    base["classe"] = np.select(
        [base["perc_acum"] <= ABC_LIMITE_A, base["perc_acum"] <= ABC_LIMITE_B],
        ["A", "B"],
        default="C",
    )
    base.loc[0, "classe"] = "A"
    return base, total


def _classificar_curva_abc(grupo: pd.DataFrame) -> dict:
    """
    Recebe o DataFrame já agregado por produto (colunas: _prod_norm, qtde, fat,
    nome) e devolve um dict com:
      - "produtos": lista (ordenada por faturamento desc) de dicts com posicao,
        nome, faturamento, quantidade, perc_individual, perc_acumulado e classe.
        Truncada em TOP_N_CURVA_ABC para persistência/exibição.
      - "resumo": agregados por classe (qtd de produtos, faturamento e % do total)
        calculados sobre o UNIVERSO COMPLETO de produtos (não só o top-N).

    A classificação vem de _ranking_abc (mesmo critério do detalhamento).
    """
    base, total = _ranking_abc(grupo)
    if base is None:
        return {"produtos": [], "resumo": []}

    # Resumo por classe via groupby vetorizado (universo completo).
    agg = base.groupby("classe")["fat"].agg(["count", "sum"])
    contagem = {c: int(agg["count"].get(c, 0)) for c in ("A", "B", "C")}
    fat_classe = {c: float(agg["sum"].get(c, 0.0)) for c in ("A", "B", "C")}

    # Apenas o top-N é materializado para persistência/exibição — aqui sim
    # iterrows é barato (no máximo TOP_N_CURVA_ABC linhas).
    produtos = []
    tem_qtde = "qtde" in base.columns
    for i, row in base.head(TOP_N_CURVA_ABC).iterrows():
        produtos.append({
            "posicao": i + 1,
            "nome": str(row["nome"]),
            "faturamento": float(row["fat"]),
            "quantidade": float(row["qtde"]) if tem_qtde else None,
            "perc_individual": round(float(row["perc_ind"]), 2),
            "perc_acumulado": round(float(row["perc_acum"]), 2),
            "classe": str(row["classe"]),
        })

    resumo = [
        {
            "classe": c,
            "qtd_produtos": contagem[c],
            "faturamento": round(fat_classe[c], 2),
            "perc_faturamento": round(fat_classe[c] / total * 100.0, 2) if total else 0.0,
        }
        for c in ("A", "B", "C")
    ]
    return {"produtos": produtos, "resumo": resumo}


# =====================================================================
# 7) Cálculo dos KPIs em memória (sem tocar no banco)
# =====================================================================
def calcular_kpis_em_memoria(caminho_vendas: str, caminho_compras: str) -> ResultadoETL:
    """Calcula sem banco em processo próprio; limites não dependem de threads."""
    from etl_runtime import run_calculation
    try:
        return run_calculation(caminho_vendas, caminho_compras, get_limits())
    except ETLInputError as erro:
        raise ETLValidationError(erro.safe_message, erro.code) from None


def _calcular_kpis_local(caminho_vendas: str, caminho_compras: str) -> ResultadoETL:
    """Cálculo financeiro oficial (operação "calculate" do worker isolado)."""
    return _calcular_kpis_e_bases(caminho_vendas, caminho_compras)[0]


def _calcular_kpis_e_bases(caminho_vendas: str, caminho_compras: str, detalhado: bool = False):
    """Devolve (ResultadoETL, bases). O ResultadoETL é o MESMO nos dois modos;
    com detalhado=True, `bases` traz os DataFrames já agregados para o
    detalhamento por produto (sem reler os arquivos). Sem detalhamento, None."""
    nome_v = os.path.basename(caminho_vendas)

    df_v = carregar_vendas(caminho_vendas, detalhado=detalhado)
    df_c, col_valor_c = carregar_compras(caminho_compras, detalhado=detalhado)

    # ---- VENDAS: agregação por produto normalizado ----
    grupo = (
        df_v.groupby("_prod_norm")
        .agg(qtde=("quantidade", "sum"),
             fat=("valor_venda", "sum"),
             nome=("produto", "first"))
        .reset_index()
    )
    if not grupo.empty:
        grupo["nome"] = grupo["nome"].map(_nome_exibivel)
    if grupo.empty:
        raise ETLValidationError(f"Sem produtos para agregar em '{nome_v}'.")
    faturamento_total = float(grupo["fat"].sum())

    i_qtd = grupo["qtde"].idxmax()
    prod_norm_mais_vendido = grupo.loc[i_qtd, "_prod_norm"]
    produto_mais_vendido_nome = str(grupo.loc[i_qtd, "nome"])
    produto_mais_vendido_quantidade = float(grupo.loc[i_qtd, "qtde"])

    # Maior faturamento: em varejos pequenos qtde e faturamento são fortemente
    # correlacionados, então o topo dos dois rankings costuma coincidir. Para
    # evitar a redundância visual ("mesmo produto em dois cards") sem violar a
    # regra NEXO (lucro/CMV proibidos como KPI), se o produto de maior
    # faturamento coincidir com o mais vendido mostramos o 2º colocado do
    # ranking de faturamento (exigindo fat > 0 para não cair em zero falso).
    # Se sobrar só 1 candidato (relatório com produto único, ou todos os outros
    # com fat=0), aceitamos a coincidência sem mascarar.
    ranking_fat = grupo.sort_values("fat", ascending=False)
    candidatos_fat = ranking_fat[
        (ranking_fat["_prod_norm"] != prod_norm_mais_vendido) & (ranking_fat["fat"] > 0)
    ]
    linha_fat = candidatos_fat.iloc[0] if not candidatos_fat.empty else ranking_fat.iloc[0]
    produto_maior_faturamento_nome = str(linha_fat["nome"])
    produto_maior_faturamento_valor = float(linha_fat["fat"])

    # ---- Curva ABC (Princípio de Pareto) sobre o faturamento por produto ----
    curva_abc = _classificar_curva_abc(grupo)

    # ---- Período da base (cabeçalho do relatório): vendas tem prioridade ----
    if detalhado:
        # Mesma extração (_extrair_periodo_base) sobre a MESMA matriz já lida em
        # carregar_*: resultado idêntico, sem reler os arquivos.
        periodo_vendas = df_v.attrs.get("periodo_arquivo")
        periodo_compras = df_c.attrs.get("periodo_arquivo")
        periodo_base = periodo_vendas or periodo_compras
    else:
        periodo_base = _detectar_periodo_arquivo(caminho_vendas) or _detectar_periodo_arquivo(caminho_compras)
    periodo_base_inicio = periodo_base[0] if periodo_base else None
    periodo_base_fim = periodo_base[1] if periodo_base else None

    # ---- COMPRAS: total (nível NF) ----
    total_comprado = float(df_c[col_valor_c].sum())

    # ---- Indicador de Pressão de Estoque ----
    saldo_estimado_compras_vendas = total_comprado - faturamento_total

    alertas: list = []

    # ---- Produto com maior saldo estimado parado (só se COMPRAS tem produto+qtde) ----
    produto_maior_saldo_parado_nome = None
    saldo_estimado_parado = None
    tem_prod_c = "produto" in df_c.columns and "_prod_norm" in df_c.columns
    tem_qtd_c = "qtde_comprada" in df_c.columns
    if tem_prod_c and tem_qtd_c:
        compras_prod = (
            df_c[df_c["_prod_norm"] != ""]
            .groupby("_prod_norm")
            .agg(qtde_comprada=("qtde_comprada", "sum"),
                 nome=("produto", "first"))
            .reset_index()
        )
        if not compras_prod.empty:
            compras_prod["nome"] = compras_prod["nome"].map(_nome_exibivel)
        vendas_prod = grupo[["_prod_norm", "qtde"]].rename(columns={"qtde": "qtde_vendida"})
        cruz = compras_prod.merge(vendas_prod, on="_prod_norm", how="left")
        cruz["qtde_vendida"] = cruz["qtde_vendida"].fillna(0.0)
        cruz["saldo"] = cruz["qtde_comprada"] - cruz["qtde_vendida"]
        positivos = cruz[cruz["saldo"] > 0]
        if not positivos.empty:
            i_saldo = positivos["saldo"].idxmax()
            produto_maior_saldo_parado_nome = str(positivos.loc[i_saldo, "nome"])
            saldo_estimado_parado = float(positivos.loc[i_saldo, "saldo"])
    else:
        alertas.append(
            "Limitação técnica: o relatório de COMPRAS está em nível de nota "
            "fiscal (fornecedor/valor) e não traz produto + quantidade comprada. "
            "O KPI 'produto com maior saldo estimado parado' não pôde ser "
            "calculado e foi persistido como nulo (sem gerar dado enganoso)."
        )

    # ---- Telemetria (em memória, NÃO persistida — sem campo no DER V4) ----
    # Colunas internas (prefixo "_": _prod_norm e, no modo detalhado, _unidade)
    # não são colunas do relatório e ficam fora da telemetria nos dois modos.
    colunas_v = [c for c in df_v.columns if not c.startswith("_")]
    colunas_c = [c for c in df_c.columns if not c.startswith("_")]
    telemetria = {
        "coluna_valor_compras": col_valor_c,
        "colunas_vendas": colunas_v,
        "colunas_compras": colunas_c,
        "linhas_vendas": int(len(df_v)),
        "linhas_compras": int(len(df_c)),
    }

    # Alerta: saldo de estoque NEGATIVO informado pelo PDV (não é KPI, é sinal)
    if "estoque" in df_v.columns:
        n_neg = int((df_v["estoque"] < 0).sum())
        taxa = n_neg / len(df_v) if len(df_v) else 0.0
        telemetria["produtos_estoque_pdv_negativo"] = n_neg
        telemetria["taxa_estoque_pdv_negativo"] = taxa
        if taxa > 0.10:
            alertas.append(
                f"Atenção: {n_neg} produto(s) ({taxa * 100:.1f}%) apresentam saldo "
                f"de estoque NEGATIVO informado pelo PDV — possível inconsistência "
                f"de registro no sistema do cliente."
            )

    # Alerta: venda abaixo do custo informado pelo PDV (observação, NÃO margem)
    if "valor_custo" in df_v.columns:
        abaixo = (df_v["valor_custo"] > 0) & (df_v["valor_venda"] < df_v["valor_custo"])
        n_abaixo = int(abaixo.sum())
        telemetria["itens_venda_abaixo_custo_pdv"] = n_abaixo
        if n_abaixo > 0:
            alertas.append(
                f"Alerta de custo informado pelo PDV: {n_abaixo} item(ns) tiveram "
                f"valor total de venda inferior ao custo total informado pelo PDV no "
                f"período. É um sinal extraído da coluna bruta de custo do PDV, NÃO "
                f"um cálculo contábil de margem."
            )

    kpis = {
        "faturamento_total": faturamento_total,
        "total_comprado": total_comprado,
        "saldo_estimado_compras_vendas": saldo_estimado_compras_vendas,
        "produto_mais_vendido_nome": produto_mais_vendido_nome,
        "produto_mais_vendido_quantidade": produto_mais_vendido_quantidade,
        "produto_maior_faturamento_nome": produto_maior_faturamento_nome,
        "produto_maior_faturamento_valor": produto_maior_faturamento_valor,
        "produto_maior_saldo_parado_nome": produto_maior_saldo_parado_nome,
        "saldo_estimado_parado": saldo_estimado_parado,
        # Curva ABC: NÃO é um único KPI escalar; é o ranking + resumo por classe.
        # Persistido em produto_curva_abc (1:N), não em indicador_analise.
        "curva_abc": curva_abc,
        # Período real coberto pela base (lido do cabeçalho do relatório).
        "periodo_base_inicio": periodo_base_inicio,
        "periodo_base_fim": periodo_base_fim,
    }
    resultado = ResultadoETL(
        sucesso=True,
        mensagem="Cálculo concluído em memória.",
        kpis=kpis,
        telemetria=telemetria,
        alertas=alertas,
    )
    if not detalhado:
        return resultado, None
    return resultado, {
        "grupo": grupo, "df_v": df_v, "df_c": df_c,
        "periodo_vendas": periodo_vendas, "periodo_compras": periodo_compras,
    }


# =====================================================================
# 7b) Detalhamento por produto (ranking completo + movimentação)
# =====================================================================
def chave_produto(produto_normalizado: str) -> str:
    """Identificador estável e compacto do produto (16 hex) a partir da chave de
    agrupamento do ETL (_normalizar_produto). Usado para casar o mesmo produto
    entre períodos sem trafegar nem indexar o nome normalizado inteiro."""
    import hashlib
    return hashlib.blake2b(str(produto_normalizado).encode("utf-8"), digest_size=8).hexdigest()


def _unidade_por_produto(df: pd.DataFrame):
    """Unidade de cada produto (_prod_norm -> código), ou None sem coluna de
    unidade. Mais de uma unidade para o mesmo produto vira _UNIDADE_MULTIPLA; um
    produto com alguma linha sem unidade fica sem unidade conhecida (None): parte
    da quantidade teria unidade desconhecida, e a comparação não é validada."""
    if "_unidade" not in df.columns or "_prod_norm" not in df.columns:
        return None
    base = df[df["_prod_norm"] != ""]
    if base.empty:
        return pd.Series(dtype=object)
    import numpy as np
    agg = base.groupby("_prod_norm")["_unidade"].agg(["nunique", "first", "count", "size"])
    unidade = np.where(agg["nunique"] == 1, agg["first"], _UNIDADE_MULTIPLA).astype(object)
    unidade[(agg["count"] < agg["size"]).to_numpy()] = None
    return pd.Series(unidade, index=agg.index, dtype=object)


def _num(valor, casas: int):
    """float finito arredondado, ou None (NaN/inf nunca cruzam o processo)."""
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    if numero != numero or numero in (float("inf"), float("-inf")):
        return None
    return round(numero, casas)


def _montar_detalhamento(bases: dict, orcamento_bytes: int) -> dict:
    """
    Ranking completo da Curva ABC + movimentação compras x vendas por produto,
    em formato compacto (linhas posicionais) e limitado por:
      - LIMITE_PRODUTOS_DETALHADOS linhas (volume no banco);
      - `orcamento_bytes` de JSON (o worker tem teto de saída).
    A ordem de corte intercala as duas listas (melhor posição no ranking ou na
    movimentação primeiro); os prefixos contínuos registrados de cada lista são
    informados para que nenhuma consulta exiba buracos como se fossem completos.

    Correspondência compras x vendas: pela MESMA chave normalizada do KPI de
    saldo estimado. A diferença em unidades só é calculada (situação "C") quando
    o produto aparece nos dois relatórios, as unidades não divergem e as
    quantidades são válidas; nos demais casos a linha é registrada com a
    situação, sem número artificial. Se um relatório tem coluna de unidade, um
    produto sem unidade nele não é comparado (situação "M"): unidade
    desconhecida não vira comparação validada. Linhas de compra sem produto ou
    com descrição que não é produto (frete, taxas, juros: a mesma lista que o
    relatório de vendas descarta) ficam fora do detalhamento.
    """
    import json
    import numpy as np

    grupo, df_v, df_c = bases["grupo"], bases["df_v"], bases["df_c"]
    ranking, total_abc = _ranking_abc(grupo)

    fatos = grupo[["_prod_norm", "nome", "qtde", "fat"]].copy()
    unidades_v = _unidade_por_produto(df_v)
    fatos["un_v"] = fatos["_prod_norm"].map(unidades_v) if unidades_v is not None else None
    if ranking is not None:
        posicoes = ranking[["_prod_norm", "perc_ind", "perc_acum", "classe"]].copy()
        posicoes["posicao"] = np.arange(1, len(ranking) + 1)
        fatos = fatos.merge(posicoes, on="_prod_norm", how="left")
    else:
        fatos["perc_ind"] = np.nan
        fatos["perc_acum"] = np.nan
        fatos["classe"] = None
        fatos["posicao"] = np.nan

    compras_por_produto = ("produto" in df_c.columns and "_prod_norm" in df_c.columns
                           and "qtde_comprada" in df_c.columns)
    produtos_compras = None
    if compras_por_produto:
        compras_prod = (
            df_c[df_c["produto"].notna() & (df_c["_prod_norm"] != "")
                 & ~df_c["_prod_norm"].isin(_NAO_PRODUTOS)]
            .groupby("_prod_norm")
            .agg(qtde_comprada=("qtde_comprada", "sum"), nome_c=("produto", "first"))
            .reset_index()
        )
        compras_prod["nome_c"] = compras_prod["nome_c"].map(_nome_exibivel)
        unidades_c = _unidade_por_produto(df_c)
        compras_prod["un_c"] = compras_prod["_prod_norm"].map(unidades_c) if unidades_c is not None else None
        produtos_compras = int(len(compras_prod))
        fatos = fatos.merge(compras_prod, on="_prod_norm", how="outer")
        fatos["nome"] = fatos["nome"].fillna(fatos["nome_c"])
    else:
        fatos["qtde_comprada"] = np.nan
        fatos["un_c"] = None

    em_compras = fatos["qtde_comprada"].notna()
    em_vendas = fatos["qtde"].notna()
    un_v = fatos["un_v"].where(fatos["un_v"].notna(), None)
    un_c = fatos["un_c"].where(fatos["un_c"].notna(), None)
    sem_unidade = ((un_v.isna() & (unidades_v is not None))
                   | (un_c.isna() & bool(compras_por_produto and "_unidade" in df_c.columns)))
    ambigua = (un_v == _UNIDADE_MULTIPLA) | (un_c == _UNIDADE_MULTIPLA) | sem_unidade
    divergente = un_v.notna() & un_c.notna() & (un_v != un_c)
    invalida = (fatos["qtde_comprada"] <= 0) | (fatos["qtde"] < 0)
    fatos["situacao"] = np.select(
        [~em_compras, ~em_vendas, ambigua, divergente, invalida],
        ["", "S", "M", "D", "Q"], default="C")
    fatos["diferenca"] = np.where(fatos["situacao"] == "C",
                                  fatos["qtde_comprada"] - fatos["qtde"], np.nan)

    # Ordem da movimentação: comparáveis por maior diferença; depois as demais
    # situações (sem número), por quantidade comprada.
    mov = fatos[em_compras].copy()
    mov["_ordem_sit"] = (mov["situacao"] != "C").astype(int)
    mov["_dif_ord"] = mov["diferenca"].fillna(0.0)
    mov = mov.sort_values(["_ordem_sit", "_dif_ord", "qtde_comprada", "nome"],
                          ascending=[True, False, False, True], kind="mergesort")
    fatos["posicao_mov"] = np.nan
    fatos.loc[mov.index, "posicao_mov"] = np.arange(1, len(mov) + 1)

    relevantes = fatos[fatos["posicao"].notna() | fatos["posicao_mov"].notna()].copy()
    relevantes["prioridade"] = relevantes[["posicao", "posicao_mov"]].min(axis=1)
    relevantes = relevantes.sort_values(["prioridade", "posicao", "posicao_mov"], kind="mergesort")
    # itertuples não aceita nomes iniciados por "_": a chave segue como "prod_norm".
    relevantes = relevantes.rename(columns={"_prod_norm": "prod_norm"})

    linhas, usados = [], 2
    limite_bytes = max(0, int(orcamento_bytes))
    for registro in relevantes.itertuples(index=False):
        if len(linhas) >= LIMITE_PRODUTOS_DETALHADOS:
            break
        posicao = int(registro.posicao) if registro.posicao == registro.posicao else None
        pos_mov = int(registro.posicao_mov) if registro.posicao_mov == registro.posicao_mov else None
        situacao = registro.situacao or None
        linha = [
            chave_produto(registro.prod_norm),
            _nome_exibivel(registro.nome),
            posicao,
            registro.classe if posicao is not None else None,
            _num(registro.fat, 2) if registro.qtde == registro.qtde else None,
            _num(registro.qtde, 4),
            _num(registro.perc_ind, 2) if posicao is not None else None,
            _num(registro.perc_acum, 2) if posicao is not None else None,
            _num(registro.qtde_comprada, 4),
            registro.un_v if isinstance(registro.un_v, str) else None,
            registro.un_c if isinstance(registro.un_c, str) else None,
            situacao,
            _num(registro.diferenca, 4) if situacao == "C" else None,
            pos_mov,
        ]
        tamanho = len(json.dumps(linha, ensure_ascii=True, allow_nan=False)) + 1
        if usados + tamanho > limite_bytes:
            break
        usados += tamanho
        linhas.append(linha)

    def _prefixo(indice: int) -> int:
        valores = sorted(linha[indice] for linha in linhas if linha[indice] is not None)
        contiguo = 0
        for valor in valores:
            if valor != contiguo + 1:
                break
            contiguo = valor
        return contiguo

    total_ranking = int(len(ranking)) if ranking is not None else 0
    total_mov = int(em_compras.sum())
    por_situacao = fatos.loc[em_compras, "situacao"].value_counts()
    totais_situacao = {letra: int(por_situacao.get(letra, 0)) for letra in ("C", "S", "D", "M", "Q")}
    ranking_registrado = _prefixo(2)
    movimentacao_registrada = _prefixo(13)
    contagem = {"A": 0, "B": 0, "C": 0}
    soma = {"A": 0.0, "B": 0.0, "C": 0.0}
    if ranking is not None:
        agg = ranking.groupby("classe")["fat"].agg(["count", "sum"])
        contagem = {c: int(agg["count"].get(c, 0)) for c in ("A", "B", "C")}
        soma = {c: float(agg["sum"].get(c, 0.0)) for c in ("A", "B", "C")}
    periodo_v, periodo_c = bases.get("periodo_vendas"), bases.get("periodo_compras")
    resumo = {
        "versao": VERSAO_DETALHAMENTO,
        "abc_total_produtos": total_ranking,
        "abc_faturamento_total": _num(total_abc, 2) or 0.0,
        "abc_produtos_a": contagem["A"], "abc_produtos_b": contagem["B"], "abc_produtos_c": contagem["C"],
        "abc_faturamento_a": _num(soma["A"], 2) or 0.0,
        "abc_faturamento_b": _num(soma["B"], 2) or 0.0,
        "abc_faturamento_c": _num(soma["C"], 2) or 0.0,
        "produtos_vendas": int(len(grupo)),
        "produtos_compras": produtos_compras,
        "compras_por_produto": bool(compras_por_produto),
        "unidade_vendas_informada": "_unidade" in df_v.columns,
        "unidade_compras_informada": bool(compras_por_produto and "_unidade" in df_c.columns),
        "periodo_vendas_inicio": periodo_v[0] if periodo_v else None,
        "periodo_vendas_fim": periodo_v[1] if periodo_v else None,
        "periodo_compras_inicio": periodo_c[0] if periodo_c else None,
        "periodo_compras_fim": periodo_c[1] if periodo_c else None,
        "produtos_registrados": len(linhas),
        "ranking_registrado": ranking_registrado,
        "movimentacao_total": total_mov,
        "movimentacao_registrada": movimentacao_registrada,
        "movimentacao_comparaveis": totais_situacao["C"],
        "movimentacao_sem_venda": totais_situacao["S"],
        "movimentacao_unidade_divergente": totais_situacao["D"],
        "movimentacao_unidade_ambigua": totais_situacao["M"],
        "movimentacao_quantidade_invalida": totais_situacao["Q"],
        "registro_limitado": bool(ranking_registrado < total_ranking or movimentacao_registrada < total_mov),
    }
    return {"resumo": resumo, "colunas": list(COLUNAS_DETALHAMENTO), "produtos": linhas}


def calcular_com_detalhamento_local(caminho_vendas: str, caminho_compras: str,
                                    orcamento_bytes: int) -> dict:
    """Operação "calculate_detailed" do worker: o MESMO ResultadoETL da operação
    "calculate" e, à parte, o detalhamento por produto. Qualquer falha do
    detalhamento (inclusive de memória) é isolada: o resultado financeiro segue
    e o detalhamento volta nulo com um código seguro."""
    resultado, bases = _calcular_kpis_e_bases(caminho_vendas, caminho_compras, detalhado=True)
    import json
    tamanho_resultado = len(json.dumps(resultado._asdict(), ensure_ascii=True, default=str))
    orcamento = int(orcamento_bytes) - tamanho_resultado - RESERVA_SAIDA_RESULTADO
    detalhamento, erro = None, None
    if orcamento <= 0:
        erro = "orcamento"
    else:
        try:
            detalhamento = _montar_detalhamento(bases, orcamento)
        except MemoryError:
            erro = "memoria"
        except Exception as falha:  # nunca derruba o resultado financeiro
            logger.warning("Detalhamento por produto indisponível (%s).", type(falha).__name__)
            erro = "detalhamento"
    return {"resultado": resultado._asdict(), "detalhamento": detalhamento, "detalhamento_erro": erro}


# =====================================================================
# 8) Persistência (somente KPIs finais) + orquestrador oficial
# =====================================================================
def _persistir_indicadores(db_session, id_analise: int, kpis: dict):
    from models import IndicadorAnalise
    indicador = db_session.execute(
        select(IndicadorAnalise).where(IndicadorAnalise.id_analise == id_analise)
    ).scalar_one_or_none()

    if indicador is None:
        indicador = IndicadorAnalise(id_analise=id_analise, versao_processamento=1)
        db_session.add(indicador)
    else:
        indicador.versao_processamento = (indicador.versao_processamento or 0) + 1

    indicador.faturamento_total = kpis["faturamento_total"]
    indicador.total_comprado = kpis["total_comprado"]
    indicador.saldo_estimado_compras_vendas = kpis["saldo_estimado_compras_vendas"]
    indicador.produto_mais_vendido_nome = kpis["produto_mais_vendido_nome"]
    indicador.produto_mais_vendido_quantidade = kpis["produto_mais_vendido_quantidade"]
    indicador.produto_maior_faturamento_nome = kpis["produto_maior_faturamento_nome"]
    indicador.produto_maior_faturamento_valor = kpis["produto_maior_faturamento_valor"]
    indicador.produto_maior_saldo_parado_nome = kpis["produto_maior_saldo_parado_nome"]
    indicador.saldo_estimado_parado = kpis["saldo_estimado_parado"]
    indicador.periodo_base_inicio = kpis.get("periodo_base_inicio")
    indicador.periodo_base_fim = kpis.get("periodo_base_fim")
    indicador.data_geracao = datetime.now(timezone.utc)
    return indicador


def _persistir_curva_abc(db_session, id_analise: int, kpis: dict) -> None:
    """
    Regrava (idempotente) o ranking ABC do top-N em produto_curva_abc:
    apaga as linhas anteriores desta análise e insere o ranking novo. Reflete
    o reprocessamento — cada execução do ETL substitui a Curva ABC anterior.
    """
    from models import ProdutoCurvaABC
    # Limpa o ranking anterior desta análise (reprocessamento limpo).
    antigos = db_session.execute(
        select(ProdutoCurvaABC).where(ProdutoCurvaABC.id_analise == id_analise)
    ).scalars().all()
    for linha in antigos:
        db_session.delete(linha)
    db_session.flush()

    for p in kpis.get("curva_abc", {}).get("produtos", []):
        db_session.add(ProdutoCurvaABC(
            id_analise=id_analise,
            posicao_ranking=p["posicao"],
            produto_nome=p["nome"],
            faturamento=p["faturamento"],
            quantidade=p.get("quantidade"),
            percentual_individual=p["perc_individual"],
            percentual_acumulado=p["perc_acumulado"],
            classe_abc=p["classe"],
        ))


def calcular_kpis_detalhados_em_memoria(caminho_vendas: str, caminho_compras: str):
    """(ResultadoETL, detalhamento|None) no processo isolado. O ResultadoETL é o
    mesmo de calcular_kpis_em_memoria; o detalhamento já vem validado."""
    from etl_runtime import run_calculation_detailed
    try:
        return run_calculation_detailed(caminho_vendas, caminho_compras, get_limits())
    except ETLInputError as erro:
        raise ETLValidationError(erro.safe_message, erro.code) from None


# Falhas da execução detalhada que não dependem do arquivo e podem não ocorrer
# no cálculo sem detalhamento (o original é refeito nesses casos).
_CODIGOS_REFAZER_SEM_DETALHAMENTO = frozenset({"output", "timeout", "worker"})


def _detalhamento_disponivel(db_session) -> bool:
    """As tabelas do detalhamento existem? A consulta ao catálogo roda num
    SAVEPOINT próprio: uma falha aqui nunca contamina a transação do ETL e só
    desliga o detalhamento (o processamento financeiro segue como antes)."""
    try:
        from detalhamento_produtos import esquema_detalhamento_disponivel
        with db_session.begin_nested():
            return esquema_detalhamento_disponivel(db_session)
    except Exception as erro:  # noqa: BLE001 - detecção nunca bloqueia o ETL
        logger.warning("Verificação do detalhamento por produto indisponível (%s).", type(erro).__name__)
        return False


def _apagar_detalhamento(db_session, id_analise: int) -> None:
    """Remove o detalhamento de processamentos anteriores da análise. "fetch" tira
    da sessão os objetos já carregados dessas linhas (a regravação pode reutilizar
    as mesmas chaves primárias, como no SQLite)."""
    from sqlalchemy import delete
    from models import IndicadorComplementarAnalise, ProdutoDesempenhoAnalise
    opcoes = {"synchronize_session": "fetch"}
    db_session.execute(delete(ProdutoDesempenhoAnalise).where(ProdutoDesempenhoAnalise.id_analise == id_analise),
                       execution_options=opcoes)
    db_session.execute(delete(IndicadorComplementarAnalise)
                       .where(IndicadorComplementarAnalise.id_analise == id_analise), execution_options=opcoes)


def _inserir_detalhamento(db_session, id_analise: int, detalhamento, versao_processamento: int) -> None:
    """Grava o detalhamento novo, marcado com a versão de indicador_analise do
    mesmo processamento (as linhas anteriores já foram apagadas)."""
    from sqlalchemy import insert
    from models import IndicadorComplementarAnalise, ProdutoDesempenhoAnalise
    if detalhamento is None:
        return
    db_session.add(IndicadorComplementarAnalise(id_analise=id_analise, versao_processamento=versao_processamento,
                                                **detalhamento["resumo"]))
    if detalhamento["produtos"]:
        db_session.execute(insert(ProdutoDesempenhoAnalise),
                           [{"id_analise": id_analise, **linha} for linha in detalhamento["produtos"]])
    db_session.flush()


def _persistir_detalhamento(db_session, id_analise: int, detalhamento, versao_processamento: int) -> None:
    """Regrava o detalhamento em DOIS SAVEPOINTs: primeiro apaga o anterior,
    depois grava o novo. Se a gravação falhar, a análise fica SEM detalhamento
    (nunca volta o de outro processamento). Erro de banco aqui (ex.: tabelas
    removidas com o processo no ar) desfaz só o detalhamento: os KPIs e a Curva
    ABC top-20 seguem gravados, e a disponibilidade do esquema volta a ser
    conferida na próxima vez. Outros erros sobem (falha fechada do ETL). Como
    defesa adicional, o portal ignora detalhamento de outra versão do indicador."""
    from sqlalchemy.exc import SQLAlchemyError
    from detalhamento_produtos import esquecer_esquema_detalhamento
    for etapa in ("apagar", "gravar"):
        try:
            with db_session.begin_nested():
                if etapa == "apagar":
                    _apagar_detalhamento(db_session, id_analise)
                else:
                    _inserir_detalhamento(db_session, id_analise, detalhamento, versao_processamento)
        except SQLAlchemyError as erro:
            esquecer_esquema_detalhamento(db_session)
            logger.warning("Detalhamento por produto não gravado (%s); KPIs preservados.", type(erro).__name__)
            return


def processar_arquivos_analise(caminho_vendas: str, caminho_compras: str,
                               id_analise: int, db_session) -> ResultadoETL:
    """
    Orquestrador oficial (assinatura imutável). Calcula em memória e persiste
    APENAS os KPIs finais. NÃO comita (caller controla transação) e NÃO
    persiste linhas processadas. Em falha, retorna sucesso=False sem gravar.

    Com as tabelas do detalhamento disponíveis (migração 5a9c3e7d1b42), usa a
    operação "calculate_detailed": o MESMO resultado financeiro + o detalhamento
    por produto. Sem elas, segue exatamente o caminho anterior ("calculate").
    """
    try:
        detalhar = _detalhamento_disponivel(db_session)
        detalhamento = None
        if detalhar:
            try:
                resultado, detalhamento = calcular_kpis_detalhados_em_memoria(caminho_vendas, caminho_compras)
            except ETLValidationError as erro:
                if erro.code not in _CODIGOS_REFAZER_SEM_DETALHAMENTO:
                    raise
                # Saída, tempo ou recursos do worker esgotados na execução detalhada:
                # o cálculo financeiro original é refeito sem o detalhamento, que
                # nunca impede um processamento que daria certo sem ele. Erros de
                # arquivo (código próprio) falhariam igual e sobem direto.
                logger.warning("Detalhamento por produto descartado (%s); cálculo refeito sem ele.", erro.code)
                resultado = calcular_kpis_em_memoria(caminho_vendas, caminho_compras)
        else:
            resultado = calcular_kpis_em_memoria(caminho_vendas, caminho_compras)
        # Somente o processo pai recebe a Session. O SAVEPOINT mantém KPIs/ABC
        # anteriores intactos em falha, sem soltar o lock externo da análise.
        with db_session.begin_nested():
            indicador = _persistir_indicadores(db_session, id_analise, resultado.kpis)
            _persistir_curva_abc(db_session, id_analise, resultado.kpis)
            if detalhar:
                _persistir_detalhamento(db_session, id_analise, detalhamento, indicador.versao_processamento)
            db_session.flush()
        return resultado._replace(
            mensagem="Processamento concluído. KPIs consolidados + Curva ABC persistidos."
        )
    except ETLInputError as erro:
        logger.warning("ETL recusado (%s).", erro.code)
        return ResultadoETL(sucesso=False, mensagem=erro.safe_message,
                            kpis={}, telemetria={}, alertas=[])
    except Exception as erro:  # não registrar SQL, caminhos, conteúdo ou credenciais
        logger.warning("Processamento ETL indisponível (%s).", type(erro).__name__)
        return ResultadoETL(sucesso=False, mensagem="Não foi possível concluir o processamento com segurança. Tente novamente ou revise os arquivos.",
                            kpis={}, telemetria={}, alertas=[])
