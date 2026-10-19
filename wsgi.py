"""
NEXO - Faturamento Inteligente | Entrypoint WSGI de produção
============================================================
Usado pelo gunicorn no deploy (ver render.yaml):

    gunicorn -w 1 --threads 50 --timeout 180 -b 0.0.0.0:$PORT wsgi:app

Por que 1 worker com threads: o Flask-SocketIO em async_mode "threading" guarda
as salas (user_<id>) e o rate limit (memory://) na memória do processo. Com
mais de um worker, cada processo teria o seu estado e as notificações em tempo
real não chegariam a quem estivesse conectado no outro. As threads atendem as
requisições concorrentes e o simple-websocket cuida do WebSocket.

`python app.py` continua sendo o jeito de subir em desenvolvimento local.
"""

import os

from app import create_app

app = create_app(os.environ.get("FLASK_ENV", "production"))
