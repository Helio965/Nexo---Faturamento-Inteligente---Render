"""NEXO-SEC-004: lixeira transacional sem alterar a condição administrativa.

Os helpers não confirmam nem revertem a transação. O chamador deve fazer
commit/rollback e só depois notificar ou desconectar conexões locais.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select

from models import Empresa, Usuario


@dataclass(frozen=True)
class ResultadoLixeira:
    empresa: Empresa
    usuarios: tuple[Usuario, ...]

    @property
    def contas_bloqueadas(self) -> int:
        return sum(not usuario.ativo for usuario in self.usuarios)


def bloquear_empresa(sessao, id_empresa: int) -> Empresa | None:
    """Primeiro lock de escrita: serializa o ciclo e inserções via sua FK."""
    with sessao.no_autoflush:
        return sessao.scalar(select(Empresa).where(
            Empresa.id_empresa == id_empresa,
        ).with_for_update().execution_options(populate_existing=True))


def bloquear_usuarios_empresa(sessao, id_empresa: int) -> tuple[Usuario, ...]:
    """Após bloquear a empresa, bloquear seus CLIENTE em ordem de PK.

    Leitores Socket.IO/notificações mantêm FOR SHARE no usuário e consultam
    a empresa por MVCC, sem adquirir seu lock. Atualizar a geração de todos os
    usuários faz a exclusão esperar as emissões anteriores, sem inverter locks.
    """
    with sessao.no_autoflush:
        return tuple(sessao.scalars(select(Usuario).where(
            Usuario.id_empresa == id_empresa,
            Usuario.role == "CLIENTE",
        ).order_by(Usuario.id_usuario).with_for_update().execution_options(
            populate_existing=True,
        )))


def excluir_empresa(sessao, id_empresa: int) -> ResultadoLixeira | None:
    """Bloqueia pela empresa e revoga sessões, preservando ativo e credencial."""
    empresa = bloquear_empresa(sessao, id_empresa)
    if empresa is None or empresa.deletado_em is not None:
        return None
    usuarios = bloquear_usuarios_empresa(sessao, id_empresa)
    agora = datetime.now(timezone.utc)
    empresa.deletado_em = agora
    empresa.data_atualizacao = agora
    for usuario in usuarios:
        usuario.geracao_autorizacao += 1
        usuario.data_atualizacao = agora
    return ResultadoLixeira(empresa, usuarios)


def restaurar_empresa(sessao, id_empresa: int) -> ResultadoLixeira | None:
    """Retira da lixeira sem ativar contas nem reutilizar gerações revogadas."""
    empresa = bloquear_empresa(sessao, id_empresa)
    if empresa is None or empresa.deletado_em is None:
        return None
    usuarios = bloquear_usuarios_empresa(sessao, id_empresa)
    empresa.deletado_em = None
    empresa.data_atualizacao = datetime.now(timezone.utc)
    return ResultadoLixeira(empresa, usuarios)
