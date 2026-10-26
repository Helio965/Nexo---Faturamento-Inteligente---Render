"""Gestão contratual: regime, contratos, coberturas pagas, eventos e preços.

Revision ID: 81287c74387a
Revises: e4c004a26b01

Somente tabelas novas (expand, Etapa 0.2 G.4): nenhuma coluna é adicionada a
empresa, usuario, analise ou plano. Nenhum contrato, cobertura ou pagamento é
criado para empresas existentes: elas continuam no regime legado até a
conciliação administrativa (ver
Docs/GESTAO_CONTRATUAL/04_PLANO_DE_MIGRACAO_E_IMPLANTACAO.md).

Vem depois da e4c004a26b01 (SEC-004), cuja janela própria continua
obrigatória. Não executar pelo build nem contra produção sem a janela de
implantação aprovada; aplicar pelo ID da revisão.

O downgrade recusa-se a apagar dados contratuais: só remove as estruturas
quando todas as tabelas novas estão vazias.
"""

from alembic import op
import sqlalchemy as sa


revision = "81287c74387a"
down_revision = "e4c004a26b01"
branch_labels = None
depends_on = None

_APLICAVEL = "situacao IN ('ATIVO', 'SUSPENSO')"


_TABELAS = ("regime_contratual", "contrato", "cobertura_paga", "evento_contratual", "historico_preco_plano")


