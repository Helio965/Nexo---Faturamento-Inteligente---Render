"""NEXO-SEC-003: Socket.IO com autorização pela credencial persistida.
SEC-001: cada conexão pertence a UMA sessão registrada (sala por sessão).

O registro de SIDs apenas localiza conexões. A autoridade é o banco; salas
por sessão e FOR SHARE impedem enfileirar dados privados após a revogação.
"""

from functools import wraps
import logging
import threading

from flask import current_app, request, session
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from extensions import db, socketio
from models import Usuario
from session_security import (
    CHAVE_CREDENCIAL, CHAVE_SESSAO, carregar_usuario, hash_token_sessao, id_sessao,
    impressao_sessao, mesma_impressao, sessao_valida,
)


logger = logging.getLogger(__name__)
_EXTENSAO = "nexo_realtime"

# Teto de conexões Socket.IO simultâneas por usuário (abas/dispositivos).
# Alto o bastante para o uso real, baixo o bastante para conter um laço.
MAX_CONEXOES_POR_USUARIO = 8


def inicializar_realtime(app, server=None):
    """Estado por aplicação; TESTING usa varredura explícita, sem thread órfã."""
    app.extensions[_EXTENSAO] = {
        "server": socketio.server if server is None else server,
        "sids": {}, "lock": threading.Lock(), "sweep_started": False,
    }


def _estado(app=None):
    app = current_app._get_current_object() if app is None else app
    return app.extensions[_EXTENSAO]


def sala_da_sessao(hash_sessao: str, impressao: str) -> str:
    """Sala privada de UMA sessão registrada, na credencial vigente.

    O logout de um navegador não silencia os demais e a sessão revogada deixa
    de ser destinatária. A impressão da credencial continua no nome: uma
    troca de senha feita fora da aplicação (SQL direto) muda a sala antes
    mesmo de a varredura derrubar o socket antigo.
    """
    return f"sessao_{hash_sessao}_{impressao}"


def revogar_conexoes_sessao(hash_sessao, app=None):
    """Após COMMIT da revogação (logout), fecha os SIDs locais dessa sessão."""
    if not isinstance(hash_sessao, str):
        return
    estado = _estado(app)
    with estado["lock"]:
        alvos = [sid for sid, dados in estado["sids"].items()
                 if dados.get("hash_sessao") == hash_sessao]
    for sid in alvos:
        _desconectar(estado, sid)


def _desconectar(estado, sid):
    try:
        estado["server"].disconnect(sid, namespace="/")
    except Exception as erro:  # transporte indisponível não autoriza dados
        logger.warning("Desconexão Socket.IO indisponível (%s).", type(erro).__name__)
    finally:
        with estado["lock"]:
            estado["sids"].pop(sid, None)


def revogar_conexoes_usuario(id_usuario, impressao_atual, app=None, *, impressao_revogada=None):
    """Após COMMIT, fecha SIDs locais antigos; salas bloqueiam outros processos."""
    estado = _estado(app)
    with estado["lock"]:
        antigos = [sid for sid, dados in estado["sids"].items()
                   if dados["id_usuario"] == id_usuario and (
                       mesma_impressao(impressao_revogada, dados["impressao"])
                       if impressao_revogada is not None else
                       not mesma_impressao(impressao_atual, dados["impressao"])
                   )]
    for sid in antigos:
        _desconectar(estado, sid)


def revogar_sockets_invalidos(app=None):
    """Reconsulta o banco em sessão independente, inclusive entre processos."""
    app = current_app._get_current_object() if app is None else app
    with app.app_context():
        estado = _estado(app)
        with estado["lock"]:
            registrados = list(estado["sids"].items())
        if not registrados:
            return 0
        invalidos = []
        try:
            # Não consultar o scoped session de um callback em estado committed.
            with Session(bind=db.engine) as consulta:
                for sid, dados in registrados:
                    usuario = consulta.scalar(select(Usuario).where(
                        Usuario.id_usuario == dados["id_usuario"],
                    ).execution_options(populate_existing=True))
                    cookie = {
                        "_user_id": str(dados["id_usuario"]),
                        "boot_id": dados["boot_id"],
                        CHAVE_CREDENCIAL: dados["impressao"],
                    }
                    if not sessao_valida(
                            usuario, cookie, permitir_primeiro_acesso=False, consulta=consulta,
                            hash_sessao=dados.get("hash_sessao")):
                        invalidos.append(sid)
        except SQLAlchemyError as erro:
            logger.warning("Verificação Socket.IO indisponível (%s).", type(erro).__name__)
            invalidos = [sid for sid, dados in registrados]
        for sid in invalidos:
            _desconectar(estado, sid)
        return len(invalidos)


