"""
NEXO - Faturamento Inteligente | E-mails transacionais (Flask-Mail / SMTP)
==========================================================================
Envio de e-mails HTML disparados por eventos de negócio (publicação de análise,
resolução de chamado). Princípios:

  - FAIL-SAFE: se MAIL_USERNAME/PASSWORD não estiverem configurados (MAIL_ATIVO
    False), o envio é SUPRIMIDO (loga e segue) — nada quebra em dev/demo.
  - NÃO-BLOQUEANTE: o envio roda numa thread com app_context próprio, para não
    travar a request enquanto o SMTP faz handshake.
  - Qualquer falha de SMTP é capturada e logada — jamais derruba o fluxo que
    disparou o e-mail (publicar análise, resolver ticket).
  - DOIS TRANSPORTES: com BREVO_API_KEY definida, o envio sai pela API HTTPS do
    Brevo (porta 443 — funciona em hosts que bloqueiam SMTP, como o Render
    Free); sem ela, sai pelo SMTP do Flask-Mail (ex.: Gmail em dev local).
"""

import json
import logging
import threading
import urllib.error
import urllib.request
from email.utils import parseaddr

from flask import current_app, render_template
from flask_mail import Message

from extensions import mail

logger = logging.getLogger(__name__)


def _enviar_brevo(app, msg: Message) -> None:
    """Envia a mensagem pela API transacional do Brevo (HTTPS). Mesmo remetente,
    destinatários, assunto e HTML que o SMTP usaria."""
    if isinstance(msg.sender, tuple):
        nome, email = msg.sender
    else:
        nome, email = parseaddr(msg.sender)
    payload = {
        "sender": {"name": nome or "NEXO", "email": email},
        "to": [{"email": d} for d in msg.recipients],
        "subject": msg.subject,
        "htmlContent": msg.html,
    }
    req = urllib.request.Request(
        app.config["BREVO_API_URL"],
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "api-key": app.config["BREVO_API_KEY"],
            "content-type": "application/json",
            "accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20):
            pass
    except urllib.error.HTTPError as e:
        # Respostas do provedor podem incluir destinatários ou conteúdo privado.
        raise RuntimeError(f"Brevo HTTP {e.code}") from None


def _enviar_async(app, msg: Message) -> None:
    with app.app_context():
        try:
            if app.config.get("BREVO_API_KEY"):
                _enviar_brevo(app, msg)
            else:
                mail.send(msg)
            # Aceitação do SMTP/API não confirma a entrega ao destinatário.
            logger.info("E-mail transacional aceito pelo transporte.")
        except Exception as e:  # noqa: BLE001
            logger.warning("Falha ao enviar e-mail (%s).", type(e).__name__)


def enviar_email(destinatarios, assunto: str, template: str, **ctx) -> bool:
    """
    Renderiza templates/emails/<template> e dispara em background.
    Retorna True se o envio foi agendado; False se suprimido/sem destinatário.
    """
    if isinstance(destinatarios, str):
        destinatarios = [destinatarios]
    destinatarios = [d for d in (destinatarios or []) if d]
    if not destinatarios:
        return False

    if not current_app.config.get("MAIL_ATIVO"):
        logger.info("MAIL inativo (sem credenciais) — envio suprimido.")
        return False

    try:
        html = render_template(f"emails/{template}", **ctx)
        msg = Message(subject=assunto, recipients=destinatarios, html=html)
        app = current_app._get_current_object()
        threading.Thread(target=_enviar_async, args=(app, msg), daemon=True).start()
    except Exception as erro:  # noqa: BLE001
        # A falha de agendamento também é fail-safe; não publicar conteúdo/URLs.
        logger.warning("Falha ao agendar e-mail (%s).", type(erro).__name__)
        return False
    return True


def _emails_da_empresa(empresa) -> list[str]:
    """Coleta e-mails de contato da empresa + dos usuários CLIENTE ativos."""
    emails = set()
    if getattr(empresa, "email_contato", None):
        emails.add(empresa.email_contato)
    for u in getattr(empresa, "usuarios", []) or []:
        if u.role == "CLIENTE" and u.ativo and u.email:
            emails.add(u.email)
    return list(emails)


# ---------------------------------------------------------------------
# Gatilhos de alto nível (chamados nos blueprints)
# ---------------------------------------------------------------------
def email_analise_publicada(analise, link_url: str) -> bool:
    """E-mail ao cliente quando a devolutiva estratégica é publicada."""
    ref = f"{analise.mes_referencia:02d}/{analise.ano_referencia}"
    return enviar_email(
        _emails_da_empresa(analise.empresa),
        f"📊 Sua Análise Executiva NEXO de {ref} está disponível",
        "analise_publicada.html",
        analise=analise, ref=ref, link_url=link_url,
    )


def email_ticket_resolvido(chamado, link_url: str) -> bool:
    """E-mail ao cliente quando um chamado é marcado como RESOLVIDO."""
    return enviar_email(
        _emails_da_empresa(chamado.empresa),
        f"✅ Chamado resolvido: “{chamado.assunto}”",
        "ticket_resolvido.html",
        chamado=chamado, link_url=link_url,
    )


def email_recuperacao_senha(usuario, link_url: str) -> bool:
    """E-mail com o link seguro (15 min) para redefinição de senha."""
    return enviar_email(
        usuario.email,
        "🔐 Redefinição de senha — NEXO",
        "recuperacao_senha.html",
        usuario=usuario, link_url=link_url,
    )


def email_boas_vindas(usuario, link_definir: str) -> bool:
    """
    E-mail de boas-vindas ao novo cliente, com o LINK SEGURO de definição de
    senha (token de 15 min) — sem senha em texto. Disparado direto pelo Flask
    após o cadastro (sem webhook externo).
    """
    return enviar_email(
        usuario.email,
        "👋 Bem-vindo(a) ao NEXO — defina sua senha de acesso",
        "boas_vindas.html",
        usuario=usuario, link_definir=link_definir,
    )
