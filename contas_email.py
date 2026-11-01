"""Normalização e busca de contas por e-mail, sem diferenciar maiúsculas.

O cadastro gravava o e-mail do usuário exatamente como digitado (ex.:
"Cliente@Empresa.com.br"), mas a recuperação de senha buscava o endereço em
minúsculas com comparação exata: a conta não era encontrada e nenhum e-mail
saía, embora a tela dissesse que o link fora enviado. Agora:

  - cadastros novos gravam o e-mail normalizado (sem espaços, minúsculas) e
    recusam um endereço que já exista com outra combinação de maiúsculas;
  - login e recuperação procuram primeiro o texto exato digitado (preserva o
    comportamento atual) e, se não houver, a conta cujo e-mail coincide
    ignorando maiúsculas/minúsculas — desde que seja UMA só. Havendo mais de
    uma (registros legados conflitantes), nada é escolhido: a situação é
    registrada em log para o administrador resolver o cadastro.

Nenhum registro existente é alterado automaticamente.
"""

from dataclasses import dataclass

from sqlalchemy import func, select

from emails import email_valido
from models import Usuario


def normalizar_email(valor) -> str:
    """Forma canônica para gravar e comparar: sem espaços nas pontas e em minúsculas."""
    if not isinstance(valor, str):
        return ""
    return valor.strip().lower()


@dataclass(frozen=True)
class BuscaConta:
    usuario: Usuario | None
    # Mais de uma conta com o mesmo e-mail ignorando maiúsculas (dado legado).
    ambigua: bool = False


def buscar_usuario_por_email(sessao, email_digitado) -> BuscaConta:
    """Conta do e-mail digitado: texto exato primeiro; depois, sem diferenciar
    maiúsculas, apenas se houver uma única correspondência.

    Sempre UMA consulta (lower(email) = lower(digitado)), exista a conta ou
    não: o login equaliza o tempo de conta inexistente com o hash fictício, e
    uma segunda consulta só para "não encontrado" quebraria essa equalização.
    """
    digitado = email_digitado.strip() if isinstance(email_digitado, str) else ""
    if not digitado:
        return BuscaConta(None)
    candidatos = list(sessao.execute(
        select(Usuario).where(func.lower(Usuario.email) == digitado.lower())
    ).scalars().all())
    exatos = [u for u in candidatos if u.email == digitado]
    if exatos:
        return BuscaConta(exatos[0])  # e-mail é único: no máximo um
    if len(candidatos) == 1:
        return BuscaConta(candidatos[0])
    return BuscaConta(None, ambigua=len(candidatos) > 1)


def email_em_uso(sessao, email_normalizado: str, *, exceto_id: int | None = None) -> bool:
    """True se algum usuário já usa este e-mail (comparação sem maiúsculas)."""
    consulta = select(Usuario.id_usuario).where(func.lower(Usuario.email) == normalizar_email(email_normalizado))
    if exceto_id is not None:
        consulta = consulta.where(Usuario.id_usuario != exceto_id)
    # Só um id inteiro conta como "encontrado".
    return type(sessao.scalar(consulta.limit(1))) is int


__all__ = ["BuscaConta", "buscar_usuario_por_email", "email_em_uso", "email_valido", "normalizar_email"]
