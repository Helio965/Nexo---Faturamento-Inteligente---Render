"""arquivo_armazenado: conteúdo dos uploads guardado no Postgres

Revision ID: b7c4e2a9f031
Revises: a3f1c9b27d04
Create Date: 2026-09-22

Cria a tabela `arquivo_armazenado`, onde storage.py passa a gravar os bytes
das planilhas (VENDAS/COMPRAS) e das imagens do Guia. Motivo: no deploy em
host gratuito (Render Free) o disco é efêmero e os arquivos gravados no
filesystem somem a cada deploy/restart/hibernação. Migração puramente
aditiva: nenhuma tabela existente é alterada.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b7c4e2a9f031"
down_revision = "a3f1c9b27d04"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "arquivo_armazenado",
        sa.Column("chave", sa.String(length=255), nullable=False),
        sa.Column("conteudo", sa.LargeBinary(), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("tamanho", sa.Integer(), nullable=False),
        sa.Column("data_criacao", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("chave"),
    )


def downgrade():
    # Mesma guarda da 81287c74387a: a tabela guarda as planilhas e as imagens
    # do Guia; removê-la com dados deixaria referências 'db:' pendentes.
    conexao = op.get_bind()
    if conexao.execute(sa.text("SELECT COUNT(*) FROM arquivo_armazenado")).scalar():
        raise RuntimeError(
            "Downgrade recusado: arquivo_armazenado contém arquivos (uploads e imagens do "
            "Guia). Exporte-os para o disco e troque as referências 'db:' antes de remover a tabela."
        )
    op.drop_table("arquivo_armazenado")
