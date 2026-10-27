import logging
import hashlib
import hmac
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlparse

from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app, has_request_context, make_response
from flask_login import login_user, logout_user, login_required, current_user
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadData
from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db, limiter
from models import Empresa, Usuario
from emails import email_recuperacao_senha, email_boas_vindas
from contract_policy import obter_situacao_contratual
from session_security import (
    CHAVE_CREDENCIAL, condicoes_empresa_acessivel, impressao_sessao,
    impressao_credencial_sessao, mesma_impressao, registrar_sessao,
    usuario_pode_acessar, vincular_geracao_autorizacao,
)

logger = logging.getLogger(__name__)

# Criação do Blueprint de Autenticação
auth_bp = Blueprint("auth", __name__)


def _destino_seguro(alvo: str) -> bool:
    """
    True se `alvo` é um caminho LOCAL seguro para redirect (mitiga open redirect).
    Rejeita URLs absolutas e protocol-relative (//evil.com, /\\evil.com), que o
    navegador trataria como destino externo.
    """
    if not alvo:
        return False
    parsed = urlparse(alvo)
    # Sem esquema e sem netloc = caminho relativo ao próprio site.
    return (
        not parsed.scheme
        and not parsed.netloc
        and alvo.startswith("/")
        and not alvo.startswith("//")
        and not alvo.startswith("/\\")
    )

# --- Tokens de senha v2: finalidade, credencial e consumo atômico ---
_ATIVACAO = "activation"
_RECUPERACAO = "recovery"
RESET_MAX_AGE = 900  # 15 minutos, em segundos


@dataclass(frozen=True)
class _CredencialEsperada:
    """Snapshot para o UPDATE; nunca publicar ou registrar o hash interno."""
    id_usuario: int
    senha_hash: str = field(repr=False)
    role: str
    primeiro_acesso: bool
    geracao_autorizacao: int
    id_empresa: int | None
    usuario: Usuario = field(repr=False, compare=False)


def _estado_credencial(usuario: Usuario) -> _CredencialEsperada:
    return _CredencialEsperada(
        usuario.id_usuario, usuario.senha_hash, usuario.role,
        bool(usuario.primeiro_acesso), usuario.geracao_autorizacao,
        usuario.id_empresa, usuario,
    )


def _serializer(finalidade: str) -> URLSafeTimedSerializer:
    """Assina, sem criptografar. Namespaces v2 não aceitam links antigos."""
    if finalidade not in (_ATIVACAO, _RECUPERACAO):
        raise ValueError("Finalidade de token inválida.")
    return URLSafeTimedSerializer(
        current_app.config["SECRET_KEY"], salt=f"nexo-password-{finalidade}-v2",
        signer_kwargs={"digest_method": hashlib.sha256},
    )


def _impressao_credencial(usuario) -> str:
    """HMAC padrão; o token não contém senha, e-mail ou hash de senha."""
    chave = current_app.config["SECRET_KEY"]
    if isinstance(chave, str):
        chave = chave.encode("utf-8")
    mensagem = b"nexo-password-credential-v2\0" + (
        f"{usuario.id_usuario}\0{usuario.senha_hash}".encode("utf-8")
    )
    mensagem = vincular_geracao_autorizacao(mensagem, usuario.geracao_autorizacao)
    return hmac.new(chave, mensagem, hashlib.sha256).hexdigest()


def _permite_finalidade(usuario, finalidade: str) -> bool:
    if usuario.role not in ("ADMIN", "CLIENTE"):
        return False
    pendente = usuario.role == "CLIENTE" and bool(usuario.primeiro_acesso)
    if finalidade == _ATIVACAO:
        return pendente
    # ADMIN pode conservar a flag legada sem precisar de ativação de cliente.
    return finalidade == _RECUPERACAO and not pendente


def _emitir_token(usuario: Usuario, finalidade: str) -> str:
    if (type(usuario.id_usuario) is not int or usuario.id_usuario <= 0
            or not isinstance(usuario.senha_hash, str) or not usuario.senha_hash):
        raise ValueError("Usuário persistido com credencial é obrigatório.")
    if not usuario_pode_acessar(usuario) or not _permite_finalidade(usuario, finalidade):
        raise ValueError("Conta não elegível para esta operação de senha.")
    return _serializer(finalidade).dumps({
        "v": 2, "uid": usuario.id_usuario, "purpose": finalidade,
        "credential": _impressao_credencial(usuario),
    })


def gerar_token_definir_senha(usuario: Usuario) -> str:
    """Emite exclusivamente ativação para CLIENTE persistido e pendente."""
    return _emitir_token(usuario, _ATIVACAO)