def _varredura(app):
    while True:
        socketio.sleep(1)
        revogar_sockets_invalidos(app)


def _iniciar_varredura(app, estado):
    if app.testing:
        return
    with estado["lock"]:
        if estado["sweep_started"]:
            return
        estado["sweep_started"] = True
    socketio.start_background_task(_varredura, app)


def guarded_socket_event(funcao):
    """Mantém FOR SHARE no usuário/geração até o fim do evento autenticado.

    O handler não deve liberar sua transação antes de terminar a ação privada.
    Novos envios privados devem usar o despachante de notificações protegido.
    """
    @wraps(funcao)
    def protegido(*args, **kwargs):
        try:
            usuario = carregar_usuario(id_sessao(), bloquear=True)
            if not sessao_valida(usuario, permitir_primeiro_acesso=False):
                _desconectar(_estado(), request.sid)
                return False
            resultado = funcao(*args, **kwargs)
            # O ACK é enfileirado pela biblioteca depois do teardown (e da
            # liberação do lock). Dados privados devem ser emitidos dentro do
            # handler; só status sem dados pode atravessar essa fronteira.
            if resultado is None or type(resultado) is bool:
                return resultado
            logger.warning("Evento Socket.IO descartou retorno fora do contrato de status.")
            return False
        except SQLAlchemyError as erro:
            db.session.rollback()
            logger.warning("Evento Socket.IO indisponível (%s).", type(erro).__name__)
            _desconectar(_estado(), request.sid)
            return False
    return protegido


@socketio.on("connect")
def _on_connect(auth=None):
    try:
        usuario = carregar_usuario(id_sessao(), bloquear=True)
        if not sessao_valida(usuario, permitir_primeiro_acesso=False):
            return False
        estado = _estado()
        impressao = impressao_sessao(usuario)
        # sessao_valida já conferiu a linha registrada deste identificador.
        hash_sessao = hash_token_sessao(session.get(CHAVE_SESSAO))
        if hash_sessao is None:
            return False
        # Registrar/entrar na sala antes de liberar FOR SHARE evita handshake
        # validado antes do reset, mas admitido na sala depois de sua revogação.
        with estado["lock"]:
            # Teto de conexões simultâneas por usuário: muitas abas/dispositivos
            # (ou um cliente em laço) não esgotam as threads do worker. O sininho
            # precisa de uma conexão por aba, não de dezenas.
            abertas = sum(1 for dados in estado["sids"].values()
                          if dados["id_usuario"] == usuario.id_usuario)
            if abertas >= MAX_CONEXOES_POR_USUARIO:
                logger.info("Conexão Socket.IO recusada: teto por usuário atingido.")
                return False
            estado["sids"][request.sid] = {
                "id_usuario": usuario.id_usuario, "impressao": impressao,
                "boot_id": session["boot_id"], "hash_sessao": hash_sessao,
            }
        estado["server"].enter_room(
            request.sid, sala_da_sessao(hash_sessao, impressao), namespace="/",
        )
        _iniciar_varredura(current_app._get_current_object(), estado)
        return True
    except SQLAlchemyError as erro:
        db.session.rollback()
        logger.warning("Conexão Socket.IO indisponível (%s).", type(erro).__name__)
        return False


@socketio.on("disconnect")
def _on_disconnect(reason=None):
    estado = _estado()
    with estado["lock"]:
        estado["sids"].pop(request.sid, None)


@socketio.on("session_check")
@guarded_socket_event
def _on_session_check():
    return True


@socketio.on("*")
@guarded_socket_event
def _on_unknown_event(event, *args):
    # Eventos desconhecidos não executam ações de negócio.
    return False
