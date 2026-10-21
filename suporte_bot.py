"""
NEXO - Faturamento Inteligente | NexoBot (assistente de suporte do portal)
==========================================================================
Fachada estável do NexoBot. A implementação vive no pacote `nexobot/`
(NexoBot Advanced): normalização linguística, classificação de intenções por
evidências, busca no Guia (tabela `guia_topico`, mantida pelo CMS do Admin),
contexto mínimo de conversa e navegação por catálogo fechado.

Estratégia (gratuita e fail-safe):
  1) Tudo é decidido localmente, sem rede: intenção, página e resposta.
  2) Se HF_API_TOKEN estiver configurado, um modelo da Hugging Face pode apenas
     REDIGIR a resposta a partir de trechos do Guia já escolhidos; a saída é
     validada e, em qualquer falha, a resposta local é usada.

Escopo rígido: o NexoBot só fala do uso do portal e nunca executa operações.
A geração de devolutivas com IA (ai_devolutiva.py) é uma funcionalidade
separada e não passa por aqui.
"""

from nexobot import responder
from nexobot.navegacao import DESTINOS, urls_destinos, validar_destino

__all__ = ["responder", "DESTINOS", "urls_destinos", "validar_destino"]
