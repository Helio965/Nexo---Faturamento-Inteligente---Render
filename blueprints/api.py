"""
NEXO - Blueprint de API interna (JSON)
======================================
Endpoints leves consumidos via Fetch pelo front-end. Hoje: o NexoBot.

Contrato de POST /api/suporte-bot (detalhes em Docs/NEXOBOT_ADVANCED.md):
  entrada: {"mensagem": str, "contexto"?: {...}, "ultimo_destino"?: str, "pagina_atual"?: str}
  saída:   {"resposta", "blocos", "sugestoes", "fonte", "acao", "destino",
            ["url", "rotulo_botao", "opcoes"], "contexto", "meta"}
  - "blocos": resposta estruturada (cabecalho, texto, passos, secao, exemplo, aviso),
    renderizada pelo widget sem HTML; "resposta" é o mesmo conteúdo em texto puro.
  - "sugestoes": chips [{rotulo, mensagem}] que apenas enviam uma nova mensagem.
  - "contexto": inclui "assunto" (id da base de conhecimento) e "nivel" (0–4) para
    aprofundar sem repetir ("explique melhor", "me dê um exemplo", "e depois?").
"""

import logging
import uuid

from flask import Blueprint, request, jsonify, abort
from flask_login import login_required, current_user
from flask_limiter.util import get_remote_address

from extensions import limiter
from suporte_bot import responder, urls_destinos

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__, url_prefix="/api")

LIMITE_CORPO_BYTES = 16 * 1024   # a mensagem tem no máximo 1000 caracteres
LIMITE_MENSAGEM = 1000


def _chave_limite() -> str:
    """Limite por usuário autenticado; sem login (não chega à view), por IP."""
    if current_user.is_authenticated:
        return f"usuario:{current_user.get_id()}"
    return get_remote_address()


def _erro(mensagem: str, status: int, **extra):
    # `erro` mantém o contrato anterior; `resposta` permite ao widget exibir o motivo.
    return jsonify(erro=mensagem, resposta=mensagem, fonte="local", acao=None, destino=None, **extra), status


@api_bp.after_request
def _cabecalhos_defensivos(resposta):
    """JSON com dados do usuário: sem cache compartilhado e sem MIME sniffing."""
    resposta.headers["Cache-Control"] = "no-store"
    resposta.headers["X-Content-Type-Options"] = "nosniff"
    return resposta


@api_bp.app_context_processor
def destinos_nexobot():
    """O widget valida ações usando o mesmo catálogo fechado do backend."""
    if current_user.is_authenticated and current_user.is_cliente:
        return {"nexobot_destinos": urls_destinos()}
    return {"nexobot_destinos": {}}


@api_bp.route("/suporte-bot", methods=["POST"])
@login_required
@limiter.limit("30 per minute", key_func=_chave_limite)
def suporte_bot():
    """Recebe a mensagem e um contexto mínimo; devolve texto e, no máximo, uma ação do catálogo."""
    if not current_user.is_cliente:
        abort(403)
    if (request.content_length or 0) > LIMITE_CORPO_BYTES or len(request.get_data(cache=True)) > LIMITE_CORPO_BYTES:
        return _erro("A mensagem enviada é grande demais.", 413)
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return _erro("Envie um objeto JSON com o campo mensagem.", 400)
    mensagem = dados.get("mensagem")
    if mensagem is None:
        mensagem = ""
    if not isinstance(mensagem, str):
        return _erro("O campo mensagem deve ser um texto.", 400)
    mensagem = mensagem.strip()[:LIMITE_MENSAGEM]   # limite defensivo
    try:
        resultado = responder(
            mensagem,
            ultimo_destino=dados.get("ultimo_destino"),
            contexto=dados.get("contexto"),
            pagina_atual=dados.get("pagina_atual"),
        )
    except Exception:  # noqa: BLE001 — falha real: registrada com traceback e informada como tal
        correlacao = uuid.uuid4().hex[:12]
        logger.exception("NexoBot: erro inesperado ao responder (correlacao=%s).", correlacao)
        return _erro("Não consegui processar sua mensagem agora. Tente novamente em instantes "
                     "ou abra um chamado em Suporte.", 500, meta={"correlacao": correlacao})
    return jsonify(resultado)
