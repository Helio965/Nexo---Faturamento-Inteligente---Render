"""
NEXO - Detalhamento por produto de uma análise (leitura e disponibilidade)
=========================================================================
Acesso às tabelas da revisão 5a9c3e7d1b42 (indicador_complementar_analise e
produto_desempenho_analise), gravadas pelo ETL na operação "calculate_detailed".

Implantação expand -> migrate -> deploy, como as Configurações e os Planos:
antes da migração o portal segue igual (a Visão Geral usa o top-20 de
produto_curva_abc e declara o que não está disponível) e o ETL não grava o
detalhamento. Todas as consultas aqui são LIMITADAS (topo, destaques por
classe e páginas de tamanho fixo): nenhuma rota carrega milhares de linhas.

Este módulo roda só no processo web; o worker do ETL não o importa.
"""

from __future__ import annotations

import logging
import time
from weakref import WeakKeyDictionary

from sqlalchemy import func, inspect, select

from contract_policy import periodo_coberto
from etl_processor import _normalizar_produto, chave_produto
from extensions import db
from inteligencia_comercial import LIMITE_RANKING_LEGADO, SAIDA_ABAIXO, Produto, dec
from models import IndicadorComplementarAnalise, ProdutoCurvaABC, ProdutoDesempenhoAnalise

logger = logging.getLogger(__name__)

REVISAO_DETALHAMENTO = "5a9c3e7d1b42"
TABELAS_DETALHAMENTO = ("indicador_complementar_analise", "produto_desempenho_analise")
_REVERIFICAR_ESQUEMA_SEGUNDOS = 30.0
_esquema_por_engine: "WeakKeyDictionary" = WeakKeyDictionary()

# Consulta paginada da Visão Geral.
ITENS_POR_PAGINA = 25
LIMITE_BUSCA = 80
VISOES = ("ranking", "movimentacao")
FILTROS_MOVIMENTACAO = {
    "acima": "Compras acima das vendas",
    "comparaveis": "Todos comparáveis",
    "sem_correspondencia": "Sem venda correspondente",
    "unidades": "Unidade diferente ou ausente",
    "invalidas": "Quantidade inválida",
    "todas": "Todos os comprados",
}


def esquema_detalhamento_disponivel(sessao=None) -> bool:
    """True quando as duas tabelas da revisão 5a9c3e7d1b42 existem neste banco.

    Confirmada a presença, o resultado fica fixo para o engine; a ausência é
    reavaliada a cada 30 s, para a migração aplicada valer sem reiniciar o
    processo. Esquema parcial conta como ausente (falha fechada) e é registrado."""
    sessao = sessao or db.session
    engine = sessao.get_bind()
    estado = _esquema_por_engine.get(engine)
    if estado is True:
        return True
    if estado is not None and time.monotonic() - estado < _REVERIFICAR_ESQUEMA_SEGUNDOS:
        return False
    # A conexão da própria sessão: sem segunda conexão nem reset de pool.
    inspetor = inspect(sessao.connection())
    presentes = {tabela for tabela in TABELAS_DETALHAMENTO if inspetor.has_table(tabela)}
    if presentes == set(TABELAS_DETALHAMENTO):
        _esquema_por_engine[engine] = True
        return True
    if presentes:
        logger.warning("Esquema do detalhamento por produto parcial: confira a migração %s.", REVISAO_DETALHAMENTO)
    _esquema_por_engine[engine] = time.monotonic()
    return False


def esquecer_esquema_detalhamento(sessao=None) -> None:
    """Uma consulta às tabelas falhou (ex.: downgrade com o processo no ar): a
    próxima verificação confere o banco de novo."""
    _esquema_por_engine.pop((sessao or db.session).get_bind(), None)


