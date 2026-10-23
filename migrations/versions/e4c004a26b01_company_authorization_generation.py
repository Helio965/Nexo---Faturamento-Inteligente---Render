"""SEC-004: geração persistente de autorização e lixeira legada conservadora.

Revision ID: e4c004a26b01
Revises: b7c4e2a9f031

Executar somente em janela de implantação revisada, com os escritores antigos
parados. O código anterior sobrescrevia ``ativo`` durante exclusão/restauração;
não existe evidência confiável para recuperar esses estados retroativamente.

O downgrade remove a geração, mas NÃO reativa contas legadas. Ele perde o
histórico de revogação e exige suspensão do tráfego e invalidação de sessões e
tokens antes de qualquer código anterior voltar a atender. Não é rollback de
segurança automático nem deve ser executado pelo build.
"""

from alembic import op
import sqlalchemy as sa


revision = "e4c004a26b01"
down_revision = "b7c4e2a9f031"
branch_labels = None
depends_on = None


def upgrade():
    # CHECK na própria coluna permite ADD COLUMN em SQLite e PostgreSQL sem
    # reconstruir usuario nem perder constraints/FKs de tabelas dependentes.
    op.add_column(
        "usuario",
        sa.Column(
            "geracao_autorizacao",
            sa.Integer(),
            sa.CheckConstraint(
                "geracao_autorizacao >= 0",
                name="ck_usuario_geracao_autorizacao",
            ),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    empresa = sa.table(
        "empresa",
        sa.column("id_empresa", sa.Integer()),
        sa.column("deletado_em", sa.DateTime()),
    )
    usuario = sa.table(
        "usuario",
        sa.column("id_empresa", sa.Integer()),
        sa.column("role", sa.String()),
        sa.column("ativo", sa.Boolean()),
        sa.column("geracao_autorizacao", sa.Integer()),
    )
    # Abrange inclusive inconsistências ativo=True em empresas já excluídas;
    # nenhuma data, senha ou flag atual comprova o estado anterior à lixeira.
    op.execute(
        usuario.update()
        .where(
            usuario.c.role == "CLIENTE",
            usuario.c.id_empresa.in_(
                sa.select(empresa.c.id_empresa).where(
                    empresa.c.deletado_em.is_not(None),
                ),
            ),
        )
        .values(ativo=False, geracao_autorizacao=1)
    )


def downgrade():
    # DROP COLUMN remove também o CHECK dependente nos dois bancos suportados.
    # Não inventar estado anterior nem desfazer o bloqueio conservador legado.
    op.drop_column("usuario", "geracao_autorizacao")