def gerar_token_recuperacao_senha(usuario: Usuario) -> str:
    """Emite recuperação para conta ativa que não aguarda ativação de cliente."""
    return _emitir_token(usuario, _RECUPERACAO)


def _falha_banco_senha(erro: SQLAlchemyError) -> None:
    db.session.rollback()
    # Não registrar SQL/params, tokens, hashes, senhas ou dados do usuário.
    logger.warning("Operação de senha indisponível (%s).", type(erro).__name__)


def _ler_token_senha(token: str, finalidade: str):
    if not isinstance(token, str) or not token or len(token) > 2048:
        return None
    try:
        dados = _serializer(finalidade).loads(token, max_age=RESET_MAX_AGE)
    except (SignatureExpired, BadData):
        return None
    if not isinstance(dados, dict) or set(dados) != {"v", "uid", "purpose", "credential"}:
        return None
    if (type(dados["v"]) is not int or dados["v"] != 2
            or type(dados["uid"]) is not int or dados["uid"] <= 0
            or dados["purpose"] != finalidade):
        return None
    impressao = dados["credential"]
    if (not isinstance(impressao, str) or len(impressao) != 64
            or any(c not in "0123456789abcdef" for c in impressao)):
        return None
    try:
        usuario = db.session.get(Usuario, dados["uid"], populate_existing=True)
        if (not usuario_pode_acessar(usuario)
                or not _permite_finalidade(usuario, finalidade)):
            return None
    except SQLAlchemyError as erro:
        _falha_banco_senha(erro)
        return None
    if not hmac.compare_digest(impressao, _impressao_credencial(usuario)):
        return None
    return _estado_credencial(usuario)


def _ler_token_reset(token: str):
    return _ler_token_senha(token, _RECUPERACAO)


def _ler_token_ativacao(token: str):
    return _ler_token_senha(token, _ATIVACAO)


def _atualizar_credencial(estado: _CredencialEsperada, nova_senha: str, *, renovar_sessao=False) -> bool:
    """CAS transacional: só uma requisição substitui a credencial esperada.

    O hash salgado muda mesmo ao escolher a mesma senha. No PostgreSQL em
    READ COMMITTED, um concorrente espera o lock e reavalia o WHERE: zero
    linhas após o primeiro commit. Rollback não consome o token.
    """
    novo_hash = generate_password_hash(nova_senha)
    comando = update(Usuario).where(
        Usuario.id_usuario == estado.id_usuario,
        Usuario.senha_hash == estado.senha_hash,
        Usuario.geracao_autorizacao == estado.geracao_autorizacao,
        Usuario.id_empresa == estado.id_empresa,
        Usuario.ativo.is_(True),
        or_(
            and_(Usuario.role == "ADMIN", Usuario.id_empresa.is_(None)),
            and_(Usuario.role == "CLIENTE", select(Empresa.id_empresa).where(
                Empresa.id_empresa == Usuario.id_empresa,
                *condicoes_empresa_acessivel(),
            ).exists()),
        ),
        Usuario.role == estado.role,
        Usuario.primeiro_acesso.is_(estado.primeiro_acesso),
    ).values(
        senha_hash=novo_hash, primeiro_acesso=False,
        data_atualizacao=datetime.now(timezone.utc),
    ).execution_options(synchronize_session=False)
    try:
        # Nunca alterar o objeto ORM antes do CAS: autoflush quebraria a condição.
        with db.session.no_autoflush:
            resultado = db.session.execute(comando)
        if resultado.rowcount != 1:
            db.session.rollback()
            return False
        renovar_cliente = (
            renovar_sessao and has_request_context()
            and session.get("_user_id") == str(estado.id_usuario)
            and session.get("boot_id") == current_app.config["BOOT_ID"]
            and mesma_impressao(impressao_sessao(estado), session.get(CHAVE_CREDENCIAL))
        )
        db.session.commit()
    except SQLAlchemyError as erro:
        _falha_banco_senha(erro)
        return False

    # Usar hash e geração que esta operação confirmou, nunca refresh de uma
    # senha ou exclusão/restauração posterior entre commit e renovação.
    impressao_atual = impressao_credencial_sessao(
        estado.id_usuario, novo_hash, estado.geracao_autorizacao,
    )
    if renovar_cliente:
        registrar_sessao(estado, impressao_esperada=impressao_atual)
    try:
        from realtime import revogar_conexoes_usuario
        revogar_conexoes_usuario(
            estado.id_usuario, impressao_atual,
            impressao_revogada=impressao_sessao(estado),
        )
    except Exception as erro:
        # Senha já confirmada: falha de transporte não muda seu resultado.
        # Salas por geração continuam negando dados aos sockets antigos.
        logger.warning("Revogação Socket.IO indisponível (%s).", type(erro).__name__)
    return True


