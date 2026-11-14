"""Detalhamento por produto da Visão Geral: universo da Curva ABC e movimentação.

Revision ID: 5a9c3e7d1b42
Revises: f4c2a8e1d9b6

Expand com duas tabelas novas, derivadas do processamento (o ETL as regrava a
cada execução). Nenhuma coluna, FK ou CHECK muda em tabela existente; em especial
produto_curva_abc continua com o top-20 que o PDF, a página da análise e a
devolutiva usam:
  - indicador_complementar_analise (1:1 com analise): distribuição A/B/C sobre
    TODOS os produtos elegíveis, contagens, quanto do detalhamento foi
    registrado (teto de linhas e de saída do worker) e o período lido de cada
    relatório;
  - produto_desempenho_analise: uma linha por produto relevante (ranking
    completo da Curva ABC e/ou comparação unidades compradas x vendidas).

As FKs usam ON DELETE CASCADE: excluir a análise remove o detalhamento no banco,
sem o ORM carregar as linhas (o modelo Analise não tem relationship para elas).

O código funciona antes desta migração (detalhamento_produtos.esquema_detalhamento_
disponivel): sem as tabelas, o ETL não grava o detalhamento e a Visão Geral usa o
top-20 de produto_curva_abc, declarando o que não está disponível.

No PostgreSQL as tabelas nascem com RLS ligado. Onde existirem os papéis da Data API
do Supabase (anon, authenticated), os privilégios deles são revogados e a política
restritiva deny_api_access lhes nega tudo; postgres e service_role, onde existirem,
recebem a política acesso_servidor. Num PostgreSQL sem esses papéis (testes,
restauração isolada) as políticas não são criadas.

O downgrade recusa apagar dados: só remove as estruturas com as duas tabelas vazias.
Os dados são reconstruíveis reprocessando as análises, mas a decisão de descartá-los
fica com quem opera o banco (backup e TRUNCATE explícitos).
"""

from alembic import op
import sqlalchemy as sa


revision = "5a9c3e7d1b42"
down_revision = "f4c2a8e1d9b6"
branch_labels = None
depends_on = None

_TABELAS = ("indicador_complementar_analise", "produto_desempenho_analise")

# Sem "%" no texto: a prévia offline (flask db upgrade --sql) sai igual ao que roda no banco.
_POLITICAS_POSTGRESQL = """
DO $$
DECLARE
    tabela text;
    papeis_api text;
    papeis_servidor text;
BEGIN
    SELECT string_agg(quote_ident(rolname), ', ' ORDER BY rolname) INTO papeis_api
      FROM pg_roles WHERE rolname IN ('anon', 'authenticated');
    SELECT string_agg(quote_ident(rolname), ', ' ORDER BY rolname) INTO papeis_servidor
      FROM pg_roles WHERE rolname IN ('postgres', 'service_role');
    FOREACH tabela IN ARRAY ARRAY['indicador_complementar_analise', 'produto_desempenho_analise'] LOOP
        IF papeis_api IS NOT NULL THEN
            EXECUTE 'REVOKE ALL ON TABLE ' || quote_ident(tabela) || ' FROM ' || papeis_api;
            EXECUTE 'CREATE POLICY deny_api_access ON ' || quote_ident(tabela)
                 || ' AS RESTRICTIVE FOR ALL TO ' || papeis_api || ' USING (false) WITH CHECK (false)';
        END IF;
        IF papeis_servidor IS NOT NULL THEN
            EXECUTE 'CREATE POLICY acesso_servidor ON ' || quote_ident(tabela)
                 || ' AS PERMISSIVE FOR ALL TO ' || papeis_servidor || ' USING (true) WITH CHECK (true)';
        END IF;
    END LOOP;
END
$$;
"""


