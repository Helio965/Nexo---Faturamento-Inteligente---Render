"""SEC-001: sessões registradas no servidor (sessao_autenticada).

Revision ID: d3f635a14ef3
Revises: 81287c74387a

Somente uma tabela nova (expand). Nenhuma linha existente é alterada e
nenhum dado real é migrado: as sessões passam a ser registradas a partir do
primeiro login após a implantação. Como a aplicação só autoriza cookies com
linha registrada, todo usuário faz um novo login após o deploy (o BOOT_ID já
impunha isso a cada reinício).

Ordem de implantação: aplicar esta migração ANTES de publicar o código que a
usa (o login grava na tabela). O downgrade apenas remove a tabela: sessões
são estado transitório e a única consequência é um novo login.
"""

from alembic import op
import sqlalchemy as sa


revision = "d3f635a14ef3"
down_revision = "81287c74387a"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sessao_autenticada",
        sa.Column("id_sessao", sa.Integer(), nullable=False),
        sa.Column("id_usuario", sa.Integer(), nullable=False),
        sa.Column("identificador_hash", sa.String(64), nullable=False),
        sa.Column("criada_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revogada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_revogacao", sa.String(40), nullable=True),
        sa.PrimaryKeyConstraint("id_sessao"),
        sa.ForeignKeyConstraint(["id_usuario"], ["usuario.id_usuario"], ondelete="CASCADE"),
        sa.UniqueConstraint("identificador_hash", name="uq_sessao_identificador"),
        sa.CheckConstraint("expira_em > criada_em", name="ck_sessao_validade"),
        sa.CheckConstraint(
            "(revogada_em IS NULL AND motivo_revogacao IS NULL) OR "
            "(revogada_em IS NOT NULL AND motivo_revogacao IS NOT NULL)",
            name="ck_sessao_revogacao",
        ),
    )
    op.create_index("ix_sessao_usuario", "sessao_autenticada", ["id_usuario"], unique=False)


def downgrade():
    op.drop_index("ix_sessao_usuario", table_name="sessao_autenticada")
    op.drop_table("sessao_autenticada")