# =====================================================================
# Conversão das linhas persistidas para a estrutura das regras
# =====================================================================
def produto_de_detalhe(linha: ProdutoDesempenhoAnalise) -> Produto:
    return Produto(
        nome=linha.produto_nome, chave=linha.produto_chave, posicao=linha.posicao_ranking,
        classe=linha.classe_abc, faturamento=dec(linha.faturamento),
        quantidade_vendida=dec(linha.quantidade_vendida),
        percentual_individual=dec(linha.percentual_individual),
        percentual_acumulado=dec(linha.percentual_acumulado),
        quantidade_comprada=dec(linha.quantidade_comprada), situacao=linha.situacao_movimentacao,
        diferenca=dec(linha.diferenca_quantidade), unidade_venda=linha.unidade_venda,
        unidade_compra=linha.unidade_compra,
    )


def produto_de_curva(linha: ProdutoCurvaABC) -> Produto:
    """Linha do top-20 legado. A chave é derivada do nome exibido com a mesma
    normalização do ETL (nomes acima de 200 caracteres podem não casar: nesse
    caso o produto simplesmente não entra na comparação entre períodos)."""
    return Produto(
        nome=linha.produto_nome, chave=chave_produto(_normalizar_produto(linha.produto_nome)),
        posicao=linha.posicao_ranking, classe=linha.classe_abc, faturamento=dec(linha.faturamento),
        quantidade_vendida=dec(linha.quantidade),
        percentual_individual=dec(linha.percentual_individual),
        percentual_acumulado=dec(linha.percentual_acumulado),
    )


# =====================================================================
# Consultas limitadas usadas pela Visão Geral
# =====================================================================
def complemento_da_analise(id_analise: int, sessao=None):
    """IndicadorComplementarAnalise da análise, ou None (sem migração ou análise
    processada antes do detalhamento). Use complemento_vigente para exibir."""
    sessao = sessao or db.session
    if not esquema_detalhamento_disponivel(sessao):
        return None
    return sessao.execute(
        select(IndicadorComplementarAnalise).where(IndicadorComplementarAnalise.id_analise == id_analise)
    ).scalar_one_or_none()


def complemento_vigente(analise, sessao=None):
    """Detalhamento gravado no MESMO processamento dos KPIs atuais da análise.

    Um detalhamento de outra versão de indicador_analise (sobra de um
    reprocessamento cuja gravação do detalhamento falhou, ou feito por outra
    versão do sistema) é ignorado: a análise aparece como sem detalhamento, em
    vez de misturar arquivos antigos aos indicadores atuais."""
    indicador = getattr(analise, "indicador", None)
    if analise is None or indicador is None:
        return None
    complemento = complemento_da_analise(analise.id_analise, sessao)
    if complemento is not None and complemento.versao_processamento != indicador.versao_processamento:
        logger.warning("Detalhamento por produto de outro processamento ignorado (análise %s).", analise.id_analise)
        return None
    return complemento


def movimentacao_autorizada(situacao, complemento) -> bool:
    """Compras por produto só são exibidas se o período do RELATÓRIO DE COMPRAS
    estiver coberto, no regime contratual. O período de vendas já integra a
    autorização da análise (indicador.periodo_base); o de compras não, e um
    relatório de compras mais amplo que a cobertura paga não pode expor, produto
    a produto, compras de meses não contratados. Sem período no cabeçalho, vale
    o período declarado (já autorizado)."""
    if complemento is None or situacao is None or not getattr(situacao, "contratual", False):
        return True
    inicio, fim = complemento.periodo_compras_inicio, complemento.periodo_compras_fim
    if inicio is None or fim is None:
        return True
    return periodo_coberto(inicio, fim, situacao.intervalos_pagos)


def ranking_topo(id_analise: int, limite: int, registrado: int, sessao=None) -> list:
    sessao = sessao or db.session
    teto = min(int(limite), int(registrado))
    if teto <= 0:
        return []
    linhas = sessao.execute(
        select(ProdutoDesempenhoAnalise)
        .where(ProdutoDesempenhoAnalise.id_analise == id_analise,
               ProdutoDesempenhoAnalise.posicao_ranking.is_not(None),
               ProdutoDesempenhoAnalise.posicao_ranking <= teto)
        .order_by(ProdutoDesempenhoAnalise.posicao_ranking)
    ).scalars().all()
    return [produto_de_detalhe(linha) for linha in linhas]


