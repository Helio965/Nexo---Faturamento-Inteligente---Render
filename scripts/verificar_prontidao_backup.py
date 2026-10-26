"""Verificações locais de prontidão; nunca conecta, grava ou restaura bancos.

Não importa a aplicação nem carrega .env. A inspeção opcional executa somente
``pg_restore --list``; sua saída pode conter metadados privados e é descartada.
"""

import argparse
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys


TOOLS = ("pg_dump", "pg_restore", "psql")
TIMEOUT_SECONDS = 15


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, _message):
        # argparse normalmente reproduz valores/argumentos potencialmente secretos.
        self.print_usage(sys.stderr)
        self.exit(2, "Erro: argumentos inválidos; consulte --help.\n")


def child_environment():
    """Não repassa credenciais, serviços ou parâmetros libpq do ambiente."""
    allowed = {
        "PATH", "SYSTEMROOT", "WINDIR", "PATHEXT", "TEMP", "TMP",
        "LANG", "LC_ALL", "LANGUAGE", "TZ",
    }
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    env.update(PGPASSFILE=os.devnull, PGSERVICEFILE=os.devnull, PGCONNECT_TIMEOUT="1")
    return env


def locate_tool(name):
    """Procura só em diretórios absolutos do PATH; no Windows, apenas ``.exe``.

    ``shutil.which`` no Windows consulta antes o diretório atual e aceita
    .bat/.cmd, que repassariam os argumentos ao cmd.exe. ``os.path.isabs``
    (Python 3.12) aceita ``/dir`` sem unidade no Windows; ``Path`` não.
    """
    filename = name + ".exe" if os.name == "nt" else name
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        if Path(directory).is_absolute():
            candidate = os.path.join(directory, filename)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
    return None


def run_local_command(arguments, stdin=subprocess.DEVNULL):
    """Executa apenas comandos construídos internamente; nunca mostra saída bruta."""
    try:
        result = subprocess.run(
            arguments, shell=False, check=False, stdin=stdin,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=TIMEOUT_SECONDS, env=child_environment(),
        )
    except subprocess.TimeoutExpired:
        return "tempo limite excedido"
    except OSError:
        return "não foi possível executar"
    return None if result.returncode == 0 else "execução recusada ou inválida"


def inspect_backup(filename, expected_sha256):
    """Lê um arquivo local sem alterá-lo; cabeçalho não valida um dump completo."""
    digest = hashlib.sha256()
    try:
        path = Path(filename).resolve(strict=True)
        if not path.is_file():
            raise OSError("arquivo regular obrigatório")
        with path.open("rb") as backup:
            header = backup.read(6)
            digest.update(header)
            for chunk in iter(lambda: backup.read(1024 * 1024), b""):
                digest.update(chunk)
    except (OSError, ValueError, RuntimeError):
        print("Backup: arquivo ausente, inacessível ou ilegível.")
        return None
    if len(header) < 6 or header[:5] != b"PGDMP":
        print("Backup: cabeçalho customizado ausente ou truncado.")
        return None
    checksum = digest.hexdigest()
    print("Backup: cabeçalho PGDMP detectado; conteúdo ainda não validado.")
    print("SHA-256 calculado: " + checksum)
    if expected_sha256 is None:
        print("SHA-256: sem referência externa para comparação.")
    elif checksum != expected_sha256.lower():
        print("SHA-256: divergente da referência; interrompa o uso deste arquivo.")
        return None
    else:
        print("SHA-256: coincide com a referência fornecida.")
    return path


def cli(argv=None):
    parser = SafeArgumentParser(
        description="Verifica ferramentas e um backup local, sem conexão com bancos.",
        allow_abbrev=False,
        epilog=("Códigos: 0 verificações solicitadas concluídas; 1 arquivo/integridade/"
                "listagem inválida; 2 argumentos inválidos; 3 ferramentas indisponíveis. "
                "Nenhuma verificação substitui um teste de restauração isolado."),
    )
    parser.add_argument("--dry-run", action="store_true", help="Não executa subprocessos; pode ler o backup e calcular SHA-256.")
    parser.add_argument("--backup", metavar="ARQUIVO", help="Arquivo PostgreSQL customizado local, somente leitura.")
    parser.add_argument("--sha256", metavar="HASH", help="SHA-256 esperado, com 64 caracteres hexadecimais.")
    parser.add_argument("--list", action="store_true", dest="list_backup", help="Inspeciona o catálogo com pg_restore --list; descarta metadados da saída.")
    args = parser.parse_args(argv)
    if args.sha256 is not None and not re.fullmatch(r"[0-9a-fA-F]{64}", args.sha256):
        parser.error("hash inválido")
    if (args.sha256 is not None or args.list_backup) and args.backup is None:
        parser.error("backup obrigatório")

    print("Modo seguro: sem conexão, escrita ou restauração de banco.")
    executables = {}
    unavailable = False
    for name in TOOLS:
        executable = locate_tool(name)
        executables[name] = executable
        if executable is None:
            print(name + ": indisponível no PATH.")
            unavailable = True
        elif args.dry_run:
            print(name + ": localizado; --version não executado (--dry-run).")
        else:
            error = run_local_command([executable, "--version"])
            if error:
                print(name + ": " + error + ".")
                executables[name] = None
                unavailable = True
            else:
                print(name + ": disponível (--version concluído).")

    if args.backup is not None:
        path = inspect_backup(args.backup, args.sha256)
        if path is None:
            return 1
        if args.list_backup:
            if args.dry_run:
                print("Catálogo: não inspecionado (--dry-run).")
            elif executables["pg_restore"] is None:
                print("Catálogo: pg_restore indisponível; inspeção pendente.")
                return 3
            else:
                # Reabre o caminho já resolvido e entrega o conteúdo pela entrada
                # padrão, pois no Windows o argv passa pela página ANSI e pode
                # indicar outro arquivo. Troca concorrente após o hash não é detectada.
                try:
                    with path.open("rb", buffering=0) as archive:
                        error = run_local_command([executables["pg_restore"], "--list"], stdin=archive)
                except OSError:
                    error = "não foi possível executar"
                if error:
                    print("Catálogo: " + error + "; backup não validado.")
                    return 1
                print("Catálogo: pg_restore --list concluído; metadados não exibidos.")
    print("Restauração: não executada; validação operacional permanece pendente.")
    return 3 if unavailable else 0


if __name__ == "__main__":
    raise SystemExit(cli())
