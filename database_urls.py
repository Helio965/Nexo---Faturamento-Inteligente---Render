"""Parse PostgreSQL URLs without logging credentials or guessing passwords.

Passwords containing URL delimiters must be percent-encoded by the provider/user.
SQLAlchemy decodes them once and renders them once; quoting the whole URL, or
quoting a password a second time, changes the credential sent to PostgreSQL.
"""

import re
from urllib.parse import parse_qsl

from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError


_DRIVERS = {"postgres", "postgresql", "postgresql+psycopg2"}
_PRISMA_PARAMS = {"pgbouncer", "connection_limit", "pool_timeout", "schema"}
_DESTINATION_PARAMS = {
    "host", "hostaddr", "port", "dbname", "database", "user", "username",
    "password", "service", "servicefile", "passfile",
}
_TLS_MODES = {"require", "verify-ca", "verify-full"}
_BAD_PERCENT_ESCAPE = re.compile(r"%(?![0-9a-fA-F]{2})")
_PASSWORD_PLACEHOLDERS = {
    "[your-password]", "[your_password]", "your-password", "your_password",
    "<your-password>", "<your_password>", "[password]", "<password>",
    "[sua-senha]", "[sua_senha]", "sua_senha", "senha_aqui",
}


class DatabaseURLValidationError(ValueError):
    """A diagnostic containing field names only, never connection values."""

    def __init__(self, *fields):
        self.fields = tuple(dict.fromkeys(fields or ("formato da URL",)))
        super().__init__("URL PostgreSQL inválida: " + ", ".join(self.fields) + ".")


def parse_postgres_url(value: str) -> URL:
    """Return an explicit psycopg2 URL, rejecting ambiguous input safely.

    This validates syntax and transport options. Project, database, user and
    port authorization belong to the caller and must precede any connection.
    """
    if not isinstance(value, str) or not value:
        raise DatabaseURLValidationError("URL ausente")
    if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value):
        raise DatabaseURLValidationError("espaços ou caracteres de controle")
    if value[0] in "\"'" or value[-1] in "\"'":
        raise DatabaseURLValidationError("aspas externas")
    if _BAD_PERCENT_ESCAPE.search(value):
        raise DatabaseURLValidationError("codificação percentual")

    scheme, separator, remainder = value.partition("://")
    if not separator or scheme not in _DRIVERS:
        raise DatabaseURLValidationError("driver PostgreSQL")
    # Inspect only the authority here. urllib.urlsplit treats brackets in the
    # password as IPv6 syntax, and its exception can repeat a supplied value.
    authority = re.split(r"[/?#]", remainder, maxsplit=1)[0]
    if authority.count("@") > 1:
        raise DatabaseURLValidationError("codificação da senha")
    if "#" in remainder:
        raise DatabaseURLValidationError("fragmento # ou codificação da senha")
    if "@" in authority:
        userinfo, _, _ = authority.rpartition("@")
        _, has_password, password = userinfo.partition(":")
        if has_password and password.lower() in _PASSWORD_PLACEHOLDERS:
            raise DatabaseURLValidationError("senha real")
        if any(char in userinfo for char in "[]"):
            raise DatabaseURLValidationError("codificação da senha")
        if has_password and any(char in password for char in ":/?#@[]"):
            raise DatabaseURLValidationError("codificação da senha")
    elif ":" in authority and "@" in remainder[len(authority):]:
        # A slash or question mark in a password can move @ out of authority,
        # making a different hostname/port appear syntactically valid.
        raise DatabaseURLValidationError("codificação da senha")

    try:
        parsed = make_url(value)
    except (ArgumentError, ValueError, TypeError):
        raise DatabaseURLValidationError("formato da URL ou porta") from None
    if parsed.password and parsed.password.lower() in _PASSWORD_PLACEHOLDERS:
        raise DatabaseURLValidationError("senha real")
    if any(ord(char) < 32 or ord(char) == 127
           for char in (parsed.username or "") + (parsed.password or "")):
        raise DatabaseURLValidationError("caracteres de controle")

    # libpq accepts options that replace the destination in the authority.
    # Checking only URL.host would authorize the wrong server with these set.
    options = {}
    seen = set()
    # SQLAlchemy drops empty query values. Preserve them here so that
    # sslmode= cannot silently become the secure default and pass validation.
    raw_query = remainder.partition("?")[2]
    for key, option in parse_qsl(raw_query, keep_blank_values=True):
        lowered = key.lower()
        if lowered in seen:
            raise DatabaseURLValidationError("parâmetros duplicados")
        seen.add(lowered)
        if any(ord(char) < 32 or ord(char) == 127 for char in key + option):
            raise DatabaseURLValidationError("caracteres de controle")
        options[lowered] = option

    # SQLAlchemy's documented Unix-socket form has no authority destination:
    # postgresql://user@/db?host=/absolute/socket/directory&port=5432
    # In that form host supplies the sole destination rather than replacing a
    # checked authority host. Keep network hosts and multihost lists forbidden.
    socket_directory = options.get("host", "")
    socket_port = options.get("port")
    unix_socket = (
        not parsed.host and parsed.port is None
        and socket_directory.startswith("/") and "," not in socket_directory
        and (socket_port is None or (
            re.fullmatch(r"[0-9]{1,5}", socket_port) is not None
            and 1 <= int(socket_port) <= 65535
        ))
    )
    query = {}
    for lowered, option in options.items():
        if lowered in _DESTINATION_PARAMS and not (
            unix_socket and lowered in {"host", "port"}
        ):
            raise DatabaseURLValidationError("parâmetros de destino")
        if lowered.startswith("ssl") and lowered not in {"sslmode", "sslrootcert"}:
            raise DatabaseURLValidationError("parâmetros TLS")
        if lowered == "sslmode" and option not in _TLS_MODES:
            raise DatabaseURLValidationError("sslmode seguro")
        if lowered in {"sslmode", "sslrootcert"} and not option:
            raise DatabaseURLValidationError("parâmetros TLS vazios")
        if lowered in _PRISMA_PARAMS:
            continue
        query[lowered] = option

    host = (parsed.host or "").lower()
    if host.endswith((".supabase.com", ".supabase.co")) and "sslmode" not in query:
        query["sslmode"] = "require"
    return parsed.set(drivername="postgresql+psycopg2", query=query)


def normalize_postgres_url(value: str) -> str:
    """Return a connection URL; callers must never log the returned string."""
    # SQLAlchemy renders a decoded password space literally. Keep it encoded
    # so the normalized URL remains unambiguous and passes the same parser.
    return parse_postgres_url(value).render_as_string(hide_password=False).replace(" ", "%20")
