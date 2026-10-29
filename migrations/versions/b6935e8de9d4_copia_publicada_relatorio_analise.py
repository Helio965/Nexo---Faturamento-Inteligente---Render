"""SEC-003: cópia publicada da devolutiva, separada do rascunho em edição.

Revision ID: b6935e8de9d4
Revises: d3f635a14ef3

Somente colunas novas e anuláveis em relatorio_analise (expand), mais
versao_rascunho com default no servidor. Nenhuma linha é reescrita: os
relatórios já publicados continuam sendo lidos pelo rascunho (legado) até a
primeira edição administrativa, que congela o texto vigente antes de
alterá-lo (models.RelatorioAnalise.preservar_publicacao_legada). Não há
migração de dados em massa nesta etapa.

Downgrade: remove as colunas. O texto publicado que só existia na cópia
(editado após a publicação sem republicar) é perdido; por isso o downgrade
só deve ser executado com backup.
"""

from alembic import op
import sqlalchemy as sa


revision = "b6935e8de9d4"
down_revision = "d3f635a14ef3"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("relatorio_analise", schema=None) as batch_op:
        batch_op.add_column(sa.Column("titulo_publicado", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("resumo_executivo_publicado", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("conclusao_estrategica_publicada", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("gerado_por_ia_publicado", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column(
            "versao_rascunho", sa.Integer(), server_default="1", nullable=False,
        ))


def downgrade():
    with op.batch_alter_table("relatorio_analise", schema=None) as batch_op:
        batch_op.drop_column("versao_rascunho")
        batch_op.drop_column("gerado_por_ia_publicado")
        batch_op.drop_column("conclusao_estrategica_publicada")
        batch_op.drop_column("resumo_executivo_publicado")
        batch_op.drop_column("titulo_publicado")
