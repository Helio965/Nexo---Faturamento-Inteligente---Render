"""Instalação excepcional do NEXO; diagnóstico padrão não altera o banco.

Executar da raiz: python -m scripts.bootstrap_supabase diagnosticar
As etapas migrar/seed exigem NEXO_BOOTSTRAP_CONFIRMATION=PREPARAR_NEXO.
Nenhuma URI, credencial, parâmetro SQL ou exceção de driver é impressa.
"""

import argparse
import os
from pathlib import Path
import subprocess
import sys

from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from werkzeug.security import check_password_hash

from database_urls import DatabaseURLValidationError, parse_postgres_url, normalize_postgres_url

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "mgjdsbcohboxzcbicbuc"
POOLER = "aws-0-us-west-2.pooler.supabase.com"
PORTS = {"DATABASE_URL": 6543, "DIRECT_URL": 5432}
QUERY_OPTIONS = {"sslmode", "sslrootcert", "connect_timeout", "application_name"}


class BootstrapError(RuntimeError):
    """Somente mensagens constantes ou nomes de campos, nunca valores recebidos."""


def validate_urls(environment):
    urls, failures = {}, []
    for key, port in PORTS.items():
        try:
            url = parse_postgres_url(environment.get(key, ""))
        except DatabaseURLValidationError as exc:
            failures.append(f"{key}: {', '.join(exc.fields)}")
            continue
        checks = {
            "usuário do projeto": url.username == f"postgres.{PROJECT}",
            "host do pooler": url.host == POOLER,
            f"porta {port}": url.port == port,
            "banco postgres": url.database == "postgres",
            "senha real codificada": bool(url.password),
            "parâmetros de conexão permitidos": not (set(url.query) - QUERY_OPTIONS),
            "TLS obrigatório": url.query.get("sslmode") in ("require", "verify-ca", "verify-full"),
        }
        invalid = [name for name, valid in checks.items() if not valid]
        if invalid:
            failures.append(f"{key}: {', '.join(invalid)}")
        urls[key] = url
    if failures:
        raise BootstrapError("Campos inválidos: " + "; ".join(failures) + ". Nenhum dado foi modificado.")
    return urls


def migration_state():
    scripts = ScriptDirectory(str(ROOT / "migrations"))
    heads = scripts.get_heads()
    if len(heads) != 1:
        raise BootstrapError("O repositório precisa ter exatamente um head Alembic.")
    return heads[0], {revision.revision for revision in scripts.walk_revisions()}


def model_tables():
    import models  # registra os modelos sem inicializar a aplicação ou conectar
    from extensions import db
    return set(db.metadata.tables)


def validate_inventory(tables, revisions, *, required, known_revisions, head, complete=False):
    if tables - (required | {"alembic_version"}):
        raise BootstrapError("Há tabelas public fora das migrações NEXO; interrompido para proteger dados.")
    if tables and "alembic_version" not in tables:
        raise BootstrapError("Esquema public não vazio sem alembic_version; nenhuma adoção automática é permitida.")
    if len(revisions) > 1 or set(revisions) - known_revisions:
        raise BootstrapError("Revisão Alembic desconhecida ou múltipla; conferir o histórico antes de continuar.")
    if tables - {"alembic_version"} and not revisions:
        raise BootstrapError("Esquema existente sem revisão Alembic válida; interrompido para proteger dados.")
    if complete and (not required.issubset(tables) or revisions != [head]):
        raise BootstrapError("Tabelas ou head Alembic incompletos; preparação não validada.")


def validate_admin(row, password):
    if (row["role"] != "ADMIN" or not row["ativo"] or row["id_empresa"] is not None
            or not check_password_hash(row["senha_hash"], password)):
        raise BootstrapError("A conta configurada não é ADMIN ativo com a senha esperada; nenhuma conta foi alterada.")