_HASH_FICTICIO = None


def _conferir_senha_ficticia(senha: str) -> None:
    """E-mail inexistente custa o mesmo hash de uma conta real (anti-enumeração por tempo)."""
    global _HASH_FICTICIO
    if _HASH_FICTICIO is None:
        _HASH_FICTICIO = generate_password_hash("nexo-login-sem-conta")
    check_password_hash(_HASH_FICTICIO, senha)


def _conta_encerrada(usuario) -> bool:
    """Senha correta de CLIENTE ativo cuja empresa perdeu o vínculo contratual.

    Só depois de a senha ser validada; usuário inativo e empresa na lixeira
    continuam com a mensagem genérica. Falha de banco falha fechado.
    """
    if not usuario.ativo or usuario.role != "CLIENTE" or usuario.id_empresa is None:
        return False
    try:
        with db.session.no_autoflush:
            empresa = db.session.scalar(select(Empresa).where(
                Empresa.id_empresa == usuario.id_empresa,
            ).execution_options(populate_existing=True))
        return empresa is not None and obter_situacao_contratual(
            empresa, carregar_coberturas=False,
        ).conta_encerrada
    except SQLAlchemyError as erro:
        db.session.rollback()
        logger.warning("Situação contratual indisponível no login (%s).", type(erro).__name__)
        return False


def _validar_nova_senha(nova: str, confirma: str):
    """Regras mínimas de senha. Retorna mensagem de erro ou None se OK."""
    if len(nova) < 8:
        return "A senha deve ter ao menos 8 caracteres."
    if nova != confirma:
        return "As senhas não coincidem."
    return None


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])  # trava brute force de senha
def login():
    """Gere o ecrã e a lógica de login do utilizador."""
    # Se já estiver autenticado, vai DIRETO ao dashboard do perfil correto.
    # (Antes redirecionava para "index", mas "index" agora serve a landing
    # institucional — voltar pra lá seria UX hostil pra quem já está logado.)
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("cliente.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "")

        # Procura o utilizador no banco de dados pelo e-mail
        usuario = db.session.execute(
            select(Usuario).where(Usuario.email == email)
        ).scalar_one_or_none()

        # Valida o utilizador e a senha (usando o método check_senha definido no Model)
        if usuario and usuario.check_senha(senha):
            # Capturar a credencial cuja senha foi verificada antes de criar
            # a sessão; nunca adotar um hash posterior por refresh do ORM.
            impressao_login = impressao_sessao(usuario)
            if not usuario_pode_acessar(usuario):
                if _conta_encerrada(usuario):
                    # Página própria, sem login_user, flash ou redirect: nenhuma
                    # sessão autenticada nem dado do portal é entregue.
                    resposta = make_response(render_template("auth/conta_encerrada.html"))
                    resposta.headers["Cache-Control"] = "no-store"
                    return resposta
                flash("Esta conta está desativada. Contacte o administrador.", "danger")
                return render_template("auth/login.html", email_digitado=email)

            # Efetua o login na sessão (sem "remember": cookie morre ao fechar o
            # navegador). Carimba a sessão com o BOOT_ID atual para que um
            # restart do servidor invalide o login automaticamente.
            login_user(usuario, remember=False)
            registrar_sessao(usuario, impressao_esperada=impressao_login)

            # Trata o redirecionamento caso o utilizador tenha tentado aceder a uma
            # página protegida antes. Só aceitamos destinos LOCAIS (anti open redirect).
            next_page = request.args.get("next")
            if _destino_seguro(next_page):
                return redirect(next_page)

            # Redirecionamento padrão com base no perfil (Role)
            if usuario.is_admin:
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("cliente.dashboard"))
        
        if usuario is None:
            _conferir_senha_ficticia(senha)
        # Mensagem genérica por motivos de segurança (não revelar se o erro foi o e-mail ou a senha)
        flash("E-mail ou senha incorretos.", "danger")

    # Depois de uma tentativa errada, o e-mail digitado volta preenchido (só a senha é redigitada).
    return render_template("auth/login.html", email_digitado=request.form.get("email", "").strip())


@auth_bp.route("/logout")
@login_required
def logout():
    """Termina a sessão do utilizador."""
    logout_user()
    flash("Sessão terminada com sucesso.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/primeiro-acesso", methods=["GET", "POST"])
