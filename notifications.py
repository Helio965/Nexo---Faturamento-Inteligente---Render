"""
NEXO - Faturamento Inteligente | Notificações (sininho da navbar)
=================================================================
Helpers para CRIAR notificações dirigidas a usuários. Seguem a disciplina de
transação do projeto: apenas fazem `session.add(...)` — quem chama é responsável
pelo commit (normalmente já há um commit logo após o gatilho).

Gatilhos atuais:
  - cliente envia relatório (upload)      -> notifica ADMIN(s)
  - admin homologa/processa o ETL         -> notifica CLIENTE(s) da empresa
  - admin publica a devolutiva            -> notifica CLIENTE(s) da empresa
  - nova resposta em chamado de suporte   -> notifica a contraparte
"""

import logging
from datetime import datetime

from flask import has_app_context
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from extensions import db, socketio
from models import Empresa, Notificacao, Usuario
from session_security import impressao_sessao, usuario_pode_acessar
from realtime import sala_do_usuario

logger = logging.getLogger(__name__)


def classificar_notificacao(texto: str) -> dict:
    """
    Classifica uma notificação em um TIPO visual de badge, a partir do texto.
    Fonte única de verdade usada tanto no render do servidor (Jinja) quanto no
    payload do Socket.IO (JS) — assim a badge é idêntica nos dois caminhos.

      resolvido -> verde   (chamado encerrado)
      analise   -> roxo    (nova análise / relatório disponível)
      aberto    -> vermelho/rosa (ação pendente: novo chamado, resposta, upload)
    """
    t = (texto or "").lower()
    if "resolvid" in t:
        return {"tipo": "resolvido", "rotulo": "Resolvido"}
    if ("dispon" in t) or ("relatório estrat" in t) or ("relatorio estrat" in t) or ("processamos" in t):
        return {"tipo": "analise", "rotulo": "Nova Análise"}
    return {"tipo": "aberto", "rotulo": "Aberto"}


def _emitir_tempo_real(id_usuario: int, n: Notificacao) -> None:
    """Enfileira payload sem ORM; só o COMMIT externo autoriza sua entrega."""
    badge = classificar_notificacao(n.texto)
    payload = {
        "id": n.id_notificacao, "texto": n.texto,
        "link": n.link_destino or "",
        "hora": datetime.now().strftime("%d/%m %H:%M"),
        "badge": badge["tipo"], "badge_rotulo": badge["rotulo"],
    }
    db.session.info.setdefault("nexo_notificacoes_pendentes", []).append((id_usuario, payload))


def _entregar_tempo_real(bind, id_usuario, payload):
    # A transação que criou a notificação já terminou. A sessão independente
    # evita consultar uma sessão committed ou bloquear o próprio chamador.
    # FOR SHARE mantém credencial e geração até enfileirar o pacote. O UPDATE
    # de senha ou exclusão da empresa só confirma depois, ou já é visto aqui.
    # A leitura da empresa é MVCC, na mesma Session e sem lock invertido.
    with Session(bind=bind) as consulta:
        usuario = consulta.scalar(select(Usuario).where(
            Usuario.id_usuario == id_usuario,
        ).with_for_update(read=True))
        if (not usuario_pode_acessar(usuario, consulta=consulta)
                or (usuario.role == "CLIENTE" and usuario.primeiro_acesso)):
            return
        socketio.emit(
            "nova_notificacao", payload,
            room=sala_do_usuario(id_usuario, impressao_sessao(usuario)),
            namespace="/",
        )


def _apos_commit_notificacoes(sessao):
    # after_commit ainda retém a conexão original. Apenas marcar o COMMIT;
    # a entrega precisa esperar after_transaction_end liberar essa conexão.
    if not sessao.in_nested_transaction():
        sessao.info["nexo_notificacoes_commit_confirmado"] = True


def _despachar_notificacoes(sessao, pendentes):
    if not pendentes:
        return
    if not has_app_context():
        logger.warning("Notificação em tempo real sem contexto de aplicação; entrega descartada.")
        return
    bind = sessao.get_bind()
    for id_usuario, payload in pendentes:
        try:
            _entregar_tempo_real(bind, id_usuario, payload)
        except Exception as erro:  # negócio já confirmado; não anunciar falha dele
            logger.warning("Entrega de notificação indisponível (%s).", type(erro).__name__)


def _inicio_transacao_notificacoes(sessao, transacao):
    if transacao.nested:
        # SAVEPOINT reverte só os payloads criados desde sua abertura.
        sessao.info.setdefault("nexo_notificacoes_checkpoints", {})[id(transacao)] = len(
            sessao.info.get("nexo_notificacoes_pendentes", []),
        )


