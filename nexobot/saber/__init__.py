"""Base de conhecimento versionada do NexoBot sobre o NEXO.

Cada módulo cobre um assunto e expõe `REGISTROS`; este pacote os reúne,
valida a unicidade dos ids e as referências cruzadas, e oferece consultas
simples. Nada aqui lê banco de dados ou código em tempo de execução: o
conteúdo é texto revisado, com as fontes do código citadas em cada registro.

Camada de busca: `nexobot/conhecimento.py` indexa estes registros ao lado dos
tópicos do Guia (CMS). Camada de apresentação: `nexobot/respostas.py` escolhe
o nível (resumo, explicação, passos, aprofundamento).
"""

from . import (
    acesso, administracao, analises, dashboard, devolutivas_historico, empresas_planos,
    indicadores, notificacoes, primeiros_passos, processamento, suporte_guia, tecnologia,
    uploads, visao_geral,
)
from .glossario import GLOSSARIO, definicao_direta, termo_definido, termos_citados
from .modelo import Conhecimento, validar

MODULOS = (
    visao_geral, primeiros_passos, acesso, empresas_planos, analises, uploads, processamento,
    indicadores, dashboard, devolutivas_historico, notificacoes, suporte_guia, administracao,
    tecnologia,
)

REGISTROS: tuple[Conhecimento, ...] = tuple(r for m in MODULOS for r in m.REGISTROS)
POR_ID: dict[str, Conhecimento] = {r.id: r for r in REGISTROS}
CATEGORIAS: tuple[str, ...] = tuple(dict.fromkeys(r.categoria for r in REGISTROS))

# Assuntos oferecidos na saudação e na ajuda (curados; nunca vêm do banco).
SUGESTOES_INICIAIS = (
    ("Como funciona o NEXO?", "nexo.visao_geral.funcionamento"),
    ("Enviar relatórios", "nexo.uploads.como_enviar"),
    ("Entender meus indicadores", "nexo.indicadores.interpretar"),
    ("Ver minhas análises", "nexo.historico.abrir"),
    ("Preciso de ajuda", "nexo.suporte.falar_com_equipe"),
)


def _conferir():
    ids = [r.id for r in REGISTROS]
    duplicados = {i for i in ids if ids.count(i) > 1}
    if duplicados:
        raise ValueError(f"Ids duplicados na base de conhecimento: {sorted(duplicados)}")
    for r in REGISTROS:
        for alvo in (*r.relacionados, *( (r.proximo,) if r.proximo else () )):
            if alvo not in POR_ID:
                raise ValueError(f"{r.id} referencia id inexistente: {alvo}")
    for termo, alvo in GLOSSARIO.items():
        if alvo not in POR_ID:
            raise ValueError(f"Glossário: termo {termo!r} aponta para id inexistente {alvo}")
    for _, alvo in SUGESTOES_INICIAIS:
        if alvo not in POR_ID:
            raise ValueError(f"Sugestão inicial aponta para id inexistente {alvo}")


_conferir()


def por_id(registro_id) -> Conhecimento | None:
    return POR_ID.get(registro_id) if isinstance(registro_id, str) else None


def validar_tudo() -> dict[str, list[str]]:
    """Problemas por id (vazio quando a base está íntegra); usado pelos testes."""
    return {r.id: p for r in REGISTROS if (p := validar(r))}


__all__ = [
    "Conhecimento", "REGISTROS", "POR_ID", "CATEGORIAS", "SUGESTOES_INICIAIS", "GLOSSARIO",
    "por_id", "validar_tudo", "definicao_direta", "termos_citados",
]
