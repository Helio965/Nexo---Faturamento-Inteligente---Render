"""Extensão editorial e mídias do Guia, sem alterar os tópicos legados.

Revision ID: c3e08eb3863a
Revises: 5a9c3e7d1b42
Create Date: 2026-11-14 19:54:02.727686

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3e08eb3863a'
down_revision = '5a9c3e7d1b42'
branch_labels = None
depends_on = None

_TABELAS = ("guia_edicao", "guia_midia")

# Nenhum acesso pela Data API: o servidor Flask aplica suas próprias permissões.
# Os papéis são opcionais no PostgreSQL descartável e existentes no Supabase.
_POLITICAS_POSTGRESQL = """
DO $$
DECLARE
    tabela text;
    papel text;
    papeis_api text;
    papeis_servidor text;
BEGIN
    SELECT string_agg(quote_ident(rolname), ', ' ORDER BY rolname) INTO papeis_api
      FROM pg_roles WHERE rolname IN ('anon', 'authenticated');
    SELECT string_agg(quote_ident(rolname), ', ' ORDER BY rolname) INTO papeis_servidor
      FROM pg_roles WHERE rolname IN ('postgres', 'service_role');
    FOREACH tabela IN ARRAY ARRAY['guia_edicao', 'guia_midia'] LOOP
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
    REVOKE ALL ON SEQUENCE guia_midia_id_seq FROM PUBLIC;
    FOR papel IN SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated') LOOP
        EXECUTE 'REVOKE ALL ON SEQUENCE guia_midia_id_seq FROM ' || quote_ident(papel);
    END LOOP;
END
$$;
"""


def upgrade():
    op.create_table(
        "guia_edicao",
        sa.Column("id_topico", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("descricao", sa.String(500), server_default=sa.text("''"), nullable=False),
        sa.Column("ordem", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("blocos", sa.JSON(), server_default=sa.text("'[]'"), nullable=True),
        sa.Column("historico", sa.JSON(), server_default=sa.text("'[]'"), nullable=True),
        sa.Column("publicado_em", sa.DateTime(), nullable=True),
        sa.Column("excluido_em", sa.DateTime(), nullable=True),
        sa.Column("versao", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint("ordem BETWEEN 0 AND 9999", name="ck_guia_edicao_ordem"),
        sa.CheckConstraint("versao > 0", name="ck_guia_edicao_versao"),
        sa.ForeignKeyConstraint(["id_topico"], ["guia_topico.id"], ondelete="CASCADE",
                                name="fk_guia_edicao_topico"),
        sa.PrimaryKeyConstraint("id_topico"),
    )
    op.create_index("ix_guia_edicao_ordem", "guia_edicao", ["ordem", "id_topico"])
    op.create_table(
        "guia_midia",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("id_topico", sa.Integer(), nullable=False),
        sa.Column("referencia", sa.String(255), nullable=False),
        sa.Column("tipo", sa.String(10), nullable=False),
        sa.Column("legenda", sa.String(500), server_default=sa.text("''"), nullable=False),
        sa.Column("alt", sa.String(240), server_default=sa.text("''"), nullable=False),
        sa.Column("data_criacao", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("tipo IN ('imagem', 'video')", name="ck_guia_midia_tipo"),
        sa.CheckConstraint("length(referencia) > 0", name="ck_guia_midia_referencia"),
        sa.ForeignKeyConstraint(["id_topico"], ["guia_topico.id"], ondelete="CASCADE",
                                name="fk_guia_midia_topico"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_guia_midia_topico", "guia_midia", ["id_topico"])
    op.create_index("ix_guia_midia_referencia", "guia_midia", ["referencia"])
    if op.get_bind().dialect.name == "postgresql":
        for tabela in _TABELAS:
            op.execute(f"ALTER TABLE {tabela} ENABLE ROW LEVEL SECURITY")
            op.execute(f"REVOKE ALL ON TABLE {tabela} FROM PUBLIC")
        op.execute(_POLITICAS_POSTGRESQL)


def downgrade():
    conexao = op.get_bind()
    if conexao.dialect.name == "postgresql":
        # Impede gravação concorrente entre a verificação e o DROP. Os dados
        # editoriais e suas referências de mídia só podem ser descartados à parte,
        # após backup e autorização do operador.
        op.execute("LOCK TABLE guia_topico, guia_edicao, guia_midia IN ACCESS EXCLUSIVE MODE")
    if any(conexao.execute(sa.text(f"SELECT COUNT(*) FROM {t}")).scalar() for t in _TABELAS):
        raise RuntimeError("Reversão do Guia recusada: preserve os dados editoriais e mídias antes de remover o esquema.")
    op.drop_table("guia_midia")
    op.drop_table("guia_edicao")
