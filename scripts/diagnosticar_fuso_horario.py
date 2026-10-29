"""Diagnóstico somente leitura do fuso horário do banco (suporte e sininho).

Antes de publicar a correção dos horários, responde se os registros antigos de
chamado_suporte, mensagem_suporte e notificacao estão no relógio UTC, que é a
convenção do código corrigido (horario.py). Essas colunas são `timestamp
without time zone`: o código anterior gravava nelas o relógio do TimeZone da
sessão do banco, tanto pelo CURRENT_TIMESTAMP quanto pelos datetime com fuso.

Usa só a URL da aplicação (DATABASE_URL, resolvida como em config.py). As
variáveis PG* do terminal são ignoradas: PGTZ ou PGOPTIONS mudariam o fuso da
sessão do script, e PGHOST ou PGSERVICE o banco consultado, sem mudar o que a
aplicação recebe. Só lê: a transação é READ ONLY e é desfeita no fim. Não
altera dados, esquema nem configuração, e não exibe a senha nem a mensagem de
erro do driver.

    python scripts/diagnosticar_fuso_horario.py

Saída: JSON com o banco e o usuário consultados, o TimeZone da sessão e a
origem dessa configuração (pg_settings.source), o relógio do banco, os tipos
das cinco colunas e o veredito. Código de saída: 0 compatível; 1 verificar
antes de publicar; 2 diagnóstico não executado ou inconclusivo.
"""

import json
import os
from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parents[1]
COLUNAS = (
    ("chamado_suporte", "data_abertura"), ("chamado_suporte", "data_atualizacao"),
    ("chamado_suporte", "data_fechamento"), ("mensagem_suporte", "data_envio"),
    ("notificacao", "data_criacao"),
)
TIPO_ESPERADO = "timestamp without time zone"
# Nomes IANA que são o próprio UTC (o PostgreSQL aceita todos).
FUSOS_UTC = {
    "utc", "etc/utc", "uct", "etc/uct", "universal", "etc/universal", "zulu", "etc/zulu",
    "gmt", "etc/gmt", "gmt0", "etc/gmt0", "etc/gmt+0", "etc/gmt-0", "greenwich", "etc/greenwich",
}


def diagnosticar(conexao) -> dict:
    """Consultas de leitura numa conexão psycopg2 já aberta; desfaz a transação."""
    try:
        with conexao.cursor() as cursor:
            cursor.execute("SET TRANSACTION READ ONLY")
            cursor.execute("SHOW transaction_read_only")
            somente_leitura = cursor.fetchone()[0] == "on"
            cursor.execute("SELECT current_database(), current_user")
            banco, usuario = cursor.fetchone()
            cursor.execute("SELECT current_setting('TimeZone'), source FROM pg_settings WHERE name = 'TimeZone'")
            fuso, origem = cursor.fetchone()
            cursor.execute(
                "SELECT now()::text, (now() AT TIME ZONE 'UTC')::text, LOCALTIMESTAMP::text, "
                "EXTRACT(TIMEZONE FROM now())::int"
            )
            agora, agora_utc, relogio_da_sessao, deslocamento = cursor.fetchone()
            cursor.execute(
                "SELECT table_name, column_name, data_type FROM information_schema.columns "
                "WHERE table_schema = current_schema() AND (table_name, column_name) IN %s ORDER BY 1, 2",
                (COLUNAS,),
            )
            tipos = {f"{tabela}.{coluna}": tipo for tabela, coluna, tipo in cursor.fetchall()}
    finally:
        conexao.rollback()
    esquema_ok = len(tipos) == len(COLUNAS) and set(tipos.values()) == {TIPO_ESPERADO}
    sessao_utc = fuso.lower() in FUSOS_UTC and deslocamento == 0
    if not esquema_ok:
        situacao = "inconclusivo"
        veredito = ("Inconclusivo: o banco consultado não tem as cinco colunas do suporte e do sininho como "
                    f"{TIPO_ESPERADO} (encontradas: {len(tipos)}). Confira se a DATABASE_URL é a da aplicação.")
    elif sessao_utc:
        situacao = "compativel"
        veredito = ("Sessão em UTC: se esta configuração já valia quando os registros antigos foram gravados, "
                    "eles estão no relógio UTC, a mesma convenção do código corrigido, e nenhuma migração de "
                    "dados é necessária.")
    else:
        situacao = "verificar"
        veredito = (f"ATENÇÃO: a sessão usa {fuso} (origem: {origem}). Se esta configuração já valia "
                    "quando os registros antigos foram gravados, eles estão no relógio desse fuso, e "
                    "não em UTC. Não publique a correção antes de decidir o tratamento desses registros.")
    return {
        "banco": banco, "usuario": usuario,
        "timezone_da_sessao": fuso, "origem_da_configuracao": origem,
        "agora_banco": agora, "agora_utc": agora_utc, "relogio_da_sessao": relogio_da_sessao,
        "deslocamento_segundos": deslocamento, "tipos_das_colunas": tipos,
        "transacao_somente_leitura": somente_leitura,
        "situacao": situacao, "compativel": situacao == "compativel", "veredito": veredito,
    }


def main() -> int:
    # Só a URL da aplicação define o alvo e a sessão (ver docstring).
    for chave in [k for k in os.environ if k.upper().startswith("PG")]:
        del os.environ[chave]
    engine = None
    try:
        sys.path.insert(0, str(RAIZ))
        from sqlalchemy import create_engine
        from sqlalchemy.pool import NullPool
        from config import _resolve_database_uri  # a mesma resolução de URL da aplicação

        uri = _resolve_database_uri()
        if not uri.startswith("postgresql"):
            print(json.dumps({"erro": "DATABASE_URL não aponta para PostgreSQL; nada foi consultado."},
                             ensure_ascii=False))
            return 2
        engine = create_engine(uri, poolclass=NullPool)
        conexao = engine.raw_connection()
        try:
            resultado = diagnosticar(conexao.dbapi_connection)
        finally:
            conexao.close()
    except Exception as erro:  # noqa: BLE001 - a URL e a mensagem do driver podem conter a senha
        print(json.dumps({"erro": f"Diagnóstico não executado ({type(erro).__name__})."}, ensure_ascii=False))
        return 2
    finally:
        if engine is not None:
            engine.dispose()
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return {"compativel": 0, "verificar": 1}.get(resultado["situacao"], 2)


if __name__ == "__main__":
    sys.exit(main())
