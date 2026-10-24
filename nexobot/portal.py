"""Compatibilidade: os "fatos do portal" agora vivem em `nexobot/saber`.

Na versão 1 do NexoBot Advanced este módulo guardava onze fatos da interface.
Na versão 2 eles foram absorvidos pela base de conhecimento estruturada
(`nexobot/saber`), que os mantém com o mesmo propósito (descrever
comportamento verificável no código) e acrescenta níveis de resposta.

`FATOS` continua disponível para quem importava daqui: é derivado dos
registros da base, com as chaves antigas preservadas.
"""

from dataclasses import dataclass

from . import saber


@dataclass(frozen=True)
class Fato:
    chave: str
    pergunta: str
    termos: str
    resposta: str
    destino: str | None


# Chave antiga -> registro atual.
_EQUIVALENTES = {
    "status_processamento": "nexo.uploads.status",
    "planilha_errada": "nexo.uploads.substituir",
    "compras_e_vendas": "nexo.uploads.por_que_dois",
    "publicacao": "nexo.devolutivas.publicacao",
    "analise_anterior": "nexo.historico.consultar_anterior",
    "pressao_estoque": "nexo.indicadores.pressao_estoque",
    "curva_abc": "nexo.indicadores.curva_abc",
    "notificacoes": "nexo.notificacoes.sininho",
    "acesso_portal": "nexo.acesso.nao_consigo_entrar",
    "chamados_status": "nexo.suporte.acompanhar",
    "conta_suspensa": "nexo.empresas.conta_suspensa",
}

FATOS = tuple(
    Fato(chave, saber.POR_ID[rid].titulo, saber.POR_ID[rid].termos, saber.POR_ID[rid].resumo,
         saber.POR_ID[rid].destino)
    for chave, rid in _EQUIVALENTES.items()
)

__all__ = ["Fato", "FATOS"]
