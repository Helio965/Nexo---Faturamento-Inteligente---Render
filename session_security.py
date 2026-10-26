"""SEC-003/004: autorização persistida e sessões ligadas à credencial atual."""

import hashlib
import hmac

from flask import current_app, session
from sqlalchemy import select
from sqlalchemy.orm import object_session

from contract_policy import condicao_sql_vinculo_contratual
from extensions import db
from models import Empresa, Usuario


CHAVE_CREDENCIAL = "credential_fingerprint"
_CONTEXTO_SESSAO = b"nexo-session-credential-v1\0"
# NEXO-AJ-06.1: CANCELADA bloqueia o CLIENTE como a lixeira. SUSPENSA mantém o
# acesso ao portal; o que ela pode consultar é decidido por contract_policy.
STATUS_CONTA_SEM_ACESSO = "CANCELADA"


def condicoes_empresa_acessivel(instante=None, *, sessao=None):
    """Critério único da empresa que libera CLIENTE: fora da lixeira, não cancelada
    e, no regime contratual, com contrato vigente cuja suspensão não expirou.

    O prazo é comparado ao relógio da política no próprio SQL: a expiração
    bloqueia login, sessão, tokens, Socket.IO e notificações antes mesmo de a
    reconciliação gravar o cancelamento. `sessao` é a Session que executará a
    consulta (entregas pós-commit usam Session própria, não db.session).
    """
    return (
        Empresa.deletado_em.is_(None),
        Empresa.status_conta != STATUS_CONTA_SEM_ACESSO,
        condicao_sql_vinculo_contratual(instante, sessao=sessao),
    )


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


def usuario_pode_acessar(usuario, *, consulta=None) -> bool:
    """Estado administrativo, lixeira e cancelamento da empresa, sempre lidos do banco.

    Não usa o relacionamento ORM potencialmente desatualizado nem outra
    conexão: notificações/varreduras passam sua própria Session. O SELECT da
    empresa é MVCC, sem lock: os leitores Socket.IO já mantêm FOR SHARE no
    usuário, e a exclusão atualiza sua geração na mesma transação da empresa.
    Assim, a exclusão só confirma depois da emissão autorizada anterior, sem
    inverter a ordem Empresa -> Usuario dos locks de escrita.
    """
    if (usuario is None or not usuario.ativo
            or usuario.role not in ("ADMIN", "CLIENTE")):
        return False
    if usuario.role == "ADMIN":
        return usuario.id_empresa is None
    if usuario.id_empresa is None:
        return False
    consulta = object_session(usuario) if consulta is None else consulta
    if consulta is None:
        return False
    with consulta.no_autoflush:
        return consulta.scalar(select(Empresa.id_empresa).where(
            Empresa.id_empresa == usuario.id_empresa,
            *condicoes_empresa_acessivel(sessao=consulta),
        )) is not None


def vincular_geracao_autorizacao(mensagem: bytes, geracao: int) -> bytes:
    """Geração zero preserva a SEC-003; gerações posteriores nunca a reutilizam."""
    if type(geracao) is not int or geracao < 0:
        raise ValueError("Geração de autorização inválida.")
    if geracao == 0:
        return mensagem
    return (b"nexo-authorization-generation-v1\0" + str(geracao).encode("ascii")
            + b"\0" + mensagem)


def impressao_credencial_sessao(
        id_usuario: int, senha_hash: str, geracao_autorizacao: int = 0) -> str:
    """HMAC padrão, com contexto distinto dos tokens de ativação/recuperação."""
    chave = current_app.config["SECRET_KEY"]
    if isinstance(chave, str):
        chave = chave.encode("utf-8")
    mensagem = vincular_geracao_autorizacao(
        _CONTEXTO_SESSAO + f"{id_usuario}\0{senha_hash}".encode("utf-8"),
        geracao_autorizacao,
    )
    return hmac.new(chave, mensagem, hashlib.sha256).hexdigest()


def impressao_sessao(usuario) -> str:
    return impressao_credencial_sessao(
        usuario.id_usuario, usuario.senha_hash, usuario.geracao_autorizacao,
    )


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


def sessao_valida(usuario, dados=None, *, permitir_primeiro_acesso=True, consulta=None) -> bool:
    dados = session if dados is None else dados
    if (not usuario_pode_acessar(usuario, consulta=consulta)
            or id_sessao(dados) != usuario.id_usuario
            or dados.get("boot_id") != current_app.config["BOOT_ID"]):
        return False
    if (not permitir_primeiro_acesso and usuario.role == "CLIENTE"
            and usuario.primeiro_acesso):
        return False
    return mesma_impressao(impressao_sessao(usuario), dados.get(CHAVE_CREDENCIAL))


def carregar_usuario(id_usuario, *, bloquear=False):
    """FOR SHARE serializa envio/evento com senha e geração de autorização no PG."""
    id_usuario = _id_valido(id_usuario)
    if id_usuario is None:
        return None
    comando = select(Usuario).where(Usuario.id_usuario == id_usuario)
    if bloquear:
        comando = comando.with_for_update(read=True)
    comando = comando.execution_options(populate_existing=True)
    with db.session.no_autoflush:
        return db.session.scalar(comando)
