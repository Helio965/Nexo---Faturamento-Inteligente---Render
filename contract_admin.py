"""Gestão contratual: operações administrativas transacionais e auditáveis.

Cada operação:
  1. bloqueia a empresa (company_security.bloquear_empresa, FOR UPDATE),
     mantendo a ordem Empresa -> Contrato -> Usuario dos demais fluxos;
  2. relê o contrato da MESMA empresa e confere a versão exibida no
     formulário (controle otimista contra telas desatualizadas);
  3. valida as regras, altera e grava EventoContratual na mesma transação;
  4. sincroniza Empresa.status_conta por aplicar_status_conta, que revoga as
     sessões dos CLIENTE ao entrar ou sair de CANCELADA (NEXO-AJ-06.1).
Nenhuma função confirma a transação: o chamador faz commit/rollback e só
depois desconecta os sockets revogados. Prazos usam contract_policy.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, select

from company_security import aplicar_status_conta, bloquear_empresa
from contract_policy import (
    agora, calcular_limite_exportacao_pdf, calcular_limite_suspensao, data_local,
    exigir_esquema_contratual, politica_prazos, utc, vigencia_efetiva,
)
from models import CoberturaPaga, Contrato, Empresa, EventoContratual, Plano, RegimeContratual

DATA_MINIMA = date(2000, 1, 1)
DATA_MAXIMA = date(2100, 12, 31)
VALOR_MAXIMO = Decimal("1000000.00")
TAMANHO_TEXTO_CURTO = 200
TAMANHO_TEXTO_LONGO = 2000
# Chave fixa do lock consultivo da reconciliação (PostgreSQL).
CHAVE_LOCK_RECONCILIACAO = 7_316_204_118
MOTIVO_EXPIRACAO = ("Prazo de suspensão encerrado sem renovação, nova contratação "
                    "ou prorrogação registrada.")


class ErroContratual(Exception):
    """Regra contratual violada; a mensagem é segura para o administrador."""


@dataclass(frozen=True)
class ResultadoOperacao:
    empresa: Empresa
    contrato: Contrato | None
    evento: EventoContratual
    revogados: tuple = ()


@dataclass(frozen=True)
class DadosContrato:
    id_plano: int
    valor_mensal: Decimal
    data_inicio: date
    data_fim: date | None = None
    data_formalizacao: date | None = None
    referencia_formalizacao: str | None = None
    meses_suspensao: int | None = None
    observacoes: str | None = None


# ---------------------------------------------------------------------------
# Validação e utilitários
# ---------------------------------------------------------------------------
def texto(valor, nome: str, *, obrigatorio: bool = False, maximo: int = TAMANHO_TEXTO_LONGO):
    valor = (valor or "").strip() if isinstance(valor, str) or valor is None else None
    if valor is None:
        raise ErroContratual(f"{nome}: valor inválido.")
    if obrigatorio and not valor:
        raise ErroContratual(f"Informe {nome}.")
    if len(valor) > maximo:
        raise ErroContratual(f"{nome}: no máximo {maximo} caracteres.")
    return valor or None


_VALOR_BR = re.compile(r"(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d{1,2})?")
_VALOR_PONTO = re.compile(r"\d+(?:\.\d{1,2})?")


def valor_monetario(valor) -> Decimal:
    """Valor em reais: '650', '650,00', '1.500' (mil e quinhentos), '1.234,56'
    ou '650.00' (ponto decimal com até duas casas, como o preenchimento automático).

    Ponto seguido de exatamente três dígitos é separador de milhar, nunca
    decimal; formatos ambíguos ou mistos ('1,234.56') são recusados.
    """
    if isinstance(valor, Decimal):
        bruto = valor
    else:
        s = valor.strip() if isinstance(valor, str) else ("" if valor is None else str(valor))
        if _VALOR_BR.fullmatch(s) and ("," in s or "." in s and not _VALOR_PONTO.fullmatch(s)):
            s = s.replace(".", "").replace(",", ".")
        elif not _VALOR_PONTO.fullmatch(s):
            raise ErroContratual("Valor mensal contratado inválido. Use o formato 1.234,56.")
        try:
            bruto = Decimal(s)
        except (InvalidOperation, ValueError):
            raise ErroContratual("Valor mensal contratado inválido.") from None
    if not bruto.is_finite() or bruto < 0 or bruto > VALOR_MAXIMO:
        raise ErroContratual("Valor mensal contratado fora do intervalo permitido.")
    if bruto != bruto.quantize(Decimal("0.01")):
        raise ErroContratual("Valor mensal contratado aceita no máximo duas casas decimais.")
    return bruto.quantize(Decimal("0.01"))


def _data_valida(valor: date | None, nome: str, *, obrigatoria: bool = False):
    if valor is None:
        if obrigatoria:
            raise ErroContratual(f"Informe {nome}.")
        return None
    if type(valor) is not date or not DATA_MINIMA <= valor <= DATA_MAXIMA:
        raise ErroContratual(f"{nome}: data fora do intervalo permitido.")
    return valor


def _serializar(valor):
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return str(valor)
    raise TypeError(type(valor).__name__)


def _detalhes(**valores) -> str:
    return json.dumps({k: v for k, v in valores.items() if v is not None},
                      default=_serializar, ensure_ascii=False, sort_keys=True)


def _instante(instante):
    return agora() if instante is None else utc(instante)


def _bloquear(sessao, id_empresa: int) -> Empresa:
    exigir_esquema_contratual(sessao)
    empresa = bloquear_empresa(sessao, id_empresa)
    if empresa is None:
        raise ErroContratual("Empresa não encontrada.")
    if empresa.deletado_em is not None:
        raise ErroContratual("A empresa está na lixeira: restaure-a antes de alterar contratos.")
    return empresa


def _contrato(sessao, empresa: Empresa, id_contrato, versao=None) -> Contrato:
    """Contrato bloqueado e pertencente à empresa já bloqueada."""
    if type(id_contrato) is not int:
        raise ErroContratual("Contrato não encontrado para esta empresa.")
    with sessao.no_autoflush:
        contrato = sessao.scalar(select(Contrato).where(
            Contrato.id_contrato == id_contrato,
            Contrato.id_empresa == empresa.id_empresa,
        ).with_for_update().execution_options(populate_existing=True))
    if contrato is None:
        raise ErroContratual("Contrato não encontrado para esta empresa.")
    if versao is not None and versao != contrato.versao:
        raise ErroContratual("O contrato foi alterado por outra operação. Recarregue a página e confira antes de salvar.")
    return contrato


def _contrato_aplicavel_bloqueado(sessao, empresa: Empresa) -> Contrato | None:
    with sessao.no_autoflush:
        return sessao.scalar(select(Contrato).where(
            Contrato.id_empresa == empresa.id_empresa,
            Contrato.situacao.in_(("ATIVO", "SUSPENSO")),
        ).with_for_update().execution_options(populate_existing=True))


def _evento(sessao, empresa, contrato, tipo, *, instante, responsavel=None,
            anterior=None, posterior=None, justificativa=None, detalhes=None, cobertura=None):
    evento = EventoContratual(
        id_empresa=empresa.id_empresa,
        id_contrato=contrato.id_contrato if contrato is not None else None,
        id_cobertura=cobertura.id_cobertura if cobertura is not None else None,
        tipo=tipo, ocorrido_em=instante,
        origem="ADMIN" if responsavel is not None else "RECONCILIACAO",
        id_usuario_responsavel=responsavel.id_usuario if responsavel is not None else None,
        situacao_anterior=anterior, situacao_posterior=posterior,
        justificativa=justificativa, detalhes=detalhes,
    )
    sessao.add(evento)
    return evento


def _regime(sessao, empresa: Empresa) -> RegimeContratual | None:
    with sessao.no_autoflush:
        return sessao.scalar(select(RegimeContratual).where(
            RegimeContratual.id_empresa == empresa.id_empresa,
        ).with_for_update().execution_options(populate_existing=True))


def _exigir_admin(responsavel):
    if responsavel is None or getattr(responsavel, "role", None) != "ADMIN" or not responsavel.ativo:
        raise ErroContratual("Somente administradores ativos podem alterar contratos.")


def _sincronizar_status(sessao, empresa: Empresa, novo_status: str, instante) -> tuple:
    if empresa.status_conta == novo_status:
        return ()
    revogados = aplicar_status_conta(sessao, empresa, novo_status)
    empresa.data_atualizacao = instante
    return revogados


def _validar_dados(sessao, dados: DadosContrato, instante) -> Plano:
    if type(dados.id_plano) is not int:
        raise ErroContratual("Selecione um plano válido.")
    plano = sessao.get(Plano, dados.id_plano)
    if plano is None or not plano.ativo:
        raise ErroContratual("Selecione um plano ativo do catálogo.")
    valor_monetario(dados.valor_mensal)
    _data_valida(dados.data_inicio, "o início da vigência", obrigatoria=True)
    _data_valida(dados.data_fim, "o término da vigência")
    if dados.data_fim is not None and dados.data_fim < dados.data_inicio:
        raise ErroContratual("O término da vigência não pode ser anterior ao início.")
    _data_valida(dados.data_formalizacao, "a data de formalização")
    if dados.data_formalizacao is not None and dados.data_formalizacao > data_local(instante):
        raise ErroContratual("A data de formalização não pode estar no futuro.")
    if dados.meses_suspensao is not None:
        maximo = politica_prazos().meses_suspensao
        if type(dados.meses_suspensao) is not int or not 1 <= dados.meses_suspensao <= maximo:
            raise ErroContratual(f"O prazo contratual de suspensão deve ficar entre 1 e {maximo} meses.")
    texto(dados.referencia_formalizacao, "a referência da formalização", maximo=TAMANHO_TEXTO_CURTO)
    texto(dados.observacoes, "as observações")
    return plano


def _novo_contrato(empresa, dados: DadosContrato, responsavel, instante, anterior=None) -> Contrato:
    return Contrato(
        id_empresa=empresa.id_empresa, id_plano=dados.id_plano,
        id_contrato_anterior=anterior.id_contrato if anterior is not None else None,
        valor_mensal_contratado=valor_monetario(dados.valor_mensal),
        data_inicio=dados.data_inicio, data_fim=dados.data_fim,
        data_formalizacao=dados.data_formalizacao,
        referencia_formalizacao=texto(dados.referencia_formalizacao, "a referência da formalização",
                                      maximo=TAMANHO_TEXTO_CURTO),
        situacao="ATIVO", meses_suspensao=dados.meses_suspensao,
        observacoes=texto(dados.observacoes, "as observações"),
        id_usuario_admin_responsavel=responsavel.id_usuario,
        versao=1, data_criacao=instante,
    )


def _dados_evento(contrato: Contrato) -> dict:
    return dict(id_plano=contrato.id_plano, valor_mensal=contrato.valor_mensal_contratado,
                data_inicio=contrato.data_inicio, data_fim=contrato.data_fim)


def _tocar(contrato: Contrato, instante):
    contrato.versao += 1
    contrato.data_atualizacao = instante


# ---------------------------------------------------------------------------
# Contratação, renovação e alteração de plano
# ---------------------------------------------------------------------------
def criar_contrato(sessao, id_empresa: int, dados: DadosContrato, *, responsavel,
                   justificativa=None, instante=None) -> ResultadoOperacao:
    """Primeiro contrato ou nova contratação após cancelamento/encerramento.

    Empresa CANCELADA volta a ATIVA: aplicar_status_conta revoga as sessões
    antigas e exige novo login; os direitos continuam dependendo da cobertura.
    Empresa SUSPENSA continua SUSPENSA (conciliação): o ADMIN registra em
    seguida a suspensão com o instante real, ou reativa explicitamente.
    """
    _exigir_admin(responsavel)
    instante = _instante(instante)
    empresa = _bloquear(sessao, id_empresa)
    if _contrato_aplicavel_bloqueado(sessao, empresa) is not None:
        raise ErroContratual("A empresa já possui contrato vigente: use a renovação ou a alteração de plano.")
    _validar_dados(sessao, dados, instante)
    justificativa = texto(justificativa, "a justificativa")
    contrato = _novo_contrato(empresa, dados, responsavel, instante)
    sessao.add(contrato)
    sessao.flush()
    status_anterior = empresa.status_conta
    revogados = (() if status_anterior == "SUSPENSA"
                 else _sincronizar_status(sessao, empresa, "ATIVA", instante))
    empresa.id_plano_atual = dados.id_plano
    evento = _evento(
        sessao, empresa, contrato, "CONTRATACAO", instante=instante, responsavel=responsavel,
        anterior=None, posterior="ATIVO", justificativa=justificativa,
        detalhes=_detalhes(status_conta_anterior=status_anterior, **_dados_evento(contrato)),
    )
    return ResultadoOperacao(empresa, contrato, evento, revogados)


def renovar_contrato(sessao, id_empresa: int, id_contrato: int, versao: int, dados: DadosContrato, *,
                     responsavel, justificativa=None, instante=None,
                     alteracao_plano: bool = False) -> ResultadoOperacao:
    """Nova vigência ligada à anterior, que passa a ENCERRADO sem perder dados.

    Serve à renovação e à alteração de plano. O contrato anterior conserva
    plano, valor e período; as análises antigas conservam id_plano_referencia.
    """
    _exigir_admin(responsavel)
    instante = _instante(instante)
    empresa = _bloquear(sessao, id_empresa)
    atual = _contrato(sessao, empresa, id_contrato, versao)
    if atual.situacao not in ("ATIVO", "SUSPENSO"):
        raise ErroContratual("Somente contratos ativos ou suspensos podem ser renovados ou alterados.")
    _validar_dados(sessao, dados, instante)
    if dados.data_inicio <= atual.data_inicio:
        raise ErroContratual("A nova vigência deve começar depois do início do contrato atual.")
    # O contrato atual passa a ENCERRADO agora: um sucessor com início futuro
    # deixaria o intervalo até lá sem contrato vigente (renovação agendada não
    # é suportada; registre-a quando a nova vigência começar).
    if dados.data_inicio > data_local(instante):
        raise ErroContratual("A nova vigência não pode começar no futuro: registre a renovação "
                             "ou a troca de plano a partir da data de início.")
    if alteracao_plano and dados.id_plano == atual.id_plano:
        raise ErroContratual("Selecione um plano diferente do atual para registrar a alteração.")
    justificativa = texto(justificativa, "a justificativa", obrigatorio=alteracao_plano)
    situacao_anterior = atual.situacao
    atual.situacao = "ENCERRADO"
    atual.encerrado_em = instante
    _tocar(atual, instante)
    sessao.flush()  # libera o índice único parcial antes do novo contrato vigente
    novo = _novo_contrato(empresa, dados, responsavel, instante, anterior=atual)
    sessao.add(novo)
    sessao.flush()
    status_anterior = empresa.status_conta
    revogados = _sincronizar_status(sessao, empresa, "ATIVA", instante)
    empresa.id_plano_atual = dados.id_plano
    evento = _evento(
        sessao, empresa, novo, "ALTERACAO_PLANO" if alteracao_plano else "RENOVACAO",
        instante=instante, responsavel=responsavel, anterior=situacao_anterior,
        posterior="ATIVO", justificativa=justificativa,
        detalhes=_detalhes(
            contrato_anterior=atual.id_contrato, status_conta_anterior=status_anterior,
            plano_anterior=atual.id_plano, valor_anterior=atual.valor_mensal_contratado,
            inicio_anterior=atual.data_inicio, fim_anterior=atual.data_fim,
            **_dados_evento(novo),
        ),
    )
    return ResultadoOperacao(empresa, novo, evento, revogados)


# ---------------------------------------------------------------------------
# Suspensão, prorrogação, reativação e cancelamento
# ---------------------------------------------------------------------------
def suspender_contrato(sessao, id_empresa: int, id_contrato: int, versao: int, *, motivo,
                       responsavel, suspenso_em: datetime | None = None,
                       instante=None) -> ResultadoOperacao:
    """Registra o instante oficial da suspensão e grava os prazos calculados."""
    _exigir_admin(responsavel)
    instante = _instante(instante)
    politica = politica_prazos()
    empresa = _bloquear(sessao, id_empresa)
    contrato = _contrato(sessao, empresa, id_contrato, versao)
    if contrato.situacao != "ATIVO":
        raise ErroContratual("Somente contratos ativos podem ser suspensos.")
    motivo = texto(motivo, "o motivo da suspensão", obrigatorio=True)
    suspenso_em = instante if suspenso_em is None else utc(suspenso_em)
    if not DATA_MINIMA.year <= suspenso_em.year <= DATA_MAXIMA.year:
        raise ErroContratual("Início da suspensão fora do intervalo permitido.")
    if suspenso_em > instante:
        raise ErroContratual("O início da suspensão não pode estar no futuro.")
    inicio_contrato = datetime.combine(contrato.data_inicio, time.min, politica.fuso)
    # Conciliação: o cadastro do contrato pode ser posterior à suspensão real,
    # por isso só uma mudança de situação já registrada (ex.: reativação)
    # limita o retroativo, além do início da vigência.
    ultima_mudanca = contrato.data_atualizacao
    if suspenso_em < utc(inicio_contrato) or (ultima_mudanca is not None and suspenso_em < ultima_mudanca):
        raise ErroContratual("O início da suspensão não pode ser anterior ao início do contrato "
                             "nem à última mudança de situação registrada nele.")
    limite = calcular_limite_suspensao(suspenso_em, contrato.meses_suspensao, politica)
    if limite <= instante:
        raise ErroContratual("Com essa data o prazo de suspensão já estaria encerrado. Revise o início informado.")
    limite_pdf = calcular_limite_exportacao_pdf(suspenso_em, limite, politica)
    contrato.situacao = "SUSPENSO"
    contrato.suspenso_em = suspenso_em
    contrato.suspensao_motivo = motivo
    contrato.suspensao_limite_original = contrato.suspensao_limite = limite
    contrato.pdf_limite_original = contrato.pdf_limite = limite_pdf
    _tocar(contrato, instante)
    revogados = _sincronizar_status(sessao, empresa, "SUSPENSA", instante)
    evento = _evento(
        sessao, empresa, contrato, "SUSPENSAO", instante=instante, responsavel=responsavel,
        anterior="ATIVO", posterior="SUSPENSO", justificativa=motivo,
        detalhes=_detalhes(
            suspenso_em=suspenso_em, suspensao_limite=limite, pdf_limite=limite_pdf,
            meses_suspensao=contrato.meses_suspensao or politica.meses_suspensao,
            dias_exportacao_pdf=politica.dias_exportacao_pdf, fuso=politica.fuso.key,
        ),
    )
    return ResultadoOperacao(empresa, contrato, evento, revogados)


def registrar_prorrogacao(sessao, id_empresa: int, id_contrato: int, versao: int, *,
                          novo_limite: datetime, justificativa, responsavel,
                          novo_limite_pdf: datetime | None = None,
                          autorizacao_pdf: bool = False, instante=None) -> ResultadoOperacao:
    """Move o limite vigente da suspensão; o original permanece gravado.

    Não registra pagamento nem amplia a exportação de PDF, salvo autorização
    contratual específica informada explicitamente.
    """
    _exigir_admin(responsavel)
    instante = _instante(instante)
    empresa = _bloquear(sessao, id_empresa)
    contrato = _contrato(sessao, empresa, id_contrato, versao)
    if contrato.situacao != "SUSPENSO":
        raise ErroContratual("Somente suspensões registradas podem ser prorrogadas.")
    justificativa = texto(justificativa, "a justificativa do acordo", obrigatorio=True)
    novo_limite = utc(novo_limite)
    if not DATA_MINIMA.year <= novo_limite.year <= DATA_MAXIMA.year or (
            novo_limite_pdf is not None and not DATA_MINIMA.year <= utc(novo_limite_pdf).year <= DATA_MAXIMA.year):
        raise ErroContratual("Nova data-limite fora do intervalo permitido.")
    if novo_limite <= contrato.suspenso_em:
        raise ErroContratual("A nova data-limite não pode ser anterior ao início da suspensão.")
    if novo_limite <= contrato.suspensao_limite:
        raise ErroContratual("A nova data-limite deve ser posterior à data-limite vigente.")
    if novo_limite <= instante:
        raise ErroContratual("A nova data-limite deve estar no futuro.")
    pdf_anterior = contrato.pdf_limite
    if novo_limite_pdf is not None or autorizacao_pdf:
        if not autorizacao_pdf or novo_limite_pdf is None:
            raise ErroContratual("A ampliação da exportação de PDF exige a data e a confirmação "
                                 "da autorização contratual específica.")
        novo_limite_pdf = utc(novo_limite_pdf)
        if novo_limite_pdf <= contrato.pdf_limite or novo_limite_pdf > novo_limite:
            raise ErroContratual("O novo prazo de PDF deve ser posterior ao atual e não pode "
                                 "ultrapassar a nova data-limite da suspensão.")
        contrato.pdf_limite = novo_limite_pdf
    limite_anterior = contrato.suspensao_limite
    contrato.suspensao_limite = novo_limite
    _tocar(contrato, instante)
    evento = _evento(
        sessao, empresa, contrato, "PRORROGACAO", instante=instante, responsavel=responsavel,
        anterior="SUSPENSO", posterior="SUSPENSO", justificativa=justificativa,
        detalhes=_detalhes(
            suspensao_limite_original=contrato.suspensao_limite_original,
            suspensao_limite_anterior=limite_anterior, suspensao_limite_novo=novo_limite,
            pdf_limite_anterior=pdf_anterior, pdf_limite_novo=contrato.pdf_limite,
            ampliacao_pdf=bool(autorizacao_pdf),
        ),
    )
    return ResultadoOperacao(empresa, contrato, evento)


def reativar_contrato(sessao, id_empresa: int, id_contrato: int, versao: int, *, justificativa,
                      responsavel, instante=None) -> ResultadoOperacao:
    """Encerra a suspensão ainda dentro do prazo; após o limite, só renovação."""
    _exigir_admin(responsavel)
    instante = _instante(instante)
    empresa = _bloquear(sessao, id_empresa)
    contrato = _contrato(sessao, empresa, id_contrato, versao)
    if contrato.situacao != "SUSPENSO":
        raise ErroContratual("Somente contratos suspensos podem ser reativados.")
    if instante >= contrato.suspensao_limite:
        raise ErroContratual("O prazo da suspensão já terminou: registre uma renovação ou nova "
                             "contratação (ou uma prorrogação acordada).")
    justificativa = texto(justificativa, "a justificativa", obrigatorio=True)
    detalhes = _detalhes(suspenso_em=contrato.suspenso_em, suspensao_limite=contrato.suspensao_limite,
                         pdf_limite=contrato.pdf_limite, suspensao_motivo=contrato.suspensao_motivo)
    contrato.situacao = "ATIVO"
    contrato.suspenso_em = contrato.suspensao_motivo = None
    contrato.suspensao_limite = contrato.suspensao_limite_original = None
    contrato.pdf_limite = contrato.pdf_limite_original = None
    _tocar(contrato, instante)
    revogados = _sincronizar_status(sessao, empresa, "ATIVA", instante)
    evento = _evento(
        sessao, empresa, contrato, "REATIVACAO", instante=instante, responsavel=responsavel,
        anterior="SUSPENSO", posterior="ATIVO", justificativa=justificativa, detalhes=detalhes,
    )
    return ResultadoOperacao(empresa, contrato, evento, revogados)


def _cancelar(sessao, empresa: Empresa, contrato: Contrato, motivo: str, instante,
              responsavel=None, detalhes=None) -> ResultadoOperacao:
    anterior = contrato.situacao
    contrato.situacao = "CANCELADO"
    contrato.cancelado_em = instante
    contrato.cancelamento_motivo = motivo
    _tocar(contrato, instante)
    revogados = _sincronizar_status(sessao, empresa, "CANCELADA", instante)
    evento = _evento(
        sessao, empresa, contrato, "CANCELAMENTO", instante=instante, responsavel=responsavel,
        anterior=anterior, posterior="CANCELADO", justificativa=motivo, detalhes=detalhes,
    )
    return ResultadoOperacao(empresa, contrato, evento, revogados)


def cancelar_contrato(sessao, id_empresa: int, id_contrato: int, versao: int, *, motivo,
                      responsavel, instante=None) -> ResultadoOperacao:
    _exigir_admin(responsavel)
    instante = _instante(instante)
    empresa = _bloquear(sessao, id_empresa)
    contrato = _contrato(sessao, empresa, id_contrato, versao)
    if contrato.situacao not in ("ATIVO", "SUSPENSO"):
        raise ErroContratual("Somente contratos ativos ou suspensos podem ser cancelados.")
    motivo = texto(motivo, "o motivo do cancelamento", obrigatorio=True)
    return _cancelar(sessao, empresa, contrato, motivo, instante, responsavel,
                     _detalhes(suspensao_limite=contrato.suspensao_limite))


# ---------------------------------------------------------------------------
# Coberturas pagas
# ---------------------------------------------------------------------------
def registrar_cobertura(sessao, id_empresa: int, id_contrato: int, *, periodo_inicio: date,
                        periodo_fim: date, referencia, responsavel,
                        instante=None) -> ResultadoOperacao:
    """Confirma administrativamente um período pago dentro da vigência do contrato."""
    _exigir_admin(responsavel)
    instante = _instante(instante)
    empresa = _bloquear(sessao, id_empresa)
    contrato = _contrato(sessao, empresa, id_contrato)
    _data_valida(periodo_inicio, "o início do período pago", obrigatoria=True)
    _data_valida(periodo_fim, "o fim do período pago", obrigatoria=True)
    if periodo_fim < periodo_inicio:
        raise ErroContratual("O fim do período pago não pode ser anterior ao início.")
    inicio_vigencia, fim_vigencia = vigencia_efetiva(contrato, sessao=sessao)
    if periodo_inicio < inicio_vigencia or (fim_vigencia is not None and periodo_fim > fim_vigencia):
        raise ErroContratual("O período pago precisa estar dentro da vigência do contrato. A vigência "
                             "efetiva termina no término previsto, na renovação ou no cancelamento.")
    referencia = texto(referencia, "a referência da confirmação", obrigatorio=True,
                       maximo=TAMANHO_TEXTO_CURTO)
    conflito = sessao.scalar(select(CoberturaPaga).where(
        CoberturaPaga.id_empresa == empresa.id_empresa,
        CoberturaPaga.revogada_em.is_(None),
        CoberturaPaga.periodo_inicio <= periodo_fim,
        CoberturaPaga.periodo_fim >= periodo_inicio,
    ).limit(1))
    if conflito is not None:
        raise ErroContratual(
            "Já existe cobertura paga de "
            f"{conflito.periodo_inicio:%d/%m/%Y} a {conflito.periodo_fim:%d/%m/%Y} "
            "que se sobrepõe a este período. Revogue-a antes, se for uma correção."
        )
    cobertura = CoberturaPaga(
        id_contrato=contrato.id_contrato, id_empresa=empresa.id_empresa,
        periodo_inicio=periodo_inicio, periodo_fim=periodo_fim,
        referencia_confirmacao=referencia, confirmado_em=instante,
        id_usuario_admin_confirmacao=responsavel.id_usuario, data_criacao=instante,
    )
    sessao.add(cobertura)
    sessao.flush()
    evento = _evento(
        sessao, empresa, contrato, "COBERTURA_CONFIRMADA", instante=instante,
        responsavel=responsavel, anterior=contrato.situacao, posterior=contrato.situacao,
        justificativa=referencia, cobertura=cobertura,
        detalhes=_detalhes(periodo_inicio=periodo_inicio, periodo_fim=periodo_fim),
    )
    return ResultadoOperacao(empresa, contrato, evento)


def revogar_cobertura(sessao, id_empresa: int, id_cobertura: int, *, motivo, responsavel,
                      instante=None) -> ResultadoOperacao:
    """Revoga sem apagar: o registro e o evento permanecem para auditoria."""
    _exigir_admin(responsavel)
    instante = _instante(instante)
    empresa = _bloquear(sessao, id_empresa)
    if type(id_cobertura) is not int:
        raise ErroContratual("Cobertura não encontrada para esta empresa.")
    with sessao.no_autoflush:
        cobertura = sessao.scalar(select(CoberturaPaga).where(
            CoberturaPaga.id_cobertura == id_cobertura,
            CoberturaPaga.id_empresa == empresa.id_empresa,
        ).with_for_update().execution_options(populate_existing=True))
    if cobertura is None:
        raise ErroContratual("Cobertura não encontrada para esta empresa.")
    if cobertura.revogada_em is not None:
        raise ErroContratual("Esta cobertura já foi revogada.")
    motivo = texto(motivo, "o motivo da revogação", obrigatorio=True)
    contrato = _contrato(sessao, empresa, cobertura.id_contrato)
    cobertura.revogada_em = instante
    cobertura.revogacao_motivo = motivo
    cobertura.id_usuario_admin_revogacao = responsavel.id_usuario
    evento = _evento(
        sessao, empresa, contrato, "COBERTURA_REVOGADA", instante=instante,
        responsavel=responsavel, anterior=contrato.situacao, posterior=contrato.situacao,
        justificativa=motivo, cobertura=cobertura,
        detalhes=_detalhes(periodo_inicio=cobertura.periodo_inicio, periodo_fim=cobertura.periodo_fim,
                           referencia=cobertura.referencia_confirmacao),
    )
    return ResultadoOperacao(empresa, contrato, evento)


# ---------------------------------------------------------------------------
# Habilitação gradual das regras por empresa
# ---------------------------------------------------------------------------
def ativar_regras_contratuais(sessao, id_empresa: int, *, justificativa, responsavel,
                              instante=None) -> ResultadoOperacao:
    """Passa a empresa ao regime contratual após a conciliação administrativa."""
    _exigir_admin(responsavel)
    instante = _instante(instante)
    empresa = _bloquear(sessao, id_empresa)
    if _regime(sessao, empresa) is not None:
        raise ErroContratual("As regras contratuais já estão ativas para esta empresa.")
    contrato = _contrato_aplicavel_bloqueado(sessao, empresa)
    if contrato is None:
        raise ErroContratual("Registre um contrato vigente antes de ativar as regras contratuais.")
    if contrato.situacao == "SUSPENSO" and instante >= contrato.suspensao_limite:
        raise ErroContratual("A suspensão deste contrato já expirou: regularize-o antes de ativar as regras.")
    esperado = "SUSPENSA" if contrato.situacao == "SUSPENSO" else "ATIVA"
    if empresa.status_conta != esperado:
        raise ErroContratual(f"O status da empresa ({empresa.status_conta}) difere do contrato "
                             f"({contrato.situacao}): registre a suspensão com o instante real, ou "
                             "reative, antes de ativar as regras.")
    justificativa = texto(justificativa, "a justificativa", obrigatorio=True)
    status_anterior = empresa.status_conta
    revogados = _sincronizar_status(
        sessao, empresa, "SUSPENSA" if contrato.situacao == "SUSPENSO" else "ATIVA", instante,
    )
    sessao.add(RegimeContratual(id_empresa=empresa.id_empresa, ativado_em=instante,
                                id_usuario_admin_ativacao=responsavel.id_usuario))
    empresa.data_atualizacao = instante
    coberturas = sessao.scalar(select(func.count(CoberturaPaga.id_cobertura)).where(
        CoberturaPaga.id_empresa == empresa.id_empresa, CoberturaPaga.revogada_em.is_(None),
    ))
    evento = _evento(
        sessao, empresa, contrato, "REGRAS_ATIVADAS", instante=instante, responsavel=responsavel,
        anterior=contrato.situacao, posterior=contrato.situacao, justificativa=justificativa,
        detalhes=_detalhes(status_conta_anterior=status_anterior, coberturas_vigentes=coberturas),
    )
    return ResultadoOperacao(empresa, contrato, evento, revogados)


def desativar_regras_contratuais(sessao, id_empresa: int, *, justificativa, responsavel,
                                 instante=None) -> ResultadoOperacao:
    """Retorno auditado ao regime legado (contingência de implantação)."""
    _exigir_admin(responsavel)
    instante = _instante(instante)
    empresa = _bloquear(sessao, id_empresa)
    regime = _regime(sessao, empresa)
    if regime is None:
        raise ErroContratual("As regras contratuais já estão inativas para esta empresa.")
    justificativa = texto(justificativa, "a justificativa", obrigatorio=True)
    contrato = _contrato_aplicavel_bloqueado(sessao, empresa)
    sessao.delete(regime)
    empresa.data_atualizacao = instante
    situacao = contrato.situacao if contrato is not None else None
    evento = _evento(
        sessao, empresa, contrato, "REGRAS_DESATIVADAS", instante=instante,
        responsavel=responsavel, anterior=situacao, posterior=situacao,
        justificativa=justificativa,
        detalhes=_detalhes(ativado_em=regime.ativado_em,
                           ativado_por=regime.id_usuario_admin_ativacao),
    )
    return ResultadoOperacao(empresa, contrato, evento)


# ---------------------------------------------------------------------------
# Reconciliação de vencimentos
# ---------------------------------------------------------------------------
@dataclass
class RelatorioReconciliacao:
    instante: datetime
    simulacao: bool
    bloqueada: bool = False
    candidatos: list = field(default_factory=list)
    cancelados: list = field(default_factory=list)
    revogados: list = field(default_factory=list)


def _candidatos_vencidos(sessao, instante):
    return list(sessao.execute(
        select(Empresa.id_empresa, Contrato.id_contrato, Contrato.suspensao_limite)
        .join(Contrato, Contrato.id_empresa == Empresa.id_empresa)
        .join(RegimeContratual, RegimeContratual.id_empresa == Empresa.id_empresa)
        .where(
            Empresa.deletado_em.is_(None),
            Contrato.situacao == "SUSPENSO",
            Contrato.suspensao_limite <= instante,
        ).order_by(Empresa.id_empresa)
    ).all())


def reconciliar_vencimentos(sessao, *, aplicar: bool = False, instante=None,
                            acionado_por=None) -> RelatorioReconciliacao:
    """Cancela suspensões vencidas no regime contratual. Idempotente.

    Simulação (padrão) só lista candidatos. Na aplicação, um lock consultivo
    de transação impede execuções concorrentes no PostgreSQL; cada empresa é
    bloqueada e reavaliada antes da mudança, então uma prorrogação ou
    renovação gravada no intervalo é respeitada. O chamador confirma a
    transação e depois desconecta os sockets revogados. `acionado_por` (ADMIN
    que usou o botão) fica nos detalhes do evento; a origem continua sendo a
    reconciliação, que aplica a regra e não uma decisão individual.
    """
    exigir_esquema_contratual(sessao)
    instante = _instante(instante)
    relatorio = RelatorioReconciliacao(instante=instante, simulacao=not aplicar)
    if aplicar and sessao.get_bind().dialect.name == "postgresql":
        if not sessao.scalar(select(func.pg_try_advisory_xact_lock(CHAVE_LOCK_RECONCILIACAO))):
            relatorio.bloqueada = True
            return relatorio
    for id_empresa, id_contrato, limite in _candidatos_vencidos(sessao, instante):
        relatorio.candidatos.append({"id_empresa": id_empresa, "id_contrato": id_contrato,
                                     "suspensao_limite": limite})
        if not aplicar:
            continue
        empresa = bloquear_empresa(sessao, id_empresa)
        if empresa is None or empresa.deletado_em is not None or _regime(sessao, empresa) is None:
            continue
        contrato = _contrato_aplicavel_bloqueado(sessao, empresa)
        if (contrato is None or contrato.id_contrato != id_contrato
                or contrato.situacao != "SUSPENSO" or contrato.suspensao_limite > instante):
            continue
        resultado = _cancelar(
            sessao, empresa, contrato, MOTIVO_EXPIRACAO, instante,
            detalhes=_detalhes(suspenso_em=contrato.suspenso_em,
                               suspensao_limite=contrato.suspensao_limite,
                               suspensao_limite_original=contrato.suspensao_limite_original,
                               acionado_por=getattr(acionado_por, "id_usuario", None)),
        )
        relatorio.cancelados.append({"id_empresa": id_empresa, "id_contrato": id_contrato})
        relatorio.revogados.extend(resultado.revogados)
    return relatorio


# ---------------------------------------------------------------------------
# Visão geral administrativa (somente leitura)
# ---------------------------------------------------------------------------
def visao_geral_contratual(sessao, *, instante=None) -> dict:
    """Painel de acompanhamento: vencimentos, suspensões e pendências de conciliação."""
    exigir_esquema_contratual(sessao)
    instante = _instante(instante)
    politica = politica_prazos()
    hoje = data_local(instante, politica.fuso)
    alerta_suspensao = instante + timedelta(days=politica.dias_alerta_suspensao)
    contagem = dict(sessao.execute(
        select(Empresa.status_conta, func.count(Empresa.id_empresa))
        .where(Empresa.deletado_em.is_(None)).group_by(Empresa.status_conta)
    ).all())
    empresas = sessao.scalars(
        select(Empresa).where(Empresa.deletado_em.is_(None)).order_by(Empresa.razao_social)
    ).all()
    regimes = set(sessao.scalars(select(RegimeContratual.id_empresa)))
    vigentes = {c.id_empresa: c for c in sessao.scalars(select(Contrato).where(
        Contrato.situacao.in_(("ATIVO", "SUSPENSO")),
    ))}
    vencendo, vencidos, suspensoes, expiradas, legado, sem_contrato, inconsistentes = ([] for _ in range(7))
    for empresa in empresas:
        contrato = vigentes.get(empresa.id_empresa)
        contratual = empresa.id_empresa in regimes
        if not contratual and empresa.status_conta != "CANCELADA":
            legado.append({"empresa": empresa, "contrato": contrato})
        if contrato is None:
            if contratual and empresa.status_conta != "CANCELADA":
                sem_contrato.append({"empresa": empresa})
            continue
        item = {"empresa": empresa, "contrato": contrato, "contratual": contratual}
        if contrato.situacao == "ATIVO" and contrato.data_fim is not None:
            dias = (contrato.data_fim - hoje).days
            if dias < 0:
                vencidos.append(item | {"dias": -dias})
            elif dias <= politica.dias_alerta_vencimento:
                vencendo.append(item | {"dias": dias})
        if contrato.situacao == "SUSPENSO":
            if contrato.suspensao_limite <= instante:
                expiradas.append(item)
            elif contrato.suspensao_limite <= alerta_suspensao:
                suspensoes.append(item)
        esperado = "ATIVA" if contrato.situacao == "ATIVO" else "SUSPENSA"
        if empresa.status_conta != esperado:
            inconsistentes.append(item | {"esperado": esperado})
    return {
        "instante": instante,
        "ativas": int(contagem.get("ATIVA", 0)),
        "suspensas": int(contagem.get("SUSPENSA", 0)),
        "canceladas": int(contagem.get("CANCELADA", 0)),
        "vencendo": vencendo, "vencidos": vencidos,
        "suspensoes_terminando": suspensoes, "suspensoes_expiradas": expiradas,
        "legado": legado, "sem_contrato": sem_contrato, "inconsistentes": inconsistentes,
        "politica": politica,
    }
