"""
NEXO - Visão Geral do cliente: montagem dos dados do painel
==========================================================
Reúne, com consultas LIMITADAS, o que a Visão Geral exibe e aplica as regras
de inteligencia_comercial.py. O blueprint só autoriza e entrega o resultado ao
template; nenhuma regra analítica fica no HTML.

Fontes (todas já processadas e autorizadas):
    - indicador_analise ............ KPIs consolidados do ETL;
    - produto_curva_abc ............ top-20 do ranking (todas as análises);
    - indicador_complementar_analise e produto_desempenho_analise
                                     detalhamento completo (análises processadas
                                     após a migração 5a9c3e7d1b42);
    - análises anteriores .......... só as que a política contratual libera;
    - relatorio_analise ............ apenas a cópia PUBLICADA (SEC-003).

Nada aqui chama serviço externo nem reprocessa arquivos: o painel lê o que o ETL
e a equipe NEXO já gravaram.
"""

from __future__ import annotations

from sqlalchemy import select

import detalhamento_produtos as det
from etl_processor import _normalizar_produto, chave_produto
from extensions import db
from inteligencia_comercial import (
    ContextoPainel, Produto, cartoes_classes, comparacao_periodos, dec, distribuicao_abc, fmt_data,
    formatadores, gerar_insights, gerar_recomendacoes, gerar_resumo_executivo,
    interpretar_evolucao_compras_vendas, interpretar_evolucao_faturamento, moeda, montar_serie_historica,
    nivel_pressao, para_float, percentual, resumo_movimentacao, variacoes_produtos,
)
from models import ProdutoDesempenhoAnalise

# Quantidades exibidas de início (o restante fica na consulta paginada). O Pareto
# mantém os 10 primeiros, como a página da análise e a explicação do NexoBot.
TOPO_PARETO = 10
TOPO_COMPARACAO_PRODUTOS = 20
TOPO_MOVIMENTACAO = 10
DESTAQUES_POR_CLASSE = 3


def _periodo_texto(auditoria) -> str:
    if not auditoria or not auditoria.get("periodo_inicio") or not auditoria.get("periodo_fim"):
        return "período não identificado"
    return f"{fmt_data(auditoria['periodo_inicio'])} a {fmt_data(auditoria['periodo_fim'])}"


def _mais_vendido(indicador, ranking: list, complemento, id_analise: int):
    """Produto mais vendido (quantidade) com sua posição/participação no
    faturamento quando conhecidas. O nome e a quantidade vêm do KPI do ETL."""
    nome = getattr(indicador, "produto_mais_vendido_nome", None)
    if not nome:
        return None
    quantidade = dec(indicador.produto_mais_vendido_quantidade)
    achado = next((p for p in ranking if p.nome == nome), None)
    if achado is None and complemento is not None:
        chave = chave_produto(_normalizar_produto(nome))
        linha = db.session.execute(
            select(ProdutoDesempenhoAnalise).where(ProdutoDesempenhoAnalise.id_analise == id_analise,
                                                   ProdutoDesempenhoAnalise.produto_chave == chave)
        ).scalar_one_or_none()
        if linha is not None:
            achado = det.produto_de_detalhe(linha)
    if achado is not None:
        return Produto(nome=nome, chave=achado.chave, posicao=achado.posicao, classe=achado.classe,
                       faturamento=achado.faturamento, quantidade_vendida=quantidade,
                       percentual_individual=achado.percentual_individual, unidade_venda=achado.unidade_venda)
    return Produto(nome=nome, quantidade_vendida=quantidade)


def _faturamento_anterior(anterior_analise, chaves: list) -> tuple:
    """(chave -> faturamento, ranking anterior completo?) do período anterior
    comparável, só para os produtos atuais (consulta limitada pelas chaves)."""
    complemento = det.complemento_vigente(anterior_analise)
    if complemento is not None:
        completo = complemento.ranking_registrado >= complemento.abc_total_produtos
        return det.faturamento_por_chave(anterior_analise.id_analise, chaves), completo
    linhas = [det.produto_de_curva(linha) for linha in anterior_analise.curva_abc]
    mapa = {p.chave: p.faturamento for p in linhas if p.faturamento is not None and p.chave in set(chaves)}
    return mapa, len(linhas) < det.LIMITE_RANKING_LEGADO