def _apos_rollback_notificacoes(sessao):
    transacao = sessao.get_nested_transaction()
    if transacao is None:
        sessao.info.pop("nexo_notificacoes_pendentes", None)
        sessao.info.pop("nexo_notificacoes_checkpoints", None)
        sessao.info.pop("nexo_notificacoes_commit_confirmado", None)
        return
    inicio = sessao.info.get("nexo_notificacoes_checkpoints", {}).pop(id(transacao), 0)
    pendentes = sessao.info.get("nexo_notificacoes_pendentes", [])
    del pendentes[inicio:]


def _fim_transacao_notificacoes(sessao, transacao):
    if transacao.nested:
        sessao.info.get("nexo_notificacoes_checkpoints", {}).pop(id(transacao), None)
    elif transacao.parent is None:
        # A conexão original já foi devolvida ao pool. Abrir a sessão de
        # entrega aqui funciona também com pool_size=1 / max_overflow=0.
        # Session.close sem COMMIT apenas descarta os payloads pendentes.
        confirmado = sessao.info.pop("nexo_notificacoes_commit_confirmado", False)
        pendentes = sessao.info.pop("nexo_notificacoes_pendentes", [])
        sessao.info.pop("nexo_notificacoes_checkpoints", None)
        if confirmado:
            _despachar_notificacoes(sessao, pendentes)


# Importar o módulo repetidamente não registra callbacks adicionais.
if not event.contains(Session, "after_commit", _apos_commit_notificacoes):
    event.listen(Session, "after_commit", _apos_commit_notificacoes)
if not event.contains(Session, "after_rollback", _apos_rollback_notificacoes):
    event.listen(Session, "after_rollback", _apos_rollback_notificacoes)
if not event.contains(Session, "after_transaction_create", _inicio_transacao_notificacoes):
    event.listen(Session, "after_transaction_create", _inicio_transacao_notificacoes)
if not event.contains(Session, "after_transaction_end", _fim_transacao_notificacoes):
    event.listen(Session, "after_transaction_end", _fim_transacao_notificacoes)


def criar_notificacao(id_usuario: int, texto: str, link_destino: str | None = None) -> Notificacao:
    """
    Cria UMA notificação e agenda o evento para depois do commit externo.
    O flush garante o id_notificacao para o payload do socket.
    """
    n = Notificacao(id_usuario=id_usuario, texto=texto, link_destino=link_destino)
    db.session.add(n)
    db.session.flush()  # garante o PK para o payload
    _emitir_tempo_real(id_usuario, n)
    return n


def notificar_admins(texto: str, link_destino: str | None = None) -> int:
    """Notifica TODOS os usuários ADMIN ativos. Retorna a quantidade gerada."""
    admins = db.session.execute(
        select(Usuario.id_usuario).where(Usuario.role == "ADMIN", Usuario.ativo.is_(True))
    ).scalars().all()
    for uid in admins:
        criar_notificacao(uid, texto, link_destino)
    return len(admins)


def notificar_clientes_empresa(id_empresa: int, texto: str, link_destino: str | None = None) -> int:
    """Notifica os usuários CLIENTE ativos vinculados a uma empresa."""
    clientes = db.session.execute(
        select(Usuario.id_usuario).where(
            Usuario.role == "CLIENTE",
            Usuario.id_empresa == id_empresa,
            Usuario.ativo.is_(True),
            select(Empresa.id_empresa).where(
                Empresa.id_empresa == Usuario.id_empresa,
                Empresa.deletado_em.is_(None),
            ).exists(),
        )
    ).scalars().all()
    for uid in clientes:
        criar_notificacao(uid, texto, link_destino)
    return len(clientes)


def contexto_sininho(usuario) -> dict:
    """
    Dados do sininho para o usuário autenticado: contagem de não-lidas e as
    5 notificações mais recentes. Usado pelo context processor (toda página).
    """
    if usuario is None or not getattr(usuario, "is_authenticated", False):
        return {"notif_nao_lidas": 0, "notif_recentes": []}

    nao_lidas = db.session.execute(
        select(db.func.count(Notificacao.id_notificacao)).where(
            Notificacao.id_usuario == usuario.id_usuario,
            Notificacao.lida.is_(False),
        )
    ).scalar() or 0

    recentes = db.session.execute(
        select(Notificacao)
        .where(Notificacao.id_usuario == usuario.id_usuario)
        .order_by(Notificacao.data_criacao.desc(), Notificacao.id_notificacao.desc())
        .limit(5)
    ).scalars().all()

    return {"notif_nao_lidas": int(nao_lidas), "notif_recentes": recentes}