def destaques_por_classe(id_analise: int, registrado: int, limite: int = 3, sessao=None) -> dict:
    """Os `limite` primeiros de cada classe dentro do prefixo registrado do ranking."""
    sessao = sessao or db.session
    destaques = {}
    for classe in ("A", "B", "C"):
        linhas = sessao.execute(
            select(ProdutoDesempenhoAnalise)
            .where(ProdutoDesempenhoAnalise.id_analise == id_analise,
                   ProdutoDesempenhoAnalise.classe_abc == classe,
                   ProdutoDesempenhoAnalise.posicao_ranking <= int(registrado))
            .order_by(ProdutoDesempenhoAnalise.posicao_ranking)
            .limit(limite)
        ).scalars().all()
        destaques[classe] = [produto_de_detalhe(linha) for linha in linhas]
    return destaques


def movimentacao_topo(id_analise: int, limite: int, registrada: int, sessao=None) -> list:
    sessao = sessao or db.session
    teto = min(int(limite), int(registrada))
    if teto <= 0:
        return []
    linhas = sessao.execute(
        select(ProdutoDesempenhoAnalise)
        .where(ProdutoDesempenhoAnalise.id_analise == id_analise,
               ProdutoDesempenhoAnalise.posicao_movimentacao.is_not(None),
               ProdutoDesempenhoAnalise.posicao_movimentacao <= teto)
        .order_by(ProdutoDesempenhoAnalise.posicao_movimentacao)
    ).scalars().all()
    return [produto_de_detalhe(linha) for linha in linhas]


def movimentacao_acima(id_analise: int, limite: int, registrada: int, sessao=None) -> list:
    """Primeiras linhas COMPARÁVEIS com compras acima das vendas (saída abaixo
    de SAIDA_ABAIXO), em todo o registro, na ordem da movimentação (maior
    diferença primeiro). As regras reconferem cada linha em Decimal."""
    sessao = sessao or db.session
    if int(limite) <= 0 or int(registrada) <= 0:
        return []
    linhas = sessao.execute(
        select(ProdutoDesempenhoAnalise)
        .where(ProdutoDesempenhoAnalise.id_analise == id_analise,
               ProdutoDesempenhoAnalise.situacao_movimentacao == "COMPARAVEL",
               ProdutoDesempenhoAnalise.diferenca_quantidade > 0,
               ProdutoDesempenhoAnalise.quantidade_comprada > 0,
               ProdutoDesempenhoAnalise.quantidade_vendida < ProdutoDesempenhoAnalise.quantidade_comprada * SAIDA_ABAIXO,
               ProdutoDesempenhoAnalise.posicao_movimentacao.is_not(None),
               ProdutoDesempenhoAnalise.posicao_movimentacao <= int(registrada))
        .order_by(ProdutoDesempenhoAnalise.posicao_movimentacao)
        .limit(int(limite))
    ).scalars().all()
    return [produto_de_detalhe(linha) for linha in linhas]


def contagem_situacoes(id_analise: int, registrada: int, sessao=None) -> dict:
    """Quantos produtos registrados há em cada situação da movimentação."""
    sessao = sessao or db.session
    linhas = sessao.execute(
        select(ProdutoDesempenhoAnalise.situacao_movimentacao, func.count())
        .where(ProdutoDesempenhoAnalise.id_analise == id_analise,
               ProdutoDesempenhoAnalise.posicao_movimentacao.is_not(None),
               ProdutoDesempenhoAnalise.posicao_movimentacao <= int(registrada))
        .group_by(ProdutoDesempenhoAnalise.situacao_movimentacao)
    ).all()
    return {situacao: int(total) for situacao, total in linhas if situacao}


def faturamento_por_chave(id_analise: int, chaves: list, sessao=None) -> dict:
    """Faturamento, no detalhamento de outra análise, dos produtos indicados."""
    sessao = sessao or db.session
    chaves = [c for c in dict.fromkeys(chaves) if c]
    if not chaves:
        return {}
    linhas = sessao.execute(
        select(ProdutoDesempenhoAnalise.produto_chave, ProdutoDesempenhoAnalise.faturamento)
        .where(ProdutoDesempenhoAnalise.id_analise == id_analise,
               ProdutoDesempenhoAnalise.produto_chave.in_(chaves),
               ProdutoDesempenhoAnalise.faturamento.is_not(None))
    ).all()
    return {chave: dec(valor) for chave, valor in linhas}


