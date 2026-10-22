"""NEXO-SEC-003: sessões vinculadas à credencial atual, sem expor seu hash."""

import hashlib
import hmac

from flask import current_app, session
from sqlalchemy import select

from extensions import db
from models import Usuario


CHAVE_CREDENCIAL = "credential_fingerprint"
_CONTEXTO_SESSAO = b"nexo-session-credential-v1\0"


def _id_valido(valor):
    if isinstance(valor, str):
        if not valor or len(valor) > 10 or not valor.isascii() or not valor.isdecimal():
            return None
        valor = int(valor)
    if type(valor) is not int or not 0 < valor <= 2147483647:
        return None
    return valor


def id_sessao(dados=None):
    dados = session if dados is None else dados
    return _id_valido(dados.get("_user_id"))


def impressao_credencial_sessao(id_usuario: int, senha_hash: str) -> str:
    """HMAC padrão, com contexto distinto dos tokens de ativação/recuperação."""
    chave = current_app.config["SECRET_KEY"]
    if isinstance(chave, str):
        chave = chave.encode("utf-8")
    mensagem = _CONTEXTO_SESSAO + f"{id_usuario}\0{senha_hash}".encode("utf-8")
    return hmac.new(chave, mensagem, hashlib.sha256).hexdigest()


def impressao_sessao(usuario) -> str:
    return impressao_credencial_sessao(usuario.id_usuario, usuario.senha_hash)


def mesma_impressao(esperada, recebida) -> bool:
    # compare_digest(str, str) não aceita Unicode não ASCII.
    for valor in (esperada, recebida):
        if (not isinstance(valor, str) or len(valor) != 64
                or any(c not in "0123456789abcdef" for c in valor)):
            return False
    return hmac.compare_digest(esperada, recebida)


def registrar_sessao(usuario, *, impressao_esperada=None) -> None:
    """Carimba a credencial verificada; login deve fornecer snapshot pré-commit."""
    session[CHAVE_CREDENCIAL] = (
        impressao_sessao(usuario) if impressao_esperada is None else impressao_esperada
    )
    session["boot_id"] = current_app.config["BOOT_ID"]


def sessao_valida(usuario, dados=None, *, permitir_primeiro_acesso=True) -> bool:
    dados = session if dados is None else dados
    if (usuario is None or not usuario.ativo
            or usuario.role not in ("ADMIN", "CLIENTE")
            or id_sessao(dados) != usuario.id_usuario
            or dados.get("boot_id") != current_app.config["BOOT_ID"]):
        return False
    if (not permitir_primeiro_acesso and usuario.role == "CLIENTE"
            and usuario.primeiro_acesso):
        return False
    return mesma_impressao(impressao_sessao(usuario), dados.get(CHAVE_CREDENCIAL))


def carregar_usuario(id_usuario, *, bloquear=False):
    """Leitura atual; FOR SHARE serializa envio/evento com troca da senha no PG."""
    id_usuario = _id_valido(id_usuario)
    if id_usuario is None:
        return None
    comando = select(Usuario).where(Usuario.id_usuario == id_usuario)
    if bloquear:
        comando = comando.with_for_update(read=True)
    comando = comando.execution_options(populate_existing=True)
    with db.session.no_autoflush:
        return db.session.scalar(comando)
