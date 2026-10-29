"""
NEXO - Faturamento Inteligente | Extensões Flask
================================================
Instâncias compartilhadas de SQLAlchemy e LoginManager.
Padrão: criar aqui, inicializar dentro da factory em app.py.
Isso evita import circular entre models.py e app.py.
"""

import hashlib

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail
from flask_socketio import SocketIO
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarativa SQLAlchemy 2.x. Todos os modelos herdam dela."""
    pass


# Instância única usada em toda a aplicação.
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
# Flask-Migrate (Alembic): versionamento de schema do Postgres/Supabase.
migrate = Migrate()
# Flask-Mail: envio de e-mails transacionais (SMTP).
mail = Mail()
# Flask-SocketIO: notificações em tempo real (sininho ao vivo).
# async_mode "threading" é o modo estável no Python 3.12 (sem eventlet/gevent),
# usando o driver simple-websocket. As origens permitidas no handshake são
# definidas na factory (config SOCKETIO_CORS_ORIGINS) para evitar Cross-Site
# WebSocket Hijacking — nunca "*" com cookie de sessão.
socketio = SocketIO(async_mode="threading", logger=False, engineio_logger=False)
# Proteção CSRF (Flask-WTF): valida token em TODAS as requisições mutáveis
# (POST/PUT/PATCH/DELETE). Inicializada na factory.
csrf = CSRFProtect()
# Rate limiting (Flask-Limiter): trava por IP em rotas sensíveis (login,
# recuperação de senha) contra brute force/abuso. Sem default global — só
# aplicamos limites explícitos via decorator nas rotas que precisam.
limiter = Limiter(key_func=get_remote_address)


def chave_limite_conta() -> str:
    """Segunda chave do login e da recuperação: a CONTA alvo (hash do e-mail
    normalizado), somada ao limite por IP. Um ataque distribuído por muitos IPs
    contra um único e-mail esbarra aqui; sem e-mail no formulário vale o IP."""
    from flask import request
    email = (request.form.get("email") or "").strip().lower()
    if not email:
        return get_remote_address()
    return "conta:" + hashlib.sha256(email.encode("utf-8")).hexdigest()[:24]


def chave_limite_usuario() -> str:
    """Limite por usuário autenticado (ações caras ou irreversíveis); anônimo = IP."""
    from flask_login import current_user
    identidade = current_user.get_id() if current_user.is_authenticated else None
    return f"usuario:{identidade}" if identidade else get_remote_address()

# Rota para onde Flask-Login redireciona quando @login_required falha.
login_manager.login_view = "auth.login"
login_manager.login_message = "Faça login para acessar esta página."
login_manager.login_message_category = "warning"