def inspect_database(url, *, environment, complete=False, engine_factory=create_engine):
    head, known = migration_state()
    required = model_tables()
    engine = engine_factory(url, connect_args={"connect_timeout": 15}, poolclass=NullPool,
                            hide_parameters=True)
    try:
        with engine.connect() as connection:
            # A trava é do servidor; mesmo uma consulta alterada não pode gravar.
            connection.execute(text("SET TRANSACTION READ ONLY"))
            if not connection.connection.driver_connection.info.ssl_in_use:
                raise BootstrapError("A conexão não confirmou TLS; operação interrompida.")
            if connection.execute(text("SELECT current_database()")).scalar_one() != "postgres":
                raise BootstrapError("Banco efetivo diferente do banco esperado; operação interrompida.")
            tables = set(connection.execute(text(
                "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public'"
            )).scalars())
            revisions = list(connection.execute(text(
                "SELECT version_num FROM public.alembic_version"
            )).scalars()) if "alembic_version" in tables else []
            validate_inventory(tables, revisions, required=required, known_revisions=known,
                               head=head, complete=complete)
            if "usuario" in tables and environment.get("ADMIN_EMAIL") and environment.get("ADMIN_SENHA"):
                row = connection.execute(text(
                    "SELECT role, ativo, id_empresa, senha_hash FROM public.usuario WHERE email = :email"
                ), {"email": environment["ADMIN_EMAIL"]}).mappings().one_or_none()
                if row is not None:
                    validate_admin(row, environment["ADMIN_SENHA"])
                elif complete:
                    raise BootstrapError("Conta ADMIN configurada ausente; preparação não validada.")
            elif complete:
                raise BootstrapError("Credenciais de validação ADMIN ausentes; preparação não validada.")
            if complete:
                plans = set(connection.execute(text(
                    "SELECT nome_plano FROM public.plano WHERE ativo = true"
                )).scalars())
                if not {"BRONZE", "PRATA", "OURO"}.issubset(plans):
                    raise BootstrapError("Planos Bronze, Prata e Ouro ativos não foram confirmados.")
            return {"tables": len(tables), "revision": revisions[0] if revisions else "vazio"}
    finally:
        engine.dispose()


def preflight(environment, *, complete=False):
    urls = validate_urls(environment)  # valida AMBAS antes da primeira conexão
    states = {}
    for key in PORTS:
        states[key] = inspect_database(urls[key], environment=environment, complete=complete)
        print(f"{key}: projeto esperado, porta, TLS e consulta somente leitura confirmados.")
    if states["DATABASE_URL"] != states["DIRECT_URL"]:
        raise BootstrapError("As conexões runtime e de migração não confirmaram o mesmo estado do esquema.")
    state = states["DIRECT_URL"]
    print(f"Estado NEXO: {state['tables']} tabelas; revisão {state['revision']}.")
    return urls


def require_authorization(environment):
    if environment.get("NEXO_BOOTSTRAP_CONFIRMATION") != "PREPARAR_NEXO":
        raise BootstrapError("Etapa de escrita exige autorização explícita PREPARAR_NEXO.")
    if not environment.get("ADMIN_EMAIL") or not environment.get("ADMIN_SENHA"):
        raise BootstrapError("Credenciais ADMIN de instalação ausentes; nenhuma escrita iniciada.")


def run_official_command(arguments, environment, label):
    # CLI e seed oficiais: saída capturada, pois exceções externas podem conter DSN/dados.
    result = subprocess.run([sys.executable, *arguments], cwd=ROOT, env=environment,
                            capture_output=True, timeout=1200, check=False)
    if result.returncode:
        raise BootstrapError(f"{label} falhou; saída sensível omitida. Nenhuma etapa posterior foi executada.")
    print(f"{label} concluído.")


def execute(stage, environment):
    if stage not in {"diagnosticar", "migrar", "seed", "verificar"}:
        raise BootstrapError("Etapa de preparação inválida; nenhuma operação foi iniciada.")
    environment = {key: value for key, value in environment.items() if not key.startswith("PG")}
    # Evita arquivos de serviço/libpq e .env sobrepondo as conexões aprovadas.
    environment["PYTHON_DOTENV_DISABLED"] = "1"
    if stage in {"migrar", "seed"}:
        require_authorization(environment)
    urls = preflight(environment, complete=stage == "verificar")
    if stage in {"diagnosticar", "verificar"}:
        return
    for key in urls:
        environment[key] = normalize_postgres_url(environment[key])
    if stage == "migrar":
        environment["NEXO_DB_DIRECT"] = "1"
        run_official_command(["-m", "flask", "--app", "app:create_app", "db", "upgrade"],
                             environment, "flask db upgrade (migrações oficiais)")
    else:
        # Nunca executar seed em uma revisão intermediária ou esquema incompleto.
        head, _ = migration_state()
        state = inspect_database(urls["DIRECT_URL"], environment=environment)
        if state["revision"] != head or state["tables"] != len(model_tables()) + 1:
            raise BootstrapError("Seed exige todas as tabelas e o head oficial; nada foi populado.")
        environment["NEXO_DB_DIRECT"] = "0"
        run_official_command(["seed.py"], environment, "Seed oficial")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("diagnosticar", "migrar", "seed", "verificar"),
                        nargs="?", default="diagnosticar")
    args = parser.parse_args(argv)
    # libpq também lê variáveis do processo pai nas consultas do preflight.
    for key in list(os.environ):
        if key.startswith("PG"):
            os.environ.pop(key)
    try:
        execute(args.stage, os.environ)
    except BootstrapError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1
    except Exception:
        print("ERRO: falha de conexão ou execução; detalhes sensíveis omitidos. "
              "Conferir acesso, certificado e credenciais nos provedores.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
