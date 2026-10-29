"""
NEXO - Blueprint de Notificações (sininho)
===========================================
Rotas compartilhadas por ADMIN e CLIENTE (qualquer usuário autenticado):
  POST /notificacoes/marcar-lidas   → marca todas as não-lidas como lidas.
  POST /notificacoes/<id>/abrir      → marca aquela como lida e redireciona
                                       para o link_destino (ou dashboard).
  GET  /notificacoes/<id>/abrir      → só redireciona (SEC-002: nenhum GET
                                       altera estado; links antigos seguem
                                       funcionando sem marcar como lida).
A leitura/contagem para o sininho é injetada em todas as páginas pelo
context processor (ver app.create_app).
"""

from urllib.parse import urlparse

from flask import Blueprint, redirect, url_for, request
from flask_login import login_required, current_user
from sqlalchemy import update

from extensions import db
from models import Notificacao

notificacoes_bp = Blueprint("notificacoes", __name__, url_prefix="/notificacoes")


def _destino_padrao() -> str:
    """Dashboard do perfil do usuário logado (fallback de redirecionamento)."""
    return url_for("admin.dashboard") if current_user.is_admin else url_for("cliente.dashboard")


def _local_ou_padrao(alvo: str) -> str:
    """
    Devolve `alvo` se for um caminho LOCAL seguro; senão, o dashboard padrão.
    Defesa em profundidade contra open redirect (referrer/link_destino externos),
    mesmo que hoje esses valores sejam sempre internos (gerados por url_for).
    """
    if alvo:
        p = urlparse(alvo)
        if not p.scheme and not p.netloc and alvo.startswith("/") and not alvo.startswith(("//", "/\\")):
            return alvo
    return _destino_padrao()


@notificacoes_bp.route("/marcar-lidas", methods=["POST"])
@login_required
def marcar_lidas():
    db.session.execute(
        update(Notificacao)
        .where(Notificacao.id_usuario == current_user.id_usuario, Notificacao.lida.is_(False))
        .values(lida=True)
    )
    db.session.commit()
    # Volta para a página de origem quando possível (UX do dropdown), validando
    # que o referrer é local.
    return redirect(_local_ou_padrao(request.referrer))


@notificacoes_bp.route("/<int:id_notificacao>/abrir", methods=["GET", "POST"])
@login_required
def abrir(id_notificacao):
    notif = db.session.get(Notificacao, id_notificacao)
    # Só o dono da notificação pode abri-la; senão, cai no dashboard.
    if notif is None or notif.id_usuario != current_user.id_usuario:
        return redirect(_destino_padrao())
    # SEC-002: a mutação exige POST (+ CSRF). O item do sininho é um
    # formulário; um GET (prefetch, histórico, link copiado) apenas navega.
    if request.method == "POST" and not notif.lida:
        notif.lida = True
        db.session.commit()
    return redirect(_local_ou_padrao(notif.link_destino))