def upgrade():
    op.create_table(
        "regime_contratual",
        sa.Column("id_empresa", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("ativado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id_usuario_admin_ativacao", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id_empresa"),
        sa.ForeignKeyConstraint(["id_empresa"], ["empresa.id_empresa"]),
        sa.ForeignKeyConstraint(["id_usuario_admin_ativacao"], ["usuario.id_usuario"]),
    )

    op.create_table(
        "contrato",
        sa.Column("id_contrato", sa.Integer(), nullable=False),
        sa.Column("id_empresa", sa.Integer(), nullable=False),
        sa.Column("id_plano", sa.Integer(), nullable=False),
        sa.Column("id_contrato_anterior", sa.Integer(), nullable=True),
        sa.Column("valor_mensal_contratado", sa.Numeric(12, 2), nullable=False),
        sa.Column("data_inicio", sa.Date(), nullable=False),
        sa.Column("data_fim", sa.Date(), nullable=True),
        sa.Column("data_formalizacao", sa.Date(), nullable=True),
        sa.Column("referencia_formalizacao", sa.String(200), nullable=True),
        sa.Column("situacao", sa.String(20), nullable=False),
        sa.Column("meses_suspensao", sa.Integer(), nullable=True),
        sa.Column("suspenso_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspensao_motivo", sa.Text(), nullable=True),
        sa.Column("suspensao_limite_original", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspensao_limite", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pdf_limite_original", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pdf_limite", sa.DateTime(timezone=True), nullable=True),
        sa.Column("encerrado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelamento_motivo", sa.Text(), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("id_usuario_admin_responsavel", sa.Integer(), nullable=False),
        sa.Column("versao", sa.Integer(), server_default="1", nullable=False),
        sa.Column("data_criacao", sa.DateTime(timezone=True),
                  server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("data_atualizacao", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id_contrato"),
        sa.ForeignKeyConstraint(["id_empresa"], ["empresa.id_empresa"]),
        sa.ForeignKeyConstraint(["id_plano"], ["plano.id_plano"]),
        sa.ForeignKeyConstraint(["id_usuario_admin_responsavel"], ["usuario.id_usuario"]),
        sa.UniqueConstraint("id_contrato", "id_empresa", name="uq_contrato_id_empresa"),
        sa.UniqueConstraint("id_contrato_anterior", name="uq_contrato_anterior"),
        sa.ForeignKeyConstraint(
            ["id_contrato_anterior", "id_empresa"],
            ["contrato.id_contrato", "contrato.id_empresa"],
            name="fk_contrato_anterior_mesma_empresa",
        ),
        sa.CheckConstraint(
            "situacao IN ('ATIVO', 'SUSPENSO', 'ENCERRADO', 'CANCELADO')",
            name="ck_contrato_situacao",
        ),
        sa.CheckConstraint("valor_mensal_contratado >= 0", name="ck_contrato_valor"),
        sa.CheckConstraint("data_fim IS NULL OR data_fim >= data_inicio", name="ck_contrato_vigencia"),
        sa.CheckConstraint(
            "meses_suspensao IS NULL OR meses_suspensao BETWEEN 1 AND 12",
            name="ck_contrato_meses_suspensao",
        ),
        sa.CheckConstraint("versao >= 1", name="ck_contrato_versao"),
        sa.CheckConstraint(
            "id_contrato_anterior IS NULL OR id_contrato_anterior <> id_contrato",
            name="ck_contrato_anterior_distinto",
        ),
        sa.CheckConstraint(
            "situacao <> 'SUSPENSO' OR ("
            "suspenso_em IS NOT NULL AND suspensao_limite_original IS NOT NULL "
            "AND suspensao_limite IS NOT NULL AND pdf_limite_original IS NOT NULL "
            "AND pdf_limite IS NOT NULL "
            "AND suspensao_limite_original > suspenso_em "
            "AND suspensao_limite >= suspensao_limite_original "
            "AND pdf_limite_original > suspenso_em "
            "AND pdf_limite >= pdf_limite_original "
            "AND pdf_limite <= suspensao_limite)",
            name="ck_contrato_suspensao",
        ),
        sa.CheckConstraint(
            "situacao <> 'ATIVO' OR (suspenso_em IS NULL AND suspensao_limite IS NULL "
            "AND suspensao_limite_original IS NULL AND pdf_limite IS NULL "
            "AND pdf_limite_original IS NULL AND encerrado_em IS NULL "
            "AND cancelado_em IS NULL)",
            name="ck_contrato_ativo_sem_prazos",
        ),
        sa.CheckConstraint("situacao <> 'ENCERRADO' OR encerrado_em IS NOT NULL", name="ck_contrato_encerrado"),
        sa.CheckConstraint(
            "situacao <> 'CANCELADO' OR (cancelado_em IS NOT NULL "
            "AND cancelamento_motivo IS NOT NULL)",
            name="ck_contrato_cancelado",
        ),
    )
    op.create_index("ix_contrato_empresa", "contrato", ["id_empresa"], unique=False)
    op.create_index(
        "uq_contrato_aplicavel_empresa", "contrato", ["id_empresa"], unique=True,
        postgresql_where=sa.text(_APLICAVEL), sqlite_where=sa.text(_APLICAVEL),
    )

    op.create_table(
        "cobertura_paga",
        sa.Column("id_cobertura", sa.Integer(), nullable=False),
        sa.Column("id_contrato", sa.Integer(), nullable=False),
        sa.Column("id_empresa", sa.Integer(), nullable=False),
        sa.Column("periodo_inicio", sa.Date(), nullable=False),
        sa.Column("periodo_fim", sa.Date(), nullable=False),
        sa.Column("referencia_confirmacao", sa.String(200), nullable=False),
        sa.Column("confirmado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id_usuario_admin_confirmacao", sa.Integer(), nullable=False),
        sa.Column("revogada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revogacao_motivo", sa.Text(), nullable=True),
        sa.Column("id_usuario_admin_revogacao", sa.Integer(), nullable=True),
        sa.Column("data_criacao", sa.DateTime(timezone=True),
                  server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id_cobertura"),
        sa.ForeignKeyConstraint(["id_empresa"], ["empresa.id_empresa"]),
        sa.ForeignKeyConstraint(["id_usuario_admin_confirmacao"], ["usuario.id_usuario"]),
        sa.ForeignKeyConstraint(["id_usuario_admin_revogacao"], ["usuario.id_usuario"]),
        sa.UniqueConstraint("id_cobertura", "id_empresa", name="uq_cobertura_id_empresa"),
        sa.ForeignKeyConstraint(
            ["id_contrato", "id_empresa"],
            ["contrato.id_contrato", "contrato.id_empresa"],
            name="fk_cobertura_contrato_mesma_empresa",
        ),
        sa.CheckConstraint("periodo_fim >= periodo_inicio", name="ck_cobertura_periodo"),
        sa.CheckConstraint("length(trim(referencia_confirmacao)) > 0", name="ck_cobertura_referencia"),
        sa.CheckConstraint(
            "(revogada_em IS NULL AND revogacao_motivo IS NULL "
            "AND id_usuario_admin_revogacao IS NULL) OR "
            "(revogada_em IS NOT NULL AND revogacao_motivo IS NOT NULL "
            "AND id_usuario_admin_revogacao IS NOT NULL)",
            name="ck_cobertura_revogacao",
        ),
    )
    op.create_index("ix_cobertura_empresa", "cobertura_paga", ["id_empresa", "periodo_inicio"], unique=False)
    op.create_index("ix_cobertura_contrato", "cobertura_paga", ["id_contrato"], unique=False)

    op.create_table(
        "evento_contratual",
        sa.Column("id_evento", sa.Integer(), nullable=False),
        sa.Column("id_empresa", sa.Integer(), nullable=False),
        sa.Column("id_contrato", sa.Integer(), nullable=True),
        sa.Column("id_cobertura", sa.Integer(), nullable=True),
        sa.Column("tipo", sa.String(40), nullable=False),
        sa.Column("ocorrido_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("origem", sa.String(20), nullable=False),
        sa.Column("id_usuario_responsavel", sa.Integer(), nullable=True),
        sa.Column("situacao_anterior", sa.String(20), nullable=True),
        sa.Column("situacao_posterior", sa.String(20), nullable=True),
        sa.Column("justificativa", sa.Text(), nullable=True),
        sa.Column("detalhes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id_evento"),
        sa.ForeignKeyConstraint(["id_empresa"], ["empresa.id_empresa"]),
        sa.ForeignKeyConstraint(["id_usuario_responsavel"], ["usuario.id_usuario"]),
        sa.ForeignKeyConstraint(
            ["id_cobertura", "id_empresa"],
            ["cobertura_paga.id_cobertura", "cobertura_paga.id_empresa"],
            name="fk_evento_cobertura_mesma_empresa",
        ),
        sa.ForeignKeyConstraint(
            ["id_contrato", "id_empresa"],
            ["contrato.id_contrato", "contrato.id_empresa"],
            name="fk_evento_contrato_mesma_empresa",
        ),
        sa.CheckConstraint(
            "tipo IN ('CONTRATACAO', 'RENOVACAO', 'ALTERACAO_PLANO', 'SUSPENSAO', "
            "'PRORROGACAO', 'REATIVACAO', 'CANCELAMENTO', 'COBERTURA_CONFIRMADA', "
            "'COBERTURA_REVOGADA', 'REGRAS_ATIVADAS', 'REGRAS_DESATIVADAS')",
            name="ck_evento_tipo",
        ),
        sa.CheckConstraint(
            "(origem = 'ADMIN' AND id_usuario_responsavel IS NOT NULL) OR "
            "(origem = 'RECONCILIACAO' AND id_usuario_responsavel IS NULL)",
            name="ck_evento_origem",
        ),
    )
    op.create_index("ix_evento_empresa", "evento_contratual", ["id_empresa", "ocorrido_em"], unique=False)
    op.create_index("ix_evento_contrato", "evento_contratual", ["id_contrato"], unique=False)

    op.create_table(
        "historico_preco_plano",
        sa.Column("id_historico", sa.Integer(), nullable=False),
        sa.Column("id_plano", sa.Integer(), nullable=False),
        sa.Column("valor_anterior", sa.Numeric(12, 2), nullable=False),
        sa.Column("valor_novo", sa.Numeric(12, 2), nullable=False),
        sa.Column("alterado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("origem", sa.String(80), nullable=False),
        sa.PrimaryKeyConstraint("id_historico"),
        sa.ForeignKeyConstraint(["id_plano"], ["plano.id_plano"]),
        sa.CheckConstraint("valor_novo >= 0", name="ck_historico_preco_valor"),
    )
    op.create_index("ix_historico_preco_plano", "historico_preco_plano", ["id_plano", "alterado_em"], unique=False)


def downgrade():
    conexao = op.get_bind()
    com_dados = [
        tabela for tabela in _TABELAS
        if conexao.execute(sa.text(f"SELECT COUNT(*) FROM {tabela}")).scalar()
    ]
    if com_dados:
        raise RuntimeError(
            "Downgrade da gestão contratual recusado: há dados contratuais em "
            + ", ".join(com_dados)
            + ". Faça backup e decida a conciliação antes de remover as estruturas."
        )
    op.drop_index("ix_historico_preco_plano", table_name="historico_preco_plano")
    op.drop_table("historico_preco_plano")
    op.drop_index("ix_evento_contrato", table_name="evento_contratual")
    op.drop_index("ix_evento_empresa", table_name="evento_contratual")
    op.drop_table("evento_contratual")
    op.drop_index("ix_cobertura_contrato", table_name="cobertura_paga")
    op.drop_index("ix_cobertura_empresa", table_name="cobertura_paga")
    op.drop_table("cobertura_paga")
    op.drop_index("uq_contrato_aplicavel_empresa", table_name="contrato")
    op.drop_index("ix_contrato_empresa", table_name="contrato")
    op.drop_table("contrato")
    op.drop_table("regime_contratual")
