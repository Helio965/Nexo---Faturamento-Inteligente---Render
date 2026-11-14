"""
NEXO - Faturamento Inteligente | Inteligência comercial da Visão Geral
=====================================================================
Regras PURAS (sem banco, sem Flask) que transformam os dados já processados
pelo ETL em leitura gerencial para o cliente:

    - série histórica comparável (faturamento e compras por período);
    - distribuição da Curva ABC sobre o universo completo de produtos;
    - cartões por classe (A, B, C);
    - movimentação por produto (unidades compradas x vendidas);
    - insights (o que aconteceu / por que importa / o que fazer / objetivo);
    - recomendações priorizadas para o próximo ciclo;
    - destaques do resumo executivo.

Quem consulta o banco é `painel_cliente.py`; aqui só entram objetos com os
atributos esperados (linhas ORM ou equivalentes), o que mantém cada regra
testável de forma isolada.

Regras de confiabilidade (iguais às do ETL e de insights.py):
    - nenhum texto afirma lucro, margem, prejuízo, rentabilidade ou estoque
      físico: comparamos apenas faturamento, compras e quantidades informadas;
    - valores monetários são tratados em Decimal até a serialização final;
    - todo insight e toda recomendação têm condição de ativação verificável,
      registrada em `rastreio` (usado nos testes, não exibido ao cliente);
    - quando o dado necessário não existe, a regra simplesmente não dispara.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_FLOOR, ROUND_HALF_UP
from typing import Any, Iterable, Optional

from insights import PRESSAO_ATENCAO, PRESSAO_CRITICA

# =====================================================================
# Limiares das regras (todos documentados no relatório técnico)
# =====================================================================
CENTAVO = Decimal("0.01")
UM_DECIMO = Decimal("0.1")
CEM = Decimal("100")
ZERO = Decimal("0")

# Descasamento compras x vendas, como fração do faturamento. Os limiares de 5%
# e 15% são os dos semáforos de insights.py; a faixa de equilíbrio (de -5% a 5%)
# e a regra do sinal sem faturamento são próprias da Visão Geral (a página da
# análise chama de "giro de estoque saudável" tudo o que não passa de 5%).
PRESSAO_ATENCAO_DEC = Decimal(str(PRESSAO_ATENCAO))
PRESSAO_CRITICA_DEC = Decimal(str(PRESSAO_CRITICA))

# Participação de um único produto no faturamento a partir da qual há
# dependência relevante (concentração).
CONCENTRACAO_PRODUTO = Decimal("30")

# Variação do faturamento total entre períodos comparáveis considerada relevante.
VARIACAO_TOTAL_RELEVANTE = Decimal("10")

# Variação de faturamento de um produto entre períodos comparáveis: precisa
# ser relevante em percentual E em impacto sobre o faturamento do período.
VARIACAO_PRODUTO_RELEVANTE = Decimal("20")
IMPACTO_PRODUTO_MINIMO = Decimal("2")  # % do faturamento total do período atual

# Saída relativa (unidades vendidas / unidades compradas) por produto.
SAIDA_BAIXA = Decimal("0.5")
SAIDA_ABAIXO = Decimal("0.9")
SAIDA_ACIMA = Decimal("1.1")

# Classe B: só vira oportunidade quando tem participação mínima no faturamento.
CLASSE_B_PARTICIPACAO_MIN = Decimal("5")
# Classe C: participação reduzida no faturamento ocupando boa parte do mix.
CLASSE_C_PARTICIPACAO_MAX = Decimal("10")
CLASSE_C_MIX_MIN = Decimal("30")

# Série histórica: duração aceitável do período efetivo de cada tipo de
# análise (em dias, inclusive). Fora disso o período não é comparável.
DURACAO_POR_TIPO = {"MENSAL": (28, 31), "QUINZENAL": (13, 16)}
# Diferença máxima (dias) entre o fim de um período e o início do seguinte
# para considerá-los consecutivos; acima disso há lacuna sem informação.
TOLERANCIA_LACUNA_DIAS = 3
# Quantidade máxima de períodos exibidos nos gráficos históricos.
LIMITE_PONTOS_SERIE = 24

# Limite herdado do ETL: até esta versão só os 20 primeiros produtos do
# ranking eram persistidos em produto_curva_abc (TOP_N_CURVA_ABC = 20).
LIMITE_RANKING_LEGADO = 20

NIVEL_ORDEM = {"critico": 0, "atencao": 1, "oportunidade": 2, "informativo": 3}
PRIORIDADE_ORDEM = {"Alta": 0, "Média": 1, "Baixa": 2}

SITUACOES_MOVIMENTACAO = (
    "COMPARAVEL", "SEM_VENDA_CORRESPONDENTE", "UNIDADE_DIVERGENTE",
    "UNIDADE_AMBIGUA", "QUANTIDADE_INVALIDA",
)


# =====================================================================
# Conversões e formatação (pt-BR)
# =====================================================================
def dec(valor) -> Optional[Decimal]:
    """Decimal exato a partir do valor persistido; None se ausente ou inválido.

    Numeric chega do banco como Decimal. Floats (dados em memória ou SQLite)
    são convertidos pela representação mais curta que os reproduz, sem
    arrastar o ruído binário para o cálculo."""
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, Decimal):
        return valor if valor.is_finite() else None
    if isinstance(valor, int):
        return Decimal(valor)
    if isinstance(valor, float):
        return Decimal(repr(valor)) if math.isfinite(valor) else None
    try:
        convertido = Decimal(str(valor))
    except (InvalidOperation, ValueError):
        return None
    return convertido if convertido.is_finite() else None


def moeda(valor) -> Optional[Decimal]:
    """Valor monetário arredondado ao centavo (meio para cima)."""
    convertido = dec(valor)
    return None if convertido is None else convertido.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def percentual(parte, total, casas: int = 1) -> Optional[Decimal]:
    """parte / total em %, arredondado; None sem base (total ausente ou zero)."""
    p, t = dec(parte), dec(total)
    if p is None or t is None or t == 0:
        return None
    return (p / t * CEM).quantize(Decimal(1).scaleb(-casas), rounding=ROUND_HALF_UP)


def para_float(valor) -> Optional[float]:
    """Serialização final para os gráficos (JSON): só aqui o Decimal vira float."""
    convertido = dec(valor)
    return None if convertido is None else float(convertido)


def _milhar(texto: str) -> str:
    """'1,234.56' (formato Python) -> '1.234,56' (pt-BR)."""
    return texto.replace(",", "§").replace(".", ",").replace("§", ".")


def fmt_moeda(valor, sinal: bool = False) -> str:
    """'R$ 1.234,56'. Com sinal=True, positivos ganham '+'. Ausente -> '—'."""
    valor = moeda(valor)
    if valor is None:
        return "—"
    prefixo = "-" if valor < 0 else ("+" if sinal and valor > 0 else "")
    return f"{prefixo}R$ {_milhar(format(abs(valor), ',.2f'))}"


def fmt_quantidade(valor) -> str:
    """Quantidade sem casas quando inteira; até 2 casas quando fracionada (kg, l)."""
    valor = dec(valor)
    if valor is None:
        return "—"
    arredondado = valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)
    if arredondado == arredondado.to_integral_value():
        return _milhar(format(arredondado.to_integral_value(), ",.0f"))
    return _milhar(format(arredondado, ",.2f")).rstrip("0").rstrip(",")


def fmt_percentual(valor, sinal: bool = False, casas: int = 1) -> str:
    valor = dec(valor)
    if valor is None:
        return "—"
    valor = valor.quantize(Decimal(1).scaleb(-casas), rounding=ROUND_HALF_UP)
    prefixo = "+" if sinal and valor > 0 else ""
    return f"{prefixo}{_milhar(format(valor, f',.{casas}f'))}%"


def fmt_quantidade_sinal(valor) -> str:
    """Diferença em unidades com sinal explícito: '+20', '-5', '0'."""
    valor = dec(valor)
    if valor is None:
        return "—"
    texto = fmt_quantidade(abs(valor))
    return ("+" if valor > 0 else "-" if valor < 0 else "") + texto


def unidade_exibivel(unidade) -> Optional[str]:
    """Unidade de medida informada nos relatórios ('KG', 'L', 'CX12'...); None
    quando não informada ou múltipla ('*'): aí nenhuma unidade é presumida."""
    return unidade if isinstance(unidade, str) and unidade and unidade != "*" else None


def fmt_quantidade_unidade(valor, unidade=None, sinal: bool = False) -> str:
    """'120,5 KG' quando a unidade é conhecida; só o número quando não é."""
    texto = fmt_quantidade_sinal(valor) if sinal else fmt_quantidade(valor)
    un = unidade_exibivel(unidade)
    return f"{texto} {un}" if un and texto != "—" else texto


def fmt_data(valor) -> str:
    return valor.strftime("%d/%m/%Y") if isinstance(valor, (date, datetime)) else "—"


def rotulo_referencia(analise) -> str:
    """Rótulo curto do período declarado, no formato já usado pelo portal:
    '03/2026' (mensal) ou '1ª quinz. 03/2026' (quinzenal, sem rótulos repetidos)."""
    mes = getattr(analise, "mes_referencia", None) or 0
    base = f"{mes:02d}/{getattr(analise, 'ano_referencia', '?')}" if 1 <= mes <= 12 else "?"
    if getattr(analise, "tipo_analise", None) == "QUINZENAL" and getattr(analise, "quinzena_referencia", None) in (1, 2):
        return f"{analise.quinzena_referencia}ª quinz. {base}"
    return base


def formatadores() -> dict:
    """Formatadores pt-BR expostos ao template da Visão Geral (`fmt`)."""
    return {"moeda": fmt_moeda, "qtd": fmt_quantidade, "qtd_sinal": fmt_quantidade_sinal,
            "qtd_un": fmt_quantidade_unidade, "pct": fmt_percentual, "data": fmt_data}


def percentuais_somando_100(valores: list, casas: int = 1) -> list:
    """Percentuais de exibição que somam exatamente 100 (maiores restos).

    Evita o clássico 79,9% + 15,1% + 5,1% = 100,1% nos cartões das classes."""
    valores = [max(dec(v) or ZERO, ZERO) for v in valores]
    total = sum(valores, ZERO)
    if total <= 0:
        return [ZERO for _ in valores]
    escala = Decimal(10) ** casas
    brutos = [v / total * CEM * escala for v in valores]
    pisos = [b.to_integral_value(rounding=ROUND_FLOOR) for b in brutos]
    falta = int(CEM * escala - sum(pisos, ZERO))
    ordem = sorted(range(len(valores)), key=lambda i: (brutos[i] - pisos[i], valores[i]), reverse=True)
    for i in ordem[:max(falta, 0)]:
        pisos[i] += 1
    return [(p / escala).quantize(Decimal(1).scaleb(-casas)) for p in pisos]


# =====================================================================
# Estruturas
# =====================================================================
@dataclass(frozen=True)
class Produto:
    """Linha de produto de uma análise (ranking e/ou movimentação)."""
    nome: str
    chave: str = ""
    posicao: Optional[int] = None
    classe: Optional[str] = None
    faturamento: Optional[Decimal] = None
    quantidade_vendida: Optional[Decimal] = None
    percentual_individual: Optional[Decimal] = None
    percentual_acumulado: Optional[Decimal] = None
    quantidade_comprada: Optional[Decimal] = None
    situacao: Optional[str] = None
    diferenca: Optional[Decimal] = None
    unidade_venda: Optional[str] = None
    unidade_compra: Optional[str] = None


@dataclass
class PontoSerie:
    id_analise: int
    rotulo: str
    inicio: date
    fim: date
    faturamento: Decimal
    compras: Optional[Decimal]
    atual: bool = False
    lacuna_antes: bool = False
    periodo_do_arquivo: bool = False

    @property
    def meio(self) -> date:
        return date.fromordinal((self.inicio.toordinal() + self.fim.toordinal()) // 2)

    @property
    def dias(self) -> int:
        return (self.fim - self.inicio).days + 1


@dataclass
class SerieHistorica:
    tipo: Optional[str]
    pontos: list = field(default_factory=list)
    atual: Optional[PontoSerie] = None
    anterior: Optional[PontoSerie] = None
    excluidas: dict = field(default_factory=dict)
    atual_comparavel: bool = False
    omitidos: int = 0
    omitidos_antigos: int = 0
    omitidos_recentes: int = 0

    @property
    def tem_lacunas(self) -> bool:
        return any(p.lacuna_antes for p in self.pontos)


# =====================================================================
# 1) Série histórica comparável
# =====================================================================
def periodo_efetivo(analise):
    """Período realmente coberto: o lido do cabeçalho do relatório (ETL) ou,
    na falta dele, o período declarado da análise. Devolve (início, fim, do_arquivo)."""
    ind = getattr(analise, "indicador", None)
    if ind is not None and ind.periodo_base_inicio and ind.periodo_base_fim:
        return ind.periodo_base_inicio, ind.periodo_base_fim, True
    return analise.periodo_inicio, analise.periodo_fim, False


def _prioridade_sobreposicao(item, atual_id):
    analise = item[0]
    conclusao = getattr(analise, "data_conclusao", None)
    if isinstance(conclusao, datetime) and conclusao.tzinfo is not None:
        conclusao = conclusao.replace(tzinfo=None)
    return (analise.id_analise == atual_id, conclusao or datetime.min, analise.id_analise)


def montar_serie_historica(analises: Iterable, atual) -> SerieHistorica:
    """Série de períodos COMPARÁVEIS com a análise atual.

    Critérios (nenhum período é inventado, somado ou interpolado):
      - mesmo tipo de análise da atual (mensal com mensal, quinzenal com quinzenal);
      - período efetivo com duração típica do tipo (DURACAO_POR_TIPO);
      - períodos sobrepostos não se repetem: fica a análise atual ou, entre as
        demais, a concluída mais recentemente (as outras são descartadas). A
        escolha é feita por prioridade, não pela ordem das datas: um período só
        sai se sobrepuser outro que permaneceu na série;
      - ordem cronológica pelo início do período efetivo;
      - lacunas (períodos sem análise) são marcadas, nunca preenchidas.
    Recebe apenas análises já autorizadas pela política contratual.
    """
    tipo = getattr(atual, "tipo_analise", None) if atual is not None else None
    serie = SerieHistorica(tipo=tipo, excluidas={
        "sem_indicador": 0, "tipo_diferente": 0, "periodo_atipico": 0, "sobreposta": 0,
    })
    if atual is None or getattr(atual, "indicador", None) is None:
        return serie
    faixa = DURACAO_POR_TIPO.get(tipo)
    candidatos = []
    for analise in analises:
        ind = getattr(analise, "indicador", None)
        if ind is None or dec(ind.faturamento_total) is None:
            serie.excluidas["sem_indicador"] += 1
            continue
        if analise.tipo_analise != tipo:
            serie.excluidas["tipo_diferente"] += 1
            continue
        inicio, fim, _ = periodo_efetivo(analise)
        duracao = (fim - inicio).days + 1 if inicio and fim and fim >= inicio else 0
        if not duracao or (faixa and not (faixa[0] <= duracao <= faixa[1])):
            serie.excluidas["periodo_atipico"] += 1
            continue
        candidatos.append((analise, inicio, fim))

    # Maior prioridade primeiro (atual; depois a conclusão mais recente): cada
    # candidato entra se não sobrepuser nenhum período já aceito.
    mantidos: list = []
    for item in sorted(candidatos, key=lambda t: _prioridade_sobreposicao(t, atual.id_analise), reverse=True):
        if any(k[1] <= item[2] and item[1] <= k[2] for k in mantidos):
            serie.excluidas["sobreposta"] += 1
            continue
        mantidos.append(item)
    mantidos.sort(key=lambda t: (t[1], t[2], t[0].id_analise))

    indice_atual = next((i for i, t in enumerate(mantidos) if t[0].id_analise == atual.id_analise), None)
    serie.atual_comparavel = indice_atual is not None
    inicio_janela = max(0, len(mantidos) - LIMITE_PONTOS_SERIE)
    # A janela sempre inclui a análise atual e, quando existe, o período
    # imediatamente anterior a ela (base das variações).
    if indice_atual is not None and inicio_janela > 0 and indice_atual <= inicio_janela:
        inicio_janela = max(0, indice_atual - LIMITE_PONTOS_SERIE // 2)
    janela = mantidos[inicio_janela:inicio_janela + LIMITE_PONTOS_SERIE]
    serie.omitidos_antigos = inicio_janela
    serie.omitidos_recentes = len(mantidos) - inicio_janela - len(janela)
    serie.omitidos = serie.omitidos_antigos + serie.omitidos_recentes

    anterior_fim = None
    for analise, inicio, fim in janela:
        ind = analise.indicador
        ponto = PontoSerie(
            id_analise=analise.id_analise,
            rotulo=rotulo_referencia(analise),
            inicio=inicio, fim=fim,
            faturamento=dec(ind.faturamento_total),
            compras=dec(ind.total_comprado),
            atual=analise.id_analise == atual.id_analise,
            lacuna_antes=bool(anterior_fim and (inicio - anterior_fim).days > TOLERANCIA_LACUNA_DIAS),
            periodo_do_arquivo=bool(ind.periodo_base_inicio and ind.periodo_base_fim),
        )
        anterior_fim = fim
        serie.pontos.append(ponto)
        if ponto.atual:
            serie.atual = ponto
    if serie.atual is not None:
        posicao = serie.pontos.index(serie.atual)
        serie.anterior = serie.pontos[posicao - 1] if posicao > 0 else None
    return serie


def variacao(atual, anterior) -> Optional[dict]:
    """Variação entre dois valores comparáveis. Sem base (anterior zero) não
    há percentual; sem um dos valores não há variação alguma."""
    atual, anterior = dec(atual), dec(anterior)
    if atual is None or anterior is None:
        return None
    delta = atual - anterior
    direcao = "alta" if delta > 0 else ("queda" if delta < 0 else "estavel")
    if anterior == 0:
        return {"percentual": None, "delta": moeda(delta), "direcao": direcao, "sem_base": True}
    pct = (delta / abs(anterior) * CEM).quantize(UM_DECIMO, rounding=ROUND_HALF_UP)
    return {"percentual": pct, "delta": moeda(delta), "direcao": direcao, "sem_base": False}


def comparacao_periodos(atual: Optional[PontoSerie], anterior: Optional[PontoSerie],
                        campo: str = "faturamento") -> Optional[dict]:
    """Variação entre dois períodos da série comparável.

    `bruta` compara os totais (é a exibida nos indicadores). `relevante` é a
    usada pelas regras de insight: quando as durações diferem (28 x 31 dias,
    13 x 16 dias), compara a MÉDIA DIÁRIA, para que o calendário não apareça
    como alta ou queda de vendas."""
    if atual is None or anterior is None:
        return None
    bruta = variacao(getattr(atual, campo), getattr(anterior, campo))
    if bruta is None:
        return None
    resultado = {"bruta": bruta, "relevante": bruta, "por_dia": False,
                 "dias_atual": atual.dias, "dias_anterior": anterior.dias}
    if atual.dias != anterior.dias and not bruta["sem_base"] and atual.dias > 0 and anterior.dias > 0:
        resultado["relevante"] = variacao(dec(getattr(atual, campo)) / atual.dias,
                                          dec(getattr(anterior, campo)) / anterior.dias)
        resultado["por_dia"] = True
    return resultado


def texto_media_diaria(comparacao: Optional[dict]) -> str:
    """Frase que explica a variação pela média diária quando as durações diferem."""
    if not comparacao or not comparacao["por_dia"]:
        return ""
    rel = comparacao["relevante"]
    if rel is None or rel["sem_base"] or rel["percentual"] is None:
        return ""
    if rel["direcao"] == "estavel" or rel["percentual"] == 0:
        movimento = "ficou estável"
    else:
        movimento = ("subiu " if rel["direcao"] == "alta" else "caiu ") + fmt_percentual(abs(rel["percentual"]))
    return (f"Como os períodos têm {comparacao['dias_atual']} e {comparacao['dias_anterior']} dias, "
            f"a média diária {movimento}.")


def estatisticas_serie(pontos: list, campo: str) -> Optional[dict]:
    """Maior, menor, média, variação acumulada e tendência de uma série com >= 2 pontos.

    Maior, menor e média descrevem os totais de cada período. Quando as durações
    diferem (28 a 31 dias, 13 a 16 dias), tendência e variação acumulada usam a
    média diária (total ÷ dias), para o calendário não aparecer como alta ou
    queda de vendas; `por_dia` indica esse caso."""
    valores = [(p, getattr(p, campo)) for p in pontos if getattr(p, campo) is not None]
    if len(valores) < 2:
        return None
    maior = max(valores, key=lambda t: t[1])
    menor = min(valores, key=lambda t: t[1])
    media = sum((v for _, v in valores), ZERO) / len(valores)
    por_dia = len({p.dias for p, _ in valores}) > 1 and all(p.dias > 0 for p, _ in valores)
    base = [(p, v / p.dias) for p, v in valores] if por_dia else valores
    passos = [b[1] - a[1] for a, b in zip(base, base[1:])]
    if len(valores) >= 3:
        if all(d >= 0 for d in passos) and any(d > 0 for d in passos):
            tendencia = "crescente"
        elif all(d <= 0 for d in passos) and any(d < 0 for d in passos):
            tendencia = "decrescente"
        elif all(d == 0 for d in passos):
            tendencia = "estavel"
        else:
            tendencia = "oscilante"
    else:
        tendencia = {"alta": "alta", "queda": "queda"}.get(variacao(base[1][1], base[0][1])["direcao"], "estavel")
    return {
        "quantidade": len(valores),
        "maior": {"valor": moeda(maior[1]), "rotulo": maior[0].rotulo},
        "menor": {"valor": moeda(menor[1]), "rotulo": menor[0].rotulo},
        "media": moeda(media),
        "primeiro": valores[0][0].rotulo,
        "ultimo": valores[-1][0].rotulo,
        "variacao_acumulada": variacao(base[-1][1], base[0][1]),
        "tendencia": tendencia,
        "por_dia": por_dia,
        "periodos_sem_vendas": sum(1 for _, v in valores if v == 0) if campo == "faturamento" else 0,
    }


def _texto_variacao(var: Optional[dict], referencia: str) -> str:
    if not var:
        return ""
    if var["sem_base"]:
        return f"sem base percentual em relação a {referencia} (período anterior sem valor registrado)"
    if var["direcao"] == "estavel":
        return f"estável em relação a {referencia}"
    palavra = "alta" if var["direcao"] == "alta" else "redução"
    return f"{palavra} de {fmt_percentual(abs(var['percentual']))} em relação a {referencia}"


def _nota_exclusoes(serie: SerieHistorica) -> str:
    ex = serie.excluidas
    partes = []
    if ex.get("tipo_diferente"):
        partes.append(f"{ex['tipo_diferente']} de outro tipo de período (mensal x quinzenal)")
    if ex.get("periodo_atipico"):
        partes.append(f"{ex['periodo_atipico']} com período de duração atípica")
    if ex.get("sobreposta"):
        partes.append(f"{ex['sobreposta']} sobreposta(s) a outra análise do mesmo período")
    if serie.omitidos_antigos:
        partes.append(f"{serie.omitidos_antigos} período(s) mais antigo(s) além dos {LIMITE_PONTOS_SERIE} exibidos")
    if serie.omitidos_recentes:
        partes.append(f"{serie.omitidos_recentes} período(s) mais recente(s) além dos {LIMITE_PONTOS_SERIE} exibidos")
    if not partes:
        return ""
    return ("Não entraram na comparação, para evitar somar ou repetir dados: "
            + "; ".join(partes) + ".")


_TEXTO_ATUAL_NAO_COMPARAVEL = ("O período desta análise tem tipo ou duração diferentes dos demais e não foi "
                               "comparado com outros períodos. ")


def interpretar_evolucao_faturamento(serie: SerieHistorica) -> dict:
    """Leitura do gráfico de evolução do faturamento (sem afirmar o que a
    série não sustenta: com menos de 2 períodos comparáveis não há tendência)."""
    nota = _nota_exclusoes(serie)
    if not serie.atual_comparavel:
        return {"disponivel": False, "texto": (_TEXTO_ATUAL_NAO_COMPARAVEL + nota).strip(), "estatisticas": None}
    stats = estatisticas_serie(serie.pontos, "faturamento")
    if stats is None:
        return {"disponivel": False, "texto": (
            "A evolução do faturamento aparece a partir da segunda análise publicada com o "
            "mesmo tipo de período. " + nota).strip(), "estatisticas": None}
    frases = [
        f"Nos {stats['quantidade']} períodos comparáveis ({stats['primeiro']} a {stats['ultimo']}), "
        f"o faturamento variou entre {fmt_moeda(stats['menor']['valor'])} ({stats['menor']['rotulo']}) e "
        f"{fmt_moeda(stats['maior']['valor'])} ({stats['maior']['rotulo']}), com média de {fmt_moeda(stats['media'])}."
    ]
    if serie.anterior is not None and serie.atual is not None:
        comp = comparacao_periodos(serie.atual, serie.anterior)
        frases.append(f"O período atual ({serie.atual.rotulo}) registrou "
                      f"{_texto_variacao(comp['bruta'] if comp else None, serie.anterior.rotulo)}.")
        if texto_media_diaria(comp):
            frases.append(texto_media_diaria(comp))
    tendencia = stats["tendencia"]
    acumulada = stats["variacao_acumulada"]
    base = "Pela média diária (os períodos têm durações diferentes), o faturamento" if stats["por_dia"] else "O faturamento"
    if tendencia == "crescente":
        frases.append(f"{base} cresceu ou se manteve em todos os períodos da sequência.")
    elif tendencia == "decrescente":
        frases.append(f"{base} recuou ou se manteve em todos os períodos da sequência.")
    elif tendencia == "estavel" and stats["por_dia"]:
        frases.append(f"{base} ficou estável ao longo da sequência.")
    elif tendencia == "oscilante" and acumulada and acumulada["percentual"] is not None:
        frases.append("A sequência alterna altas e quedas; entre o primeiro e o último período a variação "
                      + ("acumulada da média diária" if stats["por_dia"] else "acumulada")
                      + f" foi de {fmt_percentual(acumulada['percentual'], sinal=True)}.")
    if stats["periodos_sem_vendas"]:
        frases.append(f"{stats['periodos_sem_vendas']} período(s) não tiveram vendas registradas.")
    if serie.tem_lacunas:
        frases.append("Há intervalos sem análise publicada entre alguns períodos; eles aparecem como "
                      "espaço sem barra no gráfico e não foram estimados.")
    if nota:
        frases.append(nota)
    return {"disponivel": True, "texto": " ".join(frases), "estatisticas": stats}


def interpretar_evolucao_compras_vendas(serie: SerieHistorica) -> dict:
    """Leitura do histórico Vendas x Compras (mesmos períodos comparáveis)."""
    pares = [p for p in serie.pontos if p.compras is not None]
    if not serie.atual_comparavel:
        return {"disponivel": False, "texto": (_TEXTO_ATUAL_NAO_COMPARAVEL + _nota_exclusoes(serie)).strip()}
    if len(pares) < 2:
        return {"disponivel": False, "texto": (
            "O histórico de compras e vendas aparece a partir da segunda análise publicada com o "
            "mesmo tipo de período. " + _nota_exclusoes(serie)).strip()}
    acima = [p for p in pares if p.compras > p.faturamento]
    frases = [f"Em {len(acima)} de {len(pares)} períodos comparáveis, as compras superaram o faturamento de vendas."]
    atual, anterior = serie.atual, serie.anterior
    if atual is not None and atual.compras is not None:
        dif_atual = atual.compras - atual.faturamento
        texto = f"No período atual ({atual.rotulo}), compras menos vendas resultou em {fmt_moeda(dif_atual)}"
        if anterior is not None and anterior.compras is not None:
            texto += f", contra {fmt_moeda(anterior.compras - anterior.faturamento)} em {anterior.rotulo}"
        frases.append(texto + ".")
    stats_compras = estatisticas_serie(pares, "compras")
    if stats_compras and stats_compras["tendencia"] in ("crescente", "decrescente"):
        frases.append(("Pela média diária, as compras " if stats_compras["por_dia"] else "As compras ")
                      + ("cresceram ou se mantiveram" if stats_compras["tendencia"] == "crescente"
                         else "recuaram ou se mantiveram") + " em todos os períodos da sequência.")
    frases.append("A comparação usa valores de compra e de venda informados nos relatórios: não representa lucro "
                  "nem saldo de estoque físico.")
    if serie.tem_lacunas:
        frases.append("Intervalos sem análise publicada aparecem como interrupção das linhas.")
    return {"disponivel": True, "texto": " ".join(frases)}


# =====================================================================
# 2) Curva ABC: distribuição e cartões por classe
# =====================================================================
@dataclass
class ClasseResumo:
    classe: str
    produtos: Optional[int]
    faturamento: Optional[Decimal]
    percentual: Optional[Decimal]
    percentual_mix: Optional[Decimal] = None


@dataclass
class DistribuicaoABC:
    disponivel: bool
    fonte: str
    motivo: Optional[str] = None
    total_produtos: Optional[int] = None
    faturamento_total: Optional[Decimal] = None
    classes: list = field(default_factory=list)
    produtos_registrados: Optional[int] = None
    registro_limitado: bool = False
    armazenados_legado: int = 0

    def classe(self, letra: str) -> Optional[ClasseResumo]:
        return next((c for c in self.classes if c.classe == letra), None)


def distribuicao_abc(complemento, linhas_legado: Optional[list] = None) -> DistribuicaoABC:
    """Participação de A, B e C calculada SEMPRE sobre todos os produtos elegíveis.

    - Análises processadas com o detalhamento: agregados exatos persistidos pelo
      ETL (universo completo, independentemente do teto de linhas registradas).
    - Análises anteriores: só há o topo do ranking (até 20 linhas). Se vieram
      menos de 20 linhas, o ranking armazenado É o universo completo; com 20,
      os demais produtos não foram armazenados e a distribuição não é exibida
      (calculá-la só com o topo distorceria as classes B e C).
    """
    if complemento is not None:
        total = dec(complemento.abc_faturamento_total)
        produtos = int(complemento.abc_total_produtos or 0)
        if not total or total <= 0 or produtos <= 0:
            return DistribuicaoABC(False, "completa", "sem_produtos", total_produtos=produtos,
                                   produtos_registrados=complemento.produtos_registrados)
        brutos = [(letra, int(getattr(complemento, f"abc_produtos_{letra.lower()}") or 0),
                   dec(getattr(complemento, f"abc_faturamento_{letra.lower()}")) or ZERO) for letra in "ABC"]
        exibidos = percentuais_somando_100([fat for _, _, fat in brutos])
        classes = [ClasseResumo(letra, qtd, moeda(fat), pct, percentual(qtd, produtos))
                   for (letra, qtd, fat), pct in zip(brutos, exibidos)]
        return DistribuicaoABC(True, "completa", total_produtos=produtos, faturamento_total=moeda(total),
                               classes=classes, produtos_registrados=complemento.produtos_registrados,
                               registro_limitado=bool(complemento.registro_limitado))
    linhas = list(linhas_legado or [])
    if not linhas:
        return DistribuicaoABC(False, "indisponivel", "sem_produtos")
    if len(linhas) >= LIMITE_RANKING_LEGADO:
        return DistribuicaoABC(False, "legado_parcial", "ranking_parcial", armazenados_legado=len(linhas))
    total = sum((dec(p.faturamento) or ZERO for p in linhas), ZERO)
    if total <= 0:
        return DistribuicaoABC(False, "legado_completo", "sem_produtos")
    contagem = {letra: 0 for letra in "ABC"}
    soma = {letra: ZERO for letra in "ABC"}
    for p in linhas:
        if p.classe in contagem:
            contagem[p.classe] += 1
            soma[p.classe] += dec(p.faturamento) or ZERO
    exibidos = percentuais_somando_100([soma[letra] for letra in "ABC"])
    classes = [ClasseResumo(letra, contagem[letra], moeda(soma[letra]), pct, percentual(contagem[letra], len(linhas)))
               for letra, pct in zip("ABC", exibidos)]
    return DistribuicaoABC(True, "legado_completo", total_produtos=len(linhas), faturamento_total=moeda(total),
                           classes=classes, produtos_registrados=len(linhas), armazenados_legado=len(linhas))


TITULOS_CLASSE = {
    "A": "Produtos estratégicos",
    "B": "Produtos intermediários",
    "C": "Produtos complementares",
}


def _lista_nomes(produtos: list, limite: int = 3) -> str:
    nomes = [f"“{p.nome}”" for p in produtos[:limite]]
    if len(nomes) <= 1:
        return "".join(nomes)
    return ", ".join(nomes[:-1]) + " e " + nomes[-1]


def cartoes_classes(dist: DistribuicaoABC, destaques: dict) -> list:
    """Cartões explicativos das classes A, B e C com dados da própria empresa.

    `destaques` traz, por classe, os produtos de maior faturamento (já
    limitados na consulta). Sem distribuição completa, o cartão mostra só os
    produtos armazenados e declara a limitação em vez de estimar participação."""
    cartoes = []
    for letra in "ABC":
        produtos = list(destaques.get(letra) or [])
        resumo = dist.classe(letra) if dist.disponivel else None
        cartao = {
            "classe": letra,
            "titulo": TITULOS_CLASSE[letra],
            "produtos": resumo.produtos if resumo else None,
            "percentual": resumo.percentual if resumo else None,
            "faturamento": resumo.faturamento if resumo else None,
            "percentual_mix": resumo.percentual_mix if resumo else None,
            "destaques": [{"nome": p.nome, "percentual": dec(p.percentual_individual),
                           "faturamento": moeda(p.faturamento)} for p in produtos],
            "leitura": "",
            "recomendacao": "",
            "vazia": bool(resumo and not resumo.produtos),
        }
        if resumo is None:
            cartao["leitura"] = ("A participação desta classe não está disponível para esta análise: "
                                 "o processamento armazenou somente os primeiros produtos do ranking.")
            cartao["recomendacao"] = ("Os produtos listados são os da classe entre os armazenados; "
                                      "um novo processamento da análise disponibiliza a distribuição completa.")
            cartoes.append(cartao)
            continue
        if not resumo.produtos:
            cartao["leitura"] = f"Nenhum produto ficou na Classe {letra} neste período."
            cartao["recomendacao"] = ""
            cartoes.append(cartao)
            continue
        mix = (f" ({fmt_percentual(resumo.percentual_mix)} do mix)" if resumo.percentual_mix is not None else "")
        cartao["leitura"] = (f"{fmt_quantidade(resumo.produtos)} produto(s){mix} somam "
                             f"{fmt_percentual(resumo.percentual)} do faturamento ({fmt_moeda(resumo.faturamento)}).")
        if letra == "A":
            texto = ("Mantenha disponibilidade, preço e exposição desses itens sob acompanhamento: "
                     "uma falta em produtos da Classe A afeta diretamente o faturamento.")
            if resumo.produtos == 1 and produtos:
                texto += f" Toda a classe depende de um único produto ({_lista_nomes(produtos, 1)})."
            cartao["recomendacao"] = texto
        elif letra == "B":
            texto = ("São itens com saída consistente: mais exposição e venda combinada com produtos da "
                     "Classe A podem ampliar sua participação.")
            if produtos:
                texto += f" Comece por {_lista_nomes(produtos, 2)}."
            cartao["recomendacao"] = texto
        else:
            reduzida = (resumo.percentual is not None and resumo.percentual <= CLASSE_C_PARTICIPACAO_MAX
                        and resumo.percentual_mix is not None and resumo.percentual_mix >= CLASSE_C_MIX_MIN)
            cartao["recomendacao"] = (
                "Revise a reposição (preferencialmente conforme a demanda), a exposição e a permanência no mix "
                "dos itens de menor saída, liberando espaço e capital para as classes A e B."
                if reduzida else
                "Acompanhe a reposição desses itens de acordo com a demanda observada.")
        cartoes.append(cartao)
    return cartoes


# =====================================================================
# 3) Movimentação por produto (unidades compradas x vendidas)
# =====================================================================
def interpretar_movimento(p: Produto) -> dict:
    """Interpretação e recomendação de UMA linha de movimentação.

    Nunca afirma estoque físico: a diferença é entre quantidades informadas nos
    relatórios do período, e só é calculada quando unidades e correspondência
    entre os relatórios permitem a comparação."""
    situacao = p.situacao
    if situacao == "SEM_VENDA_CORRESPONDENTE":
        return {"nivel": "informativo",
                "interpretacao": "Comprado no período, sem venda correspondente no relatório de vendas.",
                "recomendacao": "Confirme se o item foi vendido com outra descrição ou se não houve venda "
                                "antes de decidir a próxima compra."}
    if situacao == "UNIDADE_DIVERGENTE":
        return {"nivel": "informativo",
                "interpretacao": f"Unidades diferentes nos relatórios ({p.unidade_compra or '?'} na compra, "
                                 f"{p.unidade_venda or '?'} na venda): diferença não calculada.",
                "recomendacao": "Confira a conversão entre as unidades antes de comparar compra e venda."}
    if situacao == "UNIDADE_AMBIGUA":
        return {"nivel": "informativo",
                "interpretacao": "Unidade de medida ausente em um dos relatórios ou registrada de mais de uma "
                                 "forma: diferença não calculada.",
                "recomendacao": "Informe uma única unidade para o item nos dois relatórios para permitir a "
                                "comparação."}
    if situacao == "QUANTIDADE_INVALIDA":
        return {"nivel": "informativo",
                "interpretacao": "Quantidade zerada ou negativa em um dos relatórios: diferença não calculada.",
                "recomendacao": "Revise os lançamentos do item no sistema de vendas ou de compras."}
    comprada, vendida = dec(p.quantidade_comprada), dec(p.quantidade_vendida)
    if situacao != "COMPARAVEL" or comprada is None or vendida is None or comprada <= 0:
        return {"nivel": "informativo", "interpretacao": "Dados insuficientes para comparar compra e venda.",
                "recomendacao": ""}
    saida = vendida / comprada
    if saida < SAIDA_BAIXA:
        return {"nivel": "atencao", "saida": saida,
                "interpretacao": "Saída abaixo da metade do volume comprado no período.",
                "recomendacao": "Revisar a quantidade da próxima compra e considerar ações para estimular a "
                                "saída (exposição, combo ou campanha)."}
    if saida < SAIDA_ABAIXO:
        return {"nivel": "atencao", "saida": saida,
                "interpretacao": "Compras acima das vendas do período.",
                "recomendacao": "Ajustar a próxima reposição ao ritmo de vendas observado."}
    if saida <= SAIDA_ACIMA:
        return {"nivel": "oportunidade", "saida": saida,
                "interpretacao": "Compras alinhadas às vendas do período.",
                "recomendacao": "Manter a cadência de reposição."}
    return {"nivel": "oportunidade", "saida": saida,
            "interpretacao": "Vendas acima das compras do período (as vendas podem ter usado estoque anterior).",
            "recomendacao": "Verificar a reposição para evitar falta do produto."}


def linha_movimentacao(p: Produto) -> dict:
    """Linha exibível da movimentação. Cada quantidade leva só a unidade do seu
    próprio relatório; a diferença, só a unidade comum aos dois (nenhuma é
    presumida quando um dos relatórios não a informa)."""
    leitura = interpretar_movimento(p)
    un_compra, un_venda = unidade_exibivel(p.unidade_compra), unidade_exibivel(p.unidade_venda)
    return {
        "nome": p.nome, "chave": p.chave, "posicao": p.posicao, "classe": p.classe,
        "comprado": dec(p.quantidade_comprada), "vendido": dec(p.quantidade_vendida),
        "diferenca": dec(p.diferenca) if p.situacao == "COMPARAVEL" else None,
        "unidade_compra": un_compra, "unidade_venda": un_venda,
        "unidade": un_compra if un_compra and un_compra == un_venda else None,
        "situacao": p.situacao, **leitura,
    }


def _totais_situacao(complemento) -> Optional[dict]:
    """Totais por situação sobre TODOS os produtos comprados, quando gravados."""
    if getattr(complemento, "movimentacao_comparaveis", None) is None:
        return None
    return {"COMPARAVEL": complemento.movimentacao_comparaveis,
            "SEM_VENDA_CORRESPONDENTE": complemento.movimentacao_sem_venda,
            "UNIDADE_DIVERGENTE": complemento.movimentacao_unidade_divergente,
            "UNIDADE_AMBIGUA": complemento.movimentacao_unidade_ambigua,
            "QUANTIDADE_INVALIDA": complemento.movimentacao_quantidade_invalida}


def resumo_movimentacao(complemento, indicador, topo: list, contagem: dict,
                        periodos_divergentes: bool = False, acima: Optional[list] = None,
                        compras_autorizadas: bool = True) -> dict:
    """Estado da seção Movimentação dos produtos, fiel ao dado disponível.

    `topo` são as primeiras linhas da movimentação (maiores diferenças);
    `acima`, quando informado, são as primeiras linhas comparáveis com saída
    abaixo de SAIDA_ABAIXO em todo o registro (consulta própria), usadas pelas
    recomendações. As contagens usam os totais por situação de TODOS os
    produtos comprados quando gravados (senão, os registrados); um registro
    limitado é sempre declarado. Sem `compras_autorizadas` (período de compras
    fora da cobertura contratada) nada de compras por produto é exibido."""
    if complemento is None:
        legado = None
        if indicador is not None and indicador.produto_maior_saldo_parado_nome and \
                (dec(indicador.saldo_estimado_parado) or ZERO) > 0:
            legado = {"nome": indicador.produto_maior_saldo_parado_nome,
                      "diferenca": dec(indicador.saldo_estimado_parado)}
        return {"disponivel": False, "motivo": "analise_sem_detalhamento", "legado": legado,
                "linhas": [], "contagem": {}, "ressalvas": [], "destaque": None, "total_comparaveis": 0}
    if not complemento.compras_por_produto:
        return {"disponivel": False, "motivo": "compras_sem_produto", "legado": None, "linhas": [],
                "contagem": {}, "ressalvas": [], "destaque": None, "total_comparaveis": 0}
    if not compras_autorizadas:
        return {"disponivel": False, "motivo": "compras_fora_da_cobertura", "legado": None, "linhas": [],
                "contagem": {}, "ressalvas": [], "destaque": None, "total_comparaveis": 0}
    linhas = [linha_movimentacao(p) for p in topo]
    totais = _totais_situacao(complemento)
    contagem_completa = totais is not None
    contagem = totais if contagem_completa else contagem
    comparaveis = int(contagem.get("COMPARAVEL", 0))
    destaque = next((ln for ln in linhas if ln["situacao"] == "COMPARAVEL" and (ln["diferenca"] or ZERO) > 0), None)
    registrados = int(getattr(complemento, "movimentacao_registrada", 0) or 0)
    universo = int(getattr(complemento, "movimentacao_total", 0) or 0)
    parcial = registrados < universo
    ressalvas = []
    if parcial:
        ressalvas.append(f"A comparação por produto foi registrada para {fmt_quantidade(registrados)} de "
                         f"{fmt_quantidade(universo)} produtos comprados (limite operacional desta análise): "
                         + ("os totais por situação consideram todos os produtos; os filtros e a consulta "
                            "abaixo mostram apenas os registrados." if contagem_completa else
                            "as contagens, os filtros e a consulta abaixo consideram apenas os registrados."))
    if not (complemento.unidade_vendas_informada and complemento.unidade_compras_informada):
        ressalvas.append("Os relatórios não informam a unidade de medida em ambos os arquivos: a comparação "
                         "considera as quantidades como registradas em cada relatório.")
    if periodos_divergentes:
        ressalvas.append("Os relatórios de compras e de vendas declaram períodos diferentes; leia a comparação "
                         "por produto com cautela.")
    if contagem.get("SEM_VENDA_CORRESPONDENTE"):
        ressalvas.append(f"{contagem['SEM_VENDA_CORRESPONDENTE']} produto(s) comprado(s) não têm venda "
                         "correspondente pela descrição e ficaram fora do cálculo da diferença.")
    divergentes = int(contagem.get("UNIDADE_DIVERGENTE", 0)) + int(contagem.get("UNIDADE_AMBIGUA", 0))
    if divergentes:
        ressalvas.append(f"{divergentes} produto(s) com unidade diferente, ausente ou registrada de mais de uma "
                         "forma não foram comparados.")
    if contagem.get("QUANTIDADE_INVALIDA"):
        ressalvas.append(f"{contagem['QUANTIDADE_INVALIDA']} produto(s) com quantidade inválida não foram comparados.")
    return {"disponivel": True, "motivo": None, "legado": None, "linhas": linhas, "contagem": dict(contagem),
            "ressalvas": ressalvas, "destaque": destaque, "total_comparaveis": comparaveis,
            "periodos_divergentes": periodos_divergentes, "parcial": parcial,
            "registrados": registrados, "universo": universo, "contagem_completa": contagem_completa,
            "acima": None if acima is None else [linha_movimentacao(p) for p in acima]}


# =====================================================================
# 4) Variação de faturamento por produto entre períodos comparáveis
# =====================================================================
def variacoes_produtos(atuais: list, anteriores: dict, anterior_completo: bool,
                       faturamento_total, dias_atual: Optional[int] = None,
                       dias_anterior: Optional[int] = None) -> list:
    """Produtos cujo faturamento mudou de forma relevante em relação ao período
    anterior comparável.

    `anteriores` mapeia chave normalizada -> faturamento no período anterior.
    Produto ausente do período anterior só conta como zero quando aquele
    ranking estava completo; caso contrário é desconhecido e ignorado.
    Exige variação >= VARIACAO_PRODUTO_RELEVANTE e impacto >= IMPACTO_PRODUTO_MINIMO
    do faturamento total do período atual. Com durações diferentes, a
    comparação usa a média diária (o anterior é ajustado à duração atual)."""
    total = dec(faturamento_total)
    if not total or total <= 0:
        return []
    por_dia = bool(dias_atual and dias_anterior and dias_atual > 0 and dias_anterior > 0
                   and dias_atual != dias_anterior)
    fator = Decimal(dias_atual) / Decimal(dias_anterior) if por_dia else Decimal(1)
    resultado = []
    for p in atuais:
        atual = dec(p.faturamento)
        if atual is None or not p.chave:
            continue
        # Ausente do período anterior: com ranking anterior completo é produto novo
        # (sem base percentual); com ranking parcial é desconhecido. Nos dois casos
        # não há variação afirmável, e o produto fica fora.
        anterior = dec(anteriores.get(p.chave)) if p.chave in anteriores else None
        if anterior is None or anterior <= 0:
            continue
        ajustado = anterior * fator
        var = variacao(atual, ajustado)
        if var is None or var["percentual"] is None:
            continue
        impacto = abs(atual - ajustado) / total * CEM
        if abs(var["percentual"]) >= VARIACAO_PRODUTO_RELEVANTE and impacto >= IMPACTO_PRODUTO_MINIMO:
            resultado.append({"produto": p, "atual": moeda(atual), "anterior": moeda(anterior),
                              "variacao": var, "impacto": impacto.quantize(UM_DECIMO, rounding=ROUND_HALF_UP),
                              "por_dia": por_dia, "dias_atual": dias_atual, "dias_anterior": dias_anterior,
                              "_peso": abs(atual - ajustado)})
    resultado.sort(key=lambda r: r["_peso"], reverse=True)
    for item in resultado:
        item.pop("_peso")
    return resultado


# =====================================================================
# 5) Contexto consolidado e insights
# =====================================================================
@dataclass
class ContextoPainel:
    """Tudo o que as regras de interpretação podem usar, já carregado e limitado."""
    analise: Any
    indicador: Any
    complemento: Any = None
    lider: Optional[Produto] = None
    mais_vendido: Optional[Produto] = None
    distribuicao: Optional[DistribuicaoABC] = None
    destaques_classe: dict = field(default_factory=dict)
    movimentacao: Optional[dict] = None
    serie: Optional[SerieHistorica] = None
    variacoes_produto: list = field(default_factory=list)

    @property
    def faturamento(self) -> Optional[Decimal]:
        return dec(self.indicador.faturamento_total) if self.indicador is not None else None

    @property
    def compras(self) -> Optional[Decimal]:
        return dec(self.indicador.total_comprado) if self.indicador is not None else None

    @property
    def diferenca(self) -> Optional[Decimal]:
        """Compras − vendas: o Indicador de Pressão de Estoque persistido pelo ETL."""
        if self.indicador is None:
            return None
        persistido = dec(self.indicador.saldo_estimado_compras_vendas)
        if persistido is not None:
            return persistido
        if self.compras is not None and self.faturamento is not None:
            return self.compras - self.faturamento
        return None

    @property
    def razao_pressao(self) -> Optional[Decimal]:
        """Diferença ÷ faturamento, arredondada como é exibida (percentual com uma
        casa): o selo e os textos nunca discordam do número mostrado (5,04% é 5,0%)."""
        if self.diferenca is None or not self.faturamento or self.faturamento <= 0:
            return None
        pct = percentual(self.diferenca, self.faturamento, 1)
        return None if pct is None else pct / CEM

    @property
    def comparacao_faturamento(self) -> Optional[dict]:
        if self.serie is None:
            return None
        return comparacao_periodos(self.serie.atual, self.serie.anterior)

    @property
    def variacao_faturamento(self) -> Optional[dict]:
        """Variação dos totais (exibição). As regras usam comparacao_faturamento."""
        comp = self.comparacao_faturamento
        return comp["bruta"] if comp else None


def nivel_pressao(razao, diferenca=None) -> str:
    """'pressao', 'giro' ou 'equilibrio' pela faixa de ±5% do faturamento (o limiar
    de 5% é o dos semáforos; a faixa negativa e o equilíbrio são da Visão Geral).
    Sem faturamento, vale só o sinal da diferença; sem diferença conhecida,
    'indisponivel' (dado ausente não é equilíbrio)."""
    razao = dec(razao)
    if razao is not None:
        if razao > PRESSAO_ATENCAO_DEC:
            return "pressao"
        if razao < -PRESSAO_ATENCAO_DEC:
            return "giro"
        return "equilibrio"
    dif = dec(diferenca)
    if dif is None:
        return "indisponivel"
    if dif == 0:
        return "equilibrio"
    return "pressao" if dif > 0 else "giro"


def _insight(chave, nivel, titulo, o_que, por_que, o_que_fazer, objetivo, rastreio, produto=None) -> dict:
    return {"chave": chave, "nivel": nivel, "titulo": titulo, "o_que": o_que, "por_que": por_que,
            "o_que_fazer": o_que_fazer, "objetivo": objetivo, "produto": produto, "rastreio": rastreio}


def _linha_acima(ln: dict) -> bool:
    """Linha comparável em que se comprou mais do que se vendeu (saída < 90%)."""
    return (ln["situacao"] == "COMPARAVEL" and (ln["diferenca"] or ZERO) > 0
            and ln.get("saida") is not None and ln["saida"] < SAIDA_ABAIXO)


def _movimento_verificavel(ctx: ContextoPainel) -> bool:
    mov = ctx.movimentacao or {}
    return bool(mov.get("disponivel")) and not mov.get("periodos_divergentes")


def _movimento_incerto(ctx: ContextoPainel) -> bool:
    """Movimentação exibida, mas com relatórios de períodos diferentes: as ações
    por produto ficam neutras (sem "garantir reposição") para não contrariar a
    leitura de cada linha da tabela."""
    mov = ctx.movimentacao or {}
    return bool(mov.get("disponivel")) and bool(mov.get("periodos_divergentes"))


def _produtos_compras_acima(ctx: ContextoPainel) -> list:
    """Linhas comparáveis com compras acima das vendas. Usa a consulta própria
    (`acima`, sobre todo o registro) quando existe; senão, as primeiras linhas."""
    if not _movimento_verificavel(ctx):
        return []
    mov = ctx.movimentacao
    fonte = mov.get("acima")
    if fonte is None:
        fonte = mov.get("linhas", [])
    return [ln for ln in fonte if _linha_acima(ln)]


def _tem_compras_acima(ctx: ContextoPainel, produto: Optional[Produto]) -> bool:
    """True quando o PRÓPRIO dado do produto mostra compras acima das vendas.

    Produtos do detalhamento trazem a sua linha de movimentação completa; por
    isso a verificação não depende de o item estar entre as primeiras linhas.
    Sem detalhamento (ou com períodos divergentes) nada é afirmado: False."""
    if produto is None or not _movimento_verificavel(ctx):
        return False
    for ln in _produtos_compras_acima(ctx):
        if (produto.chave and ln.get("chave") == produto.chave) or ln["nome"] == produto.nome:
            return True
    return produto.situacao == "COMPARAVEL" and _linha_acima(linha_movimentacao(produto))


def gerar_insights(ctx: ContextoPainel) -> list:
    """Cartões de interpretação gerencial; cada um só existe se sua condição
    verificável for satisfeita (ver `rastreio`)."""
    if ctx.indicador is None:
        return []
    cards = []
    nomes_classe_a = {p.nome for p in (ctx.destaques_classe.get("A") or [])}

    # 1. Compras x vendas no período (mesmos limiares dos semáforos).
    razao = ctx.razao_pressao
    if razao is not None:
        dif = ctx.diferenca
        pct = (razao * CEM).quantize(UM_DECIMO, rounding=ROUND_HALF_UP)
        rastreio = {"indicador": "saldo_estimado_compras_vendas / faturamento_total",
                    "valor": str(pct), "criterio": f"> {PRESSAO_ATENCAO_DEC * CEM}% atenção; "
                                                   f"> {PRESSAO_CRITICA_DEC * CEM}% crítico; < -{PRESSAO_ATENCAO_DEC * CEM}% vendas acima"}
        if razao > PRESSAO_ATENCAO_DEC:
            cards.append(_insight(
                "compras_superiores_vendas", "critico" if razao > PRESSAO_CRITICA_DEC else "atencao",
                "Compras acima das vendas",
                f"As compras ({fmt_moeda(ctx.compras)}) superaram o faturamento de vendas ({fmt_moeda(ctx.faturamento)}) "
                f"em {fmt_moeda(dif)}, o equivalente a {fmt_percentual(pct)} do faturamento.",
                "Comprar mais do que se vende no período compromete capital de giro com mercadorias que ainda "
                "precisam ser vendidas. Isso não indica, sozinho, estoque físico parado: parte das compras pode "
                "atender períodos seguintes.",
                "Planejar o próximo pedido com base no ritmo de vendas observado e priorizar a saída dos itens com "
                "maior diferença entre compra e venda (seção Movimentação dos produtos).",
                "Equilibrar compras e vendas e preservar o capital de giro.", rastreio))
        elif razao < -PRESSAO_ATENCAO_DEC:
            cards.append(_insight(
                "vendas_superiores_compras", "oportunidade", "Vendas acima das compras",
                f"O faturamento de vendas ({fmt_moeda(ctx.faturamento)}) superou as compras ({fmt_moeda(ctx.compras)}) "
                f"em {fmt_moeda(abs(dif))}.",
                "As vendas do período podem ter utilizado mercadorias compradas anteriormente; manter a reposição "
                "em dia evita a falta dos produtos de maior saída.",
                "Verificar a reposição dos produtos de maior faturamento antes do próximo ciclo.",
                "Sustentar o ritmo de vendas sem falta de produtos.", rastreio))
        else:
            cards.append(_insight(
                "compras_vendas_equilibradas", "oportunidade", "Compras e vendas equilibradas",
                f"A diferença entre compras e vendas ficou em {fmt_moeda(dif)} ({fmt_percentual(pct)} do faturamento).",
                "Compras próximas do volume vendido indicam reposição alinhada à demanda do período.",
                "Manter a cadência atual de compras, acompanhando os produtos de maior saída.",
                "Preservar o equilíbrio entre reposição e vendas.", rastreio))

    # 2. Concentração em um único produto.
    lider = ctx.lider
    part = dec(lider.percentual_individual) if lider else None
    if lider and part is not None and part >= CONCENTRACAO_PRODUTO:
        if _tem_compras_acima(ctx, lider):
            acao = (f"Manter “{lider.nome}” abastecido na medida das vendas observadas (no período, as compras do "
                    "produto superaram as vendas) e desenvolver a venda de produtos complementares.")
        elif _movimento_incerto(ctx):
            acao = (f"Acompanhar o abastecimento de “{lider.nome}” pelas vendas observadas e desenvolver a venda de "
                    "produtos complementares.")
        else:
            acao = f"Garantir o abastecimento de “{lider.nome}” e desenvolver a venda de produtos complementares."
        cards.append(_insight(
            "concentracao_produto", "atencao", "Faturamento concentrado em um produto",
            f"“{lider.nome}” respondeu por {fmt_percentual(part)} do faturamento ({fmt_moeda(lider.faturamento)}).",
            "Dependência elevada de um único item aumenta o risco: uma falta, mudança de preço ou queda de "
            "demanda nesse produto afeta fortemente o faturamento.",
            acao,
            "Reduzir a dependência de um único produto.",
            {"indicador": "percentual_individual (posição 1)", "valor": str(part),
             "criterio": f">= {CONCENTRACAO_PRODUTO}%", "produto": lider.nome}, produto=lider.nome))

    # 3. Produto com baixa saída relativa (movimentação comparável).
    baixa = [ln for ln in _produtos_compras_acima(ctx) if ln["saida"] < SAIDA_BAIXA]
    if baixa:
        alvo = baixa[0]
        estrategico = alvo["nome"] in nomes_classe_a or alvo.get("classe") == "A"
        acao = (f"Ajustar a reposição de “{alvo['nome']}” ao ritmo de vendas observado, sem deixar faltar o "
                "produto, que é estratégico (Classe A)." if estrategico else
                f"Revisar a quantidade da próxima compra de “{alvo['nome']}” e, se fizer sentido, criar ações "
                "de exposição ou venda combinada.")
        saida_pct = (alvo["saida"] * CEM).quantize(UM_DECIMO, rounding=ROUND_HALF_UP)
        cards.append(_insight(
            "baixa_saida_relativa", "atencao", "Produto com saída abaixo do volume comprado",
            f"“{alvo['nome']}”: quantidade comprada {fmt_quantidade_unidade(alvo['comprado'], alvo.get('unidade_compra'))} e "
            f"vendida {fmt_quantidade_unidade(alvo['vendido'], alvo.get('unidade_venda'))} no período "
            f"(saída de {fmt_percentual(saida_pct)} do volume comprado).",
            "Volume comprado bem acima da saída pode indicar compra superdimensionada ou demanda abaixo do "
            "esperado. A diferença considera apenas as quantidades informadas nos relatórios do período.",
            acao, "Alinhar as compras à demanda real do produto.",
            {"indicador": "quantidade_vendida / quantidade_comprada", "valor": str(saida_pct),
             "criterio": f"< {SAIDA_BAIXA * CEM}% com unidades comparáveis", "produto": alvo["nome"]},
            produto=alvo["nome"]))

    # 4. Variação relevante do faturamento total. Com durações diferentes, a
    # relevância é medida pela média diária (o calendário não vira tendência).
    comp = ctx.comparacao_faturamento
    rel = comp["relevante"] if comp else None
    if rel and rel["percentual"] is not None and abs(rel["percentual"]) >= VARIACAO_TOTAL_RELEVANTE:
        ref = ctx.serie.anterior.rotulo
        bruta = comp["bruta"]
        alta = rel["direcao"] == "alta"
        o_que = (f"O faturamento variou {fmt_percentual(bruta['percentual'], sinal=True)} em relação a {ref} "
                 f"({fmt_moeda(ctx.serie.anterior.faturamento)} → {fmt_moeda(ctx.serie.atual.faturamento)}).")
        if comp["por_dia"]:
            o_que += " " + texto_media_diaria(comp)
        cards.append(_insight(
            "variacao_faturamento", "oportunidade" if alta else "atencao",
            "Faturamento em alta" if alta else "Faturamento em queda",
            o_que,
            "Variações dessa ordem entre períodos comparáveis mudam a necessidade de compra e de capital de giro.",
            ("Identificar os produtos que puxaram o crescimento e garantir sua reposição." if alta else
             "Verificar os produtos com maior redução e as possíveis causas (falta de produto, preço ou sazonalidade)."),
            "Sustentar o crescimento." if alta else "Recuperar o nível de vendas.",
            {"indicador": ("faturamento médio diário" if comp["por_dia"] else "faturamento_total")
                          + " vs período anterior comparável", "valor": str(rel["percentual"]),
             "criterio": f"|variação| >= {VARIACAO_TOTAL_RELEVANTE}% (média diária quando as durações diferem)",
             "referencia": ref, "dias": [comp["dias_atual"], comp["dias_anterior"]]}))

    # 5. Produtos com crescimento e com redução (períodos comparáveis).
    crescimentos = [v for v in ctx.variacoes_produto if v["variacao"]["direcao"] == "alta"]
    reducoes = [v for v in ctx.variacoes_produto if v["variacao"]["direcao"] == "queda"]
    for chave, lista, alta in (("crescimento_produto", crescimentos, True), ("reducao_produto", reducoes, False)):
        if not lista:
            continue
        item = lista[0]
        nome = item["produto"].nome
        ref = ctx.serie.anterior.rotulo if ctx.serie and ctx.serie.anterior else "o período anterior"
        o_que = (f"“{nome}” faturou {fmt_moeda(item['atual'])}, {fmt_percentual(item['variacao']['percentual'], sinal=True)} "
                 f"em relação a {ref} ({fmt_moeda(item['anterior'])})")
        if item.get("por_dia"):
            o_que += (f", comparando a média diária (períodos de {item['dias_atual']} e "
                      f"{item['dias_anterior']} dias)")
        # Crescimento com compras acima das vendas: ampliar a exposição sem
        # "garantir reposição" (o mesmo produto não recebe ações opostas).
        compras_acima = alta and _tem_compras_acima(ctx, item["produto"])
        if alta and compras_acima:
            acao = (f"Ampliar a exposição de “{nome}” e dimensionar a próxima compra pelas vendas observadas: no "
                    "período, as compras do produto superaram as vendas.")
        elif alta and _movimento_incerto(ctx):
            acao = f"Avaliar a reposição de “{nome}” pelas vendas observadas e ampliar sua exposição."
        elif alta:
            acao = f"Garantir a reposição de “{nome}” e avaliar ampliar sua exposição."
        else:
            acao = f"Investigar a causa da redução de “{nome}” antes do próximo pedido."
        card = _insight(
            chave, "oportunidade" if alta else "atencao",
            "Produto em crescimento" if alta else "Produto em queda",
            o_que + ".",
            ("O produto ganhou relevância e passa a exigir reposição compatível com a nova demanda." if alta else
             "A queda reduz o faturamento do período e pode indicar falta de produto, mudança de preço ou de demanda."),
            acao,
            "Aproveitar a demanda crescente." if alta else "Recuperar as vendas do produto.",
            {"indicador": "faturamento do produto vs período anterior comparável"
                          + (" (média diária)" if item.get("por_dia") else ""),
             "valor": str(item["variacao"]["percentual"]), "impacto_pct_faturamento": str(item["impacto"]),
             "criterio": f"|variação| >= {VARIACAO_PRODUTO_RELEVANTE}% e impacto >= {IMPACTO_PRODUTO_MINIMO}%",
             "produto": nome}, produto=nome)
        card["compras_acima"] = compras_acima
        cards.append(card)

    # 6. Classe B: oportunidade (distribuição completa).
    dist = ctx.distribuicao
    if dist and dist.disponivel:
        b = dist.classe("B")
        destaques_b = ctx.destaques_classe.get("B") or []
        if b and b.produtos and b.percentual is not None and b.percentual >= CLASSE_B_PARTICIPACAO_MIN and destaques_b:
            cards.append(_insight(
                "oportunidade_classe_b", "oportunidade", "Oportunidade na Classe B",
                f"{fmt_quantidade(b.produtos)} produto(s) da Classe B somam {fmt_percentual(b.percentual)} do faturamento; "
                f"os primeiros da classe são {_lista_nomes(destaques_b, 2)}.",
                "Esses itens já têm saída consistente: pequenos ganhos de venda neles têm impacto relevante e "
                "reduzem a dependência dos produtos da Classe A.",
                "Dar mais visibilidade aos primeiros itens da Classe B e combiná-los com produtos da Classe A.",
                "Ampliar o faturamento distribuindo melhor as vendas.",
                {"indicador": "participação da Classe B", "valor": str(b.percentual),
                 "criterio": f">= {CLASSE_B_PARTICIPACAO_MIN}% com produtos na classe"}))
        c = dist.classe("C")
        if (c and c.produtos and c.percentual is not None and c.percentual <= CLASSE_C_PARTICIPACAO_MAX
                and c.percentual_mix is not None and c.percentual_mix >= CLASSE_C_MIX_MIN):
            cards.append(_insight(
                "classe_c_participacao_reduzida", "informativo", "Classe C com participação reduzida",
                f"{fmt_quantidade(c.produtos)} produto(s) — {fmt_percentual(c.percentual_mix)} do mix — somam apenas "
                f"{fmt_percentual(c.percentual)} do faturamento.",
                "Itens de baixa participação ocupam espaço, capital e atenção da operação.",
                "Revisar exposição, reposição sob demanda e permanência no mix dos itens de menor saída.",
                "Racionalizar o mix e liberar capital para as classes A e B.",
                {"indicador": "participação e mix da Classe C", "valor": f"{c.percentual}% / {c.percentual_mix}%",
                 "criterio": f"participação <= {CLASSE_C_PARTICIPACAO_MAX}% e mix >= {CLASSE_C_MIX_MIN}%"}))

    cards.sort(key=lambda card: NIVEL_ORDEM.get(card["nivel"], 9))
    return cards


# =====================================================================
# 6) Recomendações para o próximo ciclo
# =====================================================================
def _recomendacao(prioridade, alvo, situacao, justificativa, acao, objetivo, rastreio) -> dict:
    return {"prioridade": prioridade, "alvo": alvo, "situacao": situacao, "justificativa": justificativa,
            "acao": acao, "objetivo": objetivo, "rastreio": rastreio}


def gerar_recomendacoes(ctx: ContextoPainel, insights: list) -> list:
    """Recomendações priorizadas, cada uma ligada a um indicador verificável.

    - Só entram recomendações com dado de suporte (nada de lista fixa).
    - Um produto não recebe ações contraditórias: itens com compras acima das
      vendas saem da recomendação da Classe A e recebem a de ajuste de reposição.
    - Sem promessa de resultado financeiro."""
    if ctx.indicador is None:
        return []
    recs = []
    chaves = {i["chave"] for i in insights}
    acima = _produtos_compras_acima(ctx)
    nomes_acima = {ln["nome"] for ln in acima}

    if acima:
        alvo = acima[:3]
        nomes = ", ".join(f"“{ln['nome']}” ({fmt_quantidade_unidade(ln['diferenca'], ln.get('unidade'), sinal=True)})"
                          for ln in alvo)
        alta = any(ln["saida"] < SAIDA_BAIXA for ln in alvo) or "compras_superiores_vendas" in chaves
        recs.append(_recomendacao(
            "Alta" if alta else "Média", "Produtos com compras superiores às vendas",
            f"No período, estes itens tiveram quantidade comprada maior que a vendida: {nomes}.",
            "A diferença foi calculada apenas para produtos com correspondência entre os relatórios e unidades "
            "comparáveis; ela não representa, sozinha, estoque físico.",
            "Revisar as quantidades do próximo pedido desses itens e estimular sua saída antes de nova compra.",
            "Alinhar compras ao ritmo de vendas e preservar o capital de giro.",
            {"indicador": "diferenca_quantidade (comprada − vendida)", "produtos": [ln["nome"] for ln in alvo],
             "criterio": f"situação COMPARAVEL e saída < {SAIDA_ABAIXO * CEM}%"}))
    elif "compras_superiores_vendas" in chaves:
        insight = next(i for i in insights if i["chave"] == "compras_superiores_vendas")
        recs.append(_recomendacao(
            "Alta" if insight["nivel"] == "critico" else "Média", "Compras do próximo ciclo",
            insight["o_que"], insight["por_que"],
            "Planejar o próximo pedido a partir do faturamento observado, priorizando os produtos de maior saída.",
            insight["objetivo"], insight["rastreio"]))

    reducao = next((i for i in insights if i["chave"] == "reducao_produto"), None)
    if reducao:
        recs.append(_recomendacao(
            "Alta", f"“{reducao['produto']}”", reducao["o_que"], reducao["por_que"], reducao["o_que_fazer"],
            reducao["objetivo"], reducao["rastreio"]))

    # Classe A: cada destaque é conferido pela SUA linha de movimentação (não
    # só pelas primeiras linhas da seção), para não afirmar "sem sinal" de um
    # item que comprou acima do que vendeu.
    destaques_a = ctx.destaques_classe.get("A") or []
    com_sinal = [p for p in destaques_a if p.nome in nomes_acima or _tem_compras_acima(ctx, p)]
    estrategicos = [p for p in destaques_a if p not in com_sinal]
    if estrategicos:
        dist = ctx.distribuicao
        a = dist.classe("A") if dist and dist.disponivel else None
        participacao = (f" A Classe A soma {fmt_percentual(a.percentual)} do faturamento com "
                        f"{fmt_quantidade(a.produtos)} produto(s)." if a and a.percentual is not None else "")
        concentrado = "concentracao_produto" in chaves
        abertura = f"Os produtos de maior faturamento são {_lista_nomes(estrategicos, 3)}."
        if com_sinal:
            # Mesmo critério da recomendação de compras acima das vendas (saída < 90%).
            abertura += (f" {_lista_nomes(com_sinal, 3)} " + ("fica" if len(com_sinal) == 1 else "ficam")
                         + " fora desta ação: " + ("vendeu" if len(com_sinal) == 1 else "venderam")
                         + " menos de 90% do volume comprado no período.")
        recs.append(_recomendacao(
            "Alta" if concentrado else "Média", "Produtos estratégicos (Classe A)",
            abertura + participacao,
            "Uma falta ou mudança de preço nesses itens tem o maior efeito sobre o faturamento do período.",
            "Acompanhar disponibilidade, preço e exposição desses produtos a cada ciclo de compra.",
            "Proteger a principal fonte de faturamento.",
            {"indicador": "classe_abc = A (maiores faturamentos)", "produtos": [p.nome for p in estrategicos[:3]],
             "criterio": "Classe A, exceto produtos com saída abaixo de 90% do volume comprado"}))

    if "oportunidade_classe_b" in chaves:
        insight = next(i for i in insights if i["chave"] == "oportunidade_classe_b")
        recs.append(_recomendacao(
            "Média", "Produtos intermediários (Classe B)", insight["o_que"], insight["por_que"],
            insight["o_que_fazer"], insight["objetivo"], insight["rastreio"]))

    crescimento = next((i for i in insights if i["chave"] == "crescimento_produto"), None)
    if crescimento and not crescimento.get("compras_acima") and crescimento["produto"] not in nomes_acima:
        recs.append(_recomendacao(
            "Média", f"“{crescimento['produto']}”", crescimento["o_que"], crescimento["por_que"],
            crescimento["o_que_fazer"], crescimento["objetivo"], crescimento["rastreio"]))

    if "classe_c_participacao_reduzida" in chaves:
        insight = next(i for i in insights if i["chave"] == "classe_c_participacao_reduzida")
        recs.append(_recomendacao(
            "Baixa", "Produtos complementares (Classe C)", insight["o_que"], insight["por_que"],
            insight["o_que_fazer"], insight["objetivo"], insight["rastreio"]))

    vistos, unicos = set(), []
    for rec in recs:
        if rec["alvo"] in vistos:
            continue
        vistos.add(rec["alvo"])
        unicos.append(rec)
    unicos.sort(key=lambda r: PRIORIDADE_ORDEM.get(r["prioridade"], 9))
    return unicos[:5]


# =====================================================================
# 7) Resumo executivo (complementar à devolutiva publicada)
# =====================================================================
def gerar_resumo_executivo(ctx: ContextoPainel, insights: list, recomendacoes: list,
                           periodo_texto: str) -> list:
    """Destaques objetivos do período, montados só com indicadores disponíveis.

    Complementa (não substitui) o resumo executivo publicado pela equipe NEXO,
    que o painel exibe antes destes destaques quando existe."""
    if ctx.indicador is None or ctx.faturamento is None:
        return []
    frases = []
    comp = ctx.comparacao_faturamento
    abertura = f"No período de {periodo_texto}, o faturamento foi de {fmt_moeda(ctx.faturamento)}"
    if comp and ctx.serie and ctx.serie.anterior:
        abertura += f" ({_texto_variacao(comp['bruta'], ctx.serie.anterior.rotulo)})"
    if ctx.compras is not None:
        abertura += f" e as compras somaram {fmt_moeda(ctx.compras)}"
    frases.append(abertura + ".")
    if texto_media_diaria(comp):
        frases.append(texto_media_diaria(comp))

    dif = ctx.diferenca
    razao = ctx.razao_pressao
    if dif is not None and razao is not None:
        if razao > PRESSAO_ATENCAO_DEC:
            frases.append(f"As compras superaram as vendas em {fmt_moeda(dif)} "
                          f"({fmt_percentual(razao * CEM)} do faturamento).")
        elif razao < -PRESSAO_ATENCAO_DEC:
            frases.append(f"As vendas superaram as compras em {fmt_moeda(abs(dif))}.")
        else:
            frases.append("Compras e vendas ficaram equilibradas no período.")

    lider, mais = ctx.lider, ctx.mais_vendido
    if lider is not None:
        texto = (f"O produto de maior faturamento foi “{lider.nome}” ({fmt_moeda(lider.faturamento)}"
                 + (f", {fmt_percentual(lider.percentual_individual)} do total" if lider.percentual_individual is not None else "")
                 + ")")
        if mais is not None and mais.nome == lider.nome:
            texto += ", que também liderou em quantidade vendida"
        frases.append(texto + ".")
    if mais is not None and (lider is None or mais.nome != lider.nome):
        frases.append(f"Em quantidade vendida, o destaque foi “{mais.nome}” "
                      f"({fmt_quantidade_unidade(mais.quantidade_vendida, mais.unidade_venda)}).")

    dist = ctx.distribuicao
    if dist and dist.disponivel:
        a = dist.classe("A")
        if a and a.produtos:
            frases.append(f"{fmt_quantidade(a.produtos)} produto(s) da Classe A concentram "
                          f"{fmt_percentual(a.percentual)} do faturamento.")

    atencao = next((i for i in insights if i["nivel"] in ("critico", "atencao")
                    and i["chave"] not in ("compras_superiores_vendas",)), None)
    if atencao:
        frases.append(f"Ponto de atenção: {atencao['o_que']}")
    oportunidade = next((i for i in insights if i["nivel"] == "oportunidade"
                         and i["chave"] not in ("compras_vendas_equilibradas", "vendas_superiores_compras")), None)
    if oportunidade:
        frases.append(f"Oportunidade: {oportunidade['o_que']}")
    if recomendacoes:
        frases.append(f"Prioridade para o próximo ciclo: {recomendacoes[0]['acao']}")
    return frases