def upgrade():
    op.create_table(
        "indicador_complementar_analise",
        sa.Column("id_indicador_complementar", sa.Integer(), nullable=False),
        sa.Column("id_analise", sa.Integer(), nullable=False),
        sa.Column("versao_metodologia", sa.Integer(), nullable=False),
        sa.Column("versao_processamento", sa.Integer(), nullable=False),
        sa.Column("abc_total_produtos", sa.Integer(), nullable=False),
        sa.Column("abc_faturamento_total", sa.Numeric(), nullable=False),
        sa.Column("abc_produtos_a", sa.Integer(), nullable=False),
        sa.Column("abc_produtos_b", sa.Integer(), nullable=False),
        sa.Column("abc_produtos_c", sa.Integer(), nullable=False),
        sa.Column("abc_faturamento_a", sa.Numeric(), nullable=False),
        sa.Column("abc_faturamento_b", sa.Numeric(), nullable=False),
        sa.Column("abc_faturamento_c", sa.Numeric(), nullable=False),
        sa.Column("produtos_vendas", sa.Integer(), nullable=False),
        sa.Column("produtos_compras", sa.Integer(), nullable=True),
        sa.Column("compras_por_produto", sa.Boolean(), nullable=False),
        sa.Column("unidade_vendas_informada", sa.Boolean(), nullable=False),
        sa.Column("unidade_compras_informada", sa.Boolean(), nullable=False),
        sa.Column("periodo_vendas_inicio", sa.Date(), nullable=True),
        sa.Column("periodo_vendas_fim", sa.Date(), nullable=True),
        sa.Column("periodo_compras_inicio", sa.Date(), nullable=True),
        sa.Column("periodo_compras_fim", sa.Date(), nullable=True),
        sa.Column("produtos_registrados", sa.Integer(), nullable=False),
        sa.Column("ranking_registrado", sa.Integer(), nullable=False),
        sa.Column("movimentacao_total", sa.Integer(), nullable=False),
        sa.Column("movimentacao_registrada", sa.Integer(), nullable=False),
        sa.Column("movimentacao_comparaveis", sa.Integer(), nullable=True),
        sa.Column("movimentacao_sem_venda", sa.Integer(), nullable=True),
        sa.Column("movimentacao_unidade_divergente", sa.Integer(), nullable=True),
        sa.Column("movimentacao_unidade_ambigua", sa.Integer(), nullable=True),
        sa.Column("movimentacao_quantidade_invalida", sa.Integer(), nullable=True),
        sa.Column("registro_limitado", sa.Boolean(), nullable=False),
        sa.Column("data_geracao", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "abc_total_produtos >= 0 AND abc_produtos_a >= 0 AND abc_produtos_b >= 0 AND abc_produtos_c >= 0 "
            "AND abc_produtos_a + abc_produtos_b + abc_produtos_c = abc_total_produtos",
            name="ck_indicador_complementar_abc",
        ),
        sa.CheckConstraint(
            "produtos_registrados >= 0 AND ranking_registrado >= 0 AND ranking_registrado <= abc_total_produtos "
            "AND movimentacao_registrada >= 0 AND movimentacao_registrada <= movimentacao_total",
            name="ck_indicador_complementar_registro",
        ),
        sa.CheckConstraint(
            "(movimentacao_comparaveis IS NULL AND movimentacao_sem_venda IS NULL "
            "AND movimentacao_unidade_divergente IS NULL AND movimentacao_unidade_ambigua IS NULL "
            "AND movimentacao_quantidade_invalida IS NULL) OR ("
            "movimentacao_comparaveis IS NOT NULL AND movimentacao_sem_venda IS NOT NULL "
            "AND movimentacao_unidade_divergente IS NOT NULL AND movimentacao_unidade_ambigua IS NOT NULL "
            "AND movimentacao_quantidade_invalida IS NOT NULL AND movimentacao_comparaveis >= 0 "
            "AND movimentacao_sem_venda >= 0 AND movimentacao_unidade_divergente >= 0 "
            "AND movimentacao_unidade_ambigua >= 0 AND movimentacao_quantidade_invalida >= 0 "
            "AND movimentacao_comparaveis + movimentacao_sem_venda + movimentacao_unidade_divergente "
            "+ movimentacao_unidade_ambigua + movimentacao_quantidade_invalida = movimentacao_total)",
            name="ck_indicador_complementar_situacoes",
        ),
        sa.ForeignKeyConstraint(["id_analise"], ["analise.id_analise"], name="fk_indicador_complementar_analise",
                                ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id_indicador_complementar"),
        sa.UniqueConstraint("id_analise", name="uq_indicador_complementar_analise"),
    )
    op.create_table(
        "produto_desempenho_analise",
        sa.Column("id_produto_desempenho", sa.Integer(), nullable=False),
        sa.Column("id_analise", sa.Integer(), nullable=False),
        sa.Column("produto_chave", sa.String(length=16), nullable=False),
        sa.Column("produto_nome", sa.String(), nullable=False),
        sa.Column("produto_busca", sa.String(length=255), nullable=False),
        sa.Column("posicao_ranking", sa.Integer(), nullable=True),
        sa.Column("classe_abc", sa.String(length=1), nullable=True),
        sa.Column("faturamento", sa.Numeric(), nullable=True),
        sa.Column("quantidade_vendida", sa.Numeric(), nullable=True),
        sa.Column("percentual_individual", sa.Numeric(), nullable=True),
        sa.Column("percentual_acumulado", sa.Numeric(), nullable=True),
        sa.Column("quantidade_comprada", sa.Numeric(), nullable=True),
        sa.Column("unidade_venda", sa.String(length=12), nullable=True),
        sa.Column("unidade_compra", sa.String(length=12), nullable=True),
        sa.Column("situacao_movimentacao", sa.String(length=30), nullable=True),
        sa.Column("diferenca_quantidade", sa.Numeric(), nullable=True),
        sa.Column("posicao_movimentacao", sa.Integer(), nullable=True),
        sa.Column("data_geracao", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("classe_abc IS NULL OR classe_abc IN ('A', 'B', 'C')", name="ck_produto_desempenho_classe"),
        sa.CheckConstraint(
            "situacao_movimentacao IS NULL OR situacao_movimentacao IN ('COMPARAVEL', 'SEM_VENDA_CORRESPONDENTE', "
            "'UNIDADE_DIVERGENTE', 'UNIDADE_AMBIGUA', 'QUANTIDADE_INVALIDA')",
            name="ck_produto_desempenho_situacao",
        ),
        sa.CheckConstraint("(posicao_ranking IS NULL) = (classe_abc IS NULL)", name="ck_produto_desempenho_ranking"),
        sa.CheckConstraint("diferenca_quantidade IS NULL OR situacao_movimentacao = 'COMPARAVEL'",
                           name="ck_produto_desempenho_diferenca"),
        sa.ForeignKeyConstraint(["id_analise"], ["analise.id_analise"], name="fk_produto_desempenho_analise",
                                ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id_produto_desempenho"),
        sa.UniqueConstraint("id_analise", "produto_chave", name="uq_produto_desempenho_chave"),
        sa.UniqueConstraint("id_analise", "posicao_ranking", name="uq_produto_desempenho_posicao"),
        sa.UniqueConstraint("id_analise", "posicao_movimentacao", name="uq_produto_desempenho_movimentacao"),
    )
    if op.get_bind().dialect.name == "postgresql":
        for tabela in _TABELAS:
            op.execute(f"ALTER TABLE {tabela} ENABLE ROW LEVEL SECURITY")
        op.execute(_POLITICAS_POSTGRESQL)


def downgrade():
    conexao = op.get_bind()
    if conexao.dialect.name == "postgresql":
        # Uma gravação do ETL em andamento não aparece na contagem e seria apagada pelo DROP:
        # espera por ela. Com processamento em curso, repita se abortar.
        op.execute("LOCK TABLE analise, " + ", ".join(_TABELAS) + " IN ACCESS EXCLUSIVE MODE")
    linhas = sum(conexao.execute(sa.text(f"SELECT COUNT(*) FROM {tabela}")).scalar() or 0 for tabela in _TABELAS)
    if linhas:
        raise RuntimeError(
            "Downgrade do detalhamento por produto recusado: indicador_complementar_analise ou "
            "produto_desempenho_analise têm dados. São dados derivados do processamento (reconstruíveis "
            "reprocessando as análises), mas descartá-los é decisão de quem opera o banco: faça backup e "
            "esvazie as duas tabelas explicitamente antes de remover as estruturas."
        )
    op.drop_table("produto_desempenho_analise")
    op.drop_table("indicador_complementar_analise")
