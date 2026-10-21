"""Representação explícita das intenções e do resultado da interpretação.

A interpretação descreve o que foi entendido; ela não autoriza nada. A
autorização de ações acontece em `servico.py`, contra o catálogo fechado.
"""

from dataclasses import dataclass, field
from enum import Enum


class Intencao(str, Enum):
    VAZIA = "vazia"                                 # nada digitado
    SEM_TEXTO = "sem_texto"                         # só emojis/símbolos
    SAUDACAO = "saudacao"
    DESPEDIDA = "despedida"                         # inclui agradecimentos
    AJUDA_GERAL = "ajuda_geral"                     # "o que você faz?"
    CONFIRMACAO = "confirmacao"                     # "sim", "pode" após uma oferta
    RECUSA = "recusa"                               # "não, obrigado"
    NAVEGAR = "navegar"                             # ordem inequívoca
    ORIENTACAO_NAVEGACAO = "orientacao_navegacao"   # "onde fica o histórico?"
    DUVIDA_FUNCIONAL = "duvida_funcional"           # "como recupero a senha?"
    CONSULTA_DADOS = "consulta_dados"               # pede valores/dados financeiros
    SUPORTE_HUMANO = "suporte_humano"
    SOBRE_O_BOT = "sobre_o_bot"                     # comandos citados, hipóteses
    AMBIGUIDADE = "ambiguidade"
    COMANDO_NEGADO = "comando_negado"
    OPERACAO_NAO_PERMITIDA = "operacao_nao_permitida"
    ACESSO_RESTRITO = "acesso_restrito"             # área admin, URLs, caminhos
    PAGINA_INEXISTENTE = "pagina_inexistente"
    PAGINA_ATUAL = "pagina_atual"
    FORA_DO_ESCOPO = "fora_do_escopo"
    ENTRADA_SUSPEITA = "entrada_suspeita"           # injeção de prompt, SQL, código
    DESCONHECIDA = "desconhecida"


# Intenções cuja resposta pode vir da base de conhecimento.
INFORMATIVAS = frozenset({
    Intencao.DUVIDA_FUNCIONAL, Intencao.ORIENTACAO_NAVEGACAO, Intencao.DESCONHECIDA,
})


@dataclass
class Evidencia:
    """Indício observado no texto. `peso` soma na pontuação da intenção."""
    intencao: Intencao
    peso: float
    motivo: str


@dataclass
class Interpretacao:
    intencao: Intencao
    confianca: float
    destino: str | None = None             # destino principal entendido
    forca_destino: float = 0.0             # 1.0 = página nomeada; 0.5 = assunto relacionado
    opcoes: tuple = ()                     # destinos em disputa (esclarecimento)
    modo_opcoes: str | None = None         # "navegar" ou "orientar"
    operacoes: tuple = ()                  # descrição das operações recusadas
    motivo: str | None = None              # rótulo interno da decisão
    contextual: bool = False               # destino veio do contexto da conversa
    saudacao: bool = False                 # mensagem começou com cumprimento
    consulta: str = ""                     # texto usado na busca do Guia
    evidencias: list = field(default_factory=list)
    detalhes: dict = field(default_factory=dict)
