"""PostgreSQL descartável dos testes; nunca aceita URL ou servidor existente."""

import os
from pathlib import Path
import secrets
import subprocess
import tempfile
from unittest.mock import patch

import psycopg2
from psycopg2 import sql
from sqlalchemy import URL

from . import test_backup_restore as backup_support


class PrivatePostgreSQL:
    """Cluster exclusivo, socket Unix privado e nenhuma interface TCP.

    O único parâmetro externo é um diretório de binários locais. Cada cluster
    usa seu próprio usuário e diretório temporário 0700, sem credenciais reais.
    O ambiente dos utilitários não herda configurações libpq nem serviços.
    """

    def __init__(self):
        raw = os.environ.get("NEXO_TEST_POSTGRES_BIN", "")
        if not raw:
            raise RuntimeError("Defina NEXO_TEST_POSTGRES_BIN para executar a suíte PostgreSQL obrigatória.")
        if "://" in raw or not Path(raw).is_absolute():
            raise RuntimeError("NEXO_TEST_POSTGRES_BIN exige um diretório local absoluto; valor omitido.")
        try:
            self.bin_dir = Path(raw).resolve(strict=True)
        except (OSError, ValueError):
            raise RuntimeError("Diretório de binários PostgreSQL indisponível; valor omitido.") from None
        if os.name != "posix" or not all((self.bin_dir / name).is_file() for name in ("initdb", "pg_ctl")):
            raise RuntimeError("A suíte exige POSIX e binários locais initdb/pg_ctl.")
        self.environment = backup_support._safe_environment()
        self.environment["PATH"] = str(self.bin_dir) + os.pathsep + self.environment.get("PATH", "")
        # A libpq também lê PGHOSTADDR/PGSERVICE antes de abrir conexões.
        # Manter o ambiente filtrado por toda a vida do cluster protege tanto
        # psycopg2 direto como conexões abertas pelo pool SQLAlchemy nas threads.
        # Este helper pertence somente ao processo dedicado dos testes PG.
        self.environment_guard = patch.dict(os.environ, self.environment, clear=True)
        self.environment_guard.start()
        self.work = tempfile.TemporaryDirectory(prefix="nexo-pg-security-")
        self.root = Path(self.work.name).resolve()
        self.root.chmod(0o700)
        self.data = self.root / "cluster"
        self.socket = self.root / "socket"
        self.socket.mkdir(mode=0o700)
        self.passfile = self.root / "empty-pgpass"
        self.passfile.touch(mode=0o600)
        self.username = "nexo_security_" + secrets.token_hex(6)
        self.port = 5432  # Só identifica o socket dentro do diretório exclusivo.
        try:
            self._command("initdb", "-D", self.data, "--username", self.username,
                          "--auth-local=trust", "--auth-host=reject", "--no-locale", "--encoding=UTF8")
            options = (
                f"-k {self.socket} -p {self.port} -c listen_addresses='' "
                "-c unix_socket_permissions=0700 -c log_statement=none "
                "-c log_min_error_statement=panic"
            )
            self._command("pg_ctl", "-D", self.data, "-l", self.root / "server.log",
                          "-w", "-t", "30", "-o", options, "start")
            connection = self.connect()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT inet_server_addr(), current_user, current_setting('transaction_isolation')")
                    address, user, isolation = cursor.fetchone()
                    if address is not None or user != self.username or isolation != "read committed":
                        raise RuntimeError("O PostgreSQL privado não confirmou socket exclusivo/READ COMMITTED.")
            finally:
                connection.close()
        except BaseException:
            self.close()
            raise

    def _command(self, name, *arguments):
        try:
            result = subprocess.run(
                [str(self.bin_dir / name), *map(str, arguments)],
                cwd=self.root, env=self.environment, stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=45, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            raise RuntimeError("Utilitário PostgreSQL privado indisponível ou excedeu o prazo; saída omitida.") from None
        if result.returncode:
            raise RuntimeError("Utilitário PostgreSQL privado falhou; saída omitida.")

    def connect(self, database="postgres"):
        # Todos os parâmetros libpq são explícitos. Nenhuma conexão externa,
        # DATABASE_URL, DIRECT_URL, PGSERVICE ou arquivo de senha é utilizado.
        return psycopg2.connect(
            dbname=database, user=self.username, host=str(self.socket),
            port=self.port, connect_timeout=5, password="", passfile=str(self.passfile),
            options="-c statement_timeout=15000 -c lock_timeout=10000",
        )

    def create_database(self):
        name = "nexo_security_test_" + secrets.token_hex(8)
        connection = self.connect()
        try:
            connection.autocommit = True
            with connection.cursor() as cursor:
                cursor.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0 ENCODING 'UTF8'").format(sql.Identifier(name)))
        finally:
            connection.close()
        return name

    def drop_database(self, name):
        if not name.startswith("nexo_security_test_"):
            raise RuntimeError("Recusa de remoção de banco fora do namespace privado.")
        connection = self.connect()
        try:
            connection.autocommit = True
            with connection.cursor() as cursor:
                cursor.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
        finally:
            connection.close()

    def url(self, database):
        if not database.startswith("nexo_security_test_"):
            raise RuntimeError("Banco fora do namespace exclusivo de teste.")
        return URL.create("postgresql+psycopg2", username=self.username,
                          host=str(self.socket), port=self.port, database=database)

    def close(self):
        try:
            if (self.data / "postmaster.pid").exists():
                self._command("pg_ctl", "-D", self.data, "-m", "fast", "-w", "-t", "30", "stop")
        finally:
            try:
                self.work.cleanup()
            finally:
                self.environment_guard.stop()
