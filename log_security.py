"""Remove bearer tokens de URLs dos registros Python controlados pela aplicação.

Não substitui o mascaramento no proxy/Render, nem remove segredos arbitrários
de campos extras de ferramentas externas de observabilidade.
"""

import logging
import re
import traceback


def _url_literal(path):
    # O access log pode conservar escapes percentuais do request target.
    return "".join(f"(?:{re.escape(char)}|%{ord(char):02x})" for char in path)


_TOKEN_PATH = re.compile(
    "(" + "|".join(_url_literal(path) for path in (
        "/auth/resetar-senha/", "/auth/primeiro-acesso/",
    )) + r")[^/\s?\"'<>#]+",
    re.IGNORECASE,
)
# Tokens temporizados ItsDangerous (também a forma compactada com ponto inicial).
# É uma defesa conservadora para exceções que contenham somente o bearer. Não
# pretende reconhecer qualquer segredo ou garantir sigilo de payloads externos.
_SIGNED_TOKEN = re.compile(
    r"(?<![A-Za-z0-9_.-])\.?[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}"
    r"\.[A-Za-z0-9_-]{20,}(?![A-Za-z0-9_.-])",
)


def _redact(text):
    return _SIGNED_TOKEN.sub("[REDACTED]", _TOKEN_PATH.sub(r"\1[REDACTED]", text))


def _sanitize_record(record):
    # Renderizar somente quando há algo a mascarar preserva os argumentos e a
    # formatação dos demais logs (inclusive o mapping SafeAtoms do Gunicorn).
    try:
        message = record.getMessage()
    except Exception:  # noqa: BLE001
        # Não deixar um formato inválido derrubar a request nem fazer o logging
        # imprimir os argumentos brutos em seu diagnóstico de erro.
        record.msg = "Registro de log com formatação inválida."
        record.args = ()
        message = record.msg
    sanitized = _redact(message)
    if sanitized != message:
        record.msg = sanitized
        record.args = ()
    if record.exc_info:
        original = "".join(traceback.format_exception(*record.exc_info))
        sanitized = _redact(original)
        if sanitized != original:
            # Preserva o stack trace em texto, sem manter a exceção sensível
            # disponível para outro handler serializá-la sem mascaramento.
            record.exc_info = None
            record.exc_text = sanitized.rstrip("\n")
    if record.exc_text:
        record.exc_text = _redact(record.exc_text)
    if record.stack_info:
        record.stack_info = _redact(record.stack_info)
    return record


def install_token_log_redaction():
    """Instala uma única camada sobre a factory existente, antes dos handlers.

    Cobre mensagens, argumentos formatados, Referer em access logs e tracebacks
    de Flask/Werkzeug/Gunicorn criados pelo logging Python deste processo.
    A configuração não habilita access logs nem muda níveis/handlers existentes.
    """
    previous = logging.getLogRecordFactory()
    if getattr(previous, "_nexo_token_redaction", False):
        return

    def factory(*args, **kwargs):
        return _sanitize_record(previous(*args, **kwargs))

    factory._nexo_token_redaction = True
    logging.setLogRecordFactory(factory)