# =====================================================================
# Consulta paginada (endpoint da Visão Geral)
# =====================================================================
def _termo_busca(busca) -> str:
    texto = " ".join(str(busca or "").split())[:LIMITE_BUSCA]
    return "".join(ch for ch in texto if ch.isprintable())


def _pagina(numero, total: int) -> tuple:
    paginas = max(1, -(-total // ITENS_POR_PAGINA))
    try:
        pagina = int(numero)
    except (TypeError, ValueError):
        pagina = 1
    pagina = min(max(1, pagina), paginas)
    return pagina, paginas


def serializar_consulta(resultado: dict) -> dict:
    """Página da consulta em JSON: só campos de exibição, já formatados em pt-BR
    (o navegador não refaz conta nem arredondamento)."""
    from inteligencia_comercial import fmt_moeda, fmt_percentual, fmt_quantidade, fmt_quantidade_sinal
    itens = []
    for item in resultado["itens"]:
        if resultado["visao"] == "ranking":
            itens.append({
                "posicao": item.posicao, "nome": item.nome, "classe": item.classe,
                "faturamento": fmt_moeda(item.faturamento),
                "percentual_individual": fmt_percentual(item.percentual_individual, casas=2),
                "percentual_acumulado": fmt_percentual(item.percentual_acumulado, casas=2),
                "quantidade_vendida": fmt_quantidade(item.quantidade_vendida),
            })
        else:
            # Cada quantidade com a unidade do seu próprio relatório (nenhuma presumida).
            itens.append({
                "nome": item["nome"], "classe": item["classe"],
                "unidade_compra": item["unidade_compra"], "unidade_venda": item["unidade_venda"],
                "comprado": fmt_quantidade(item["comprado"]), "vendido": fmt_quantidade(item["vendido"]),
                "diferenca": None if item["diferenca"] is None else fmt_quantidade_sinal(item["diferenca"]),
                "nivel": item["nivel"], "interpretacao": item["interpretacao"],
                "recomendacao": item["recomendacao"] or "—",
            })
    meta = {chave: valor for chave, valor in resultado.items() if chave != "itens"}
    return {**meta, "itens": itens}


_NAO_CARREGADO = object()


def consultar_produtos(analise, visao: str, pagina=1, classe=None, filtro=None, busca=None, sessao=None,
                       complemento=_NAO_CARREGADO, compras_autorizadas: bool = True) -> dict:
    """Página da consulta completa (ranking ABC ou movimentação) de UMA análise
    já autorizada pelo chamador. `itens` traz Produto (ranking) ou a linha
    interpretada da movimentação; serializar_consulta prepara o JSON.
    `complemento` evita reconsultar o resumo quando o chamador já o tem;
    `compras_autorizadas` (movimentacao_autorizada) libera a visão de compras."""
    from inteligencia_comercial import linha_movimentacao
    sessao = sessao or db.session
    visao = visao if visao in VISOES else "ranking"
    classe = classe if classe in ("A", "B", "C") else None
    termo = _termo_busca(busca)
    if complemento is _NAO_CARREGADO:
        complemento = complemento_vigente(analise, sessao)

    if visao == "ranking":
        if complemento is None:
            # Análise anterior ao detalhamento: só o top-20 armazenado.
            linhas = [produto_de_curva(linha) for linha in analise.curva_abc]
            if classe:
                linhas = [p for p in linhas if p.classe == classe]
            if termo:
                alvo = _normalizar_produto(termo)
                linhas = [p for p in linhas if alvo in _normalizar_produto(p.nome)]
            total = len(linhas)
            pagina, paginas = _pagina(pagina, total)
            inicio = (pagina - 1) * ITENS_POR_PAGINA
            armazenados = len(analise.curva_abc)
            return {"visao": visao, "pagina": pagina, "paginas": paginas, "total": total,
                    "itens": linhas[inicio:inicio + ITENS_POR_PAGINA], "completo": armazenados < LIMITE_RANKING_LEGADO,
                    "legado": True, "registrados": armazenados, "universo": None, "filtro": None}
        condicoes = [ProdutoDesempenhoAnalise.id_analise == analise.id_analise,
                     ProdutoDesempenhoAnalise.posicao_ranking.is_not(None),
                     ProdutoDesempenhoAnalise.posicao_ranking <= complemento.ranking_registrado]
        if classe:
            condicoes.append(ProdutoDesempenhoAnalise.classe_abc == classe)
        ordem = ProdutoDesempenhoAnalise.posicao_ranking
        universo = complemento.abc_total_produtos
        registrados = complemento.ranking_registrado
    else:
        if complemento is None or not complemento.compras_por_produto or not compras_autorizadas:
            return {"visao": visao, "pagina": 1, "paginas": 1, "total": 0, "itens": [], "completo": False,
                    "legado": complemento is None, "registrados": 0, "universo": None, "indisponivel": True}
        filtro = filtro if filtro in FILTROS_MOVIMENTACAO else "acima"
        condicoes = [ProdutoDesempenhoAnalise.id_analise == analise.id_analise,
                     ProdutoDesempenhoAnalise.posicao_movimentacao.is_not(None),
                     ProdutoDesempenhoAnalise.posicao_movimentacao <= complemento.movimentacao_registrada]
        situacao = ProdutoDesempenhoAnalise.situacao_movimentacao
        if filtro == "acima":
            # Mesmo critério das recomendações: saída abaixo de 90% do volume comprado.
            condicoes += [situacao == "COMPARAVEL", ProdutoDesempenhoAnalise.diferenca_quantidade > 0,
                          ProdutoDesempenhoAnalise.quantidade_comprada > 0,
                          ProdutoDesempenhoAnalise.quantidade_vendida
                          < ProdutoDesempenhoAnalise.quantidade_comprada * SAIDA_ABAIXO]
        elif filtro == "comparaveis":
            condicoes.append(situacao == "COMPARAVEL")
        elif filtro == "sem_correspondencia":
            condicoes.append(situacao == "SEM_VENDA_CORRESPONDENTE")
        elif filtro == "unidades":
            condicoes.append(situacao.in_(("UNIDADE_DIVERGENTE", "UNIDADE_AMBIGUA")))
        elif filtro == "invalidas":
            condicoes.append(situacao == "QUANTIDADE_INVALIDA")
        ordem = ProdutoDesempenhoAnalise.posicao_movimentacao
        universo = complemento.movimentacao_total
        registrados = complemento.movimentacao_registrada
    alvo = _normalizar_produto(termo) if termo else ""
    if alvo:
        # Mesma normalização do ETL e da consulta legada (sem acentos, sem
        # pontuação, maiúsculas): "acucar" encontra "AÇÚCAR", "coca cola"
        # encontra "COCA-COLA". O termo normalizado só tem [A-Z0-9 ].
        condicoes.append(ProdutoDesempenhoAnalise.produto_busca.contains(alvo, autoescape=True))
    total = int(sessao.scalar(select(func.count()).select_from(ProdutoDesempenhoAnalise).where(*condicoes)) or 0)
    pagina, paginas = _pagina(pagina, total)
    linhas = sessao.execute(
        select(ProdutoDesempenhoAnalise).where(*condicoes).order_by(ordem)
        .offset((pagina - 1) * ITENS_POR_PAGINA).limit(ITENS_POR_PAGINA)
    ).scalars().all()
    produtos = [produto_de_detalhe(linha) for linha in linhas]
    itens = produtos if visao == "ranking" else [linha_movimentacao(p) for p in produtos]
    return {"visao": visao, "pagina": pagina, "paginas": paginas, "total": total,
            "itens": itens, "completo": registrados >= universo,
            "legado": False, "registrados": registrados, "universo": universo,
            "filtro": filtro if visao == "movimentacao" else None}
