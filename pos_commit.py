"""Fila pós-commit genérica (SEC-004): efeitos irreversíveis só após o COMMIT.

Um item agendado durante a transação é processado somente depois de o
COMMIT ser confirmado e a conexão devolvida ao pool; rollback descarta os
itens, inclusive os agendados dentro de um SAVEPOINT revertido. O processador
é executado fora da transação e deve ser idempotente e tolerante a falhas:
a operação de negócio já está confirmada e não pode ser desfeita por ele.

Uso: registrar_processador("nome", funcao) uma vez; agendar(sessao, "nome",
item) dentro da transação. Mesmo protocolo das notificações em tempo real
(notifications.py), que mantém sua própria fila por compatibilidade.
"""

import logging

from sqlalchemy import event
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_PENDENTES = "nexo_pos_commit_pendentes"
_CHECKPOINTS = "nexo_pos_commit_checkpoints"
_CONFIRMADO = "nexo_pos_commit_confirmado"
_processadores = {}


def registrar_processador(nome: str, funcao) -> None:
    _processadores[nome] = funcao


def agendar(sessao, nome: str, item) -> None:
    if nome not in _processadores:
        raise ValueError("Processador pós-commit não registrado.")
    sessao.info.setdefault(_PENDENTES, []).append((nome, item))


def pendentes(sessao) -> list:
    return list(sessao.info.get(_PENDENTES, []))


def _apos_commit(sessao):
    if not sessao.in_nested_transaction():
        sessao.info[_CONFIRMADO] = True


def _inicio_transacao(sessao, transacao):
    if transacao.nested:
        sessao.info.setdefault(_CHECKPOINTS, {})[id(transacao)] = len(sessao.info.get(_PENDENTES, []))


def _apos_rollback(sessao):
    transacao = sessao.get_nested_transaction()
    if transacao is None:
        for chave in (_PENDENTES, _CHECKPOINTS, _CONFIRMADO):
            sessao.info.pop(chave, None)
        return
    inicio = sessao.info.get(_CHECKPOINTS, {}).pop(id(transacao), 0)
    itens = sessao.info.get(_PENDENTES, [])
    del itens[inicio:]


def _fim_transacao(sessao, transacao):
    if transacao.nested:
        sessao.info.get(_CHECKPOINTS, {}).pop(id(transacao), None)
        return
    if transacao.parent is not None:
        return
    confirmado = sessao.info.pop(_CONFIRMADO, False)
    itens = sessao.info.pop(_PENDENTES, [])
    sessao.info.pop(_CHECKPOINTS, None)
    if not confirmado:
        return
    for nome, item in itens:
        try:
            _processadores[nome](item)
        except Exception as erro:  # noqa: BLE001 — negócio já confirmado
            logger.warning("Processador pós-commit %s falhou (%s).", nome, type(erro).__name__)


for _nome, _funcao in (("after_commit", _apos_commit), ("after_rollback", _apos_rollback),
                       ("after_transaction_create", _inicio_transacao),
                       ("after_transaction_end", _fim_transacao)):
    if not event.contains(Session, _nome, _funcao):
        event.listen(Session, _nome, _funcao)
