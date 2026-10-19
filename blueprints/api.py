"""
NEXO - Blueprint de API interna (JSON)
======================================
Endpoints leves consumidos via Fetch pelo front-end. Hoje: o NexoBot.
"""

from flask import Blueprint, request, jsonify, abort
from flask_login import login_required, current_user

from suporte_bot import responder

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/suporte-bot", methods=["POST"])
@login_required
def suporte_bot():
    """Recebe {mensagem} e devolve {resposta, fonte} do NexoBot (cliente apenas)."""
    if not current_user.is_cliente:
        abort(403)
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return jsonify(erro="Envie um objeto JSON com o campo mensagem."), 400
    mensagem = dados.get("mensagem")
    if mensagem is None:
        mensagem = ""
    if not isinstance(mensagem, str):
        return jsonify(erro="O campo mensagem deve ser um texto."), 400
    mensagem = mensagem.strip()[:1000]   # limite defensivo
    return jsonify(responder(mensagem))