def _serie_json(serie) -> dict | None:
    """Série dos gráficos históricos. Mantém o contrato anterior do painel
    (labels/vendas/compras, nula com menos de 2 pontos) e acrescenta os pontos
    com datas reais e marcação de lacunas."""
    if not serie.atual_comparavel or len(serie.pontos) < 2:
        return None
    return {
        "tipo": serie.tipo,
        "labels": [p.rotulo for p in serie.pontos],
        "vendas": [para_float(moeda(p.faturamento)) for p in serie.pontos],
        "compras": [para_float(moeda(p.compras)) if p.compras is not None else None for p in serie.pontos],
        "pontos": [{
            "id": p.id_analise, "rotulo": p.rotulo, "inicio": p.inicio.isoformat(), "fim": p.fim.isoformat(),
            "periodo": f"{fmt_data(p.inicio)} a {fmt_data(p.fim)}", "meio": p.meio.isoformat(),
            "faturamento": para_float(moeda(p.faturamento)),
            "compras": para_float(moeda(p.compras)) if p.compras is not None else None,
            "atual": p.atual, "lacuna_antes": p.lacuna_antes,
        } for p in serie.pontos],
    }


def montar_painel(analise, analises: list, auditoria, situacao=None) -> dict:
    """Contexto completo da Visão Geral para UMA análise publicada e autorizada.

    `analises` são as análises publicadas que a política contratual permite
    consultar (já filtradas pelo chamador): só elas entram no histórico.
    `situacao` (SituacaoContratual) decide se as compras por produto podem ser
    exibidas (período do relatório de compras coberto)."""
    indicador = analise.indicador
    complemento = det.complemento_vigente(analise)
    compras_autorizadas = det.movimentacao_autorizada(situacao, complemento)
    periodos_divergentes = bool(complemento is not None and complemento.periodos_divergentes)

    if complemento is not None:
        ranking = det.ranking_topo(analise.id_analise, max(TOPO_PARETO, TOPO_COMPARACAO_PRODUTOS),
                                   complemento.ranking_registrado)
        destaques = det.destaques_por_classe(analise.id_analise, complemento.ranking_registrado, DESTAQUES_POR_CLASSE)
        linhas_legado = None
        if complemento.compras_por_produto and compras_autorizadas:
            topo_mov = det.movimentacao_topo(analise.id_analise, TOPO_MOVIMENTACAO, complemento.movimentacao_registrada)
            contagem = det.contagem_situacoes(analise.id_analise, complemento.movimentacao_registrada)
            acima = det.movimentacao_acima(analise.id_analise, TOPO_MOVIMENTACAO, complemento.movimentacao_registrada)
        else:
            topo_mov, contagem, acima = [], {}, None
    else:
        linhas_legado = [det.produto_de_curva(linha) for linha in analise.curva_abc]
        ranking = linhas_legado
        destaques = {c: [p for p in linhas_legado if p.classe == c][:DESTAQUES_POR_CLASSE] for c in "ABC"}
        topo_mov, contagem, acima = [], {}, None

    distribuicao = distribuicao_abc(complemento, linhas_legado)
    lider = ranking[0] if ranking else None
    mais_vendido = _mais_vendido(indicador, ranking, complemento, analise.id_analise)
    serie = montar_serie_historica(analises, analise)

    # Variação por produto em relação ao período anterior COMPARÁVEL (mesma série).
    # Só consulta o período anterior quando há produtos atuais a comparar: no máximo
    # duas consultas, independentemente de quantas análises a empresa tenha.
    # Durações diferentes (28 x 31 dias) são comparadas pela média diária.
    variacoes = []
    atuais = [p for p in ranking[:TOPO_COMPARACAO_PRODUTOS] if p.chave]
    if serie.anterior is not None and serie.atual is not None and atuais:
        anterior = next((a for a in analises if a.id_analise == serie.anterior.id_analise), None)
        if anterior is not None:
            mapa, anterior_completo = _faturamento_anterior(anterior, [p.chave for p in atuais])
            variacoes = variacoes_produtos(atuais, mapa, anterior_completo, indicador.faturamento_total,
                                           dias_atual=serie.atual.dias, dias_anterior=serie.anterior.dias)

    movimentacao = resumo_movimentacao(complemento, indicador, topo_mov, contagem, periodos_divergentes,
                                       acima=acima, compras_autorizadas=compras_autorizadas)
    ctx = ContextoPainel(
        analise=analise, indicador=indicador, complemento=complemento, lider=lider,
        mais_vendido=mais_vendido, distribuicao=distribuicao, destaques_classe=destaques,
        movimentacao=movimentacao, serie=serie, variacoes_produto=variacoes,
    )
    insights = gerar_insights(ctx)
    recomendacoes = gerar_recomendacoes(ctx, insights)
    periodo = _periodo_texto(auditoria)
    resumo = gerar_resumo_executivo(ctx, insights, recomendacoes, periodo)

    comp_faturamento = comparacao_periodos(serie.atual, serie.anterior)
    comp_compras = comparacao_periodos(serie.atual, serie.anterior, "compras")
    var_faturamento = comp_faturamento["bruta"] if comp_faturamento else None
    var_compras = comp_compras["bruta"] if comp_compras else None
    # Totais de períodos com durações diferentes: o indicador mostra a variação
    # dos totais e declara as durações (as regras usam a média diária).
    nota_duracao = (f"Períodos com durações diferentes: {serie.atual.dias} dias neste e "
                    f"{serie.anterior.dias} em {serie.anterior.rotulo}."
                    if comp_faturamento and comp_faturamento["por_dia"] else None)

    faturamento = moeda(indicador.faturamento_total)
    compras = moeda(indicador.total_comprado)
    diferenca = moeda(ctx.diferenca)
    pareto = ranking[:TOPO_PARETO]
    graficos = {
        # Sem um dos totais, nada é desenhado (valor ausente não vira zero).
        "comparativo": {"labels": ["Compras", "Vendas"],
                        "values": [para_float(compras), para_float(faturamento)]}
        if compras is not None and faturamento is not None else None,
        "pressao_estoque": para_float(diferenca) or 0.0,
        "curva_abc": {
            "labels": [p.nome for p in pareto],
            "values": [para_float(moeda(p.faturamento)) or 0.0 for p in pareto],
            "classes": [p.classe for p in pareto],
            "acumulado": [para_float(p.percentual_acumulado) or 0.0 for p in pareto],
        } if pareto else None,
        "distribuicao": {
            "classes": [c.classe for c in distribuicao.classes],
            "valores": [para_float(c.faturamento) or 0.0 for c in distribuicao.classes],
            "percentuais": [para_float(c.percentual) or 0.0 for c in distribuicao.classes],
            "produtos": [c.produtos for c in distribuicao.classes],
            "total_produtos": distribuicao.total_produtos,
        } if distribuicao.disponivel else None,
        "historico": _serie_json(serie),
    }
    if graficos["historico"]:
        stats = interpretar_evolucao_faturamento(serie)["estatisticas"]
        graficos["historico"]["media"] = para_float(stats["media"]) if stats else None

    # Primeira página das consultas completas (o restante vem do endpoint paginado).
    consulta_ranking = det.consultar_produtos(analise, "ranking", complemento=complemento)
    consulta_movimentacao = (det.consultar_produtos(analise, "movimentacao", filtro="acima", complemento=complemento,
                                                    compras_autorizadas=compras_autorizadas)
                             if movimentacao["disponivel"] else None)

    return {
        "consulta_ranking": consulta_ranking,
        "consulta_movimentacao": consulta_movimentacao,
        "fmt": formatadores(),
        "periodo_texto": periodo,
        "faturamento": faturamento,
        "compras": compras,
        "diferenca": diferenca,
        "diferenca_percentual": percentual(ctx.diferenca, indicador.faturamento_total, 1),
        "variacao_faturamento": var_faturamento,
        "variacao_compras": var_compras,
        "nota_duracao": nota_duracao,
        "nivel_pressao": nivel_pressao(ctx.razao_pressao, ctx.diferenca),
        "referencia_anterior": serie.anterior.rotulo if serie.anterior else None,
        "lider": lider,
        "mais_vendido": mais_vendido,
        "lider_coincide": bool(lider and mais_vendido and lider.nome == mais_vendido.nome),
        "segundo_faturamento": (ranking[1] if len(ranking) > 1 else None),
        "distribuicao": distribuicao,
        "tem_produtos": bool(ranking),
        "cartoes_classes": cartoes_classes(distribuicao, destaques),
        "pareto_total": len(pareto),
        "movimentacao": movimentacao,
        "insights": insights,
        "recomendacoes": recomendacoes,
        "resumo_destaques": resumo,
        "evolucao_faturamento": interpretar_evolucao_faturamento(serie),
        "evolucao_compras_vendas": interpretar_evolucao_compras_vendas(serie),
        "serie": serie,
        "complemento": complemento,
        "periodos_divergentes": periodos_divergentes,
        "graficos": graficos,
    }