@login_required
def primeiro_acesso():
    """
    Troca obrigatória de senha no primeiro acesso do cliente.
    O guard em app.py manda o cliente para cá enquanto primeiro_acesso=True.
    Ao salvar, baixa a flag e libera o portal.
    """
    # Já trocou (ou é admin): não há o que fazer aqui.
    if not getattr(current_user, "primeiro_acesso", False):
        destino = "admin.dashboard" if current_user.is_admin else "cliente.dashboard"
        return redirect(url_for(destino))

    if request.method == "POST":
        nova = request.form.get("nova_senha", "")
        confirma = request.form.get("confirma_senha", "")
        erro = _validar_nova_senha(nova, confirma)
        if erro:
            flash(erro, "danger")
            return render_template("auth/primeiro_acesso.html")

        estado = _estado_credencial(current_user)
        if not _atualizar_credencial(estado, nova, renovar_sessao=True):
            flash("Não foi possível definir a senha. Faça login ou solicite um novo link.", "danger")
            return redirect(url_for("auth.login"))
        flash("Senha definida com sucesso. Bem-vindo(a) ao NEXO!", "success")
        return redirect(url_for("cliente.dashboard"))

    return render_template("auth/primeiro_acesso.html")


@auth_bp.route("/recuperar-senha", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])  # evita abuso do envio de e-mail
def recuperar_senha():
    """
    Solicita recuperação ou reenvio de ativação, conforme o estado da conta.
    A resposta é genérica mesmo em DEBUG e não expõe o link ao solicitante.
    """
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        try:
            usuario = db.session.execute(
                select(Usuario).where(Usuario.email == email)
            ).scalar_one_or_none()
            if usuario_pode_acessar(usuario):
                if _permite_finalidade(usuario, _ATIVACAO):
                    token = gerar_token_definir_senha(usuario)
                    link = url_for("auth.ativar_acesso", token=token, _external=True)
                    email_boas_vindas(usuario, link)
                else:
                    token = gerar_token_recuperacao_senha(usuario)
                    link = url_for("auth.resetar_senha", token=token, _external=True)
                    email_recuperacao_senha(usuario, link)
                logger.info("Solicitação de recuperação de senha processada.")
        except SQLAlchemyError as erro:
            _falha_banco_senha(erro)

        # Mensagem genérica sempre (anti-enumeração de e-mails).
        flash("Se o e-mail estiver cadastrado, enviamos um link de redefinição válido por 15 minutos.", "success")
        return redirect(url_for("auth.recuperar_senha"))

    return render_template("auth/recuperar_senha.html")


@auth_bp.route("/resetar-senha/<token>", methods=["GET", "POST"])
def resetar_senha(token):
    """
    Valida o token (assinatura + expiração de 15 min). Token adulterado ou
    expirado → 'Token inválido ou expirado'. Válido → permite definir nova senha.
    """
    estado = _ler_token_reset(token)
    if estado is None:
        flash("Token inválido ou expirado. Solicite um novo link de redefinição.", "danger")
        return redirect(url_for("auth.recuperar_senha"))

    if request.method == "POST":
        nova = request.form.get("nova_senha", "")
        confirma = request.form.get("confirma_senha", "")
        erro = _validar_nova_senha(nova, confirma)
        if erro:
            flash(erro, "danger")
            return render_template("auth/resetar_senha.html", token=token)

        if not _atualizar_credencial(estado, nova):
            flash("Token inválido ou expirado. Solicite um novo link de redefinição.", "danger")
            return redirect(url_for("auth.recuperar_senha"))
        flash("Senha redefinida com sucesso. Faça login com a nova senha.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/resetar_senha.html", token=token)


@auth_bp.route("/primeiro-acesso/<token>", methods=["GET", "POST"])
def ativar_acesso(token):
    """
    Ativação de conta via link do e-mail de boas-vindas (anônimo). Valida o token
    (15 min). Expirado/adulterado → tela amigável para solicitar novo link
    (recuperar-senha). Válido → o cliente define a senha e a conta é ativada.
    """
    estado = _ler_token_ativacao(token)
    if estado is None:
        flash(
            "Seu link de definição de senha é inválido ou expirou (validade de 15 minutos). "
            "Informe seu e-mail abaixo para receber um novo link.", "danger",
        )
        return redirect(url_for("auth.recuperar_senha"))

    usuario = estado.usuario

    if request.method == "POST":
        nova = request.form.get("nova_senha", "")
        confirma = request.form.get("confirma_senha", "")
        erro = _validar_nova_senha(nova, confirma)
        if erro:
            flash(erro, "danger")
            return render_template("auth/primeiro_acesso_token.html", token=token, usuario=usuario)

        if not _atualizar_credencial(estado, nova):
            flash("Seu link de definição de senha é inválido ou expirou. Solicite um novo link.", "danger")
            return redirect(url_for("auth.recuperar_senha"))
        flash("Senha definida com sucesso! Já pode acessar o portal.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/primeiro_acesso_token.html", token=token, usuario=usuario)
