"""Catálogo comercial padrão dos planos: fonte única de preços e benefícios.

Preços públicos definidos pelo proprietário (NEXO-AJ-02): Bronze R$ 150,
Prata R$ 300 e Ouro R$ 650 por mês. Frequência e níveis de serviço continuam
os do catálogo anterior até decisão comercial específica.

O seed só cria planos ausentes. Planos já gravados mudam apenas pela
atualização auditada abaixo (comando `flask planos atualizar-precos`), que
registra cada alteração em historico_preco_plano. Contratos não são tocados:
cada um guarda o próprio valor contratado.
"""

from decimal import Decimal

from sqlalchemy import select

from models import HistoricoPrecoPlano, Plano

VERSAO_CATALOGO = "catalogo-2026-10-bronze150-prata300-ouro650"

CATALOGO_PLANOS = (
    {
        "nome_plano": "BRONZE",
        "descricao": "Análise mensal básica para pequenos comércios.",
        "valor_mensal": Decimal("150.00"),
        "qtd_analises_mes": 1,
        "tipo_analise_permitida": "MENSAL",
        "nivel_entrega_analise": "BASICA",
        "nivel_dashboard": "RESUMIDO",
        "nivel_atendimento": "BAIXO",
    },
    {
        "nome_plano": "PRATA",
        "descricao": "Análise mensal completa com KPIs detalhados.",
        "valor_mensal": Decimal("300.00"),
        "qtd_analises_mes": 1,
        "tipo_analise_permitida": "MENSAL",
        "nivel_entrega_analise": "COMPLETA",
        "nivel_dashboard": "GERENCIAL",
        "nivel_atendimento": "MEDIO",
    },
    {
        "nome_plano": "OURO",
        "descricao": "Análises quinzenais premium com atendimento prioritário.",
        "valor_mensal": Decimal("650.00"),
        "qtd_analises_mes": 2,
        "tipo_analise_permitida": "QUINZENAL",
        "nivel_entrega_analise": "PREMIUM",
        "nivel_dashboard": "COMPLETO",
        "nivel_atendimento": "ALTO",
    },
)


def precos_padrao() -> dict:
    return {item["nome_plano"]: item["valor_mensal"] for item in CATALOGO_PLANOS}


def planejar_atualizacao_precos(sessao, *, bloquear: bool = False) -> list:
    """Diferenças entre o banco e o catálogo; nada é alterado."""
    consulta = select(Plano).where(Plano.nome_plano.in_(precos_padrao())).order_by(Plano.id_plano)
    if bloquear:
        consulta = consulta.with_for_update()
    alteracoes = []
    for plano in sessao.scalars(consulta):
        novo = precos_padrao()[plano.nome_plano]
        atual = Decimal(str(plano.valor_mensal))
        if atual != novo:
            alteracoes.append({"plano": plano, "anterior": atual, "novo": novo})
    return alteracoes


def aplicar_atualizacao_precos(sessao, *, instante, origem: str = VERSAO_CATALOGO) -> list:
    """Idempotente: só altera o que diverge e registra o histórico na mesma transação.

    Não confirma a transação; o chamador decide commit ou rollback.
    """
    alteracoes = planejar_atualizacao_precos(sessao, bloquear=True)
    for item in alteracoes:
        plano = item["plano"]
        sessao.add(HistoricoPrecoPlano(
            id_plano=plano.id_plano, valor_anterior=item["anterior"], valor_novo=item["novo"],
            alterado_em=instante, origem=origem,
        ))
        plano.valor_mensal = item["novo"]
        plano.data_atualizacao = instante
    return alteracoes
