"""
Cria (ou reseta) um CLIENTE de demonstração com primeiro_acesso=True, para
mostrar o fluxo de interceptação de primeiro acesso ao vivo em apresentações.

SEC-007: utilitário exclusivo de ambiente de teste/demonstração.
  - Importar este módulo não executa nada (tudo fica em main()).
  - Só roda com NEXO_AMBIENTE_DEMO=1 e NUNCA com FLASK_ENV=production.
  - Recusa qualquer banco que não seja local (SQLite ou PostgreSQL em
    localhost/127.0.0.1/::1): a verificação acontece ANTES de criar a app ou
    abrir conexão, então nenhuma escrita chega a um banco de produção.
  - Sem credencial fixa: a senha temporária vem de NEXO_DEMO_SENHA (mínimo 12
    caracteres), definida por quem apresenta, e nunca é impressa.
  - Dados sintéticos: e-mail em domínio reservado (NEXO_DEMO_EMAIL opcional).

Uso (somente ambiente local):
  NEXO_AMBIENTE_DEMO=1 NEXO_DEMO_SENHA='<senha-temporaria>' python criar_cliente_demo.py
"""

import os
import sys
from urllib.parse import urlsplit

EMAIL_PADRAO = "primeiro-acesso@demo.example.invalid"
NOME = "Cliente Demo · Primeiro Acesso"
HOSTS_LOCAIS = {"localhost", "127.0.0.1", "::1"}
TAMANHO_MINIMO_SENHA = 12


class DemoRecusada(RuntimeError):
    """Pré-condição de segurança não atendida; nada foi executado."""


def banco_e_local(url: str) -> bool:
    """SQLite ou PostgreSQL em host local. Vazio = SQLite padrão (local)."""
    url = (url or "").strip()
    if not url or url.startswith("sqlite:"):
        return True
    partes = urlsplit(url)
    if not partes.scheme.startswith("postgres"):
        return False
    try:
        host = partes.hostname
    except ValueError:
        return False
    return host in HOSTS_LOCAIS


def verificar_ambiente(ambiente=None) -> dict:
    """Levanta DemoRecusada antes de qualquer app, conexão ou escrita."""
    ambiente = os.environ if ambiente is None else ambiente
    if ambiente.get("NEXO_AMBIENTE_DEMO") != "1":
        raise DemoRecusada("Defina NEXO_AMBIENTE_DEMO=1 para confirmar que este é um ambiente de demonstração.")
    if ambiente.get("FLASK_ENV", "development") == "production":
        raise DemoRecusada("Este utilitário não roda com FLASK_ENV=production.")
    for variavel in ("DATABASE_URL", "DIRECT_URL"):
        if not banco_e_local(ambiente.get(variavel, "")):
            raise DemoRecusada(f"{variavel} não aponta para um banco local; o utilitário de demonstração foi recusado.")
    senha = ambiente.get("NEXO_DEMO_SENHA") or ""
    if len(senha) < TAMANHO_MINIMO_SENHA:
        raise DemoRecusada(f"NEXO_DEMO_SENHA deve ter ao menos {TAMANHO_MINIMO_SENHA} caracteres (não é impressa).")
    email = (ambiente.get("NEXO_DEMO_EMAIL") or EMAIL_PADRAO).strip().lower()
    if "@" not in email:
        raise DemoRecusada("NEXO_DEMO_EMAIL inválido.")
    return {"senha": senha, "email": email}


def criar_ou_rearmar(app, email: str, senha: str) -> dict:
    """Idempotente: cria o cliente demo ou re-arma a flag e a senha temporária."""
    from sqlalchemy import select

    from extensions import db
    from models import Empresa, Usuario

    with app.app_context():
        empresa = db.session.execute(select(Empresa).order_by(Empresa.id_empresa)).scalars().first()
        if empresa is None:
            raise DemoRecusada("Nenhuma empresa cadastrada — crie uma empresa antes de rodar este script.")
        usuario = db.session.execute(select(Usuario).where(Usuario.email == email)).scalar_one_or_none()
        if usuario is None:
            usuario = Usuario(nome=NOME, email=email, role="CLIENTE", id_empresa=empresa.id_empresa, ativo=True)
            db.session.add(usuario)
            acao = "criado"
        else:
            if usuario.role != "CLIENTE":
                raise DemoRecusada("O e-mail informado pertence a uma conta que não é CLIENTE; nada foi alterado.")
            usuario.ativo = True
            if usuario.id_empresa is None:
                usuario.id_empresa = empresa.id_empresa
            acao = "atualizado (flag re-armada)"
        usuario.set_senha(senha)
        usuario.primeiro_acesso = True
        db.session.commit()
        return {"acao": acao, "email": email, "empresa": empresa.razao_social,
                "id_empresa": empresa.id_empresa, "primeiro_acesso": usuario.primeiro_acesso}


def main(argv=None) -> int:
    try:
        parametros = verificar_ambiente()
    except DemoRecusada as erro:
        print(f"Recusado: {erro}", file=sys.stderr)
        return 2
    from app import create_app

    app = create_app("development")
    try:
        resultado = criar_ou_rearmar(app, parametros["email"], parametros["senha"])
    except DemoRecusada as erro:
        print(f"Recusado: {erro}", file=sys.stderr)
        return 2
    print("=" * 56)
    print(f"Cliente demo {resultado['acao']}.")
    print(f"  E-mail ........: {resultado['email']}")
    print("  Senha temporária: (a definida em NEXO_DEMO_SENHA; não é impressa)")
    print(f"  Empresa .......: {resultado['empresa']} (id {resultado['id_empresa']})")
    print(f"  primeiro_acesso: {resultado['primeiro_acesso']}")
    print("=" * 56)
    print("Faça login com ele para ver a interceptação de primeiro acesso ao vivo.")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
